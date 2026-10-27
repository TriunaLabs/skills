"""Live S2C runs respect a site's published crawler refusal."""

from pathlib import Path
from unittest.mock import patch
import sys
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "skills/scan-to-comprehend/scripts"
sys.path.insert(0, str(SCRIPTS))
import s2c_run  # noqa: E402


class RobotsPreflightTests(unittest.TestCase):
    def test_disallowed_url_stops_before_capture(self):
        with patch.object(s2c_run.s2c_robot_visibility, "fetch_robots",
                          return_value={"status": "retrieved", "text": "User-agent: *\nDisallow: /private"}):
            with self.assertRaisesRegex(ValueError, "disallows"):
                s2c_run.public_robots_preflight("https://example.com/private")
            self.assertEqual(s2c_run.public_robots_preflight("https://example.com/public")["status"], "retrieved")

    def test_unavailable_robots_stops_live_run(self):
        with patch.object(s2c_run.s2c_robot_visibility, "fetch_robots",
                          return_value={"status": "unavailable", "text": ""}):
            with self.assertRaisesRegex(ValueError, "could not be checked"):
                s2c_run.public_robots_preflight("https://example.com/")


if __name__ == "__main__":
    unittest.main()
