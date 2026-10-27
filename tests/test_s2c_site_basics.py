"""Site-basics findings must reflect the captured page and bounded link sample."""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "scan-to-comprehend" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import s2c_site_basics  # noqa: E402
import s2c_visualize  # noqa: E402


def link(label: str, href: str) -> dict:
    return {"tag": "a", "text": label, "href": href, "visible": True}


class SiteBasicsTests(unittest.TestCase):
    def setUp(self):
        self.frame = {"id": "desktop", "url": "https://example.com/", "anchor_ids": ["features"],
                      "performance": {"ttfb_ms": 121, "dom_content_loaded_ms": 300,
                                      "load_event_ms": 450, "resource_count": 8},
                      "nodes": [link("Privacy", "/privacy"), link("Contact", "/contact"),
                                link("Read terms", "/terms"), link("Features", "#features"),
                                link("Missing section", "#absent"), link("Bad page", "/missing"),
                                link("External", "https://other.example/path"),
                                link("Query", "/search?q=secret")]}
        self.snapshot = {"schema": "s2c-browser-capture/v1", "audited_on": "2026-10-27",
                         "url": "https://example.com/", "frames": [self.frame]}

    def test_reports_discovery_and_broken_fragments_without_claiming_sitewide_absence(self):
        result = s2c_site_basics.project(self.snapshot)
        self.assertEqual([item["status"] for item in result["checks"]], ["found", "found", "found"])
        self.assertEqual(result["link_summary"]["broken_fragments"], 1)
        self.assertEqual(result["performance"][0]["ttfb_ms"], 121)
        self.frame["nodes"] = [link("Home", "/")]
        result = s2c_site_basics.project(self.snapshot)
        self.assertTrue(all(item["status"] == "review" for item in result["checks"]))
        self.assertIn("this captured page", result["checks"][1]["detail"])

    def test_link_probe_is_bounded_same_origin_and_head_only(self):
        selected = s2c_site_basics.candidate_links(self.frame, max_links=3)
        self.assertEqual(selected, ["https://example.com/privacy", "https://example.com/contact",
                                    "https://example.com/terms"])
        with patch.object(s2c_site_basics, "head_status", side_effect=[200, 404, 405, 200]):
            probes = s2c_site_basics.probe_links(self.frame)
        self.assertEqual([item["result"] for item in probes[:3]],
                         ["reachable", "possible_broken", "inconclusive"])
        self.assertNotIn("https://other.example/path", [item["url"] for item in probes])
        self.assertNotIn("https://example.com/search?q=secret", [item["url"] for item in probes])

    def test_report_keeps_basics_as_separate_evidence_and_actions(self):
        self.frame["nodes"] = [link("Missing", "#absent")]
        basics = s2c_site_basics.project(self.snapshot)
        source = {"schema_version": "1.1", "audited_on": "2026-10-27", "reports": [{
            "source": "https://example.com/", "headings": [], "findings": [], "suggestions": [],
            "strengths": [], "next_checks": [], "estimated_cognitive_load": {"score": 0}}]}
        report = s2c_visualize.render(source, site_basics=basics)
        self.assertIn("id='site-basics'", report)
        self.assertIn("Broken in-page destination", report)
        self.assertIn("not field Core Web Vitals", report)
        self.assertIn("REPORT NAVIGATION", report)


if __name__ == "__main__":
    unittest.main()
