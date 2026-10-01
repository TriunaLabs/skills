# Release artifact schema

The collector emits one JSON artifact with these top-level fields:

- `source`: repository name, requested refs, resolved commit IDs, target tag when exact, dirty-state count, and collection time;
- `audience`: requested report audience;
- `summary`: commits, changed files, additions, deletions, included entries, breaking changes, risk flags, and evidence gaps;
- `commits`: immutable commit provenance, messages, changed paths, categories, issue references, and inclusion decision;
- `entries`: release-facing outcomes derived from commits, with category, audiences, evidence references, and uncertainty;
- `files`: range-level name/status and line statistics;
- `risk_flags`: deterministic signals such as breaking-change markers, migrations, authentication/security changes, configuration, and dependency changes;
- `evidence`: supplied issue, test, deployment, rollback, and known-limitation records;
- `evidence_gaps`: claims the range does not establish;
- `readiness`: always `draft` until an external release process approves publication.

Schema version `1.0` is append-only within the `0.2.x` skill series. Consumers must ignore unknown fields and must not infer missing evidence from absent fields.

## Evidence input

```json
{
  "issues": [{"id":"142","title":"Session expiry contract","url":"https://tracker.example/142","state":"closed"}],
  "tests": [{"name":"contract suite","status":"passed","evidence_ref":"run:8841"}],
  "deployment": {"status":"not_deployed","environment":null,"evidence_ref":null},
  "rollback": {"status":"documented","evidence_ref":"docs:rollback-auth-v2"},
  "known_limitations": ["Older mobile clients require an upgrade."]
}
```

Allowed test statuses are `passed`, `failed`, `partial`, `not_run`, and `unknown`. Allowed deployment statuses are `deployed`, `partially_deployed`, `not_deployed`, and `unknown`. These values are evidence records, not instructions to deploy.
