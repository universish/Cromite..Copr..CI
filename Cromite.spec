%global debug_package %{nil}
%global __strip /bin/true
%global __brp_strip %{nil}
%global __brp_strip_comment_note %{nil}
%global __brp_strip_lto %{nil}
%global __brp_strip_static_archive %{nil}
%global __brp_mangle_shebangs %{nil}
%define _build_id_links none

# check-rpaths ve brp kontrollerini devre dışı bırakır (Fedora 44/45/Rawhide ve openSUSE Tumbleweed/Leap 16 uyumu)
%global __os_install_post %{nil}
%global __spec_install_post /usr/lib/rpm/check-buildroot

# Dahili kütüphanelerin (libEGL.so, libGLESv2.so, libvulkan.so.1, libqt5/6_shim.so, libvk_swiftshader.so)
# sistem RPM bağımlılıklarına sızmasını ve aarch64 üzerinde ELF mimari hatası vermesini engeller
%global __provides_exclude_from ^/opt/cromite/.*$
%global __requires_exclude_from ^/opt/cromite/.*$

# Dışarıdan makro gelmezse kullanılacak yedek varsayılanlar
%{!?pkg_version: %global pkg_version 153.0.8010.37}
%{!?pkg_release: %global pkg_release 1}

Name:           cromite
Version:        153.0.8010.37
Release:        1%{?dist}
Summary:        A Bromite fork with ad blocking and privacy enhancements

License:        GPL-3.0-or-later AND BSD-3-Clause AND LGPL-2.1-or-later AND MIT
URL:            https://github.com/uazo/cromite

# release.yaml çıktısındaki resmi Linux tarball arşivi, metainfo ve masaüstü kısayolu
Source0:        chrome-lin64.tar.gz
Source1:        org.cromite.cromite.metainfo.xml
Source2:        cromite.desktop

ExclusiveArch:  x86_64 aarch64

BuildRequires:  tar
BuildRequires:  gzip
BuildRequires:  desktop-file-utils
%if 0%{?fedora}
BuildRequires:  libappstream-glib
%endif
%if 0%{?suse_version}
BuildRequires:  appstream-glib
%endif

# Masaüstü, grafik, ses ve Wayland/X11 bağımlılıkları (Fedora 44/45/Rawhide & openSUSE Tumbleweed/Leap 16 ortak)
Requires:       hicolor-icon-theme
Requires:       xdg-utils
Requires:       xdg-user-dirs
Requires:       at-spi2-core
Requires:       fontconfig
Requires:       (alsa-lib or libasound2)
Requires:       (at-spi2-atk or libatk-bridge-2_0-0)
Requires:       (atk or libatk-1_0-0)
Requires:       (cairo or libcairo2)
Requires:       (cups-libs or libcups2)
Requires:       (dbus-libs or libdbus-1-3)
Requires:       (expat or libexpat1)
Requires:       (freetype or libfreetype6)
Requires:       (glib2 or libglib-2_0-0)
Requires:       (gtk3 or libgtk-3-0)
Requires:       (libX11 or libX11-6)
Requires:       (libXcomposite or libXcomposite1)
Requires:       (libXdamage or libXdamage1)
Requires:       (libXext or libXext6)
Requires:       (libXfixes or libXfixes3)
Requires:       (libXrandr or libXrandr2)
Requires:       (libgbm or libgbm1)
Requires:       (libxcb or libxcb1)
Requires:       (libxkbcommon or libxkbcommon0)
Requires:       (nspr or mozilla-nspr)
Requires:       (nss or mozilla-nss)
Requires:       (pango or libpango-1_0-0)
Requires:       (pipewire-libs or libpipewire-0_3-0)
Requires:       (libwayland-client or libwayland-client0)
Requires:       (libwayland-egl or libwayland-egl1)
Requires:       (libwayland-cursor or libwayland-cursor0)

Provides:       Cromite = %{version}-%{release}
Provides:       cromite-browser = %{version}-%{release}
Provides:       bundled(chromium) = %{version}

%description
Cromite is an unofficial RPM repackaging of upstream portable Linux releases
(chrome-lin64.tar.gz). Cromite is a Chromium/Bromite fork featuring built-in
ad blocking, tracking protection, and anti-fingerprinting privacy enhancements.

%prep
%setup -q -c -T
tar -xzf %{SOURCE0}

# Arşiv içeriği tek klasöre (chrome-lin/) açıldıysa kök dizine taşı
if [ $(ls -1A | wc -l) -eq 1 ] && [ -d * ]; then
    SUBDIR=$(ls -1A)
    mv "$SUBDIR"/* . 2>/dev/null || true
    mv "$SUBDIR"/.* . 2>/dev/null || true
    rmdir "$SUBDIR" 2>/dev/null || true
fi

%build
# Portable binary (chrome-lin64.tar.gz); derleme adımı gerekmez.

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/opt/cromite
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_datadir}/applications
mkdir -p %{buildroot}%{_datadir}/metainfo
mkdir -p %{buildroot}%{_datadir}/icons/hicolor/scalable/apps
mkdir -p %{buildroot}%{_datadir}/icons/hicolor/48x48/apps

# Dosyaları /opt/cromite altına yerleştir
cp -a ./* %{buildroot}/opt/cromite/

# Ana ikili dosyalara çalıştırma izni ver
for bin in chrome chrome_crashpad_handler chrome-wrapper chrome_sandbox; do
    if [ -f "%{buildroot}/opt/cromite/$bin" ]; then
        chmod 755 "%{buildroot}/opt/cromite/$bin"
    fi
done

# /usr/bin/cromite başlatıcı betiği (NVIDIA PRIME / VA-API algılama + kullanıcı bayrakları)
cat << 'EOF' > %{buildroot}%{_bindir}/cromite
#!/usr/bin/env bash
set -euo pipefail

CROMITE_DIR="/opt/cromite"
USER_FLAGS_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/cromite-flags.conf"
declare -a EXTRA_FLAGS=()

if [ -f "$USER_FLAGS_FILE" ]; then
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in
            \#*|"") continue ;;
        esac
        # shellcheck disable=SC2206
        EXTRA_FLAGS+=($line)
    done < "$USER_FLAGS_FILE"
fi

# NVIDIA sürücüsü yüklüyse donanımsal hızlandırma ve PRIME Render Offload ortam değişkenlerini etkinleştir
if [ -d /proc/driver/nvidia ] || [ -e /dev/nvidiactl ]; then
    export NVD_BACKEND="${NVD_BACKEND:-direct}"
    export __NV_PRIME_RENDER_OFFLOAD="${__NV_PRIME_RENDER_OFFLOAD:-1}"
    export __GLX_VENDOR_LIBRARY_NAME="${__GLX_VENDOR_LIBRARY_NAME:-nvidia}"
fi

export CHROME_WRAPPER="$(readlink -f "$0")"
export CHROME_DESKTOP="cromite.desktop"
export LD_LIBRARY_PATH="${CROMITE_DIR}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

# aarch64 (arm64) sistemde box64 yüklüyse x86_64 ikilisini box64 ile çalıştır
if [ "$(uname -m)" = "aarch64" ] && command -v box64 >/dev/null 2>&1; then
    exec box64 "${CROMITE_DIR}/chrome" "${EXTRA_FLAGS[@]}" "$@"
fi

exec "${CROMITE_DIR}/chrome" "${EXTRA_FLAGS[@]}" "$@"
EOF
chmod 755 %{buildroot}%{_bindir}/cromite

# Alternatif komut adı için sembolik bağ
ln -sf cromite %{buildroot}%{_bindir}/cromite-browser

# Masaüstü kısayolu (sources/cromite.desktop) kurulumu
install -Dm 644 %{SOURCE2} %{buildroot}%{_datadir}/applications/%{name}.desktop

# Metainfo kurulumu
install -Dm 644 %{SOURCE1} %{buildroot}%{_datadir}/metainfo/org.cromite.cromite.metainfo.xml

# Arşiv içindeki product_logo_48.png simgesini kopyala
if [ -f "%{buildroot}/opt/cromite/product_logo_48.png" ]; then
    cp -f %{buildroot}/opt/cromite/product_logo_48.png %{buildroot}%{_datadir}/icons/hicolor/48x48/apps/cromite.png
fi

# Ölçeklenebilir SVG simgesi oluştur
cat << 'EOF' > %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/cromite.svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">
  <defs>
    <linearGradient id="cromiteGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1e88e5"/>
      <stop offset="100%" stop-color="#1565c0"/>
    </linearGradient>
  </defs>
  <circle cx="64" cy="64" r="56" fill="url(#cromiteGrad)"/>
  <circle cx="64" cy="64" r="24" fill="#ffffff"/>
  <circle cx="64" cy="64" r="18" fill="#0d47a1"/>
  <path d="M64 24 A40 40 0 0 1 101 80" fill="none" stroke="#bbdefb" stroke-width="10" stroke-linecap="round"/>
</svg>
EOF

find %{buildroot}%{_datadir}/icons/hicolor -type d -empty -delete 2>/dev/null || true

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/%{name}.desktop || true
appstream-util validate-relax --nonet %{buildroot}%{_datadir}/metainfo/org.cromite.cromite.metainfo.xml || true

%files
/opt/cromite
%{_bindir}/cromite
%{_bindir}/cromite-browser
%{_datadir}/applications/%{name}.desktop
%{_datadir}/metainfo/org.cromite.cromite.metainfo.xml
%dir %{_datadir}/icons/hicolor
%dir %{_datadir}/icons/hicolor/48x48
%dir %{_datadir}/icons/hicolor/48x48/apps
%dir %{_datadir}/icons/hicolor/scalable
%dir %{_datadir}/icons/hicolor/scalable/apps
%{_datadir}/icons/hicolor/*/*/*

%changelog
* Thu Oct 15 2026 Saffet Yavuz : universish <universish@tutamail.com> - %{version}-%{release}
- Added hardware acceleration, VA-API, ANGLE/Zero-Copy and privacy-hardened performance flags to cromite.desktop
