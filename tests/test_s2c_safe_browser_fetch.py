"""A browser resource must pass the pinned public-IP transport."""

from pathlib import Path
import json
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
FETCHER = ROOT / "skills/scan-to-comprehend/scripts/s2c_safe_browser_fetch.py"


class SafeBrowserFetchTests(unittest.TestCase):
    def test_local_resource_is_refused(self):
        result = subprocess.run([sys.executable, str(FETCHER), "http://127.0.0.1/private"],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout), {"error": "ValueError"})


if __name__ == "__main__":
    unittest.main()
