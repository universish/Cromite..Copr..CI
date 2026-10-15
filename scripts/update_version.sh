#!/usr/bin/env bash
# https://github.com/uazo/cromite/releases sayfasındaki son sürümü ve
# chrome-lin64.tar.gz arşivini kontrol ederek cromite.spec dosyasını günceller.
set -euo pipefail

SPEC_FILE="${1:-cromite.spec}"
UPSTREAM_REPO="uazo/cromite"
TARBALL_NAME="chrome-lin64.tar.gz"

echo "🔍 Upstream https://github.com/${UPSTREAM_REPO}/releases kontrol ediliyor..."

CURL_ARGS=(-fsSL -H "Accept: application/vnd.github+json")
if [[ -n "${GH_TOKEN:-}" ]]; then
    CURL_ARGS+=(-H "Authorization: Bearer ${GH_TOKEN}")
fi

# Tüm sürümler içinden içerisinde chrome-lin64.tar.gz bulunan en güncel sürümü seç
RELEASES_JSON="$(curl "${CURL_ARGS[@]}" "https://api.github.com/repos/${UPSTREAM_REPO}/releases?per_page=10")"

RELEASE_DATA="$(echo "${RELEASES_JSON}" | jq -r --arg tarball "${TARBALL_NAME}" '
  [ .[] | select(.draft == false) | select(any(.assets[]; .name == $tarball)) ][0]
')"

if [[ -z "${RELEASE_DATA}" || "${RELEASE_DATA}" == "null" ]]; then
    echo "❌ https://github.com/${UPSTREAM_REPO}/releases üzerinde ${TARBALL_NAME} içeren sürüm bulunamadı!" >&2
    exit 1
fi

TAG_NAME="$(echo "${RELEASE_DATA}" | jq -r '.tag_name')"
ASSET_URL="$(echo "${RELEASE_DATA}" | jq -r --arg tarball "${TARBALL_NAME}" '.assets[] | select(.name == $tarball) | .browser_download_url')"
ASSET_DIGEST="$(echo "${RELEASE_DATA}" | jq -r --arg tarball "${TARBALL_NAME}" '.assets[] | select(.name == $tarball) | .digest // empty')"

# Tag formatı: v153.0.8010.37-11507ac1061b5ea227806f5e84db5a57df6ccf6a
CLEAN_TAG="${TAG_NAME#v}"
NEW_VERSION="${CLEAN_TAG%%-*}"
NEW_COMMIT="${CLEAN_TAG#*-}"
SHORT_COMMIT="${NEW_COMMIT:0:7}"

CURRENT_VERSION="$(awk '/^Version:/ {print $2}' "${SPEC_FILE}")"
CURRENT_COMMIT="$(awk '/^%global _commit/ {print $3}' "${SPEC_FILE}")"

echo "📌 Mevcut Sürüm  : ${CURRENT_VERSION} (${CURRENT_COMMIT:0:7})"
echo "🚀 Upstream Sürüm: ${NEW_VERSION} (${SHORT_COMMIT})"
echo "📦 Tarball URL   : ${ASSET_URL}"

if [[ "${NEW_VERSION}" == "${CURRENT_VERSION}" && "${NEW_COMMIT}" == "${CURRENT_COMMIT}" ]]; then
    echo "✅ ${SPEC_FILE} zaten güncel (${TAG_NAME})."
    if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
        {
            echo "updated=false"
            echo "version=${CURRENT_VERSION}"
            echo "commit=${CURRENT_COMMIT}"
            echo "short_commit=${CURRENT_COMMIT:0:7}"
            echo "tag=${TAG_NAME}"
            echo "asset_url=${ASSET_URL}"
        } >> "${GITHUB_OUTPUT}"
    fi
    exit 0
fi

# cromite.spec dosyasını yeni sürüm ve commit ile güncelle
sed -i "s/^Version:[[:space:]]*.*/Version:        ${NEW_VERSION}/" "${SPEC_FILE}"
sed -i "s/^%global _commit .*/%global _commit ${NEW_COMMIT}/" "${SPEC_FILE}"
sed -i "s/^Release:[[:space:]]*.*/Release:        1.git%{_shortcommit}%{?dist}/" "${SPEC_FILE}"

CHANGELOG_DATE="$(LC_ALL=C date '+%a %b %d %Y')"
CHANGELOG_ENTRY="* ${CHANGELOG_DATE} universish <noreply@github.com> - ${NEW_VERSION}-1.git${SHORT_COMMIT}\n- Upstream ${TAG_NAME} (${TARBALL_NAME}) sürümüne güncellendi\n- Kaynak: ${ASSET_URL}"
if [[ -n "${ASSET_DIGEST}" ]]; then
    CHANGELOG_ENTRY="${CHANGELOG_ENTRY}\n- Digest: ${ASSET_DIGEST}"
fi

sed -i "/^%changelog/a ${CHANGELOG_ENTRY}\n" "${SPEC_FILE}"

echo "✅ ${SPEC_FILE} dosyası ${NEW_VERSION} (${SHORT_COMMIT}) sürümüne güncellendi."

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    {
        echo "updated=true"
        echo "version=${NEW_VERSION}"
        echo "commit=${NEW_COMMIT}"
        echo "short_commit=${SHORT_COMMIT}"
        echo "tag=${TAG_NAME}"
        echo "asset_url=${ASSET_URL}"
    } >> "${GITHUB_OUTPUT}"
fi
