"""Browser and projection checks for the S2C assistive view."""

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/scan-to-comprehend/scripts"
SPEC = importlib.util.spec_from_file_location("s2c_assistive", SCRIPTS / "s2c_assistive.py")
ASSISTIVE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ASSISTIVE)


class S2CAssistiveTests(unittest.TestCase):
    def test_chromium_order_hidden_heading_and_small_target(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            directory = Path(folder)
            (directory / "index.html").write_text("""<!doctype html><html lang='en'><title>Fixture</title>
<h1 aria-hidden='true'>Hidden hero</h1><h1>Visible hero</h1>
<button tabindex='2'>Second in focus</button><button tabindex='1'>First in focus</button>
<button style='width:20px;height:20px;padding:0' aria-label='Tiny action'>×</button>
""", encoding="utf-8")
            completed = subprocess.run(["node", str(SCRIPTS / "s2c_browser_capture.mjs"),
                            "--url", (directory / "index.html").as_uri(),
                            "--audit-date", "2026-10-26", "--out", str(directory / "capture")],
                           cwd=ROOT, capture_output=True, text=True, timeout=60)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            snapshot = json.loads((directory / "capture/snapshot.json").read_text(encoding="utf-8"))
            desktop = snapshot["frames"][0]
            names = [step["name"] for step in desktop["ax_path"]]
            self.assertNotIn("Hidden hero", names)
            self.assertIn("Visible hero", names)
            self.assertEqual([step["label"] for step in desktop["focus_path"][:2]],
                             ["First in focus", "Second in focus"])
            result = ASSISTIVE.project(snapshot)
            self.assertEqual(result["audited_on"], "2026-10-26")
            self.assertTrue(any(item["kind"] == "target_review" for item in result["frames"][0]["findings"]))
            self.assertEqual([frame["viewport"]["width"] for frame in result["frames"]], [1265, 375, 320])


if __name__ == "__main__":
    unittest.main()
