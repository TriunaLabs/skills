"""Check that the editable browser rubric scores only assessed facts."""

import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "skills/scan-to-comprehend/scripts/s2c_browser_rubric.py"
SPEC = importlib.util.spec_from_file_location("s2c_browser_rubric", SCRIPT)
RUBRIC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUBRIC)


class BrowserRubricTests(unittest.TestCase):
    def test_shared_navigation_target_is_scored_and_unknown_contrast_is_excluded(self):
        nodes = [
            {"tag": "a", "landmark": "nav", "href": "#top", "name": "How it works"},
            {"tag": "a", "landmark": "nav", "href": "#top", "name": "Who it's for"},
            {"tag": "h1", "heading_level": 1, "visible": True, "in_viewport": True,
             "aria_hidden": False},
            {"tag": "img", "visible": True, "alt": "Example"},
        ]
        frames = [{"id": id_, "viewport": {"width": width}, "nodes": nodes,
                   "document_width": width, "client_width": width}
                  for id_, width in (("desktop", 1265), ("reflow-320", 320))]
        snapshot = {"schema": "s2c-browser-capture/v1", "audited_on": "2026-10-26",
                    "url": "https://example.com/", "frames": frames}
        assistive = {"schema": "s2c-assistive-v1", "audited_on": "2026-10-26",
                     "frames": [{"id": id_, "focus_path": [{"index": 1}], "findings": []}
                                for id_ in ("desktop", "reflow-320")]}
        attention = {"schema": "s2c-attention/v1", "frames": [
            {"text_contrast_spotcheck": {"checks": [{"status": "needs_review"}]}}]}
        result = RUBRIC.evaluate(snapshot, assistive, attention)
        self.assertEqual(result["score"]["earned"], 70)
        self.assertEqual(result["score"]["assessed"], 90)
        self.assertEqual(result["counts"], {"pass": 5, "warning": 1, "review": 1, "not_checked": 0})
        self.assertIn("How it works", result["rules"][0]["evidence"][0])
        self.assertEqual(result["rules"][-1]["status"], "review")

    def test_editable_weights_require_complete_100_point_contract(self):
        with self.assertRaisesRegex(ValueError, "Expected s2c-browser-rubric-config"):
            RUBRIC.weights_from({})
        config = {"schema": "s2c-browser-rubric-config/v1", "weights": {key: 1 for key in RUBRIC.RULES}}
        with self.assertRaisesRegex(ValueError, "sum to 100"):
            RUBRIC.weights_from(config)
        config["weights"]["nav_shared_fragment"] = 94
        self.assertEqual(sum(RUBRIC.weights_from(config).values()), 100)


if __name__ == "__main__":
    unittest.main()
