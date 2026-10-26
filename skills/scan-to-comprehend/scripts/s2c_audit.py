#!/usr/bin/env python3
"""Observable structure checks for S2C; never a comprehension or gaze score."""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import socket
import subprocess
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

MAX_BYTES = 2_000_000
HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$", re.M)
MD_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]+\)")


def issue(code: str, level: str, message: str) -> dict[str, str]:
    return {"code": code, "level": level, "message": message}


class Structure(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[tuple[int, str]] = []
        self.links: list[str] = []
        self.images_missing_alt = 0
        self.tables = 0
        self.table_headers = 0
        self._capture: list[tuple[str, list[str]]] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        props = dict(attrs)
        if tag in {"script", "style", "template", "noscript"}:
            self._skip += 1
        if tag == "img" and "alt" not in props:
            self.images_missing_alt += 1
        if tag == "table":
            self.tables += 1
        if tag == "th":
            self.table_headers += 1
        if not self._skip and (re.fullmatch(r"h[1-6]", tag) or tag == "a"):
            self._capture.append((tag, []))

    def handle_data(self, data: str) -> None:
        if not self._skip:
            for _, chunks in self._capture:
                chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._capture:
            for index in range(len(self._capture) - 1, -1, -1):
                name, chunks = self._capture[index]
                if name == tag:
                    self._capture.pop(index)
                    value = " ".join(" ".join(chunks).split())
                    if tag.startswith("h"):
                        self.headings.append((int(tag[1]), value))
                    elif tag == "a":
                        self.links.append(value)
                    break
        if tag in {"script", "style", "template", "noscript"} and self._skip:
            self._skip -= 1


def assess(headings: list[tuple[int, str]], missing_alt: int, tables: int = 0,
           table_headers: int = 0, links: list[str] | None = None,
           require_h1: bool = True) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if require_h1 and not any(level == 1 for level, _ in headings):
        findings.append(issue("no_h1", "high", "No level-one heading was found; check the entry point and title."))
    if not headings:
        findings.append(issue("no_headings", "high", "No headings were found; inspect whether readers can navigate the content."))
    if any(not label for _, label in headings):
        findings.append(issue("empty_heading", "review", "At least one heading has no source text; check whether runtime content supplies it."))
    for previous, current in zip(headings, headings[1:]):
        if current[0] > previous[0] + 1:
            findings.append(issue("heading_jump", "review", "Heading levels jump; check whether the outline communicates the intended hierarchy."))
            break
    if missing_alt:
        findings.append(issue("missing_alt", "high", f"{missing_alt} image(s) lack an alt attribute or Markdown alternative. Check decorative versus informative intent."))
    if tables and not table_headers:
        findings.append(issue("table_headers", "review", "A table has no header cells; inspect whether row and column relationships are clear."))
    if links and any(re.fullmatch(r"(?:click here|here|read more|learn more)", text, re.I) for text in links):
        findings.append(issue("generic_link", "review", "A generic link label may hide its destination when scanned out of context."))
    return findings


def audit_html(source: str, label: str) -> dict:
    parser = Structure()
    parser.feed(source)
    full_page = bool(re.search(r"<html\b|<!doctype\s+html", source, re.I))
    return {"source": label, "format": "html", "headings": [{"level": n, "text": t} for n, t in parser.headings],
            "findings": assess(parser.headings, parser.images_missing_alt, parser.tables, parser.table_headers, parser.links, full_page),
            "limit": "Structural signals only; no rendered-layout, gaze, accessibility, or comprehension measurement."}


def audit_markdown(source: str, label: str) -> dict:
    # Ignore fenced code so example headings and image syntax do not affect a document audit.
    visible = re.sub(r"(?ms)^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1[^\n]*$", "", source)
    headings = [(len(mark), re.sub(r"\s+", " ", title).strip()) for mark, title in HEADING.findall(visible)]
    missing_alt = sum(not alt.strip() for alt in MD_IMAGE.findall(visible))
    return {"source": label, "format": "markdown", "headings": [{"level": n, "text": t} for n, t in headings],
            "findings": assess(headings, missing_alt),
            "limit": "Structural signals only; no rendered-layout, gaze, accessibility, or comprehension measurement."}


def audit(source: str, label: str) -> dict:
    suffix = Path(urlsplit(label).path).suffix.lower()
    if suffix in {".md", ".markdown"}:
        return audit_markdown(source, label)
    return audit_html(source, label)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ValueError("Redirects are not followed; supply the final public URL explicitly.")


def fetch(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Supply a public HTTP or HTTPS URL without credentials.")
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("URL host must resolve only to public addresses.")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(url, headers={"User-Agent": "S2C-structural-audit/0.1"})
    with opener.open(request, timeout=10) as response:
        if "html" not in response.headers.get_content_type():
            raise ValueError("URL response is not HTML.")
        data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("URL response exceeds 2 MB limit.")
        return data.decode(response.headers.get_content_charset() or "utf-8", errors="replace")


def staged() -> list[dict]:
    names = subprocess.check_output(["git", "diff", "--cached", "--name-only", "-z", "--diff-filter=ACM"]).split(b"\0")
    reports = []
    for raw in names:
        if not raw:
            continue
        name = raw.decode("utf-8", errors="surrogateescape")
        if Path(name).suffix.lower() not in {".md", ".markdown", ".html", ".htm"}:
            continue
        content = subprocess.check_output(["git", "show", ":" + name]).decode("utf-8", errors="replace")
        reports.append(audit(content, name))
    return reports


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("path", nargs="?", help="Local HTML or Markdown file")
    group.add_argument("--url", help="Public HTML URL; no redirects")
    group.add_argument("--staged", action="store_true", help="Audit staged HTML and Markdown blobs")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    parser.add_argument("--fail-on-high", action="store_true", help="Exit 1 if any high-level structural finding")
    args = parser.parse_args()
    try:
        if args.staged:
            reports = staged()
        elif args.url:
            reports = [audit_html(fetch(args.url), args.url)]
        else:
            reports = [audit(Path(args.path).read_text(encoding="utf-8"), args.path)]
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"S2C audit: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({"reports": reports}, indent=2, ensure_ascii=False))
    else:
        for report in reports:
            print(f"{report['source']}: {len(report['findings'])} structural finding(s)")
            for finding in report["findings"]:
                print(f"  [{finding['level']}] {finding['code']}: {finding['message']}")
        if not reports:
            print("No staged HTML or Markdown files to audit.")
    return int(args.fail_on_high and any(f["level"] == "high" for r in reports for f in r["findings"]))


if __name__ == "__main__":
    raise SystemExit(main())
