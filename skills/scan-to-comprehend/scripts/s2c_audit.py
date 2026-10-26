#!/usr/bin/env python3
"""S2C source audit with an experimental structural-friction estimate."""

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

# Editorial triage weights, not coefficients fitted from eye-tracking or cognitive-load data.
# Keep them versioned so API/MCP consumers can distinguish changes to the heuristic.
RISK_WEIGHTS = {
    "no_headings": 22,
    "no_h1": 12,
    "empty_heading": 12,
    "heading_jump": 8,
    "missing_alt": 10,
    "table_headers": 12,
    "generic_link": 8,
}
SUGGESTIONS = {
    "no_headings": "Add descriptive sections that let a reader locate the relevant answer.",
    "no_h1": "Give the full page a specific level-one heading that states its subject.",
    "empty_heading": "Supply a meaningful visible heading or verify the rendered runtime text.",
    "heading_jump": "Check the heading outline and use levels that reflect section nesting.",
    "missing_alt": "Describe informative images in text; use empty alt text for decorative images.",
    "table_headers": "Mark row or column headers so comparison cells retain their labels.",
    "generic_link": "Name the destination or action in the link text.",
}


def issue(code: str, level: str, message: str) -> dict[str, str]:
    return {"code": code, "level": level, "message": message}


class Structure(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[tuple[int, str]] = []
        self.links: list[str] = []
        self.images = 0
        self.images_missing_alt = 0
        self.tables = 0
        self.table_headers = 0
        self.tables_without_headers = 0
        self._table_header_stack: list[bool] = []
        self._capture: list[tuple[str, list[str]]] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        props = dict(attrs)
        if tag in {"script", "style", "template", "noscript"}:
            self._skip += 1
        if tag == "img":
            self.images += 1
            if "alt" not in props:
                self.images_missing_alt += 1
        if tag == "table":
            self.tables += 1
            self._table_header_stack.append(False)
        if tag == "th":
            self.table_headers += 1
            if self._table_header_stack:
                self._table_header_stack[-1] = True
        if not self._skip and (re.fullmatch(r"h[1-6]", tag) or tag == "a"):
            self._capture.append((tag, []))

    def handle_data(self, data: str) -> None:
        if not self._skip:
            for _, chunks in self._capture:
                chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "table" and self._table_header_stack:
            if not self._table_header_stack.pop():
                self.tables_without_headers += 1
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
           require_h1: bool = True, tables_without_headers: int | None = None) -> list[dict[str, str]]:
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
    unlabelled_tables = tables_without_headers if tables_without_headers is not None else int(bool(tables and not table_headers))
    if unlabelled_tables:
        findings.append(issue("table_headers", "review", f"{unlabelled_tables} table(s) have no header cells; inspect whether row and column relationships are clear."))
    if links and any(re.fullmatch(r"(?:click here|here|read more|learn more)", text, re.I) for text in links):
        findings.append(issue("generic_link", "review", "A generic link label may hide its destination when scanned out of context."))
    return findings


def evaluate_structure(findings: list[dict[str, str]], *, headings: list[tuple[int, str]],
                       links: list[str], images: int, missing_alt: int, tables: int,
                       table_headers: int, tables_without_headers: int, full_page: bool) -> dict:
    """Explain an uncalibrated source-only index and actionable observations."""
    codes = {item["code"] for item in findings}
    components = []
    for item in findings:
        code = item["code"]
        if code == "no_h1" and "no_headings" in codes:
            continue  # One absent outline should not be charged twice.
        points = min(20, missing_alt * RISK_WEIGHTS[code]) if code == "missing_alt" else RISK_WEIGHTS[code]
        components.append({"code": code, "points": points, "evidence": item["message"]})
    strengths = []
    if headings and all(text for _, text in headings):
        strengths.append({"code": "labeled_sections", "message": "Source headings provide named entry points."})
    if full_page and any(level == 1 for level, _ in headings):
        strengths.append({"code": "page_heading", "message": "The full page has a level-one heading."})
    if links and "generic_link" not in codes:
        strengths.append({"code": "descriptive_links", "message": "No generic link labels were detected in source text."})
    if images and not missing_alt:
        strengths.append({"code": "image_alternatives", "message": "Every source image has an alt attribute or Markdown alternative; quality still needs review."})
    if tables and table_headers and not tables_without_headers:
        strengths.append({"code": "table_headers_present", "message": "Every table has header cells; their relationships still need review."})
    suggestions = [{"code": item["code"], "priority": item["level"],
                    "action": SUGGESTIONS[item["code"]]} for item in findings]
    return {
        "estimated_cognitive_load": {
            "name": "Structural friction risk index",
            "score": min(100, sum(item["points"] for item in components)),
            "scale": "0-100; higher means more flagged source-structure friction, not more measured cognitive load",
            "method": "s2c-source-heuristic-v1",
            "confidence": "low",
            "calibration": "Uncalibrated editorial weights; no population norm or validated cognitive-load units.",
            "components": components,
        },
        "strengths": strengths,
        "suggestions": suggestions,
        "next_checks": [
            "Inspect rendered desktop and mobile layout, including visual density and text-graphic proximity.",
            "Ask representative readers to find a fact and explain it; record task success separately from this index.",
        ],
    }


def audit_html(source: str, label: str) -> dict:
    parser = Structure()
    parser.feed(source)
    full_page = bool(re.search(r"<html\b|<!doctype\s+html", source, re.I))
    findings = assess(parser.headings, parser.images_missing_alt, parser.tables, parser.table_headers,
                      parser.links, full_page, parser.tables_without_headers)
    evaluation = evaluate_structure(findings, headings=parser.headings, links=parser.links,
                                    images=parser.images, missing_alt=parser.images_missing_alt,
                                    tables=parser.tables, table_headers=parser.table_headers,
                                    tables_without_headers=parser.tables_without_headers, full_page=full_page)
    return {"source": label, "format": "html", "headings": [{"level": n, "text": t} for n, t in parser.headings],
            "findings": findings, **evaluation,
            "limit": "Source-only estimate; no rendered-layout, gaze, accessibility, or comprehension measurement."}


def audit_markdown(source: str, label: str) -> dict:
    # Ignore fenced code so example headings and image syntax do not affect a document audit.
    visible = re.sub(r"(?ms)^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1[^\n]*$", "", source)
    headings = [(len(mark), re.sub(r"\s+", " ", title).strip()) for mark, title in HEADING.findall(visible)]
    missing_alt = sum(not alt.strip() for alt in MD_IMAGE.findall(visible))
    findings = assess(headings, missing_alt)
    evaluation = evaluate_structure(findings, headings=headings, links=[],
                                    images=len(MD_IMAGE.findall(visible)), missing_alt=missing_alt,
                                    tables=0, table_headers=0, tables_without_headers=0, full_page=True)
    return {"source": label, "format": "markdown", "headings": [{"level": n, "text": t} for n, t in headings],
            "findings": findings, **evaluation,
            "limit": "Source-only estimate; no rendered-layout, gaze, accessibility, or comprehension measurement."}


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
        print(json.dumps({"schema_version": "1.1", "reports": reports}, indent=2, ensure_ascii=True))
    else:
        for report in reports:
            print(f"{report['source']}: {len(report['findings'])} structural finding(s)")
            estimate = report["estimated_cognitive_load"]
            print(f"  Structural friction risk: {estimate['score']}/100 (experimental; low confidence)")
            for finding in report["findings"]:
                print(f"  [{finding['level']}] {finding['code']}: {finding['message']}")
            for suggestion in report["suggestions"]:
                print(f"  Suggestion: {suggestion['action']}")
            for strength in report["strengths"]:
                print(f"  Strength: {strength['message']}")
        if not reports:
            print("No staged HTML or Markdown files to audit.")
    return int(args.fail_on_high and any(f["level"] == "high" for r in reports for f in r["findings"]))


if __name__ == "__main__":
    raise SystemExit(main())
