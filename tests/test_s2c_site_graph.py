"""Bounded site traversal distinguishes raw and rendered start-page routes."""

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/scan-to-comprehend/scripts"))
import s2c_site_graph  # noqa: E402


class SiteGraphTests(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / "examples/s2c-demo"
        self.start = (self.root / "index.html").as_uri()
        self.fetch = s2c_site_graph.fixture_fetch(self.root)
        self.snapshot = {"schema": "s2c-browser-capture/v1", "url": self.start, "frames": [{
            "id": "desktop", "url": self.start, "nodes": [
                {"id": "n00001", "tag": "a", "href": "programs.html", "visible": True},
                {"id": "n00002", "tag": "a", "href": "siblings.html", "visible": True},
                {"id": "n00003", "tag": "a", "href": "https://elsewhere.example/", "visible": True},
            ]}]}

    def test_rendered_link_shortens_task_route_and_missing_page_is_reported(self):
        result = s2c_site_graph.crawl(self.start, self.fetch, max_depth=2,
                                      snapshot=self.snapshot, target="siblings.html")
        self.assertEqual(result["coverage"]["fetched_pages"], 5)
        self.assertEqual(result["coverage"]["skipped_pages"], 1)
        self.assertEqual([Path(url).name for url in result["task_path"]["initial_html"]],
                         ["index.html", "corrected.html", "siblings.html"])
        self.assertEqual([Path(url).name for url in result["task_path"]["rendered_start"]],
                         ["index.html", "siblings.html"])
        self.assertEqual(result["rendered_overlay"]["edges"][1]["node_id"], "n00002")
        self.assertIn("Rendered start page", s2c_site_graph.render_report(result))

    def test_unfetched_target_is_not_counted_as_reachable(self):
        result = s2c_site_graph.crawl(self.start, self.fetch, max_depth=1,
                                      snapshot=self.snapshot, target="siblings.html")
        self.assertEqual(result["task_path"]["initial_html"], [])
        self.assertEqual(result["task_path"]["rendered_start"], [])

    def test_budget_and_snapshot_url_are_enforced(self):
        with self.assertRaisesRegex(ValueError, "budget"):
            s2c_site_graph.crawl(self.start, self.fetch, max_pages=0)
        self.snapshot["frames"][0]["url"] = "file:///other/index.html"
        with self.assertRaisesRegex(ValueError, "must match"):
            s2c_site_graph.crawl(self.start, self.fetch, snapshot=self.snapshot)


if __name__ == "__main__":
    unittest.main()
