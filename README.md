# TriunaLabs Agent Skills

A public library of focused, portable workflows for Claude Code, Codex, and other AI agents.

[Browse the catalog](https://triunalabs.github.io/skills/) · [Installation](docs/installation.md) · [Contribute](CONTRIBUTING.md)

## Original starter collection

| Skill | Purpose | Requirements |
| --- | --- | --- |
| [Decision record](skills/decision-record/SKILL.md) | Compare options and capture a revisitable decision | Project context |
| [Reproduce a bug](skills/reproduce-bug/SKILL.md) | Reduce a failure to a repeatable regression check | Project runtime / tests |
| [Release brief](skills/release-brief/SKILL.md) | Draft evidence-backed release communication | Git |
| [Profile a CSV](skills/csv-profile/SKILL.md) | Report structural and missing-value issues | Python 3.10+ |
| [Route an agent message](skills/route-agent-message/SKILL.md) | Route a change or question to relevant active sessions with delivery receipts | Python 3.10+; session registry and messaging transport |

All starters are original contributions prepared for this library, not exports of personal or installed skills. Version 0.1.0 is a starter release. Format compatibility is not an end-to-end runtime test or a performance claim. See each `catalog.json` for requirements, provenance, and compatibility status.

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
