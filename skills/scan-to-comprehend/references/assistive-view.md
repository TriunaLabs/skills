# Assistive reading view

Use this projection for a page the user has authorized you to inspect. It records three rendered viewports from Chromium: 1265 × 712, 375 × 812, and 320 × 800 CSS px. It adds an accessibility-tree reading path and actual browser Tab traversal to the existing S2C report. Capture time, audit date, viewport, URL, and screenshot stay with the JSON so a later audit can be compared.

From the skills repository, install the package once with `npm install`. Playwright uses an installed Google Chrome, or its bundled Chromium after `npx playwright install chromium`. No camera or gaze tracking is involved.

```bash
node skills/scan-to-comprehend/scripts/s2c_browser_capture.mjs --url https://example.com/ --audit-date YYYY-MM-DD --out capture-dir
python skills/scan-to-comprehend/scripts/s2c_assistive.py capture-dir/snapshot.json --output capture-dir/assistive.json
python skills/scan-to-comprehend/scripts/s2c_visualize.py audit.json --assistive capture-dir/assistive.json --output report.html
```

The same snapshot can feed the experimental attention layer and its separate contrast screen:

```bash
python skills/scan-to-comprehend/scripts/s2c_browser_to_attention.py capture-dir/snapshot.json --output capture-dir/attention-capture.json
python skills/scan-to-comprehend/scripts/s2c_attention.py render capture-dir/attention-capture.json --output capture-dir/attention.json
python skills/scan-to-comprehend/scripts/s2c_visualize.py audit.json --assistive capture-dir/assistive.json --attention capture-dir/attention.json --output report.html
```

This mapping keeps first-viewport semantic element boxes, clips them to the screenshot, and omits color ratios for text overlapping a captured image. Other overlays and CSS effects can still escape the check. Inspect the aligned screenshot and spot-check colors before using the layer in a review. The heatmap is a fixed heuristic that trailed a simple position-only baseline in its held-out UEyes test; it is not a measured gaze map.

`--audit-date` is the date of inspection in the reviewer's timezone; if omitted, it defaults to the UTC date. Each frame retains an ISO UTC timestamp. The browser capture returns `s2c-browser-capture/v1` with the DOM nodes, computed styles, first-viewport image, Chromium AX path, observed focus order, and document width. The pure projection returns `s2c-assistive-v1`. Save the snapshot as the reusable source; rerun the projection when rules change, without pretending to have recaptured the site.

The report displays the first 20 mapped reading and focus markers on each first-viewport screenshot. The first 10 are solid and later markers faint. Full order lists include offscreen steps. Accessibility-tree text nodes sometimes have no painted element box; those remain in the list and do not receive invented coordinates. Focus may move the browser scroll position during capture, so the overlay uses each node's original screenshot coordinates.

Review candidates include unnamed focus targets, images without an `alt` attribute, small non-inline keyboard targets, clipped text, and 320 px document overflow. A small target needs a human check for WCAG 2.2 SC 2.5.8 spacing and exceptions. Text link targets may qualify for the inline exception; the simple geometry screen excludes them unless both dimensions are under 24 px. An empty image alt can be correct for decoration. Computed solid colors in the snapshot can feed the separate S2C contrast spot check, but this view does not run it. Visible focus indicators, custom-widget keyboard operation, touch behavior, timing, status messages, and meaningful sequence require separate tests.

The path is **Chromium's accessibility-tree order**, not a recording of a screen reader speaking. Real screen readers, browsers, interaction states, nested frames, and shadow roots can differ. The Tab path is observed in Chromium for this state, but not a universal keyboard trace. Do not call this a WCAG conformance audit or a prediction of comprehension. Verify any proposed change with a keyboard user or screen-reader user on the task that matters.
