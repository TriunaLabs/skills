#!/usr/bin/env python3
"""Generate a deterministic interface design system and standalone specimen."""
from __future__ import annotations
import argparse, html, json, re
from datetime import datetime, timezone
from pathlib import Path
from design_model import contrast, validate_system

PROFILES = {
 "precision": {"keywords":{"operations","dashboard","technical","precise","credible","developer","finance","analytics"},"mood":"Measured, calm, information-forward","primary":"#176B54","bg":"#F4F3ED","surface":"#FFFDF8","alt":"#E8EEE8","text":"#172A24","muted":"#52645D","border":"#CBD5CE","display":"'Source Serif 4', Georgia, serif","body":"Inter, 'Segoe UI', Arial, sans-serif","radius":"10px"},
 "editorial": {"keywords":{"editorial","consulting","research","thoughtful","premium","writing","portfolio"},"mood":"Editorial, assured, spacious","primary":"#59459A","bg":"#F7F3EA","surface":"#FFFCF6","alt":"#ECE6F6","text":"#261F31","muted":"#655D70","border":"#D8D0DD","display":"'Source Serif 4', Georgia, serif","body":"Manrope, 'Segoe UI', Arial, sans-serif","radius":"6px"},
 "warm": {"keywords":{"community","education","hospitality","warm","human","friendly","wellness"},"mood":"Warm, approachable, grounded","primary":"#96502F","bg":"#FAF4E8","surface":"#FFFDF8","alt":"#F4E3CF","text":"#33251E","muted":"#6C5B52","border":"#DECFC0","display":"Fraunces, Georgia, serif","body":"'DM Sans', 'Segoe UI', Arial, sans-serif","radius":"16px"},
 "civic": {"keywords":{"healthcare","government","civic","trustworthy","accessible","institutional","service"},"mood":"Clear, dependable, restrained","primary":"#155E75","bg":"#F1F5F4","surface":"#FFFFFF","alt":"#DDECEF","text":"#173039","muted":"#52666D","border":"#C5D3D6","display":"'IBM Plex Sans', 'Segoe UI', Arial, sans-serif","body":"'IBM Plex Sans', 'Segoe UI', Arial, sans-serif","radius":"8px"}
}

def slug(value: str) -> str: return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "interface-system"
def choose_profile(brief: dict) -> tuple[str, dict, list[dict]]:
    corpus = " ".join([str(brief.get("product_type", "")), str(brief.get("audience", "")), " ".join(brief.get("tone", [])), " ".join(brief.get("primary_tasks", []))]).lower()
    scored = []
    for name, profile in PROFILES.items():
        matches = sorted(word for word in profile["keywords"] if word in corpus); scored.append({"label":name,"score":len(matches),"evidence":matches})
    scored.sort(key=lambda item: (-item["score"], item["label"])); selected = scored[0]["label"] if scored[0]["score"] else "precision"
    return selected, PROFILES[selected], scored

def build(brief: dict) -> dict:
    name = str(brief.get("name") or "Untitled interface")
    selected, profile, scores = choose_profile(brief)
    brand = brief.get("brand") if isinstance(brief.get("brand"), dict) else {}
    primary = brand.get("primary", profile["primary"])
    primary_text = "#FFFFFF" if contrast(primary, "#FFFFFF") >= 4.5 else "#111111"
    density = brief.get("density") if brief.get("density") in {"compact","balanced","spacious"} else "balanced"
    space = {"compact":[4,8,12,16,24,32],"balanced":[4,8,12,16,24,32,48,64],"spacious":[6,12,18,24,36,54,72,96]}[density]
    roles = {"background":profile["bg"],"surface":profile["surface"],"surface_alt":profile["alt"],"text":profile["text"],"text_muted":profile["muted"],"border":profile["border"],"primary":primary,"primary_text":primary_text,"danger":"#A23B32","danger_text":"#FFFFFF","success":"#26734D","focus":"#C56B12"}
    assumptions = []
    for key, message in (("audience","Audience was not supplied; general professional users assumed."),("primary_tasks","Primary tasks were not supplied; common browse, inspect, and act tasks assumed."),("tone","Tone was not supplied; the selected direction uses a restrained default.")):
        if not brief.get(key): assumptions.append(message)
    prompt = f"""Use {name}'s design-system.json as the source of truth. Load page-specific overrides only when they explicitly exist. Use semantic tokens instead of raw color or spacing values. Preserve the {selected} direction, {density} density, documented type roles, component states, and responsive behaviors. Do not invent new token families or use color as the only carrier of meaning. Keep focus-visible states, error text, loading labels, and reduced-motion behavior. Before handoff, validate contrast pairs, keyboard order, target size, text wrapping, empty/error/loading/success states, and narrow/wide layouts. Record any necessary exception with its component, reason, and replacement plan."""
    system = {
      "schema_version":"1.0","name":name,"generated_at":datetime.now(timezone.utc).isoformat(),"brief":brief,"assumptions":assumptions,
      "direction":{"label":selected,"atmosphere":profile["mood"],"density":density,"selection":{"method":"deterministic keyword scoring","candidates":scores},"rationale":f"Selected {selected} from the supplied product, audience, tasks, and tone; supplied brand roles override profile defaults."},
      "color":{"roles":roles,"contrast_pairs":[{"foreground":"text","background":"background","minimum":4.5},{"foreground":"text","background":"surface","minimum":4.5},{"foreground":"text_muted","background":"surface","minimum":4.5},{"foreground":"primary_text","background":"primary","minimum":4.5},{"foreground":"danger_text","background":"danger","minimum":4.5}]},
      "typography":{"families":{"display":profile["display"],"heading":profile["body"],"body":profile["body"],"mono":"'SFMono-Regular', Consolas, monospace"},"scale":{"xs":"0.75rem","sm":"0.875rem","base":"1rem","lg":"1.25rem","xl":"1.625rem","2xl":"2.25rem","3xl":"3.25rem"},"rules":["Body line length: 55–75 characters.","Use sentence case for labels and headings.","Remote fonts are optional; system fallbacks must preserve hierarchy."]},
      "components":{key:{"states":["default","hover","active","focus-visible","disabled","loading","error","success"],"rule":rule} for key,rule in {"button":"One primary action per decision region; destructive actions are visually distinct.","input":"Persistent label, visible focus, nearby help or error text, and tolerant input where possible.","card":"Use for one coherent group; avoid nesting cards for decoration.","navigation":"Use familiar labels, indicate current location, and preserve keyboard order."}.items()},
      "layout":{"spacing_px":space,"content_max_px":1180,"grid":{"wide":"12 columns","medium":"8 columns","narrow":"4 columns"},"radius":profile["radius"],"rules":["Use spacing tokens only.","Group by proximity before adding a border.","Keep primary task content in the first reading region."]},
      "elevation":{"none":"none","raised":"0 8px 24px rgba(23,42,36,.08)","overlay":"0 18px 50px rgba(23,42,36,.18)","rules":["Raised means independently actionable.","Overlay is reserved for temporary layers.","Do not stack shadows for decoration."]},
      "guardrails":{"do":["Use semantic tokens and documented states.","Keep one dominant action per decision region.","Show status with text or icon as well as color.","Test keyboard, zoom, narrow width, and reduced motion."],"dont":["Do not invent gradients or decorative glass effects.","Do not use placeholder text as the only label.","Do not hide essential actions on hover.","Do not add a new token for a one-off visual preference."]},
      "responsive":[{"condition":"below 720px","behavior":"Collapse navigation into an explicitly labeled menu; stack split layouts; keep actions full width only when the group remains clear."},{"condition":"720px to 1023px","behavior":"Use the 8-column grid; allow tables to scroll inside a labeled region rather than clipping."},{"condition":"1024px and wider","behavior":"Use the 12-column grid and cap reading width; do not stretch text to fill the viewport."},{"condition":"pointer coarse","behavior":"Use at least 44px preferred interactive targets and sufficient separation."},{"condition":"prefers-reduced-motion","behavior":"Remove nonessential transforms and preserve immediate semantic state changes."}],
      "agent_prompt":prompt,"provenance":{domain:"recommended" for domain in ["direction","color","typography","components","layout","elevation","guardrails","responsive"]}
    }
    return system

def css(system: dict) -> str:
    roles, layout, typography = system["color"]["roles"], system["layout"], system["typography"]
    lines = [":root {"] + [f"  --color-{k.replace('_','-')}: {v};" for k,v in roles.items()]
    lines += [f"  --space-{i+1}: {v}px;" for i,v in enumerate(layout["spacing_px"])]
    lines += [f"  --font-{k}: {v};" for k,v in typography["families"].items()]
    lines += [f"  --text-{k}: {v};" for k,v in typography["scale"].items()]
    lines += [f"  --radius: {layout['radius']};",f"  --shadow-raised: {system['elevation']['raised']};",f"  --shadow-overlay: {system['elevation']['overlay']};","}"]
    return "\n".join(lines) + "\n"

def dtcg_tokens(system: dict) -> dict:
    roles = system["color"]["roles"]
    spaces = system["layout"]["spacing_px"]
    return {"$schema":"https://www.designtokens.org/schemas/2025.10/format.json",
      "color":{"$type":"color", **{k:{"$value":v,"$description":f"Semantic {k.replace('_',' ')} role."} for k,v in roles.items()}},
      "space":{"$type":"dimension", **{str(i+1):{"$value":{"value":v,"unit":"px"}} for i,v in enumerate(spaces)}},
      "font":{"$type":"fontFamily", **{k:{"$value":[part.strip().strip("'") for part in v.split(',')]} for k,v in system["typography"]["families"].items()}},
      "radius":{"$type":"dimension","control":{"$value":{"value":float(system["layout"]["radius"].replace("px","")),"unit":"px"}}},
      "shadow":{"$type":"shadow","raised":{"$value":{"color":"#172A2414","offsetX":{"value":0,"unit":"px"},"offsetY":{"value":8,"unit":"px"},"blur":{"value":24,"unit":"px"},"spread":{"value":0,"unit":"px"}}}}}

def guide(system: dict) -> str:
    d, c = system["direction"], system["color"]["roles"]
    return f"""# {system['name']} interface design system

## Direction

**{d['label'].title()}** — {d['atmosphere']}. Density: **{d['density']}**.

## Semantic color roles

| Role | Value |
|---|---|
{chr(10).join(f'| `{k}` | `{v}` |' for k,v in c.items())}

## Typography

- Display: `{system['typography']['families']['display']}`
- Heading and body: `{system['typography']['families']['body']}`
- Scale: {', '.join(system['typography']['scale'].values())}

## Layout and elevation

- Spacing: {', '.join(str(v) + 'px' for v in system['layout']['spacing_px'])}
- Grid: {system['layout']['grid']['narrow']} narrow, {system['layout']['grid']['medium']} medium, {system['layout']['grid']['wide']} wide
- Raised surface: `{system['elevation']['raised']}`
- Overlay: `{system['elevation']['overlay']}`

## Do
{chr(10).join('- ' + item for item in system['guardrails']['do'])}

## Don't
{chr(10).join('- ' + item for item in system['guardrails']['dont'])}

## Responsive behavior
{chr(10).join('- **' + item['condition'] + ':** ' + item['behavior'] for item in system['responsive'])}
"""

def specimen(system: dict, tokens: str) -> str:
    name, direction = html.escape(system["name"]), system["direction"]
    swatches = "".join(f'<li><i style="background:{v}"></i><b>{html.escape(k)}</b><code>{v}</code></li>' for k,v in system["color"]["roles"].items())
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{name} · Interface system</title><style>{tokens}
*{{box-sizing:border-box}}body{{margin:0;background:var(--color-background);color:var(--color-text);font:16px/1.55 var(--font-body)}}a{{color:var(--color-primary)}}:focus-visible{{outline:3px solid var(--color-focus);outline-offset:3px}}.shell{{max-width:1180px;margin:auto;padding:24px}}header{{display:flex;align-items:center;justify-content:space-between;gap:24px;padding:14px 0;border-bottom:1px solid var(--color-border)}}nav{{display:flex;gap:22px}}nav a,.mobile-nav a{{color:var(--color-text);text-decoration:none;font-weight:650}}.mobile-nav{{display:none}}.badge{{font:700 11px var(--font-mono);letter-spacing:.08em;color:var(--color-primary)}}h1{{font:500 clamp(2.4rem,7vw,var(--text-3xl))/1.02 var(--font-display);max-width:14ch;margin:.35em 0}}h2{{font-size:var(--text-xl);margin:0 0 18px}}.hero{{padding:72px 0 48px;display:grid;grid-template-columns:1.35fr .65fr;gap:48px;align-items:end}}.lede{{font-size:var(--text-lg);max-width:58ch;color:var(--color-text-muted)}}button,.button{{min-height:44px;border:0;border-radius:var(--radius);padding:0 18px;background:var(--color-primary);color:var(--color-primary-text);font-weight:750;cursor:pointer}}button.secondary{{background:transparent;color:var(--color-text);border:1px solid var(--color-border)}}button:disabled{{opacity:.5;cursor:not-allowed}}.actions{{display:flex;gap:10px;flex-wrap:wrap}}section{{padding:42px 0;border-top:1px solid var(--color-border)}}.meta{{color:var(--color-text-muted)}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}}.card{{background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:22px;box-shadow:var(--shadow-raised)}}.card strong{{display:block;font-size:var(--text-lg)}}.status{{display:inline-flex;gap:7px;align-items:center;font-weight:700;color:var(--color-success)}}.status:before{{content:'✓';display:grid;place-items:center;width:20px;height:20px;border-radius:50%;background:var(--color-success);color:white}}.swatches{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;list-style:none;padding:0}}.swatches li{{display:grid;grid-template-columns:42px 1fr;gap:3px 10px;align-items:center;background:var(--color-surface);border:1px solid var(--color-border);padding:10px;border-radius:var(--radius)}}.swatches i{{grid-row:1/3;width:42px;height:42px;border-radius:8px;border:1px solid var(--color-border)}}.swatches code{{font-size:11px;color:var(--color-text-muted)}}label{{display:grid;gap:6px;font-weight:700}}input{{min-height:44px;border:1px solid var(--color-border);background:var(--color-surface);color:var(--color-text);border-radius:var(--radius);padding:0 12px;font:inherit}}.field-help{{font-size:13px;color:var(--color-text-muted)}}.error input{{border-color:var(--color-danger)}}.error .field-help{{color:var(--color-danger)}}.component-row{{display:flex;align-items:end;gap:14px;flex-wrap:wrap}}footer{{padding:36px 0;color:var(--color-text-muted)}}@media(max-width:760px){{.hero,.grid{{grid-template-columns:1fr}}nav{{display:none}}.mobile-nav{{display:block;position:relative}}.mobile-nav summary{{cursor:pointer;min-height:44px;display:grid;place-items:center;font-weight:700}}.mobile-nav div{{position:absolute;right:0;top:48px;display:grid;gap:12px;min-width:170px;padding:16px;background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);box-shadow:var(--shadow-overlay);z-index:2}}.swatches{{grid-template-columns:1fr 1fr}}.hero{{padding-top:44px}}}}@media(max-width:460px){{.swatches{{grid-template-columns:1fr}}.actions button{{width:100%}}}}@media(prefers-reduced-motion:no-preference){{button{{transition:transform .15s,filter .15s}}button:hover{{filter:brightness(.92)}}button:active{{transform:translateY(1px)}}}}@media print{{nav,.mobile-nav,.actions{{display:none}}body{{background:white}}.card{{box-shadow:none}}}}
</style></head><body><div class="shell"><header><b>{name}</b><nav aria-label="Specimen"><a href="#foundation">Foundation</a><a href="#components">Components</a><a href="#rules">Rules</a></nav><details class="mobile-nav"><summary>Menu</summary><div><a href="#foundation">Foundation</a><a href="#components">Components</a><a href="#rules">Rules</a></div></details></header><main><div class="hero"><div><span class="badge">{html.escape(direction['label'].upper())} · {html.escape(direction['density'].upper())}</span><h1>A system for clear, confident action.</h1><p class="lede">{html.escape(direction['atmosphere'])}. This specimen makes the design contract visible before a team commits it to product code.</p></div><div class="actions"><button>Review system</button><button class="secondary">Export tokens</button></div></div><section><div class="grid"><article class="card"><span class="badge">SIGNAL</span><strong>Service health</strong><p class="meta">Semantic status combines language, icon, and color.</p><span class="status">Operating normally</span></article><article class="card"><span class="badge">DECISION</span><strong>One next action</strong><p class="meta">Primary emphasis is reserved for the decision that advances the task.</p><button>Inspect exception</button></article><article class="card"><span class="badge">EVIDENCE</span><strong>Documented contract</strong><p class="meta">Tokens, states, behaviors, and exceptions remain inspectable.</p><a href="#rules">Read guardrails</a></article></div></section><section id="foundation"><span class="badge">01 · FOUNDATION</span><h2>Semantic color roles</h2><ul class="swatches">{swatches}</ul></section><section id="components"><span class="badge">02 · COMPONENTS</span><h2>States that communicate</h2><div class="component-row"><button>Default action</button><button class="secondary">Secondary</button><button disabled>Unavailable</button><button aria-busy="true">Loading…</button><label>Workspace name<input value="Northstar"><span class="field-help">Visible help stays attached to the field.</span></label><label class="error">Deployment region<input aria-invalid="true" value=""><span class="field-help">Select a supported region.</span></label></div></section><section id="rules"><span class="badge">03 · AGENT CONTRACT</span><h2>Generate within the system</h2><div class="grid"><article class="card"><strong>Use roles</strong><p>Apply semantic tokens and the documented component states.</p></article><article class="card"><strong>Preserve meaning</strong><p>Never rely on color alone or hide essential actions on hover.</p></article><article class="card"><strong>Verify behavior</strong><p>Check keyboard order, wrapping, responsive reflow, and reduced motion.</p></article></div></section></main><footer>Generated locally · schema 1.0 · no external assets required</footer></div></body></html>'''

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an interface design system")
    parser.add_argument("brief"); parser.add_argument("--out", required=True)
    args = parser.parse_args(); brief = json.loads(Path(args.brief).read_text(encoding="utf-8"))
    if not isinstance(brief, dict): raise SystemExit("brief must be a JSON object")
    system = build(brief); errors = validate_system(system)
    if errors: raise SystemExit("Generated invalid system:\n- " + "\n- ".join(errors))
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True); tokens = css(system)
    (out / "design-system.json").write_text(json.dumps(system, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "tokens.json").write_text(json.dumps(dtcg_tokens(system), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "tokens.css").write_text(tokens, encoding="utf-8")
    (out / "DESIGN-GUIDE.md").write_text(guide(system), encoding="utf-8")
    (out / "agent-prompt.md").write_text("# Agent prompt\n\n" + system["agent_prompt"] + "\n", encoding="utf-8")
    (out / "specimen.html").write_text(specimen(system, tokens), encoding="utf-8")
    print(f"wrote {out} ({system['direction']['label']} direction)")
if __name__ == "__main__": main()
