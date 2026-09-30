/** TypeScript contract for the zero-dependency report UI in report.js. */
export type Severity = "high" | "medium" | "low";

export interface CsvIssue {
  severity: Severity;
  kind: string;
  column: string | null;
  count: number;
  detail: string;
}

export interface NumericProfile {
  min: number | null;
  q1: number | null;
  median: number | null;
  q3: number | null;
  max: number | null;
  outliers: number;
  sample_size: number;
}

export interface ColumnProfile {
  index: number;
  name: string;
  raw_name: string;
  inferred_type: "numeric" | "temporal" | "boolean" | "string" | "empty";
  type_counts: Record<string, number>;
  non_null: number;
  missing: number;
  missing_percent: number;
  type_issues: number;
  whitespace: number;
  unique: number;
  unique_is_lower_bound: boolean;
  unique_percent: number;
  length: { min: number | null; max: number | null; mean: number | null };
  numeric: NumericProfile | null;
  case_or_spacing_variants: Array<{ normalized: string; values: string[]; count: number }>;
  variant_scan_capped: boolean;
  issue_count: number;
  key_candidate: boolean;
}

export interface CsvProfileReport {
  schema_version: "1.0";
  generated_at: string;
  source: { name: string; path: string; bytes: number; delimiter: string; encoding: string };
  summary: {
    rows: number; rectangular_rows: number; columns: number; cells: number; missing: number; missing_percent: number;
    duplicate_rows: number; width_issues: number; mixed_type_values: number;
    quality_score: number; status: "Strong" | "Watch" | "Needs attention"; issue_groups: number;
  };
  headers: { duplicate: string[]; empty: number };
  columns: ColumnProfile[];
  issues: CsvIssue[];
  row_samples: Array<{ row: number; issues: Array<{ column: string; issue: string }>; values?: string[] }>;
  width_issue_samples: Array<{ row: number; expected: number; actual: number }>;
  privacy: { values_included: boolean; row_sample_limit: number };
  methodology: {
    null_tokens: string[]; numeric_outliers: string; type_detection: string;
    score_deductions: Record<string, number>; limits: string[];
  };
}

declare global {
  interface Window {
    __CSV_PROFILE_REPORT__?: CsvProfileReport;
  }
}

export {};
