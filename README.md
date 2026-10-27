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
| [Scan to Comprehend](skills/scan-to-comprehend/SKILL.md) | Design dense content, audit source structure, and render page walkthroughs with optional assistive and section views | Python 3.10+ for audit/report; Node, Playwright, and Chrome or Chromium for assistive capture |

These are original contributions prepared for this library, not exports of personal or installed skills. Packages marked `visibility: hidden` remain in source while they are developed, but are excluded from the public catalog and its downloadable build. Format compatibility is not an end-to-end runtime test or a performance claim. See each `catalog.json` for requirements, provenance, and compatibility status.

### Scan to Comprehend audit

The open S2C CLI checks headings, link labels, image alternatives, and table headers in HTML or Markdown. It returns observed weaknesses, narrow strengths, suggested fixes, and an experimental 0–100 **structural friction risk index**. The index has low confidence and is not a measured cognitive-load, gaze, accessibility, or comprehension score. It is unrelated to the web-performance metric Cumulative Layout Shift (CLS).

```sh
python skills/scan-to-comprehend/scripts/s2c_audit.py path/to/page.html --json
```

The JSON output is suitable for a bounded API or MCP wrapper. A rendered-page walkthrough can embed actual captures and numbered reviewer callouts in a [self-contained HTML report](site/case-studies/jobfitiq-s2c.html); see the [visual-report workflow](skills/scan-to-comprehend/references/visual-report.md). The [JobFitIQ source-audit JSON](site/case-studies/jobfitiq-s2c.audit.json) remains separate from the rendered observations. See also the [audit contract](skills/scan-to-comprehend/references/audit-engine.md), [research boundaries](skills/scan-to-comprehend/references/evidence.md), [element-attention research plan](skills/scan-to-comprehend/references/element-attention-research.md), and [pattern map](skills/scan-to-comprehend/references/patterns.md). The cited research informs what to inspect; the index weights are transparent editorial triage settings, not coefficients from a published model. The element-attention model is a proposal, not a shipped predictor.

The [assistive reading view](skills/scan-to-comprehend/references/assistive-view.md) captures Chromium accessibility-tree and observed Tab paths at desktop, mobile, and 320 px widths. Its [dated JobFitIQ report](site/case-studies/jobfitiq-assistive-view.html) embeds the screenshots and review candidates. It is a browser projection, not a screen-reader recording or WCAG conformance result. The raw snapshot and versioned JSON are retained beside the report for repeatable processing.

The [reader projections](skills/scan-to-comprehend/references/reader-views.md) add deterministic crawler, passage retrieval, and cross-view gap panels to the same capture. An optional `--question` scores passages with local BM25; the runner exports `reader-views.json` beside its HTML report. These editorial views do not predict search ranking, AI citations, or observed gaze.

The local S2C playground visualizes a versioned scoring profile: browser checklist points, crawler element weights, BM25 passage settings, and the cross-view gap threshold. Change rules before a URL run or create saved scoring revisions afterward without capturing the site again. The HTML report shows its exact profile and fingerprint. See [scoring profiles and BM25 inputs](skills/scan-to-comprehend/references/reader-views.md#scoring-profile-and-saved-revisions).

The [page basics layer](skills/scan-to-comprehend/references/site-basics.md) adds one-run navigation timings, bounded same-origin link checks, broken in-page fragments, and contact/privacy/terms link discovery. Its results appear as separate review items, with coverage and limits visible; they do not change the S2C reading scores.

The [robot visibility review](skills/scan-to-comprehend/references/robot-visibility.md) compares important phrases and links in raw HTML with one no-interaction rendered DOM, and screens index directives and `robots.txt`. Findings feed the final action plan. Add `--important "phrase"` to a URL run, or use `--html-file page.html` for a self-contained offline prototype. The report comes from the versioned `s2c_visualize.py` renderer and `assets/report-shell.css` template; no generative model is required.

To try it locally after installing the audit dependencies, run `python playground/server.py` and open `http://127.0.0.1:8787/`. Runs and their scoring revisions are saved under the ignored `.playground-runs/` directory. A `?run=<id>` local link reopens a saved report after restarting the server. This loopback test server is not a public deployment.

For owned pages, the optional [section interaction probe](skills/scan-to-comprehend/references/interaction-signals.md) collects foreground viewport exposure, mouse hover, clicks, and taps after the host starts it. It has no camera, network request, or persistent storage. Pass consented session exports to `s2c_visualize.py --signals` to add a separately labeled observed-behavior section to the HTML report. These signals are not measured gaze or comprehension. The [attention baseline](skills/scan-to-comprehend/references/attention-baseline.md) adds a separate WCAG text contrast spot check and a held-out no-contrast comparison to test whether contrast contributes predictive value. The [AGD-to-audit guide](skills/scan-to-comprehend/references/agd-to-audit.md) translates the graphic-design attention paper into page observations, hypotheses, and reader checks without claiming to run its model.

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

The optional S2C browser probe has a separate Node test: `node --test tests/s2c_section_signals.test.cjs`.

### Local S2C audit playground

Run `python playground/server.py` and open `http://127.0.0.1:8787/`. Enter a public HTML URL or upload one self-contained `.html` prototype, plus an optional reader question and up to five important phrases. The site runs the source, browser, assistive, rubric, attention, crawler, robot visibility, retrieval, gap, and HTML report stages of `s2c_run.py`. View buttons navigate the report and a JSON link exposes the versioned projections. Uploaded HTML renders with JavaScript and external requests disabled; its extracted evidence and report remain in the ignored `.playground-runs/` directory until manually removed. The server listens on loopback only. This test interface is separate from a hosted anonymous service. It does not provide accounts, visitor quotas, ownership verification, or export controls. Review a page's terms before capturing it. A site can refuse automated capture.

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
