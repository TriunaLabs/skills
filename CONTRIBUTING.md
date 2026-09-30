# Contributing

Submit one focused skill or improvement per pull request. Start with [the submission template](templates/skill-submission.md); proposals without code can use the Skill submission issue form.

1. Create `skills/<lowercase-hyphenated-name>/SKILL.md` with `name`, `description`, and `license: MIT` frontmatter. Name must match the directory, be at most 64 characters, and identify a specific workflow.
2. Add `catalog.json` using the [metadata example](templates/catalog.json). Required fields: title, category, tags, semantic version, license, author, origin, requirements, compatibility, and examples. Arrays must contain meaningful values; use an explicit no-extra-tools statement where appropriate.
3. Keep instructions portable. Agent-specific syntax belongs in installation documentation or clearly scoped references. Put reusable templates in `assets/`, executable helpers in `scripts/`, and conditional guidance in `references/`. Link resources from SKILL.md.
4. State provenance honestly. Only contribute material you can release under MIT. Do not export installed, employer, customer, or private skills without explicit selection and redistribution rights. Remove secrets, identifiable production data, and local machine paths.
5. Include at least one realistic positive example and a non-trigger case in the pull request. Exercise any helper scripts on synthetic fixtures. Report actual commands, versions, results, and limitations; do not label a format check as a runtime evaluation.
6. Run validation, tests, and build using the README commands. Review the rendered catalog and install guidance for your package.

`format-compatible` means the package uses the common format and avoids required agent-specific features; it does not assert an agent run. `untested` makes no runtime compatibility claim; `unsupported` identifies known incompatibility. These are the accepted catalog values. Runtime evaluation evidence belongs in the PR with the exact agent version and scenario.

Maintainers review usefulness, trigger precision, license/provenance, requirements, resource links, script behavior, and external side effects. A skill must preserve the user's requested scope; it cannot authorize publishing, deletion, messaging, or account access on its own. CI parses content but never executes contributed skill scripts as part of building the catalog. Review script changes before running them locally.
