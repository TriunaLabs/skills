#!/usr/bin/env python3
"""Evaluate an explicit reader task against a bounded S2C site graph."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
from urllib.parse import urlsplit

import s2c_robot_visibility
import s2c_site_graph


SCHEMA = "s2c-journey-scenario/v1"


def validate(scenario: object) -> dict:
    if not isinstance(scenario, dict) or scenario.get("schema") != SCHEMA:
        raise ValueError(f"Expected {SCHEMA}")
    allowed = {"schema", "id", "role", "goal", "target", "device", "required_phrases", "success_action"}
    if set(scenario) - allowed:
        raise ValueError("Unknown journey scenario fields")
    for key, limit in (("id", 80), ("role", 120), ("goal", 300)):
        value = scenario.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError(f"Journey {key} must be non-empty and at most {limit} characters")
    for key in ("target", "success_action"):
        value = scenario.get(key, "")
        if not isinstance(value, str) or len(value) > 300:
            raise ValueError(f"Journey {key} must be at most 300 characters")
    if scenario.get("device", "desktop") not in {"desktop", "mobile", "reflow-320"}:
        raise ValueError("Journey device must be a captured viewport ID")
    phrases = scenario.get("required_phrases", [])
    if not isinstance(phrases, list) or len(phrases) > 8 or any(
        not isinstance(value, str) or not 3 <= len(value.strip()) <= 160 for value in phrases
    ):
        raise ValueError("Give at most eight required phrases of 3–160 characters")
    return {"schema": SCHEMA, "id": scenario["id"].strip(), "role": scenario["role"].strip(),
            "goal": scenario["goal"].strip(), "target": scenario.get("target", "").strip(),
            "device": scenario.get("device", "desktop"),
            "required_phrases": list(dict.fromkeys(value.strip() for value in phrases)),
            "success_action": scenario.get("success_action", "").strip()}


def project(graph: dict, scenario: dict, snapshot: dict | None = None) -> dict:
    if graph.get("schema") != "s2c-site-graph/v1":
        raise ValueError("Expected s2c-site-graph/v1")
    scenario = validate(scenario)
    start = graph["start_url"]
    target = s2c_site_graph.canonical_url(start, scenario["target"]) if scenario["target"] else ""
    if scenario["target"] and not target:
        raise ValueError("Journey target must be on the captured site's origin")
    pages = {page["url"]: page for page in graph["pages"]}
    raw_edges = graph["edges"]
    rendered_edges = (graph.get("rendered_overlay") or {}).get("edges") or []
    mixed_edges = ([edge for edge in raw_edges if edge["from"] != start] + rendered_edges
                   if rendered_edges else [])
    raw_path = s2c_site_graph.shortest_path(start, target, raw_edges) if target in pages else []
    rendered_path = (s2c_site_graph.shortest_path(start, target, mixed_edges)
                     if target in pages and rendered_edges else None)
    frame = None
    if snapshot is not None:
        if snapshot.get("schema") != "s2c-browser-capture/v1" or snapshot.get("url") != start:
            raise ValueError("Journey snapshot must capture the graph start URL")
        frame = next((item for item in snapshot.get("frames", []) if item.get("id") == scenario["device"]), None)
    initial = []
    for page in pages.values():
        initial.append((page["url"], page.get("title", "")))
        initial.extend((page["url"], heading.get("text", "")) for heading in page.get("headings", []))
    rendered = ([(node.get("id"), str(node.get("text") or "")) for node in frame.get("nodes", [])
                 if node.get("visible")] if frame else [])
    evidence = []
    for phrase in scenario["required_phrases"]:
        needle = s2c_robot_visibility.normalized(phrase)
        page_hits = [{"url": url, "text": text[:220]} for url, text in initial
                     if needle in s2c_robot_visibility.normalized(text)][:5]
        node_hits = [{"node_id": node_id, "text": text[:220]} for node_id, text in rendered
                     if needle in s2c_robot_visibility.normalized(text)][:5]
        evidence.append({"phrase": phrase, "status": "found" if page_hits or node_hits else "review",
                         "initial_heading_hits": page_hits, "rendered_start_hits": node_hits})
    action = {"label": scenario["success_action"], "status": "not_requested" if not scenario["success_action"] else
              "not_checked" if frame is None else "review", "node_hits": []}
    if scenario["success_action"] and frame is not None:
        needle = s2c_robot_visibility.normalized(scenario["success_action"])
        hits = [{"node_id": node.get("id"), "tag": node.get("tag"), "label": label[:160],
                 "href": node.get("href")}
                for node in frame["nodes"] if node.get("visible") and node.get("tag") in {"a", "button", "input"}
                if (label := str(node.get("name") or node.get("aria_label") or node.get("text") or "").strip())
                and needle in s2c_robot_visibility.normalized(label)]
        action = {"label": scenario["success_action"], "status": "found" if hits else "review",
                  "node_hits": hits[:8]}
    return {"schema": "s2c-journey-evaluation/v1", "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "scenario": scenario, "start_url": start, "target_url": target,
            "coverage": graph["coverage"], "route": {"initial_html": raw_path,
                "rendered_start": rendered_path,
                "status": "found" if raw_path or rendered_path else
                          "not_requested" if not target else "review"},
            "evidence": evidence, "success_action": action,
            "limits": ["The role changes the requested evidence and success action; it does not alter a gaze model.",
                       "Only fetched page titles and headings plus visible start-page elements were searched.",
                       "A phrase or control-label match does not verify the answer or that the action works.",
                       "A missing route or phrase within this bounded graph is a review candidate, not proof of absence.",
                       "No task completion, comprehension, or actual user behavior was measured."]}


def render(result: dict) -> str:
    if result.get("schema") != "s2c-journey-evaluation/v1":
        raise ValueError("Expected s2c-journey-evaluation/v1")
    scenario = result["scenario"]
    def route(value: list[str] | None) -> str:
        if value is None:
            return "No rendered start-page overlay captured"
        if not value:
            return "No route found within the captured graph"
        return " → ".join(escape(urlsplit(url).path or "/") for url in value)
    evidence = "".join(f"<li><strong>{escape(item['phrase'])}</strong> · {escape(item['status'])}"
                       f"<small>{len(item['initial_heading_hits'])} initial heading/title hit(s); "
                       f"{len(item['rendered_start_hits'])} rendered start-page hit(s)</small></li>"
                       for item in result["evidence"])
    limits = "".join(f"<li>{escape(item)}</li>" for item in result["limits"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>S2C journey · {escape(scenario['id'])}</title><style>
    :root{{font:16px/1.5 system-ui,sans-serif;color:#18312a;background:#f5f7f4}}body{{margin:0}}main{{max-width:860px;margin:auto;padding:32px 20px 80px}}h1{{font-size:clamp(30px,5vw,52px);line-height:1.1}}section{{background:white;border:1px solid #d9e1d9;border-radius:10px;padding:22px;margin:16px 0}}.eyebrow{{color:#0d6b4e;font-weight:800;font-size:12px;letter-spacing:.1em}}article{{background:#f1f6f2;border-left:4px solid #0d6b4e;padding:12px 16px;margin:10px 0;overflow-wrap:anywhere}}small{{display:block;color:#52635a}}li{{margin:8px 0}}
    </style></head><body><main><p class="eyebrow">SCAN TO COMPREHEND / TASK JOURNEY</p><h1>{escape(scenario['goal'])}</h1><p>Role: {escape(scenario['role'])} · Device: {escape(scenario['device'])} · Evaluated {escape(result['evaluated_at'])}</p>
    <section><h2>Route within the captured graph</h2><p>Target: {escape(result['target_url'] or 'none supplied')}</p><article><strong>Initial HTML</strong><p>{route(result['route']['initial_html'])}</p></article><article><strong>Rendered start page</strong><p>{route(result['route']['rendered_start'])}</p></article></section>
    <section><h2>Required evidence</h2><ul>{evidence or '<li>No phrase criterion supplied.</li>'}</ul></section>
    <section><h2>Success action</h2><p>{escape(result['success_action']['label'] or 'None supplied')} · {escape(result['success_action']['status'])}</p><p>{len(result['success_action']['node_hits'])} matching captured start-page control(s).</p></section>
    <section><h2>Assessment boundary</h2><ul>{limits}</ul><p>Fetched pages: {result['coverage']['fetched_pages']}; skipped pages: {result['coverage']['skipped_pages']}; frontier remaining: {result['coverage']['frontier_remaining']}.</p></section></main></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-graph", required=True, type=Path)
    parser.add_argument("--scenario", required=True, type=Path)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    read = lambda path: json.loads(path.read_text(encoding="utf-8")) if path else None
    result = project(read(args.site_graph), read(args.scenario), read(args.snapshot))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "journey.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output / "journey.html").write_text(render(result), encoding="utf-8")
    print(args.output / "journey.html")


if __name__ == "__main__":
    main()
