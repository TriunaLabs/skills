---
name: csv-profile
description: Inspect a local CSV for structural and missing-value issues and produce an aggregate quality report. Use before importing or analyzing a CSV; does not infer sensitive attributes or repair records automatically.
license: MIT
---

# Profile a CSV

Produce a structural report without exposing raw records.

Run the bundled helper with an explicit file path:

```sh
python scripts/profile_csv.py /path/to/input.csv
```

Resolve the script relative to this skill folder, not the user's project. It emits JSON to stdout, reads UTF-8 with optional BOM, uses comma delimiters by default, and treats whitespace-only fields as empty. Use `--delimiter ';'` for semicolon-separated files. See [interpretation notes](references/interpretation.md) before drawing conclusions from malformed rows.

Report record count, duplicate header names, row-width issues, and missing-field counts. Avoid pasting raw records into the answer. Ask for an encoding or delimiter when parsing assumptions do not match the file. Do not silently rewrite or discard records. Suggest concrete import checks based on the report; absence of structural issues does not establish business validity.
