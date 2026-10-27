#!/usr/bin/env python3
"""Generate a real S2C report from the owned, synthetic JavaScript demo site."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
SITE = Path(__file__).resolve().parent
SCRIPTS = ROOT / "skills" / "scan-to-comprehend" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import s2c_audit  # noqa: E402
import s2c_site_graph  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New or empty audit directory; default is a unique folder under tmp/")
    parser.add_argument("--skip-attention", action="store_true", help="Omit the experimental attention heatmap")
    args = parser.parse_args()
    temp_root = ROOT / "tmp"
    temp_root.mkdir(exist_ok=True)
    output = args.output or Path(tempfile.mkdtemp(prefix="s2c-demo-report-", dir=temp_root))
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output must be new or empty")
    raw_html = (SITE / "index.html").read_text(encoding="utf-8")
    url = (SITE / "index.html").as_uri()
    with tempfile.TemporaryDirectory(prefix="s2c-demo-input-", dir=temp_root) as temporary:
        inputs = Path(temporary)
        capture_dir = inputs / "capture"
        subprocess.run(["node", str(SCRIPTS / "s2c_browser_capture.mjs"), "--url", url,
                        "--out", str(capture_dir)], check=True, cwd=ROOT)
        snapshot = json.loads((capture_dir / "snapshot.json").read_text(encoding="utf-8"))
        source = {"schema_version": "1.1", "audited_on": snapshot["audited_on"],
                  "reports": [s2c_audit.audit_html(raw_html, url)]}
        source_path = inputs / "source-audit.json"
        source_path.write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")
        raw_path = inputs / "source.html"
        raw_path.write_text(raw_html, encoding="utf-8")
        command = [sys.executable, str(SCRIPTS / "s2c_run.py"), "--source-json", str(source_path),
                   "--snapshot", str(capture_dir / "snapshot.json"), "--raw-html-file", str(raw_path),
                   "--output", str(output), "--important", "Options for multiple children"]
        if args.skip_attention:
            command.append("--skip-attention")
        subprocess.run(command, check=True, cwd=ROOT)
        graph = s2c_site_graph.crawl(url, s2c_site_graph.fixture_fetch(SITE),
                                     snapshot=snapshot, target="siblings.html")
        (output / "site-graph.json").write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")
        (output / "site-graph.html").write_text(s2c_site_graph.render_report(graph), encoding="utf-8")
        manifest_path = output / "run.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["artifacts"]["site_graph"] = "site-graph.json"
        manifest["artifacts"]["site_graph_report"] = "site-graph.html"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Report: {output.resolve() / 'report.html'}")
    print(f"Site graph: {output.resolve() / 'site-graph.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
