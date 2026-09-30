---
name: csv-profile
description: Analyze a local CSV for nulls, inferred-type conflicts, malformed rows, duplicates, whitespace, category variants, and numeric outliers, then generate an interactive HTML, Markdown, or JSON quality report. Use before importing, modeling, or cleaning a CSV; does not repair records automatically.
license: MIT
---

# Profile a CSV

Create a read-only data-quality observation. Prefer the interactive HTML report when the user wants to inspect patterns and drill into columns. Use Markdown for a compact review artifact, and JSON for downstream automation.

Run the analyzer with an explicit input and output:

```sh
python scripts/analyze_csv.py /path/to/input.csv --format html --output /path/to/input.profile.html
python scripts/analyze_csv.py /path/to/input.csv --format markdown --output /path/to/input.profile.md
```

Resolve the script and its assets relative to this skill folder. Read [report formats](references/report-formats.md) for output choice and CLI options. Read [interpretation notes](references/interpretation.md) before turning detected signals into recommendations.

The HTML should lead with the overall quality signal, then ranked findings, searchable column diagnostics, sampled issue rows, and transparent method limits. It is standalone and works offline. Generate it in a user-accessible project or artifact directory and open or link it after generation when the environment supports that.

Exclude raw values by default. Use `--include-values` only when row-level values materially help the requested analysis and the local report can be handled like the source CSV. Never claim that an outlier, inferred-type conflict, or high score proves a record is wrong or a dataset is fit for use.

Report the strongest findings, the affected columns, relevant counts or rates, and the generated artifact path. Suggest specific validation or cleaning steps, but do not alter the CSV unless the user separately asks for repair.
