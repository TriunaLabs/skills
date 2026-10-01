#!/usr/bin/env python3
"""Render a Laws of UX findings file as a standalone annotated poster.

Usage:
    python scripts/render_review.py findings.json -o review.html
    python scripts/render_review.py findings.json -o review.html --screenshot page.png
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import mimetypes
from pathlib import Path
from review_model import validate_review


def esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def load_screenshot(path: str | None) -> str | None:
    if not path:
        return None
    file_path = Path(path)
    if not file_path.is_file():
        raise SystemExit(f"screenshot not found: {file_path}")
    mime = mimetypes.guess_type(file_path.name)[0] or "image/png"
    if mime not in {"image/png", "image/jpeg", "image/webp"}:
        raise SystemExit("screenshot must be PNG, JPEG, or WebP")
    if file_path.stat().st_size > 12 * 1024 * 1024:
        raise SystemExit("screenshot exceeds the 12 MB limit")
    encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def card(finding: dict) -> str:
    fix = finding.get("recommendation") or ""
    fix_html = f'<p class="fix">{esc(fix)}</p>' if fix else ""
    verification = finding.get("verification") or []
    verify_html = f'<p class="verify">Verify: {esc(verification[0])}</p>' if verification else ""
    anchor = finding.get("anchor") or {}
    x = float(anchor.get("x", 0.5))
    y = float(anchor.get("y", 0.5))
    return f"""
      <article class="card" data-n="{esc(finding.get('n'))}" data-x="{x:.4f}" data-y="{y:.4f}">
        <span class="num">{esc(finding.get('n'))}</span>
        <div>
          <div class="card-meta"><span>{esc(finding.get('region'))}</span><span class="severity {esc(finding.get('severity'))}">{esc(finding.get('severity'))}</span><span>{float(finding.get('confidence', 0)):.0%}</span></div>
          <h2>{esc(finding.get('principle'))}</h2>
          <p>{esc(finding.get('observation'))}</p>
          {fix_html}
          {verify_html}
        </div>
      </article>"""


def render(data: dict, screenshot: str | None) -> str:
    errors = validate_review(data, poster=True)
    if errors:
        raise SystemExit("Invalid review:\n- " + "\n- ".join(errors))
    findings = list(data.get("findings") or [])
    if not findings:
        raise SystemExit("findings array is empty")
    if len(findings) > 14:
        raise SystemExit("cap the poster at 14 findings; group overlaps first")

    left, right = [], []
    for index, finding in enumerate(findings):
        side = (finding.get("side") or "").lower()
        if side == "right":
            right.append(finding)
        elif side == "left":
            left.append(finding)
        elif index % 2 == 0:
            left.append(finding)
        else:
            right.append(finding)

    if screenshot:
        plate = f'<img class="shot" alt="Reviewed interface evidence" src="{screenshot}">' 
    else:
        plate = """
          <div class="wire">
            <div class="logo">logo</div>
            <div class="nav"><span></span><span></span><span></span><span></span></div>
            <div class="hero"><b></b><b class="short"></b><i></i></div>
            <div class="pills"><span></span><span></span><span></span></div>
            <div class="block"></div>
            <div class="rows"><span></span><span></span><span></span></div>
            <div class="cards"><span></span><span></span><span></span></div>
          </div>"""

    url = (data.get("source") or {}).get("ref") or ""
    url_html = f'<p class="url">{esc(url)}</p>' if url else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(data.get("title") or "Laws of UX Review")}</title>
  <style>
    :root {{
      --paper: #f6f3ec;
      --ink: #1c1c1c;
      --muted: #5e5a52;
      --line: #d9d3c7;
      --card: #fffcf7;
      --green: #1f6b45;
      --green-soft: #dcecde;
      --frame: #fbfaf6;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: Georgia, "Iowan Old Style", Palatino, "Palatino Linotype", serif;
    }}
    .poster {{
      width: min(1100px, 100%);
      margin: 0 auto;
      padding: 42px 36px 56px;
      position: relative;
    }}
    header {{ text-align: center; margin-bottom: 28px; }}
    h1 {{
      font-weight: 500;
      font-size: 64px;
      line-height: 0.95;
      letter-spacing: -1.5px;
      margin: 0;
    }}
    h1 em {{
      font-style: italic;
      background: #e4f0d8;
      padding: 0 0.12em;
    }}
    .sub {{
      margin: 14px 0 0;
      font-family: "Avenir Next", "Segoe UI", sans-serif;
      font-size: 22px;
      font-weight: 650;
      letter-spacing: -0.2px;
    }}
    .url {{
      margin: 6px 0 0;
      color: var(--muted);
      font-family: "Avenir Next", "Segoe UI", sans-serif;
      font-size: 13px;
    }}
    .stage {{
      display: grid;
      grid-template-columns: 1fr 380px 1fr;
      gap: 18px;
      align-items: stretch;
      min-height: 760px;
      position: relative;
    }}
    .col {{
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 14px;
      z-index: 2;
    }}
    .card {{
      display: flex;
      gap: 10px;
      background: var(--card);
      border: 1px solid #e4ded2;
      border-radius: 10px;
      padding: 12px 12px 12px 10px;
      box-shadow: 0 1px 0 rgba(255,255,255,0.8) inset;
    }}
    .num {{
      flex: 0 0 28px;
      height: 28px;
      border-radius: 50%;
      background: var(--green-soft);
      color: var(--green);
      font-family: "Avenir Next", "Segoe UI", sans-serif;
      font-weight: 700;
      font-size: 14px;
      display: grid;
      place-items: center;
    }}
    .card h2 {{
      margin: 2px 0 4px;
      font-size: 15px;
      line-height: 1.2;
      font-weight: 650;
    }}
    .card p {{
      margin: 0;
      font-family: "Avenir Next", "Segoe UI", sans-serif;
      font-size: 13px;
      line-height: 1.35;
      color: #333;
    }}
    .card .fix {{
      margin-top: 6px;
      color: var(--green);
    }}
    .card-meta {{display:flex;gap:6px;align-items:center;margin-bottom:6px;font:600 9px/1.2 "Segoe UI",sans-serif;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}}
    .card-meta .severity {{padding:3px 5px;border-radius:10px;background:#eee9de}}
    .card-meta .critical,.card-meta .high {{background:#f4dfd8;color:#8b2e1f}}
    .card .verify {{margin-top:6px;color:var(--muted);font-size:11px}}
    .frame-wrap {{ position: relative; z-index: 1; }}
    .browser {{
      background: var(--frame);
      border: 1.5px solid #cfc8bb;
      border-radius: 16px;
      min-height: 760px;
      overflow: hidden;
      box-shadow: 0 10px 30px rgba(40, 36, 28, 0.06);
    }}
    .chrome {{
      height: 34px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 0 12px;
    }}
    .chrome i {{
      width: 8px; height: 8px; border-radius: 50%;
      background: #e4dfd6; display: block;
    }}
    .shot {{ width: 100%; display: block; }}
    .wire {{ padding: 22px 22px 28px; }}
    .logo {{
      height: 14px; width: 72px; margin: 8px auto 18px;
      background: #e7e1d6; border-radius: 4px;
    }}
    .nav {{ display: flex; justify-content: center; gap: 10px; margin-bottom: 22px; }}
    .nav span {{ width: 42px; height: 8px; background: #ece7de; border-radius: 4px; }}
    .hero {{
      background: #e7f0df;
      border-radius: 8px;
      padding: 28px 22px;
      margin-bottom: 18px;
    }}
    .hero b {{ display: block; height: 12px; background: #c9d7c4; border-radius: 4px; margin: 8px 18px; }}
    .hero .short {{ width: 62%; margin-left: auto; margin-right: auto; }}
    .hero i {{ display: block; width: 92px; height: 28px; background: #234; border-radius: 6px; margin: 16px auto 0; }}
    .pills, .cards {{ display: flex; gap: 10px; justify-content: center; margin: 14px 0; }}
    .pills span, .cards span {{
      width: 72px; height: 72px; border-radius: 50%; background: #e7f0df;
    }}
    .cards span {{ border-radius: 8px; height: 108px; background: #f3f7ef; border: 1px solid #e0eadc; }}
    .block {{
      height: 120px; border-radius: 10px; background: #eef4ea; margin: 16px 0;
    }}
    .rows span {{
      display: block; height: 12px; background: #ece7de; border-radius: 4px; margin: 10px 12px;
    }}
    svg.links {{
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
      z-index: 3;
    }}
    @media (max-width: 860px) {{
      h1 {{ font-size: 42px; }}
      .stage {{ grid-template-columns: 1fr; }}
      .browser {{ min-height: 0; }}
      svg.links {{ display: none; }}
    }}
    @media print {{
      @page {{ size: landscape; margin: 8mm; }}
      body {{ background: white; }}
      .poster {{ width: 100%; padding: 0; }}
    }}
    @media (prefers-contrast: more) {{ .card,.browser {{border-color:#4c4c4c}} .card p {{color:#111}} }}
  </style>
</head>
<body>
  <div class="poster">
    <header>
      <h1>Laws of UX <em>Review</em></h1>
      <p class="sub">{esc(data.get("subtitle") or "Annotated findings")}</p>
      {url_html}
    </header>
    <div class="stage" id="stage">
      <div class="col" id="left">{''.join(card(item) for item in left)}</div>
      <div class="frame-wrap">
        <div class="browser" id="browser">
          <div class="chrome"><i></i><i></i><i></i></div>
          {plate}
        </div>
      </div>
      <div class="col" id="right">{''.join(card(item) for item in right)}</div>
      <svg class="links" id="links"></svg>
    </div>
  </div>
  <script>
    function draw() {{
      const stage = document.getElementById("stage");
      const browser = document.getElementById("browser");
      const svg = document.getElementById("links");
      const sr = stage.getBoundingClientRect();
      const br = browser.getBoundingClientRect();
      svg.setAttribute("viewBox", `0 0 ${{sr.width}} ${{sr.height}}`);
      svg.innerHTML = "";
      document.querySelectorAll(".card").forEach((card) => {{
        const cr = card.getBoundingClientRect();
        const x = parseFloat(card.dataset.x || "0.5");
        const y = parseFloat(card.dataset.y || "0.5");
        const onLeft = cr.left < br.left;
        const x1 = (onLeft ? cr.right : cr.left) - sr.left;
        const y1 = cr.top + cr.height / 2 - sr.top;
        const x2 = br.left - sr.left + br.width * x;
        const y2 = br.top - sr.top + br.height * y;
        const mid = (x1 + x2) / 2;
        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        path.setAttribute("d", `M ${{x1}} ${{y1}} C ${{mid}} ${{y1}}, ${{mid}} ${{y2}}, ${{x2}} ${{y2}}`);
        path.setAttribute("fill", "none");
        path.setAttribute("stroke", "#b7cfc0");
        path.setAttribute("stroke-width", "1.4");
        svg.appendChild(path);
      }});
    }}
    window.addEventListener("load", draw);
    window.addEventListener("resize", draw);
  </script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a Laws of UX annotated poster")
    parser.add_argument("findings", help="Path to findings JSON")
    parser.add_argument("-o", "--output", required=True, help="Output HTML path")
    parser.add_argument("--screenshot", help="Optional page screenshot to embed")
    args = parser.parse_args()

    data = json.loads(Path(args.findings).read_text(encoding="utf-8"))
    screenshot = load_screenshot(args.screenshot)
    html_out = render(data, screenshot)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html_out, encoding="utf-8")
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
