"""Behavior checks for the untrained S2C attention baseline."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image


SCRIPT = Path(__file__).resolve().parents[1] / "skills/scan-to-comprehend/scripts/s2c_attention.py"
SPEC = importlib.util.spec_from_file_location("s2c_attention", SCRIPT)
ATTENTION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ATTENTION)


class AttentionBaselineTests(unittest.TestCase):
    def test_contrast_and_unknown_background_are_distinct(self):
        self.assertAlmostEqual(ATTENTION.contrast_ratio("#000", "#fff"), 21, places=4)
        plain = {"kind": "heading", "x": 10, "y": 10, "width": 100, "height": 20}
        self.assertEqual(ATTENTION.element_strength(plain, 200, 100)["contrast_status"], "unknown")
        with self.assertRaises(ValueError):
            ATTENTION.contrast_ratio("rgb(0,0,0)", "#fff")

    def test_render_and_held_out_comparison(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            Image.new("RGB", (200, 160), "white").save(root / "view.png")
            capture = {"schema": "s2c-attention-capture/v1", "frames": [{
                "id": "view", "image": "view.png", "coordinate_width": 400,
                "coordinate_height": 320, "elements": [{
                    "kind": "heading", "label": "Answer", "x": 260, "y": 230,
                    "width": 100, "height": 50, "font_px": 32,
                    "foreground": "#000000", "background": "#ffffff",
                }],
            }]}
            (root / "capture.json").write_text(json.dumps(capture), encoding="utf-8")
            result = ATTENTION.render(root / "capture.json", root / "attention.json")
            self.assertTrue((root / result["frames"][0]["overlay"]).is_file())
            self.assertEqual(result["status"], "untrained heuristic; no gaze validation")
            self.assertEqual(result["frames"][0]["cues"][0]["contrast_ratio"], 21)
            fixations = {"schema": "s2c-attention-fixations/v1", "trials": [{
                "frame_id": "view", "split": "held_out", "fixations": [{"x": 154, "y": 127}],
            }]}
            (root / "fixations.json").write_text(json.dumps(fixations), encoding="utf-8")
            comparison = ATTENTION.evaluate(root / "capture.json", root / "fixations.json", root / "evaluation.json")
            self.assertGreater(comparison["equal_trial_mean_bits_vs_position"], 0)
            self.assertEqual(comparison["fixation_count"], 1)
            fixations["trials"][0]["split"] = "train"
            (root / "fixations.json").write_text(json.dumps(fixations), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "held_out"):
                ATTENTION.evaluate(root / "capture.json", root / "fixations.json", root / "evaluation.json")


if __name__ == "__main__":
    unittest.main()
