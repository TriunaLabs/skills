---
name: scan-to-comprehend
description: "Design or audit information-dense websites, articles, and infographics using task-aware scanning patterns. Includes a source preflight, visual walkthrough, assistive reading view, and experimental attention heatmap; does not measure gaze or comprehension."
license: MIT
---

# Scan to Comprehend (S2C)

Build a route from **orientation → finding the relevant part → understanding it in context**. S2C applies eye-tracking observations to content and layout decisions. A scanpath is a sequence of fixations connected by rapid eye movements (saccades); a diagram of a possible path is a design hypothesis, not an instruction that human eyes will obey.

The source concept names an F-pattern shield, layer-cake grid, spotted intercept, and lawn-mower track. Use those as memorable design moves, with the more precise definitions and limits in [the pattern map](references/patterns.md). NN/g also describes commitment reading, bypassing, zigzag behavior, and other patterns. Readers can switch patterns as their task changes.

## Route the work

1. **Frame the reader task.** Identify the audience, the question they need answered, whether they are browsing, locating a known fact, comparing options, or studying, and the surface, viewport, language direction, and source material. List facts, caveats, and evidence that must survive compression.
2. **Map content before styling.** Make a compact inventory: each module's question, one-sentence answer, supporting detail, source, priority, and relationship to adjacent modules. Mark what can be skimmed and what requires close reading. See the [S2C blueprint](references/blueprints.md) for a reusable schema and worked Triuna Labs example.
3. **Choose a likely scan route.** Use the [pattern map](references/patterns.md): support an F-like first pass through prose; use descriptive headings for layer-cake scanning; make task-relevant anchors findable for spotted scanning; keep labels and cells legible during comparison-table lawn-mower scanning. Consider bypassing and commitment reading. Treat decorative zigzag alternation cautiously.
4. **Design the three passes.** The title and summary orient. Headings, labels, links, numbers, and consistent groups enable targeted finding. Prose, definitions, data labels, sources, and caveats support a close read. Do not remove needed complexity merely to make the first pass short.
5. **Build the requested artifact.** Read [surface guidance](references/surfaces.md) for website, article, or infographic decisions. Respect the existing brand and medium. Do not force arrows, asymmetry, visual jolts, or bold prefixes into every module.
6. **Verify the result.** Inspect rendered desktop and mobile views, reading and keyboard order, and text alternatives where relevant. Run a quick-scan, find-a-fact, and explain-the-answer task with representative readers when the outcome matters. Use [evaluation guidance](references/evaluation.md). Cite observations separately from hypotheses and measured outcomes.

## Optional structural preflight

For HTML or Markdown, run `python scripts/s2c_audit.py PATH`, `python scripts/s2c_audit.py --url https://example.com/page`, or `python scripts/s2c_audit.py --staged`. Use `--json` for machine-readable findings, narrow strengths, proactive suggestions, and an **experimental structural friction risk index**. Read the [audit contract](references/audit-engine.md) before interpreting or integrating the score. URL mode needs network access and an authorized public URL. The source parser cannot identify an actual gaze pattern, inspect visual contrast or responsive layout, measure cognitive load or comprehension, or prove accessibility.

When a user gives a URL for a visual audit, follow the [rendered-page walkthrough](references/visual-report.md): capture the actual page at a stated viewport and audit date, record evidence-linked callouts in an artificial report margin, and render a self-contained HTML report with `s2c_visualize.py`. A JSON-only source preflight can use `python scripts/s2c_visualize.py audit.json --output audit.html`. Neither report draws a predicted gaze path or presents the risk index as measured cognitive load. Keep rendered-page observations and reader-task results separate from automatic findings.

For a browser-reported accessibility-tree path, observed Tab order, and 320 px reflow review, follow the [assistive reading view](references/assistive-view.md). Its Chromium capture is reusable across S2C projections. Show keyboard and reading order separately, preserve unmapped text in the list, and label target size, names, alternatives, and clipping as review candidates. This is not a screen-reader recording or WCAG conformance audit.

When the user asks to apply the AGD visual-attention paper to a particular page, use the [AGD-to-audit guide](references/agd-to-audit.md). Capture the task and viewport, inspect competing components, and write each finding as observed feature → attention hypothesis → proposed change → disconfirming check. AGD's free-viewing results do not establish task success or supply coefficients for the S2C heatmap.

When the user asks for an estimated attention heatmap, use the [experimental attention baseline](references/attention-baseline.md) with a real viewport screenshot and reviewed element boxes. It produces a separate, untrained heuristic layer labeled **estimated visual attention** and a separately labeled WCAG 2.2 text contrast spot check where solid colors and font metrics are supplied. Do not describe heatmap colors as fixation probability, gaze, dwell, task success, or comprehension. A contrast threshold is not a gaze prediction threshold; the heatmap uses contrast continuously as an unvalidated feature. A held-out UEyes evaluation has been run: the fixed S2C map trailed a Train-fitted position-only map on 27 held-out webpages at 3 seconds (NSS 0.506 versus 1.148). See [the evaluation result](references/attention-baseline.md) before making predictive claims. Treat screenshot-derived contrast as indicative, not a WCAG conformance finding.

The [optional pre-commit hook](integrations/pre-commit) runs that structural preflight on staged content. Review existing hooks before installing it. The [Triuna Labs card specimen](assets/triuna-spotted-card.html) is a branded example only.

On a page the user controls, the optional [section interaction probe](references/interaction-signals.md) can add observed viewport exposure, mouse hover, click, and tap counts to the HTML report. It must be started explicitly after the host page's notice or consent step. Keep its session exports separate from gaze predictions and reader-task outcomes; it uses no camera and sends no data by default.

## Research boundary

Read [evidence and models](references/evidence.md) before explaining the science or proposing eye-tracking tools. The infographic studies motivate checking text–graphic integration but do not define universal layout distances or score coefficients. AGD predicts attention for free viewing of graphic documents; ScanTextGAN generates text scanpaths for NLP tasks; a reading tracker and WebEyeTrack address different measurement problems. Camera-based gaze tracking is outside the S2C page-audit workflow. None is an S2C optimizer or evidence that a particular layout improves comprehension. Do not substitute saliency or the source-only risk index for understanding.

For requests to derive calibrated element-level attention estimates from gaze datasets, follow the [element-attention research track](references/element-attention-research.md). It defines a reproducible dataset join, task-specific validation, and a possible report contract. The heuristic baseline above is implemented but untrained; the public audit must not emit fixation probabilities, dwell estimates, or synthetic scanpaths from these rules.

The source material's “comprehension-to-ink ratio,” F-pattern risk percentages, bounce estimates, fixed word or sentence limits, “zero-baseline disruption,” and 80/100 threshold are not validated measures. If an alignment break or high-contrast anchor seems useful, describe it as a design choice and test whether it helps the stated task. Do not claim that a layout forces a fixation.

## Deliverable

Return the artifact or a prioritized review with the reader task, content map, pattern hypotheses, specific changes, and verification results or next test. For each review finding, separate **observed feature → likely task effect → proposed change → check**. Say when an effect remains untested.
