# Editable browser checklist

Use this when a visual audit needs repeatable warnings alongside reviewer callouts. The checklist consumes the shared Chromium snapshot, optional assistive projection, and optional attention contrast screen:

```bash
python skills/scan-to-comprehend/scripts/s2c_browser_rubric.py capture-dir/snapshot.json --assistive capture-dir/assistive.json --attention capture-dir/attention.json --output capture-dir/browser-rubric.json
python skills/scan-to-comprehend/scripts/s2c_visualize.py audit.json --walkthrough capture-dir/walkthrough.json --rubric capture-dir/browser-rubric.json --output capture-dir/report.html
```

The seven rules screen shared in-page navigation destinations, visible H1 count, H1 presence in captured first viewports, 320 CSS px document overflow, captured focus names, image alt-attribute presence, and supplied solid-color text contrast. Each rule reports its evidence, status, weight, and next action. `warning` is a detected rule deviation; `review` means the captured evidence needs human interpretation; `not_checked` means the required capture was absent. Review and not-checked weights are excluded from the assessed denominator. The displayed `earned/assessed` points are an **editorial checklist score**, not measured cognitive load, usability, comprehension, gaze, or WCAG conformance. A rule may pass while meaning is wrong: an image can have an irrelevant alt string, or a CTA can point to a technically valid destination that misstates what is available.

To change weights, copy [browser-rubric.json](browser-rubric.json), edit its seven integer weights so they total 100, and pass `--config your-rubric.json` to `s2c_browser_rubric.py`. Keep the config and output with the report. Change the version when the rule definitions or weights change; do not compare scores made with different rubric versions or capture scopes. Rule logic lives in the script. The HTML displays the applied version and each rule's point contribution; it does not silently rescore edited text.

The checklist is a triage layer. Reviewer findings from screenshots, browser actions, and cross-section content comparison remain separate in the prioritized action queue. Assign P1/P2/P3 as a reviewer judgment and mark each review callout's evidence as `observed` or `hypothesis`. Keep the likely reader effect untested unless people have completed the task.
