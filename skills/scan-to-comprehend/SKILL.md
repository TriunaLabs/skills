---
name: scan-to-comprehend
description: "Design or review information-dense websites, articles, and infographics for fast orientation and accurate understanding. Use when readers must scan, find a fact, and then comprehend its context; not for predicting eye movements or assigning a comprehension score."
license: MIT
---

# Scan to Comprehend (S2C)

Help a reader answer three questions in order: **What is this about? Where is the part I need? What does that part mean?** Preserve the information needed to answer the real task. Treat scan patterns as observations that inform design choices, not mandatory paths that every reader follows.

## Use the appropriate path

- **Create or revise:** identify the audience's task, the key facts, and what evidence or caveats must remain. Draft an information hierarchy, then produce the requested website, article, or infographic in the user's medium and design system.
- **Review:** inspect the supplied page, source, image, or URL at its actual viewport or dimensions. Report observable barriers, the likely task impact, a concrete revision, and how to verify it. Distinguish visible evidence from inference.
- **Structural preflight:** for HTML or Markdown, optionally run `python scripts/s2c_audit.py PATH` or `python scripts/s2c_audit.py --url https://example.com/page`. The audit reports markup signals and review prompts. It cannot observe gaze, measure comprehension, inspect a rendered responsive layout, or prove accessibility. Use `--json` for machine-readable output. URL mode needs network access and should be used only for a URL the user has authorized you to fetch.

Read [surface guidance](references/surfaces.md) for the requested medium. Read [evidence and limits](references/evidence.md) before making a research or performance claim. The [Triuna Labs card specimen](assets/triuna-spotted-card.html) is an optional branded example, not a required style for other brands.

## Core decisions

1. **Start with the question.** Place an accurate, specific title and a concise answer or overview where a new reader can orient. State units, timeframe, population, and source next to consequential numbers.
2. **Make the outline useful on its own.** Use descriptive, non-repeating headings and labels. Group related facts; let a reader jump to the right section and then read it in depth. Avoid heading levels chosen merely for visual size.
3. **Give details a clear home.** Prefer short paragraphs, meaningful lists, direct labels, tables for true comparisons, and captions for visual evidence. Use bold only where it identifies a meaningful distinction. Preserve nuance, definitions, and exceptions instead of compressing them away.
4. **Connect visuals to meaning.** Place explanations next to the chart, diagram, or metric they explain. Use a visible sequence when order matters. Never rely on color, animation, or an implied gaze path alone to carry meaning.
5. **Check multiple reading routes.** Can someone understand the overview in a quick scan, find a specific fact, and read the supporting detail? Review desktop and mobile layouts, keyboard and screen-reader order where applicable, and the plain-text or alt-text path for an infographic.
6. **Validate with people when outcomes matter.** Ask representative readers to find a fact and explain it in their own words. Record task, success criterion, and observations before claiming faster understanding or better comprehension.

Do not turn the source material's “comprehension-to-ink ratio,” F-pattern risk percentages, bounce estimates, 80/100 score, or fixed word and sentence limits into measurements. No such values are validated by this skill. Do not claim a layout forces a fixation or that an automated check predicts reader behavior.

## Deliverable

Return the edited artifact or a prioritized review. For a review, include the reader task, surface and viewport, up to the most consequential findings, specific changes, and a verification step for each. State which claims came from observation, research, or a proposed hypothesis.

The optional [pre-commit hook](integrations/pre-commit) can check staged HTML and Markdown for structural warnings. It is opt-in and does not impose a numerical quality gate. Install it only when asked, after reviewing repository policy and existing hooks.
