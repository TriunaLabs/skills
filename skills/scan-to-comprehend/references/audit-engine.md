# Source audit and automation contract

`scripts/s2c_audit.py` is the open, dependency-free preflight for HTML and Markdown. It accepts a local file, an explicitly supplied public HTML URL, or staged Git blobs. `--json` returns a stable wrapper with `schema_version` and `reports`; each report includes findings, strengths, suggestions, and `estimated_cognitive_load`.

## Interpret the estimate

The numeric field is an **experimental structural friction risk index**, 0–100, where higher means more flagged source-structure issues. It is a triage order for reviewing *the same kind of input with the same heuristic version*. It is not a cognitive-load measurement, probability of confusion, predicted gaze sequence, accessibility grade, or comprehension score. A zero means that this short source checklist found no issue; it does not certify an easy page. Confidence is always `low` in this version.

The `s2c-source-heuristic-v1` weights are editorial and intentionally visible in the script: absent outline 22, missing page-level heading 12, empty heading 12, heading-level jump 8, missing image alternative 10 per image capped at 20, table without any header cells 12, and a generic link label 8. An absent outline is not charged again for a missing H1. These weights are **not derived from the cited studies**. Keep method versions when changing them, and do not compare scores across versions without recalculating the same source.

The findings identify source evidence. Strengths are narrow positive observations (for example, all source images have an `alt` attribute), with quality still subject to review. Suggestions respond to the flagged weakness. `next_checks` lists work the source parser cannot do: inspect rendered desktop/mobile layout and ask readers to find and explain an answer.

Example command:

```sh
python scripts/s2c_audit.py page.html --json > audit.json
python scripts/s2c_visualize.py audit.json --output audit.html
```

The CLI records its local run date as top-level `audited_on` in JSON and prints it in text mode. The optional HTML report displays that date beside the title and visualizes the existing JSON rather than adding new measurements. Its heading map reflects source order; the three reader questions and next checks are prompts for a rendered and reader review, not automatic pass/fail results. Preserve the JSON alongside the HTML when the report is shared so each displayed claim remains inspectable.

For a public URL case study with actual page captures and reviewer callouts, use the [rendered-page walkthrough](visual-report.md). Its visual observations are a separate evidence layer and do not change the source-only index.

An API or MCP wrapper can invoke this same command with a bounded input and return the JSON object. Preserve `schema_version`, `method`, source label, score caveat, strengths, findings, suggestions, and next checks. Do not send private pages to a third-party service by default. The CLI's URL mode refuses redirects, non-public IP addresses, credentials in URLs, non-HTML responses, and responses over 2 MB; an exposed service also needs request authentication, rate limits, outbound network controls, and its own SSRF review.

## Further evidence layers

1. **Rendered webpage:** capture desktop and mobile screenshots plus DOM bounds and computed styles. Link each graphic to its actual caption/key before evaluating their proximity; report the viewport and the relation rather than a universal pixel threshold. Check visual density, contrast, overlap, reading order, and table-label persistence separately. Static HTML alone cannot observe these.
2. **Infographic:** accept a raster or SVG plus text equivalent and source data. Identify visual groups, legends, units, labels, and the claim each graphic supports. A reviewer confirms the pairings. The Majooni and Wu/Liu studies motivate testing text–graphic integration; they do not provide plug-in weights for arbitrary graphics.
3. **Short-form video:** sample frames and transcript at declared time points, then inspect text timing, legibility, scene changes, and claim-to-visual alignment. This is a proposed extension requiring a separate evidence base and human testing. Do not apply webpage scanpath findings as a video score.
4. **Validation:** before making a cognitive-load prediction, collect consented reader-task outcomes and, if appropriate, calibrated gaze/pupillometry on representative material. Pre-register the outcome, compare the index with a baseline, assess calibration and group/device differences, and report failures. Until then, call it a source-structure risk estimate.

For a production application, keep the open CLI and JSON contract separate from the hosted intake, rendering workers, user accounts, storage, billing, and private reports. That boundary makes each layer testable and avoids presenting a paid interface as the source of scientific validity.
