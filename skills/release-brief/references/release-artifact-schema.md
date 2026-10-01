# Release artifact schema

The collector emits one JSON artifact with these top-level fields:

- `source`: repository name, requested refs, resolved commit IDs, target tag when exact, dirty-state count, and collection time;
- `audience`: requested report audience;
- `summary`: contributors, commits, changed files, churn context, evidence-domain counts, new critical/high exposure, risk flags, and evidence gaps;
- `commits`: immutable commit provenance, messages, changed paths, categories, issue references, and inclusion decision;
- `entries`: release-facing outcomes derived from commits, with category, audiences, evidence references, and uncertainty;
- `files`: range-level name/status and line statistics;
- `risk_flags`: deterministic signals such as breaking-change markers, migrations, authentication/security changes, configuration, and dependency changes;
- `collaboration`: contributor participation, commit span, category coverage, and an explicit warning against interpreting activity as productivity;
- `confidence`: independent quality, security, recoverability, operability, and provenance states plus security and dependency deltas;
- `evidence`: supplied issue, test, security scan, dependency review, supply-chain, deployment, rollback, observability, rollout, delivery-history, and known-limitation records;
- `evidence_gaps`: claims the range does not establish;
- `readiness`: always `draft` until an external release process approves publication.

Schema version `1.1` adds `collaboration`, `confidence`, and richer evidence. The renderer also accepts `1.0`. Consumers must ignore unknown fields and must not infer missing evidence from absent fields.

## Evidence input

```json
{
  "issues": [{"id":"142","title":"Session expiry contract","url":"https://tracker.example/142","state":"closed"}],
  "tests": [{"name":"contract suite","status":"passed","evidence_ref":"run:8841"}],
  "security_scans": [{"provider":"Snyk","scope":"dependencies","status":"passed","introduced":{"critical":0,"high":0,"medium":1,"low":0},"resolved":{"critical":0,"high":1,"medium":0,"low":0},"remaining":{"critical":0,"high":0,"medium":2,"low":1},"evidence_ref":"snyk:scan-993"}],
  "dependency_review": {"status":"verified","added":1,"updated":2,"removed":0,"vulnerable_added":0,"license_changes":0,"evidence_ref":"github:dependency-review-774"},
  "supply_chain": {"sbom":{"status":"present","format":"CycloneDX 1.6","evidence_ref":"artifact:sbom"},"provenance":{"status":"verified","level":"SLSA Build L2","evidence_ref":"attestation:441"},"signature":{"status":"verified","method":"Sigstore","evidence_ref":"rekor:11933021"}},
  "deployment": {"status":"not_deployed","environment":null,"evidence_ref":null},
  "rollback": {"status":"tested","evidence_ref":"run:8850"},
  "observability": {"status":"verified","summary":"SLO and release alerts linked","evidence_ref":"dashboard:auth"},
  "rollout": {"status":"ready","strategy":"10% canary with hold","evidence_ref":"plan:auth-v13"},
  "delivery_metrics": {"window":"previous 90 days","change_lead_time_hours":18,"change_fail_rate_percent":7.5,"failed_deployment_recovery_hours":0.7,"evidence_ref":"dora:q3"},
  "known_limitations": ["Older mobile clients require an upgrade."]
}
```

Allowed test and scan statuses are `passed`, `failed`, `partial`, `not_run`, and `unknown`. Allowed deployment statuses are `deployed`, `partially_deployed`, `not_deployed`, and `unknown`. Security counts represent scanner-reported introduced, resolved, and remaining findings by severity. These values are evidence records, not instructions to deploy.
