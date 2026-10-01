#!/usr/bin/env python3
"""Deterministic landing-page observation for the answer-ready-web skill."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


SKIP = {"script", "style", "template", "noscript", "svg"}
CAPTURE = {"title", "h1", "h2", "h3", "p", "time", "a", "button"}
CLAIM_RE = re.compile(
    r"\b(?:\d+(?:[.,]\d+)?%?|best|leading|fastest|easiest|proven|guaranteed|"
    r"save[sd]?|reduce[sd]?|increase[sd]?|trusted by|secure|compliant)\b",
    re.I,
)
QUESTION_WORDS = ("what ", "how ", "why ", "who ", "when ", "where ", "which ", "can ", "does ", "is ", "are ")


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


@dataclass
class Capture:
    tag: str
    attrs: dict[str, str]
    text: list[str] = field(default_factory=list)


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: Counter[str] = Counter()
        self.attrs: dict[str, list[dict[str, str]]] = {}
        self.captures: list[Capture] = []
        self.values: dict[str, list[tuple[str, dict[str, str]]]] = {tag: [] for tag in CAPTURE}
        self.visible: list[str] = []
        self.skip_depth = 0
        self.jsonld_active = False
        self.jsonld_buffer: list[str] = []
        self.jsonld: list[object] = []
        self.jsonld_errors = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        data = {k.lower(): (v or "") for k, v in attrs}
        self.tags[tag] += 1
        self.attrs.setdefault(tag, []).append(data)
        if tag == "script" and data.get("type", "").lower() == "application/ld+json":
            self.jsonld_active = True
            self.jsonld_buffer = []
        if tag in SKIP:
            self.skip_depth += 1
        if tag in CAPTURE and self.skip_depth == 0:
            self.captures.append(Capture(tag, data))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self.jsonld_active:
            self.jsonld_buffer.append(data)
        if self.skip_depth == 0:
            if clean(data):
                self.visible.append(data)
            for capture in self.captures:
                capture.text.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "script" and self.jsonld_active:
            raw = "".join(self.jsonld_buffer).strip()
            if raw:
                try:
                    self.jsonld.append(json.loads(raw))
                except json.JSONDecodeError:
                    self.jsonld_errors += 1
            self.jsonld_active = False
        if tag in CAPTURE and self.captures:
            for index in range(len(self.captures) - 1, -1, -1):
                if self.captures[index].tag == tag:
                    capture = self.captures.pop(index)
                    self.values[tag].append((clean(" ".join(capture.text)), capture.attrs))
                    break
        if tag in SKIP and self.skip_depth:
            self.skip_depth -= 1


def load_source(source: str, timeout: int) -> tuple[str, str]:
    if source.startswith(("https://", "http://")):
        request = urllib.request.Request(source, headers={"User-Agent": "TriunaLabs-AnswerReadyAudit/0.1"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace"), response.geturl()
    path = Path(source).expanduser().resolve()
    return path.read_text(encoding="utf-8"), str(path)


def meta_value(parser: PageParser, *, name: str = "", prop: str = "") -> str:
    for item in parser.attrs.get("meta", []):
        if name and item.get("name", "").lower() == name.lower():
            return item.get("content", "")
        if prop and item.get("property", "").lower() == prop.lower():
            return item.get("content", "")
    return ""


def link_value(parser: PageParser, rel: str) -> str:
    for item in parser.attrs.get("link", []):
        if rel in item.get("rel", "").lower().split():
            return item.get("href", "")
    return ""


def schema_types(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        current = value.get("@type")
        if isinstance(current, str):
            found.add(current)
        elif isinstance(current, list):
            found.update(str(item) for item in current)
        for child in value.values():
            found.update(schema_types(child))
    elif isinstance(value, list):
        for child in value:
            found.update(schema_types(child))
    return found


def dimension(key: str, label: str, score: int, evidence: str, recommendation: str, applicable: bool = True) -> dict:
    score = max(0, min(10, score))
    status = "not-assessed" if not applicable else ("strong" if score >= 8 else "review" if score >= 5 else "weak")
    return {"id": key, "label": label, "score": score, "max": 10, "status": status,
            "applicable": applicable, "evidence": evidence, "recommendation": recommendation}


def analyze(source: str, document: str) -> dict:
    parser = PageParser()
    parser.feed(document)
    text = clean(" ".join(parser.visible))
    titles = [value for value, _ in parser.values["title"] if value]
    h1s = [value for value, _ in parser.values["h1"] if value]
    h2s = [value for value, _ in parser.values["h2"] if value]
    h3s = [value for value, _ in parser.values["h3"] if value]
    paragraphs = [value for value, _ in parser.values["p"] if value]
    links = [(value, attrs.get("href", "")) for value, attrs in parser.values["a"]]
    buttons = [value for value, _ in parser.values["button"] if value]
    canonical = link_value(parser, "canonical")
    description = meta_value(parser, name="description")
    robots = meta_value(parser, name="robots").lower()
    author = meta_value(parser, name="author")
    lang = parser.attrs.get("html", [{}])[0].get("lang", "") if parser.attrs.get("html") else ""
    types = sorted(set().union(*(schema_types(item) for item in parser.jsonld)))
    opening_candidates = [
        value for value, attrs in parser.values["p"]
        if value and len(value.split()) >= 12 and not re.search(r"\b(?:kicker|eyebrow|label)\b", attrs.get("class", ""), re.I)
    ]
    opening = opening_candidates[0] if opening_candidates else (paragraphs[0] if paragraphs else "")
    opening_words = len(opening.split())
    question_headings = [heading for heading in h2s + h3s if heading.endswith("?") or heading.lower().startswith(QUESTION_WORDS)]
    images = parser.attrs.get("img", [])
    missing_alt = [item.get("src", "(inline image)") for item in images if "alt" not in item]
    generic_links = [label for label, _ in links if clean(label).lower() in {"learn more", "click here", "read more", "more"}]
    external_links = [href for _, href in links if href.startswith(("http://", "https://"))]
    byline_visible = bool(re.search(r"\b(?:written by|by [A-Z][a-z]+|founder|author)\b", text[:2500], re.I))
    cta_labels = [value for value in buttons + [label for label, _ in links] if re.search(r"\b(?:start|book|buy|try|contact|discuss|download|install|play|join|request|email)\b", value, re.I)]

    sentences = [
        clean(part)
        for paragraph in paragraphs
        for part in re.split(r"(?<=[.!?])\s+", paragraph)
        if 8 <= len(clean(part).split()) <= 60
    ]
    claims = []
    has_evidence_section = bool(re.search(r"\b(?:evidence|proof|case stud|benchmark|methodology|source|research)\b", " ".join(h2s + h3s), re.I))
    for sentence in sentences:
        if CLAIM_RE.search(sentence):
            support = "review"
            rationale = "Potential material claim; verify a nearby source and its scope."
            if has_evidence_section and external_links:
                support = "candidate-support"
                rationale = "The page exposes evidence links, but direct claim-to-source support still needs review."
            claims.append({"claim": sentence[:280], "status": support, "note": rationale})
        if len(claims) == 12:
            break

    audience_score = (4 if len(h1s) == 1 else 1 if h1s else 0) + (2 if titles else 0) + (2 if description else 0)
    if h1s and 15 <= len(h1s[0]) <= 110:
        audience_score += 2
    answer_score = 0
    if opening:
        answer_score += 3
    if 35 <= opening_words <= 90:
        answer_score += 4
    elif 20 <= opening_words <= 120:
        answer_score += 2
    if opening and not re.search(r"\b(?:revolutionary|game-changing|world-class|next-generation)\b", opening, re.I):
        answer_score += 3
    architecture_score = min(6, len(h2s) * 2) + (2 if len(h3s) <= max(6, len(h2s) * 3) else 0) + (2 if question_headings else 1)
    entity_score = (3 if author or byline_visible else 0) + (4 if {"Organization", "Person"} & set(types) else 0) + (3 if canonical else 0)
    evidence_score = (3 if has_evidence_section else 0) + min(4, len(external_links)) + (3 if not claims else 1 if external_links else 0)
    semantic_score = (2 if parser.tags["main"] else 0) + (2 if lang else 0) + (2 if len(h1s) == 1 else 0) + (2 if not missing_alt else 0) + (2 if not generic_links else 0)
    schema_score = (4 if parser.jsonld and not parser.jsonld_errors else 0) + (2 if types else 0) + (2 if canonical else 0) + (2 if description else 0)
    access_score = (4 if "noindex" not in robots else 0) + (2 if len(text.split()) >= 120 else 0) + (2 if parser.tags["main"] else 0) + (2 if cta_labels else 0)
    freshness_signals = [value for value, _ in parser.values["time"] if value]
    date_modified = any("dateModified" in json.dumps(item) for item in parser.jsonld)
    freshness_score = (5 if freshness_signals else 0) + (5 if date_modified else 0)
    freshness_applicable = bool(
        freshness_signals or date_modified or {"Article", "NewsArticle"} & set(types)
        or re.search(r"\b(?:last updated|published on|changelog|release notes|pricing)\b", text, re.I)
    )
    comparison_applicable = bool(parser.tags["table"] or re.search(r"\b(?:compare|comparison|alternative|versus| vs\.?|pricing|plans)\b", text, re.I))
    comparison_score = (6 if parser.tags["table"] else 0) + (4 if parser.tags["th"] else 0)
    faq_applicable = len(question_headings) >= 2 or "FAQPage" in types or bool(re.search(r"\bfaq\b", text, re.I))
    faq_score = min(10, len(question_headings) * 2 + (2 if "FAQPage" not in types else 0))

    dims = [
        dimension("audience", "Audience and proposition", audience_score,
                  f"{len(h1s)} H1; title {'present' if titles else 'missing'}; description {'present' if description else 'missing'}.",
                  "Clarify one audience, offer, and decision in the title, H1, and opening context."),
        dimension("answer", "Opening answer", answer_score,
                  f"First paragraph contains {opening_words} words.",
                  "Place a concise factual proposition near the H1; treat 40–60 words as a pattern, not a quota."),
        dimension("architecture", "Decision-path structure", architecture_score,
                  f"{len(h2s)} H2, {len(h3s)} H3, and {len(question_headings)} question-shaped headings.",
                  "Use specific sections that answer the questions needed to make the decision."),
        dimension("entity", "Entity and ownership clarity", entity_score,
                  f"Author signal {'present' if author or byline_visible else 'not detected'}; schema types: {', '.join(types) or 'none'}.",
                  "Make organizational or author responsibility visible where it helps readers judge the offer."),
        dimension("evidence", "Evidence and claim support", evidence_score,
                  f"{len(claims)} potential material claims; {len(external_links)} external links; evidence section {'detected' if has_evidence_section else 'not detected'}.",
                  "Map each consequential claim to direct, scoped, checkable evidence or qualify/remove it."),
        dimension("semantics", "Semantics and accessibility", semantic_score,
                  f"main={bool(parser.tags['main'])}; lang={lang or 'missing'}; missing alt={len(missing_alt)}; generic links={len(generic_links)}.",
                  "Repair landmarks, heading order, link labels, language, and image alternatives without obscuring content."),
        dimension("schema", "Metadata and structured data", schema_score,
                  f"Canonical {'present' if canonical else 'missing'}; {len(parser.jsonld)} JSON-LD block(s); {parser.jsonld_errors} parse error(s).",
                  "Use only supported visible facts and validate syntax and provider-specific eligibility separately."),
        dimension("access", "Crawlable decision content", access_score,
                  f"robots={robots or 'unspecified'}; {len(text.split())} visible source words; {len(cta_labels)} action label(s).",
                  "Keep essential decision information in source text and verify rendered/source parity."),
        dimension("comparison", "Comparison support", comparison_score,
                  f"{parser.tags['table']} table(s), {parser.tags['th']} header cell(s).",
                  "If comparison affects the decision, use a sourced semantic table with stable dimensions.", comparison_applicable),
        dimension("faq", "Objection and FAQ coverage", faq_score,
                  f"{len(question_headings)} question-shaped headings; FAQPage schema {'present' if 'FAQPage' in types else 'absent'}.",
                  "Answer real objections visibly; do not add FAQ schema as a ranking or citation tactic.", faq_applicable),
        dimension("freshness", "Freshness integrity", freshness_score,
                  f"Visible time signal {'present' if freshness_signals else 'not detected'}; dateModified {'present' if date_modified else 'not detected'}.",
                  "Show an update date only after substantive review and keep structured dates consistent.", freshness_applicable),
    ]
    applicable = [item for item in dims if item["applicable"]]
    overall = round(sum(item["score"] for item in applicable) / len(applicable) * 10) if applicable else 0
    critical = []
    if "noindex" in robots:
        critical.append("The page declares noindex. Confirm whether public search visibility is intended before changing it.")
    if not h1s:
        critical.append("No primary H1 was detected in the source HTML.")
    elif len(h1s) > 1:
        critical.append(f"{len(h1s)} H1 elements were detected; clarify the page's primary heading.")
    if parser.jsonld_errors:
        critical.append(f"{parser.jsonld_errors} JSON-LD block(s) could not be parsed.")
    if missing_alt:
        critical.append(f"{len(missing_alt)} image(s) have no alt attribute; classify them as informative or decorative.")
    unsupported_faq = "FAQPage" in types
    if unsupported_faq:
        critical.append("FAQPage schema is present. Review whether it still serves a non-Google consumer; Google retired FAQ rich results in 2026.")

    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "overall": overall,
        "summary": {
            "title": titles[0] if titles else "Untitled page",
            "h1": h1s[0] if h1s else "",
            "opening": opening,
            "canonical": canonical,
            "schema_types": types,
            "visible_words": len(text.split()),
        },
        "dimensions": dims,
        "critical_issues": critical,
        "claims": claims,
        "inventory": {
            "headings": {"h1": h1s, "h2": h2s, "h3": h3s},
            "images": len(images), "missing_alt": missing_alt,
            "links": len(links), "external_links": len(external_links),
            "generic_link_labels": generic_links, "cta_labels": cta_labels,
        },
        "limits": [
            "Scores are heuristic observations, not predictions of ranking, indexing, conversion, or AI citation.",
            "The analyzer does not verify factual truth, evidence relevance, rendered JavaScript, robots.txt, link health, performance, or real search demand.",
            "Editorial and technical recommendations require review in the page's actual business and publishing context.",
        ],
    }


def render_markdown(report: dict) -> str:
    lines = [f"# Answer-ready audit: {report['summary']['title']}", "",
             f"**Directional score:** {report['overall']}/100", f"**Source:** `{report['source']}`", "",
             "## Dimensions", "", "| Dimension | Score | Status | Evidence |", "| --- | ---: | --- | --- |"]
    for item in report["dimensions"]:
        score = f"{item['score']}/10" if item["applicable"] else "N/A"
        lines.append(f"| {item['label']} | {score} | {item['status']} | {item['evidence']} |")
    lines.extend(["", "## Critical issues", ""])
    lines.extend([f"- {issue}" for issue in report["critical_issues"]] or ["- None detected by the deterministic checks."])
    lines.extend(["", "## Claim-readiness ledger", ""])
    if report["claims"]:
        for claim in report["claims"]:
            lines.extend([f"- **{claim['status']}** — {claim['claim']}", f"  - {claim['note']}"])
    else:
        lines.append("- No material claim patterns were detected; review the copy manually.")
    lines.extend(["", "## Limits", ""] + [f"- {item}" for item in report["limits"]])
    return "\n".join(lines) + "\n"


def render_html(report: dict) -> str:
    esc = lambda value: html.escape(str(value))
    dims = "".join(
        f'<article class="metric"><div><span>{esc(item["label"])}</span><strong>{item["score"] if item["applicable"] else "N/A"}</strong></div>'
        f'<div class="bar"><i style="width:{item["score"] * 10 if item["applicable"] else 0}%"></i></div>'
        f'<p>{esc(item["evidence"])}</p><small>{esc(item["recommendation"])}</small></article>'
        for item in report["dimensions"]
    )
    issues = "".join(f"<li>{esc(item)}</li>" for item in report["critical_issues"]) or "<li>No critical issue was detected by the deterministic checks.</li>"
    claims = "".join(
        f'<tr><td><span class="pill">{esc(item["status"])}</span></td><td>{esc(item["claim"])}</td><td>{esc(item["note"])}</td></tr>'
        for item in report["claims"]
    ) or '<tr><td colspan="3">No material claim pattern was detected. Review the copy manually.</td></tr>'
    limits = "".join(f"<li>{esc(item)}</li>" for item in report["limits"])
    data = esc(json.dumps(report, indent=2))
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Answer-ready audit · {esc(report['summary']['title'])}</title><style>
:root{{--ink:#17211b;--muted:#637067;--paper:#f5f6f1;--panel:#fff;--line:#d7ddd8;--green:#146c4b;--pale:#e3f0e8;--gold:#c7861c}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 Inter,system-ui,sans-serif}}header,main,footer{{width:min(1120px,calc(100% - 36px));margin:auto}}header{{padding:54px 0 34px;border-bottom:1px solid var(--line)}}.eyebrow{{color:var(--green);font:800 11px ui-monospace,monospace;letter-spacing:.14em;text-transform:uppercase}}h1{{max-width:850px;margin:13px 0 10px;font:600 clamp(2.6rem,7vw,5.6rem)/.96 Georgia,serif;letter-spacing:-.045em}}.lede{{max-width:760px;color:var(--muted);font-size:1.05rem}}.score{{display:flex;align-items:end;gap:12px;margin-top:30px}}.score strong{{font:700 4rem/1 Georgia,serif;color:var(--green)}}.score span{{padding-bottom:7px;color:var(--muted)}}section{{padding:38px 0;border-bottom:1px solid var(--line)}}h2{{font:600 2rem Georgia,serif}}.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}}.metric{{padding:20px;border:1px solid var(--line);border-radius:12px;background:var(--panel)}}.metric>div:first-child{{display:flex;justify-content:space-between;gap:14px}}.metric span{{font-weight:800}}.metric strong{{color:var(--green);font-size:1.3rem}}.bar{{height:6px;margin:14px 0;background:#edf0ec;border-radius:9px;overflow:hidden}}.bar i{{display:block;height:100%;background:var(--green)}}.metric p{{margin:0 0 9px;color:var(--muted)}}.metric small{{display:block;color:var(--green)}}.issues{{padding:18px 22px;background:#fff7e8;border-left:4px solid var(--gold)}}table{{width:100%;border-collapse:collapse;background:var(--panel)}}th,td{{padding:13px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}}th{{font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}}.pill{{display:inline-block;padding:3px 8px;border-radius:99px;background:var(--pale);color:var(--green);font-size:.7rem;font-weight:800}}details{{margin-top:20px}}pre{{max-height:440px;overflow:auto;padding:18px;background:#101713;color:#e8efe9;border-radius:10px;font-size:.75rem}}footer{{padding:26px 0 50px;color:var(--muted);font-size:.78rem}}@media(max-width:720px){{.grid{{grid-template-columns:1fr}}th:nth-child(3),td:nth-child(3){{display:none}}}}@media(prefers-reduced-motion:reduce){{*{{scroll-behavior:auto!important}}}}
</style></head><body><header><div class="eyebrow">Triuna Labs · Answer-ready observation</div><h1>{esc(report['summary']['title'])}</h1><p class="lede">{esc(report['summary']['h1'] or 'No primary heading detected.')}</p><div class="score"><strong>{report['overall']}</strong><span>/ 100 directional score<br>{esc(report['source'])}</span></div></header><main><section><h2>Readiness dimensions</h2><div class="grid">{dims}</div></section><section><h2>Critical review</h2><ul class="issues">{issues}</ul></section><section><h2>Claim-readiness ledger</h2><table><thead><tr><th>Status</th><th>Potential claim</th><th>Review note</th></tr></thead><tbody>{claims}</tbody></table></section><section><h2>Method limits</h2><ul>{limits}</ul><details><summary>Raw audit JSON</summary><pre>{data}</pre></details></section></main><footer>Generated {esc(report['generated_at'])}. Review findings in the page's business, user, and publishing context.</footer></body></html>'''


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit a landing page for answer, evidence, semantic, and technical signals.")
    parser.add_argument("source", help="Local HTML path or http(s) URL")
    parser.add_argument("--format", choices=("html", "markdown", "json"), default="html")
    parser.add_argument("--output", help="Output path; defaults to stdout for JSON/Markdown and <source>.answer-ready.html for local HTML")
    parser.add_argument("--timeout", type=int, default=15, help="URL timeout in seconds")
    args = parser.parse_args()
    try:
        document, resolved = load_source(args.source, args.timeout)
        report = analyze(resolved, document)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"audit failed: {error}", file=sys.stderr)
        return 2
    rendered = json.dumps(report, indent=2) + "\n" if args.format == "json" else render_markdown(report) if args.format == "markdown" else render_html(report)
    output = args.output
    if not output and args.format == "html":
        if args.source.startswith(("https://", "http://")):
            host = urlparse(args.source).netloc.replace(":", "-") or "page"
            output = f"{host}.answer-ready.html"
        else:
            output = str(Path(args.source).with_suffix(".answer-ready.html"))
    if output:
        path = Path(output).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
        print(path)
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
