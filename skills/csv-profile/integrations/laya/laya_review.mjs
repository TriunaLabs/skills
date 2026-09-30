#!/usr/bin/env node
import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import process from "node:process";

function usage(message) {
  if (message) console.error(message);
  console.error("Usage: node laya_review.mjs <profile.json> <review.json> [--threshold 0.80] [--model-dir PATH] [--cache-dir PATH]");
  process.exit(message ? 2 : 0);
}

function parseArgs(argv) {
  const positional = [];
  const options = { threshold: 0.8 };
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];
    if (value === "--help" || value === "-h") usage();
    if (value === "--threshold") options.threshold = Number(argv[++index]);
    else if (value === "--model-dir") options.modelDir = argv[++index];
    else if (value === "--cache-dir") options.cacheDir = argv[++index];
    else if (value.startsWith("--")) usage(`Unknown option: ${value}`);
    else positional.push(value);
  }
  if (positional.length !== 2) usage("Expected an input profile and output review path.");
  if (!Number.isFinite(options.threshold) || options.threshold < 0.5 || options.threshold > 1) usage("--threshold must be between 0.5 and 1.");
  return { input: positional[0], output: positional[1], ...options };
}

function decision(answer) {
  const probabilities = answer?.probabilities ?? {};
  const label = String(answer?.choice ?? "unknown");
  const confidence = Number(probabilities[label] ?? answer?.confidence ?? 0);
  return { label, confidence, probabilities };
}

function stateFor(report, column) {
  return {
    dataset: report.source.name,
    row_count: report.summary.rows,
    column_name: column.name,
    inferred_technical_type: column.inferred_type,
    completeness_percent: 100 - column.missing_percent,
    distinct_count: column.unique,
    distinct_percent: column.unique_percent,
    key_candidate: column.key_candidate,
    type_conflict_count: column.type_issues,
    whitespace_count: column.whitespace,
    numeric_outlier_count: column.numeric?.outliers ?? 0,
    minimum_length: column.length.min,
    maximum_length: column.length.max,
  };
}

const QUESTIONS = {
  semantic_role: {
    type: "choice",
    instructions: "Choose the most likely semantic role for this CSV column. Use unknown when the aggregate profile does not support a reliable role.",
    criteria: {
      identifier: "A key, code, account number, row identifier, or other label used to distinguish entities.",
      measure: "A numeric amount, count, rate, quantity, or continuous measurement.",
      timestamp: "A date, time, year, duration, or event-time field.",
      category: "A bounded class, status, flag, group, or low-cardinality label.",
      free_text: "Names, descriptions, comments, addresses, or other unconstrained text.",
      unknown: "The role is ambiguous from the column name and aggregate statistics."
    }
  },
  review_priority: {
    type: "choice",
    instructions: "Suggest a review priority from this aggregate quality evidence. This is advisory and must not override deterministic validation.",
    criteria: {
      routine: "No strong aggregate signal requires focused manual review.",
      inspect: "A human should inspect the column before relying on it.",
      resolve: "Resolve likely quality or schema problems before production use."
    }
  }
};

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const profile = JSON.parse(await readFile(options.input, "utf8"));
  if (!Array.isArray(profile.columns) || !profile.source?.name || !profile.summary) usage("Input is not a csv-profile JSON report.");

  let Laya;
  try {
    ({ Laya } = await import("@receptron/laya"));
  } catch (error) {
    console.error("Install the optional runtime first with `npm install` in integrations/laya.");
    throw error;
  }
  const loadOptions = {};
  if (options.modelDir) loadOptions.modelDir = options.modelDir;
  if (options.cacheDir) loadOptions.cacheDir = options.cacheDir;
  const laya = await Laya.load(loadOptions);
  const columns = [];
  try {
    for (const column of profile.columns) {
      const state = stateFor(profile, column);
      const result = await laya.systemOne(state, QUESTIONS);
      const semanticRole = decision(result.answers.semantic_role);
      const reviewPriority = decision(result.answers.review_priority);
      columns.push({
        index: column.index,
        name: column.name,
        semantic_role: semanticRole,
        review_priority: reviewPriority,
        gate: Math.min(semanticRole.confidence, reviewPriority.confidence) >= options.threshold ? "accepted" : "review"
      });
    }
  } finally {
    await laya.close();
  }

  const inputSignature = createHash("sha256").update(JSON.stringify(profile.columns.map((column) => stateFor(profile, column)))).digest("hex");
  const review = {
    schema_version: "1.0",
    generated_at: new Date().toISOString(),
    source: { name: profile.source.name, profile_schema_version: profile.schema_version, aggregate_sha256: inputSignature },
    engine: { name: "Laya", runtime: "@receptron/laya@0.1.2", model: options.modelDir ?? "receptron/laya-onnx@main" },
    policy: { mode: "shadow", confidence_threshold: options.threshold, low_confidence_action: "review" },
    privacy: { raw_values_sent: false, input: "column names and aggregate profile statistics" },
    columns
  };
  await writeFile(options.output, `${JSON.stringify(review, null, 2)}\n`, "utf8");
  console.log(options.output);
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
});
