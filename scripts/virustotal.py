#!/usr/bin/env python3
"""Look up the archive and every extracted regular file by SHA-256 in VirusTotal."""

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


class DetectionError(Exception):
    pass


class VirusTotal:
    def __init__(self, api_key, *, request_interval=16):
        self.api_key = api_key
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
            if result.stdout == "404":
                return 404, None
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
            raise ScanError(f"{label}: geçerli motor sonuçları yok")
        print(f"VirusTotal {label}: zararlı={stats['malicious']}, şüpheli={stats['suspicious']}, "
              f"temiz={stats['harmless']}, tespit yok={stats['undetected']}")
        if stats["malicious"]:
            raise DetectionError(f"{label}: VirusTotal zararlı tespit etti")
        return stats

    def check_hash(self, digest, label):
        code, body = self.request("GET", f"{BASE_URL}/files/{digest}")
        if code == 404:
            return {"status": "unknown_hash"}
        if code != 200:
            raise ScanError(f"{label}: beklenmeyen dosya raporu yanıtı")
        try:
            stats = body["data"]["attributes"]["last_analysis_stats"]
        except (KeyError, TypeError):
            raise ScanError(f"{label}: geçersiz dosya raporu") from None
        return {"status": "known_report", "stats": self.check_stats(stats, label)}

    def upload_archive(self, path, label, *, poll_attempts=18, poll_interval=20):
        if path.stat().st_size > MAX_UPLOAD_SIZE:
            return {"status": "unavailable_size_limit"}
        upload_url = f"{BASE_URL}/files"
        if path.stat().st_size > DIRECT_UPLOAD_SIZE:
            code, body = self.request("GET", f"{BASE_URL}/files/upload_url")
            if code != 200 or not isinstance(body, dict) or not isinstance(body.get("data"), str):
                raise ScanError(f"{label}: yükleme adresi alınamadı")
            upload_url = body["data"]
        code, body = self.request("POST", upload_url, upload=path)
        data = body.get("data") if isinstance(body, dict) else None
        analysis_id = data.get("id") if isinstance(data, dict) else None
        if code not in (200, 201) or not isinstance(analysis_id, str) or not analysis_id:
            raise ScanError(f"{label}: yüklemeden analiz kimliği alınamadı")
        for attempt in range(poll_attempts):
            if attempt:
                time.sleep(poll_interval)
            code, body = self.request("GET", f"{BASE_URL}/analyses/{quote(analysis_id, safe='')}")
            if code != 200:
                raise ScanError(f"{label}: analiz sonucu alınamadı")
            data = body.get("data") if isinstance(body, dict) else None
            attributes = data.get("attributes") if isinstance(data, dict) else None
            if not isinstance(attributes, dict):
                raise ScanError(f"{label}: geçersiz analiz yanıtı")
            if attributes.get("status") == "completed":
                return {"status": "uploaded_analysis",
                        "stats": self.check_stats(attributes.get("stats"), label)}
            if attributes.get("status") not in ("queued", "in-progress"):
                raise ScanError(f"{label}: bilinmeyen analiz durumu")
        raise ScanError(f"{label}: analiz süresi doldu")


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def scan_files(archive, extracted, client, *, max_requests=None):
    if max_requests is not None and max_requests < 0:
        raise ValueError("VT_MAX_REQUESTS negatif olamaz")
    paths = [archive] + sorted(
        path for path in extracted.rglob("*") if path.is_file() and not path.is_symlink()
    )
    entries = []
    by_hash = {}
    request_count = 0
    api_error = None
    for path in paths:
        label = "Upstream-Cromite-Arşivi" if path == archive else str(path.relative_to(extracted))
        digest = sha256(path)
        if digest not in by_hash:
            if not client.api_key:
                by_hash[digest] = {"status": "skipped_no_key"}
            elif api_error:
                by_hash[digest] = {"status": "skipped_api_error"}
            elif max_requests is not None and request_count >= max_requests:
                by_hash[digest] = {"status": "skipped_request_limit"}
            else:
                request_count += 1
                try:
                    by_hash[digest] = client.check_hash(digest, label)
                except (ScanError, OSError) as error:
                    api_error = str(error)
                    by_hash[digest] = {"status": "skipped_api_error"}
        entries.append({"path": label, "sha256": digest, **by_hash[digest]})
    # The official upstream archive is already gzip-compressed. Submit it only
    # when the hash is unknown; a bundle result does not certify each inner file.
    archive_entry = entries[0]
    if archive_entry["status"] == "unknown_hash":
        try:
            archive_entry.update(client.upload_archive(archive, archive_entry["path"]))
        except (ScanError, OSError) as error:
            archive_entry["status"] = "skipped_upload_error"
            archive_entry["upload_error"] = str(error)
    counts = {status: sum(item["status"] == status for item in entries)
              for status in sorted({item["status"] for item in entries})}
    warnings = []
    if not client.api_key:
        warnings.append("VirusTotal anahtarı yok")
    if api_error:
        warnings.append("VirusTotal API kullanılamıyor: " + api_error)
    if counts.get("skipped_request_limit"):
        warnings.append(f"VirusTotal sorgu sınırına ({max_requests}) ulaşıldı")
    if counts.get("unknown_hash"):
        warnings.append(f"{counts['unknown_hash']} dosya özeti VirusTotal'de bulunamadı")
    if counts.get("unavailable_size_limit"):
        warnings.append("Sıkıştırılmış arşiv VirusTotal'ın 650 MiB yükleme sınırını aşıyor")
    if counts.get("skipped_upload_error"):
        warnings.append("VirusTotal arşiv yüklemesi/analizi başarısız: " + archive_entry.get("upload_error", "bilinmiyor"))
    for warning in warnings:
        print(f"::warning::{warning}. Zorunlu ClamAV ve statik kontroller başarılıysa yayınlama devam eder.")
    return {"status": "partial" if warnings else "complete", "warnings": warnings,
            "requests": request_count, "counts": counts, "files": entries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("extracted", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        client = VirusTotal(os.environ.get("VT_API_KEY", ""),
                            request_interval=float(os.environ.get("VT_REQUEST_INTERVAL", "16")))
        configured_limit = os.environ.get("VT_MAX_REQUESTS", "")
        reports = scan_files(args.archive, args.extracted, client,
                             max_requests=int(configured_limit) if configured_limit else None)
        if args.report:
            args.report.write_text(json.dumps(reports, indent=2) + "\n")
    except DetectionError as error:
        parser.exit(1, f"VirusTotal zararlı tespiti: {error}\n")
    except (ScanError, OSError, ValueError) as error:
        parser.exit(1, f"VirusTotal dosya envanteri oluşturulamadı: {error}\n")


if __name__ == "__main__":
    main()
