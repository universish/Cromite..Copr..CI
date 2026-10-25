import contextlib
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.virustotal import BASE_URL, MAX_UPLOAD_SIZE, ScanError, VirusTotal


STATS = {"malicious": 0, "suspicious": 0, "harmless": 1, "undetected": 1}


class VirusTotalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.file = Path(self.temp.name) / "chrome"
        self.file.write_bytes(b"harmless fixture")
        self.client = VirusTotal("test-key", poll_attempts=2, poll_interval=0, request_interval=0)

    def test_key_is_mandatory(self):
        with self.assertRaises(ScanError):
            VirusTotal("")

    def test_known_report(self):
        body = {"data": {"attributes": {"last_analysis_stats": STATS}}}
        with patch.object(self.client, "request", return_value=(200, body)):
            self.assertEqual(self.client.check_file(self.file, "ELF")["status"], "known_report")

    def test_unknown_small_file_is_uploaded_and_completed(self):
        responses = [(404, {}), (200, {"data": {"id": "analysis-id"}}),
                     (200, {"data": {"attributes": {"status": "queued"}}}),
                     (200, {"data": {"attributes": {"status": "completed", "stats": STATS}}})]
        with patch.object(self.client, "request", side_effect=responses) as request:
            report = self.client.check_file(self.file, "ELF")
        self.assertEqual(report["status"], "uploaded_analysis")
        self.assertEqual(request.call_args_list[1].args, ("POST", BASE_URL + "/files"))

    def test_large_file_uses_upload_url(self):
        responses = [(404, {}), (200, {"data": "https://www.virustotal.com/_ah/upload/token"}),
                     (200, {"data": {"id": "analysis-id"}}),
                     (200, {"data": {"attributes": {"status": "completed", "stats": STATS}}})]
        with patch.object(Path, "stat", return_value=SimpleNamespace(st_size=40 * 1024 * 1024)), \
                patch.object(self.client, "request", side_effect=responses) as request:
            self.client.check_file(self.file, "archive")
        self.assertEqual(request.call_args_list[1].args, ("GET", BASE_URL + "/files/upload_url"))
        self.assertEqual(request.call_args_list[2].kwargs["upload"], self.file)

    def test_oversized_unknown_file_warns_without_upload_or_clean_verdict(self):
        output = io.StringIO()
        with patch.object(Path, "stat", return_value=SimpleNamespace(st_size=MAX_UPLOAD_SIZE + 1)), \
                patch.object(self.client, "request", return_value=(404, {})) as request, \
                contextlib.redirect_stdout(output):
            report = self.client.check_file(self.file, "ELF")
        self.assertEqual(report["status"], "unavailable_size_limit")
        self.assertNotIn("stats", report)
        self.assertIn("::warning::", output.getvalue())
        request.assert_called_once()

    def test_analysis_timeout_is_not_success(self):
        responses = [(404, {}), (200, {"data": {"id": "id"}})]
        responses += [(200, {"data": {"attributes": {"status": "queued"}}})] * 2
        with patch.object(self.client, "request", side_effect=responses), self.assertRaises(ScanError):
            self.client.check_file(self.file, "ELF")

    def test_empty_analysis_id_is_rejected(self):
        with patch.object(self.client, "request", side_effect=[(404, {}), (200, {"data": {}})]), \
                self.assertRaises(ScanError):
            self.client.check_file(self.file, "ELF")

    def test_invalid_or_detected_stats_fail(self):
        for stats in ({}, {**STATS, "malicious": None}, {**STATS, "malicious": -1},
                      {**STATS, "malicious": 1}, dict.fromkeys(STATS, 0)):
            with self.subTest(stats=stats), self.assertRaises(ScanError):
                self.client.check_stats(stats, "ELF")

    def test_upload_does_not_send_key_to_untrusted_host(self):
        for url in ("https://example.com/upload", "http://www.virustotal.com/upload"):
            with self.subTest(url=url), patch("subprocess.run") as command, self.assertRaises(ScanError):
                self.client.request("POST", url, upload=self.file)
            command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
