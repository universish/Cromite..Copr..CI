#!/usr/bin/env bash
# Fedora COPR derleme tetikleyicisi ve Webhook bildirim gönderici
# CI Deposu  : https://github.com/universish/Cromite..Copr..CI
# COPR Deposu: https://copr.fedorainfracloud.org/coprs/universish/Cromite../
set -euo pipefail

VERSION="${1:?Sürüm parametresi gerekli (örn. 153.0.8010.37)}"
COMMIT="${2:?Commit parametresi gerekli}"
TAG_NAME="v${VERSION}-${COMMIT}"
TARBALL_URL="https://github.com/uazo/cromite/releases/download/${TAG_NAME}/chrome-lin64.tar.gz"
UPSTREAM_URL="https://github.com/uazo/cromite/releases/tag/${TAG_NAME}"
CI_REPO_URL="https://github.com/universish/Cromite..Copr..CI"
COPR_URL="https://copr.fedorainfracloud.org/coprs/universish/Cromite../"

# 1. Fedora COPR Özel Webhook Tetiklemesi
if [[ -n "${COPR_WEBHOOK_URL:-}" ]]; then
    echo "📦 Fedora COPR webhook tetikleniyor (${COPR_URL})..."
    curl -fsSL -X POST "${COPR_WEBHOOK_URL}"
    echo "✅ Fedora COPR derleme isteği gönderildi."
else
    echo "ℹ️ COPR_WEBHOOK_URL tanımlı değil, doğrudan COPR webhook tetiklemesi atlandı."
fi

# 2. Güncelleme Bildirimi Webhook'u (Discord / Slack / Gotify / Genel JSON)
if [[ -n "${NOTIFY_WEBHOOK_URL:-}" ]]; then
    echo "🔔 Güncelleme bildirimi webhook adresine gönderiliyor..."
    PAYLOAD="$(jq -n \
        --arg ver "${VERSION}" \
        --arg commit "${COMMIT:0:7}" \
        --arg upstream "${UPSTREAM_URL}" \
        --arg tarball "${TARBALL_URL}" \
        --arg copr "${COPR_URL}" \
        --arg cirepo "${CI_REPO_URL}" \
        '{
            username: "Cromite COPR CI Bildirici",
            content: "🚀 **Cromite \($ver)** (`\($commit)`) yayınlandı! `chrome-lin64.tar.gz` ile Fedora (44, 45, Rawhide) ve openSUSE (Tumbleweed, Leap 16) için COPR derlemesi tetiklendi.",
            text: "🚀 *Cromite \($ver)* (`\($commit)`) yayınlandı!
• Tarball: \($tarball)
• COPR: \($copr)
• CI Repo: \($cirepo)",
            embeds: [
                {
                    title: "Cromite \($ver) — Fedora & openSUSE RPM Güncellemesi",
                    url: $copr,
                    color: 3447003,
                    fields: [
                        { name: "Sürüm", value: $ver, inline: true },
                        { name: "Commit", value: $commit, inline: true },
                        { name: "Hedef Mimariler", value: "x86_64, aarch64 (arm64)", inline: true },
                        { name: "Hedef Dağıtımlar", value: "Fedora 44, Fedora 45, Fedora Rawhide, openSUSE Tumbleweed, openSUSE Leap 16", inline: false },
                        { name: "Kaynak Tarball", value: $tarball, inline: false },
                        { name: "Fedora COPR Deposu", value: $copr, inline: false },
                        { name: "GitHub CI Deposu", value: $cirepo, inline: false }
                    ]
                }
            ]
        }')"

    curl -fsSL -H "Content-Type: application/json" -X POST -d "${PAYLOAD}" "${NOTIFY_WEBHOOK_URL}"
    echo "✅ Bildirim başarıyla gönderildi."
else
    echo "ℹ️ NOTIFY_WEBHOOK_URL tanımlı değil, bildirim gönderimi atlandı."
fi
