"""Behavior checks for the S2C visual audit report."""

import base64
import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "skills/scan-to-comprehend/scripts/s2c_visualize.py"
SPEC = importlib.util.spec_from_file_location("s2c_visualize", SCRIPT)
VISUALIZE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VISUALIZE)

PIXEL = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/lV8AAAAASUVORK5CYII="
)


def payload():
    return {
        "schema_version": "1.1",
        "reports": [{
            "source": "<script>alert(1)</script>",
            "headings": [{"level": 1, "text": "A page title"}],
            "findings": [{"code": "generic_link", "message": "Generic link", "level": "review"}],
            "suggestions": [{"code": "generic_link", "action": "Name the destination", "priority": "review"}],
            "strengths": [],
            "next_checks": ["Ask a reader to find the answer."],
            "estimated_cognitive_load": {"score": 8, "method": "s2c-source-heuristic-v1", "confidence": "low"},
        }],
    }


class S2CVisualizeTests(unittest.TestCase):
    def test_source_report_escapes_page_text_and_shows_action(self):
        result = VISUALIZE.render(payload())
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", result)
        self.assertNotIn("<script>alert(1)</script>", result)
        self.assertIn("Name the destination", result)
        self.assertIn("This is not measured cognitive load", result)

    def test_walkthrough_embeds_capture_and_keeps_callouts_separate(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "hero.png").write_bytes(PIXEL)
            walkthrough = {
                "url": "https://example.com/",
                "reader_task": "Find the evidence",
                "frames": [{"image": "hero.png", "callouts": [{
                    "kind": "review", "title": "Unclear number", "x": 0.5, "y": 0.4,
                    "observed": "No unit is visible.", "likely_effect": "Meaning may vary.",
                }]}],
            }
            result = VISUALIZE.render(payload(), walkthrough, directory)
            self.assertIn("data:image/png;base64,", result)
            self.assertIn("No unit is visible.", result)
            self.assertIn("Callouts are review observations, not measured gaze", result)
            walkthrough["frames"][0]["image"] = "../outside.png"
            with self.assertRaises(ValueError):
                VISUALIZE.render(payload(), walkthrough, directory)


if __name__ == "__main__":
    unittest.main()
