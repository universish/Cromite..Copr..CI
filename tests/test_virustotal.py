import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.virustotal import DetectionError, ScanError, VirusTotal, scan_files


STATS = {"malicious": 0, "suspicious": 0, "harmless": 1, "undetected": 1}


class VirusTotalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / "archive.tar.gz"
        self.archive.write_bytes(b"archive")
        self.extracted = self.root / "extracted"
        self.extracted.mkdir()
        (self.extracted / "chrome").write_bytes(b"binary")
        (self.extracted / "resources.pak").write_bytes(b"resources")
        self.client = VirusTotal("test-key", request_interval=0)

    def test_queries_archive_and_every_extracted_file_by_hash(self):
        with patch.object(self.client, "request", return_value=(200, {"data": {"attributes": {
                "last_analysis_stats": STATS}}})) as request:
            report = scan_files(self.archive, self.extracted, self.client)
        self.assertEqual(report["status"], "complete")
        self.assertEqual(len(report["files"]), 3)
        self.assertEqual(request.call_count, 3)
        self.assertTrue(all(len(item["sha256"]) == 64 for item in report["files"]))

    def test_unknown_hash_is_unscanned_and_warns(self):
        output = io.StringIO()
        with patch.object(self.client, "request", return_value=(404, None)), \
                patch.object(self.client, "upload_archive", return_value={"status": "uploaded_analysis", "stats": STATS}), \
                contextlib.redirect_stdout(output):
            report = scan_files(self.archive, self.extracted, self.client)
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["counts"]["unknown_hash"], 2)
        self.assertEqual(report["counts"]["uploaded_analysis"], 1)
        self.assertIn("::warning::", output.getvalue())

    def test_api_error_skips_remaining_queries_and_warns(self):
        output = io.StringIO()
        with patch.object(self.client, "request", side_effect=ScanError("HTTP 429")) as request, \
                contextlib.redirect_stdout(output):
            report = scan_files(self.archive, self.extracted, self.client)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(report["counts"]["skipped_api_error"], 3)
        self.assertIn("HTTP 429", output.getvalue())

    def test_missing_curl_warns_and_skips(self):
        with patch("scripts.virustotal.subprocess.run", side_effect=FileNotFoundError("curl")):
            report = scan_files(self.archive, self.extracted, self.client)
        self.assertEqual(report["counts"]["skipped_api_error"], 3)

    def test_hash_request_never_uploads_file_contents(self):
        def respond(command, **kwargs):
            Path(command[command.index("--output") + 1]).write_text("{}")
            return type("Response", (), {"returncode": 0, "stdout": "404"})()

        with patch("scripts.virustotal.subprocess.run", side_effect=respond) as run:
            self.assertEqual(self.client.request("GET", "https://www.virustotal.com/api/v3/files/" + "a" * 64), (404, None))
        command = run.call_args.args[0]
        self.assertEqual(command[command.index("--request") + 1], "GET")
        self.assertNotIn("--form", command)

    def test_missing_key_skips_without_network(self):
        client = VirusTotal("", request_interval=0)
        with patch.object(client, "request") as request:
            report = scan_files(self.archive, self.extracted, client)
        request.assert_not_called()
        self.assertEqual(report["counts"]["skipped_no_key"], 3)

    def test_request_budget_hashes_all_files_but_queries_one(self):
        with patch.object(self.client, "request", return_value=(404, None)), \
                patch.object(self.client, "upload_archive", return_value={"status": "uploaded_analysis", "stats": STATS}):
            request = self.client.request
            report = scan_files(self.archive, self.extracted, self.client, max_requests=1)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(report["counts"]["skipped_request_limit"], 2)
        self.assertEqual(len(report["files"]), 3)

    def test_duplicate_file_uses_one_query(self):
        (self.extracted / "copy").write_bytes(b"binary")
        with patch.object(self.client, "request", return_value=(404, None)), \
                patch.object(self.client, "upload_archive", return_value={"status": "uploaded_analysis", "stats": STATS}):
            request = self.client.request
            report = scan_files(self.archive, self.extracted, self.client)
        self.assertEqual(request.call_count, 3)
        self.assertEqual(len(report["files"]), 4)

    def test_malicious_result_blocks(self):
        malicious = {**STATS, "malicious": 1}
        with patch.object(self.client, "request", return_value=(200, {"data": {"attributes": {
                "last_analysis_stats": malicious}}})), self.assertRaises(DetectionError):
            scan_files(self.archive, self.extracted, self.client)

    def test_invalid_report_is_operational_error(self):
        with patch.object(self.client, "request", return_value=(200, {"data": {}})), \
                self.assertRaises(ScanError):
            self.client.check_hash("a" * 64, "sample")

    def test_unknown_archive_upload_failure_is_warning(self):
        with patch.object(self.client, "request", return_value=(404, None)), \
                patch.object(self.client, "upload_archive", side_effect=ScanError("HTTP 429")):
            report = scan_files(self.archive, self.extracted, self.client)
        self.assertEqual(report["files"][0]["status"], "skipped_upload_error")
        self.assertEqual(report["status"], "partial")

    def test_compressed_archive_upload_waits_for_completed_analysis(self):
        self.archive.write_bytes(b"A" * (32 * 1024 * 1024 + 1))
        replies = [
            (200, {"data": "https://www.virustotal.com/_ah/upload/once"}),
            (200, {"data": {"id": "analysis-id"}}),
            (200, {"data": {"attributes": {"status": "queued"}}}),
            (200, {"data": {"attributes": {"status": "completed", "stats": STATS}}}),
        ]
        with patch.object(self.client, "request", side_effect=replies) as request, \
                patch("scripts.virustotal.time.sleep"):
            result = self.client.upload_archive(self.archive, "archive", poll_interval=0)
        self.assertEqual(result["status"], "uploaded_analysis")
        self.assertEqual(request.call_args_list[1].kwargs["upload"], self.archive)

    def test_uploaded_archive_malicious_result_blocks(self):
        replies = [(200, {"data": {"id": "analysis-id"}}),
                   (200, {"data": {"attributes": {"status": "completed",
                                                "stats": {**STATS, "malicious": 1}}}})]
        with patch.object(self.client, "request", side_effect=replies), \
                self.assertRaises(DetectionError):
            self.client.upload_archive(self.archive, "archive")

    def test_oversized_archive_is_not_uploaded(self):
        with patch.object(self.client, "request", return_value=(404, None)), \
                patch("pathlib.Path.stat") as stat, patch.object(self.client, "upload_archive", wraps=self.client.upload_archive):
            stat.return_value.st_size = 650 * 1024 * 1024 + 1
            report = scan_files(self.archive, self.extracted, self.client)
        self.assertEqual(report["files"][0]["status"], "unavailable_size_limit")


if __name__ == "__main__":
    unittest.main()
