# **Cromite..Copr..CI — Fedora & openSUSE RPM Repository** 

This repository (universish/Cromite..Copr..CI) uses the official Linux tarball archive ( `chromelin64.tar.gz` ) published by <u>uazo/cromite to generate RPM packages for universish/Cromite..</u> Fedora COPR repository and automatically generates RPM packages via GitHub Actions. 

Since there are no ready-made `.deb` , `.rpm,` or `.AppImage files` in the upstream source, this build is based directly on the official `chrome-lin64.tar.gz` (e.g., `v153.0.8010.37-11507ac1061b5ea227806f5e84db5a57df6ccf6a/chrome-lin64.tar.gz` ) and converts it into a standards-compliant RPM package. 

### **Supported Distributions and Architectures** 

| Distribution | Version / Branch | COPR Chroot<br>Names (`x86_64`&<br>`aarch64`) |
| :--- | :--- | :--- |
| **Fedora** | 44, 45, Rawhide | `fedora-44-x86_64`, `fedora-45-x86_64`, `fedora-rawhide-x86_64` (and `aarch64`) |
| **openSUSE Tumbleweed** | Rolling | `opensuse-tumbleweed-x86_64`, `opensuse-tumbleweed-aarch64` |
| **openSUSE Leap** | 16.0 | `opensuse-leap-16.0-x86_64`, `opensuse-leap-16.0-aarch64` |



(configured with the `%ifarch aarch64` conditional dependency filter and `cromite.sh` with `box64` wrapper support). 

### **Directory and File Structure** 

```text
Cromite..Copr..CI/
├── .copr/
│   └── Makefile                                    # Makefile# Fedora COPR 'make_srpm' script(compatible withdnf and zypper)
├── .github/
│   └── workflows/
│       └── Cromite_ci.yml                         # Upstream check, GitHub Actions virus scan, RPM build and COPR upload
├── scripts/
│   ├── scan_archive.sh                             # Mandatory ClamAV scan and optional VirusTotal hash lookup in GitHub Actions
│   ├── send_webhook.sh                             # Optional notification sender
│   └── update_version.sh                           # chrome-Git rules that exclude the output of the scriptthat checks the lin64.tar.gz
├── .gitignore                                      # RPM build version and updates cromite.spec
├── cromite.desktop                                 # Desktop startup file (Turkish & English)
├── cromite.sh                                      # Wayland/Ozone, ~/.config/cromite-flags.conf and a launcher supportingarm64 and box64
├── cromite.spec                                    # Fedora (44/45/ (Rawhide) and anopenSUSE (Tumbleweed/Leap 16)-compatible RPM spec
├── org.cromite.cromite.metainfo.xml                # AppStream application storemetadata
└── README.md                                       # Installation and Configuration Guide
```
## **1. Fedora COPR (** **`universish/Cromite..` ) Configuration** 

<u>1.</u> On the <u>universish/Cromite.. COPR project page, go to</u> **Settings -> Edit and** enable the following chroot targets: • `fedora-44-x86_64` , `fedora-44-aarch64 fedora-45-x86_64` , `fedora-45-aarch64` 

- `fedora-rawhide-x86_64` , `fedora-rawhide-aarch64` 

- `opensuse-tumbleweed-x86_64` , `opensuse-tumbleweed-aarch64` 

- `openSUSE-leap-16.0-x86_64` , `openSUSE-leap-16.0-aarch64` 

**2.** GitHub Actions uploads the scanned source RPM directly with `copr-cli build universish/Cromite.. dist/*.src.rpm`. Disable automatic SCM rebuilds and COPR build webhooks for this package: those routes download upstream files outside the GitHub Actions scan gate. COPR only rebuilds and publishes the uploaded SRPM; it does not run ClamAV, FreshClam, or VirusTotal.

## **2. GitHub Actions (** **`universish/Cromite..Copr..CI` ) Secrets**

Under **Settings -> Secrets and variables -> Actions**, configure:

| Secret | Purpose |
| :--- | :--- |
| `COPR_LOGIN`, `COPR_USERNAME`, `COPR_TOKEN` | COPR API credentials for direct SRPM upload |
| `VIRUSTOTAL_API_KEY` | Optional VirusTotal SHA-256 lookup |
| `NOTIFY_WEBHOOK_URL` | Optional notification webhook |

The Fedora container in stage 2 runs on the GitHub Actions VM. It downloads the upstream archive, updates the ClamAV database, and scans the extracted files with `scripts/scan_archive.sh` before creating RPMs and the SRPM from that same archive. A database update failure, scan error, detection, or scan size limit blocks packaging and COPR upload. The scanner allows files up to 2000 MB so the Chromium executable is not silently skipped by the default size limit.

VirusTotal is an optional hash lookup, not a file upload. A missing API key or HTTP 404 is reported and the mandatory ClamAV scan still runs. With a configured key, a detection, invalid response, or API/network error blocks packaging. Run the workflow manually with **force_build = true** to rebuild the current upstream version after applying these CI changes.

## **3. Installation Commands**

### **Fedora (44, 45, Rawhide)**
```bash
sudo dnf copr enable universish/Cromite..
sudo dnf install cromite
```

### **openSUSE Tumbleweed**
```bash
sudo zypper addrepo --refresh https://copr.fedorainfracloud.org/coprs/universish/Cromite../repo/opensuse-tumbleweed/universish-Cromite..-opensuse-tumbleweed.repo
sudo zypper --gpg-auto-import-keys refresh
sudo zypper install cromite
```

### **openSUSE Leap 16.0**
```bash
sudo zypper addrepo --refresh https://copr.fedorainfracloud.org/coprs/universish/Cromite../repo/opensuse-leap-16.0/universish-Cromite..-opensuse-leap-16.0.repo
sudo zypper --gpg-auto-import-keys refresh
sudo zypper install cromite
```

----

TR-tr:

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
│       └── Cromite_ci.yml                         # Sürüm kontrolü, GitHub Actions virüs taraması, RPM ve COPR gönderimi
├── scripts/
│   ├── scan_archive.sh                             # GitHub Actions'ta zorunlu ClamAV ve isteğe bağlı VirusTotal sorgusu
│   ├── send_webhook.sh                             # İsteğe bağlı bildirim gönderici
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
2. GitHub Actions, taranmış kaynak RPM'i doğrudan `copr-cli build universish/Cromite.. dist/*.src.rpm` ile yükler. Bu paket için otomatik SCM derlemelerini ve COPR derleme webhook'larını kapatın; bunlar GitHub Actions tarama adımının dışında upstream arşivini yeniden indirir. COPR yalnızca yüklenen SRPM'i derler ve yayınlar; ClamAV, FreshClam veya VirusTotal çalıştırmaz.

## 2. GitHub Actions (`universish/Cromite..Copr..CI`) Sırları

[universish/Cromite..Copr..CI](https://github.com/universish/Cromite..Copr..CI) deponuzda **Settings -> Secrets and variables -> Actions** altına şu Secret değerlerini ekleyin:

| Secret Adı | Açıklama |
| :--- | :--- |
| `COPR_LOGIN`, `COPR_USERNAME`, `COPR_TOKEN` | SRPM'i doğrudan yüklemek için COPR API kimlik bilgileri |
| `VIRUSTOTAL_API_KEY` | İsteğe bağlı VirusTotal SHA-256 sorgusu |
| `NOTIFY_WEBHOOK_URL` | Yeni `chrome-lin64.tar.gz` sürümü algılandığında bildirim gönderilecek Discord, Slack, Gotify veya JSON Webhook adresi |

İkinci aşamadaki Fedora konteyneri GitHub Actions sanal makinesinde çalışır. Upstream arşivi indirilir, ClamAV veritabanı güncellenir ve çıkarılan dosyalar `scripts/scan_archive.sh` ile taranır. Ancak tarama başarılı olduktan sonra aynı arşivden RPM ve SRPM oluşturulur. Veritabanı güncelleme hatası, tarama hatası, zararlı tespiti veya tarama boyutu sınırının aşılması paketlemeyi ve COPR'a gönderimi durdurur. Chromium ikilisinin varsayılan boyut sınırında sessizce atlanmaması için dosya sınırı 2000 MB olarak ayarlanmıştır.

VirusTotal isteğe bağlı bir dosya özeti sorgusudur; dosya yüklemez. API anahtarı yoksa veya HTTP 404 dönerse bu durum bildirilir ve zorunlu ClamAV taraması yapılır. Anahtar tanımlıyken zararlı tespiti, geçersiz yanıt veya API/ağ hatası paketlemeyi durdurur. Bu CI değişikliklerini uyguladıktan sonra mevcut upstream sürümünü yeniden paketlemek için iş akışını **force_build = true** ile elle çalıştırın.

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
