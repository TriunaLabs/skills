# Laya semantic review

The Laya stage follows the same separation used in the Jev demos: ordinary code collects evidence, a typed decision model interprets a bounded state, and the application owns the gate. The deterministic CSV profiler remains the source of truth for counts, inferred technical types, and quality findings.

## What is sent to Laya

Each column is reviewed independently with its name and aggregate statistics: technical type, completeness, distinctness, key-candidate status, conflict counts, whitespace counts, outlier count, and value-length range. Raw cell values, sampled rows, category labels, and source paths are excluded.

Laya answers two small choice questions:

- likely semantic role: identifier, measure, timestamp, category, free text, or unknown;
- review priority: routine, inspect, or resolve.

Both answers must meet the configured threshold for the column to display as `accepted`; otherwise it displays as `review`. This is a presentation gate only. It does not change the profiler's findings, severity, or quality score.

## Runtime

The optional adapter uses Node.js 20+ and `@receptron/laya`, an ONNX Runtime implementation that works on Windows, macOS, and Linux. Its first run downloads about 1.7 GB of model weights and requires roughly 2 GB of memory for the loaded model. Pin a local model directory with `--model-dir` when reproducibility or offline reuse matters.

Install only when requested:

```sh
cd integrations/laya
npm install
node laya_review.mjs profile.json review.json --threshold 0.80
```

Use `--cache-dir` to control the model cache. The default model revision follows the runtime's upstream default; record and pin a local bundle for evaluated production workflows.

## Evaluation boundary

The base model is a starting point, not evidence that these two CSV questions are accurate. Before promoting any decision beyond shadow display:

1. Build a labeled set of representative columns without train/test overlap.
2. Measure accuracy and coverage at several confidence thresholds.
3. Inspect performance by semantic role, language, file source, and rare schema pattern.
4. Keep an explicit unknown/review path and retain deterministic fallbacks.
5. Version the question wording, model bundle, threshold, and evaluation set together.

Prefer fewer, clearly distinct answer choices. Large choice sets consume the model's option token budget and should be split into smaller staged questions.
