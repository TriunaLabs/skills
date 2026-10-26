# S2C blueprint

Use this as a planning record, not a rigid compiler input. Keep the artifact in the user's requested format. A page can support several routes at once.

```yaml
surface: website | article | infographic
audience_task: "Compare which products are live and what each does"
viewport_and_language: "desktop and phone; left-to-right English"
must_preserve: ["current status", "primary purpose", "source or next step"]
modules:
  - id: products
    reader_question: "Which product fits my task?"
    scan_answer: "Fold publishes; JobFitIQ compares job evidence; DailyGauntlet offers daily games"
    detail: "A short, accurate description and a direct product link for each"
    evidence: "canonical product pages"
    likely_routes: ["spotted", "lawn-mower comparison", "commitment for details"]
    visual_role: "aligned comparison rows with status and purpose labels"
checks:
  quick_scan: "Can a newcomer state the page purpose?"
  targeted_find: "Can they locate a specified product and its current status?"
  explanation: "Can they explain the product's role without inventing a feature?"
```

## Website blueprint

**Entry:** page identity, specific thesis, and a clear route to the major groups. **Catalog or comparison:** consistent product labels, distinct purposes, explicit availability, and direct links. Use a table when readers compare the same fields; use cards when modules have different kinds of detail. **Deeper sections:** informative headings, summary statements, methods and supporting evidence. A product can be spotted by name and status while a buyer can read its detail closely. Keep reading order intact when columns collapse on mobile.

### Worked Triuna Labs mapping

This is an illustrative S2C plan based on the supplied blueprint and the site's public content as of October 26, 2026. Verify current product claims before reuse.

| Module | Main reader task | Likely route to support | Information to keep close |
| --- | --- | --- | --- |
| Global navigation and thesis | Understand what Triuna Labs makes | Layer-cake orientation and spotted destination links | Distinct Products, Skills & Tools, Articles, and Consulting labels |
| Product catalog | Find a product by purpose and availability | Spotted names/status; lawn-mower comparison only if fields align | Product purpose, availability, direct link; no invented status metric |
| Frameworks and protocols | Locate a technical method | Layer-cake headings and descriptive links | Scope, maturity, documentation link |
| Research | Identify a finding and inspect its evidence | F-aware lead words, layer-cake publication titles, commitment read | Measured result, method, limits, reproducibility link |
| Consulting | Find a relevant engagement path | Layer-cake offer headings and spotted next step | Scope, deliverables, contact route |

Do not force a zigzag path through the product catalog or research modules. Adjacent cards are not automatically a comparison table. Use a stable alignment when readers need to compare repeated fields.

### Dense product comparison recipe

Use this structure when each product has the same fields. A status belongs in a labeled cell, not a free-floating badge whose meaning depends on color. On a phone, use a readable horizontally scrollable table or convert each row to a labeled group while keeping every value associated with its field.

```html
<section aria-labelledby="products-title">
  <h2 id="products-title">Choose a product by the work it helps with</h2>
  <p>Compare purpose and current availability before opening a product page.</p>
  <table>
    <caption>Triuna Labs product overview</caption>
    <thead><tr><th scope="col">Product</th><th scope="col">Purpose</th><th scope="col">Availability</th></tr></thead>
    <tbody>
      <tr><th scope="row"><a href="/fold/">Fold</a></th><td>Article and carousel publishing</td><td>[verified current status]</td></tr>
      <tr><th scope="row"><a href="/jobfitiq/">JobFitIQ</a></th><td>Evidence-backed job alignment</td><td>[verified current status]</td></tr>
    </tbody>
  </table>
</section>
```

The example avoids hard-coded status claims; fetch current availability from the canonical source before publishing. A pinned column header can help a long comparison, but check that it does not cover content or break keyboard and screen-reader use.

## Article blueprint

Start with the question, answer, and scope. Build a heading-only outline that lets a reader find one topic. Within each section, place the claim, evidence, method, example, and limitation where the relationship is clear. Highlight a keyword only when it helps a task. Provide a route from the brief answer into full reasoning. Test both a quick overview and a close read.

### Dense article recipe

```markdown
# What changed in the measured result?

The central finding in one or two accurate sentences, with scope and timeframe.

## What was measured?
Define the metric, unit, population, and baseline before interpreting a change.

## What did the comparison show?
Present the result, with a labeled table or figure when it clarifies the relationship.

## How was it tested?
Explain the method and provide the source or reproducible material.

## What remains uncertain?
State caveats and plausible alternatives without burying them in a footnote.
```

The headings support a layer-cake pass; the lead and opening words support a partial F-like pass; the metric and source can act as spotted anchors. Full methods remain available for commitment reading.

## Infographic blueprint

State the central message, population, timeframe, units, and data source. Divide the visual into a small number of labeled groups according to the actual relationship: sequence, comparison, distribution, or geography. For a comparison, align measures and labels; for a process, use numbered steps and connectors only if order matters. Make the graphic understandable through a text equivalent and verify it at final display size. Do not add a sparkline or oversized number unless it represents relevant, sourced data.

### Dense infographic recipe

```text
Title: the finding, with population and timeframe
Key: units, definitions, and source

Panel 1 — Context: what is being compared or sequenced?
Panel 2 — Evidence: directly labeled values or stages, with consistent scale
Panel 3 — Interpretation: what the evidence supports and what it does not

Text equivalent: the same finding, values, and caveat in reading order
```

If panels share comparable fields, align those fields for a possible lawn-mower pass. If they form a process, number the stages. Avoid a decorative zigzag that separates text from its visual evidence.
