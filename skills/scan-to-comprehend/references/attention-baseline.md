# Experimental attention baseline

Use this mode only when a user asks for a **visual attention estimate** on a rendered page. It is an untrained rule baseline, not predictive eye tracking. It requires a viewport screenshot and element boxes. The optional DevTools snippet `scripts/s2c_capture.js` exports visible DOM boxes, font sizes and weights, and solid CSS foreground/background colors on a page the user may inspect. Save a matching viewport screenshot as `screenshot.png` beside the downloaded `s2c-capture.json`; edit the screenshot filename in JSON if needed. The script sends no data. Review its boxes before analysis; nested text, gradients, images, overlays, and cropped regions need human correction. Add a `face` element only if a face was explicitly annotated; the snippet does not detect faces.

For an automated browser capture, use [the assistive reading view](assistive-view.md) and `s2c_browser_to_attention.py` to project its shared snapshot into this input schema. That projection is repeatable but still needs a box and color review, particularly for text over images or overlays.

```bash
python scripts/s2c_attention.py render s2c-capture.json
python scripts/s2c_visualize.py audit.json --attention attention.json --output report.html
```

`render` writes a transparent PNG for each viewport plus `attention.json` in the capture folder. The report embeds the screenshot and overlay and offers a visible on/off control. The capture format is `s2c-attention-capture/v1` with `frames[]`; each frame has `id`, `image`, optional `coordinate_width`/`coordinate_height` for CSS pixel scaling, optional `color_basis` provenance, and `elements[]`. Each element needs `kind`, `x`, `y`, `width`, `height` in capture coordinates; optional fields are `id`, `label`, `font_px`, `font_weight`, `foreground`, and `background`. Kinds: `heading`, `text`, `button`, `link`, `image`, `logo`, `face`, `icon`. Colors are solid `#RGB` or `#RRGGBB`. Leave color fields absent when the actual background is unknown. The renderer requires images in the same directory tree and embeds them in the HTML.

## Rule and interpretation

`s2c-heuristic-attention-v1` combines a mild top and left position prior with box area, font size, color contrast when known, and an element-type multiplier. Every coefficient is an **editorial setting**, not a value fitted to eye-tracking evidence. Each element places a two-dimensional Gaussian around its visible box; overlapping spots add together. The output colors are normalized **within each screenshot** and have no probability, time, or person interpretation. A large headline may rank highest because its box and font are large. That is an inspectable design hypothesis, not a measured first fixation. The source structural-friction index and any observed section interaction signals remain separate.

The source snippet cannot recover a text-on-image contrast ratio or infer faces. It includes only the first visible viewport and does not know the reader's goal. A page must be recaptured for each viewport, interaction state, or visual revision. Check box alignment, color assumptions, and whether transient overlays or sticky elements were present before sharing the heatmap.

For an evidence-linked interpretation of component competition on a page, use the [AGD-to-audit guide](agd-to-audit.md). The paper informs audit questions; this baseline does not implement AGD.

## Accessibility screening and a testable attention hypothesis

The same supplied text and background colors support a **separate** [WCAG 2.2 SC 1.4.3 text contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) spot check. It compares unrounded ratios to 4.5:1 for normal text or 3:1 for text at least 24 CSS px or about 18.67 CSS px at weight 700+. Missing font size or effective colors become `needs_review`; logos and non-text graphics are excluded. The report labels ratios from manually sampled colors as approximations. Neither a per-element result nor a screenshot constitutes a full WCAG pass/fail judgment. Verify effective CSS, overlays, states, device sizes, [non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html), and keyboard focus separately.

Contrast is already one **continuous heuristic feature** in the heatmap. WCAG's 3:1 and 4.5:1 thresholds are accessibility decision points, not measured gaze breakpoints, so the WCAG result does not become a binary attention multiplier. A below-threshold label flags a readability question; it does not prove low fixation probability. The held-out UEyes test below found only a 0.005 NSS difference between the full map and a version without its pixel-contrast proxy at 3 seconds on webpages. That does not establish a predictive benefit from contrast. Document capture color quality and bootstrap uncertainty before claiming predictive value.

## Observed held-out result, October 26, 2026

The separate `gaze-element-map` research repo evaluated the unchanged `s2c-heuristic-attention-v1` map on UEyes's supplied Train/Test screen split. On 27 held-out Test webpages at the cumulative 3-second window, the map reached **0.506 NSS**; a Train-fitted center Gaussian reached **0.309**, and a Train-fitted position-only map reached **1.148**. The paired S2C minus center difference was +0.197 NSS (95% screen-bootstrap interval −0.014 to +0.399). S2C minus position-only was −0.642 (−0.910 to −0.353). The S2C map therefore did not establish an NSS advantage over center and was worse than the simple position-only baseline. The no-contrast version reached 0.501 NSS.

This was a same-corpus screenshot test using OCR and detected UI boxes as proxies for DOM elements; pixel contrast and OCR cap height stood in for CSS properties. It does not validate the JobFitIQ heatmap or transfer to a live URL audit. Do not label the map “predictive eye tracking” or claim individual gaze, task success, or comprehension. Keep the result with its comparison baselines and 27-screen scope whenever describing validation.

## Held-out fixation test

For another licensed, consented gaze dataset, map every fixation to screenshot pixel coordinates and make a separate `s2c-attention-fixations/v1` file:

```json
{
  "schema": "s2c-attention-fixations/v1",
  "trials": [
    {"frame_id": "first-viewport", "split": "held_out",
     "fixations": [{"x": 330, "y": 180}, {"x": 290, "y": 220}]}
  ]
}
```

Run `python scripts/s2c_attention.py evaluate s2c-capture.json fixations.json --output evaluation.json`. It compares the fixed full heuristic with a **position-only** map, a **uniform** map, and an otherwise identical **no-contrast** map using mean log2 fixation-density ratios (bits per fixation). Positive means the full heuristic assigned more density to held-out fixations than the comparator. The result is averaged per trial before aggregation so one long trial cannot silently dominate. All maps use the same 5% uniform floor. This command trusts the supplied `held_out` label; it cannot verify participant, page, or site separation. Keep all trials from one screenshot/site on one side of a split when fitting future coefficients. Report counts, device/task mix, errors by page, and uncertainty before claiming performance. Do not use a hand-picked JobFitIQ screenshot or synthetic fixture as validation.
