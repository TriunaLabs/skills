#!/usr/bin/env python3
"""Render an S2C source-audit JSON result as an inspectable HTML report."""

from __future__ import annotations

import argparse
import base64
import html
import json
from pathlib import Path
from urllib.parse import urlsplit


def escaped(value: object) -> str:
    return html.escape(str(value), quote=True)


def item_list(items: list[object], empty: str, *, field: str = "message") -> str:
    if not items:
        return f"<p class='empty'>{escaped(empty)}</p>"
    rows = []
    for item in items:
        if isinstance(item, dict):
            label = item.get(field, "")
            code = item.get("code", "")
            prefix = f"<span class='code'>{escaped(code)}</span> " if code else ""
        else:
            label, prefix = item, ""
        rows.append(f"<li>{prefix}{escaped(label)}</li>")
    return "<ul>" + "".join(rows) + "</ul>"


def heading_map(headings: list[object]) -> str:
    if not headings:
        return "<p class='empty'>No source headings found.</p>"
    rows = []
    for heading in headings:
        if not isinstance(heading, dict):
            continue
        level = heading.get("level", 1)
        try:
            level = max(1, min(6, int(level)))
        except (TypeError, ValueError):
            level = 1
        rows.append(
            f"<li class='h{level}'><span class='code'>H{level}</span> "
            f"{escaped(heading.get('text', '')) or '<em>Empty heading</em>'}</li>"
        )
    return "<ol class='outline'>" + "".join(rows) + "</ol>"


def report_html(report: dict[str, object], walkthrough: str = "") -> str:
    estimate = report.get("estimated_cognitive_load", {})
    if not isinstance(estimate, dict):
        estimate = {}
    score = estimate.get("score", "?")
    findings = report.get("findings", [])
    strengths = report.get("strengths", [])
    suggestions = report.get("suggestions", [])
    headings = report.get("headings", [])
    next_checks = report.get("next_checks", [])
    for name, value in (("findings", findings), ("strengths", strengths),
                        ("suggestions", suggestions), ("headings", headings),
                        ("next_checks", next_checks)):
        if not isinstance(value, list):
            raise ValueError(f"{name} must be an array")
    score_width = "0"
    if isinstance(score, (int, float)) and not isinstance(score, bool):
        score_width = str(max(0, min(100, score)))
    return f"""
    <article class="report" aria-label="Audit for {escaped(report.get('source', 'unknown source'))}">
      <header>
        <p class="eyebrow">SCAN TO COMPREHEND / SOURCE PREFLIGHT</p>
        <h1>{escaped(report.get('source', 'Unknown source'))}</h1>
        <p class="subtitle">A source check followed by questions for rendered and reader review.</p>
      </header>
      <section class="summary" aria-label="Structural friction estimate">
        <div class="score"><strong>{escaped(score)}</strong><span>/ 100</span></div>
        <div class="score-context">
          <h2>Structural friction risk index</h2>
          <div class="track" aria-hidden="true"><span style="width:{score_width}%"></span></div>
          <p>{len(findings)} flagged source issue(s) · {len(strengths)} narrow strength(s) · {escaped(estimate.get('confidence', 'unknown'))} confidence</p>
        </div>
      </section>
      <p class="boundary">Experimental, uncalibrated source heuristic ({escaped(estimate.get('method', 'unknown method'))}).
      This is not measured cognitive load, gaze, comprehension, or an accessibility grade.
      A zero means only that these source checks found no flagged issue.</p>
      <div class="route" aria-label="Three reader questions">
        <section><span class="step">01 / ORIENT</span><h2>What is this about?</h2><p>Check that the page title and opening summary answer the reader's question.</p></section>
        <section><span class="step">02 / LOCATE</span><h2>Where is the answer?</h2><p>Use this source heading map as one entry point; inspect the rendered page too.</p></section>
        <section><span class="step">03 / UNDERSTAND</span><h2>What does it mean?</h2><p>Ask a reader to explain the answer and its caveats. This audit cannot measure that.</p></section>
      </div>
      {walkthrough}
      <div class="columns">
        <section><h2>Source heading map</h2>{heading_map(headings)}</section>
        <section><h2>Flagged issues</h2>{item_list(findings, 'No issue flagged by the source checklist.')}
          <h2>Suggested fixes</h2>{item_list(suggestions, 'No automatic suggestion for this source.', field='action')}</section>
      </div>
      <div class="columns final">
        <section><h2>Narrow strengths</h2>{item_list(strengths, 'No source strength recorded.')}</section>
        <section><h2>Checks still needed</h2>{item_list(next_checks, 'No next checks supplied.')}</section>
      </div>
      <footer>{escaped(report.get('limit', 'Source-only result.'))}</footer>
    </article>"""


def screenshot_uri(path: Path) -> str:
    data = path.read_bytes()
    if len(data) > 8_000_000:
        raise ValueError(f"Screenshot exceeds 8 MB: {path}")
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        media = "image/png"
    elif data.startswith(b"\xff\xd8\xff"):
        media = "image/jpeg"
    elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        media = "image/webp"
    else:
        raise ValueError(f"Expected a PNG, JPEG, or WebP screenshot: {path}")
    return f"data:{media};base64,{base64.b64encode(data).decode('ascii')}"


def walkthrough_html(walkthrough: dict[str, object], asset_dir: Path) -> str:
    frames = walkthrough.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError("Walkthrough needs a non-empty frames array")
    url = str(walkthrough.get("url", ""))
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Walkthrough URL must be HTTP(S)")
    task = escaped(walkthrough.get("reader_task", "Reader task not supplied"))
    basis = escaped(walkthrough.get("audit_basis", "Source audit"))
    rows = []
    for frame_number, frame in enumerate(frames, 1):
        if not isinstance(frame, dict):
            raise ValueError("Each frame must be an object")
        image_name = frame.get("image")
        if not isinstance(image_name, str) or not image_name:
            raise ValueError("Each frame needs an image path")
        image_path = (asset_dir / image_name).resolve()
        if not image_path.is_relative_to(asset_dir.resolve()):
            raise ValueError("Screenshot path must stay inside the walkthrough directory")
        uri = screenshot_uri(image_path)
        notes = frame.get("callouts", [])
        if not isinstance(notes, list):
            raise ValueError("Callouts must be an array")
        pins, rail = [], []
        for note_number, note in enumerate(notes, 1):
            if not isinstance(note, dict):
                raise ValueError("Each callout must be an object")
            x, y = note.get("x"), note.get("y")
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)) or not (0 <= x <= 1 and 0 <= y <= 1):
                raise ValueError("Callout x and y must be proportions from 0 to 1")
            kind = note.get("kind", "review")
            if kind not in {"strength", "review"}:
                raise ValueError("Callout kind must be strength or review")
            key = f"f{frame_number}-n{note_number}"
            label = escaped(note.get("title", f"Observation {note_number}"))
            pins.append(
                f"<a class='pin {kind}' href='#note-{key}' style='left:{x*100:.2f}%;top:{y*100:.2f}%' "
                f"aria-label='{label}, callout {note_number}'>{note_number}</a>"
            )
            def line(field: str, heading: str) -> str:
                value = note.get(field)
                return f"<p><b>{heading}</b> {escaped(value)}</p>" if value else ""
            rail.append(
                f"<li id='note-{key}' class='callout {kind}'><span class='callout-type'>{kind}</span>"
                f"<h4>{note_number}. {label}</h4>"
                + line("observed", "Observed:") + line("likely_effect", "Likely task effect:")
                + line("suggestion", "Suggestion:") + line("check", "Check:") + "</li>"
            )
        rows.append(
            f"<section class='walk-frame'><h3>{escaped(frame.get('label', f'Page view {frame_number}'))}</h3>"
            f"<div class='walk-row'><div class='shot'><img src='{uri}' alt='{escaped(frame.get('alt', 'Rendered page capture'))}'>"
            + "".join(pins) + "</div><ol class='margin'>" + "".join(rail) + "</ol></div></section>"
        )
    return (
        "<section class='walkthrough' aria-label='Rendered page walkthrough'>"
        f"<div class='walk-head'><p class='eyebrow'>RENDERED PAGE WALKTHROUGH</p><h2>{task}</h2>"
        f"<p><a href='{escaped(url)}'>{escaped(url)}</a> · {basis} · Callouts are review observations, not measured gaze.</p></div>"
        + "".join(rows) + "</section>"
    )


def render(payload: dict[str, object], walkthrough: dict[str, object] | None = None,
           asset_dir: Path | None = None) -> str:
    if payload.get("schema_version") != "1.1":
        raise ValueError("Expected S2C audit schema_version 1.1")
    reports = payload.get("reports")
    if not isinstance(reports, list) or not reports:
        raise ValueError("Expected a non-empty reports array")
    for report in reports:
        if not isinstance(report, dict):
            raise ValueError("Each report must be an object")
    walk = walkthrough_html(walkthrough, asset_dir or Path.cwd()) if walkthrough else ""
    body = report_html(reports[0], walk) + "\n" + "\n".join(report_html(report) for report in reports[1:])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>S2C source audit</title>
<style>
:root{{color-scheme:light;--ink:#17211b;--muted:#4b5d50;--line:#c9d6ca;--paper:#f7f7f2;--green:#0d6b4e;--soft:#e8f2e9}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.5 system-ui,sans-serif}}
main{{max-width:1100px;margin:auto;padding:clamp(1rem,3vw,2.5rem)}}.report{{margin-bottom:3rem}}
.eyebrow,.step{{color:var(--green);font-size:.78rem;font-weight:700;letter-spacing:.12em}}
h1{{font-size:clamp(1.8rem,4vw,3rem);overflow-wrap:anywhere;line-height:1.15;margin:.35rem 0}}
h2{{font-size:1.15rem;line-height:1.25;margin:0 0 .65rem}}p{{margin:.25rem 0 1rem}}.subtitle{{color:var(--muted)}}
.summary{{display:flex;gap:1.5rem;align-items:center;background:#fff;border:1px solid var(--line);padding:1.3rem;margin:1.7rem 0 .7rem}}
.score{{display:flex;align-items:baseline;white-space:nowrap}}.score strong{{font-size:3.5rem;line-height:1}}.score span{{color:var(--muted)}}
.score-context{{flex:1;min-width:0}}.score-context p{{margin:.45rem 0 0;color:var(--muted);font-size:.9rem}}
.track{{height:10px;background:#e3e9e2;overflow:hidden}}.track span{{display:block;height:100%;background:var(--green)}}
.boundary{{color:var(--muted);font-size:.91rem;max-width:85ch}}
.route,.columns{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem;margin:1.8rem 0}}
.route section{{border-top:3px solid var(--green);padding:1rem 0}}.route h2{{margin-top:.45rem}}.route p{{color:var(--muted)}}
.columns{{grid-template-columns:repeat(2,minmax(0,1fr))}}.columns section{{background:#fff;border:1px solid var(--line);padding:1.3rem;min-width:0}}
.columns h2:not(:first-child){{margin-top:1.5rem}}ul,.outline{{padding-left:1.4rem;margin:.4rem 0 0}}li{{margin:.5rem 0}}.outline{{list-style:none;padding-left:0}}
.outline li{{padding:.25rem 0;border-bottom:1px solid var(--line)}}.outline .h2{{padding-left:1rem}}.outline .h3{{padding-left:2rem}}.outline .h4{{padding-left:3rem}}.outline .h5{{padding-left:4rem}}.outline .h6{{padding-left:5rem}}
.code{{font:700 .8rem ui-monospace,monospace;color:var(--green)}}.empty,footer{{color:var(--muted)}}footer{{font-size:.85rem;border-top:1px solid var(--line);padding-top:1rem}}
.walkthrough{{margin:2.5rem 0}}.walk-head{{border-top:2px solid var(--ink);padding-top:1rem;margin-bottom:1.5rem}}.walk-head h2{{font-size:1.5rem;max-width:60ch}}.walk-head p:last-child{{color:var(--muted);font-size:.9rem}}
.walk-head a{{color:var(--green);overflow-wrap:anywhere}}.walk-frame{{margin:0 0 2.2rem}}.walk-frame h3{{font-size:1.08rem;margin:0 0 .7rem}}
.walk-row{{display:grid;grid-template-columns:minmax(0,1.9fr) minmax(260px,1fr);gap:1.2rem;align-items:start}}
.shot{{position:relative;min-width:0}}.shot img{{display:block;width:100%;height:auto;border:1px solid var(--line)}}
.pin{{position:absolute;transform:translate(-50%,-50%);display:grid;place-items:center;width:2rem;height:2rem;border-radius:50%;background:var(--ink);color:#fff;text-decoration:none;font-weight:700;box-shadow:0 0 0 3px #fff}}
.pin.strength{{background:var(--green)}}.pin:focus-visible{{outline:3px solid #e08d12;outline-offset:4px}}
.margin{{list-style:none;padding:0;margin:0;display:grid;gap:.8rem}}.callout{{border-left:4px solid #b06c00;padding:.3rem 0 .3rem .8rem;background:#fff}}
.callout.strength{{border-left-color:var(--green)}}.callout:target{{background:var(--soft)}}.callout-type{{text-transform:uppercase;letter-spacing:.1em;color:var(--muted);font-size:.7rem;font-weight:700}}
.callout h4{{margin:.15rem 0 .35rem;font-size:1rem}}.callout p{{font-size:.87rem;margin:.25rem 0;color:var(--muted)}}.callout b{{color:var(--ink)}}
@media(max-width:700px){{.route,.columns{{grid-template-columns:1fr}}.summary{{align-items:flex-start}}}}
@media(max-width:850px){{.walk-row{{grid-template-columns:1fr}}.margin{{grid-template-columns:1fr 1fr}}}}
@media(max-width:540px){{.margin{{grid-template-columns:1fr}}}}
@media(max-width:450px){{.summary{{display:block}}.score{{margin-bottom:.7rem}}.outline .h5,.outline .h6{{padding-left:3rem}}}}
</style></head><body><main>{body}</main></body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit_json", type=Path, help="JSON from s2c_audit.py --json")
    parser.add_argument("--output", required=True, type=Path, help="HTML report to write")
    parser.add_argument("--walkthrough", type=Path, help="Optional rendered-page capture and callout JSON")
    args = parser.parse_args()
    payload = json.loads(args.audit_json.read_text(encoding="utf-8"))
    walkthrough = json.loads(args.walkthrough.read_text(encoding="utf-8")) if args.walkthrough else None
    result = render(payload, walkthrough, args.walkthrough.parent if args.walkthrough else None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result, encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
