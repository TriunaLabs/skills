# Sources and license audit

Audit date: 2026-10-01.

This package is an original TriunaLabs implementation. It adopts the general architecture of searchable design guidance, deterministic generation, persisted systems, and an open-core product boundary after reviewing `nextlevelbuilder/ui-ux-pro-max-skill`. No code, datasets, palettes, font catalog, prose, templates, or generated assets were copied from that project.

The reviewed project's root license and package metadata identify MIT. Its history included a conflicting CLI README declaration that was reported in issue 481 and subsequently corrected. A nested `ui-styling` skill also carries an Apache-2.0 license. Because no material was imported, those licenses do not flow into this package. Future imports require a per-file license and provenance review rather than relying on the repository badge.

Primary references used for independent implementation:

- Design Tokens Community Group, Design Tokens Format Module 2025.10: https://www.designtokens.org/TR/2025.10/format/
- W3C WAI, WCAG 2.2 understanding documents: https://www.w3.org/WAI/WCAG22/Understanding/
- W3C WAI, Contrast Minimum: https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
- W3C WAI, Focus Visible: https://www.w3.org/WAI/WCAG22/Understanding/focus-visible
- W3C WAI, Target Size Enhanced: https://www.w3.org/WAI/WCAG22/Understanding/target-size-enhanced
- MDN, `prefers-reduced-motion`: https://developer.mozilla.org/docs/Web/CSS/@media/prefers-reduced-motion

The generated `tokens.json` follows the DTCG `$value`, `$type`, and `$description` shape for the supported color, dimension, font-family, and shadow tokens. The broader `design-system.json` is a TriunaLabs workflow artifact, not a claim of DTCG conformance.
