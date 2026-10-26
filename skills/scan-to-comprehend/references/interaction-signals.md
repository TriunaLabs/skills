# Optional page interaction signals

The [first-party JavaScript probe](../integrations/section-signals.js) adds **observed section behavior** to an S2C audit on pages you control. It records qualifying viewport exposure, mouse hover time, primary mouse clicks, and touch taps for named sections. It never requests a camera, records raw pointer coordinates, reads form values, stores identifiers, or sends data. It stays in memory until the host page calls `download()` or `snapshot()`.

This is a different evidence layer from [Attention Insight's predictive heatmaps](https://attentioninsight.com/feature/attention-heatmap/): those estimate attention from a design without visitors or tracking code. The S2C probe observes browser events on a live page. Neither establishes what a person read or understood. [Cursor research on search result pages](https://www.microsoft.com/en-us/research/publication/no-clicks-no-problem-using-cursor-movements-to-understand-and-improve-search-2/) found useful gaze–cursor relationships in that task; it does not make hover a universal gaze substitute.

## Install on an owned page

Mark stable, non-overlapping sections with nonpersonal IDs:

```html
<section data-s2c-section="hero">...</section>
<section data-s2c-section="evidence">...</section>
<section data-s2c-section="decision">...</section>
<script src="/section-signals.js"></script>
```

Start only after the page's appropriate notice or consent step. Starting the probe is an explicit host action; loading the script alone collects nothing.

```js
const session = S2CSignals.start({ pageLabel: "product-page-v2" });
// Wire this to a user-controlled export button or a consented study workflow.
session.download();
// When the study ends:
session.stop();
```

Copy `integrations/section-signals.js` into the host site's static assets. `snapshot()` returns the same JSON without downloading it. A production collector could receive this aggregate export **only after a separate, reviewed transport and retention design**; the supplied script has no collector. Use stable section IDs across versions and keep device widths and reader tasks in the study record. Do not place names, email addresses, search terms, or account IDs in `data-s2c-section` or `pageLabel`.

The probe samples every 250 ms. A section qualifies when at least 25% of the smaller of its area or the viewport area is visible. It counts time only while the tab is foreground, the window is focused, and the page has had interaction within 30 seconds. Hover time counts only mouse pointers and stops after five seconds without mouse movement. A suspended timer is capped at one second per sample. These are implementation settings, not gaze-study coefficients. Viewport exposure can include obscured or transparent content, and movement or an open tab does not prove attention. [Intersection Observer timing guidance](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API/Timing_element_visibility) and the [Page Visibility API](https://developer.mozilla.org/en-US/docs/Web/API/Page_Visibility_API) explain the browser primitives and their limits.

## Add observations to the visual report

Collect one JSON export per session. Then pass the exports alongside a source audit and, optionally, a rendered-page walkthrough:

```sh
python scripts/s2c_visualize.py audit.json --walkthrough walkthrough.json --signals session-a.json session-b.json --output report.html
```

The report shows section reach, median visible time among reached sessions, mouse-hover session counts, mouse clicks, and touch taps in narrow and wide viewport groups. Its bars visualize observed viewport reach, not predicted saliency. Every denominator is a **session export**, never a unique person. Keep collection dates distinct from the original screenshot audit date. Review bots, sampling, consent coverage, section changes, and traffic source before interpreting a difference.

Use the observed signal to form a check: “Only 3 of 20 session exports reached the evidence section; can target readers find it?” Then test the reader task directly. Do not merge these values into the structural friction index or call them dwell, gaze, comprehension, or cognitive load.
