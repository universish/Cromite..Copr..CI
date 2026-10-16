%global debug_package %{nil}
%global __strip /bin/true
%global __brp_strip %{nil}
%global __brp_strip_comment_note %{nil}
%global __brp_strip_lto %{nil}
%global __brp_strip_static_archive %{nil}
%global __brp_mangle_shebangs %{nil}
%define _build_id_links none

# check-rpaths ve brp kontrollerini devre dışı bırakır (Tauon.spec mimarisi)
%global __os_install_post %{nil}
%global __spec_install_post /usr/lib/rpm/check-buildroot

# Dahili kütüphanelerin sistem RPM bağımlılıklarına sızmasını engeller
%global __provides_exclude_from ^/opt/cromite/.*$
%global __requires_exclude_from ^/opt/cromite/.*$

Name:           cromite
Version:        153.0.8010.37
Release:        3%{?dist}
Summary:        A Bromite fork with ad blocking and privacy enhancements

License:        GPL-3.0-or-later
URL:            https://github.com/uazo/cromite

Source0:        chrome-lin64.tar.gz

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

Requires:       ca-certificates
Requires:       hicolor-icon-theme
Requires:       xdg-utils
Requires:       xdg-user-dirs
Requires:       at-spi2-core
Requires:       fontconfig
Requires:       (p11-kit-trust or mozilla-nss-certs)
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
Requires:       (vulkan-loader or libvulkan1)

Provides:       Cromite = %{version}-%{release}
Provides:       cromite-browser = %{version}-%{release}
Provides:       bundled(chromium) = %{version}

%description
Cromite is an unofficial repackaging of upstream portable Linux releases (chrome-lin64.tar.gz).
A fast and privacy-focused Chromium/Bromite fork featuring built-in ad blocking,
anti-fingerprinting defenses, and hardware-accelerated VA-API video playback.

%prep
%setup -q -c -T
tar -xzf %{SOURCE0} || :

# Arşiv içeriği tek klasöre (chrome-lin/) açıldıysa kök dizine taşı
if [ $(ls -1A | wc -l) -eq 1 ] && [ -d * ]; then
    SUBDIR=$(ls -1A)
    mv "$SUBDIR"/* . 2>/dev/null || true
    mv "$SUBDIR"/.* . 2>/dev/null || true
    rmdir "$SUBDIR" 2>/dev/null || true
fi

%build
# Portable binary; derleme adımı gerekmez.

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

# Uyumsuz gömülü libvulkan.so.1 ikilisini silip sistemin yerel Vulkan kütüphanesine bağla
rm -f %{buildroot}/opt/cromite/libvulkan.so.1
ln -sf %{_libdir}/libvulkan.so.1 %{buildroot}/opt/cromite/libvulkan.so.1

# Ana ikili dosyalara çalıştırma izni ver
for bin in chrome chrome_crashpad_handler chrome-wrapper chrome_sandbox; do
    if [ -f "%{buildroot}/opt/cromite/$bin" ]; then
        chmod +x "%{buildroot}/opt/cromite/$bin"
    fi
done

# /usr/bin/cromite başlatıcı betiği (Saf Wayland ve X11 otomatik algılama + izole ~/.config/cromite profili)
cat << 'EOF' > %{buildroot}%{_bindir}/cromite
#!/usr/bin/env bash
set -euo pipefail

CROMITE_DIR="/opt/cromite"
CROMITE_USER_DATA_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/cromite"
USER_FLAGS_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/cromite-flags.conf"

export CHROME_WRAPPER="$(readlink -f "$0")"
export CHROME_DESKTOP="cromite.desktop"
export LD_LIBRARY_PATH="${CROMITE_DIR}:/usr/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

if [ -d /proc/driver/nvidia ] || [ -e /dev/nvidiactl ]; then
    export NVD_BACKEND="${NVD_BACKEND:-direct}"
    export __NV_PRIME_RENDER_OFFLOAD="${__NV_PRIME_RENDER_OFFLOAD:-1}"
    # Yalnızca X11 oturumunda GLX vendor zorla (saf Wayland'de EGL kullanılır)
    if [ -z "${WAYLAND_DISPLAY:-}" ] && [ -n "${DISPLAY:-}" ]; then
        export __GLX_VENDOR_LIBRARY_NAME="${__GLX_VENDOR_LIBRARY_NAME:-nvidia}"
    fi
fi

declare -a DEFAULT_FLAGS=(
    "--user-data-dir=${CROMITE_USER_DATA_DIR}"
    "--ozone-platform-hint=auto"
    "--disable-features=Vulkan"
    "--enable-features=VaapiVideoDecodeLinuxGL,VaapiVideoEncoderLinuxGL,AcceleratedVideoDecodeLinuxGL,AcceleratedVideoDecodeLinuxZeroCopyGL,AcceleratedVideoEncoder,VaapiIgnoreDriverChecks,CanvasOopRasterization,ParallelDownloading,BackForwardCache"
    "--ignore-gpu-blocklist"
    "--enable-gpu-rasterization"
    "--enable-oop-rasterization"
    "--enable-zero-copy"
    "--no-default-browser-check"
    "--no-first-run"
    "--disable-breakpad"
    "--disable-crash-reporter"
    "--disable-domain-reliability"
    "--disable-pings"
)

if [ -f "$USER_FLAGS_FILE" ]; then
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in
            \#*|"") continue ;;
        esac
        # shellcheck disable=SC2206
        DEFAULT_FLAGS+=($line)
    done < "$USER_FLAGS_FILE"
fi

if [ "$(uname -m)" = "aarch64" ] && command -v box64 >/dev/null 2>&1; then
    exec box64 "${CROMITE_DIR}/chrome" "${DEFAULT_FLAGS[@]}" "$@"
fi

exec "${CROMITE_DIR}/chrome" "${DEFAULT_FLAGS[@]}" "$@"
EOF
chmod 755 %{buildroot}%{_bindir}/cromite

ln -sf cromite %{buildroot}%{_bindir}/cromite-browser

cat << 'EOF' > %{buildroot}%{_datadir}/applications/%{name}.desktop
[Desktop Entry]
Version=1.0
Type=Application
Name=Cromite
GenericName=Web Browser
GenericName[tr]=Web Tarayıcı
Comment=Fast and Private Web Browser
Comment[tr]=İnternet'e gizlilik ve yüksek performansla erişin
Exec=/usr/bin/cromite --ozone-platform-hint=auto --disable-features=Vulkan --enable-features=VaapiVideoDecodeLinuxGL,VaapiVideoEncoderLinuxGL,AcceleratedVideoDecodeLinuxGL,AcceleratedVideoDecodeLinuxZeroCopyGL,AcceleratedVideoEncoder,VaapiIgnoreDriverChecks,CanvasOopRasterization,ParallelDownloading,BackForwardCache --ignore-gpu-blocklist --enable-gpu-rasterization --enable-oop-rasterization --enable-zero-copy --no-default-browser-check --no-first-run --disable-breakpad --disable-crash-reporter --disable-domain-reliability --disable-pings %U
TryExec=/usr/bin/cromite
Icon=cromite
Terminal=false
X-MultipleArgs=false
StartupNotify=true
StartupWMClass=cromite
Categories=Network;WebBrowser;
Keywords=browser;cromite;privacy;chromium;
MimeType=application/pdf;application/rdf+xml;application/rss+xml;application/xhtml+xml;application/xhtml_xml;application/xml;image/gif;image/jpeg;image/png;image/webp;text/html;text/xml;x-scheme-handler/http;x-scheme-handler/https;x-scheme-handler/about;x-scheme-handler/unknown;
Actions=new-window;new-private-window;temp-profile;safe-mode;dark-mode;

[Desktop Action new-window]
Name=New Window
Name[tr]=Yeni Pencere
Icon=cromite
Exec=/usr/bin/cromite --ozone-platform-hint=auto --disable-features=Vulkan --enable-features=VaapiVideoDecodeLinuxGL,VaapiVideoEncoderLinuxGL,AcceleratedVideoDecodeLinuxGL,AcceleratedVideoDecodeLinuxZeroCopyGL,AcceleratedVideoEncoder,VaapiIgnoreDriverChecks,CanvasOopRasterization,ParallelDownloading,BackForwardCache --ignore-gpu-blocklist --enable-gpu-rasterization --enable-oop-rasterization --enable-zero-copy --no-default-browser-check --no-first-run --disable-breakpad --disable-crash-reporter --disable-domain-reliability --disable-pings %U

[Desktop Action new-private-window]
Name=New Incognito Window
Name[tr]=Yeni Gizli Pencere
Icon=cromite
Exec=/usr/bin/cromite --ozone-platform-hint=auto --disable-features=Vulkan --enable-features=VaapiVideoDecodeLinuxGL,VaapiVideoEncoderLinuxGL,AcceleratedVideoDecodeLinuxGL,AcceleratedVideoDecodeLinuxZeroCopyGL,AcceleratedVideoEncoder,VaapiIgnoreDriverChecks,CanvasOopRasterization,ParallelDownloading,BackForwardCache --ignore-gpu-blocklist --enable-gpu-rasterization --enable-oop-rasterization --enable-zero-copy --no-default-browser-check --no-first-run --disable-breakpad --disable-crash-reporter --disable-domain-reliability --disable-pings --incognito %U

[Desktop Action temp-profile]
Name=Open New Window with a temporary profile
Name[tr]=Geçici Profil ile Yeni Pencere Aç
Icon=cromite
Exec=/usr/bin/cromite --ozone-platform-hint=auto --disable-features=Vulkan --enable-features=VaapiVideoDecodeLinuxGL,VaapiVideoEncoderLinuxGL,AcceleratedVideoDecodeLinuxGL,AcceleratedVideoDecodeLinuxZeroCopyGL,AcceleratedVideoEncoder,VaapiIgnoreDriverChecks,CanvasOopRasterization,ParallelDownloading,BackForwardCache --ignore-gpu-blocklist --enable-gpu-rasterization --enable-oop-rasterization --enable-zero-copy --no-default-browser-check --no-first-run --disable-breakpad --disable-crash-reporter --disable-domain-reliability --disable-pings --temp-profile %U

[Desktop Action safe-mode]
Name=Open in Safe Mode
Name[tr]=Güvenli Modda Aç
Icon=cromite
Exec=/usr/bin/cromite --ozone-platform-hint=auto --disable-features=Vulkan --enable-features=VaapiVideoDecodeLinuxGL,VaapiVideoEncoderLinuxGL,AcceleratedVideoDecodeLinuxGL,AcceleratedVideoDecodeLinuxZeroCopyGL,AcceleratedVideoEncoder,VaapiIgnoreDriverChecks,CanvasOopRasterization,ParallelDownloading,BackForwardCache --ignore-gpu-blocklist --enable-gpu-rasterization --enable-oop-rasterization --enable-zero-copy --no-default-browser-check --no-first-run --disable-breakpad --disable-crash-reporter --disable-domain-reliability --disable-pings --disable-extensions --safe-mode %U

[Desktop Action dark-mode]
Name=Open in Dark Mode
Name[tr]=Karanlık Modda Aç
Icon=cromite
Exec=/usr/bin/cromite --ozone-platform-hint=auto --disable-features=Vulkan --enable-features=VaapiVideoDecodeLinuxGL,VaapiVideoEncoderLinuxGL,AcceleratedVideoDecodeLinuxGL,AcceleratedVideoDecodeLinuxZeroCopyGL,AcceleratedVideoEncoder,VaapiIgnoreDriverChecks,CanvasOopRasterization,ParallelDownloading,BackForwardCache --ignore-gpu-blocklist --enable-gpu-rasterization --enable-oop-rasterization --enable-zero-copy --no-default-browser-check --no-first-run --disable-breakpad --disable-crash-reporter --disable-domain-reliability --disable-pings --force-dark-mode %U
EOF

cat << 'EOF' > %{buildroot}%{_datadir}/metainfo/org.cromite.cromite.metainfo.xml
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>org.cromite.cromite</id>
  <metadata_license>CC0-1.0</metadata_license>
  <project_license>GPL-3.0-or-later</project_license>
  <name>Cromite</name>
  <summary>A Bromite fork with ad blocking and privacy enhancements</summary>
  <summary xml:lang="tr">Reklam engelleme ve gizlilik geliştirmelerine sahip Bromite/Chromium çatalı</summary>
  <description>
    <p>
      Cromite is a Chromium fork based on Bromite with built-in support for ad blocking
      and privacy enhancements — take back your browser!
    </p>
    <ul>
      <li>Built-in ad blocking engine with custom filter support (uBlock / Bromite filters).</li>
      <li>Enhanced anti-fingerprinting protections (Canvas, WebGL, AudioContext, Font defenses).</li>
      <li>Telemetry, reporting, and background Google connections stripped out by default.</li>
      <li>Hardened network and security defaults (HTTPS-First, DNS-over-HTTPS, strict site isolation).</li>
      <li>Native Wayland and X11 hardware-accelerated VA-API video playback and Zero-Copy rasterization.</li>
    </ul>
  </description>
  <launchable type="desktop-id">cromite.desktop</launchable>
  <url type="homepage">https://github.com/uazo/cromite</url>
  <url type="bugtracker">https://github.com/universish/Cromite..Copr..CI/issues</url>
  <provides>
    <binary>cromite</binary>
  </provides>
  <categories>
    <category>Network</category>
    <category>WebBrowser</category>
  </categories>
</component>
EOF

find %{buildroot}/opt/cromite -iname "*logo*.png" -exec cp -f {} %{buildroot}%{_datadir}/icons/hicolor/48x48/apps/cromite.png \; 2>/dev/null || true

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
%{_datadir}/icons/hicolor/*/*/*

%changelog
* Thu Oct 15 2026 Saffet Yavuz : universish <universish@tutamail.com> - %{version}-%{release}
- Auto-incrementing release number, native Wayland/X11 auto-detection (--ozone-platform-hint=auto --disable-features=Vulkan), and isolated ~/.config/cromite profile
