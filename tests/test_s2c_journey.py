"""Task-specific graph checks cite captured evidence and retain unassessed states."""

from pathlib import Path
import sys
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "skills/scan-to-comprehend/scripts"
sys.path.insert(0, str(SCRIPTS))
import s2c_journey  # noqa: E402


class JourneyTests(unittest.TestCase):
    def setUp(self):
        self.start = "https://example.com/"
        self.target = "https://example.com/next"
        self.graph = {"schema": "s2c-site-graph/v1", "start_url": self.start,
                      "coverage": {"fetched_pages": 2, "skipped_pages": 0, "frontier_remaining": 0},
                      "pages": [{"url": self.start, "title": "Start", "headings": []},
                                {"url": self.target, "title": "Sibling schedules",
                                 "headings": [{"text": "Two learning paths"}]}],
                      "edges": [{"from": self.start, "to": self.target}],
                      "rendered_overlay": {"edges": [{"from": self.start, "to": self.target}]}}
        self.scenario = {"schema": s2c_journey.SCHEMA, "id": "family", "role": "Parent",
                         "goal": "Compare schedules", "target": "/next", "device": "desktop",
                         "required_phrases": ["Two learning paths", "Enrollment price"],
                         "success_action": "Compare schedules"}
        self.snapshot = {"schema": "s2c-browser-capture/v1", "url": self.start,
                         "frames": [{"id": "desktop", "nodes": [
                             {"id": "n1", "tag": "a", "visible": True,
                              "text": "Compare schedules", "href": "/next"}]}]}

    def test_route_evidence_and_action_are_separate(self):
        result = s2c_journey.project(self.graph, self.scenario, self.snapshot)
        self.assertEqual(result["route"]["initial_html"], [self.start, self.target])
        self.assertEqual([item["status"] for item in result["evidence"]], ["found", "review"])
        self.assertEqual(result["success_action"]["node_hits"][0]["node_id"], "n1")
        self.assertIn("No task completion", s2c_journey.render(result))

    def test_no_snapshot_marks_action_unchecked(self):
        result = s2c_journey.project(self.graph, self.scenario)
        self.assertEqual(result["success_action"]["status"], "not_checked")

    def test_cross_origin_target_is_refused(self):
        self.scenario["target"] = "https://another.example/"
        with self.assertRaisesRegex(ValueError, "origin"):
            s2c_journey.project(self.graph, self.scenario)


if __name__ == "__main__":
    unittest.main()
