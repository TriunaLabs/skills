---
name: laws-of-ux
description: "Review, compare, or constrain an interface using evidence-backed UX principles, and render an annotated teardown when useful. Use for decision load, target acquisition, grouping, expectations, complexity, feedback, progress, and endings; not for visual tokens, CSS architecture, or standalone WCAG conformance."
license: MIT
---

# Laws of UX — Review and annotated teardown

Apply a short list of named principles to a real surface. Default output is a findings list. Render the annotated poster only when the user asks for a teardown, poster, annotated page, or a review that looks like a callout sheet.

Laws are hypotheses, not evidence. Do not invent conversion lifts, timings, or user quotes. Do not cite every law on every screen.

## Decide the mode

- Findings list: review, audit, "why does this feel heavy", "where should the button go".
- Poster: "annotated page", "teardown", "poster", "callout sheet", or a request to render the review like a marked-up landing page.
- Guidance: user is about to build a menu, form, flow, or empty state. Constrain the design before layout. Skip the poster unless asked.
- Compare: review before and after evidence, preserving stable finding IDs and separating resolved, changed, new, and unchanged issues.
- Validate: check a findings file before rendering, comparing, or handing it to another workflow.

Not this skill: token values, type scales, BEM, component APIs, standalone WCAG conformance, protocol design. State the boundary and use an available specialist workflow only when the user requested that broader work.

Useful invocation patterns are `$laws-of-ux review ...`, `$laws-of-ux poster ...`, `$laws-of-ux design ...`, `$laws-of-ux focus ...`, `$laws-of-ux compare ...`, `$laws-of-ux prioritize ...`, `$laws-of-ux test-plan ...`, `$laws-of-ux validate ...`, and `$laws-of-ux handoff ...`. These are natural-language modes; the deterministic helpers expose matching validation, comparison, and rendering commands.

## Review workflow

1. Name the surface: menu, form, checkout, hero, pricing, settings, onboarding, error, empty state.
2. Take evidence from the URL, screenshot, markup, or the user's description. If a screenshot exists, use it as the poster plate. Do not invent a pixel replica of their brand.
3. Run the checklist below. Stop at the clusters that explain the problem. Read only those files in `references/`.
4. Write findings with evidence and verification. Cap at 12 on a poster, 8 in a list unless the user asks for the full pass.
5. One primary law per finding. If several laws describe the same issue, file one finding and name the law that dictates the fix. Mention a second law only when the fix differs.
6. Validate the findings JSON before rendering, comparison, or handoff.
7. For a poster, run the renderer and hand back the standalone HTML file.

## Checklist

| If you see | Primary law | Also check | Read |
|---|---|---|---|
| Long undifferentiated menu, pricing grid, or filter set | Hick's Law | Pareto, serial position, von Restorff | `references/decision.md` |
| More peer items than a chunk | Miller's Law | Proximity | `references/decision.md` |
| Small or far primary action, tight adjacent targets | Fitts's Law | Jakob, for expected placement | `references/motor.md` |
| Label far from its field, related controls scattered | Proximity | Similarity, common region, uniform connectedness | `references/gestalt.md` |
| Icon or diagram with more than one obvious reading | Prägnanz | Similarity | `references/gestalt.md` |
| One item must be remembered among peers | Von Restorff | Serial position | `references/expectation.md` |
| Novel nav, cart, or settings pattern | Jakob's Law | — | `references/expectation.md` |
| Input rejected for a format the user could not predict | Postel's Law | Tesler | `references/expectation.md` |
| Form or settings page that grew to fill the sprint | Parkinson's Law | Pareto, Occam | `references/complexity.md` |
| Extra steps that dump irreducible complexity on the user | Tesler's Law | Occam | `references/complexity.md` |
| Action with no acknowledgement within a few hundred ms | Doherty Threshold | Peak-end | `references/feedback.md` |
| Multi-step flow with no progress and a flat ending | Zeigarnik, Goal-Gradient | Peak-end | `references/feedback.md` |
| Happy path ends on a dead confirmation | Peak-End Rule | Zeigarnik | `references/feedback.md` |

"Minimize target distance" is the practical half of Fitts's Law, not a separate law. Cite Fitts.

## Finding shape

Each finding has a stable ID, surface and region, observable evidence, one primary principle, its mechanism, user impact, severity, confidence, a recommendation, and a verification step. Read [evidence and severity](references/evidence-and-severity.md) before assigning severity or confidence.

```
ux-001 · Hero actions — Hick's Law — high · 0.94
Observation: Four equal CTAs: Start free, Book demo, See pricing, Talk to sales.
Evidence: pricing-mobile.png#hero-actions
Recommendation: Keep one primary. Demote the rest to text links.
Verify: Only one action has primary visual weight at mobile and desktop widths.
```

Do not write "this violates Hick's Law" with no countable choice set. Do not write "users will convert more."

## Poster

Write schema-versioned JSON, validate it, then render it. Full details and a sample live in [the report schema](references/report-schema.md) and `assets/sample-findings.json`.

```json
{
  "schema_version": "2.0",
  "title": "Laws of UX Review",
  "subtitle": "Annotated findings for example.com/pricing",
  "source": {"type": "url", "ref": "https://example.com/pricing"},
  "findings": [
    {
      "id": "ux-001",
      "n": 1,
      "side": "left",
      "surface": "pricing page",
      "region": "hero actions",
      "observation": "Four equal hero CTAs compete for the first decision.",
      "evidence_ref": "pricing.png#hero-actions",
      "principle": "Hick's Law",
      "mechanism": "Equivalent choices increase decision complexity.",
      "severity": "high",
      "confidence": 0.94,
      "recommendation": "Keep one primary. Demote the rest to text links.",
      "verification": ["Only one hero action has primary visual weight."],
      "anchor": {"x": 0.5, "y": 0.28}
    }
  ]
}
```

`anchor` is a fraction of the browser plate, origin top-left. `side` is `left` or `right`. Alternate sides when omitted.

Run:

```bash
python scripts/validate_findings.py findings.json --poster
python scripts/render_review.py findings.json -o review.html
python scripts/render_review.py findings.json -o review.html --screenshot page.png
python scripts/compare_reviews.py before.json after.json -o comparison.json
```

The script embeds the screenshot and draws connector lines from each card to its anchor. Without a screenshot it draws a neutral wireframe. Open the HTML in a browser. Do not claim the wireframe is their page.

Cap poster cards at 14. Group overlaps before rendering. Card copy is the symptom; the fix is the green line. The law is the card title.

## Knowledge graph

Start at [the reference index](references/INDEX.md).

- `references/decision.md` — Hick, Miller, serial position, Pareto, Occam as a choice rule
- `references/motor.md` — Fitts and target distance
- `references/gestalt.md` — proximity, similarity, Prägnanz, uniform connectedness, common region
- `references/expectation.md` — Jakob, Postel, von Restorff
- `references/complexity.md` — Tesler, Parkinson, Occam
- `references/feedback.md` — Doherty, peak-end, Zeigarnik, goal-gradient
- `references/anti-patterns.md` — wrong citations
- `references/report-schema.md` — poster JSON
- `references/evidence-and-severity.md` — source types, severity, confidence, and verification
- `references/sources.md` — bibliographic and standards sources

## Cross-skill connections

This skill names the principle. Siblings own the implementation.

- Forms, validation copy, multi-step flows: use Postel, Tesler, Hick, and Zeigarnik here; route implementation to a form specialist when one is available and useful.
- Nav labels and wayfinding: use Jakob, serial position, Hick, and Miller here; route structural work to information architecture when available.
- Loading, empty, error, success: use Doherty, peak-end, and Zeigarnik here; measure actual latency with performance tooling.
- Touch size, contrast, names, keyboard: route conformance to accessibility review. Fitts explains acquisition; it does not replace WCAG.
- Tokens, type, color: do not load this skill.

## Common issues

| Problem | Fix |
|---|---|
| Poster cites 19 laws | Group. One card per issue. |
| Wireframe presented as the user's brand | Use their screenshot, or label the plate as a neutral wireframe. |
| Fitts cited for a copy problem | Move the finding to Hick, Jakob, or content. |
| Law stated as a measured result | Delete the number. Keep the mechanism. |
| Postel used to excuse a sloppy API response | Postel applies to input acceptance. Output stays strict. |
