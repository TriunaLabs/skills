#!/usr/bin/env python3
"""Render an S2C source-audit JSON result as an inspectable HTML report."""

from __future__ import annotations

import argparse
import base64
from datetime import date
import html
import json
from pathlib import Path
import re
from statistics import median
from urllib.parse import urlsplit


def escaped(value: object) -> str:
    return html.escape(str(value), quote=True)


def audit_date(value: object) -> tuple[str, str]:
    """Return a machine-readable audit date and a readable label."""
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("audited_on must be a valid YYYY-MM-DD date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("audited_on must be a valid YYYY-MM-DD date") from exc
    return value, f"{parsed.strftime('%B')} {parsed.day}, {parsed.year}"


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


def report_html(report: dict[str, object], walkthrough: str = "", audited_on: object = None,
                signals: str = "", attention: str = "") -> str:
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
    if audited_on is None:
        date_line = "<p class='audit-date'><b>Audit date:</b> Not recorded</p>"
    else:
        iso_date, readable_date = audit_date(audited_on)
        date_line = f"<p class='audit-date'><b>Audit date:</b> <time datetime='{iso_date}'>{readable_date}</time></p>"
    return f"""
    <article class="report" aria-label="Audit for {escaped(report.get('source', 'unknown source'))}">
      <header>
        <p class="eyebrow">SCAN TO COMPREHEND / SOURCE PREFLIGHT</p>
        <h1>{escaped(report.get('source', 'Unknown source'))}</h1>
        {date_line}
        <p class="subtitle">A source check followed by questions for rendered and reader review.</p>
      </header>
      {attention}
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
      {signals}
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


def attention_html(result: dict[str, object], asset_dir: Path) -> str:
    if result.get("schema") != "s2c-attention/v1" or result.get("model_version") != "s2c-heuristic-attention-v1":
        raise ValueError("Expected S2C heuristic attention v1 result")
    frames = result.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError("Attention result needs frames")
    rows = []
    for index, frame in enumerate(frames, 1):
        if not isinstance(frame, dict):
            raise ValueError("Attention frame must be an object")
        paths = []
        for field in ("image", "overlay"):
            name = frame.get(field)
            if not isinstance(name, str) or not name:
                raise ValueError(f"Attention frame needs {field}")
            path = (asset_dir / name).resolve()
            if not path.is_relative_to(asset_dir.resolve()):
                raise ValueError("Attention image path must stay inside result directory")
            paths.append(path)
        cues = frame.get("cues", [])
        if not isinstance(cues, list):
            raise ValueError("Attention cues must be an array")
        cue_rows = []
        for cue in cues[:6]:
            if not isinstance(cue, dict):
                raise ValueError("Attention cue must be an object")
            cue_rows.append(
                f"<li><b>{escaped(cue.get('label') or cue.get('kind', 'Element'))}</b> "
                f"<span>{escaped(cue.get('kind', ''))} · relative rule weight {escaped(cue.get('weight', '?'))}</span></li>"
            )
        rows.append(
            f"<section class='attention-frame'><h3>{escaped(frame.get('label', f'View {index}'))}</h3>"
            + (f"<p class='attention-provenance'>Captured: {escaped(frame['captured_at'])}</p>" if frame.get("captured_at") else "")
            + f"<p class='attention-provenance'>Element basis: {escaped(frame.get('provenance', 'unspecified'))}</p>"
            f"<input class='heat-toggle' type='checkbox' id='heat-{index}' checked>"
            f"<label class='heat-label' for='heat-{index}'>Show estimated heatmap</label>"
            f"<div class='heat-view'><img src='{screenshot_uri(paths[0])}' alt='Audited page screenshot'>"
            f"<img class='heat-overlay' src='{screenshot_uri(paths[1])}' alt=''></div>"
            "<p class='heat-legend'>Relative intensity within this screenshot: "
            "<span class='legend-gradient' aria-hidden='true'></span> low → high. Colors are not probabilities.</p>"
            f"<h4>Highest rule weights</h4><ol class='attention-cues'>{''.join(cue_rows)}</ol></section>"
        )
    return (
        "<section class='attention' aria-label='Estimated visual attention'>"
        "<p class='eyebrow'>EXPERIMENTAL / ESTIMATED VISUAL ATTENTION</p>"
        "<h2>Heuristic attention baseline</h2>"
        "<p>Fixed editorial rules combine position, element area, text size, supplied color contrast, "
        "and element type. Gaussian spots are blended into a relative heatmap. Face cues require explicit annotation. "
        "This model has not been fitted to gaze data or validated on held-out fixations. "
        "It does not measure gaze, dwell, comprehension, or cognitive load.</p>"
        + "".join(rows) + "</section>"
    )


def wcag_spotcheck_html(result: dict[str, object]) -> str:
    """Keep deterministic contrast screening separate from predicted attention."""
    sections = []
    for frame in result.get("frames", []):
        spotcheck = frame.get("text_contrast_spotcheck")
        if spotcheck is None:
            continue  # Older attention results remain renderable.
        checks = spotcheck.get("checks")
        if not isinstance(checks, list):
            raise ValueError("Text contrast checks must be an array")
        rows = []
        for check in checks:
            if not isinstance(check, dict) or check.get("status") not in {
                    "below_threshold", "at_or_above_threshold", "needs_review"}:
                raise ValueError("Invalid text contrast check")
            status = {"below_threshold": "Below reference threshold",
                      "at_or_above_threshold": "At or above on supplied colors",
                      "needs_review": "Needs color or font review"}[check["status"]]
            ratio = check.get("ratio")
            threshold = check.get("threshold")
            rows.append(
                f"<tr><th scope='row'>{escaped(check.get('label') or check.get('id') or 'Text element')}</th>"
                f"<td>{escaped(f'{ratio:.2f}:1' if isinstance(ratio, (int, float)) else '—')}</td>"
                f"<td>{escaped(f'{threshold:g}:1' if isinstance(threshold, (int, float)) else '—')}</td>"
                f"<td>{escaped(status)}</td></tr>"
            )
        below = sum(check["status"] == "below_threshold" for check in checks)
        unknown = sum(check["status"] == "needs_review" for check in checks)
        sections.append(
            f"<section class='wcag-frame'><h3>{escaped(frame.get('label', 'Viewport'))}</h3>"
            f"<p><b>{below}</b> below the reference threshold · <b>{unknown}</b> need review "
            f"· {len(checks)} annotated text elements screened.</p>"
            f"<p class='attention-provenance'>Color basis: {escaped(spotcheck.get('color_basis', 'unspecified'))}. "
            "Ratios use supplied solid foreground and background colors; rounded display values were not used for comparisons.</p>"
            "<div class='wcag-scroll'><table class='wcag-table'><thead><tr><th scope='col'>Text element</th>"
            "<th scope='col'>Ratio</th><th scope='col'>Reference</th><th scope='col'>Screening result</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div></section>"
        )
    if not sections:
        return ""
    return (
        "<section class='wcag' aria-label='WCAG text contrast spot check'>"
        "<p class='eyebrow'>ACCESSIBILITY / TEXT CONTRAST SPOT CHECK</p>"
        "<h2>Can the highlighted text be read?</h2>"
        "<p>This screens annotated text against <a href='https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html'>"
        "WCAG 2.2 SC 1.4.3</a>: 4.5:1 for normal text and 3:1 for large text. "
        "It is separate from the estimated heatmap and structural friction score. A low-contrast element can "
        "receive less estimated attention under the current heuristic, but that gaze effect has not been validated.</p>"
        + "".join(sections)
        + "<p class='boundary'>These are screening results for visible annotated elements, not WCAG conformance. "
        "Confirm exact CSS colors, backgrounds, font size and weight, all responsive and interaction states. "
        "Check meaningful graphics and control indicators under <a href='https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html'>"
        "SC 1.4.11</a>, plus keyboard focus, labels, reading order, and alternatives manually.</p></section>"
    )


def walkthrough_html(walkthrough: dict[str, object], asset_dir: Path) -> str:
    audit_date(walkthrough.get("audited_on"))
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


def section_signals_html(samples: list[object]) -> str:
    """Summarize opt-in page observations without treating them as gaze or reading."""
    if not samples:
        raise ValueError("Provide at least one section signals export")
    groups: dict[str, list[dict[str, object]]] = {"Narrow (<768 px)": [], "Wide (768+ px)": []}
    labels = set()
    dates = set()
    for sample in samples:
        if not isinstance(sample, dict) or sample.get("schema") != "s2c-section-signals/v1":
            raise ValueError("Expected an S2C section signals v1 export")
        viewport = sample.get("viewport")
        sections = sample.get("sections")
        if (not isinstance(viewport, dict) or isinstance(viewport.get("width"), bool)
                or not isinstance(viewport.get("width"), (int, float)) or viewport["width"] <= 0):
            raise ValueError("Section signals need a valid viewport width")
        if not isinstance(sections, list) or not sections:
            raise ValueError("Section signals need a non-empty sections array")
        if not isinstance(sample.get("mouseSeen"), bool):
            raise ValueError("Section signals need mouseSeen")
        audit_date(sample.get("capturedOn"))
        dates.add(sample["capturedOn"])
        labels.add(str(sample.get("pageLabel", "")))
        seen = set()
        for section in sections:
            if (not isinstance(section, dict) or not isinstance(section.get("id"), str)
                    or not section["id"].strip() or section["id"] in seen):
                raise ValueError("Section signals need unique section IDs per export")
            seen.add(section["id"])
            for field in ("visibleMs", "hoverMs", "mouseClicks", "touchTaps"):
                value = section.get(field)
                if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value < 86_400_000:
                    raise ValueError(f"Invalid section signal: {field}")
            if (section["hoverMs"] > section["visibleMs"] or
                    (section["hoverMs"] > 0 and not sample["mouseSeen"])):
                raise ValueError("Hover time must be visible time from a mouse session")
            if not isinstance(section["mouseClicks"], int) or not isinstance(section["touchTaps"], int):
                raise ValueError("Pointer activation counts must be integers")
        group = "Narrow (<768 px)" if viewport["width"] < 768 else "Wide (768+ px)"
        groups[group].append(sample)
    if len(labels) != 1:
        raise ValueError("Section signals must share one pageLabel")
    if len(samples) > 1 and not next(iter(labels)):
        raise ValueError("Multiple section signals exports need a shared nonempty pageLabel")

    tables = []
    for name, members in groups.items():
        if not members:
            continue
        ids = sorted({section["id"] for sample in members for section in sample["sections"]})
        rows = []
        for section_id in ids:
            present = [next((section for section in sample["sections"] if section["id"] == section_id), None)
                       for sample in members]
            paired = [(sample, section) for sample, section in zip(members, present) if section is not None]
            exposed = [section["visibleMs"] for _, section in paired if section["visibleMs"] > 0]
            mouse = [section for sample, section in paired if sample["mouseSeen"]]
            reached = len(exposed)
            denominator = len(paired)
            reach_pct = 100 * reached / denominator
            median_seconds = f"{median(exposed) / 1000:.1f} s" if exposed else "—"
            hovered = sum(section["hoverMs"] > 0 for section in mouse)
            hover_display = f"{hovered}/{len(mouse)}" if mouse else "—"
            mouse_clicks = sum(section["mouseClicks"] for _, section in paired)
            touch_taps = sum(section["touchTaps"] for _, section in paired)
            rows.append(
                f"<tr><th scope='row'>{escaped(section_id)}</th>"
                f"<td>{reached}/{denominator}<span class='mini-track' aria-hidden='true'><i style='width:{reach_pct:.1f}%'></i></span></td>"
                f"<td>{median_seconds}</td><td>{hover_display}</td>"
                f"<td>{mouse_clicks}</td><td>{touch_taps}</td></tr>"
            )
        tables.append(
            f"<h3>{escaped(name)} · {len(members)} session export(s)</h3>"
            "<div class='signal-scroll'><table class='signal-table'><thead><tr>"
            "<th scope='col'>Section</th><th scope='col'>Viewport reach</th>"
            "<th scope='col'>Median visible time*</th><th scope='col'>Mouse hover sessions</th>"
            "<th scope='col'>Mouse clicks</th><th scope='col'>Touch taps</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
        )
    span = min(dates) if len(dates) == 1 else f"{min(dates)} to {max(dates)}"
    return (
        "<section class='signals' aria-label='Observed section behavior'>"
        "<p class='eyebrow'>OPT-IN PAGE OBSERVATIONS</p><h2>Which sections entered the viewport?</h2>"
        f"<p><b>Page label:</b> {escaped(next(iter(labels)) or 'Unlabeled')} · <b>Captured:</b> {escaped(span)}. "
        "Session exports are not unique visitors. *Median visible time uses reached sessions only.</p>"
        + "".join(tables)
        + "<p class='boundary'>Visible time means foreground viewport exposure while the page was recently active. "
        "Hover and clicks are separate pointer signals. None measures gaze, reading, understanding, or cognitive load. "
        "Compare the same section IDs and reader task across versions before drawing a design conclusion.</p></section>"
    )


def render(payload: dict[str, object], walkthrough: dict[str, object] | None = None,
           asset_dir: Path | None = None, signal_samples: list[object] | None = None,
           attention: dict[str, object] | None = None,
           attention_dir: Path | None = None) -> str:
    if payload.get("schema_version") != "1.1":
        raise ValueError("Expected S2C audit schema_version 1.1")
    reports = payload.get("reports")
    if not isinstance(reports, list) or not reports:
        raise ValueError("Expected a non-empty reports array")
    for report in reports:
        if not isinstance(report, dict):
            raise ValueError("Each report must be an object")
    walk = walkthrough_html(walkthrough, asset_dir or Path.cwd()) if walkthrough else ""
    signals = section_signals_html(signal_samples) if signal_samples is not None else ""
    heat = (attention_html(attention, attention_dir or Path.cwd()) + wcag_spotcheck_html(attention)
            if attention else "")
    dated = walkthrough.get("audited_on") if walkthrough else payload.get("audited_on")
    if walkthrough and payload.get("audited_on") and payload["audited_on"] != dated:
        raise ValueError("Audit JSON and walkthrough dates do not match")
    body = report_html(reports[0], walk, dated, signals, heat) + "\n" + "\n".join(report_html(report, audited_on=dated) for report in reports[1:])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{'S2C visual attention baseline' if attention else 'S2C source audit'}</title>
<style>
:root{{color-scheme:light;--ink:#17211b;--muted:#4b5d50;--line:#c9d6ca;--paper:#f7f7f2;--green:#0d6b4e;--soft:#e8f2e9}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.5 system-ui,sans-serif}}
main{{max-width:1100px;margin:auto;padding:clamp(1rem,3vw,2.5rem)}}.report{{margin-bottom:3rem}}
.eyebrow,.step{{color:var(--green);font-size:.78rem;font-weight:700;letter-spacing:.12em}}
h1{{font-size:clamp(1.8rem,4vw,3rem);overflow-wrap:anywhere;line-height:1.15;margin:.35rem 0}}
h2{{font-size:1.15rem;line-height:1.25;margin:0 0 .65rem}}p{{margin:.25rem 0 1rem}}.subtitle{{color:var(--muted)}}
.audit-date{{display:inline-block;background:var(--soft);border-left:3px solid var(--green);padding:.45rem .7rem;margin:.45rem 0 .7rem;font-size:.93rem}}
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
.attention{{margin:2.5rem 0;padding:1.4rem;background:#fff;border:1px solid var(--line)}}
.attention>h2{{font-size:1.55rem}}.attention>p{{max-width:85ch}}
.attention-frame{{border-top:1px solid var(--line);padding:1.3rem 0}}.attention-frame h3{{font-size:1.1rem;margin:0 0 .25rem}}
.attention-provenance,.heat-legend{{font-size:.87rem;color:var(--muted)}}
.heat-toggle{{accent-color:var(--green);margin:.2rem .3rem .8rem 0}}.heat-label{{font-weight:700;cursor:pointer}}
.heat-view{{position:relative;max-width:850px}}.heat-view img{{display:block;width:100%;height:auto;border:1px solid var(--line)}}
.heat-view .heat-overlay{{position:absolute;inset:0;border:0}}.heat-toggle:not(:checked)~.heat-view .heat-overlay{{display:none}}
.legend-gradient{{display:inline-block;width:7rem;height:.7rem;vertical-align:middle;background:linear-gradient(90deg,#165ccd,#00c1da,#ffe137,#e42723)}}
.attention-cues{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.15rem 1rem;padding-left:1.4rem;max-width:850px}}
.attention-cues li span{{display:block;font-size:.83rem;color:var(--muted)}}
.wcag{{margin:2.5rem 0;padding:1.4rem;background:#fff;border:1px solid var(--line)}}
.wcag>h2{{font-size:1.55rem}}.wcag>p{{max-width:85ch}}.wcag a{{color:var(--green)}}
.wcag-frame{{border-top:1px solid var(--line);padding:1.2rem 0}}.wcag-frame h3{{margin:0 0 .3rem;font-size:1.1rem}}
.wcag-scroll{{overflow-x:auto}}.wcag-table{{width:100%;min-width:610px;border-collapse:collapse;text-align:left}}
.wcag-table th,.wcag-table td{{padding:.55rem .7rem;border-bottom:1px solid var(--line);vertical-align:top}}
.signals{{margin:2.5rem 0;padding:1.4rem;background:#fff;border:1px solid var(--line)}}.signals h2{{font-size:1.5rem}}
.signals h3{{font-size:1rem;margin:1.5rem 0 .6rem}}.signal-scroll{{overflow-x:auto}}
.signal-table{{width:100%;min-width:720px;border-collapse:collapse;text-align:left}}
.signal-table th,.signal-table td{{padding:.7rem;border-bottom:1px solid var(--line);vertical-align:top}}
.signal-table th{{font-weight:700}}.mini-track{{display:block;width:100%;height:5px;background:#e3e9e2;margin-top:.35rem}}
.mini-track i{{display:block;height:100%;background:var(--green)}}
@media(max-width:700px){{.route,.columns{{grid-template-columns:1fr}}.summary{{align-items:flex-start}}}}
@media(max-width:850px){{.walk-row{{grid-template-columns:1fr}}.margin{{grid-template-columns:1fr 1fr}}}}
@media(max-width:540px){{.margin{{grid-template-columns:1fr}}}}
@media(max-width:700px){{.attention-cues{{grid-template-columns:1fr}}}}
@media(max-width:450px){{.summary{{display:block}}.score{{margin-bottom:.7rem}}.outline .h5,.outline .h6{{padding-left:3rem}}}}
</style></head><body><main>{body}</main></body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit_json", type=Path, help="JSON from s2c_audit.py --json")
    parser.add_argument("--output", required=True, type=Path, help="HTML report to write")
    parser.add_argument("--walkthrough", type=Path, help="Optional rendered-page capture and callout JSON")
    parser.add_argument("--signals", nargs="+", type=Path, help="Optional opt-in section signals session exports")
    parser.add_argument("--attention", type=Path, help="Optional S2C heuristic attention result JSON")
    args = parser.parse_args()
    payload = json.loads(args.audit_json.read_text(encoding="utf-8"))
    walkthrough = json.loads(args.walkthrough.read_text(encoding="utf-8")) if args.walkthrough else None
    signal_samples = [json.loads(path.read_text(encoding="utf-8")) for path in args.signals] if args.signals else None
    attention = json.loads(args.attention.read_text(encoding="utf-8")) if args.attention else None
    result = render(payload, walkthrough, args.walkthrough.parent if args.walkthrough else None,
                    signal_samples, attention, args.attention.parent if args.attention else None)
    result = "\n".join(line.rstrip() for line in result.splitlines()) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result, encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
