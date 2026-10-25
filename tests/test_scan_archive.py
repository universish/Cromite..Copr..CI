"""End-to-end checks of the CI scan gate, with no external API calls."""

import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import unittest


SCAN_SCRIPT = Path(__file__).resolve().parents[1] / "scripts/scan_archive.sh"
REAL_CLAMSCAN = shutil.which("clamscan")
CLEAN_STATS = {"malicious": 0, "suspicious": 0, "harmless": 1, "undetected": 1}


class ScanArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.scan_tmp = self.root / "tmp"
        self.scan_tmp.mkdir()
        self.marker = self.root / "scanned"
        self.report = self.root / "report.json"
        self.archive = self.root / "chrome-lin64.tar.gz"
        with tarfile.open(self.archive, "w:gz") as archive:
            archive.add("/bin/true", arcname="chrome-lin/chrome")
        self.env = {**os.environ, "PATH": f"{self.bin_dir}:{os.environ['PATH']}",
                    "TMPDIR": str(self.scan_tmp), "VT_API_KEY": "test-key",
                    "SCAN_MARKER": str(self.marker), "SCAN_STATUS": "0",
                    "VT_HTTP_CODE": "200", "CURL_STATUS": "0",
                    "VT_REQUEST_INTERVAL": "0", "EXPECTED_SHA256": "",
                    "VT_JSON": json.dumps({"data": {"attributes": {"last_analysis_stats": CLEAN_STATS}}})}
        self.command("clamscan", '''
for target; do :; done
test -s "$target/chrome-lin/chrome" || exit 2
touch "$SCAN_MARKER"
exit "$SCAN_STATUS"
''')
        self.command("curl", '''
if [[ "$CURL_STATUS" != 0 ]]; then exit "$CURL_STATUS"; fi
while [[ $# -gt 0 ]]; do
    if [[ "$1" == --output ]]; then
        printf '%s' "$VT_JSON" > "$2"
        shift
    fi
    shift
done
printf '%s' "$VT_HTTP_CODE"
''')

    def command(self, name, body):
        path = self.bin_dir / name
        path.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + body)
        path.chmod(0o755)

    def run_scan(self, **env):
        self.marker.unlink(missing_ok=True)
        self.report.unlink(missing_ok=True)
        result = subprocess.run(
            ["bash", str(SCAN_SCRIPT), str(self.archive), str(self.report)],
            env={**self.env, **env}, text=True, capture_output=True, timeout=10,
        )
        self.assertEqual(list(self.scan_tmp.iterdir()), [], "Temporary scan files leaked")
        return result

    def test_success_records_both_hash_checks_and_clamav(self):
        digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        result = self.run_scan(EXPECTED_SHA256="sha256:" + digest)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(self.report.read_text())
        self.assertEqual(report["clamav"], "passed")
        self.assertEqual(report["archive_sha256"], digest)
        self.assertEqual(len(report["virustotal"]["files"]), 2)
        self.assertEqual(report["virustotal"]["status"], "complete")
        self.assertTrue(self.marker.exists())

    def test_missing_api_key_warns_and_allows_packaging(self):
        result = self.run_scan(VT_API_KEY="")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("::warning::", result.stdout)
        report = json.loads(self.report.read_text())
        self.assertEqual(report["virustotal"]["counts"]["skipped_no_key"], 2)

    def test_clamav_detection_and_errors_block_packaging(self):
        for status in ("1", "2"):
            with self.subTest(status=status):
                result = self.run_scan(SCAN_STATUS=status)
                self.assertEqual(result.returncode, int(status), result.stderr)
                self.assertFalse(self.report.exists())

    def test_virustotal_detection_blocks_packaging(self):
        stats = {**CLEAN_STATS, "malicious": 1}
        response = {"data": {"attributes": {"last_analysis_stats": stats}}}
        result = self.run_scan(VT_JSON=json.dumps(response))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.report.exists())

    def test_api_and_network_errors_warn_and_allow_packaging(self):
        for code in ("401", "403", "429", "500"):
            with self.subTest(code=code):
                result = self.run_scan(VT_HTTP_CODE=code)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("::warning::", result.stdout)
        result = self.run_scan(CURL_STATUS="28")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.report.read_text())["virustotal"]["status"], "partial")

    def test_incomplete_and_malformed_results_warn_and_allow_packaging(self):
        for body in ("{}", "not JSON", json.dumps({"data": {"attributes": {"last_analysis_stats": {}}}})):
            with self.subTest(body=body):
                result = self.run_scan(VT_JSON=body)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("::warning::", result.stdout)
                self.assertEqual(json.loads(self.report.read_text())["virustotal"]["status"], "partial")

    def test_upstream_digest_mismatch_blocks_before_scanning(self):
        self.assertNotEqual(self.run_scan(EXPECTED_SHA256="0" * 64).returncode, 0)
        self.assertFalse(self.marker.exists())

    def test_corrupt_archive_blocks_packaging(self):
        self.archive.write_text("not a gzip archive")
        self.assertNotEqual(self.run_scan().returncode, 0)
        self.assertFalse(self.marker.exists())

    def test_missing_archive_blocks_packaging(self):
        self.archive.unlink()
        self.assertNotEqual(self.run_scan().returncode, 0)

    @unittest.skipUnless(REAL_CLAMSCAN, "ClamAV is required for the integration test")
    def test_real_clamav_detects_signature_beyond_100_mb(self):
        database = self.root / "db"
        database.mkdir()
        marker = b"Cromite harmless scanner test marker"
        (database / "test.ndb").write_text("Cromite.Test.Marker:0:*:" + marker.hex() + "\n")
        sample = self.root / "resources.pak"
        with sample.open("wb") as stream:
            stream.seek(120 * 1024 * 1024)
            stream.write(marker)
        with tarfile.open(self.archive, "w:gz") as archive:
            archive.add("/bin/true", arcname="chrome-lin/chrome")
            archive.add(sample, arcname="chrome-lin/resources.pak")
        self.command("clamscan", "exec " + shlex.quote(REAL_CLAMSCAN)
                     + " --database=" + shlex.quote(str(database)) + ' "$@"\n')
        result = self.run_scan()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Cromite.Test.Marker", result.stdout)


if __name__ == "__main__":
    unittest.main()
