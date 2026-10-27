#!/usr/bin/env python3
"""Local S2C MCP adapter. Runs the same deterministic engine as the playground."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import tempfile
import uuid

from mcp.server.fastmcp import FastMCP


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import s2c_api_result  # noqa: E402
import s2c_run  # noqa: E402


server = FastMCP("scan-to-comprehend", instructions=(
    "Local deterministic page audits. A URL run fetches a public page. "
    "An HTML run renders offline with scripts and external requests blocked. "
    "Scores are editorial checks, not measured gaze or cognitive load."))
MAX_RUNS = 10
ROOT = Path(os.environ.get("S2C_MCP_RUN_ROOT", Path(tempfile.gettempdir()) / "s2c-mcp-runs"))


def execute(*, url: str | None = None, html: str | None = None, question: str = "") -> dict:
    if (url is None) == (html is None):
        raise ValueError("Supply a URL or HTML, not both")
    if not isinstance(question, str) or len(question) > 200:
        raise ValueError("Question must be at most 200 characters")
    if html is not None and (not isinstance(html, str) or not html.strip() or
                             len(html.encode("utf-8")) > 2_000_000):
        raise ValueError("HTML must be non-empty and at most 2 MB")
    ROOT.mkdir(parents=True, exist_ok=True)
    if sum(path.is_dir() for path in ROOT.iterdir()) >= MAX_RUNS:
        raise RuntimeError("Local MCP run cap reached; remove old runs before starting another")
    output = ROOT / uuid.uuid4().hex
    s2c_run.run(argparse.Namespace(
        url=url, html_source=html, html_file=None, important=[], source_json=None, snapshot=None,
        raw_html_file=None, output=output, rubric_config=None, scoring_profile=None,
        scoring_profile_data=None, skip_attention=False, otel=False, otlp_endpoint=None,
        question=question.strip(),
    ))
    result = s2c_api_result.from_run(output)
    result["artifacts"]["local_report_path"] = str(output / "report.html")
    result["artifacts"]["local_result_path"] = str(output / "result.json")
    s2c_run.write_json(output / "result.json", result)
    return result


@server.tool()
def audit_public_url(url: str, question: str = "") -> dict:
    """Audit one public HTTP(S) page; robots refusals and private destinations are rejected."""
    return execute(url=url, question=question)


@server.tool()
def audit_html_prototype(html: str, question: str = "") -> dict:
    """Audit one self-contained HTML prototype offline; no page script or external request runs."""
    return execute(html=html, question=question)


if __name__ == "__main__":
    server.run(transport="stdio")
