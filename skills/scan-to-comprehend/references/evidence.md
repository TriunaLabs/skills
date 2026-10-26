# Evidence and models

S2C is a design synthesis, not a validated score or a deployed eye-tracking model. The [NN/g report overview](https://www.nngroup.com/reports/how-people-read-online-eyetracking-evidence/) identifies task, motivation, focus, and personal differences as influences on scanning and lists multiple gaze patterns. The report's full recommendations are not reproduced here; use its public overview and linked primary articles for attributed claims.

## Eye-tracking observations

- [NN/g text scanning patterns](https://www.nngroup.com/articles/text-scanning-patterns-eyetracking/) describes F, spotted, layer-cake, and commitment behavior in text. It notes that task, assumptions, layout, and content affect scanning. Commitment is close reading rather than skimming.
- [NN/g F-pattern clarification](https://www.nngroup.com/articles/f-shaped-pattern-reading-web-content/) warns against treating the F as the only pattern. It also describes bypassing repeated list openings. An F-shaped heatmap is not a bounce-rate formula.
- [NN/g layer-cake article](https://www.nngroup.com/articles/layer-cake-pattern-scanning/) connects descriptive, visually distinct headings with efficient topic finding.
- [NN/g lawn-mower article](https://www.nngroup.com/articles/lawn-mower-pattern/) documents back-and-forth scanning especially in comparison tables, including difficulty with distant labels, jargon, and repetitive cells.
- [NN/g zigzag layout study](https://www.nngroup.com/articles/zigzag-page-layout/) found that decorative alternating image/text layouts made scanning less efficient in the studied pages. Do not prescribe zigzag as a universal path for infographics.
- [Majooni, Masood, and Akhavan, *Information Visualization*](https://journals.sagepub.com/doi/abs/10.1177/1473871617701971) compared layouts of two infographic stories using eye movements and pupil-diameter fluctuation. The abstract reports higher comprehension and lower load for the tested zigzag form. This does not establish a universal zigzag rule or a maximum image-to-label pixel distance. The finding concerns information graphics; NN/g's result above concerns alternating decorative image/text rows on webpages.
- [Wu and Liu, *Journalism & Mass Communication Quarterly*](https://journals.sagepub.com/doi/abs/10.1177/10776990241255974) studied 95 college students reading infographics. Higher-comprehension readers made more transitions between words and graphics and spent more time processing the graphics. This supports checking whether visual evidence and explanatory text can be cross-referenced; an automated page audit cannot infer those eye movements from markup.
- [W3C headings and labels](https://www.w3.org/WAI/WCAG22/Understanding/headings-and-labels) and [information relationships](https://www.w3.org/WAI/WCAG22/Understanding/info-and-relationships) support descriptive labels and programmatic structure. An S2C review is not a WCAG conformance audit.

## Computational research: what it can and cannot say

| Work | Actual task and evidence | Appropriate S2C use |
| --- | --- | --- |
| [AGD / WebSaliency, arXiv:2407.02439](https://arxiv.org/abs/2407.02439) | A two-stage model predicts fixation-density maps and scanpaths during *free viewing* of graphic documents. It uses component- and layout-aware features and inverse reinforcement learning; the authors collected gaze from 41 people viewing 450 webpages. | Research context for component saliency and temporal attention modeling. A free-viewing prediction is not a task-specific comprehension test or a guarantee of first fixation. |
| [ScanTextGAN, arXiv:2302.05721](https://arxiv.org/abs/2302.05721) | Generates synthetic scanpaths over text and evaluates their value as signals in downstream NLP tasks. | Illustrates gaze modeling. It does not prescribe website, article, or infographic layouts. |
| [See Where You Read, arXiv:2409.19454](https://arxiv.org/abs/2409.19454) | A gaze and LLM system tracks reading location across linear and jump reading. | Relevant to reading-location detection, not proof that a given layout improves understanding. |
| [WebEyeTrack, arXiv:2508.19544](https://arxiv.org/abs/2508.19544) | Browser-based gaze estimation with on-device personalization. | A potential measurement approach requiring calibration, consent, and error analysis; not integrated into this skill. |

## Information-visualization datasets and model evaluations

- [MASSVIS annotations](https://github.com/massvis/dataset) and [eye-tracking records](https://github.com/massvis/eyetracking) cover 393 eye-tracking target visualizations, with eye movements from 33 participants and memorability/description data. This is a benchmark for studied visualizations, not gaze data for an arbitrary website submitted to S2C. The repositories say source images must be requested and restrict images/annotations to research and educational uses; **do not bundle or redistribute those images in a commercial report or skill asset**.
- [UMSS, *Scanpath Prediction on Information Visualisations*](https://arxiv.org/abs/2112.02340) predicts element-level saliency over viewing durations and samples scanpaths. Its reported improvements are on its evaluation benchmarks, not evidence that an S2C callout or page edit improves a reader task. S2C does not run UMSS.
- [Dashboard Vision, *IEEE TVCG*](https://doi.org/10.1109/TVCG.2025.3532497) studies eye movements on dashboards and develops a dashboard saliency model. Dashboard object attention is useful research context for labels, graphics, and layout, but the model is not a general website-comprehension measure. S2C does not run it.
- [Lopez-Cardona et al., *A Comparative Study of Scanpath Models in Graph-Based Visualization*](https://arxiv.org/abs/2503.24160) compares human and modeled scanpaths for graph-analysis questions with 40 participants. Task complexity and graph structure matter in that setting; this does not supply coefficients for a webpage risk score.

An S2C rendered-page walkthrough may place **reviewer callouts** beside actual screenshots. Their coordinates locate observations, not predicted fixations. Only a separately identified, consented eye-tracking study should display gaze paths or fixation maps as measured data; model predictions need their own model, dataset, task, and validation labels.

The supplied [arXiv:2403.07834](https://arxiv.org/abs/2403.07834) is a review of eye tracking in **medical image analysis**, so it is not evidence for a web-layout rule. The supplied [arXiv:2305.11345](https://arxiv.org/abs/2305.11345) is a general website-usability overview; it does not validate “zero-baseline” attention capture. “Component dominance” and deliberate alignment breaks are S2C design hypotheses unless tested for the task and audience.

The supplied [van Dyck et al. natural-image model](https://arxiv.org/abs/2206.10587) investigates how guiding a CNN with human fixation data affects object-recognition attention. It reports category-specific effects involving animacy and faces, but no significant increase in model human-likeness. It is not a calibrated face-priority rule for a webpage, infographic, or video audit.

No cited study supplies transferable coefficients for a page-level cognitive-load score. In web performance, **CLS already means Cumulative Layout Shift** ([web.dev](https://web.dev/articles/cls)); use “S2C structural friction risk” for the experimental source-only index. Its weights are editorial triage settings, not fitted research parameters. See [audit engine contract](audit-engine.md).

Separate **observed** features (a missing heading, distant table label), **inferred** effects (a likely harder comparison), and **measured** outcomes (defined reader tasks with recorded results). Saliency, gaze, task success, and comprehension are different outcomes. Do not infer one directly from another.
