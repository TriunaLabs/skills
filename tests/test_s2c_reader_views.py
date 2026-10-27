"""Behavior checks for the deterministic multi-reader projection."""

import sys
from pathlib import Path
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "scan-to-comprehend" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import s2c_reader_views  # noqa: E402


def node(id, tag, text, x, *, landmark="main", alt=None):
    return {"id": id, "tag": tag, "text": text, "name": text, "alt": alt,
            "visible": True, "aria_hidden": False, "in_viewport": True,
            "landmark": landmark, "a11y_index": int(id[1:]), "dom_index": int(id[1:]),
            "box": {"x": x, "y": 20, "width": 80, "height": 30}}


class ReaderViewTests(unittest.TestCase):
    def setUp(self):
        self.frame = {"id": "desktop", "image": "desktop.png", "viewport": {"width": 500, "height": 400},
                      "captured_at": "2026-10-27T00:00:00Z",
                      "head": {"title": "Product", "meta_description": "A useful description of a service with a clear opening statement for visitors and search previews.", "lang": "en"},
                      "nodes": [node("n01", "a", "Pricing", 0, landmark="nav"),
                                node("n02", "h1", "Product", 100),
                                node("n03", "p", "The plan cost is twenty dollars per month.", 200),
                                node("n04", "p", "Start by creating an account.", 300),
                                node("n05", "img", "", 400)]}
        self.snapshot = {"schema": "s2c-browser-capture/v1", "url": "https://example.com/",
                         "audited_on": "2026-10-27", "frames": [self.frame]}
        self.assistive = {"schema": "s2c-assistive-v1", "frames": [
            {"id": "desktop", "reading_path": [{"id": "n02", "index": 1}, {"id": "n03", "index": 2}]}]}
        self.attention = {"frames": [{"id": "desktop", "cues": [
            {"id": "n02", "weight": 0.9}, {"id": "n03", "weight": 0.1},
            {"id": "n04", "weight": 0.2}, {"id": "n05", "weight": 0.8}]}]}

    def test_crawler_flags_missing_alt_and_damps_navigation(self):
        view = s2c_reader_views.crawler(self.frame)
        rows = {row["id"]: row for row in view["nodes"]}
        self.assertEqual(rows["n05"]["flag"], "missing_alt")
        self.assertEqual(rows["n05"]["weight"], 0)
        self.assertLess(rows["n01"]["weight"], rows["n02"]["weight"])

    def test_retrieval_removes_navigation_and_matches_question(self):
        view = s2c_reader_views.retrieval(self.frame, "How much does the plan cost?")
        self.assertNotIn("n01", {key for chunk in view["chunks"] for key in chunk["node_ids"]})
        self.assertEqual(view["chunks"][0]["relative_score"], 1)
        self.assertIn("cost", view["chunks"][0]["matched_terms"])

    def test_gap_is_versioned_and_optional_when_attention_skipped(self):
        projected = s2c_reader_views.project(self.snapshot, self.assistive, self.attention)
        self.assertEqual(projected["frames"][0]["gap"]["version"], "s2c-gap-v1")
        skipped = s2c_reader_views.project(self.snapshot, self.assistive)
        self.assertFalse(skipped["frames"][0]["gap"]["available"])
        self.assertEqual(s2c_reader_views.percentile_map({"a": 0, "b": 0}, ["a", "b"]), {"a": 0.5, "b": 0.5})


if __name__ == "__main__":
    unittest.main()
