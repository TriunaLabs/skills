#!/usr/bin/env python3
"""Bounded raw-HTML site graph with an optional captured rendered-link overlay."""

from __future__ import annotations

import argparse
from collections import deque
from datetime import datetime, timezone
import hashlib
from html import escape
import json
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.request import url2pathname
from urllib.robotparser import RobotFileParser

import s2c_robot_visibility
import s2c_site_basics


MAX_HTML_BYTES = 2_000_000
MAX_LINKS_PER_PAGE = 100


def canonical_url(base: str, href: str) -> str:
    if not href or href.startswith("#") or len(href) > 2048:
        return ""
    target = urljoin(base, href)
    parsed = urlsplit(target)
    if parsed.scheme not in {"https", "http", "file"} or not s2c_site_basics.same_origin(base, target):
        return ""
    return parsed._replace(fragment="").geturl()


def shortest_path(start: str, target: str, edges: list[dict]) -> list[str]:
    adjacency: dict[str, list[str]] = {}
    for edge in edges:
        adjacency.setdefault(edge["from"], []).append(edge["to"])
    queue = deque([(start, [start])])
    seen = {start}
    while queue:
        current, path = queue.popleft()
        if current == target:
            return path
        for next_url in adjacency.get(current, []):
            if next_url not in seen:
                seen.add(next_url)
                queue.append((next_url, path + [next_url]))
    return []


def crawl(start: str, fetch, *, max_pages: int = 12, max_depth: int = 2,
          allowed=None, snapshot: dict | None = None, target: str = "") -> dict:
    if not 1 <= max_pages <= 50 or not 0 <= max_depth <= 5:
        raise ValueError("The crawl budget must be 1–50 pages and 0–5 link steps")
    start = urlsplit(start)._replace(fragment="").geturl()
    if urlsplit(start).scheme not in {"https", "http", "file"}:
        raise ValueError("Start with an HTTP(S) URL or an owned local file fixture")
    allowed = allowed or (lambda _url: True)
    queue = deque([(start, 0)])
    seen: set[str] = set()
    pages: list[dict] = []
    edges: list[dict] = []
    skipped: list[dict] = []
    while queue and len(pages) < max_pages:
        url, depth = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        if not allowed(url):
            skipped.append({"url": url, "depth": depth, "reason": "disallowed"})
            continue
        try:
            status, source = fetch(url)
        except (OSError, ValueError) as error:
            skipped.append({"url": url, "depth": depth, "reason": type(error).__name__})
            continue
        if status != 200:
            skipped.append({"url": url, "depth": depth, "reason": f"http_{status}"})
            continue
        raw = s2c_robot_visibility.SourceView()
        raw.feed(source)
        links = list(dict.fromkeys(filter(None, (canonical_url(url, href)
                                                   for href in raw.links[:MAX_LINKS_PER_PAGE]))))
        pages.append({"url": url, "depth": depth, "title": " ".join(raw.title_parts),
                      "headings": raw.headings[:20], "link_count": len(links),
                      "raw_html_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
                      "fetched_at": datetime.now(timezone.utc).isoformat()})
        for link in links:
            edges.append({"from": url, "to": link, "view": "initial_html"})
            if depth < max_depth and link not in seen:
                queue.append((link, depth + 1))

    rendered_edges: list[dict] = []
    rendered_basis = "not_captured"
    if snapshot and snapshot.get("frames"):
        frame = next((item for item in snapshot["frames"] if item.get("id") == "desktop"), snapshot["frames"][0])
        frame_url = frame.get("url") or snapshot.get("url")
        if frame_url != start:
            raise ValueError("Rendered snapshot URL must match the crawl start URL")
        rendered_edges = [{"from": start, "to": link, "view": "rendered_dom", "node_id": node.get("id")}
                          for node in frame.get("nodes", []) if node.get("tag") == "a" and node.get("visible")
                          and (link := canonical_url(start, str(node.get("href") or "")))]
        rendered_basis = "one no-interaction desktop capture at the start URL"

    target_url = canonical_url(start, target) if target else ""
    fetched_urls = {page["url"] for page in pages}
    raw_path = shortest_path(start, target_url, edges) if target_url in fetched_urls else []
    overlay_edges = [edge for edge in edges if edge["from"] != start] + rendered_edges if rendered_edges else []
    rendered_path = shortest_path(start, target_url, overlay_edges) if target_url in fetched_urls and rendered_edges else []
    return {"schema": "s2c-site-graph/v1", "created_at": datetime.now(timezone.utc).isoformat(),
            "start_url": start, "budget": {"max_pages": max_pages, "max_depth": max_depth,
                                           "max_links_per_page": MAX_LINKS_PER_PAGE},
            "coverage": {"fetched_pages": len(pages), "skipped_pages": len(skipped),
                         "frontier_remaining": len(queue), "raw_edges": len(edges),
                         "rendered_start_edges": len(rendered_edges)},
            "pages": pages, "edges": edges, "skipped": skipped,
            "rendered_overlay": {"basis": rendered_basis, "edges": rendered_edges},
            "task_path": {"target": target_url, "initial_html": raw_path,
                          "rendered_start": rendered_path if rendered_edges else None},
            "limitations": ["Only links in initial HTML were traversed; rendered links were observed on the start page only.",
                            "Skipped, blocked, deep, and undiscovered pages were not audited.",
                            "A graph route is not a measured human task completion or search-engine crawl."]}


def render_report(result: dict) -> str:
    if result.get("schema") != "s2c-site-graph/v1":
        raise ValueError("Expected s2c-site-graph/v1")
    path = result["task_path"]
    def route(urls: list[str] | None) -> str:
        if urls is None:
            return "Not captured"
        if not urls:
            return "No route found within the captured graph"
        return " → ".join(escape(urlsplit(url).path.rsplit("/", 1)[-1] or "/") for url in urls)
    pages = "".join(f"<tr><td>{escape(urlsplit(page['url']).path.rsplit('/', 1)[-1] or '/')}</td>"
                    f"<td>{escape(page['title'])}</td><td>{page['depth']}</td><td>{page['link_count']}</td></tr>"
                    for page in result["pages"])
    skipped = "".join(f"<li>{escape(urlsplit(item['url']).path.rsplit('/', 1)[-1])}: "
                      f"{escape(item['reason'])}</li>" for item in result["skipped"])
    coverage = result["coverage"]
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>S2C site graph</title><style>
    :root{{font-family:Inter,ui-sans-serif,system-ui,sans-serif;color:#18312a;background:#f5f7f4}}body{{margin:0}}main{{max-width:1000px;margin:auto;padding:36px 24px 80px}}h1{{font-size:clamp(32px,5vw,55px);letter-spacing:-.05em}}.eyebrow{{color:#0d6b4e;font-weight:800;font-size:12px;letter-spacing:.1em}}section{{background:#fff;border:1px solid #d9e1d9;border-radius:11px;padding:24px;margin:18px 0}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}.cards div{{background:#eaf1eb;padding:17px;border-radius:8px}}.cards strong{{display:block;font-size:26px}}.cards span,.note{{font-size:12px;color:#52635a}}.routes{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}.routes article{{padding:16px;border-left:4px solid #0d6b4e;background:#f8fbf8;overflow-wrap:anywhere}}table{{border-collapse:collapse;width:100%}}th,td{{padding:10px;border-bottom:1px solid #d9e1d9;text-align:left}}.scroll{{overflow:auto}}@media(max-width:700px){{.cards,.routes{{grid-template-columns:1fr 1fr}}}}@media(max-width:430px){{.cards,.routes{{grid-template-columns:1fr}}}}
    </style></head><body><main><p class="eyebrow">SCAN TO COMPREHEND / BOUNDED SITE GRAPH</p><h1>Where can the task go?</h1><p class="note">Generated {escape(result['created_at'])}. Start: {escape(result['start_url'])}. This is a captured graph, not a record of a person's browsing.</p>
    <section class="cards"><div><strong>{coverage['fetched_pages']}</strong><span>HTML pages fetched</span></div><div><strong>{coverage['raw_edges']}</strong><span>Initial HTML links</span></div><div><strong>{coverage['rendered_start_edges']}</strong><span>Rendered start links</span></div><div><strong>{coverage['skipped_pages']}</strong><span>Skipped or failed</span></div></section>
    <section><h2>Task path</h2><p>Target: {escape(path['target'] or 'none supplied')}</p><div class="routes"><article><h3>Initial HTML</h3><p>{route(path['initial_html'])}</p></article><article><h3>Rendered start page</h3><p>{route(path['rendered_start'])}</p></article></div><p class="note">The rendered overlay replaces only the start page's edges. Other pages use their initial HTML links. No clicks were simulated.</p></section>
    <section><h2>Fetched pages</h2><div class="scroll"><table><thead><tr><th>Page</th><th>Title</th><th>Depth</th><th>Links</th></tr></thead><tbody>{pages}</tbody></table></div></section>
    <section><h2>Outside the captured graph</h2>{'<ul>'+skipped+'</ul>' if skipped else '<p>No fetch failure within the bounded frontier.</p>'}<p class="note">Frontier remaining: {coverage['frontier_remaining']}. Budget: {result['budget']['max_pages']} pages, {result['budget']['max_depth']} link steps.</p></section>
    </main></body></html>"""


def fixture_fetch(root: Path):
    root = root.resolve()
    def fetch(url: str) -> tuple[int, str]:
        parsed = urlsplit(url)
        if parsed.scheme != "file":
            raise ValueError("Fixture crawl accepts only local files")
        path = Path(url2pathname(parsed.path)).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Fixture link left the demo directory")
        if path.suffix.lower() not in {".html", ".htm"}:
            return 415, ""
        if not path.is_file():
            return 404, ""
        if path.stat().st_size > MAX_HTML_BYTES:
            raise ValueError("HTML page exceeds the byte cap")
        return 200, path.read_text(encoding="utf-8")
    return fetch


def public_fetch(url: str) -> tuple[int, str]:
    status, headers, body = s2c_site_basics.get_public(url, MAX_HTML_BYTES, timeout=10)
    if status != 200 or "html" not in headers.get("content-type", ""):
        return status if status != 200 else 415, ""
    return status, body.decode("utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="Public HTTP(S) start URL; robots.txt and public-IP rules apply")
    source.add_argument("--fixture-dir", type=Path, help="Owned local HTML fixture directory with index.html")
    parser.add_argument("--snapshot", type=Path, help="Optional captured start-page snapshot for rendered links")
    parser.add_argument("--target", default="", help="Same-origin target path or URL for route comparison")
    parser.add_argument("--max-pages", type=int, default=12)
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--output", required=True, type=Path, help="New or empty output directory")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output directory must be new or empty")
    if args.fixture_dir:
        root = args.fixture_dir.resolve()
        start = (root / "index.html").as_uri()
        fetch = fixture_fetch(root)
        allowed = lambda url: (urlsplit(url).scheme == "file" and
                               Path(url2pathname(urlsplit(url).path)).resolve().is_relative_to(root))
    else:
        start = args.url
        if urlsplit(start).scheme not in {"http", "https"}:
            raise ValueError("Public crawl requires HTTP(S)")
        robots = s2c_robot_visibility.fetch_robots(start)
        if robots["status"] not in {"absent", "retrieved"}:
            raise ValueError("Could not confirm robots policy; no crawl started")
        robot_parser = RobotFileParser()
        robot_parser.parse(robots.get("text", "").splitlines())
        allowed = lambda url: robot_parser.can_fetch("S2C-SiteGraph/0.1", url)
        fetch = public_fetch
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8")) if args.snapshot else None
    result = crawl(start, fetch, max_pages=args.max_pages, max_depth=args.max_depth,
                   allowed=allowed, snapshot=snapshot, target=args.target)
    output.mkdir(parents=True, exist_ok=True)
    (output / "site-graph.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output / "site-graph.html").write_text(render_report(result), encoding="utf-8")
    print(output / "site-graph.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
