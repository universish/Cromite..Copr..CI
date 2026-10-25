import json
from pathlib import Path
import re
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
CHROOTS = json.loads((ROOT / "tests/fixtures/copr_chroots.json").read_text())
MIN_GLIBC = re.search(r"^%global _min_glibc ([0-9.]+)$", (ROOT / "Cromite.spec").read_text(), re.MULTILINE).group(1)


class SpecTests(unittest.TestCase):
    def test_all_requested_chroot_and_architecture_combinations(self):
        for chroot in CHROOTS:
            with self.subTest(chroot=chroot):
                family, release, arch = chroot.rsplit("-", 2)
                defines = ["--undefine", "fedora", "--undefine", "rhel", "--undefine", "suse_version"]
                if chroot.startswith("opensuse-"):
                    defines += ["--define", "suse_version 1600"]
                elif family == "fedora":
                    defines += ["--define", "fedora " + ("46" if release == "rawhide" else release)]
                else:
                    defines += ["--define", "rhel " + release]
                query = ["rpmspec", "-q", "--target", arch, *defines, str(ROOT / "Cromite.spec")]
                result = subprocess.run([*query, "--requires"], text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                requirements = result.stdout.splitlines()
                self.assertFalse(any(" or " in line for line in requirements))
                self.assertIn("glibc >= " + MIN_GLIBC, requirements)
                self.assertEqual("box64" in requirements, arch == "aarch64")
                result = subprocess.run([*query, "--buildrequires"], text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("clamav", result.stdout)
                self.assertNotIn("curl", result.stdout)


if __name__ == "__main__":
    unittest.main()
