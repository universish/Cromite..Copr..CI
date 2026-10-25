#!/usr/bin/env bash
# Yalnızca GitHub Actions'ta çalıştırılır; RPM spec dosyası bu betiği çağırmaz.
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 || ! -s "$1" ]]; then
    echo "Kullanım: bash scripts/scan_archive.sh <chrome-lin64.tar.gz> [rapor.json]" >&2
    exit 1
fi

ARCHIVE="$1"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SCAN_DIR="$(mktemp -d)"
trap 'rm -rf -- "$SCAN_DIR"' EXIT

TAR_HASH="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
echo "🔒 Taranacak arşivin SHA-256 özeti: $TAR_HASH"
if [[ -n "${EXPECTED_SHA256:-}" ]]; then
    EXPECTED_SHA256="${EXPECTED_SHA256#sha256:}"
    if [[ ! "$EXPECTED_SHA256" =~ ^[0-9a-f]{64}$ || "$TAR_HASH" != "$EXPECTED_SHA256" ]]; then
        echo "❌ Upstream SHA-256 özeti eşleşmiyor; tarama ve paketleme durduruldu." >&2
        exit 1
    fi
fi

echo "🔍 Kabuk örüntüleri, ELF RPATH/RUNPATH ve GLIBC gereksinimleri denetleniyor..."
python3 "$SCRIPT_DIR/check_payload.py" "$ARCHIVE" "$SCAN_DIR/extracted" "$SCAN_DIR/payload.json"

echo "🦠 Arşiv içeriği GitHub Actions üzerinde ClamAV ile taranıyor..."

# Chromium ikilisi varsayılan 100 MB sınırını aşar. Sınır aşımı sessizce
# atlanmamalı; taranamayan büyük dosyalar da yayınlamayı durdurmalıdır.
# https://github.com/Cisco-Talos/clamav/blob/clamav-1.4.6/docs/man/clamscan.1.in
if clamscan --recursive --infected --alert-macros=yes \
    --max-filesize=2000M --max-scansize=2000M --max-scantime=0 \
    --alert-exceeds-max=yes --fail-if-cvd-older-than=7 \
    "$SCAN_DIR/extracted"; then
    echo "✅ ClamAV taraması tamamlandı."
else
    SCAN_STATUS=$?
    if [[ "$SCAN_STATUS" -eq 1 ]]; then
        echo "❌ ClamAV zararlı içerik veya tarama sınırı aşımı bildirdi; paketleme durduruldu." >&2
    else
        echo "❌ ClamAV taraması tamamlanamadı (çıkış kodu: $SCAN_STATUS); paketleme durduruldu." >&2
    fi
    exit "$SCAN_STATUS"
fi

python3 "$SCRIPT_DIR/virustotal.py" "$ARCHIVE" "$SCAN_DIR/extracted" --report "$SCAN_DIR/virustotal.json"
if [[ $# -eq 2 ]]; then
    mkdir -p -- "$(dirname -- "$2")"
    jq -s '.[0] + {static_checks: "passed", clamav: "passed", virustotal: .[1]}' \
        "$SCAN_DIR/payload.json" "$SCAN_DIR/virustotal.json" > "$2"
fi
echo "✅ Zorunlu statik kontroller ve ClamAV başarılı; VirusTotal sonuçları/uyarıları kaydedildi."
