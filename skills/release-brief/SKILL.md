---
name: release-brief
description: Build an evidence-backed release brief from an explicit Git revision range, with audience-aware Markdown, JSON, or interactive HTML reports. Use when preparing release communication or reviewing release readiness; does not tag, deploy, publish, or infer that merged work shipped.
license: MIT
---

# Build a release brief

Turn a resolved Git range and supplied verification evidence into a draft another person can audit.

1. Require an explicit base revision, target revision, and audience: `users`, `developers`, `operators`, or `executives`. Resolve both revisions to commits before collecting evidence. Do not silently choose a tag or release boundary.
2. Run [`scripts/collect-release`](scripts/collect-release) against the local repository. It records immutable commit IDs, subjects, bodies, changed paths, additions/deletions, issue references, deterministic categories, risk signals, and the repository's dirty-state warning. Read [the artifact schema](references/release-artifact-schema.md) when integrating another collector.
3. Add issue, test, deployment, rollback, and limitation records through a JSON evidence file. Apply [the evidence policy](references/evidence-policy.md): a merge proves inclusion in the selected Git range, not deployment, test success, performance improvement, or user impact.
4. Review deterministic categories and audience inclusion. Use [the audience guide](references/audience-and-voice.md) for emphasis and language. Reclassify only with cited evidence; retain the original commit and path provenance.
5. Explain breaking changes with previous behavior, new behavior, and required action. If any part is unknown, keep it in evidence gaps instead of completing it from implication.
6. Render the same artifact as JSON, Markdown, or self-contained interactive HTML with [`scripts/render-release`](scripts/render-release). The visualization is observational and must not alter categories, evidence state, or readiness.
7. Deliver the brief as a draft with its exact revision range, evidence gaps, known limitations, and provenance. Do not create a tag, GitHub release, deployment, announcement, or outbound message unless separately requested and authorized.

```sh
python scripts/collect-release --repo . --base v1.2.0 --target v1.3.0 --audience users --evidence verification.json --out release.json
python scripts/render-release release.json --format html --out release.report.html
python scripts/render-release release.json --format markdown --out RELEASE-NOTES.md
```

The `samples/` directory contains a synthetic release artifact and verification evidence for safe previewing. Generated reports contain repository and commit metadata; review them before sharing outside the project.
