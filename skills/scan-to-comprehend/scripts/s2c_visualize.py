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

import s2c_browser_rubric
import s2c_scoring_profile


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


def site_basics_html(result: dict) -> str:
    if result.get("schema") != "s2c-site-basics/v1":
        raise ValueError("Expected s2c-site-basics/v1")
    performance = result.get("performance") or []
    performance_rows = []
    for item in performance:
        def timing(key: str) -> str:
            value = item.get(key)
            return f"{escaped(value)} ms" if isinstance(value, (int, float)) and not isinstance(value, bool) else "not captured"
        performance_rows.append(
            f"<tr><th scope='row'>{escaped(item.get('viewport', 'viewport'))}</th>"
            f"<td>{timing('ttfb_ms')}</td><td>{timing('dom_content_loaded_ms')}</td>"
            f"<td>{timing('load_event_ms')}</td><td>{escaped(item.get('resource_count', '—'))}</td></tr>")
    checks = "".join(
        f"<li class='basic-check {escaped(item.get('status', 'review'))}'><strong>{escaped(item.get('label', 'Check'))}</strong>"
        f"<span>{escaped(item.get('status', 'review'))}</span><p>{escaped(item.get('detail', ''))}</p>"
        + (f"<p class='next'>Next: {escaped(item.get('action', 'Review this result.'))}</p>"
           if item.get("status") != "found" else "") + "</li>"
        for item in result.get("checks", []))
    links = "".join(
        f"<tr><td>{escaped(item.get('url', ''))}</td><td>{escaped(item.get('status') if item.get('status') is not None else '—')}</td>"
        f"<td>{escaped(item.get('result', 'inconclusive'))}</td></tr>"
        for item in result.get("link_probes", []))
    fragments = "".join(
        f"<li>{escaped(item.get('label') or item.get('href', 'fragment'))}: {escaped(item.get('result', 'not_checked'))}</li>"
        for item in result.get("fragment_checks", []) if item.get("result") == "broken_fragment")
    summary = result.get("link_summary") or {}
    boundary = ("Uploaded HTML is rendered with scripts disabled and external requests blocked. "
                "Network timing and live link status are unavailable. Contact and policy links are markup discovery only."
                if result.get("source_kind") == "html" else
                "One captured page. Timings are synthetic navigation observations from this audit environment, "
                "not field Core Web Vitals. Missing contact or legal links are discovery review items, "
                "not proof those pages do not exist.")
    return (
        "<section class='site-basics' id='site-basics'><p class='eyebrow'>PAGE BASICS / SEPARATE FROM S2C SCORING</p>"
        "<h2>Performance, links, and public information</h2>"
        f"<p class='boundary'>{escaped(boundary)}</p>"
        "<h3>Navigation signals</h3><div class='basic-scroll'><table><thead><tr><th>Viewport</th><th>Response wait</th>"
        "<th>DOM ready</th><th>Load event</th><th>Resources seen</th></tr></thead><tbody>"
        + "".join(performance_rows) + "</tbody></table></div>"
        "<p class='basic-note'>Response wait uses responseStart − requestStart. Resource counts are entries observed by this browser, "
        "not total page weight; cross-origin transfer sizes may be unavailable.</p>"
        "<h3>Contact and policy discovery</h3><ul class='basic-checks'>" + checks + "</ul>"
        f"<h3>Link sample</h3><p>{escaped(summary.get('sampled', 0))} same-origin URL(s) checked with HEAD; "
        f"{escaped(summary.get('possible_broken', 0))} possible 404/410 link(s); "
        f"{escaped(summary.get('broken_fragments', 0))} broken in-page fragment(s). "
        "Redirects and blocked HEAD requests are inconclusive; external links and unselected links were not checked.</p>"
        + ("<div class='basic-scroll'><table><thead><tr><th>URL</th><th>HTTP</th><th>Result</th></tr></thead><tbody>"
           + links + "</tbody></table></div>" if links else "<p>No HTTP links probed in this run.</p>")
        + ("<ul>" + fragments + "</ul>" if fragments else "")
        + "</section>")


def robot_visibility_html(result: dict) -> str:
    if result.get("schema") != "s2c-robot-visibility/v1":
        raise ValueError("Expected s2c-robot-visibility/v1")
    rows = "".join(
        f"<tr><th scope='row'>{escaped(item.get('phrase', ''))}</th>"
        f"<td>{'yes' if item.get('source') else 'no'}</td><td>{'yes' if item.get('rendered') else 'no'}</td>"
        f"<td>{escaped(item.get('status', ''))}</td></tr>" for item in result.get("phrases", []))
    checks = "".join(
        f"<li class='robot-check {escaped(item.get('status', 'review'))}'><strong>{escaped(item.get('title', 'Check'))}</strong>"
        f"<p>{escaped(item.get('evidence', ''))}</p><p><b>Suggested action:</b> {escaped(item.get('action', ''))}</p></li>"
        for item in result.get("checks", []))
    return ("<section class='robot-visibility' id='robot-visibility'><p class='eyebrow'>ROBOT VISIBILITY / RAW VS RENDERED</p>"
            "<h2>Can a crawler find the important information?</h2>"
            "<p class='boundary'>This compares the initial HTML with one Chromium capture before clicks or scrolling. "
            "Google can render JavaScript; a rendered-only result is a dependency to verify, not proof of invisibility.</p>"
            f"<p>Watch list: {escaped(result.get('important_basis', 'first visible headings'))}. "
            f"robots.txt: {escaped(result.get('robots_txt_status', 'not checked'))}.</p>"
            + ("<ul class='robot-checks'>" + checks + "</ul>" if checks else "<p>No visibility risk flagged by these limited checks.</p>")
            + ("<div class='basic-scroll'><table><thead><tr><th>Watched phrase</th><th>Initial HTML</th>"
               "<th>Rendered DOM</th><th>Result</th></tr></thead><tbody>" + rows + "</tbody></table></div>" if rows else "")
            + ("<p><b>Rendered-only links:</b> " + ", ".join(escaped(link) for link in result.get("rendered_only_links", [])[:8]) + "</p>"
               if result.get("rendered_only_links") else "")
            + ("<p><b>Potentially blocked CSS/JS:</b> " + ", ".join(escaped(link) for link in result.get("blocked_assets", [])[:8]) + "</p>"
               if result.get("blocked_assets") else "")
            + "<p class='basic-note'>Crawler-specific confirmation belongs in the target search engine's URL Inspection tool. "
            "This screen does not establish indexing or search ranking.</p></section>")


def collect_actions(report: dict, rubric: dict | None, basics: dict | None, robot: dict | None) -> list[tuple[str, str, str, str]]:
    actions = []
    if rubric:
        for rule in rubric.get("rules", []):
            if rule.get("status") in ("warning", "review"):
                actions.append((rule["status"], rule.get("title", "Browser rule"),
                                "; ".join(str(value) for value in rule.get("evidence", [])[:2]),
                                rule.get("suggestion", "Inspect the captured page.")))
    suggestions = {item.get("code"): item.get("action") for item in report.get("suggestions", [])}
    for finding in report.get("findings", []):
        code = finding.get("code", "")
        actions.append((finding.get("level", "review"), code.replace("_", " ").title(),
                        finding.get("message", ""), suggestions.get(code) or "Inspect the source finding."))
    if basics:
        for check in basics.get("checks", []):
            if check.get("status") == "review":
                actions.append(("review", check.get("label", "Page information"),
                                check.get("detail", ""), check.get("action", "Inspect the site.")))
        for check in basics.get("link_probes", []):
            if check.get("result") == "possible_broken":
                actions.append(("review", "Possible broken page link", check.get("url", ""),
                                "Confirm this 404/410 with a normal browser visit, then repair the destination or link."))
        for check in basics.get("fragment_checks", []):
            if check.get("result") == "broken_fragment":
                actions.append(("warning", "Broken in-page destination", check.get("href", ""),
                                "Update the fragment target or add the matching element ID."))
    if robot:
        for check in robot.get("checks", []):
            if check.get("status") in ("warning", "review"):
                actions.append((check["status"], check.get("title", "Robot visibility"),
                                check.get("evidence", ""), check.get("action", "Verify crawler access.")))
    return actions


def priority_actions_html(actions: list[tuple[str, str, str, str]]) -> str:
    if not actions:
        return ""
    cards = "".join(
        f"<li><span class='action-kind {escaped(kind)}'>{escaped(kind)}</span><h3>{escaped(title)}</h3>"
        f"<p>{escaped(evidence)}</p><p class='action-next'><b>Suggested action</b> {escaped(next_step)}</p></li>"
        for kind, title, evidence, next_step in actions[:8])
    return ("<section class='priority-actions' id='actions'><p class='eyebrow'>PRIORITY ACTIONS / EVIDENCE FIRST</p>"
            "<h2>What deserves attention</h2><p>Review these captured signals before changing the page. "
            "A missing link on this page is a discovery gap, not a sitewide finding.</p><ol>" + cards + "</ol></section>")


def action_plan_html(actions: list[tuple[str, str, str, str]]) -> str:
    rows = "".join(
        f"<li><span class='action-kind {escaped(kind)}'>{escaped(kind)}</span><div><h3>{escaped(title)}</h3>"
        f"<p><b>Evidence:</b> {escaped(evidence)}</p><p><b>Do:</b> {escaped(next_step)}</p></div></li>"
        for kind, title, evidence, next_step in actions)
    return ("<section class='action-plan' id='action-plan'><p class='eyebrow'>FINAL PAGE / ACTION PLAN</p>"
            "<h2>Fix, then verify</h2><p>Use this list for triage. Re-run the same rule version and viewport after a change; "
            "confirm effects with the appropriate browser, crawler tool, or reader task.</p>"
            + ("<ol>" + rows + "</ol>" if rows else "<p>No automatic action was flagged. Check the intended reader task with people.</p>")
            + "</section>")


def report_html(report: dict[str, object], walkthrough: str = "", audited_on: object = None,
                signals: str = "", attention: str = "", assistive: str = "", rubric: str = "",
                rubric_teaser: str = "", reader_views: str = "", contrast: str = "",
                scoring_profile: str = "", site_basics: str = "", priority_actions: str = "",
                robot_visibility: str = "", action_plan: str = "") -> str:
    visual_audit = bool(walkthrough or attention or assistive or rubric or reader_views or site_basics or robot_visibility)
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
    links = []
    if priority_actions:
        links.append("<a href='#actions'>Priority actions</a>")
    if walkthrough:
        links.append("<a href='#walkthrough'>Reviewer walkthrough</a>")
    if attention:
        links.append("<a href='#attention'>Attention</a>")
    if assistive:
        links.append("<a href='#assistive'>Reading and Tab paths</a>")
    if reader_views:
        links.extend(("<a href='#crawler'>Crawler</a>", "<a href='#retrieval'>Retrieval</a>", "<a href='#gap'>Gaps</a>"))
    if contrast:
        links.append("<a href='#contrast'>Contrast</a>")
    if rubric:
        links.append("<a href='#rubric'>Deterministic checklist</a>")
    if scoring_profile:
        links.append("<a href='#scoring-profile'>Scoring profile</a>")
    if site_basics:
        links.append("<a href='#site-basics'>Page basics</a>")
    if robot_visibility:
        links.append("<a href='#robot-visibility'>Robot visibility</a>")
    if action_plan:
        links.append("<a href='#action-plan'>Action plan</a>")
    nav = f"<nav class='report-nav' aria-label='Report sections'>{' · '.join(links)}</nav>" if links else ""
    return f"""
    <article class="report" aria-label="Audit for {escaped(report.get('source', 'unknown source'))}">
      <header id="overview">
        <p class="eyebrow">SCAN TO COMPREHEND / {'VISUAL AUDIT' if visual_audit else 'SOURCE PREFLIGHT'}</p>
        <h1>{escaped(report.get('source', 'Unknown source'))}</h1>
        {date_line}
        <p class="subtitle">{'Captured page evidence, browser checks, and source structure.' if visual_audit else 'A source check followed by questions for rendered and reader review.'}</p>
        {nav}
      </header>
      {rubric_teaser}
      {priority_actions}
      {walkthrough}
      {rubric}
      {scoring_profile}
      {site_basics}
      {robot_visibility}
      <section class="summary" id="summary" aria-label="Source-only structural friction estimate">
        <div class="score"><strong>{escaped(score)}</strong><span>/ 100</span></div>
        <div class="score-context">
          <h2>Source-only structural friction risk index</h2>
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
      {attention}
      {assistive}
      {reader_views}
      {contrast}
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
      {action_plan}
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
        "<section class='attention' id='attention' aria-label='Estimated visual attention'>"
        "<p class='eyebrow'>EXPERIMENTAL / ESTIMATED VISUAL ATTENTION</p>"
        "<h2>Heuristic attention baseline</h2>"
        "<p>Fixed editorial rules combine position, element area, text size, supplied color contrast, "
        "and element type. Gaussian spots are blended into a relative heatmap. Face cues require explicit annotation. "
        "The rules were not fitted to gaze data. A held-out UEyes webpage test found 0.506 NSS at 3 seconds "
        "versus 1.148 for a Train-fitted position map; this version does not beat that simple baseline. "
        "It does not measure gaze, dwell, comprehension, or cognitive load.</p>"
        + "".join(rows) + "</section>"
    )


def assistive_html(result: dict[str, object], asset_dir: Path) -> str:
    if result.get("schema") != "s2c-assistive-v1":
        raise ValueError("Expected s2c-assistive-v1")
    frames = result.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError("Assistive result needs frames")

    def plotted_steps(steps: list[dict]) -> list[dict]:
        return [step for step in steps if step.get("in_viewport") and isinstance(step.get("box"), dict)][:20]

    def path_svg(steps: list[dict], viewport: dict, color: str, css_class: str) -> str:
        width, height = int(viewport["width"]), int(viewport["height"])
        points = []
        circles = []
        for marker, step in enumerate(plotted_steps(steps), 1):
            box = step["box"]
            x = max(0, min(width, float(box["x"]) + float(box["width"]) / 2))
            y = max(0, min(height, float(box["y"]) + float(box["height"]) / 2))
            points.append(f"{x:.1f},{y:.1f}")
            opacity = ".48" if marker > 10 else "1"
            circles.append(f"<g opacity='{opacity}'><circle cx='{x:.1f}' cy='{y:.1f}' r='12' fill='{color}' stroke='white' stroke-width='2'/>"
                           f"<text x='{x:.1f}' y='{y + 4:.1f}' text-anchor='middle' fill='white' font-size='11' font-weight='700'>{marker}</text></g>")
        line = f"<polyline points='{' '.join(points[:10])}' fill='none' stroke='{color}' stroke-width='3' stroke-opacity='.85'/>" if len(points) > 1 else ""
        if len(points) > 10:
            line += f"<polyline points='{' '.join(points[9:])}' fill='none' stroke='{color}' stroke-width='2' stroke-opacity='.35'/>"
        return f"<svg class='{css_class}' viewBox='0 0 {width} {height}' aria-hidden='true'>{line}{''.join(circles)}</svg>"

    blocks = []
    for frame in frames:
        image_name = frame.get("image")
        if not isinstance(image_name, str) or not image_name:
            raise ValueError("Assistive frame needs image")
        image_path = (asset_dir / image_name).resolve()
        if not image_path.is_relative_to(asset_dir.resolve()):
            raise ValueError("Assistive image path must stay inside result directory")
        viewport = frame["viewport"]
        reading = frame.get("reading_path", [])
        focus = frame.get("focus_path", [])
        if not isinstance(reading, list) or not isinstance(focus, list):
            raise ValueError("Assistive paths must be arrays")
        first_heading = frame.get("first_heading_step")
        heading_note = f"First heading: reading step {first_heading}." if first_heading else "No heading in the captured AX path."
        action = frame.get("first_action_step")
        action_note = f"First named action: reading step {action}." if action else "No named action in the captured AX path."
        reading_rows = "".join(f"<li><b>{escaped(step['role'])}</b> — {escaped(step['name'])}</li>" for step in reading[:30])
        focus_rows = "".join(f"<li><b>{escaped(step['tag'])}</b> — {escaped(step.get('label') or '(no captured label)')}</li>" for step in focus[:30])
        reading_markers = "".join(
            f"<li>Marker {marker} → reading step {escaped(step['index'])}: <b>{escaped(step['role'])}</b> — {escaped(step['name'])}</li>"
            for marker, step in enumerate(plotted_steps(reading), 1))
        focus_markers = "".join(
            f"<li>Marker {marker} → Tab step {escaped(step['index'])}: <b>{escaped(step['tag'])}</b> — {escaped(step.get('label') or '(no captured label)')}</li>"
            for marker, step in enumerate(plotted_steps(focus), 1))
        findings = frame.get("findings", [])
        finding_rows = item_list(findings[:20], "No automatic review candidate in this capture.")
        blocks.append(
            f"<section class='assistive-frame'><h3>{escaped(frame['id'])} · {escaped(viewport['width'])} × {escaped(viewport['height'])} CSS px</h3>"
            f"<p class='attention-provenance'>Captured {escaped(frame['captured_at'])} (UTC). {escaped(heading_note)} {escaped(action_note)} "
            f"Keyboard steps recorded: {len(focus)}; traversal stopped at {escaped(frame.get('focus_stop', 'unknown'))}. "
            f"Document width {escaped(frame['document_width'])} px.</p>"
            f"<input type='checkbox' class='assistive-toggle reading-toggle' id='reading-{escaped(frame['id'])}' checked>"
            f"<label for='reading-{escaped(frame['id'])}'>Show AX reading path</label> "
            f"<input type='checkbox' class='assistive-toggle focus-toggle' id='focus-{escaped(frame['id'])}'>"
            f"<label for='focus-{escaped(frame['id'])}'>Show Tab path</label>"
            f"<div class='assistive-view' style='max-width:min(100%,{int(viewport['width'])}px)'><img src='{screenshot_uri(image_path)}' alt='Audited {escaped(frame['id'])} screenshot'>"
            f"{path_svg(reading, viewport, '#0d6b4e', 'reading-path')}"
            f"{path_svg(focus, viewport, '#9b4d06', 'focus-path')}</div>"
            f"<div class='assistive-columns'><details open><summary>Visible marker key · reading</summary><ol class='marker-key'>{reading_markers}</ol></details>"
            f"<details><summary>Visible marker key · Tab</summary><ol class='marker-key'>{focus_markers}</ol></details>"
            f"<details><summary>Full reading order · first 30 of {len(reading)}</summary><ol>{reading_rows}</ol></details>"
            f"<details><summary>Full keyboard order · first 30 of {len(focus)}</summary><ol>{focus_rows}</ol></details>"
            f"<div><h4>Review candidates · {len(findings)}</h4>{finding_rows}</div></div></section>"
        )
    return ("<section class='assistive' id='assistive' aria-label='Assistive reading view'>"
            "<p class='eyebrow'>CHROMIUM / ASSISTIVE READING VIEW</p><h2>Reading and keyboard paths</h2>"
            f"<p>{escaped(result.get('basis', 'Chromium capture'))}. {escaped(result.get('limit', ''))} "
            "Screenshot markers count only mapped, visible elements from 1 in each viewport; the marker key maps them back to full reading or Tab steps. "
            "The full order lists may contain offscreen or unboxed AX nodes, including parent and child text, so their step numbers can differ. "
            "Markers after 10 are faint. Lines show neither eye movement nor speech timing.</p>"
            + "".join(blocks) + "</section>")


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
        "<section class='wcag' id='contrast' aria-label='WCAG text contrast spot check'>"
        "<p class='eyebrow'>ACCESSIBILITY / TEXT CONTRAST SPOT CHECK</p>"
        "<h2>Can the highlighted text be read?</h2>"
        "<p>This screens annotated text against <a href='https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html'>"
        "WCAG 2.2 SC 1.4.3</a>: 4.5:1 for normal text and 3:1 for large text. "
        "It is separate from the estimated heatmap and structural friction score. A low-contrast element can "
        "receive less estimated attention under the current heuristic; a held-out test did not establish a benefit from its pixel-contrast proxy.</p>"
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
    actions = []
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
            priority = note.get("priority")
            evidence_level = note.get("evidence_level")
            if priority is not None and priority not in {"P1", "P2", "P3"}:
                raise ValueError("Callout priority must be P1, P2, or P3")
            if evidence_level is not None and evidence_level not in {"observed", "hypothesis"}:
                raise ValueError("Callout evidence_level must be observed or hypothesis")
            key = f"f{frame_number}-n{note_number}"
            label = escaped(note.get("title", f"Observation {note_number}"))
            pins.append(
                f"<a class='pin {kind}' href='#note-{key}' style='left:{x*100:.2f}%;top:{y*100:.2f}%' "
                f"aria-label='{label}, callout {note_number}'>{note_number}</a>"
            )
            def line(field: str, heading: str) -> str:
                value = note.get(field)
                return f"<p><b>{heading}</b> {escaped(value)}</p>" if value else ""
            if kind == "review":
                actions.append(({"P1": 1, "P2": 2, "P3": 3}.get(priority, 4),
                                f"<li><span class='priority'>{escaped(priority or 'Review')}</span> "
                                f"<a href='#note-{key}'>{label}</a>"
                                f"<span class='evidence-level'>{escaped(evidence_level or 'review judgment')}</span>"
                                f"<p><b>Suggested action:</b> {escaped(note.get('suggestion') or 'Inspect this finding.')}</p></li>"))
            rail.append(
                f"<li id='note-{key}' class='callout {kind}'><span class='callout-type'>{kind}</span>"
                + (f" <span class='priority'>{escaped(priority)}</span>" if priority else "")
                + (f" <span class='evidence-level'>{escaped(evidence_level)}</span>" if evidence_level else "")
                + f"<h4>{note_number}. {label}</h4>"
                + line("observed", "Observed:") + line("likely_effect", "Likely task effect:")
                + (f"<p class='suggestion'><b>Suggested action:</b> {escaped(note['suggestion'])}</p>" if note.get("suggestion") else "")
                + line("check", "Check:") + "</li>"
            )
        rows.append(
            f"<section class='walk-frame'><h3>{escaped(frame.get('label', f'Page view {frame_number}'))}</h3>"
            f"<div class='walk-row'><div class='shot'><img src='{uri}' alt='{escaped(frame.get('alt', 'Rendered page capture'))}'>"
            + "".join(pins) + "</div><ol class='margin'>" + "".join(rail) + "</ol></div></section>"
        )
    action_board = ("<section class='action-board' aria-label='Prioritized actions'>"
                    f"<h3>Action queue · {len(actions)} review items</h3>"
                    "<p>Priorities are reviewer judgments; observed evidence and untested effects stay distinct in each callout.</p>"
                    "<ol>" + "".join(item for _, item in sorted(actions, key=lambda row: row[0])) + "</ol></section>") if actions else ""
    return (
        "<section class='walkthrough' id='walkthrough' aria-label='Rendered page walkthrough'>"
        f"<div class='walk-head'><p class='eyebrow'>RENDERED PAGE WALKTHROUGH</p><h2>{task}</h2>"
        f"<p><a href='{escaped(url)}'>{escaped(url)}</a> · {basis} · Callouts are review observations, not measured gaze.</p></div>"
        + action_board
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


def browser_rubric_html(result: dict[str, object]) -> str:
    if result.get("schema") != "s2c-browser-rubric/v1":
        raise ValueError("Expected s2c-browser-rubric/v1")
    score = result.get("score", {})
    rules = result.get("rules")
    if not isinstance(score, dict) or not isinstance(rules, list):
        raise ValueError("Browser rubric needs score and rules")
    rows = []
    for rule in rules:
        if not isinstance(rule, dict) or rule.get("status") not in {"pass", "warning", "review", "not_checked"}:
            raise ValueError("Invalid browser rubric rule")
        status = rule["status"]
        evidence = item_list(rule.get("evidence", [])[:5], "No evidence supplied.")
        points = (f"{escaped(rule.get('earned', 0))}/{escaped(rule.get('weight', 0))} points"
                  if status in {"pass", "warning"} else f"{escaped(rule.get('weight', 0))} points held out")
        rows.append(
            f"<li class='rubric-rule {status}'><div class='rubric-rule-head'><span class='rubric-status'>{escaped(status.replace('_', ' '))}</span>"
            f"<h3>{escaped(rule.get('title', rule.get('id', 'Check')))}</h3>"
            f"<strong>{points}</strong></div>"
            f"{evidence}<p class='rubric-next'><b>Next action:</b> {escaped(rule.get('suggestion', 'Review this check.'))}</p></li>"
        )
    return (
        "<section class='browser-rubric' id='rubric' aria-label='Deterministic browser checklist'>"
        "<p class='eyebrow'>REPEATABLE CHECKS / EDITABLE RUBRIC</p><h2>What did the browser rules flag?</h2>"
        f"<div class='rubric-summary'><strong>{escaped(score.get('earned', 0))}<span>/{escaped(score.get('assessed', 0))}</span></strong>"
        f"<p>screened points confirmed · {escaped(score.get('percent_of_assessed', '—'))}% of assessed weight. "
        f"{escaped(result.get('counts', {}).get('warning', 0))} warning(s), "
        f"{escaped(result.get('counts', {}).get('review', 0))} review item(s), "
        f"{escaped(result.get('counts', {}).get('not_checked', 0))} not checked.</p></div>"
        f"<p class='boundary'>{escaped(result.get('limit', ''))} Rubric version {escaped(result.get('rubric_version', 'unknown'))}; "
        "weights are editable in browser-rubric.json and the same capture can be rescored. Compare pages only with the same rule version, task and capture scope.</p>"
        "<ol class='rubric-rules'>" + "".join(rows) + "</ol></section>"
    )


def scoring_profile_html(profile: dict) -> str:
    profile = s2c_scoring_profile.validate(profile)
    browser = "".join(f"<tr><th scope='row'>{escaped(s2c_browser_rubric.RULES[key])}</th><td>{value} points</td></tr>"
                      for key, value in profile["browser_weights"].items())
    crawler = "".join(f"<tr><th scope='row'>{escaped(s2c_scoring_profile.CRAWLER_LABELS[key])}</th><td>{escaped(value)}</td></tr>"
                      for key, value in profile["crawler_weights"].items())
    retrieval = profile["retrieval"]
    return ("<section class='scoring-profile' id='scoring-profile'><p class='eyebrow'>SCORING PROFILE / "
            f"{escaped(profile['schema'])}</p><h2>How this report was weighted</h2>"
            f"<p>Profile fingerprint: <code>{s2c_scoring_profile.fingerprint(profile)}</code>. Browser points sum to 100; "
            "review and not-checked rules stay outside the assessed denominator. These weights change an editorial checklist, not the evidence or a measured outcome.</p>"
            "<div class='profile-columns'><div><h3>Browser checklist points</h3><table><tbody>" + browser + "</tbody></table></div>"
            "<div><h3>Crawler element weights</h3><table><tbody>" + crawler + "</tbody></table></div></div>"
            f"<p><b>Retrieval:</b> BM25 k1={escaped(retrieval['k1'])}, b={escaped(retrieval['b'])}, "
            f"split target {escaped(retrieval['max_words'])} words at paragraph boundaries (a single paragraph can exceed it). With no question, passage length target is "
            f"{escaped(retrieval['length_target'])} words and position priors are "
            f"{escaped(', '.join(str(x) for x in retrieval['position_priors']))}. "
            f"<b>Gap:</b> rank difference threshold {escaped(profile['gap']['rank_threshold'])}.</p>"
            "<p class='boundary'>Source-friction and experimental attention formulas are fixed in this profile. "
            "Changing weights or the question from a saved capture creates a new report revision; it does not change the original capture.</p></section>")


def reader_views_html(result: dict[str, object], asset_dir: Path) -> str:
    """Render three projections of the same saved Chromium frames."""
    if result.get("schema") != "s2c-reader-views/v1" or not result.get("frames"):
        raise ValueError("Expected non-empty s2c-reader-views/v1")

    def map_html(frame: dict, items: list[dict], kind: str) -> str:
        viewport = frame["viewport"]
        width, height = int(viewport["width"]), int(viewport["height"])
        image_name = frame["image"]
        if not isinstance(image_name, str) or Path(image_name).name != image_name:
            raise ValueError("Reader view image must be a capture filename")
        image_path = (asset_dir / image_name).resolve()
        if not image_path.is_relative_to(asset_dir.resolve()):
            raise ValueError("Reader view image must stay inside the capture directory")
        maximum = max((float(item.get("weight", item.get("relative_score", abs(item.get("difference", 0))))) for item in items), default=0) or 1
        marks = []
        for item in items:
            if not item.get("in_viewport", True) or not isinstance(item.get("box"), dict):
                continue
            box = item["box"]
            try:
                x, y = max(0, float(box["x"])), max(0, float(box["y"]))
                w, h = max(0, float(box["width"])), max(0, float(box["height"]))
            except (KeyError, TypeError, ValueError):
                continue
            if x >= width or y >= height or w <= 0 or h <= 0:
                continue
            if item.get("flag"):
                marks.append(f"<rect x='{x:.1f}' y='{y:.1f}' width='{w:.1f}' height='{h:.1f}' fill='url(#hatch-{kind}-{escaped(frame['id'])})' stroke='#ab491d' stroke-width='3'/>")
                continue
            value = float(item.get("weight", item.get("relative_score", abs(item.get("difference", 0)))))
            if value <= 0:
                continue
            color = ("#c52e28" if float(item.get("difference", 0)) >= 0 else "#1558be") if kind == "gap" else "#dc6927"
            opacity = 0.18 + 0.48 * value / maximum
            marks.append(f"<rect x='{x:.1f}' y='{y:.1f}' width='{w:.1f}' height='{h:.1f}' rx='3' fill='{color}' fill-opacity='{opacity:.2f}' stroke='{color}' stroke-opacity='.9' stroke-width='2'/>")
        pattern = f"<defs><pattern id='hatch-{kind}-{escaped(frame['id'])}' patternUnits='userSpaceOnUse' width='6' height='6' patternTransform='rotate(45)'><line x1='0' y1='0' x2='0' y2='6' stroke='#ab491d' stroke-width='3'/></pattern></defs>"
        return (f"<div class='reader-map' style='max-width:min(100%,{width}px)'><img src='{screenshot_uri(image_path)}' alt='{escaped(frame['id'])} page capture'>"
                f"<svg viewBox='0 0 {width} {height}' aria-hidden='true'>{pattern}{''.join(marks)}</svg></div>")

    def frame_title(frame: dict) -> str:
        return f"<h3>{escaped(frame['id'])} · {escaped(frame['viewport']['width'])} × {escaped(frame['viewport']['height'])} CSS px</h3>"

    crawler_rows, retrieval_rows, gap_rows = [], [], []
    for frame in result["frames"]:
        crawler = frame["crawler"]
        crawler_nodes = crawler["nodes"]
        top = sorted((row for row in crawler_nodes if row["weight"] > 0), key=lambda row: -row["weight"])[:8]
        flags = [row for row in crawler_nodes if row.get("flag") and row.get("in_viewport")]
        checks = "".join(f"<li><b>{escaped(c['label'])}:</b> {escaped(c['status'])} · {escaped(c['detail'])}</li>" for c in crawler["checks"])
        crawler_rows.append(f"<div class='reader-frame'>{frame_title(frame)}"
                            + map_html(frame, crawler_nodes, "crawler")
                            + "<p class='map-key'>Orange: relative editorial index weight. Hatched: visible content without a captured name or alt.</p>"
                            + "<h4>Highest rule weights</h4><ol>"
                            + "".join(f"<li><b>{escaped(row['label'])}</b> · {row['weight']:.2f} · {escaped(row['rule'])}</li>" for row in top)
                            + "</ol><h4>Warnings</h4><ul>"
                            + ("".join(f"<li>{escaped(row['label'])}: {escaped(row['rule'])}</li>" for row in flags[:8]) or "<li>None in this viewport.</li>")
                            + f"</ul><h4>Checks</h4><ul>{checks}</ul></div>")

        retrieval = frame["retrieval"]
        chunks = sorted(retrieval["chunks"], key=lambda chunk: -chunk["relative_score"])
        boxes = [{"id": box["id"], "box": box["box"], "in_viewport": box["in_viewport"],
                  "relative_score": chunk["relative_score"]} for chunk in chunks for box in chunk["boxes"]]
        chunk_rows = "".join(f"<li><b>{escaped(chunk['heading'] or 'Opening text')}</b> · {chunk['word_count']} words · score {chunk['relative_score']:.2f}"
                             + (f" · matched: {escaped(', '.join(chunk['matched_terms']))}" if chunk["matched_terms"] else "")
                             + f"<p>{escaped(chunk['text'][:250])}</p></li>" for chunk in chunks[:8])
        retrieval_rows.append(f"<div class='reader-frame'>{frame_title(frame)}"
                              + map_html(frame, boxes, "retrieval")
                              + f"<p class='map-key'>Orange: relative passage score. {len(retrieval['removed'])} captured boilerplate nodes removed. {retrieval['main_word_count']} retained words in {len(chunks)} chunks.</p>"
                              + f"<h4>Top passages</h4><ol>{chunk_rows or '<li>No retained text in this capture.</li>'}</ol></div>")

        gap = frame["gap"]
        if gap["available"]:
            comparisons = gap["comparisons"][:8]
            gap_rows.append(f"<div class='reader-frame'>{frame_title(frame)}"
                            + map_html(frame, comparisons, "gap")
                            + f"<p class='map-key'>Red: attention estimate higher. Blue: other reader higher. Compared {gap['compared_nodes']} mapped nodes; {escaped(gap.get('rank_threshold', 0.4))} rank-percentile threshold.</p>"
                            + "<h4>Largest differences</h4><ol>"
                            + ("".join(f"<li><b>{escaped(row['label'])}</b> · {escaped(row['reader'])} · {escaped(row['direction'])} ({abs(row['difference']):.2f}) · {escaped(row['reason'])}</li>" for row in comparisons) or "<li>No difference crossed the threshold in this viewport.</li>")
                            + "</ol></div>")
        else:
            gap_rows.append(f"<div class='reader-frame'>{frame_title(frame)}<p>{escaped(gap['reason'])}</p></div>")

    question = result.get("question") or "No question: position and passage length prior"
    retrieval_mode = result["frames"][0]["retrieval"]["mode"]
    return ("<section class='reader-section' id='crawler'><p class='eyebrow'>CRAWLER / S2C-CRAWLER-V1</p><h2>What can an indexer find?</h2>"
            "<p>Basis: captured DOM roles, text, head metadata, and element boxes. Index weights are editorial rules, not search ranking. The map shows what this capture offers an indexer and where it appears on screen; it does not predict traffic or snippets. Network files and structured data were not inspected.</p>"
            + "".join(crawler_rows) + "</section>"
            + "<section class='reader-section' id='retrieval'><p class='eyebrow'>RETRIEVAL / S2C-RETRIEVAL-V1</p><h2>Which passages match a question?</h2>"
            f"<p><b>Question:</b> {escaped(question)}. Basis: boilerplate-stripped captured text, heading chunks, and {'local BM25' if retrieval_mode == 'bm25' else 'fixed position and length priors'}. The score is relative within each viewport. This does not predict citation, inclusion, or ranking in any AI product.</p>"
            + "".join(retrieval_rows) + "</section>"
            + "<section class='reader-section' id='gap'><p class='eyebrow'>CROSS-VIEW / S2C-GAP-V1</p><h2>Where do these projections disagree?</h2>"
            "<p>Basis: rank differences between the uncalibrated attention estimate and crawler weights, passage scores, or the first ten accessibility reading steps. These are element-rank comparisons, not measured pixel saliency or reader behavior. The attention estimate has not beaten a position-only baseline on held-out webpages.</p>"
            + "".join(gap_rows) + "</section>")


def render(payload: dict[str, object], walkthrough: dict[str, object] | None = None,
           asset_dir: Path | None = None, signal_samples: list[object] | None = None,
           attention: dict[str, object] | None = None,
           attention_dir: Path | None = None, assistive: dict[str, object] | None = None,
           assistive_dir: Path | None = None, rubric: dict[str, object] | None = None,
           reader_views: dict[str, object] | None = None,
           reader_views_dir: Path | None = None,
           scoring_profile: dict[str, object] | None = None,
           site_basics: dict[str, object] | None = None,
           robot_visibility: dict[str, object] | None = None) -> str:
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
    heat = attention_html(attention, attention_dir or Path.cwd()) if attention else ""
    contrast = wcag_spotcheck_html(attention) if attention else ""
    assistive_view = assistive_html(assistive, assistive_dir or Path.cwd()) if assistive else ""
    reader_view = reader_views_html(reader_views, reader_views_dir or Path.cwd()) if reader_views else ""
    rubric_view = browser_rubric_html(rubric) if rubric else ""
    profile_view = scoring_profile_html(scoring_profile) if scoring_profile else ""
    basics_view = site_basics_html(site_basics) if site_basics else ""
    robot_view = robot_visibility_html(robot_visibility) if robot_visibility else ""
    actions = collect_actions(reports[0], rubric, site_basics, robot_visibility)
    actions_view = priority_actions_html(actions)
    final_actions_view = action_plan_html(actions)
    rubric_teaser = ("<aside class='rubric-teaser' aria-label='Browser checklist summary'>"
                     f"<strong>{escaped(rubric['score']['earned'])}/{escaped(rubric['score']['assessed'])}</strong>"
                     f"<span>assessed browser points confirmed · {escaped(rubric['counts']['warning'])} warning(s). "
                     "Editorial checklist, not a UX or cognitive-load score.</span>"
                     "<a href='#rubric'>See all rule evidence and actions</a></aside>") if rubric else ""
    dated = walkthrough.get("audited_on") if walkthrough else (assistive.get("audited_on") if assistive else payload.get("audited_on"))
    if payload.get("audited_on") and payload["audited_on"] != dated:
        raise ValueError("Audit JSON and report dates do not match")
    if assistive and assistive.get("audited_on") != dated:
        raise ValueError("Assistive and report dates do not match")
    if rubric and rubric.get("audited_on") != dated:
        raise ValueError("Browser rubric and report dates do not match")
    if reader_views and reader_views.get("audited_on") != dated:
        raise ValueError("Reader views and report dates do not match")
    if site_basics and site_basics.get("audited_on") != dated:
        raise ValueError("Site basics and report dates do not match")
    if robot_visibility and robot_visibility.get("audited_on") != dated:
        raise ValueError("Robot visibility and report dates do not match")
    body = report_html(reports[0], walk, dated, signals, heat, assistive_view, rubric_view, rubric_teaser,
                       reader_view, contrast, profile_view, basics_view, actions_view, robot_view,
                       final_actions_view) + "\n" + "\n".join(report_html(report, audited_on=dated) for report in reports[1:])
    source_name = str(reports[0].get("source", "Audited page"))
    host = urlsplit(source_name).hostname or source_name
    menu = [("overview", "Overview", True), ("actions", "Priority actions", bool(actions_view)),
            ("rubric", "Browser checklist", bool(rubric)), ("scoring-profile", "Scoring profile", bool(profile_view)),
            ("site-basics", "Page basics", bool(basics_view)), ("attention", "Attention map", bool(heat)),
            ("robot-visibility", "Robot visibility", bool(robot_view)),
            ("assistive", "Reading & keyboard", bool(assistive_view)), ("crawler", "Crawler", bool(reader_view)),
            ("retrieval", "Retrieval", bool(reader_view)), ("gap", "Gaps", bool(reader_view)),
            ("contrast", "Text contrast", bool(contrast)), ("summary", "Source structure", True),
            ("action-plan", "Action plan", True)]
    side_nav = "".join(f"<a href='#{anchor}'>{escaped(label)}</a>" for anchor, label, shown in menu if shown)
    shell_css = (Path(__file__).resolve().parents[1] / "assets" / "report-shell.css").read_text(encoding="utf-8")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{'S2C page audit' if rubric or walkthrough else ('S2C assistive reading view' if assistive else ('S2C visual attention baseline' if attention else 'S2C source audit'))}</title>
<style>
:root{{color-scheme:light;--ink:#17211b;--muted:#4b5d50;--line:#c9d6ca;--paper:#f7f7f2;--green:#0d6b4e;--soft:#e8f2e9}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.5 system-ui,sans-serif}}
main{{max-width:1100px;margin:auto;padding:clamp(1rem,3vw,2.5rem)}}.report{{margin-bottom:3rem}}
.eyebrow,.step{{color:var(--green);font-size:.78rem;font-weight:700;letter-spacing:.12em}}
h1{{font-size:clamp(1.8rem,4vw,3rem);overflow-wrap:anywhere;line-height:1.15;margin:.35rem 0}}
h2{{font-size:1.15rem;line-height:1.25;margin:0 0 .65rem}}p{{margin:.25rem 0 1rem}}.subtitle{{color:var(--muted)}}
.audit-date{{display:inline-block;background:var(--soft);border-left:3px solid var(--green);padding:.45rem .7rem;margin:.45rem 0 .7rem;font-size:.93rem}}
.report-nav{{display:flex;flex-wrap:wrap;gap:.4rem 1rem;margin:.6rem 0 1rem;font-size:.93rem}}.report-nav a{{color:var(--green);font-weight:700}}
.rubric-teaser{{display:flex;align-items:center;gap:.65rem 1rem;flex-wrap:wrap;background:#fff;border-left:5px solid #a35a00;padding:.7rem 1rem;margin:1.2rem 0}}.rubric-teaser strong{{font-size:1.3rem;white-space:nowrap}}.rubric-teaser span{{flex:1 1 360px;font-size:.88rem}}.rubric-teaser a{{color:var(--green);font-weight:700;font-size:.88rem}}
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
.action-board{{background:#fff;border:1px solid var(--line);border-top:5px solid #a35a00;padding:1.2rem;margin:1rem 0 2rem}}.action-board h3{{font-size:1.35rem;margin:0}}.action-board>p{{color:var(--muted);font-size:.9rem}}
.action-board ol{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.7rem;list-style:none;padding:0;margin:0}}.action-board li{{background:#fff8eb;border:1px solid #e8d5b7;padding:.8rem;margin:0}}.action-board a{{color:var(--ink);font-weight:750}}.action-board li p{{margin:.4rem 0 0;font-size:.9rem}}.priority{{display:inline-block;background:#763b00;color:#fff;padding:.13rem .42rem;border-radius:.2rem;font:700 .72rem system-ui,sans-serif;margin-right:.3rem}}.evidence-level{{display:inline-block;color:#5d533f;font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;margin-left:.3rem}}
.walk-row{{display:grid;grid-template-columns:minmax(0,1.9fr) minmax(260px,1fr);gap:1.2rem;align-items:start}}
.shot{{position:relative;min-width:0}}.shot img{{display:block;width:100%;height:auto;border:1px solid var(--line)}}
.pin{{position:absolute;transform:translate(-50%,-50%);display:grid;place-items:center;width:2rem;height:2rem;border-radius:50%;background:var(--ink);color:#fff;text-decoration:none;font-weight:700;box-shadow:0 0 0 3px #fff}}
.pin.strength{{background:var(--green)}}.pin:focus-visible{{outline:3px solid #e08d12;outline-offset:4px}}
.margin{{list-style:none;padding:0;margin:0;display:grid;gap:.8rem}}.callout{{border-left:4px solid #b06c00;padding:.3rem 0 .3rem .8rem;background:#fff}}
.callout.strength{{border-left-color:var(--green)}}.callout:target{{background:var(--soft)}}.callout-type{{text-transform:uppercase;letter-spacing:.1em;color:var(--muted);font-size:.7rem;font-weight:700}}
.callout h4{{margin:.15rem 0 .35rem;font-size:1rem}}.callout p{{font-size:.87rem;margin:.25rem 0;color:var(--muted)}}.callout b{{color:var(--ink)}}
.callout .suggestion{{background:#fff0d8;border-left:3px solid #a35a00;color:var(--ink);padding:.5rem .6rem;margin:.55rem 0;font-size:.9rem}}.callout.strength .suggestion{{background:#e8f2e9;border-left-color:var(--green)}}
.browser-rubric{{margin:2.5rem 0;padding:1.4rem;background:#fff;border:1px solid var(--line)}}.browser-rubric>h2{{font-size:1.55rem}}.rubric-summary{{display:flex;align-items:center;gap:1.2rem;background:#f4f6f0;padding:1rem;margin:1rem 0}}.rubric-summary>strong{{white-space:nowrap;font-size:2.3rem;line-height:1}}.rubric-summary>strong span{{font-size:1.3rem;color:var(--muted)}}.rubric-summary p{{margin:0}}.rubric-rules{{list-style:none;padding:0;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.8rem}}.rubric-rule{{margin:0;padding:1rem;border:1px solid var(--line);border-left:4px solid var(--green);background:#fbfcfa}}.rubric-rule.warning{{border-left-color:#a35a00;background:#fff8eb}}.rubric-rule.review,.rubric-rule.not_checked{{border-left-color:#667784}}.rubric-rule-head{{display:flex;flex-wrap:wrap;gap:.3rem .6rem;align-items:baseline}}.rubric-rule-head h3{{flex:1 1 100%;font-size:1rem;margin:.1rem 0}}.rubric-rule-head strong{{font-size:.82rem}}.rubric-status{{font-size:.72rem;font-weight:800;text-transform:uppercase;letter-spacing:.06em}}.rubric-rule ul{{font-size:.85rem;margin:.35rem 0}}.rubric-next{{font-size:.85rem;background:#fff;padding:.4rem .55rem;margin:.5rem 0 0}}
.scoring-profile{{margin:2.5rem 0;padding:1.4rem;background:#fff;border:1px solid var(--line)}}.scoring-profile>h2{{font-size:1.55rem}}.profile-columns{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}}.profile-columns>div{{min-width:0}}.profile-columns table{{border-collapse:collapse;width:100%;font-size:.84rem}}.profile-columns th,.profile-columns td{{border-bottom:1px solid var(--line);padding:.38rem;text-align:left;vertical-align:top}}.profile-columns td{{white-space:nowrap}}@media(max-width:700px){{.profile-columns{{grid-template-columns:1fr}}}}
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
.assistive{{margin:2.5rem 0;padding:1.4rem;background:#fff;border:1px solid var(--line)}}
.assistive>h2{{font-size:1.55rem}}.assistive>p{{max-width:85ch}}.assistive-frame{{border-top:1px solid var(--line);padding:1.3rem 0}}
.assistive-frame h3{{font-size:1.1rem}}.assistive-toggle{{accent-color:var(--green);margin:.2rem .3rem .8rem .8rem}}
.assistive-toggle:first-of-type{{margin-left:0}}.assistive-toggle+label{{cursor:pointer;font-weight:700}}
.assistive-view{{position:relative;max-width:850px}}.assistive-view img{{display:block;width:100%;height:auto;border:1px solid var(--line)}}
.assistive-view svg{{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}}
.reading-toggle:not(:checked)~.assistive-view .reading-path,.focus-toggle:not(:checked)~.assistive-view .focus-path{{display:none}}
.assistive-columns{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem;margin-top:1rem;font-size:.87rem}}
.assistive-columns details,.assistive-columns>div{{min-width:0;background:var(--paper);padding:.7rem}}.assistive-columns summary{{cursor:pointer;font-weight:700}}
.assistive-columns ol,.assistive-columns ul{{max-height:20rem;overflow:auto;overflow-wrap:anywhere}}
.assistive-columns .marker-key{{list-style:none;padding-left:0}}
.reader-section{{margin:2.5rem 0;padding:1.4rem;background:#fff;border:1px solid var(--line)}}
.reader-section>h2{{font-size:1.55rem}}.reader-section>p{{max-width:85ch}}
.reader-frame{{border-top:1px solid var(--line);padding:1.3rem 0}}
.reader-frame h3{{font-size:1.1rem;margin:0 0 .75rem}}.reader-frame h4{{margin:1rem 0 .3rem}}
.reader-frame ol,.reader-frame ul{{max-width:85ch;overflow-wrap:anywhere}}
.reader-frame li p{{color:var(--muted);font-size:.87rem;margin:.15rem 0 .5rem}}
.reader-map{{position:relative}}.reader-map img{{display:block;width:100%;height:auto;border:1px solid var(--line)}}
.reader-map svg{{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}}
.map-key{{font-size:.87rem;color:var(--muted);margin:.6rem 0}}
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
@media(max-width:700px){{.action-board ol{{grid-template-columns:1fr}}}}
@media(max-width:700px){{.rubric-rules{{grid-template-columns:1fr}}}}
@media(max-width:540px){{.margin{{grid-template-columns:1fr}}}}
@media(max-width:700px){{.attention-cues{{grid-template-columns:1fr}}}}
@media(max-width:700px){{.assistive-columns{{grid-template-columns:1fr}}}}
@media(max-width:450px){{.summary{{display:block}}.score{{margin-bottom:.7rem}}.outline .h5,.outline .h6{{padding-left:3rem}}}}
</style><style>{shell_css}</style></head><body><div class="s2c-shell">
<aside class="s2c-sidebar"><div class="s2c-brand"><span class="s2c-mark">S<span>2</span>C</span>
<div><strong>SCAN TO COMPREHEND</strong><small>Triuna Labs / audit report</small></div></div>
<p class="s2c-side-label">REPORT NAVIGATION</p><nav aria-label="Report navigation">{side_nav}</nav>
<div class="s2c-side-foot">AUDITED {escaped(dated or 'DATE NOT RECORDED')}<br>Method and limits accompany each view.</div></aside>
<div class="s2c-content"><div class="s2c-topbar"><span>Website audit <b>/</b> {escaped(host)}</span>
<span>CAPTURED EVIDENCE · EDITORIAL SCORING</span></div><main>{body}</main></div></div></body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit_json", type=Path, help="JSON from s2c_audit.py --json")
    parser.add_argument("--output", required=True, type=Path, help="HTML report to write")
    parser.add_argument("--walkthrough", type=Path, help="Optional rendered-page capture and callout JSON")
    parser.add_argument("--signals", nargs="+", type=Path, help="Optional opt-in section signals session exports")
    parser.add_argument("--attention", type=Path, help="Optional S2C heuristic attention result JSON")
    parser.add_argument("--assistive", type=Path, help="Optional s2c-assistive-v1 result JSON")
    parser.add_argument("--reader-views", type=Path, help="Optional s2c-reader-views/v1 result JSON")
    parser.add_argument("--scoring-profile", type=Path, help="Optional s2c-scoring-profile/v1 JSON")
    parser.add_argument("--site-basics", type=Path, help="Optional s2c-site-basics/v1 JSON")
    parser.add_argument("--robot-visibility", type=Path, help="Optional s2c-robot-visibility/v1 JSON")
    parser.add_argument("--rubric", type=Path, help="Optional deterministic browser rubric result JSON")
    args = parser.parse_args()
    payload = json.loads(args.audit_json.read_text(encoding="utf-8"))
    walkthrough = json.loads(args.walkthrough.read_text(encoding="utf-8")) if args.walkthrough else None
    signal_samples = [json.loads(path.read_text(encoding="utf-8")) for path in args.signals] if args.signals else None
    attention = json.loads(args.attention.read_text(encoding="utf-8")) if args.attention else None
    assistive = json.loads(args.assistive.read_text(encoding="utf-8")) if args.assistive else None
    reader_views = json.loads(args.reader_views.read_text(encoding="utf-8")) if args.reader_views else None
    scoring_profile = s2c_scoring_profile.read(args.scoring_profile) if args.scoring_profile else None
    site_basics = json.loads(args.site_basics.read_text(encoding="utf-8")) if args.site_basics else None
    robot_visibility = json.loads(args.robot_visibility.read_text(encoding="utf-8")) if args.robot_visibility else None
    rubric = json.loads(args.rubric.read_text(encoding="utf-8")) if args.rubric else None
    result = render(payload, walkthrough, args.walkthrough.parent if args.walkthrough else None,
                    signal_samples, attention, args.attention.parent if args.attention else None,
                    assistive, args.assistive.parent if args.assistive else None, rubric,
                    reader_views, (args.reader_views.parent / "capture") if args.reader_views else None,
                    scoring_profile, site_basics, robot_visibility)
    result = "\n".join(line.rstrip() for line in result.splitlines()) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result, encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
