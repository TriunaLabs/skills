# Evidence, severity, confidence, and verification

## Evidence hierarchy

Record what was actually inspected:

1. measured interaction or trace
2. DOM, accessibility tree, or source markup
3. supplied screenshot or recording
4. reproducible user description
5. reviewer inference

An inference can guide investigation but cannot support a measured claim. Store the source in `evidence_ref` and describe the visible fact in `observation` before naming a principle.

## Severity

- **Critical:** credible risk of irreversible harm, destructive error, security/privacy loss, or complete task failure with no recovery.
- **High:** blocks a required or frequent task, hides material cost or consequence, or makes a primary decision unreliable.
- **Medium:** causes repeated confusion, delay, avoidable error, or abandonment while a viable path remains.
- **Low:** localized friction or inconsistency with limited task impact.

Consider task impact, frequency, affected audience, reversibility, and reach. Do not infer severity from the prestige of a named law.

## Confidence

- `0.90–1.00`: directly measured or unambiguous in supplied evidence.
- `0.70–0.89`: clearly visible, but user intent or context is partly inferred.
- `0.50–0.69`: plausible hypothesis requiring interaction or user validation.
- Below `0.50`: do not ship as a finding; record it as a question.

## Verification

Each recommendation needs at least one observable completion check. Prefer behavior and task outcomes over implementation wording. A test may be a DOM assertion, interaction check, performance measurement, usability task, or before/after comparison.

Do not promise conversion improvement. When experimentation is warranted, state the metric, population, guardrail, duration owner, and decision rule without inventing values.

