#!/usr/bin/env python3
"""Run the existing S2C stages together, optionally exporting privacy-bounded OTLP traces."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

import s2c_audit
import s2c_assistive
import s2c_browser_rubric
import s2c_visualize
from s2c_telemetry import Telemetry


SCRIPTS = Path(__file__).resolve().parent


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def copy_capture(snapshot_path: Path, capture_dir: Path) -> dict:
    source = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if source.get("schema") != "s2c-browser-capture/v1" or not source.get("frames"):
        raise ValueError("Expected a non-empty s2c-browser-capture/v1 snapshot")
    capture_dir.mkdir(parents=True, exist_ok=True)
    for frame in source["frames"]:
        name = frame.get("image")
        if not isinstance(name, str) or Path(name).name != name:
            raise ValueError("Capture image must be a filename inside the snapshot directory")
        image = snapshot_path.parent / name
        if image.resolve() != (snapshot_path.parent.resolve() / name):
            raise ValueError("Capture image must stay inside the snapshot directory")
        shutil.copyfile(image, capture_dir / name)
    write_json(capture_dir / "snapshot.json", source)
    return source


def run(args: argparse.Namespace) -> dict:
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output directory must be new or empty")
    if not args.url and (not args.source_json or not args.snapshot):
        raise ValueError("Give --url, or both --source-json and --snapshot for replay")
    if args.source_json and not args.snapshot:
        raise ValueError("--source-json requires --snapshot")
    output.mkdir(parents=True, exist_ok=True)
    telemetry = Telemetry.create(args.otel, args.otlp_endpoint)
    run_id = uuid.uuid4().hex
    trace_id = None
    report_path = output / "report.html"
    capture_dir = output / "capture"
    try:
        with telemetry.span("s2c.run", {
            "s2c.run.id": run_id, "s2c.mode": "rules",
            "s2c.input.kind": "replay" if args.snapshot else "url",
        }) as root:
            trace_id = Telemetry.trace_id(root)
            with telemetry.span("s2c.source_audit", {
                "s2c.stage.mode": "reuse" if args.source_json else "fetch",
            }) as span:
                if args.source_json:
                    audit = json.loads(args.source_json.read_text(encoding="utf-8"))
                else:
                    document = s2c_audit.fetch(args.url)
                    audit = {"schema_version": "1.1", "audited_on": datetime.now(timezone.utc).date().isoformat(),
                             "reports": [s2c_audit.audit_html(document, args.url)]}
                if audit.get("schema_version") != "1.1" or not audit.get("reports"):
                    raise ValueError("Expected S2C source audit schema_version 1.1")
                write_json(output / "audit.json", audit)
                span.set_attribute("s2c.source.finding_count", sum(len(r.get("findings", [])) for r in audit["reports"]))

            with telemetry.span("s2c.capture", {
                "s2c.stage.mode": "reuse" if args.snapshot else "browser",
            }) as span:
                if args.snapshot:
                    snapshot = copy_capture(args.snapshot, capture_dir)
                else:
                    capture_dir.mkdir(parents=True, exist_ok=True)
                    subprocess.run(["node", str(SCRIPTS / "s2c_browser_capture.mjs"),
                                    "--url", args.url, "--out", str(capture_dir)],
                                   check=True, capture_output=True, text=True, cwd=SCRIPTS.parents[2])
                    snapshot = json.loads((capture_dir / "snapshot.json").read_text(encoding="utf-8"))
                span.set_attribute("s2c.capture.frame_count", len(snapshot["frames"]))
                span.set_attribute("s2c.capture.bytes", (capture_dir / "snapshot.json").stat().st_size)

            with telemetry.span("s2c.projection.assistive"):
                assistive = s2c_assistive.project(snapshot)
                write_json(output / "assistive.json", assistive)

            attention = None
            if not args.skip_attention:
                # Load Pillow only for this optional projection.
                import s2c_browser_to_attention
                import s2c_attention
                with telemetry.span("s2c.projection.attention_experiment") as span:
                    attention_capture = s2c_browser_to_attention.project(snapshot, capture_dir)
                    write_json(capture_dir / "attention-capture.json", attention_capture)
                    attention = s2c_attention.render(capture_dir / "attention-capture.json",
                                                     capture_dir / "attention.json")
                    span.set_attribute("s2c.attention.frame_count", len(attention["frames"]))

            with telemetry.span("s2c.rules.browser") as span:
                config_path = args.rubric_config or s2c_browser_rubric.DEFAULT_CONFIG
                config = json.loads(config_path.read_text(encoding="utf-8"))
                rubric = s2c_browser_rubric.evaluate(snapshot, assistive, attention, config)
                write_json(output / "browser-rubric.json", rubric)
                span.set_attribute("s2c.rubric.version", rubric["rubric_version"])
                for status in ("pass", "warning", "review", "not_checked"):
                    span.set_attribute(f"s2c.rule.{status}_count", rubric["counts"][status])

            with telemetry.span("s2c.report.render") as span:
                html = s2c_visualize.render(audit, attention=attention,
                                            attention_dir=capture_dir if attention else None,
                                            assistive=assistive, assistive_dir=capture_dir,
                                            rubric=rubric)
                report_path.write_text("\n".join(line.rstrip() for line in html.splitlines()) + "\n", encoding="utf-8")
                span.set_attribute("s2c.report.bytes", report_path.stat().st_size)

        manifest = {"schema": "s2c-run/v1", "run_id": run_id, "trace_id": trace_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "url": snapshot["url"], "audited_on": snapshot["audited_on"],
                    "mode": "rules", "rubric_version": rubric["rubric_version"],
                    "telemetry": {"enabled": args.otel, "export_accepted": telemetry.finish()},
                    "artifacts": {"report": "report.html", "source": "audit.json",
                                  "capture": "capture/snapshot.json", "assistive": "assistive.json",
                                  "browser_rubric": "browser-rubric.json",
                                  "attention": "capture/attention.json" if attention else None}}
        write_json(output / "run.json", manifest)
        return manifest
    except Exception:
        telemetry.finish()
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="Public HTML URL for source audit and browser capture")
    parser.add_argument("--source-json", type=Path, help="Existing S2C source audit for offline replay")
    parser.add_argument("--snapshot", type=Path, help="Existing Chromium snapshot for offline replay")
    parser.add_argument("--output", required=True, type=Path, help="New or empty output directory")
    parser.add_argument("--rubric-config", type=Path, help="Versioned editable browser rubric config")
    parser.add_argument("--skip-attention", action="store_true", help="Skip the experimental attention layer")
    parser.add_argument("--otel", action="store_true", help="Export stage spans through OTLP/HTTP")
    parser.add_argument("--otlp-endpoint", help="Full OTLP traces URL, such as http://127.0.0.1:4318/v1/traces")
    args = parser.parse_args()
    try:
        result = run(args)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"S2C run failed: {error}", file=sys.stderr)
        return 2
    print(args.output.resolve() / result["artifacts"]["report"])
    if result["trace_id"]:
        print(f"trace_id={result['trace_id']}")
    if args.otel and not result["telemetry"]["export_accepted"]:
        print("S2C trace export was not accepted by the OTLP endpoint", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
