# S2C OpenTelemetry: implemented local trace boundary

The `scripts/s2c_run.py` orchestrator now runs the source audit, browser capture or snapshot replay, assistive projection, optional experimental attention, browser rubric, and HTML renderer under one trace. The existing standalone scripts remain usable without OpenTelemetry. This is a local implementation; no hosted S2C account, API, MCP endpoint, queue, model review, or production collector has been deployed.

## Run with OTLP/HTTP

Install the optional packages from the repository root:

```powershell
python -m pip install -r skills/scan-to-comprehend/observability/requirements.txt
```

Start a local `otelcol-contrib` Collector with `observability/collector.local.yaml` (resolve this path relative to the skill directory). The Collector accepts OTLP/HTTP on `127.0.0.1:4318` and applies an attribute allowlist before its local debug exporter. It is a development configuration; replace the debug exporter and review network binding, storage, access, and retention before using it with real accounts.

```powershell
python skills/scan-to-comprehend/scripts/s2c_run.py `
  --url https://example.com/ `
  --output tmp/s2c-example `
  --otel `
  --otlp-endpoint http://127.0.0.1:4318/v1/traces
```

For a repeatable offline run using an existing source result and Chromium snapshot:

```powershell
python skills/scan-to-comprehend/scripts/s2c_run.py `
  --source-json path/to/audit.json `
  --snapshot path/to/snapshot.json `
  --output tmp/s2c-replay `
  --otel `
  --otlp-endpoint http://127.0.0.1:4318/v1/traces
```

For a skill-folder-only installation, install `observability/requirements.txt` from inside that folder. The output directory must be new or empty. It contains `run.json`, `audit.json`, `capture/snapshot.json`, `assistive.json`, `browser-rubric.json`, optional `capture/attention.json`, and `report.html`. Fresh URL/HTML runs and replay with `--raw-html-file` also save `source.html`; `run.json` records its SHA-256 digest. The manifest also records the run ID, trace ID, audit date, rubric version, and artifact names. The URL stays in that local manifest and report; it does not become a trace attribute. Protect and retain source HTML and other artifacts according to the later hosted account policy.

## Trace contract

The root span is `s2c.run`. Stage spans include `s2c.robots_preflight` for live URLs, `s2c.source_audit`, `s2c.capture`, `s2c.projection.assistive`, optional `s2c.projection.attention_experiment`, `s2c.rules.browser`, and `s2c.report.render`. The capture span covers the child browser process as a timed operation and records only request and block counts from the guarded public URL render; the JavaScript process is not independently instrumented yet. A reused snapshot is marked with `s2c.stage.mode=reuse`.

Attributes are allowlisted in `s2c_telemetry.py` and again in the sample Collector. They contain run ID, input/mode, method version, counts, and artifact size. Raw URL, page text, screenshot, prompt, path, account identity, and exception message are excluded. Errors record only the exception class and error status; the Python SDK's automatic exception recording is disabled. A requested OTLP endpoint must be explicit through `--otlp-endpoint` or `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`; ordinary skill use sends no telemetry.

`telemetry.export_accepted` in `run.json` means the SDK flushed and the configured OTLP HTTP endpoint accepted at least one span batch without an exporter failure. A requested export that fails makes the command exit with status 3. This does **not** prove a downstream backend retained the spans. Verify arrival and retention in the Collector/backend before claiming a production trace guarantee. The opt-in local OTLP test starts an HTTP receiver, decodes the exported protobuf, and confirms parent/child linkage; the normal in-memory test checks that a deliberately sensitive URL and exception message are absent.

## Hosted release work still required

The future hosted service needs ingress-to-queue context propagation, capture-worker and model-call instrumentation, metrics for queue delay and resource/cost usage, tenant-safe trace access, export failure alerting, collector/backend monitoring, retention rules, and redaction tests using representative hostile pages. An end-to-end trace and sensitive-data check are launch gates for that service. The local implementation is the first slice, not that completed gate.

## Primary references

- OpenTelemetry Python instrumentation: https://opentelemetry.io/docs/languages/python/instrumentation/
- OTLP Python exporter: https://opentelemetry.io/docs/languages/python/exporters/
- W3C context propagation: https://opentelemetry.io/docs/concepts/context-propagation/
- Collector sensitive-data processing: https://opentelemetry.io/docs/security/handling-sensitive-data/
