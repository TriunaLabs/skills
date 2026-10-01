# Release brief evidence model

Use this model when deciding which signals belong in a release brief or infographic.

## What readers need first

1. **Outcome and compatibility:** user-visible changes, breaking behavior, migration actions, and known limitations.
2. **Release confidence:** independent quality, security, recoverability, operability, and provenance evidence. Do not collapse these into one score.
3. **Security delta:** newly introduced, resolved, and remaining findings by severity and scanner scope.
4. **Supply-chain change:** dependencies added, updated, or removed; vulnerable additions; license changes; SBOM; artifact signatures; and build provenance.
5. **Operational readiness:** deployment state, staged rollout, rollback rehearsal, dashboards, alerts, and recovery expectations.
6. **Collaboration and scope:** contributors, commits, commit span, change composition, and affected files as context rather than performance measurement.
7. **Traceability:** immutable revisions, issue evidence, test runs, scan references, and artifact attestations.

## Why these signals

- [DORA's delivery metrics](https://dora.dev/guides/dora-metrics/) separate throughput from instability and are most useful over time for one application or service. Use historical lead time, deployment frequency, change fail rate, failed-deployment recovery time, and rework rate as context; do not score one release from commit volume.
- The [SPACE framework](https://www.microsoft.com/en-us/research/publication/the-space-of-developer-productivity-theres-more-to-it-than-you-think/) finds that developer productivity cannot be captured by one metric or dimension. Contributor and commit counts must not become an individual leaderboard.
- [GitHub generated release notes](https://docs.github.com/en/repositories/releasing-projects-on-github/automatically-generated-release-notes) include merged changes, contributors, categories, and a full changelog. These establish useful scope and traceability, not quality.
- [GitHub dependency review](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependency-review) compares dependency changes and reports vulnerabilities and license information. A release brief should show what the release introduces separately from the repository's existing backlog.
- [Snyk reports](https://docs.snyk.io/manage-risk/reporting/getting-started-with-snyk-reports) support severity filtering and contextual PDF exports. Preserve provider, scope, filters, timestamp, and evidence reference when importing scan results.
- [SLSA provenance](https://slsa.dev/spec/v1.2/provenance) tracks artifacts back to their source and build process. Provenance is distinct from an SBOM or vulnerability scan.
- The [CycloneDX SBOM guide](https://cyclonedx.org/guides/sbom/) treats component inventory and vulnerability-exploitability data as related but distinct evidence.
- [Google Cloud recovery guidance](https://docs.cloud.google.com/architecture/framework/reliability/perform-testing-for-recovery-from-failures) recommends testing rollback and recovery while monitoring latency, errors, throughput, logs, and alerts.

## Visual hierarchy

- Lead with the five-domain evidence matrix and explicit unknowns.
- Use delta bars or tables for introduced, resolved, and remaining security findings.
- Show collaboration with neutral participation bars and a warning that activity is not productivity.
- Keep additions and deletions in a secondary scope strip.
- Use print styles that preserve evidence labels, source references, and page breaks. Do not rely on hover state or color alone.
