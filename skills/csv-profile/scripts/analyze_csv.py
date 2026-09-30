"""Create privacy-conscious HTML, Markdown, or JSON CSV quality reports."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any

NULL_TOKENS = {"", "na", "n/a", "null", "none", "nan", "missing", "not available", "not_available", "?", "-", "--"}
MAX_UNIQUES = 10_000
MAX_NUMERIC_SAMPLE = 50_000
MAX_VARIANTS = 2_000
ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"


def _percent(part: int | float, whole: int | float) -> float:
    return round((part / whole * 100) if whole else 0.0, 2)


def _classify(value: str) -> tuple[str, float | None]:
    raw = value.strip()
    lower = raw.lower()
    if lower in {"true", "false", "yes", "no", "y", "n"}:
        return "boolean", None
    if re.fullmatch(r"[+-]?0\d+", raw):
        return "string", None
    if re.fullmatch(r"[+-]?(?:0|[1-9]\d*)", raw):
        return "integer", float(raw)
    try:
        number = float(raw)
        if math.isfinite(number):
            return "number", number
    except ValueError:
        pass
    formatted = re.fullmatch(r"[€£$]?\s*([+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*(%)?", raw)
    if formatted:
        number = float(formatted.group(1).replace(",", ""))
        if formatted.group(2):
            number /= 100
        return "formatted-number", number
    for label, formats in (
        ("datetime", ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ")),
        ("date", ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y")),
    ):
        for fmt in formats:
            try:
                datetime.strptime(raw, fmt)
                return label, None
            except ValueError:
                continue
    return "string", None


def _family(label: str) -> str:
    if label in {"integer", "number", "formatted-number"}:
        return "numeric"
    if label in {"date", "datetime"}:
        return "temporal"
    return label


def _quantile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] * (high - position) + ordered[high] * (position - low)


def _display_number(value: float | None) -> float | int | None:
    if value is None:
        return None
    rounded = round(value, 6)
    return int(rounded) if rounded.is_integer() else rounded


def analyze(
    path: str | Path,
    delimiter: str = ",",
    encoding: str = "utf-8-sig",
    null_tokens: set[str] | None = None,
    include_values: bool = False,
    row_sample_limit: int = 120,
) -> dict[str, Any]:
    source = Path(path)
    tokens = {token.casefold() for token in (null_tokens or NULL_TOKENS)}
    headers: list[str] = []
    states: list[dict[str, Any]] = []
    width_issues: list[dict[str, Any]] = []
    sampled_rows: list[dict[str, Any]] = []
    duplicate_rows = 0
    row_count = 0
    valid_row_count = 0
    width_issue_count = 0
    row_hashes: set[str] = set()

    with source.open(encoding=encoding, newline="") as stream:
        reader = csv.reader(stream, delimiter=delimiter, strict=True)
        headers = next(reader, [])
        states = [
            {
                "missing": 0, "whitespace": 0, "types": Counter(), "families": Counter(),
                "uniques": set(), "uniques_capped": False, "numeric": [],
                "numeric_min": None, "numeric_max": None, "length_min": None,
                "length_max": None, "length_total": 0, "variants": defaultdict(Counter),
                "variant_capped": False,
            }
            for _ in headers
        ]
        for row_number, row in enumerate(reader, start=2):
            row_count += 1
            digest = hashlib.sha256("\x1f".join(row).encode("utf-8", errors="replace")).hexdigest()
            if digest in row_hashes:
                duplicate_rows += 1
            else:
                row_hashes.add(digest)
            if len(row) != len(headers):
                width_issue_count += 1
                if len(width_issues) < row_sample_limit:
                    width_issues.append({"row": row_number, "expected": len(headers), "actual": len(row)})
                continue
            valid_row_count += 1
            row_issues: list[dict[str, Any]] = []
            for index, value in enumerate(row):
                state = states[index]
                stripped = value.strip()
                if stripped.casefold() in tokens:
                    state["missing"] += 1
                    row_issues.append({"column": headers[index], "issue": "null"})
                    continue
                if value != stripped:
                    state["whitespace"] += 1
                    row_issues.append({"column": headers[index], "issue": "surrounding whitespace"})
                kind, numeric = _classify(value)
                family = _family(kind)
                state["types"][kind] += 1
                state["families"][family] += 1
                if len(state["uniques"]) < MAX_UNIQUES:
                    state["uniques"].add(value)
                else:
                    state["uniques_capped"] = True
                length = len(value)
                state["length_min"] = length if state["length_min"] is None else min(state["length_min"], length)
                state["length_max"] = length if state["length_max"] is None else max(state["length_max"], length)
                state["length_total"] += length
                if numeric is not None:
                    state["numeric_min"] = numeric if state["numeric_min"] is None else min(state["numeric_min"], numeric)
                    state["numeric_max"] = numeric if state["numeric_max"] is None else max(state["numeric_max"], numeric)
                    if len(state["numeric"]) < MAX_NUMERIC_SAMPLE:
                        state["numeric"].append(numeric)
                if family == "string" and not state["variant_capped"]:
                    normalized = re.sub(r"\s+", " ", stripped).casefold()
                    state["variants"][normalized][value] += 1
                    if len(state["variants"]) >= MAX_VARIANTS:
                        state["variant_capped"] = True
            if row_issues and len(sampled_rows) < row_sample_limit:
                sample: dict[str, Any] = {"row": row_number, "issues": row_issues}
                if include_values:
                    sample["values"] = row
                sampled_rows.append(sample)

    columns: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    total_cells = valid_row_count * len(headers)
    total_missing = total_type_issues = total_whitespace = 0
    for index, (header, state) in enumerate(zip(headers, states)):
        non_null = valid_row_count - state["missing"]
        dominant_family, dominant_count = state["families"].most_common(1)[0] if state["families"] else ("empty", 0)
        type_issues = non_null - dominant_count
        total_missing += state["missing"]
        total_type_issues += type_issues
        total_whitespace += state["whitespace"]
        q1 = _quantile(state["numeric"], 0.25)
        q3 = _quantile(state["numeric"], 0.75)
        med = median(state["numeric"]) if state["numeric"] else None
        outlier_count = 0
        if q1 is not None and q3 is not None:
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            outlier_count = sum(value < lower or value > upper for value in state["numeric"])
        variants = [
            {"normalized": key, "values": [value for value, _ in counts.most_common(6)], "count": sum(counts.values())}
            for key, counts in state["variants"].items() if len(counts) > 1
        ]
        variants.sort(key=lambda item: item["count"], reverse=True)
        column = {
            "index": index, "name": header or f"Unnamed column {index + 1}", "raw_name": header,
            "inferred_type": dominant_family, "type_counts": dict(state["types"].most_common()),
            "non_null": non_null, "missing": state["missing"],
            "missing_percent": _percent(state["missing"], valid_row_count), "type_issues": type_issues,
            "whitespace": state["whitespace"], "unique": len(state["uniques"]),
            "unique_is_lower_bound": state["uniques_capped"],
            "unique_percent": _percent(len(state["uniques"]), non_null),
            "length": {"min": state["length_min"], "max": state["length_max"], "mean": round(state["length_total"] / non_null, 2) if non_null else None},
            "numeric": {
                "min": _display_number(state["numeric_min"]), "q1": _display_number(q1),
                "median": _display_number(med), "q3": _display_number(q3),
                "max": _display_number(state["numeric_max"]), "outliers": outlier_count,
                "sample_size": len(state["numeric"]),
            } if state["numeric"] else None,
            "case_or_spacing_variants": variants[:8], "variant_scan_capped": state["variant_capped"],
            "issue_count": state["missing"] + type_issues + state["whitespace"] + outlier_count,
            "key_candidate": bool(non_null == valid_row_count and len(state["uniques"]) == valid_row_count and not state["uniques_capped"]),
        }
        columns.append(column)
        if state["missing"]:
            issues.append({"severity": "high" if column["missing_percent"] >= 20 else "medium", "kind": "nulls", "column": column["name"], "count": state["missing"], "detail": f'{column["missing_percent"]}% missing'})
        if type_issues:
            issues.append({"severity": "high" if _percent(type_issues, non_null) >= 10 else "medium", "kind": "mixed types", "column": column["name"], "count": type_issues, "detail": f"Dominant family: {dominant_family}"})
        if outlier_count:
            issues.append({"severity": "medium", "kind": "numeric outliers", "column": column["name"], "count": outlier_count, "detail": "Outside 1.5× IQR in numeric sample"})
        if state["whitespace"]:
            issues.append({"severity": "low", "kind": "whitespace", "column": column["name"], "count": state["whitespace"], "detail": "Leading or trailing whitespace"})
        if variants:
            issues.append({"severity": "low", "kind": "category variants", "column": column["name"], "count": len(variants), "detail": "Case or spacing variants normalize to the same value"})

    duplicate_headers = [name for name, count in Counter(headers).items() if count > 1]
    empty_headers = sum(not name.strip() for name in headers)
    if width_issue_count:
        issues.append({"severity": "high", "kind": "row width", "column": None, "count": width_issue_count, "detail": "Rows have a different field count than the header"})
    if duplicate_rows:
        issues.append({"severity": "medium", "kind": "duplicate rows", "column": None, "count": duplicate_rows, "detail": "Exact duplicate records"})
    if duplicate_headers:
        issues.append({"severity": "high", "kind": "duplicate headers", "column": None, "count": len(duplicate_headers), "detail": ", ".join(duplicate_headers)})
    if empty_headers:
        issues.append({"severity": "high", "kind": "empty headers", "column": None, "count": empty_headers, "detail": "Unnamed columns"})
    severity_order = {"high": 0, "medium": 1, "low": 2}
    issues.sort(key=lambda item: (severity_order[item["severity"]], -item["count"], item.get("column") or ""))

    deductions = {
        "missing data": min(35, round(_percent(total_missing, total_cells) * 0.7, 1)),
        "mixed types": min(20, round(_percent(total_type_issues, max(total_cells - total_missing, 1)), 1)),
        "structural rows": min(20, round(_percent(width_issue_count, row_count) * 2.0, 1)),
        "duplicate rows": min(15, round(_percent(duplicate_rows, row_count) * 0.75, 1)),
        "header problems": min(10, float((len(duplicate_headers) + empty_headers) * 5)),
        "whitespace": min(5, round(_percent(total_whitespace, total_cells) * 0.25, 1)),
    }
    score = max(0, round(100 - sum(deductions.values())))
    return {
        "schema_version": "1.1", "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": {"name": source.name, "path": str(source.resolve()), "bytes": source.stat().st_size, "delimiter": delimiter, "encoding": encoding},
        "summary": {
            "rows": row_count, "rectangular_rows": valid_row_count, "columns": len(headers), "cells": total_cells, "missing": total_missing,
            "missing_percent": _percent(total_missing, total_cells), "duplicate_rows": duplicate_rows,
            "width_issues": width_issue_count, "mixed_type_values": total_type_issues,
            "quality_score": score, "status": "Strong" if score >= 90 else "Watch" if score >= 75 else "Needs attention",
            "issue_groups": len(issues),
        },
        "headers": {"duplicate": duplicate_headers, "empty": empty_headers}, "columns": columns,
        "issues": issues, "row_samples": sampled_rows, "width_issue_samples": width_issues,
        "privacy": {"values_included": include_values, "row_sample_limit": row_sample_limit},
        "methodology": {
            "null_tokens": sorted(tokens),
            "numeric_outliers": "Tukey fences (1.5× IQR) over up to 50,000 numeric values per column.",
            "type_detection": "Boolean, integer, number, formatted number, ISO/common date, datetime, then string.",
            "score_deductions": deductions,
            "limits": [
                f"Unique counts become lower bounds after {MAX_UNIQUES:,} distinct values per column.",
                f"Numeric distribution statistics sample the first {MAX_NUMERIC_SAMPLE:,} numeric values per column.",
                "Findings indicate data-quality risks; they do not establish business validity.",
            ],
        },
    }


def attach_semantic_review(report: dict[str, Any], review_path: str | Path) -> dict[str, Any]:
    """Attach a separately produced, aggregate-only semantic review."""
    path = Path(review_path)
    review = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(review, dict) or review.get("schema_version") != "1.0":
        raise ValueError("semantic review must use schema_version 1.0")
    if review.get("source", {}).get("name") != report["source"]["name"]:
        raise ValueError("semantic review source does not match the CSV filename")
    expected = [(column["index"], column["name"]) for column in report["columns"]]
    observed = [(column.get("index"), column.get("name")) for column in review.get("columns", [])]
    if expected != observed:
        raise ValueError("semantic review columns do not match the current CSV profile")
    if review.get("privacy", {}).get("raw_values_sent") is not False:
        raise ValueError("semantic review must declare raw_values_sent as false")
    report["semantic_review"] = review
    return report


def profile(path: str | Path, delimiter: str = ",") -> dict[str, Any]:
    report = analyze(path, delimiter=delimiter)
    return {
        "rows": report["summary"]["rows"], "columns": report["summary"]["columns"],
        "duplicate_headers": report["headers"]["duplicate"], "empty_headers": report["headers"]["empty"],
        "width_mismatches": report["summary"]["width_issues"],
        "missing_by_column_index": [column["missing"] for column in report["columns"]],
    }


def render_html(report: dict[str, Any]) -> str:
    template = (ASSET_DIR / "report-template.html").read_text(encoding="utf-8")
    styles = (ASSET_DIR / "report.css").read_text(encoding="utf-8") + "\n" + (ASSET_DIR / "semantic.css").read_text(encoding="utf-8")
    script = (ASSET_DIR / "report.js").read_text(encoding="utf-8")
    data = json.dumps(report, ensure_ascii=False).replace("</", "<\\/")
    return template.replace("/*__CSV_PROFILE_CSS__*/", styles).replace("/*__CSV_PROFILE_DATA__*/", data).replace("/*__CSV_PROFILE_JS__*/", script)


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        f'# CSV quality report: {report["source"]["name"]}', "", f'**{summary["status"]} · {summary["quality_score"]}/100**', "",
        f'Generated {report["generated_at"]}. Values included: {"yes" if report["privacy"]["values_included"] else "no"}.', "",
        "## Overview", "", "| Rows | Columns | Missing | Duplicates | Width issues | Mixed-type values |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
        f'| {summary["rows"]:,} | {summary["columns"]:,} | {summary["missing"]:,} ({summary["missing_percent"]}%) | {summary["duplicate_rows"]:,} | {summary["width_issues"]:,} | {summary["mixed_type_values"]:,} |', "",
        "## Priority findings", "",
    ]
    if report["issues"]:
        lines.extend(["| Severity | Issue | Column | Count | Detail |", "| --- | --- | --- | ---: | --- |"])
        for issue in report["issues"]:
            lines.append(f'| {issue["severity"].title()} | {issue["kind"]} | {issue.get("column") or "—"} | {issue["count"]:,} | {issue["detail"]} |')
    else:
        lines.append("No structural, missing-value, duplicate, whitespace, or inferred-type issues were detected.")
    lines.extend(["", "## Columns", "", "| Column | Inferred type | Missing | Unique | Type issues | Outliers |", "| --- | --- | ---: | ---: | ---: | ---: |"])
    for column in report["columns"]:
        unique = f'≥{column["unique"]:,}' if column["unique_is_lower_bound"] else f'{column["unique"]:,}'
        outliers = column["numeric"]["outliers"] if column["numeric"] else 0
        lines.append(f'| {column["name"]} | {column["inferred_type"]} | {column["missing"]:,} ({column["missing_percent"]}%) | {unique} | {column["type_issues"]:,} | {outliers:,} |')
    review = report.get("semantic_review")
    if review:
        threshold = review["policy"]["confidence_threshold"]
        lines.extend([
            "", "## Laya semantic review", "",
            f'**Shadow mode · confidence threshold {threshold:.0%}.** These typed decisions annotate the deterministic profile; they do not change its findings or score.', "",
            "| Column | Suggested role | Confidence | Review priority | Confidence | Gate |",
            "| --- | --- | ---: | --- | ---: | --- |",
        ])
        for item in review["columns"]:
            role = item["semantic_role"]
            priority = item["review_priority"]
            lines.append(
                f'| {item["name"]} | {role["label"]} | {role["confidence"]:.1%} | '
                f'{priority["label"]} | {priority["confidence"]:.1%} | {item["gate"]} |'
            )
        lines.extend(["", f'Model: `{review["engine"]["model"]}`. Input: column names and aggregate profile statistics only; raw values sent: no.'])
    lines.extend(["", "## How to read this report", "", report["methodology"]["numeric_outliers"], "", "Quality score deductions:"])
    lines.extend(f"- {label}: −{points} points" for label, points in report["methodology"]["score_deductions"].items())
    lines.append("")
    lines.extend(f'- {limit}' for limit in report["methodology"]["limits"])
    return "\n".join(lines) + "\n"


def main(default_format: str = "html") -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="CSV file to analyze")
    parser.add_argument("--format", choices=("html", "markdown", "json"), default=default_format)
    parser.add_argument("--output", help="Output path; stdout for JSON when omitted")
    parser.add_argument("--delimiter", default=",")
    parser.add_argument("--encoding", default="utf-8-sig")
    parser.add_argument("--include-values", action="store_true", help="Include values for sampled issue rows in the local report")
    parser.add_argument("--row-sample-limit", type=int, default=120)
    parser.add_argument("--null-token", action="append", dest="extra_null_tokens", default=[])
    parser.add_argument("--semantic-review", help="Attach aggregate-only Laya review JSON produced by integrations/laya/laya_review.mjs")
    args = parser.parse_args()
    if len(args.delimiter) != 1:
        parser.error("--delimiter must be one character")
    if args.row_sample_limit < 0 or args.row_sample_limit > 2_000:
        parser.error("--row-sample-limit must be between 0 and 2000")
    try:
        tokens = NULL_TOKENS | {token.casefold() for token in args.extra_null_tokens}
        report = analyze(args.path, args.delimiter, args.encoding, tokens, args.include_values, args.row_sample_limit)
        if args.semantic_review:
            attach_semantic_review(report, args.semantic_review)
        content = json.dumps(report, indent=2, ensure_ascii=False) + "\n" if args.format == "json" else render_markdown(report) if args.format == "markdown" else render_html(report)
        if args.output:
            output = Path(args.output)
        elif args.format == "html":
            output = Path(args.path).with_suffix(".profile.html")
        elif args.format == "markdown":
            output = Path(args.path).with_suffix(".profile.md")
        else:
            print(content, end="")
            return
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
        print(output.resolve())
    except (OSError, UnicodeError, csv.Error, ValueError) as error:
        parser.exit(1, f"Unable to profile CSV: {error}\n")


if __name__ == "__main__":
    main()
