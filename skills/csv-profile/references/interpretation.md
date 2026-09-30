# Interpreting a profile

Counts exclude the header. Physical line count can differ from record count when quoted fields contain newlines. Width mismatches are counted separately, and their cells are excluded from column statistics. Duplicate headers are reported exactly as written. Empty header names are counted and displayed with a positional fallback.

## Signals

- **Nulls:** empty strings and the configured null vocabulary, case-insensitively.
- **Types:** boolean, integer, number, formatted number, common/ISO date, datetime, then string. Related types roll into numeric or temporal families. A type issue is a non-null value outside the column's dominant family.
- **Outliers:** values outside Tukey's 1.5× IQR fences. This is a review signal, not proof of an error.
- **Variants:** strings that become equal after trimming, collapsing whitespace, and case-folding.
- **Duplicates:** exact full-row duplicates, detected with a SHA-256 digest. The report stores counts rather than row contents.
- **Key candidates:** complete, uncapped columns whose observed values are all unique.

## Sampling and privacy

The scan counts rows, nulls, types, whitespace, and duplicates across the full file. Unique-value tracking caps at 10,000 distinct values per column; numeric distribution statistics use the first 50,000 numeric values. The report states these limits.

HTML and Markdown exclude raw values by default. `--include-values` adds values for sampled issue rows to the generated local artifact, so treat that artifact like the source CSV. No report code makes network requests.

The 0–100 score is a transparent triage aid. It deducts bounded points for missing data, mixed types, malformed rows, duplicate rows, header problems, and whitespace. It does not measure semantic correctness, fitness for a particular model, bias, provenance, or compliance.
