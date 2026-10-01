---
description: "Versioned JSON contract for validation, comparison, and annotated HTML posters."
connections: [anti-patterns, evidence-and-severity]
---

# Review artifact schema 2.0

Start with `assets/sample-findings.json`. The root requires `schema_version`, `title`, `subtitle`, `source`, and `findings`. `source.type` is one of `url`, `screenshot`, `html`, `description`, or `trace`; `source.ref` points to the evidence.

Every finding requires a stable `id`, consecutive one-based `n`, `surface`, `region`, observable `observation`, `evidence_ref`, one supported `principle`, causal `mechanism`, `severity`, numeric `confidence`, actionable `recommendation`, at least one `verification` step, and a normalized `anchor` with `x` and `y` from 0 to 1. Optional `side` is `left` or `right`.

Validate before use:

```bash
python scripts/validate_findings.py findings.json
python scripts/validate_findings.py findings.json --poster
```

The poster limit is 14 findings. Read [anti-patterns](anti-patterns.md) when several findings overlap and [evidence and severity](evidence-and-severity.md) before assigning risk or confidence.

