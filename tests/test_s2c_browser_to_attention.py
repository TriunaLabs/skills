"""The browser-to-attention bridge preserves boxes and unknown image backgrounds."""

import importlib.util
from pathlib import Path
import tempfile
import unittest

from PIL import Image


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

    def test_icon_only_control_is_not_a_text_contrast_sample(self):
        node = {"id": "chat", "tag": "button", "role": None, "heading_level": None,
                "name": "Open chat", "text": "", "in_viewport": True, "aria_hidden": False,
                "box": {"x": 5, "y": 5, "width": 30, "height": 30},
                "style": {"color": "rgb(0, 0, 0)", "background": "rgb(0, 0, 0)"}}
        snapshot = {"schema": "s2c-browser-capture/v1", "frames": [{"id": "desktop", "image": "screen.png",
                    "viewport": {"width": 100, "height": 100}, "captured_at": "2026-10-26T10:00:00Z",
                    "nodes": [node]}]}
        element = BRIDGE.project(snapshot)["frames"][0]["elements"][0]
        self.assertFalse(element["painted_text"])
        self.assertNotIn("foreground", element)

    def test_screenshot_rejects_css_color_from_hidden_underlay(self):
        with tempfile.TemporaryDirectory(dir=SCRIPT.parents[3]) as folder:
            root = Path(folder)
            Image.new("RGB", (100, 100), "#006b52").save(root / "screen.png")
            node = {"id": "hero", "tag": "h1", "heading_level": 1, "name": "A lesson",
                    "in_viewport": True, "aria_hidden": False,
                    "box": {"x": 5, "y": 10, "width": 80, "height": 30},
                    "style": {"color": "rgb(255, 255, 255)", "background": "rgb(247, 245, 239)"}}
            snapshot = {"schema": "s2c-browser-capture/v1", "frames": [{"id": "desktop", "image": "screen.png",
                        "viewport": {"width": 100, "height": 100}, "captured_at": "2026-10-26T10:00:00Z",
                        "nodes": [node]}]}
            element = BRIDGE.project(snapshot, root)["frames"][0]["elements"][0]
            self.assertNotIn("background", element)
            self.assertNotIn("foreground", element)


if __name__ == "__main__":
    unittest.main()
