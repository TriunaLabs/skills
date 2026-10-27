"""Robot visibility exposes dependencies without claiming index status."""

from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "scan-to-comprehend" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import s2c_robot_visibility  # noqa: E402
import s2c_visualize  # noqa: E402


class RobotVisibilityTests(unittest.TestCase):
    def setUp(self):
        nodes = [
            {"tag": "h1", "text": "Reliable garden planning", "visible": True},
            {"tag": "p", "text": "Important plan details", "visible": True},
            {"tag": "a", "text": "Our pricing", "href": "/pricing", "visible": True},
        ]
        self.snapshot = {"schema": "s2c-browser-capture/v1", "audited_on": "2026-10-27",
                         "url": "https://example.com/services", "frames": [
                             {"id": "desktop", "url": "https://example.com/services", "nodes": nodes}]}

    def test_raw_rendered_and_robots_checks_are_separate(self):
        raw = ("<html><head><meta name='robots' content='noindex'><script src='/assets/app.js'></script>"
               "<link rel='stylesheet' href='/assets/site.css'></head><body><h1>Reliable garden planning</h1></body></html>")
        result = s2c_robot_visibility.project(raw, self.snapshot, important=["Important plan details"],
                                              robots={"status": "retrieved", "text": "User-agent: *\nDisallow: /assets/"})
        self.assertEqual(result["phrases"][0]["status"], "rendered_only")
        self.assertEqual({item["id"] for item in result["checks"]},
                         {"noindex", "robots_assets", "rendered_only_text", "rendered_only_links"})
        self.assertNotIn("robots_page", {item["id"] for item in result["checks"]})
        source = {"schema_version": "1.1", "audited_on": "2026-10-27", "reports": [{
            "source": "https://example.com/services", "headings": [], "findings": [], "suggestions": [],
            "strengths": [], "next_checks": [], "estimated_cognitive_load": {"score": 0}}]}
        report = s2c_visualize.render(source, robot_visibility=result)
        self.assertIn("id='robot-visibility'", report)
        self.assertIn("FINAL PAGE / ACTION PLAN", report)
        self.assertIn("Important text relies on rendering", report)

    def test_initial_html_content_does_not_get_rendered_only_warning(self):
        raw = "<html><body><h1>Reliable garden planning</h1><p>Important plan details</p></body></html>"
        result = s2c_robot_visibility.project(raw, self.snapshot, important=["Important plan details"],
                                              robots={"status": "absent", "text": ""})
        self.assertEqual(result["phrases"][0]["status"], "both")
        self.assertNotIn("rendered_only_text", {item["id"] for item in result["checks"]})

    def test_noscript_text_counts_as_source_text(self):
        raw = "<html><body><noscript><p>Important plan details</p></noscript></body></html>"
        result = s2c_robot_visibility.project(raw, self.snapshot, important=["Important plan details"],
                                              robots={"status": "absent", "text": ""})
        self.assertEqual(result["phrases"][0]["status"], "both")

    def test_wanted_text_requires_no_interaction_review(self):
        raw = "<html><body><p>Hidden eligibility rule</p></body></html>"
        result = s2c_robot_visibility.project(raw, self.snapshot,
                                              important=["Hidden eligibility rule", "Required cancellation detail"],
                                              robots={"status": "absent", "text": ""})
        self.assertEqual([row["status"] for row in result["phrases"]], ["source_only", "not_found"])
        self.assertTrue({"source_only_text", "wanted_text_missing"}.issubset(
            {item["id"] for item in result["checks"]}))


if __name__ == "__main__":
    unittest.main()
