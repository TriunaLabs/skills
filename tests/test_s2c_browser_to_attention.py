"""The browser-to-attention bridge preserves boxes and unknown image backgrounds."""

import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "skills/scan-to-comprehend/scripts/s2c_browser_to_attention.py"
SPEC = importlib.util.spec_from_file_location("s2c_browser_to_attention", SCRIPT)
BRIDGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BRIDGE)


class BrowserToAttentionTests(unittest.TestCase):
    def test_image_backed_text_needs_contrast_review_and_boxes_are_clipped(self):
        base = {"visible": True, "in_viewport": True, "aria_hidden": False,
                "heading_level": None, "role": None, "name": "", "text": "",
                "style": {"font_size": 18, "font_weight": "700", "color": "rgb(255, 255, 255)",
                          "background": "rgb(247, 245, 239)"}}
        snapshot = {"schema": "s2c-browser-capture/v1", "frames": [{
            "id": "desktop", "image": "desktop.png", "captured_at": "2026-10-26T10:00:00Z",
            "viewport": {"width": 100, "height": 100}, "nodes": [
                {**base, "id": "image", "tag": "img", "box": {"x": 0, "y": 20, "width": 100, "height": 80}},
                {**base, "id": "title", "tag": "h1", "heading_level": 1, "text": "Over photo",
                 "box": {"x": 5, "y": 30, "width": 60, "height": 20}},
                {**base, "id": "nav", "tag": "a", "text": "Visit", "box": {"x": 90, "y": 0, "width": 20, "height": 15}},
                {**base, "id": "offscreen", "tag": "p", "text": "Later", "in_viewport": False,
                 "box": {"x": 0, "y": 110, "width": 30, "height": 20}},
            ]}]}
        frame = BRIDGE.project(snapshot)["frames"][0]
        elements = {element["id"]: element for element in frame["elements"]}
        self.assertNotIn("foreground", elements["title"])
        self.assertEqual(elements["nav"]["foreground"], "#ffffff")
        self.assertEqual(elements["nav"]["width"], 10)
        self.assertNotIn("offscreen", elements)
        self.assertEqual(len(elements), 3)


if __name__ == "__main__":
    unittest.main()
