#!/usr/bin/env python3
"""Local, loopback-only website for trying the real S2C URL audit pipeline."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
from pathlib import Path
import re
import socket
import sys
from threading import Lock
from urllib.parse import urlsplit
import uuid

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "scan-to-comprehend" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import s2c_run  # noqa: E402
import s2c_browser_rubric  # noqa: E402
import s2c_reader_views  # noqa: E402
import s2c_robot_visibility  # noqa: E402
import s2c_scoring_profile  # noqa: E402
import s2c_site_basics  # noqa: E402
import s2c_visualize  # noqa: E402
import s2c_api_result  # noqa: E402

PUBLIC = Path(__file__).resolve().parent
RUNS = ROOT / ".playground-runs"
MAX_BODY = 8192
MAX_UPLOAD_BODY = 2_400_000
MAX_JOBS = 2
JOBS: dict[str, dict] = {}
LOCK = Lock()
POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="s2c-audit")


def valid_public_url(raw: object) -> str:
    if not isinstance(raw, str) or len(raw) > 2048:
        raise ValueError("Enter a public website URL under 2,048 characters.")
    url = raw.strip()
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Enter a public HTTP or HTTPS URL without credentials.")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("The URL has an invalid port.") from exc
    if port not in (None, 80, 443):
        raise ValueError("This test accepts websites on ports 80 and 443 only.")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise ValueError("The website host could not be resolved.") from exc
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("The URL must resolve only to public addresses.")
    return url


def summary(run_id: str) -> dict:
    with LOCK:
        job = dict(JOBS[run_id])
    folder = RUNS / run_id
    if job["status"] == "running":
        if (folder / "report.html").exists():
            job["stage"] = "Rendering report"
        elif (folder / "browser-rubric.json").exists():
            job["stage"] = "Scoring browser rules"
        elif (folder / "capture" / "snapshot.json").exists():
            job["stage"] = "Building assistive and attention views"
        elif (folder / "audit.json").exists():
            job["stage"] = "Capturing desktop, mobile, and 320 px views"
        else:
            job["stage"] = "Checking page source"
    job["run_id"] = run_id
    if job["status"] == "complete":
        job["revisions"] = revisions_for(folder)
    return job


def revisions_for(folder: Path) -> list[dict]:
    root = folder / "revisions"
    if not root.is_dir():
        return []
    revisions = []
    for candidate in root.iterdir():
        if not candidate.is_dir() or not re.fullmatch(r"[0-9a-f]{32}", candidate.name):
            continue
        try:
            item = json.loads((candidate / "revision.json").read_text(encoding="utf-8"))
            revisions.append({key: item[key] for key in ("revision_id", "rescored_at", "question", "score",
                                                           "report_url", "views_url", "scoring_profile_id")})
        except (OSError, ValueError, KeyError):
            continue
    return sorted(revisions, key=lambda item: item["rescored_at"], reverse=True)[:20]


def completed_fields(folder: Path, manifest: dict) -> dict:
    rubric = json.loads((folder / "browser-rubric.json").read_text(encoding="utf-8"))
    audit = json.loads((folder / "audit.json").read_text(encoding="utf-8"))
    basics_path = folder / "site-basics.json"
    basics = json.loads(basics_path.read_text(encoding="utf-8")) if basics_path.is_file() else {}
    robot_path = folder / "robot-visibility.json"
    robot = json.loads(robot_path.read_text(encoding="utf-8")) if robot_path.is_file() else {}
    return {
        "status": "complete", "audited_on": manifest["audited_on"],
        "rubric_version": manifest["rubric_version"],
        "score": rubric["score"], "counts": rubric["counts"],
        "source_findings": len(audit["reports"][0].get("findings", [])),
        "site_basics_reviews": sum(item.get("status") == "review" for item in basics.get("checks", []))
                               + basics.get("link_summary", {}).get("possible_broken", 0)
                               + basics.get("link_summary", {}).get("broken_fragments", 0),
        "robot_visibility_reviews": sum(item.get("status") in {"review", "warning"} for item in robot.get("checks", [])),
        "input_kind": manifest.get("input_kind", "url"),
        "report_url": f"/api/runs/{folder.name}/report",
        "reader_views": (folder / "reader-views.json").is_file(),
        "site_basics": (folder / "site-basics.json").is_file(),
        "views_url": f"/api/runs/{folder.name}/views",
        "profile": s2c_scoring_profile.read(folder / "scoring-profile.json") if (folder / "scoring-profile.json").is_file() else s2c_scoring_profile.default_profile(),
        "question": manifest.get("retrieval_question", ""),
        "revisions": revisions_for(folder),
    }


def load_previous_runs() -> None:
    """Keep completed local reports reachable after restarting the test server."""
    for folder in RUNS.iterdir():
        if not folder.is_dir() or not re.fullmatch(r"[0-9a-f]{32}", folder.name):
            continue
        try:
            manifest = json.loads((folder / "run.json").read_text(encoding="utf-8"))
            if not (folder / "report.html").is_file():
                continue
            JOBS[folder.name] = {"url": manifest["url"], "submitted_at": manifest["created_at"],
                                 **completed_fields(folder, manifest)}
        except (OSError, ValueError, KeyError, IndexError):
            continue


def execute(run_id: str, url: str, question: str, profile: dict,
            html_source: str | None = None, important: list[str] | None = None) -> None:
    folder = RUNS / run_id
    with LOCK:
        JOBS[run_id]["status"] = "running"
    try:
        manifest = s2c_run.run(argparse.Namespace(
            url=url if html_source is None else None, html_source=html_source,
            important=important or [], source_json=None, snapshot=None, output=folder,
            rubric_config=None, skip_attention=False, otel=False, otlp_endpoint=None,
            question=question, scoring_profile_data=profile,
        ))
        with LOCK:
            JOBS[run_id].update(completed_fields(folder, manifest))
    except Exception as exc:
        with LOCK:
            JOBS[run_id].update({"status": "failed", "error": str(exc)[:500]})


def rescore(run_id: str, profile: dict, question: str) -> dict:
    """Create an immutable revision from saved audit evidence; no website request."""
    folder = RUNS / run_id
    revisions = folder / "revisions"
    if revisions.exists() and sum(path.is_dir() for path in revisions.iterdir()) >= 20:
        raise ValueError("This local run already has 20 revisions.")
    read = lambda path: json.loads(path.read_text(encoding="utf-8"))
    snapshot = read(folder / "capture" / "snapshot.json")
    audit = read(folder / "audit.json")
    assistive = read(folder / "assistive.json")
    attention_path = folder / "capture" / "attention.json"
    attention = read(attention_path) if attention_path.is_file() else None
    basics_path = folder / "site-basics.json"
    site_basics = read(basics_path) if basics_path.is_file() else s2c_site_basics.project(snapshot)
    robot_path = folder / "robot-visibility.json"
    robot_visibility = read(robot_path) if robot_path.is_file() else None
    rubric = s2c_browser_rubric.evaluate(snapshot, assistive, attention, {
        "schema": "s2c-browser-rubric-config/v1",
        "version": "profile-" + s2c_scoring_profile.fingerprint(profile),
        "weights": profile["browser_weights"],
    })
    views = s2c_reader_views.project(snapshot, assistive, attention, question, profile)
    report = s2c_visualize.render(audit, attention=attention,
                                  attention_dir=folder / "capture" if attention else None,
                                  assistive=assistive, assistive_dir=folder / "capture",
                                  rubric=rubric, reader_views=views,
                                  reader_views_dir=folder / "capture", scoring_profile=profile,
                                  site_basics=site_basics, robot_visibility=robot_visibility)
    revision_id = uuid.uuid4().hex
    target = revisions / revision_id
    target.mkdir(parents=True)
    s2c_run.write_json(target / "scoring-profile.json", profile)
    s2c_run.write_json(target / "browser-rubric.json", rubric)
    s2c_run.write_json(target / "reader-views.json", views)
    (target / "report.html").write_text(report, encoding="utf-8")
    result = {"status": "complete", "revision_id": revision_id, "baseline_run_id": run_id,
              "url": audit["reports"][0].get("source", snapshot["url"]),
              "audited_on": snapshot["audited_on"],
              "rescored_at": datetime.now(timezone.utc).isoformat(),
              "question": question, "profile": profile,
              "scoring_profile_id": s2c_scoring_profile.fingerprint(profile),
              "rubric_version": rubric["rubric_version"], "score": rubric["score"],
              "counts": rubric["counts"],
              "source_findings": len(audit["reports"][0].get("findings", [])),
              "site_basics_reviews": sum(item.get("status") == "review" for item in site_basics.get("checks", []))
                                     + site_basics.get("link_summary", {}).get("possible_broken", 0)
                                     + site_basics.get("link_summary", {}).get("broken_fragments", 0),
              "robot_visibility_reviews": sum(item.get("status") in {"review", "warning"} for item in (robot_visibility or {}).get("checks", [])),
              "input_kind": snapshot.get("source_kind", "url"),
              "report_url": f"/api/runs/{run_id}/revisions/{revision_id}/report",
              "views_url": f"/api/runs/{run_id}/revisions/{revision_id}/views",
              "reader_views": True}
    s2c_run.write_json(target / "revision.json", result)
    return result


class Handler(BaseHTTPRequestHandler):
    server_version = "S2CPlayground/0.1"

    def local_host(self) -> bool:
        return bool(re.fullmatch(r"(localhost|127\.0\.0\.1)(:\d+)?", self.headers.get("Host", ""), re.I))

    def send_bytes(self, data: bytes, content_type: str, status: int = 200, *, report: bool = False) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        if report:
            self.send_header("Content-Security-Policy", "sandbox; default-src 'none'; img-src data:; style-src 'unsafe-inline'")
        else:
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; frame-src 'self'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, payload: dict, status: int = 200) -> None:
        self.send_bytes(json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8", status)

    def do_GET(self) -> None:
        if not self.local_host():
            self.send_json({"error": "Use this playground from its local address."}, 403)
            return
        path = self.path.split("?", 1)[0]
        static = {"/": ("index.html", "text/html; charset=utf-8"),
                  "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                  "/styles.css": ("styles.css", "text/css; charset=utf-8")}
        if path in static:
            name, mime = static[path]
            self.send_bytes((PUBLIC / name).read_bytes(), mime)
            return
        if path == "/api/health":
            self.send_json({"status": "ok", "mode": "local-rules", "capacity": MAX_JOBS})
            return
        if path == "/api/scoring-profile":
            self.send_json({"profile": s2c_scoring_profile.default_profile(),
                            "browser_labels": s2c_browser_rubric.RULES,
                            "crawler_labels": s2c_scoring_profile.CRAWLER_LABELS,
                            "fixed": ["Source structural-friction formula", "Experimental attention baseline"],
                            "bm25_basis": "Lowercase Unicode word tokens; common stop words removed; no stemming, embeddings, or model call. IDF and average length use only this page's retained heading-and-paragraph chunks."})
            return
        revision = re.fullmatch(r"/api/runs/([0-9a-f]{32})/revisions/([0-9a-f]{32})(/(?:report|views|profile))?", path)
        if revision:
            run_id, revision_id, artifact = revision.groups()
            target = RUNS / run_id / "revisions" / revision_id
            if not (target / "revision.json").is_file():
                self.send_json({"error": "Revision not found."}, 404)
                return
            if artifact == "/report":
                self.send_bytes((target / "report.html").read_bytes(), "text/html; charset=utf-8", report=True)
            elif artifact in ("/views", "/profile"):
                filename = "reader-views.json" if artifact == "/views" else "scoring-profile.json"
                self.send_bytes((target / filename).read_bytes(), "application/json; charset=utf-8")
            else:
                self.send_bytes((target / "revision.json").read_bytes(), "application/json; charset=utf-8")
            return
        match = re.fullmatch(r"/api/runs/([0-9a-f]{32})(/(?:report|views|result))?", path)
        if not match:
            self.send_json({"error": "Not found."}, 404)
            return
        run_id, artifact = match.groups()
        with LOCK:
            found = run_id in JOBS
        if not found:
            self.send_json({"error": "Run not found in this server session."}, 404)
            return
        if artifact == "/report":
            report = RUNS / run_id / "report.html"
            if summary(run_id)["status"] != "complete" or not report.is_file():
                self.send_json({"error": "Report is not ready."}, 409)
                return
            self.send_bytes(report.read_bytes(), "text/html; charset=utf-8", report=True)
            return
        if artifact == "/views":
            views = RUNS / run_id / "reader-views.json"
            if summary(run_id)["status"] != "complete" or not views.is_file():
                self.send_json({"error": "Projection JSON is not ready."}, 409)
                return
            self.send_bytes(views.read_bytes(), "application/json; charset=utf-8")
            return
        if artifact == "/result":
            if summary(run_id)["status"] != "complete":
                self.send_json({"error": "Result is not ready."}, 409)
                return
            self.send_json(s2c_api_result.from_run(RUNS / run_id))
            return
        self.send_json(summary(run_id))

    def do_POST(self) -> None:
        revision_match = re.fullmatch(r"/api/runs/([0-9a-f]{32})/revisions", self.path)
        if self.path != "/api/runs" and not revision_match:
            self.send_json({"error": "Not found."}, 404)
            return
        origin = self.headers.get("Origin")
        host = self.headers.get("Host", "")
        if not self.local_host() or (origin and origin != f"http://{host}"):
            self.send_json({"error": "Use this playground from its local address."}, 403)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            maximum = MAX_UPLOAD_BODY if self.path == "/api/runs" else MAX_BODY
            if size < 2 or size > maximum:
                raise ValueError("Request body is too large or empty.")
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValueError("Expected a JSON object.")
            html_source = None
            important = []
            if revision_match:
                url = ""
            elif payload.get("kind", "url") == "html":
                html_source = payload.get("html")
                if (not isinstance(html_source, str) or not html_source.strip()
                        or len(html_source.encode("utf-8")) > 2_000_000):
                    raise ValueError("Choose one non-empty HTML file under 2 MB.")
                url = "Uploaded HTML prototype"
            elif payload.get("kind", "url") == "url":
                url = valid_public_url(payload.get("url"))
            else:
                raise ValueError("Choose a public URL or one HTML prototype.")
            if not revision_match:
                important = payload.get("important", [])
                if (not isinstance(important, list) or len(important) > 5 or
                        any(not isinstance(value, str) or not 3 <= len(value.strip()) <= 160 for value in important)):
                    raise ValueError("Provide at most five important phrases of 3–160 characters each.")
            question = payload.get("question", "")
            if not isinstance(question, str) or len(question) > 200:
                raise ValueError("Reader question must be at most 200 characters.")
            question = question.strip()
            profile = s2c_scoring_profile.validate(payload.get("profile", s2c_scoring_profile.default_profile()))
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_json({"error": str(exc)}, 400)
            return
        if revision_match:
            run_id = revision_match.group(1)
            with LOCK:
                complete = run_id in JOBS and JOBS[run_id]["status"] == "complete"
            if not complete:
                self.send_json({"error": "Original run is not complete."}, 409)
                return
            try:
                result = rescore(run_id, profile, question)
            except ValueError as exc:
                self.send_json({"error": str(exc)}, 400)
                return
            except (OSError, KeyError) as exc:
                self.send_json({"error": f"Could not rescore the saved capture: {exc}"}, 500)
                return
            self.send_json(result, 201)
            return
        with LOCK:
            active = sum(job["status"] in ("queued", "running") for job in JOBS.values())
            if active >= MAX_JOBS:
                self.send_json({"error": "The test runner is busy. Try again after a run finishes."}, 429)
                return
            run_id = uuid.uuid4().hex
            JOBS[run_id] = {"status": "queued", "url": url,
                            "submitted_at": datetime.now(timezone.utc).isoformat()}
        POOL.submit(execute, run_id, url, question, profile, html_source, important)
        self.send_json({"run_id": run_id, "status": "queued", "status_url": f"/api/runs/{run_id}"}, 202)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    RUNS.mkdir(exist_ok=True)
    load_previous_runs()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"S2C playground: http://127.0.0.1:{server.server_port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
