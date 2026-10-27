#!/usr/bin/env python3
"""Compare source and no-interaction rendering for crawler visibility review."""

from __future__ import annotations

from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import s2c_site_basics


def normalized(value: object) -> str:
    return " ".join(re.findall(r"\w+", str(value or "").casefold()))


class SourceView(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text: list[str] = []
        self.links: list[str] = []
        self.assets: list[str] = []
        self.robots: list[str] = []
        self.suppressed = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag in {"script", "style", "template"}:
            self.suppressed += 1
        if tag == "a" and values.get("href"):
            self.links.append(values["href"] or "")
        if tag == "script" and values.get("src"):
            self.assets.append(values["src"] or "")
        if tag == "link" and "stylesheet" in (values.get("rel") or "").lower() and values.get("href"):
            self.assets.append(values["href"] or "")
        if tag == "meta" and (values.get("name") or "").lower() in {"robots", "googlebot"}:
            self.robots.append(values.get("content") or "")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "template"}:
            self.suppressed = max(0, self.suppressed - 1)

    def handle_data(self, data: str) -> None:
        if not self.suppressed and data.strip():
            self.text.append(data.strip())


def watched_phrases(frame: dict, requested: list[str] | None) -> list[str]:
    if requested:
        if len(requested) > 5 or any(not isinstance(value, str) or not 3 <= len(value.strip()) <= 160 for value in requested):
            raise ValueError("Provide at most five important phrases of 3–160 characters each")
        return list(dict.fromkeys(value.strip() for value in requested))
    seen, chosen = set(), []
    for node in frame.get("nodes", []):
        if node.get("tag") not in {"h1", "h2", "h3"} or not node.get("visible"):
            continue
        words = str(node.get("text") or "").split()
        phrase = " ".join(words[:18]).strip()
        key = normalized(phrase)
        if len(key) >= 8 and key not in seen:
            seen.add(key)
            chosen.append(phrase)
        if len(chosen) == 10:
            break
    return chosen


def _directives(value: str) -> set[str]:
    return {token.strip().lower() for token in re.split(r"[,\s]+", value or "") if token.strip()}


def _same_origin_links(base: str, hrefs: list[str]) -> set[str]:
    result = set()
    for href in hrefs:
        target = urljoin(base, href)
        if s2c_site_basics.same_origin(base, target):
            result.add(urlsplit(target)._replace(fragment="").geturl())
    return result


def fetch_robots(base: str) -> dict:
    parsed = urlsplit(base)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return {"status": "not_applicable", "text": ""}
    url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        status, headers, data = s2c_site_basics.get_public(url, max_bytes=65536)
    except (OSError, ValueError) as error:
        return {"status": "unavailable", "text": "", "detail": type(error).__name__}
    if status == 404:
        return {"status": "absent", "text": "", "http_status": status}
    if status != 200 or "text" not in headers.get("content-type", "text/plain"):
        return {"status": "unavailable", "text": "", "http_status": status}
    return {"status": "retrieved", "text": data.decode("utf-8", errors="replace"), "http_status": status}


def project(raw_html: str | None, snapshot: dict, *, important: list[str] | None = None,
            x_robots_tag: str = "", robots: dict | None = None) -> dict:
    if not snapshot.get("frames"):
        raise ValueError("Robot visibility needs a captured frame")
    frame = next((item for item in snapshot["frames"] if item.get("id") == "desktop"), snapshot["frames"][0])
    base = frame.get("url") or snapshot.get("url") or ""
    raw = SourceView()
    if raw_html is not None:
        raw.feed(raw_html)
    raw_text = normalized(" ".join(raw.text)) if raw_html is not None else ""
    rendered_text = normalized(" ".join(str(node.get("text") or "") for node in frame.get("nodes", [])
                                        if node.get("visible")))
    phrases = watched_phrases(frame, important)
    phrase_rows = []
    for phrase in phrases:
        needle = normalized(phrase)
        source = bool(raw_html is not None and needle and needle in raw_text)
        rendered = bool(needle and needle in rendered_text)
        status = ("both" if source and rendered else "rendered_only" if rendered else
                  "source_only" if source else "not_found")
        phrase_rows.append({"phrase": phrase, "source": source, "rendered": rendered, "status": status})
    rendered_links = _same_origin_links(base, [str(node.get("href") or "") for node in frame.get("nodes", [])
                                                if node.get("tag") == "a" and node.get("visible") and node.get("href")])
    raw_links = _same_origin_links(base, raw.links) if raw_html is not None else set()
    rendered_only_links = sorted(rendered_links - raw_links)[:15] if raw_html is not None else []
    directives = _directives(" ".join(raw.robots) + " " + x_robots_tag)
    rendered_directives = _directives((frame.get("head") or {}).get("robots_meta", ""))
    checks = []
    if raw_html is None:
        checks.append({"id": "source_unavailable", "status": "not_checked", "title": "Initial HTML comparison unavailable",
                       "evidence": "This replay has no saved raw HTML.", "action": "Run a fresh audit or provide the source HTML."})
    if directives & {"noindex", "none"}:
        checks.append({"id": "noindex", "status": "warning", "title": "Initial response requests no indexing",
                       "evidence": "Raw robots meta or X-Robots-Tag contains noindex/none.",
                       "action": "If this page should appear in search, remove the unintended directive and verify with URL Inspection."})
    if directives & {"nofollow", "none"}:
        checks.append({"id": "nofollow", "status": "review", "title": "Initial response requests no link following",
                       "evidence": "Raw robots meta or X-Robots-Tag contains nofollow/none.",
                       "action": "Confirm that suppressing link discovery is intended."})
    if rendered_directives & {"noindex", "none"} and not directives & {"noindex", "none"}:
        checks.append({"id": "rendered_noindex", "status": "review", "title": "Rendered DOM adds a noindex directive",
                       "evidence": "The captured DOM robots meta contains noindex/none, absent from the initial response.",
                       "action": "Confirm whether this script-set directive is intentional in the target crawler's rendered HTML."})
    robots = robots or {"status": "not_checked", "text": ""}
    blocked_assets = []
    if robots.get("status") == "retrieved" and base.startswith(("http://", "https://")):
        parser = RobotFileParser()
        parser.parse(robots.get("text", "").splitlines())
        if not parser.can_fetch("Googlebot", base):
            checks.append({"id": "robots_page", "status": "warning", "title": "robots.txt appears to block this page",
                           "evidence": "Googlebot rule screen disallows the audited URL.",
                           "action": "Review the matching robots.txt group and confirm the intended crawl policy in Search Console."})
        for asset in raw.assets[:30]:
            target = urljoin(base, asset)
            if s2c_site_basics.same_origin(base, target) and not parser.can_fetch("Googlebot", target):
                blocked_assets.append(target)
        if blocked_assets:
            checks.append({"id": "robots_assets", "status": "review", "title": "robots.txt may block rendering assets",
                           "evidence": f"{len(blocked_assets)} same-origin CSS/JS asset(s) matched a disallow rule.",
                           "action": "Allow essential CSS and JS resources, then inspect the crawler-rendered page."})
    if any(item["status"] == "rendered_only" for item in phrase_rows):
        count = sum(item["status"] == "rendered_only" for item in phrase_rows)
        checks.append({"id": "rendered_only_text", "status": "review", "title": "Important text relies on rendering",
                       "evidence": f"{count} watched phrase(s) appear in the no-interaction rendered DOM but not initial HTML.",
                       "action": "Make essential copy available in initial HTML or verify the target crawler's rendered HTML."})
    if any(item["status"] == "source_only" for item in phrase_rows):
        count = sum(item["status"] == "source_only" for item in phrase_rows)
        checks.append({"id": "source_only_text", "status": "review", "title": "Important text is absent from the no-interaction view",
                       "evidence": f"{count} watched phrase(s) occur in initial HTML but not in captured visible text.",
                       "action": "Inspect tabs, accordions, lazy loading, and wording. Make essential information findable without a click if that matches the reader task."})
    if important and any(item["status"] == "not_found" for item in phrase_rows):
        count = sum(item["status"] == "not_found" for item in phrase_rows)
        checks.append({"id": "wanted_text_missing", "status": "review", "title": "Wanted text was not found in either view",
                       "evidence": f"{count} user-supplied phrase(s) were absent from initial HTML and captured visible text.",
                       "action": "Check alternate wording and capture timing, then add the essential fact or a clear link to it if missing."})
    if rendered_only_links:
        checks.append({"id": "rendered_only_links", "status": "review", "title": "Links depend on rendering",
                       "evidence": f"{len(rendered_only_links)} sampled same-origin link(s) appear only after rendering.",
                       "action": "Put important crawl paths in initial HTML or verify rendered link discovery."})
    return {"schema": "s2c-robot-visibility/v1", "audited_on": snapshot.get("audited_on"), "url": base,
            "basis": "Raw response compared with one Chromium no-interaction DOM; not a Googlebot emulation",
            "important_basis": "user supplied" if important else "first visible headings",
            "phrases": phrase_rows, "rendered_only_links": rendered_only_links,
            "raw_robots_meta": raw.robots, "rendered_robots_meta": (frame.get("head") or {}).get("robots_meta", ""),
            "x_robots_tag": x_robots_tag,
            "robots_txt_status": robots.get("status", "not_checked"), "blocked_assets": blocked_assets[:15],
            "checks": checks,
            "limitations": ["Googlebot can render JavaScript; rendered-only content is a dependency to verify, not proof of invisibility.",
                            "robots.txt parsing is an advisory Googlebot rule screen, not a verified crawler fetch.",
                            "This audit does not access Search Console or establish indexing, ranking, or all-bot behavior.",
                            "Hidden tab content and below-fold lazy loading are not exhaustively exercised."]}
