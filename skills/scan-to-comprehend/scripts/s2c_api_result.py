"""Normalize saved S2C artifacts into a versioned machine-readable result."""

from __future__ import annotations

import json
from pathlib import Path


SCHEMA = "s2c-api-result/v1"


def from_run(folder: Path) -> dict:
    folder = folder.resolve()
    def read(name: str) -> dict:
        return json.loads((folder / name).read_text(encoding="utf-8"))
    manifest = read("run.json")
    source = read("audit.json")["reports"][0]
    rubric = read("browser-rubric.json")
    basics = read("site-basics.json")
    robots = read("robot-visibility.json")
    actions = []
    for index, finding in enumerate(source.get("findings", []), 1):
        code = finding.get("code", "unknown")
        suggestion = next((item.get("action", "") for item in source.get("suggestions", [])
                           if item.get("code") == code), "Review the source finding in context.")
        actions.append({"id": f"source:{code}:{index}", "status": finding.get("level", "review"),
                        "scope": "initial_html", "title": finding.get("message", "Source finding"),
                        "evidence": [finding.get("message", "")], "suggestion": suggestion})
    for rule in rubric.get("rules", []):
        if rule.get("status") not in {"warning", "review"}:
            continue
        actions.append({"id": f"browser:{rule['id']}", "status": rule["status"],
                        "scope": "rendered_capture", "title": rule["title"],
                        "evidence": rule.get("evidence", []), "suggestion": rule.get("suggestion", "")})
    for check in basics.get("checks", []):
        if check.get("status") != "review":
            continue
        actions.append({"id": f"basics:{check['id']}", "status": "review", "scope": "captured_page",
                        "title": check["label"], "evidence": [check.get("detail", "")],
                        "suggestion": check.get("action", "")})
    for check in robots.get("checks", []):
        if check.get("status") not in {"warning", "review"}:
            continue
        actions.append({"id": f"robots:{check['id']}", "status": check["status"],
                        "scope": "initial_vs_rendered", "title": check.get("title", check["id"]),
                        "evidence": [check.get("evidence", "")], "suggestion": check.get("action", "")})
    return {"schema": SCHEMA, "run_id": manifest["run_id"], "audited_on": manifest["audited_on"],
            "input_kind": manifest["input_kind"], "url": manifest["url"],
            "rubric_version": manifest["rubric_version"],
            "scoring_profile_id": manifest["scoring_profile_id"],
            "score": rubric["score"], "counts": rubric["counts"],
            "actions": actions,
            "provenance": {"source_html_sha256": manifest.get("source_html_sha256"),
                           "capture_network": manifest.get("capture_network", []),
                           "trace_id": manifest.get("trace_id")},
            "artifacts": manifest["artifacts"],
            "limits": ["Browser points are editorial checklist scores, not measured cognitive load or gaze.",
                       "Action candidates need review against the cited capture and task.",
                       "A one-page URL audit does not establish domain ownership or sitewide coverage."]}
