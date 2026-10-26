# Rendered-page walkthrough report

Use this mode when the user gives a public URL and wants to inspect a visual audit. The output is a **self-contained HTML file** with screenshots, numbered callouts, a side margin explaining each observation, and the optional structural preflight. It is a reviewer aid, not an eye-tracking simulation.

## Capture and review

1. Frame one reader task before looking for issues. Open the explicitly supplied public URL in an authorized browser. Record the final URL, capture date, and viewport size. Inspect the first viewport, a key task area, and the evidence or decision area; add a mobile pass when relevant. Do not submit forms or upload files merely to produce a report.
2. Capture actual screenshots as PNG, JPEG, or WebP. Use the browser's rendered DOM snapshot if available, or the CLI's `--url` mode for raw HTML when network access permits. Say which basis was audited. A rendered DOM snapshot may differ from server HTML; neither captures all interaction states.
3. Run `s2c_audit.py` on that HTML with `--json`. Draft callouts from visible evidence. For every callout, state **observed feature → likely task effect → proposed change → check**. Mark effects as untested unless representative-reader results exist. Do not infer a fixation, gaze path, saliency score, or cognitive-load change from a screenshot.
4. Put screenshots and a `walkthrough.json` file in the same directory. Render with `python scripts/s2c_visualize.py audit.json --walkthrough walkthrough.json --output report.html`. The HTML embeds screenshots, so the recipient does not need the original image files to view it. Inspect the result in a browser when available and give the user the actual HTML, not links to temporary screenshots.

## Walkthrough manifest

Screenshot paths are relative to the manifest directory. Pin coordinates are proportions of the screenshot width and height; `0,0` is its top-left corner. The renderer checks paths stay inside the manifest directory and accepts only PNG, JPEG, and WebP bytes.

```json
{
  "url": "https://example.com/",
  "reader_task": "Can a visitor find the evidence behind a headline claim?",
  "audit_basis": "Rendered DOM and 1280 × 720 desktop captures, 2026-10-26",
  "frames": [
    {
      "label": "First viewport",
      "image": "hero.png",
      "alt": "Description of the captured page view.",
      "callouts": [
        {
          "kind": "review",
          "title": "Claim lacks a nearby definition",
          "x": 0.62,
          "y": 0.38,
          "observed": "The displayed number has no visible unit or scale in this view.",
          "likely_effect": "Readers may interpret it differently; untested.",
          "suggestion": "Show the unit and link to the method.",
          "check": "Ask readers to explain the number before following the link."
        }
      ]
    }
  ]
}
```

Use `"kind": "strength"` for a narrow, visible positive observation or `"review"` for a potential weakness. Keep the screenshot, observation, and task effect separate. The source index remains experimental and low-confidence even when its HTML report contains rendered-page callouts. Do not add manual observations to the numeric index without a separately specified and validated method.

For a public report, check screenshot and dataset rights. In particular, the [MASSVIS repositories](https://github.com/massvis/dataset) restrict reuse of their source images and annotations; cite the research without bundling those images. If the URL cannot be fetched from the CLI but an authorized browser can render it, audit the browser's DOM snapshot and label it accordingly rather than claiming a raw-source URL audit.
