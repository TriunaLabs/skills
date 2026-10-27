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

    def test_wcag_screening_uses_unrounded_ratio_and_large_text_threshold(self):
        base = {"kind": "text", "id": "sample", "label": "Sample", "font_px": 16,
                "foreground": "#777777", "background": "#ffffff"}
        small = ATTENTION.text_contrast_spotcheck(base)
        self.assertEqual(small["threshold"], 4.5)
        self.assertEqual(small["status"], "below_threshold")
        large = ATTENTION.text_contrast_spotcheck({**base, "font_px": 24})
        self.assertEqual(large["threshold"], 3.0)
        self.assertEqual(large["status"], "at_or_above_threshold")
        bold = ATTENTION.text_contrast_spotcheck({**base, "font_px": 19, "font_weight": 700})
        self.assertEqual(bold["threshold"], 3.0)
        self.assertIsNone(ATTENTION.text_contrast_spotcheck({**base, "kind": "logo"}))
        self.assertEqual(ATTENTION.text_contrast_spotcheck({"kind": "link"})["status"], "needs_review")

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
                }, {"kind": "text", "label": "Muted lead", "x": 20, "y": 20,
                    "width": 100, "height": 40, "font_px": 16,
                    "foreground": "#aaaaaa", "background": "#ffffff"}],
            }]}
            (root / "capture.json").write_text(json.dumps(capture), encoding="utf-8")
            result = ATTENTION.render(root / "capture.json", root / "attention.json")
            self.assertTrue((root / result["frames"][0]["overlay"]).is_file())
            self.assertEqual(result["status"], "untrained heuristic; held-out UEyes test trailed a position-only baseline")
            self.assertEqual(result["frames"][0]["cues"][0]["contrast_ratio"], 21)
            self.assertEqual(result["frames"][0]["text_contrast_spotcheck"]["checks"][0]["status"],
                             "at_or_above_threshold")
            fixations = {"schema": "s2c-attention-fixations/v1", "trials": [{
                "frame_id": "view", "split": "held_out", "fixations": [{"x": 154, "y": 127}],
            }]}
            (root / "fixations.json").write_text(json.dumps(fixations), encoding="utf-8")
            comparison = ATTENTION.evaluate(root / "capture.json", root / "fixations.json", root / "evaluation.json")
            self.assertGreater(comparison["equal_trial_mean_bits_vs_position"], 0)
            self.assertIn("equal_trial_mean_bits_vs_no_contrast", comparison)
            self.assertNotEqual(comparison["equal_trial_mean_bits_vs_no_contrast"], 0)
            self.assertEqual(comparison["fixation_count"], 1)
            fixations["trials"][0]["split"] = "train"
            (root / "fixations.json").write_text(json.dumps(fixations), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "held_out"):
                ATTENTION.evaluate(root / "capture.json", root / "fixations.json", root / "evaluation.json")


if __name__ == "__main__":
    unittest.main()
