# Report formats

Use `scripts/analyze_csv.py` for new work. Resolve it and its asset files relative to this skill folder.

## HTML

```sh
python scripts/analyze_csv.py input.csv --format html --output input.profile.html
```

The result is a standalone interactive file with no external fonts, libraries, trackers, or network requests. It contains a summary, transparent quality-score deductions, ranked findings, searchable column diagnostics, row issue samples, print styles, and light/dark themes. Raw values are excluded unless `--include-values` is present.

## Markdown

```sh
python scripts/analyze_csv.py input.csv --format markdown --output input.profile.md
```

Use Markdown for code review, issue trackers, terminal workflows, or when the user asks for a compact text artifact. It includes the same aggregate signals and limitations without interactive controls.

## JSON

```sh
python scripts/analyze_csv.py input.csv --format json --output input.profile.json
```

Use JSON as an integration format. The legacy `scripts/profile_csv.py input.csv` command still prints the compact JSON shape expected by earlier callers.

## Options

- `--delimiter ';'`: specify a one-character delimiter.
- `--encoding cp1252`: specify an input encoding.
- `--null-token UNKNOWN`: add a domain-specific null token; repeat as needed.
- `--include-values`: include values for sampled issue rows in the local artifact.
- `--row-sample-limit 250`: change the issue-row sample size, from 0 through 2,000.

Do not publish an HTML report with included values unless the user explicitly intends to share those records.
