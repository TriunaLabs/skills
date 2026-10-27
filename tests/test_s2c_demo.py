"""The owned demo must produce replayable, evidence-linked raw/render findings."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class S2CDemoTests(unittest.TestCase):
    def test_demo_report_identifies_its_deliberate_render_dependencies(self):
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="s2c-demo-test-", dir=ROOT / "tmp") as temporary:
            output = Path(temporary) / "report"
            subprocess.run([sys.executable, str(ROOT / "examples/s2c-demo/run_demo.py"),
                            "--skip-attention", "--output", str(output)],
                           cwd=ROOT, check=True, capture_output=True, text=True, timeout=90)
            manifest = json.loads((output / "run.json").read_text(encoding="utf-8"))
            visibility = json.loads((output / "robot-visibility.json").read_text(encoding="utf-8"))
            comparison = visibility["comparison"]
            self.assertEqual(manifest["source_html_sha256"],
                             hashlib.sha256((output / "source.html").read_bytes()).hexdigest())
            self.assertEqual(comparison["headings"]["rendered_only_count"], 1)
            self.assertEqual(comparison["links"]["rendered_only_count"], 1)
            self.assertEqual({item["field"] for item in comparison["head_changes"]},
                             {"meta_description", "canonical"})
            report = (output / "report.html").read_text(encoding="utf-8")
            self.assertIn("Initial HTML ⇄ rendered page", report)
            self.assertIn("Options for multiple children", report)
            self.assertIn("FINAL PAGE / ACTION PLAN", report)
            graph = json.loads((output / "site-graph.json").read_text(encoding="utf-8"))
            self.assertEqual(graph["coverage"]["fetched_pages"], 5)
            self.assertEqual(graph["coverage"]["skipped_pages"], 1)
            self.assertEqual(len(graph["task_path"]["initial_html"]), 3)
            self.assertEqual(len(graph["task_path"]["rendered_start"]), 2)
            self.assertEqual(manifest["artifacts"]["site_graph_report"], "site-graph.html")


if __name__ == "__main__":
    unittest.main()
