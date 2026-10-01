# Design-system schema

`design-system.json` uses schema version `1.0` and records the input summary, assumptions, selected direction and rationale, all nine design domains, provenance, and validation results.

Required top-level keys are `schema_version`, `name`, `generated_at`, `brief`, `assumptions`, `direction`, `color`, `typography`, `components`, `layout`, `elevation`, `guardrails`, `responsive`, `agent_prompt`, and `provenance`.

Colors use six-digit hexadecimal values. `color.roles` defines background, surface, surface_alt, text, text_muted, border, primary, primary_text, danger, danger_text, success, and focus. `color.contrast_pairs` declares intended foreground/background combinations and minimum ratios.

Typography defines display, heading, body, and mono families plus a modular scale. Components enumerate required interaction states. Responsive rules have a condition and behavior. Provenance assigns a status to generated domains.
