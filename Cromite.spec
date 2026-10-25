%global debug_package %{nil}
%global __strip /bin/true
%global __brp_strip %{nil}
%global __brp_strip_comment_note %{nil}
%global __brp_strip_lto %{nil}
%global __brp_strip_static_archive %{nil}
%global __brp_mangle_shebangs %{nil}
%global _commit 11507ac1061b5ea227806f5e84db5a57df6ccf6a
%global _min_glibc 2.25
# EL7 dahil eski RPM okuyucuları için RPM v4 ve gzip payload kullan.
%global _rpmformat 4
%global _source_payload w9.gzdio
%global _binary_payload w9.gzdio
%define _build_id_links none

# check-rpaths ve brp kontrollerini devre dışı bırakır (Tauon.spec mimarisi)
%global __os_install_post %{nil}
%global __spec_install_post /usr/lib/rpm/check-buildroot

# Dahili kütüphanelerin sistem RPM bağımlılıklarına sızmasını engeller
%global __provides_exclude_from ^/opt/cromite/.*$
%global __requires_exclude_from ^/opt/cromite/.*$

Name:           cromite
Version:        153.0.8010.37
Release:        6%{?dist}
Summary:        A Bromite fork with ad blocking and privacy enhancements

License:        GPL-3.0-or-later
URL:            https://github.com/uazo/cromite

Source0:        https://github.com/uazo/cromite/releases/download/v%{version}-%{_commit}/chrome-lin64.tar.gz
Source1:        https://raw.githubusercontent.com/universish/Cromite..Copr..CI/main/assets/cromite-icon.png

ExclusiveArch:  x86_64 x86_64_v2 aarch64

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
Requires:       bash
Requires:       glibc >= %{_min_glibc}
# SONAME yetenekleri Fedora, EL ve openSUSE paket adlarından bağımsızdır.
# Parantezli "pkgA or pkgB" ifadeleri RPM 4.11 / EL7 tarafından okunamaz.
Requires:       libasound.so.2()(64bit)
Requires:       libatk-1.0.so.0()(64bit)
Requires:       libatk-bridge-2.0.so.0()(64bit)
Requires:       libatspi.so.0()(64bit)
Requires:       libcairo.so.2()(64bit)
Requires:       libcups.so.2()(64bit)
Requires:       libdbus-1.so.3()(64bit)
Requires:       libexpat.so.1()(64bit)
Requires:       libfreetype.so.6()(64bit)
Requires:       libgcc_s.so.1()(64bit)
Requires:       libgio-2.0.so.0()(64bit)
Requires:       libglib-2.0.so.0()(64bit)
Requires:       libgobject-2.0.so.0()(64bit)
Requires:       libgtk-3.so.0()(64bit)
Requires:       libnspr4.so()(64bit)
Requires:       libnss3.so()(64bit)
Requires:       libnssutil3.so()(64bit)
Requires:       libpango-1.0.so.0()(64bit)
Requires:       libsmime3.so()(64bit)
Requires:       libudev.so.1()(64bit)
Requires:       libX11.so.6()(64bit)
Requires:       libXcomposite.so.1()(64bit)
Requires:       libXdamage.so.1()(64bit)
Requires:       libXext.so.6()(64bit)
Requires:       libXfixes.so.3()(64bit)
Requires:       libXrandr.so.2()(64bit)
Requires:       libgbm.so.1()(64bit)
Requires:       libxcb.so.1()(64bit)
Requires:       libxkbcommon.so.0()(64bit)
Requires:       libvulkan.so.1()(64bit)

%ifarch aarch64
# Upstream Linux arşivi x86-64'tür; ARM üzerinde yerel derleme değildir.
Requires:       box64
%endif

Provides:       Cromite = %{version}-%{release}
Provides:       cromite-browser = %{version}-%{release}
Provides:       bundled(chromium) = %{version}

%description
Cromite is an unofficial repackaging of upstream portable Linux releases (chrome-lin64.tar.gz).
A fast and privacy-focused Chromium/Bromite fork featuring built-in ad blocking,
anti-fingerprinting defenses, and hardware-accelerated VA-API video playback.

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
# Upstream ikili arşivi GitHub Actions üzerinde, SRPM oluşturulmadan önce taranır.
# RPM derleme aşamasında tarayıcı çalıştırılmaz ve ağ erişimi gerekmez.

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/opt/cromite
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_datadir}/applications
mkdir -p %{buildroot}%{_datadir}/metainfo

# Yeni eklediğiniz 1024x1024 kaliteli ikonu sisteme tek ve ana ikon olarak yüklüyoruz
install -Dm644 %{SOURCE1} %{buildroot}%{_datadir}/pixmaps/cromite.png

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
    "--log-level=3"
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

if [ "$(uname -m)" = "aarch64" ]; then
    if ! command -v box64 >/dev/null 2>&1; then
        echo "Cromite x86-64 ikilisini ARM64 üzerinde çalıştırmak için box64 gereklidir." >&2
        exit 1
    fi
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
Exec=/usr/bin/cromite --ozone-platform-hint=auto --disable-features=Vulkan --enable-features=VaapiVideoDecodeLinuxGL,VaapiVideoEncoderLinuxGL,AcceleratedVideoDecodeLinuxGL,AcceleratedVideoDecodeLinuxZeroCopyGL,AcceleratedVideoEncoder,VaapiIgnoreDriverChecks,CanvasOopRasterization,ParallelDownloading,BackForwardCache --ignore-gpu-blocklist --enable-gpu-rasterization --enable-oop-rasterization --enable-zero-copy --no-default-browser-check --no-first-run --disable-breakpad --disable-crash-reporter --disable-domain-reliability --disable-pings --log-level=3 %U
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
Exec=/usr/bin/cromite --ozone-platform-hint=auto --disable-features=Vulkan --enable-features=VaapiVideoDecodeLinuxGL,VaapiVideoEncoderLinuxGL,AcceleratedVideoDecodeLinuxGL,AcceleratedVideoDecodeLinuxZeroCopyGL,AcceleratedVideoEncoder,VaapiIgnoreDriverChecks,CanvasOopRasterization,ParallelDownloading,BackForwardCache --ignore-gpu-blocklist --enable-gpu-rasterization --enable-oop-rasterization --enable-zero-copy --no-default-browser-check --no-first-run --disable-breakpad --disable-crash-reporter --disable-domain-reliability --disable-pings --log-level=3 %U

[Desktop Action new-private-window]
Name=New Incognito Window
Name[tr]=Yeni Gizli Pencere
Icon=cromite
Exec=/usr/bin/cromite --ozone-platform-hint=auto --disable-features=Vulkan --enable-features=VaapiVideoDecodeLinuxGL,VaapiVideoEncoderLinuxGL,AcceleratedVideoDecodeLinuxGL,AcceleratedVideoDecodeLinuxZeroCopyGL,AcceleratedVideoEncoder,VaapiIgnoreDriverChecks,CanvasOopRasterization,ParallelDownloading,BackForwardCache --ignore-gpu-blocklist --enable-gpu-rasterization --enable-oop-rasterization --enable-zero-copy --no-default-browser-check --no-first-run --disable-breakpad --disable-crash-reporter --disable-domain-reliability --disable-pings --log-level=3 --incognito %U

[Desktop Action temp-profile]
Name=Open New Window with a temporary profile
Name[tr]=Geçici Profil ile Yeni Pencere Aç
Icon=cromite
Exec=/usr/bin/cromite --ozone-platform-hint=auto --disable-features=Vulkan --enable-features=VaapiVideoDecodeLinuxGL,VaapiVideoEncoderLinuxGL,AcceleratedVideoDecodeLinuxGL,AcceleratedVideoDecodeLinuxZeroCopyGL,AcceleratedVideoEncoder,VaapiIgnoreDriverChecks,CanvasOopRasterization,ParallelDownloading,BackForwardCache --ignore-gpu-blocklist --enable-gpu-rasterization --enable-oop-rasterization --enable-zero-copy --no-default-browser-check --no-first-run --disable-breakpad --disable-crash-reporter --disable-domain-reliability --disable-pings --log-level=3 --temp-profile %U

[Desktop Action safe-mode]
Name=Open in Safe Mode
Name[tr]=Güvenli Modda Aç
Icon=cromite
Exec=/usr/bin/cromite --ozone-platform-hint=auto --disable-features=Vulkan --enable-features=VaapiVideoDecodeLinuxGL,VaapiVideoEncoderLinuxGL,AcceleratedVideoDecodeLinuxGL,AcceleratedVideoDecodeLinuxZeroCopyGL,AcceleratedVideoEncoder,VaapiIgnoreDriverChecks,CanvasOopRasterization,ParallelDownloading,BackForwardCache --ignore-gpu-blocklist --enable-gpu-rasterization --enable-oop-rasterization --enable-zero-copy --no-default-browser-check --no-first-run --disable-breakpad --disable-crash-reporter --disable-domain-reliability --disable-pings --log-level=3 --disable-extensions --safe-mode %U

[Desktop Action dark-mode]
Name=Open in Dark Mode
Name[tr]=Karanlık Modda Aç
Icon=cromite
Exec=/usr/bin/cromite --ozone-platform-hint=auto --disable-features=Vulkan --enable-features=VaapiVideoDecodeLinuxGL,VaapiVideoEncoderLinuxGL,AcceleratedVideoDecodeLinuxGL,AcceleratedVideoDecodeLinuxZeroCopyGL,AcceleratedVideoEncoder,VaapiIgnoreDriverChecks,CanvasOopRasterization,ParallelDownloading,BackForwardCache --ignore-gpu-blocklist --enable-gpu-rasterization --enable-oop-rasterization --enable-zero-copy --no-default-browser-check --no-first-run --disable-breakpad --disable-crash-reporter --disable-domain-reliability --disable-pings --log-level=3 --force-dark-mode %U
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

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/%{name}.desktop || true
appstream-util validate-relax --nonet %{buildroot}%{_datadir}/metainfo/org.cromite.cromite.metainfo.xml || true

%files
/opt/cromite
%{_bindir}/cromite
%{_bindir}/cromite-browser
%{_datadir}/applications/%{name}.desktop
%{_datadir}/metainfo/org.cromite.cromite.metainfo.xml
%{_datadir}/pixmaps/cromite.png

%changelog
* Sun Oct 25 2026 Saffet Yavuz : universish <universish@tutamail.com> - 153.0.8010.37-6
- EL, AlmaLinux ve x86_64_v2 hedefleri için RPM v4/gzip ve taşınabilir SONAME bağımlılıkları
- GLIBC alt sınırını ve ARM64 için Box64 gereksinimini açıkça belirt

* Sun Oct 25 2026 Saffet Yavuz : universish <universish@tutamail.com> - 153.0.8010.37-1
- Upstream v153.0.8010.37-11507ac1061b5ea227806f5e84db5a57df6ccf6a (chrome-lin64.tar.gz) sürümüne güncellendi
- Digest: sha256:6fe67a4a75a3a5013cc470a3061606c44dc148531c42d8c56317ef0c7f8340cf

* Sun Oct 25 2026 Saffet Yavuz : universish <universish@tutamail.com> - 153.0.8010.37-5
- Virüs taramalarını GitHub Actions'a taşı; COPR derlemelerinden ClamAV ve VirusTotal bağımlılıklarını kaldır

* Sun Oct 25 2026 Saffet Yavuz : universish <universish@tutamail.com> - 153.0.8010.37-1
- Upstream v153.0.8010.37-11507ac1061b5ea227806f5e84db5a57df6ccf6a (chrome-lin64.tar.gz) sürümüne güncellendi
- Digest: sha256:6fe67a4a75a3a5013cc470a3061606c44dc148531c42d8c56317ef0c7f8340cf

* Sun Oct 25 2026 Saffet Yavuz : universish <universish@tutamail.com> - 153.0.8010.37-1
- Upstream v153.0.8010.37-11507ac1061b5ea227806f5e84db5a57df6ccf6a (chrome-lin64.tar.gz) sürümüne güncellendi
- Digest: sha256:6fe67a4a75a3a5013cc470a3061606c44dc148531c42d8c56317ef0c7f8340cf

* Sun Oct 25 2026 Saffet Yavuz : universish <universish@tutamail.com> - 153.0.8010.37-1
- Upstream v153.0.8010.37-11507ac1061b5ea227806f5e84db5a57df6ccf6a (chrome-lin64.tar.gz) sürümüne güncellendi
- Digest: sha256:6fe67a4a75a3a5013cc470a3061606c44dc148531c42d8c56317ef0c7f8340cf

* Sun Oct 25 2026 Saffet Yavuz : universish <universish@tutamail.com> - 153.0.8010.37-1
- Upstream v153.0.8010.37-11507ac1061b5ea227806f5e84db5a57df6ccf6a (chrome-lin64.tar.gz) sürümüne güncellendi
- Digest: sha256:6fe67a4a75a3a5013cc470a3061606c44dc148531c42d8c56317ef0c7f8340cf

* Sun Oct 25 2026 Saffet Yavuz : universish <universish@tutamail.com> - 153.0.8010.37-1
- Upstream v153.0.8010.37-11507ac1061b5ea227806f5e84db5a57df6ccf6a (chrome-lin64.tar.gz) sürümüne güncellendi
- Digest: sha256:6fe67a4a75a3a5013cc470a3061606c44dc148531c42d8c56317ef0c7f8340cf

* Sun Oct 25 2026 Saffet Yavuz : universish <universish@tutamail.com> - 153.0.8010.37-1
- Upstream v153.0.8010.37-11507ac1061b5ea227806f5e84db5a57df6ccf6a (chrome-lin64.tar.gz) sürümüne güncellendi
- Digest: sha256:6fe67a4a75a3a5013cc470a3061606c44dc148531c42d8c56317ef0c7f8340cf

* Thu Oct 15 2026 Saffet Yavuz : universish <universish@tutamail.com> - %{version}-%{release}
- Auto-incrementing release number, native Wayland/X11 auto-detection (--ozone-platform-hint=auto --disable-features=Vulkan), and isolated ~/.config/cromite profile
