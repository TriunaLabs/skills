"""Public URL intake constraints for the local S2C test website."""

import socket
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from playground.server import completed_fields, valid_public_url


class PlaygroundURLTests(unittest.TestCase):
    def test_accepts_public_https_page(self):
        addresses = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("104.21.85.128", 443))]
        with patch("playground.server.socket.getaddrinfo", return_value=addresses):
            self.assertEqual(valid_public_url(" https://example.com/page "), "https://example.com/page")

    def test_rejects_private_or_mixed_dns_answers(self):
        public = (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("104.21.85.128", 443))
        private = (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))
        with patch("playground.server.socket.getaddrinfo", return_value=[public, private]):
            with self.assertRaisesRegex(ValueError, "public addresses"):
                valid_public_url("https://example.com/")

    def test_rejects_credentials_and_non_web_port(self):
        for url in ("https://name:secret@example.com/", "https://example.com:8080/"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                valid_public_url(url)

    def test_report_link_uses_playground_id_when_engine_id_differs(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / ("a" * 32)
            folder.mkdir()
            (folder / "browser-rubric.json").write_text(json.dumps({"score": {"earned": 10, "assessed": 10}, "counts": {"warning": 0}}))
            (folder / "audit.json").write_text(json.dumps({"reports": [{"findings": []}]}))
            result = completed_fields(folder, {"run_id": "b" * 32, "audited_on": "2026-10-27", "rubric_version": "1.0.0"})
            self.assertEqual(result["report_url"], f"/api/runs/{'a' * 32}/report")


if __name__ == "__main__":
    unittest.main()
