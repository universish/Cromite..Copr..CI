#!/usr/bin/env bash
# Yalnızca GitHub Actions'ta çalıştırılır; RPM spec dosyası bu betiği çağırmaz.
set -euo pipefail

if [[ $# -ne 1 || ! -s "$1" ]]; then
    echo "Kullanım: bash scripts/scan_archive.sh <chrome-lin64.tar.gz>" >&2
    exit 1
fi

ARCHIVE="$1"
SCAN_DIR="$(mktemp -d)"
trap 'rm -rf -- "$SCAN_DIR"' EXIT

TAR_HASH="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
echo "🔒 Taranacak arşivin SHA-256 özeti: $TAR_HASH"

if [[ -z "${VT_API_KEY:-}" ]]; then
    echo "⚠️ VIRUSTOTAL_API_KEY tanımlı değil; VirusTotal sorgusu atlanıyor. ClamAV zorunludur."
else
    echo "🔍 VirusTotal üzerinde arşivin SHA-256 özeti sorgulanıyor..."
    HTTP_CODE="$(curl --silent --show-error --connect-timeout 30 --max-time 120 \
        --output "$SCAN_DIR/virustotal.json" --write-out '%{http_code}' \
        --header "x-apikey: ${VT_API_KEY}" \
        "https://www.virustotal.com/api/v3/files/$TAR_HASH")"

    case "$HTTP_CODE" in
        200)
            if ! MALICIOUS="$(jq -er '
                .data.attributes.last_analysis_stats.malicious
                | select(type == "number" and . >= 0 and . == floor)
            ' "$SCAN_DIR/virustotal.json")"; then
                echo "❌ VirusTotal yanıtı geçerli bir tarama sonucu içermiyor." >&2
                exit 1
            fi
            if [[ "$MALICIOUS" != "0" ]]; then
                echo "❌ VirusTotal: $MALICIOUS zararlı tespiti. Paketleme durduruldu." >&2
                exit 1
            fi
            echo "✅ VirusTotal: 0 zararlı tespiti."
            ;;
        404)
            echo "ℹ️ Arşiv henüz VirusTotal'de kayıtlı değil; zorunlu ClamAV taramasıyla devam ediliyor."
            ;;
        *)
            echo "❌ VirusTotal sorgusu başarısız (HTTP $HTTP_CODE); paketleme durduruldu." >&2
            exit 1
            ;;
    esac
fi

echo "🦠 Arşiv içeriği GitHub Actions üzerinde ClamAV ile taranıyor..."
mkdir "$SCAN_DIR/extracted"
tar -xzf "$ARCHIVE" -C "$SCAN_DIR/extracted"

# Chromium ikilisi varsayılan 100 MB sınırını aşar. Sınır aşımı sessizce
# atlanmamalı; taranamayan büyük dosyalar da yayınlamayı durdurmalıdır.
# https://github.com/Cisco-Talos/clamav/blob/clamav-1.4.6/docs/man/clamscan.1.in
if clamscan --recursive --infected --alert-macros=yes \
    --max-filesize=2000M --max-scansize=2000M --max-scantime=0 \
    --alert-exceeds-max=yes --fail-if-cvd-older-than=7 \
    "$SCAN_DIR/extracted"; then
    echo "✅ ClamAV taraması tamamlandı; RPM ve SRPM paketlemesine izin veriliyor."
else
    SCAN_STATUS=$?
    if [[ "$SCAN_STATUS" -eq 1 ]]; then
        echo "❌ ClamAV zararlı içerik veya tarama sınırı aşımı bildirdi; paketleme durduruldu." >&2
    else
        echo "❌ ClamAV taraması tamamlanamadı (çıkış kodu: $SCAN_STATUS); paketleme durduruldu." >&2
    fi
    exit "$SCAN_STATUS"
fi
