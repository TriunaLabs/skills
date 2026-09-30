# Interpreting a profile

Counts exclude the header. Physical line count can differ from record count when quoted fields contain newlines. Width mismatches are counted separately; missing-field totals cover only rows whose width matches the header. Duplicate names are reported without normalizing case or whitespace. Empty header names are counted, not renamed. Empty files have no header and zero data rows.

The helper does not guess encoding, detect duplicate records, establish unique keys, validate types, or sample personal values. A clean structural profile is not a data-quality certification. Very large files stream through memory, but unusually large individual fields may exceed Python's CSV field limit and produce an explicit error.
