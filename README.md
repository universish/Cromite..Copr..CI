# Cromite..Copr..CI — Fedora & openSUSE RPM Paketleme Deposu

Bu depo ([universish/Cromite..Copr..CI](https://github.com/universish/Cromite..Copr..CI)), [uazo/cromite](https://github.com/uazo/cromite/releases) tarafından yayınlanan resmi Linux tarball arşivini (`chrome-lin64.tar.gz`) kullanarak [universish/Cromite..](https://copr.fedorainfracloud.org/coprs/universish/Cromite../) Fedora COPR deposu ve GitHub Actions üzerinde otomatik RPM paketleri üretir.

Upstream kaynakta hazır `.deb`, `.rpm` veya `.AppImage` bulunmadığından, bu yapı doğrudan resmi `chrome-lin64.tar.gz` (ör. `v153.0.8010.37-11507ac1061b5ea227806f5e84db5a57df6ccf6a/chrome-lin64.tar.gz`) ikili arşivini indirip standartlara uygun bir RPM paketine dönüştürür.

## Desteklenen Dağıtımlar ve Mimariler

| Dağıtım | Sürüm / Dal | COPR Chroot Adları (`x86_64` & `aarch64`) |
| :--- | :--- | :--- |
| **Fedora** | 44, 45, Rawhide | `fedora-44-x86_64`, `fedora-45-x86_64`, `fedora-rawhide-x86_64` (ve `aarch64`) |
| **openSUSE Tumbleweed** | Rolling | `opensuse-tumbleweed-x86_64`, `opensuse-tumbleweed-aarch64` |
| **openSUSE Leap** | 16.0 | `opensuse-leap-16.0-x86_64`, `opensuse-leap-16.0-aarch64` |

> **Mimari Notu (`x86_64` ve `arm64`/`aarch64`):** Upstream [uazo/cromite Releases](https://github.com/uazo/cromite/releases) sayfasında Linux için yalnızca `x86_64` mimarili `chrome-lin64.tar.gz` arşivi yayınlanmaktadır (`arm64` derlemeleri upstream'de yalnızca Android `.apk` içindir). `cromite.spec` dosyası hem `x86_64` hem de `aarch64` chroot hedeflerinde derlenebilecek şekilde (`%ifarch aarch64` koşullu bağımlılık filtresi ve `cromite.sh` içinde `box64` sarmalayıcı desteğiyle) yapılandırılmıştır.

## Dizin ve Dosya Yapısı

```text
Cromite..Copr..CI/
├── .copr/
│   └── Makefile                                    # Fedora COPR 'make_srpm' betiği (dnf ve zypper uyumlu)
├── .github/
│   └── workflows/
│       ├── build-rpm.yml                           # Fedora (44, Rawhide) ve openSUSE (Tumbleweed, Leap 16.0) CI derlemesi
│       └── check-update-and-webhook.yml            # 6 saatte bir uazo/cromite/releases kontrolü ve COPR/Webhook tetikleyici
├── scripts/
│   ├── send_webhook.sh                             # universish/Cromite.. COPR webhook ve bildirim gönderici
│   └── update_version.sh                           # chrome-lin64.tar.gz sürümünü denetleyip cromite.spec güncelleyen betik
├── .gitignore                                      # RPM derleme çıktılarını hariç tutan Git kuralları
├── cromite.desktop                                 # Masaüstü başlatıcı dosyası (Türkçe & İngilizce)
├── cromite.sh                                      # Wayland/Ozone, ~/.config/cromite-flags.conf ve arm64 box64 destekli başlatıcı
├── cromite.spec                                    # Fedora (44/45/Rawhide) ve openSUSE (Tumbleweed/Leap 16) uyumlu RPM spec
├── org.cromite.cromite.metainfo.xml                # AppStream uygulama mağazası üstverisi
└── README.md                                       # Kurulum ve yapılandırma kılavuzu
```

## 1. Fedora COPR (`universish/Cromite..`) Yapılandırması

1. [universish/Cromite.. COPR](https://copr.fedorainfracloud.org/coprs/universish/Cromite../) proje sayfasında **Settings -> Edit** sekmesinden aşağıdaki chroot hedeflerini etkinleştirin:
   - `fedora-44-x86_64`, `fedora-44-aarch64`
   - `fedora-45-x86_64`, `fedora-45-aarch64`
   - `fedora-rawhide-x86_64`, `fedora-rawhide-aarch64`
   - `opensuse-tumbleweed-x86_64`, `opensuse-tumbleweed-aarch64`
   - `opensuse-leap-16.0-x86_64`, `opensuse-leap-16.0-aarch64`
2. **Packages -> New Package** (veya mevcut `cromite` paketinde **Edit**) bölümünde şu bilgileri girin:
   - **Package name:** `cromite`
   - **Choose how to build SRPM:** `SCM`
   - **SCM type:** `git`
   - **Clone URL:** `https://github.com/universish/Cromite..Copr..CI.git`
   - **Committish:** `main`
   - **Path to .spec file:** `cromite.spec`
   - **Build SRPM with:** `make_srpm`
   - **Auto-rebuild:** Etkin (`On`)
3. **Settings -> Integrations** sayfasındaki **Custom Webhook URL** bağlantısını (`https://copr.fedorainfracloud.org/webhooks/custom/<id>/<uuid>/cromite/`) kopyalayın.

## 2. GitHub Actions (`universish/Cromite..Copr..CI`) Sırları

[universish/Cromite..Copr..CI](https://github.com/universish/Cromite..Copr..CI) deponuzda **Settings -> Secrets and variables -> Actions** altına şu iki Secret değerini ekleyin:

| Secret Adı | Açıklama |
| :--- | :--- |
| `COPR_WEBHOOK_URL` | [universish/Cromite..](https://copr.fedorainfracloud.org/coprs/universish/Cromite../) **Settings -> Integrations** altındaki özel tetikleme URL'si |
| `NOTIFY_WEBHOOK_URL` | Yeni `chrome-lin64.tar.gz` sürümü algılandığında bildirim gönderilecek Discord, Slack, Gotify veya JSON Webhook adresi |

## 3. Kurulum Komutları

### Fedora (44, 45, Rawhide)
```bash
sudo dnf copr enable universish/Cromite..
sudo dnf install cromite
```

### openSUSE Tumbleweed
```bash
sudo zypper addrepo --refresh https://copr.fedorainfracloud.org/coprs/universish/Cromite../repo/opensuse-tumbleweed/universish-Cromite..-opensuse-tumbleweed.repo
sudo zypper --gpg-auto-import-keys refresh
sudo zypper install cromite
```

### openSUSE Leap 16.0
```bash
sudo zypper addrepo --refresh https://copr.fedorainfracloud.org/coprs/universish/Cromite../repo/opensuse-leap-16.0/universish-Cromite..-opensuse-leap-16.0.repo
sudo zypper --gpg-auto-import-keys refresh
sudo zypper install cromite
```
