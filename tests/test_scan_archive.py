"""Exercise the scan gate without accessing VirusTotal or downloading signatures."""

import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import unittest


SCAN_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "scan_archive.sh"
REAL_CLAMSCAN = shutil.which("clamscan")


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
        self.archive = self.root / "chrome-lin64.tar.gz"
        with tarfile.open(self.archive, "w:gz") as archive:
            data = b"harmless upstream fixture"
            entry = tarfile.TarInfo("chrome-lin/chrome")
            entry.size = len(data)
            archive.addfile(entry, io.BytesIO(data))

        self.env = dict(os.environ)
        self.env.update(
            PATH=f"{self.bin_dir}:{os.environ['PATH']}",
            TMPDIR=str(self.scan_tmp),
            VT_API_KEY="",
            SCAN_MARKER=str(self.marker),
            SCAN_STATUS="0",
            VT_HTTP_CODE="200",
            VT_JSON=json.dumps(
                {"data": {"attributes": {"last_analysis_stats": {"malicious": 0}}}}
            ),
            CURL_STATUS="0",
        )
        self.command("clamscan", """
for target; do :; done
test "$(cat "$target/chrome-lin/chrome")" = "harmless upstream fixture" || exit 2
touch "$SCAN_MARKER"
exit "$SCAN_STATUS"
""")
        self.command("curl", """
if [[ "$CURL_STATUS" != 0 ]]; then exit "$CURL_STATUS"; fi
while [[ $# -gt 0 ]]; do
    if [[ "$1" == --output ]]; then
        printf '%s' "$VT_JSON" > "$2"
        shift
    fi
    shift
done
printf '%s' "$VT_HTTP_CODE"
""")

    def command(self, name, body):
        path = self.bin_dir / name
        path.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + body)
        path.chmod(0o755)

    def run_scan(self, **env):
        result = subprocess.run(
            ["bash", str(SCAN_SCRIPT), str(self.archive)],
            env={**self.env, **env},
            text=True,
            capture_output=True,
            timeout=10,
        )
        self.assertEqual(list(self.scan_tmp.iterdir()), [], "Temporary scan files leaked")
        return result

    def test_clamav_is_mandatory_without_virustotal_key(self):
        result = self.run_scan()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.marker.exists())

    def test_detection_and_scanner_errors_block_packaging(self):
        for status in ("1", "2"):
            with self.subTest(status=status):
                result = self.run_scan(SCAN_STATUS=status)
                self.assertEqual(result.returncode, int(status), result.stderr)
                self.assertTrue(self.marker.exists())
                self.assertNotIn("✅ ClamAV", result.stdout)

    def test_clean_virustotal_result_still_requires_clamav(self):
        result = self.run_scan(VT_API_KEY="test-key", SCAN_STATUS="1")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertTrue(self.marker.exists())

    def test_clean_result_from_both_scanners_passes(self):
        result = self.run_scan(VT_API_KEY="test-key")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.marker.exists())

    def test_virustotal_detection_blocks_packaging(self):
        response = {"data": {"attributes": {"last_analysis_stats": {"malicious": 1}}}}
        result = self.run_scan(VT_API_KEY="test-key", VT_JSON=json.dumps(response))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.marker.exists())

    def test_unknown_virustotal_hash_still_requires_clamav(self):
        for status in ("0", "1", "2"):
            with self.subTest(status=status):
                result = self.run_scan(
                    VT_API_KEY="test-key", VT_HTTP_CODE="404", SCAN_STATUS=status
                )
                self.assertEqual(result.returncode, int(status), result.stderr)
                self.assertTrue(self.marker.exists())

    def test_virustotal_api_and_network_errors_block_packaging(self):
        for code in ("401", "403", "429", "500"):
            with self.subTest(code=code):
                result = self.run_scan(VT_API_KEY="test-key", VT_HTTP_CODE=code)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.marker.exists())
        result = self.run_scan(VT_API_KEY="test-key", CURL_STATUS="28")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.marker.exists())

    def test_invalid_virustotal_responses_do_not_count_as_clean(self):
        for value in (None, "0", -1, 0.5):
            with self.subTest(value=value):
                response = {"data": {"attributes": {"last_analysis_stats": {"malicious": value}}}}
                result = self.run_scan(VT_API_KEY="test-key", VT_JSON=json.dumps(response))
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.marker.exists())
        for body in ("{}", "not JSON"):
            with self.subTest(body=body):
                result = self.run_scan(VT_API_KEY="test-key", VT_JSON=body)
                self.assertNotEqual(result.returncode, 0)

    def test_corrupt_archive_blocks_packaging(self):
        self.archive.write_text("not a gzip archive")
        result = self.run_scan()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.marker.exists())

    def test_missing_archive_blocks_packaging(self):
        self.archive.unlink()
        result = self.run_scan()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.marker.exists())


@unittest.skipUnless(REAL_CLAMSCAN, "ClamAV is required for the large-file integration test")
class RealClamAVTests(unittest.TestCase):
    def test_detection_past_default_file_size_limit_blocks_packaging(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            database = root / "db"
            database.mkdir()
            marker = b"Cromite harmless scanner test marker"
            (database / "test.ndb").write_text(
                "Cromite.Test.Marker:0:*:" + marker.hex() + "\n"
            )
            sample = root / "chrome"
            with sample.open("wb") as stream:
                stream.seek(120 * 1024 * 1024)
                stream.write(marker)
            archive = root / "chrome-lin64.tar.gz"
            with tarfile.open(archive, "w:gz") as tar:
                tar.add(sample, arcname="chrome-lin/chrome")

            # Supply a harmless local signature database to the real scanner.
            bin_dir = root / "bin"
            bin_dir.mkdir()
            scanner = bin_dir / "clamscan"
            scanner.write_text(
                "#!/bin/sh\nexec " + shlex.quote(REAL_CLAMSCAN)
                + " --database=" + shlex.quote(str(database)) + ' "$@"\n'
            )
            scanner.chmod(0o755)
            result = subprocess.run(
                ["bash", str(SCAN_SCRIPT), str(archive)],
                env={**os.environ, "VT_API_KEY": "", "PATH": f"{bin_dir}:{os.environ['PATH']}"},
                text=True,
                capture_output=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("Cromite.Test.Marker", result.stdout)


if __name__ == "__main__":
    unittest.main()
