import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/update_version.sh"
COMMIT = "a" * 40
TAG = "v153.0.8010.37-" + COMMIT
DIGEST = "sha256:" + "b" * 64


class UpdateVersionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.output = self.root / "output"
        self.url_log = self.root / "url"
        (self.root / "Cromite.spec").write_text(
            f"%global _commit {COMMIT}\nVersion: 153.0.8010.37\nRelease: 6%{{?dist}}\n"
            "Source0: https://example.invalid/old.tar.gz\n%changelog\n"
        )
        self.release = {"tag_name": TAG, "draft": False, "assets": [{
            "name": "chrome-lin64.tar.gz", "browser_download_url": "https://github.com/uazo/cromite/fixture",
            "digest": DIGEST,
        }]}
        curl = self.bin / "curl"
        curl.write_text('#!/usr/bin/env bash\nfor url; do :; done\nprintf "%s" "$url" > "$URL_LOG"\n'
                        'if [[ "$url" == *"/releases/tags/"* ]]; then printf "%s" "$RELEASE"; '
                        'else printf "[%s]" "$RELEASE"; fi\n')
        curl.chmod(0o755)
        self.env = {**os.environ, "PATH": str(self.bin) + ":" + os.environ["PATH"],
                    "GITHUB_OUTPUT": str(self.output), "URL_LOG": str(self.url_log),
                    "RELEASE": json.dumps(self.release), "UPSTREAM_TAG": "", "FORCE_BUILD": "false"}

    def test_pinned_release_uses_tag_endpoint(self):
        result = subprocess.run(["bash", str(SCRIPT)], cwd=self.root,
                                env={**self.env, "UPSTREAM_TAG": TAG, "FORCE_BUILD": "true"},
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.url_log.read_text().endswith("/releases/tags/" + TAG))
        self.assertIn("asset_digest=" + DIGEST, self.output.read_text())

    def test_invalid_tag_is_rejected_before_network(self):
        result = subprocess.run(["bash", str(SCRIPT)], cwd=self.root,
                                env={**self.env, "UPSTREAM_TAG": "invalid"}, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.url_log.exists())

    def test_current_release_still_exports_digest(self):
        result = subprocess.run(["bash", str(SCRIPT)], cwd=self.root, env=self.env,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("updated=false", self.output.read_text())
        self.assertIn("asset_digest=" + DIGEST, self.output.read_text())


if __name__ == "__main__":
    unittest.main()
