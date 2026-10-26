# Evidence and models

S2C is a design synthesis, not a validated score or a deployed eye-tracking model. The [NN/g report overview](https://www.nngroup.com/reports/how-people-read-online-eyetracking-evidence/) identifies task, motivation, focus, and personal differences as influences on scanning and lists multiple gaze patterns. The report's full recommendations are not reproduced here; use its public overview and linked primary articles for attributed claims.

## Eye-tracking observations

- [NN/g text scanning patterns](https://www.nngroup.com/articles/text-scanning-patterns-eyetracking/) describes F, spotted, layer-cake, and commitment behavior in text. It notes that task, assumptions, layout, and content affect scanning. Commitment is close reading rather than skimming.
- [NN/g F-pattern clarification](https://www.nngroup.com/articles/f-shaped-pattern-reading-web-content/) warns against treating the F as the only pattern. It also describes bypassing repeated list openings. An F-shaped heatmap is not a bounce-rate formula.
- [NN/g layer-cake article](https://www.nngroup.com/articles/layer-cake-pattern-scanning/) connects descriptive, visually distinct headings with efficient topic finding.
- [NN/g lawn-mower article](https://www.nngroup.com/articles/lawn-mower-pattern/) documents back-and-forth scanning especially in comparison tables, including difficulty with distant labels, jargon, and repetitive cells.
- [NN/g zigzag layout study](https://www.nngroup.com/articles/zigzag-page-layout/) found that decorative alternating image/text layouts made scanning less efficient in the studied pages. Do not prescribe zigzag as a universal path for infographics.
- [W3C headings and labels](https://www.w3.org/WAI/WCAG22/Understanding/headings-and-labels) and [information relationships](https://www.w3.org/WAI/WCAG22/Understanding/info-and-relationships) support descriptive labels and programmatic structure. An S2C review is not a WCAG conformance audit.

## Computational research: what it can and cannot say

| Work | Actual task and evidence | Appropriate S2C use |
| --- | --- | --- |
| [AGD / WebSaliency, arXiv:2407.02439](https://arxiv.org/abs/2407.02439) | A two-stage model predicts fixation-density maps and scanpaths during *free viewing* of graphic documents. It uses component- and layout-aware features and inverse reinforcement learning; the authors collected gaze from 41 people viewing 450 webpages. | Research context for component saliency and temporal attention modeling. A free-viewing prediction is not a task-specific comprehension test or a guarantee of first fixation. |
| [ScanTextGAN, arXiv:2302.05721](https://arxiv.org/abs/2302.05721) | Generates synthetic scanpaths over text and evaluates their value as signals in downstream NLP tasks. | Illustrates gaze modeling. It does not prescribe website, article, or infographic layouts. |
| [See Where You Read, arXiv:2409.19454](https://arxiv.org/abs/2409.19454) | A gaze and LLM system tracks reading location across linear and jump reading. | Relevant to reading-location detection, not proof that a given layout improves understanding. |
| [WebEyeTrack, arXiv:2508.19544](https://arxiv.org/abs/2508.19544) | Browser-based gaze estimation with on-device personalization. | A potential measurement approach requiring calibration, consent, and error analysis; not integrated into this skill. |

The supplied [arXiv:2403.07834](https://arxiv.org/abs/2403.07834) is a review of eye tracking in **medical image analysis**, so it is not evidence for a web-layout rule. The supplied [arXiv:2305.11345](https://arxiv.org/abs/2305.11345) is a general website-usability overview; it does not validate “zero-baseline” attention capture. “Component dominance” and deliberate alignment breaks are S2C design hypotheses unless tested for the task and audience.

Separate **observed** features (a missing heading, distant table label), **inferred** effects (a likely harder comparison), and **measured** outcomes (defined reader tasks with recorded results). Saliency, gaze, task success, and comprehension are different outcomes. Do not infer one directly from another.
