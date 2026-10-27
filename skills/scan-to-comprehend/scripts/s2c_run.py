#!/usr/bin/env python3
"""Run the existing S2C stages together, optionally exporting privacy-bounded OTLP traces."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.robotparser import RobotFileParser
import uuid

import s2c_audit
import s2c_assistive
import s2c_browser_rubric
import s2c_reader_views
import s2c_robot_visibility
import s2c_scoring_profile
import s2c_site_basics
import s2c_visualize
from s2c_telemetry import Telemetry


SCRIPTS = Path(__file__).resolve().parent


def public_robots_preflight(url: str) -> dict:
    """Decline a live URL when its robots policy cannot be verified or forbids S2C."""
    robots = s2c_robot_visibility.fetch_robots(url)
    if robots["status"] not in {"retrieved", "absent"}:
        raise ValueError("robots.txt could not be checked; retry when it is available")
    if robots["status"] == "retrieved":
        parser = RobotFileParser()
        parser.parse(robots["text"].splitlines())
        if not parser.can_fetch("S2C-Audit/1.0", url):
            raise ValueError("robots.txt disallows S2C-Audit at this URL")
    return robots


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
    html_source = getattr(args, "html_source", None)
    html_file = getattr(args, "html_file", None)
    if html_file:
        if html_source is not None:
            raise ValueError("Supply HTML by path or data, not both")
        if html_file.suffix.lower() not in {".html", ".htm"}:
            raise ValueError("HTML prototype must be a .html or .htm file")
        if html_file.stat().st_size > s2c_audit.MAX_BYTES:
            raise ValueError("HTML prototype exceeds 2 MB")
        html_source = html_file.read_text(encoding="utf-8")
    modes = int(bool(args.url)) + int(html_source is not None) + int(bool(args.source_json or args.snapshot))
    if modes != 1 or (args.source_json and not args.snapshot):
        raise ValueError("Give one URL, one HTML prototype, or both source JSON and snapshot for replay")
    if args.source_json and not args.snapshot:
        raise ValueError("--source-json requires --snapshot")
    raw_html_file = getattr(args, "raw_html_file", None)
    if raw_html_file and not (args.source_json and args.snapshot):
        raise ValueError("--raw-html-file requires --source-json and --snapshot replay inputs")
    if raw_html_file and raw_html_file.stat().st_size > s2c_audit.MAX_BYTES:
        raise ValueError("Replay initial HTML exceeds 2 MB")
    if html_source is not None and len(html_source.encode("utf-8")) > s2c_audit.MAX_BYTES:
        raise ValueError("HTML prototype exceeds 2 MB")
    important = getattr(args, "important", None) or []
    if len(important) > 5 or any(not isinstance(value, str) or not 3 <= len(value.strip()) <= 160 for value in important):
        raise ValueError("Provide at most five important phrases of 3–160 characters each")
    scoring_profile_path = getattr(args, "scoring_profile", None)
    scoring_profile_data = getattr(args, "scoring_profile_data", None)
    if scoring_profile_path and scoring_profile_data:
        raise ValueError("Supply scoring profile by path or data, not both")
    if (scoring_profile_path or scoring_profile_data) and args.rubric_config:
        raise ValueError("Choose --scoring-profile or --rubric-config, not both")
    profile = (s2c_scoring_profile.validate(scoring_profile_data) if scoring_profile_data is not None
               else s2c_scoring_profile.read(scoring_profile_path))
    robots_preflight = public_robots_preflight(args.url) if args.url and not args.snapshot else None
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "scoring-profile.json", profile)
    telemetry = Telemetry.create(args.otel, args.otlp_endpoint)
    run_id = uuid.uuid4().hex
    trace_id = None
    report_path = output / "report.html"
    capture_dir = output / "capture"
    try:
        with telemetry.span("s2c.run", {
            "s2c.run.id": run_id, "s2c.mode": "rules",
            "s2c.input.kind": "replay" if args.snapshot else ("html" if html_source is not None else "url"),
        }) as root:
            trace_id = Telemetry.trace_id(root)
            raw_html = (raw_html_file.read_text(encoding="utf-8") if raw_html_file else html_source)
            x_robots_tag = ""
            with telemetry.span("s2c.source_audit", {
                "s2c.stage.mode": "reuse" if args.source_json else ("upload" if html_source is not None else "fetch"),
            }) as span:
                if args.source_json:
                    audit = json.loads(args.source_json.read_text(encoding="utf-8"))
                elif html_source is not None:
                    audit = {"schema_version": "1.1", "audited_on": datetime.now(timezone.utc).date().isoformat(),
                             "reports": [s2c_audit.audit_html(html_source, "Uploaded HTML prototype")]}
                else:
                    status, headers, body = s2c_site_basics.get_public(args.url, s2c_audit.MAX_BYTES, timeout=10)
                    if status != 200 or "html" not in headers.get("content-type", ""):
                        raise ValueError("URL did not return a 200 HTML response; supply the final public URL")
                    match = re.search(r"charset=([^;\s]+)", headers.get("content-type", ""), re.I)
                    raw_html = body.decode(match.group(1).strip('"') if match else "utf-8", errors="replace")
                    x_robots_tag = headers.get("x-robots-tag", "")
                    audit = {"schema_version": "1.1", "audited_on": datetime.now(timezone.utc).date().isoformat(),
                             "reports": [s2c_audit.audit_html(raw_html, args.url)]}
                if audit.get("schema_version") != "1.1" or not audit.get("reports"):
                    raise ValueError("Expected S2C source audit schema_version 1.1")
                write_json(output / "audit.json", audit)
                if raw_html is not None:
                    (output / "source.html").write_bytes(raw_html.encode("utf-8"))
                span.set_attribute("s2c.source.finding_count", sum(len(r.get("findings", [])) for r in audit["reports"]))

            with telemetry.span("s2c.capture", {
                "s2c.stage.mode": "reuse" if args.snapshot else "browser",
            }) as span:
                if args.snapshot:
                    snapshot = copy_capture(args.snapshot, capture_dir)
                else:
                    capture_dir.mkdir(parents=True, exist_ok=True)
                    command = ["node", str(SCRIPTS / "s2c_browser_capture.mjs"), "--out", str(capture_dir)]
                    command += ["--python", sys.executable]
                    command += ["--html-stdin"] if html_source is not None else ["--url", args.url]
                    subprocess.run(command, input=html_source if html_source is not None else None,
                                   check=True, capture_output=True, text=True, cwd=SCRIPTS.parents[2], timeout=180)
                    snapshot = json.loads((capture_dir / "snapshot.json").read_text(encoding="utf-8"))
                span.set_attribute("s2c.capture.frame_count", len(snapshot["frames"]))
                span.set_attribute("s2c.capture.bytes", (capture_dir / "snapshot.json").stat().st_size)

            with telemetry.span("s2c.projection.site_basics") as span:
                desktop = next((frame for frame in snapshot["frames"] if frame.get("id") == "desktop"), snapshot["frames"][0])
                probes = s2c_site_basics.probe_links(desktop) if args.url and not args.snapshot else []
                site_basics = s2c_site_basics.project(snapshot, probes)
                write_json(output / "site-basics.json", site_basics)
                span.set_attribute("s2c.links.probed_count", len(probes))
                span.set_attribute("s2c.links.possible_broken_count", site_basics["link_summary"]["possible_broken"])

            with telemetry.span("s2c.projection.robot_visibility") as span:
                robots = (robots_preflight if robots_preflight is not None else
                          {"status": "not_applicable" if html_source is not None else "not_checked", "text": ""})
                robot_visibility = s2c_robot_visibility.project(raw_html, snapshot, important=important,
                                                                 x_robots_tag=x_robots_tag, robots=robots)
                write_json(output / "robot-visibility.json", robot_visibility)
                span.set_attribute("s2c.robot.finding_count", len(robot_visibility["checks"]))

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

            with telemetry.span("s2c.projection.reader_views") as span:
                reader_views = s2c_reader_views.project(snapshot, assistive, attention,
                                                        getattr(args, "question", "") or "", profile)
                write_json(output / "reader-views.json", reader_views)
                span.set_attribute("s2c.capture.frame_count", len(reader_views["frames"]))

            with telemetry.span("s2c.rules.browser") as span:
                if args.rubric_config:
                    config = json.loads(args.rubric_config.read_text(encoding="utf-8"))
                    profile["browser_weights"] = s2c_browser_rubric.weights_from(config)
                    write_json(output / "scoring-profile.json", profile)
                else:
                    config = {"schema": "s2c-browser-rubric-config/v1",
                              "version": "1.0.0" if not (scoring_profile_path or scoring_profile_data) else "profile-" + s2c_scoring_profile.fingerprint(profile),
                              "weights": profile["browser_weights"]}
                rubric = s2c_browser_rubric.evaluate(snapshot, assistive, attention, config)
                write_json(output / "browser-rubric.json", rubric)
                span.set_attribute("s2c.rubric.version", rubric["rubric_version"])
                for status in ("pass", "warning", "review", "not_checked"):
                    span.set_attribute(f"s2c.rule.{status}_count", rubric["counts"][status])

            with telemetry.span("s2c.report.render") as span:
                html = s2c_visualize.render(audit, attention=attention,
                                            attention_dir=capture_dir if attention else None,
                                            assistive=assistive, assistive_dir=capture_dir,
                                            rubric=rubric, reader_views=reader_views,
                                            reader_views_dir=capture_dir, scoring_profile=profile,
                                            site_basics=site_basics, robot_visibility=robot_visibility)
                report_path.write_text("\n".join(line.rstrip() for line in html.splitlines()) + "\n", encoding="utf-8")
                span.set_attribute("s2c.report.bytes", report_path.stat().st_size)

        manifest = {"schema": "s2c-run/v1", "run_id": run_id, "trace_id": trace_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "url": "Uploaded HTML prototype" if html_source is not None else snapshot["url"],
                    "audited_on": snapshot["audited_on"],
                    "mode": "rules", "input_kind": "html" if html_source is not None else ("replay" if args.snapshot else "url"),
                    "important_phrases": important, "rubric_version": rubric["rubric_version"],
                    "retrieval_question": reader_views["question"],
                    "scoring_profile_id": s2c_scoring_profile.fingerprint(profile),
                    "source_html_sha256": hashlib.sha256(raw_html.encode("utf-8")).hexdigest() if raw_html is not None else None,
                    "capture_network": site_basics.get("capture_network", []),
                    "telemetry": {"enabled": args.otel, "export_accepted": telemetry.finish()},
                    "artifacts": {"report": "report.html", "source": "audit.json",
                                  "capture": "capture/snapshot.json", "assistive": "assistive.json",
                                  "browser_rubric": "browser-rubric.json",
                                  "reader_views": "reader-views.json",
                                  "site_basics": "site-basics.json",
                                  "robot_visibility": "robot-visibility.json",
                                  "scoring_profile": "scoring-profile.json",
                                  "source_html": "source.html" if raw_html is not None else None,
                                  "attention": "capture/attention.json" if attention else None}}
        write_json(output / "run.json", manifest)
        return manifest
    except Exception:
        telemetry.finish()
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="Public HTML URL for source audit and browser capture")
    parser.add_argument("--html-file", type=Path, help="Self-contained local .html prototype (scripts disabled, external requests blocked)")
    parser.add_argument("--important", action="append", default=[], help="Phrase this page should make discoverable; repeat up to five times")
    parser.add_argument("--source-json", type=Path, help="Existing S2C source audit for offline replay")
    parser.add_argument("--snapshot", type=Path, help="Existing Chromium snapshot for offline replay")
    parser.add_argument("--raw-html-file", type=Path, help="Saved initial HTML for a source JSON and snapshot replay")
    parser.add_argument("--output", required=True, type=Path, help="New or empty output directory")
    parser.add_argument("--rubric-config", type=Path, help="Versioned editable browser rubric config")
    parser.add_argument("--scoring-profile", type=Path, help="Versioned browser, crawler, retrieval, and gap profile")
    parser.add_argument("--skip-attention", action="store_true", help="Skip the experimental attention layer")
    parser.add_argument("--question", default="", help="Optional retrieval question (local BM25; 200 characters max)")
    parser.add_argument("--otel", action="store_true", help="Export stage spans through OTLP/HTTP")
    parser.add_argument("--otlp-endpoint", help="Full OTLP traces URL, such as http://127.0.0.1:4318/v1/traces")
    args = parser.parse_args()
    try:
        result = run(args)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired) as error:
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
