# From AGD research to an S2C page audit

Use this guide when a user asks what [Chakraborty et al., *Predicting visual attention in graphic design documents*](https://arxiv.org/html/2407.02439v1) means for a **specific rendered page**. It turns the paper into inspectable questions and tests. It does not run AGD, reproduce its trained weights, or turn a free-viewing result into a claim about an individual reader.

## What the paper establishes

AGD separates a **fixation-density map** (where fixations accumulate across viewers) from a **scanpath** (the order of fixations). Its first stage models page layout and component-specific attention for text, faces, logos, banners, and images; its second stage predicts a sequence using those maps. The study collected gaze from 41 participants, ages 17–23, each freely viewing a subset of 450 webpage screenshots for five seconds. Each image had 13 or 14 viewers. The scanpath evaluation used the **first seven fixations**. The paper's test set contained 58 randomly selected WebSaliency images. [Method, dataset, and evaluation](https://arxiv.org/html/2407.02439v1)

The paper reports that including layout improved its saliency model's normalized scanpath saliency from **1.802 to 1.821** on that test set. Its scanpath Sequence Score was **0.224**, compared with **0.314** for agreement between observers. These are benchmark results for AGD, not S2C coefficients or expected accuracy on a new site. The modest layout ablation gain supports checking layout as a feature; it does not establish a preferred page geometry. [Paper's saliency and scanpath comparisons](https://arxiv.org/html/2407.02439v1)

## Turn it into an audit

| Move | Record in the report | Evidence boundary |
| --- | --- | --- |
| Capture the reader context | Dated screenshot, viewport, page state, intended reader task, and the element the reader needs to find or understand. | AGD's five-second free viewing does not model a named task, scrolling, or interaction. |
| Map competing elements | Mark visible text, images, faces, logos, banners, and task-relevant controls. Record each element's location, size, and legibility. | AGD's component categories motivate inspection. S2C button/link boxes and contrast checks are its own additions, not AGD predictions. |
| Inspect the attention hypothesis | Overlay the S2C heuristic only when capture boxes and colors have been reviewed. Ask whether the intended answer or evidence sits among strong competing cues. | Call the map **estimated attention**. Do not infer first fixation, dwell, or a human scanpath from a static heatmap. |
| Propose and verify a change | Name the observed feature, likely task effect, one concrete edit, and a check that could disprove the hypothesis. | Compare task outcomes with representative readers. Use held-out fixation data only for gaze-prediction claims. |

Keep three report statements distinct:

1. **Observed:** what the capture, DOM, or source actually shows. Example: “The waitlist button and résumé example link are both visible in the first desktop viewport.”
2. **Estimated:** what S2C's untrained heatmap ranks or what an AGD-like model predicts. Name the model, version, viewport, and confidence limits. A heatmap intensity is not a fixation probability.
3. **Measured:** a reader's recorded task result, consented fixation trial, or separately labeled interaction signal. Do not relabel section exposure, hover, or cursor position as gaze.

### Worked JobFitIQ question

**Reader task:** Understand the product and inspect an example résumé before deciding whether to join the waitlist. **Capture:** [JobFitIQ first-viewport report](https://triunalabs.com/tools/scan-to-comprehend/case-studies/jobfitiq-attention.html), audited October 26, 2026.

- **Observed:** The desktop capture shows a large headline, two waitlist controls, and a link to the résumé example. The annotations and screenshot are reviewable in the report.
- **Estimated:** S2C's editorial heuristic ranks the headline and visible controls highly. AGD's paper supports asking how layout and component competition affect attention, but it did not analyze this page or this task. Its published component scores cannot be assigned to these controls.
- **Hypothesis:** A reader focused on proof may take an extra step to recognize the résumé link as the example they need. This remains untested; its current placement may work well.
- **Possible change:** Test a clearer “See an example résumé” label and its placement beside the main action. Preserve the existing destination and accessible name quality.
- **Check:** Give representative readers the task above. Record whether they find the example, what they believe JobFitIQ does, and where they hesitate. If licensed gaze data is available later, compare a fixed prediction with held-out fixations separately from task success.

## When to use a model or dataset

The current S2C [attention baseline](attention-baseline.md) is an **untrained heuristic**, not AGD. It can compare its full map with position-only, uniform, and no-contrast maps on user-supplied held-out fixations. That comparison says nothing about task comprehension. For a calibrated element-level model, follow the [research track](element-attention-research.md): verify dataset access and rights, preserve site-level splits, document task and viewport, and report uncertainty and out-of-domain failures. The AGD paper's publication license does not establish rights to reuse its images, gaze records, or model assets.
