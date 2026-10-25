#!/usr/bin/env python3
"""Extract and inspect the public Cromite payload without executing its programs."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import tarfile


SHELL_PATTERNS = re.compile(
    r"\bLD_(?:PRELOAD|AUDIT)\b|\bbase64\s+(?:-d\b|--decode\b)"
    r"|\beval\s+[\"']?\$\(|\b(?:curl|wget)\b[^\n]*\|\s*(?:ba)?sh\b|/dev/tcp/",
    re.IGNORECASE,
)
WRITABLE_PATHS = ("/tmp", "/var/tmp", "/dev/shm", "/home", "/run/user")


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inspect_payload(root):
    root = Path(root)
    candidates = (root / "chrome-lin/chrome", root / "chrome")
    main_binary = next((path for path in candidates if path.is_file() and not path.is_symlink()), None)
    if main_binary is None:
        raise ValueError("Cromite ana ikilisi (chrome-lin/chrome veya chrome) bulunamadı")
    with main_binary.open("rb") as stream:
        header = stream.read(20)
    if (len(header) < 20 or header[:6] != b"\x7fELF\x02\x01"
            or struct.unpack_from("<H", header, 18)[0] != 62):
        raise ValueError("Cromite ana ikilisi beklenen x86-64 ELF dosyası değil")

    glibc_versions = set()
    elf_count = script_count = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        with path.open("rb") as stream:
            prefix = stream.read(256)
        relative = path.relative_to(root)
        if prefix.startswith(b"#!") or path.suffix == ".sh" or path.name == "chrome-wrapper":
            script_count += 1
            for number, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
                if line.lstrip().startswith("#"):
                    continue
                if SHELL_PATTERNS.search(line):
                    raise ValueError(f"Şüpheli kabuk örüntüsü: {relative}:{number}; inceleme gerekli")
        if not prefix.startswith(b"\x7fELF"):
            continue
        elf_count += 1
        result = subprocess.run(
            ["readelf", "--dynamic", "--version-info", str(path)],
            text=True, capture_output=True,
        )
        if result.returncode:
            raise ValueError(f"ELF metadata okunamadı: {relative}")
        for search_path in re.findall(r"\((?:RPATH|RUNPATH)\).*?\[(.*?)\]", result.stdout):
            for entry in search_path.split(":"):
                if any(entry == base or entry.startswith(base + "/") for base in WRITABLE_PATHS):
                    raise ValueError(f"Yazılabilir konuma yönelen RPATH/RUNPATH: {relative}: {entry}")
        glibc_versions.update(re.findall(r"\bGLIBC_([0-9]+(?:\.[0-9]+)+)\b", result.stdout))
    if not glibc_versions:
        raise ValueError("Upstream ELF dosyalarının GLIBC gereksinimi belirlenemedi")
    return {
        "main_binary": str(main_binary.relative_to(root)),
        "main_binary_sha256": sha256(main_binary),
        "main_binary_size": main_binary.stat().st_size,
        "architecture": "x86_64",
        "min_glibc": max(glibc_versions, key=lambda v: tuple(map(int, v.split(".")))),
        "elf_files_checked": elf_count,
        "scripts_checked": script_count,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        # data rejects paths and links escaping the extraction directory.
        with tarfile.open(args.archive, "r:gz") as archive:
            archive.extractall(args.destination, filter="data")
        report = inspect_payload(args.destination)
        report["archive_sha256"] = sha256(args.archive)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
        print(f"Statik kontroller tamamlandı: {report['elf_files_checked']} ELF, "
              f"{report['scripts_checked']} betik; GLIBC >= {report['min_glibc']}")
    except (OSError, ValueError, tarfile.TarError) as error:
        parser.exit(1, f"Payload doğrulaması başarısız: {error}\n")


if __name__ == "__main__":
    main()
