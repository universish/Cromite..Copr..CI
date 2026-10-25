#!/usr/bin/env python3
"""Check public Cromite files; warn when an unknown file exceeds the upload limit."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from urllib.parse import quote, urlsplit


BASE_URL = "https://www.virustotal.com/api/v3"
MAX_UPLOAD_SIZE = 650 * 1024 * 1024
DIRECT_UPLOAD_SIZE = 32 * 1024 * 1024


class ScanError(Exception):
    pass


class VirusTotal:
    def __init__(self, api_key, *, poll_attempts=18, poll_interval=20, request_interval=16):
        if not api_key:
            raise ScanError("VIRUSTOTAL_API_KEY tanımlı değil; VirusTotal doğrulaması zorunludur")
        self.api_key = api_key
        self.poll_attempts = poll_attempts
        self.poll_interval = poll_interval
        self.request_interval = request_interval
        self.last_request = None

    def request(self, method, url, *, upload=None):
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.hostname != "www.virustotal.com"
                or parsed.username or parsed.password or parsed.port not in (None, 443)):
            raise ScanError("VirusTotal yanıtında güvenilmeyen yükleme adresi")
        if self.last_request is not None:
            # The public API allows four requests per minute.
            time.sleep(max(0, self.request_interval - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic()
        with tempfile.TemporaryDirectory() as temp:
            response_file = Path(temp) / "response.json"
            command = [
                "curl", "--silent", "--show-error", "--connect-timeout", "30",
                "--max-time", "600" if upload else "120", "--request", method,
                "--header", "x-apikey: " + self.api_key,
                "--output", str(response_file), "--write-out", "%{http_code}",
            ]
            if upload:
                command.extend(["--form", "file=@" + str(upload)])
            command.append(url)
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode:
                raise ScanError("VirusTotal ağ isteği tamamlanamadı")
            if result.stdout not in ("200", "201", "404"):
                raise ScanError(f"VirusTotal API isteği başarısız (HTTP {result.stdout})")
            try:
                body = json.loads(response_file.read_text())
            except (ValueError, OSError):
                raise ScanError("VirusTotal geçerli JSON yanıtı vermedi") from None
            if not isinstance(body, dict):
                raise ScanError("VirusTotal JSON yanıtı bir nesne değil")
            return int(result.stdout), body

    @staticmethod
    def check_stats(stats, label):
        keys = ("malicious", "suspicious", "harmless", "undetected")
        if (not isinstance(stats, dict)
                or any(type(stats.get(key)) is not int or stats[key] < 0 for key in keys)
                or sum(stats[key] for key in keys) == 0):
            raise ScanError(f"{label}: geçerli ve tamamlanmış motor sonuçları yok")
        print(f"VirusTotal {label}: zararlı={stats['malicious']}, şüpheli={stats['suspicious']}, "
              f"temiz={stats['harmless']}, tespit yok={stats['undetected']}")
        if stats["malicious"]:
            raise ScanError(f"{label}: VirusTotal zararlı tespit etti")
        return stats

    def check_file(self, path, label):
        path = Path(path)
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        print(f"VirusTotal {label}: SHA-256 {digest}")
        code, body = self.request("GET", f"{BASE_URL}/files/{digest}")
        if code == 200:
            stats = self.check_stats(body.get("data", {}).get("attributes", {}).get("last_analysis_stats"), label)
            return {"label": label, "sha256": digest, "status": "known_report", "stats": stats}
        if code != 404:
            raise ScanError(f"{label}: beklenmeyen dosya raporu yanıtı (HTTP {code})")
        if path.stat().st_size > MAX_UPLOAD_SIZE:
            print(f"::warning::{label}: dosya özeti VirusTotal'de yok ve dosya 650 MiB yükleme sınırını aşıyor. "
                  "VirusTotal sonucu yok; zorunlu ClamAV ve statik kontroller esas alınacak.")
            return {"label": label, "sha256": digest, "status": "unavailable_size_limit"}
        upload_url = f"{BASE_URL}/files"
        if path.stat().st_size > DIRECT_UPLOAD_SIZE:
            code, body = self.request("GET", f"{BASE_URL}/files/upload_url")
            if code != 200 or not isinstance(body.get("data"), str):
                raise ScanError(f"{label}: yükleme adresi alınamadı")
            upload_url = body["data"]
        code, body = self.request("POST", upload_url, upload=path)
        analysis_id = body.get("data", {}).get("id")
        if code not in (200, 201) or not isinstance(analysis_id, str) or not analysis_id:
            raise ScanError(f"{label}: yüklemeden analiz kimliği alınamadı")
        for attempt in range(self.poll_attempts):
            if attempt:
                time.sleep(self.poll_interval)
            code, body = self.request("GET", f"{BASE_URL}/analyses/{quote(analysis_id, safe='')}")
            attributes = body.get("data", {}).get("attributes", {})
            if code != 200:
                raise ScanError(f"{label}: analiz sonucu alınamadı")
            status = attributes.get("status")
            if status == "completed":
                stats = self.check_stats(attributes.get("stats"), label)
                return {"label": label, "sha256": digest, "status": "uploaded_analysis", "stats": stats}
            if status not in ("queued", "in-progress"):
                raise ScanError(f"{label}: bilinmeyen analiz durumu")
        raise ScanError(f"{label}: analiz süresi doldu; tamamlanmamış analiz temiz sayılmaz")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("main_binary", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        client = VirusTotal(os.environ.get("VT_API_KEY", ""),
                            request_interval=float(os.environ.get("VT_REQUEST_INTERVAL", "16")))
        reports = [
            client.check_file(args.archive, "Upstream-Cromite-Arşivi"),
            client.check_file(args.main_binary, "Ana-Cromite-ELF"),
        ]
        if args.report:
            args.report.write_text(json.dumps(reports, indent=2) + "\n")
    except (ScanError, OSError, ValueError, AttributeError, TypeError) as error:
        parser.exit(1, f"VirusTotal doğrulaması başarısız: {error}\n")


if __name__ == "__main__":
    main()
