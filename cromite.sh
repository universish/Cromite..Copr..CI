#!/usr/bin/env bash
# Cromite Tarayıcı Başlatıcı Betiği (/usr/bin/cromite)
# Desteklenen sistemler: Fedora 44, 45, Rawhide & openSUSE Tumbleweed, Leap 16
set -euo pipefail

if [[ -d "/usr/lib64/cromite" ]]; then
    CROMITE_DIR="/usr/lib64/cromite"
else
    CROMITE_DIR="/usr/lib/cromite"
fi

USER_FLAGS_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/cromite-flags.conf"
declare -a EXTRA_FLAGS=()

# Kullanıcı özel bayraklarını (~/.config/cromite-flags.conf) oku
if [[ -f "${USER_FLAGS_FILE}" ]]; then
    while IFS= read -r line || [[ -n "${line}" ]]; do
        [[ "${line}" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        # shellcheck disable=SC2206
        EXTRA_FLAGS+=(${line})
    done < "${USER_FLAGS_FILE}"
fi

# Wayland oturumunda Ozone platformunu otomatik etkinleştir
if [[ "${XDG_SESSION_TYPE:-}" == "wayland" ]] && [[ ! " ${EXTRA_FLAGS[*]} " =~ "--ozone-platform" ]]; then
    EXTRA_FLAGS+=("--ozone-platform-hint=auto")
fi

export CHROME_WRAPPER="$(readlink -f "$0")"
export CHROME_DESKTOP="cromite.desktop"

# aarch64 (arm64) sistemde x86_64 ikilisi çalıştırılıyorsa ve box64 mevcutsa otomatik kullan
if [[ "$(uname -m)" == "aarch64" ]] && command -v box64 >/dev/null 2>&1; then
    exec box64 "${CROMITE_DIR}/chrome" "${EXTRA_FLAGS[@]}" "$@"
fi

exec "${CROMITE_DIR}/chrome" "${EXTRA_FLAGS[@]}" "$@"
