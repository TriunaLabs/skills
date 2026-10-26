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
    def test_opt_in_section_signals_are_a_separate_observed_layer(self):
        samples = [{
            "schema": "s2c-section-signals/v1", "capturedOn": "2026-10-26",
            "pageLabel": "product-v1", "viewport": {"width": 390, "height": 844},
            "mouseSeen": True,
            "sections": [{"id": "evidence<script>", "visibleMs": 1200,
                          "hoverMs": 300, "mouseClicks": 1, "touchTaps": 0}],
        }, {
            "schema": "s2c-section-signals/v1", "capturedOn": "2026-10-27",
            "pageLabel": "product-v1", "viewport": {"width": 390, "height": 844},
            "mouseSeen": False,
            "sections": [{"id": "evidence<script>", "visibleMs": 0,
                          "hoverMs": 0, "mouseClicks": 0, "touchTaps": 1}],
        }]
        result = VISUALIZE.render(payload(), signal_samples=samples)
        self.assertIn("OPT-IN PAGE OBSERVATIONS", result)
        self.assertIn("evidence&lt;script&gt;", result)
        self.assertNotIn("evidence<script>", result)
        self.assertIn("1/2", result)
        self.assertIn("1.2 s", result)
        self.assertIn("Hover and clicks are separate pointer signals", result)
        samples[1]["pageLabel"] = "other-page"
        with self.assertRaisesRegex(ValueError, "share one pageLabel"):
            VISUALIZE.render(payload(), signal_samples=samples)

    def test_source_report_escapes_page_text_and_shows_action(self):
        result = VISUALIZE.render(payload())
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", result)
        self.assertNotIn("<script>alert(1)</script>", result)
        self.assertIn("Name the destination", result)
        self.assertIn("This is not measured cognitive load", result)
        self.assertIn("Audit date:</b> Not recorded", result)

    def test_walkthrough_embeds_capture_and_keeps_callouts_separate(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "hero.png").write_bytes(PIXEL)
            walkthrough = {
                "url": "https://example.com/",
                "audited_on": "2026-10-26",
                "reader_task": "Find the evidence",
                "frames": [{"image": "hero.png", "callouts": [{
                    "kind": "review", "title": "Unclear number", "x": 0.5, "y": 0.4,
                    "observed": "No unit is visible.", "likely_effect": "Meaning may vary.",
                }]}],
            }
            result = VISUALIZE.render(payload(), walkthrough, directory)
            self.assertIn("data:image/png;base64,", result)
            self.assertIn("<time datetime='2026-10-26'>October 26, 2026</time>", result)
            self.assertIn("No unit is visible.", result)
            self.assertIn("Callouts are review observations, not measured gaze", result)
            payload_with_date = payload()
            payload_with_date["audited_on"] = "2026-10-25"
            with self.assertRaisesRegex(ValueError, "dates do not match"):
                VISUALIZE.render(payload_with_date, walkthrough, directory)
            walkthrough["audited_on"] = "2026-02-30"
            with self.assertRaisesRegex(ValueError, "valid YYYY-MM-DD"):
                VISUALIZE.render(payload(), walkthrough, directory)
            walkthrough["audited_on"] = "2026-10-26"
            walkthrough["frames"][0]["image"] = "../outside.png"
            with self.assertRaises(ValueError):
                VISUALIZE.render(payload(), walkthrough, directory)

    def test_attention_overlay_is_optional_labeled_and_self_contained(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "screen.png").write_bytes(PIXEL)
            (directory / "heat.png").write_bytes(PIXEL)
            attention = {"schema": "s2c-attention/v1", "model_version": "s2c-heuristic-attention-v1",
                         "frames": [{"label": "First viewport", "image": "screen.png", "overlay": "heat.png",
                                     "provenance": "Manual <boxes>", "cues": [{"label": "<headline>",
                                                                                   "kind": "heading", "weight": 1.2}]}]}
            result = VISUALIZE.render(payload(), attention=attention, attention_dir=directory)
            self.assertIn("EXPERIMENTAL / ESTIMATED VISUAL ATTENTION", result)
            self.assertIn("Show estimated heatmap", result)
            self.assertIn("Manual &lt;boxes&gt;", result)
            self.assertNotIn("<headline>", result)
            self.assertGreaterEqual(result.count("data:image/png;base64,"), 2)
            attention["frames"][0]["text_contrast_spotcheck"] = {
                "color_basis": "Reviewer <estimate>", "checks": [{
                    "label": "<small text>", "status": "below_threshold",
                    "ratio": 4.49, "threshold": 4.5}]}
            result = VISUALIZE.render(payload(), attention=attention, attention_dir=directory)
            self.assertIn("WCAG text contrast spot check", result)
            self.assertIn("Below reference threshold", result)
            self.assertIn("Reviewer &lt;estimate&gt;", result)
            self.assertNotIn("<small text>", result)
            attention["frames"][0]["overlay"] = "../heat.png"
            with self.assertRaisesRegex(ValueError, "inside result directory"):
                VISUALIZE.render(payload(), attention=attention, attention_dir=directory)


if __name__ == "__main__":
    unittest.main()
