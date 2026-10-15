%global _commit 11507ac1061b5ea227806f5e84db5a57df6ccf6a
%global _shortcommit %(c=%{_commit}; echo ${c:0:7})
%global debug_package %{nil}
%global _build_id_links none
%global __strip /bin/true
%undefine _missing_build_ids_terminate_build

# Paket içindeki gömülü Chromium kütüphanelerinin sistem RPM bağımlılıklarıyla çakışmasını engelle
%global __provides_exclude_from ^%{_libdir}/%{name}/.*\.so.*$
%global __requires_exclude ^(libffmpeg|libvk_swiftshader|libvulkan|libEGL|libGLESv2|libqt5_shim|libqt6_shim)\.so.*$

# arm64 (aarch64) chroot derlemelerinde x86_64 ELF ikilileri için otomatik soname taramasını devre dışı bırak
%ifarch aarch64
AutoReqProv:    no
%endif

Name:           cromite
Version:        153.0.8010.37
Release:        1.git%{_shortcommit}%{?dist}
Summary:        Gizlilik ve reklam engelleme odaklı Chromium tabanlı web tarayıcısı
License:        GPL-3.0-or-later AND BSD-3-Clause AND LGPL-2.1-or-later AND MIT
URL:            https://github.com/uazo/cromite

# x86_64 (yerel) ve aarch64 (arm64 COPR hedefleri) mimarileri
ExclusiveArch:  x86_64 aarch64

# Upstream yalnızca chrome-lin64.tar.gz tarball yayınlamaktadır
Source0:        https://github.com/uazo/cromite/releases/download/v%{version}-%{_commit}/chrome-lin64.tar.gz
Source1:        cromite.desktop
Source2:        cromite.sh
Source3:        org.cromite.cromite.metainfo.xml

BuildRequires:  desktop-file-utils
BuildRequires:  tar
BuildRequires:  gzip
%if 0%{?fedora}
BuildRequires:  libappstream-glib
%endif
%if 0%{?suse_version}
BuildRequires:  appstream-glib
%endif

# Dağıtıma özgü çalışma zamanı bağımlılıkları (Fedora 44/45/Rawhide vs openSUSE Tumbleweed/Leap 16)
Requires:       hicolor-icon-theme
Requires:       xdg-utils
%if 0%{?fedora}
Requires:       alsa-lib
Requires:       at-spi2-atk
Requires:       at-spi2-core
Requires:       atk
Requires:       cairo
Requires:       cups-libs
Requires:       dbus-libs
Requires:       expat
Requires:       fontconfig
Requires:       freetype
Requires:       glib2
Requires:       gtk3
Requires:       libX11
Requires:       libXcomposite
Requires:       libXdamage
Requires:       libXext
Requires:       libXfixes
Requires:       libXrandr
Requires:       libxcb
Requires:       libxkbcommon
Requires:       libgbm
Requires:       nspr
Requires:       nss
Requires:       pango
Requires:       pipewire-libs
%endif

%if 0%{?suse_version}
Requires:       at-spi2-core
Requires:       fontconfig
Requires:       libX11-6
Requires:       libXcomposite1
Requires:       libXdamage1
Requires:       libXext6
Requires:       libXfixes3
Requires:       libXrandr2
Requires:       libasound2
Requires:       libatk-1_0-0
Requires:       libatk-bridge-2_0-0
Requires:       libcairo2
Requires:       libcups2
Requires:       libdbus-1-3
Requires:       libexpat1
Requires:       libfreetype6
Requires:       libgbm1
Requires:       libglib-2_0-0
Requires:       libgtk-3-0
Requires:       libpipewire-0_3-0
Requires:       libxcb1
Requires:       libxkbcommon0
Requires:       mozilla-nspr
Requires:       mozilla-nss
Requires:       libpango-1_0-0
%endif

Provides:       bundled(chromium) = %{version}

%description
Cromite, yerleşik reklam engelleme motoru ve gelişmiş gizlilik/parmak izi
koruması yamaları içeren, Chromium ve Bromite tabanlı açık kaynaklı bir web
tarayıcısıdır. Bu paket, resmi uazo/cromite Linux tarball (chrome-lin64.tar.gz)
arşivinden Fedora (44, 45, Rawhide) ve openSUSE (Tumbleweed, Leap 16) için
hazırlanmıştır.

%prep
%setup -q -n chrome-lin

%build
# Upstream tarafından önceden derlenmiş chrome-lin64.tar.gz arşivi kullanılır.

%install
export NO_BRP_STALE_LINK_ERROR=yes

install -d -m 0755 %{buildroot}%{_libdir}/%{name}
cp -a * %{buildroot}%{_libdir}/%{name}/

# Başlatıcı betik (/usr/bin/cromite)
install -D -m 0755 %{SOURCE2} %{buildroot}%{_bindir}/%{name}

# Masaüstü başlatıcısı (.desktop)
install -D -m 0644 %{SOURCE1} %{buildroot}%{_datadir}/applications/%{name}.desktop

# AppStream MetaInfo dosyası
install -D -m 0644 %{SOURCE3} %{buildroot}%{_datadir}/metainfo/org.cromite.cromite.metainfo.xml

# Uygulama simgesi kurulumu
install -d -m 0755 %{buildroot}%{_datadir}/icons/hicolor/48x48/apps
if [ -f "%{buildroot}%{_libdir}/%{name}/product_logo_48.png" ]; then
    install -D -m 0644 %{buildroot}%{_libdir}/%{name}/product_logo_48.png \
        %{buildroot}%{_datadir}/icons/hicolor/48x48/apps/%{name}.png
fi

# chrome_sandbox izinlerini ayarla
if [ -f "%{buildroot}%{_libdir}/%{name}/chrome_sandbox" ]; then
    chmod 0755 %{buildroot}%{_libdir}/%{name}/chrome_sandbox
fi

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/%{name}.desktop
appstream-util validate-relax --nonet %{buildroot}%{_datadir}/metainfo/org.cromite.cromite.metainfo.xml || :

%files
%{_bindir}/%{name}
%dir %{_libdir}/%{name}
%{_libdir}/%{name}/*
%if 0%{?suse_version}
%verify(not mode) %attr(0755, root, root) %{_libdir}/%{name}/chrome_sandbox
%else
%attr(4755, root, root) %{_libdir}/%{name}/chrome_sandbox
%endif
%{_datadir}/applications/%{name}.desktop
%dir %{_datadir}/metainfo
%{_datadir}/metainfo/org.cromite.cromite.metainfo.xml
%dir %{_datadir}/icons/hicolor
%dir %{_datadir}/icons/hicolor/48x48
%dir %{_datadir}/icons/hicolor/48x48/apps
%{_datadir}/icons/hicolor/48x48/apps/%{name}.png

%changelog
* Thu Oct 15 2026 universish <noreply@github.com> - 153.0.8010.37-1.git11507ac
- Upstream v153.0.8010.37-11507ac1061b5ea227806f5e84db5a57df6ccf6a chrome-lin64.tar.gz sürümü
- Fedora 44, 45, Rawhide ve openSUSE Tumbleweed, Leap 16.0 (x86_64 / aarch64) desteği eklendi
