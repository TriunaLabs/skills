# TriunaLabs Agent Skills

A public library of focused, portable workflows for Claude Code, Codex, and other AI agents.

[Browse the catalog](https://triunalabs.github.io/skills/) · [Installation](docs/installation.md) · [Contribute](CONTRIBUTING.md)

## Ready workflows

| Skill | Purpose | Requirements |
| --- | --- | --- |
| [Release brief](skills/release-brief/SKILL.md) | Build release-confidence briefs with security, provenance, and PDF-ready reports | Python 3.10+; Git |
| [Profile a CSV](skills/csv-profile/SKILL.md) | Report structural and missing-value issues | Python 3.10+ |
| [Route an agent message](skills/route-agent-message/SKILL.md) | Route a change or question to relevant active sessions with delivery receipts | Python 3.10+; session registry and messaging transport |
| [Make a page answer-ready](skills/answer-ready-web/SKILL.md) | Audit or create evidence-backed landing pages for people, search, and retrieval systems | Python 3.10+ |
| [Review an interface with UX principles](skills/laws-of-ux/SKILL.md) | Produce evidence-backed UX findings, before/after comparisons, and annotated HTML posters | Python 3.10+ |
| [Create an interface design system](skills/create-interface-design-system/SKILL.md) | Generate semantic tokens, components, responsive rules, agent guidance, and a standalone specimen | Python 3.10+ |
| [Scan to Comprehend](skills/scan-to-comprehend/SKILL.md) | Design dense content and audit source-structure friction with explained suggestions | Python 3.10+ for optional audit |

These are original contributions prepared for this library, not exports of personal or installed skills. Packages marked `visibility: hidden` remain in source while they are developed, but are excluded from the public catalog and its downloadable build. Format compatibility is not an end-to-end runtime test or a performance claim. See each `catalog.json` for requirements, provenance, and compatibility status.

### Scan to Comprehend audit

The open S2C CLI checks headings, link labels, image alternatives, and table headers in HTML or Markdown. It returns observed weaknesses, narrow strengths, suggested fixes, and an experimental 0–100 **structural friction risk index**. The index has low confidence and is not a measured cognitive-load, gaze, accessibility, or comprehension score. It is unrelated to the web-performance metric Cumulative Layout Shift (CLS).

```sh
python skills/scan-to-comprehend/scripts/s2c_audit.py path/to/page.html --json
```

The JSON output is suitable for a bounded API or MCP wrapper. See the [audit contract](skills/scan-to-comprehend/references/audit-engine.md), [research boundaries](skills/scan-to-comprehend/references/evidence.md), and [pattern map](skills/scan-to-comprehend/references/patterns.md). The cited research informs what to inspect; the index weights are transparent editorial triage settings, not coefficients from a published model.

## Local development

Python 3.10+ is required for catalog tooling. Node is optional for npm command aliases.

```sh
python -m pip install -r requirements.txt
python scripts/validate.py
python -m unittest discover -s tests
python scripts/build.py
python -m http.server 4173 --directory dist
```

Open http://localhost:4173. The generated `dist/` contains the website, JSON catalog, and browsable skill files. Sources live in `site/` and `skills/`; never edit generated output. The build does not run skill scripts.

## Repository layout

- `skills/<name>/SKILL.md`: portable instructions, with scripts, references, or assets where useful.
- `skills/<name>/catalog.json`: catalog metadata, separate from portable frontmatter.
- `templates/`: skill submission starter.
- `scripts/`: validation and deterministic static build.
- `site/`: dependency-free accessible catalog UI.
- `.github/workflows/`: pull request checks and GitHub Pages deployment.

## Publishing

The Pages workflow deploys on pushes to `main` after checks pass. In repository Settings → Pages, choose GitHub Actions as the build source. The intended project URL is https://triunalabs.github.io/skills/. Relative links also support a future custom domain. No custom domain is configured by this code; see [deployment notes](docs/deployment.md).

## License and trust

MIT. Read a skill and its scripts before installing. Installing instructions does not grant tools, account access, or permission for external actions. Contributions must be redistributable and contain no secrets, private context, or unselected personal skills.
