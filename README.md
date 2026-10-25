# **Cromite..Copr..CI — Fedora, Enterprise Linux & openSUSE RPM Repository**

This repository (universish/Cromite..Copr..CI) uses the official Linux tarball archive ( `chromelin64.tar.gz` ) published by <u>uazo/cromite to generate RPM packages for universish/Cromite..</u> Fedora COPR repository and automatically generates RPM packages via GitHub Actions. 

Since there are no ready-made `.deb` , `.rpm,` or `.AppImage files` in the upstream source, this build is based directly on the official `chrome-lin64.tar.gz` (e.g., `v153.0.8010.37-11507ac1061b5ea227806f5e84db5a57df6ccf6a/chrome-lin64.tar.gz` ) and converts it into a standards-compliant RPM package. 

### **Supported Distributions and Architectures** 

| Distribution | Version / Branch | COPR Chroot<br>Names (`x86_64`&<br>`aarch64`) |
| :--- | :--- | :--- |
| **Fedora** | 44, 45, Rawhide | `fedora-44-x86_64`, `fedora-45-x86_64`, `fedora-rawhide-x86_64` (and `aarch64`) |
| **openSUSE Tumbleweed** | Rolling | `opensuse-tumbleweed-x86_64`, `opensuse-tumbleweed-aarch64` |
| **openSUSE Leap** | 16.0 | `opensuse-leap-16.0-x86_64`, `opensuse-leap-16.0-aarch64` |
| **AlmaLinux / Alma+EPEL / Kitten** | 9, 10 | Enabled `x86_64`, `x86_64_v2`, `aarch64` targets |
| **CentOS Stream / Stream+EPEL Next** | 8, 9, 10 | Enabled `x86_64`, `aarch64` targets |
| **RHEL / EPEL** | 7, 8, 9, 10 | Enabled targets; EL7 cannot run this upstream binary |

The [compatibility guide](docs/compatibility.md) lists all 47 enabled chroots and separates RPM build targets from runtime support. The official Linux payload is x86-64; ARM64 packages require Box64. The inspected payload requires GLIBC 2.25, so standard EL7 systems cannot install/run it even if an RPM is produced.

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
| `VIRUSTOTAL_API_KEY` | Required VirusTotal checks of the archive and main Cromite ELF |
| `NOTIFY_WEBHOOK_URL` | Optional notification webhook |

The Fedora container in stage 2 runs on the GitHub Actions VM. It verifies the upstream digest when available, inspects shell scripts and ELF metadata, updates ClamAV, and scans the extracted files with `scripts/scan_archive.sh` before creating RPMs and the SRPM from that same archive. A database update failure, scan error, detection, or scan size limit blocks packaging and COPR upload. The scanner allows files up to 2000 MiB so the Chromium executable is not silently skipped by the default size limit.

VirusTotal checks both SHA-256 hashes. Unknown public upstream files within the upload limit are submitted and a completed analysis is required. A missing key, detection, invalid response, API/network error, or analysis timeout blocks packaging. As selected by the user, an unknown file above 650 MiB produces a warning and an `unavailable_size_limit` report entry; packaging may proceed only after the mandatory ClamAV and static checks pass. The file is never labeled clean based on that warning. See the [security policy and target details](docs/compatibility.md). Run the workflow manually with **force_build = true** to rebuild the current upstream version after applying these CI changes.

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

# Cromite..Copr..CI — Fedora, Enterprise Linux & openSUSE RPM Paketleme Deposu

Bu depo ([universish/Cromite..Copr..CI](https://github.com/universish/Cromite..Copr..CI)), [uazo/cromite](https://github.com/uazo/cromite/releases) tarafından yayınlanan resmi Linux tarball arşivini (`chrome-lin64.tar.gz`) kullanarak [universish/Cromite..](https://copr.fedorainfracloud.org/coprs/universish/Cromite../) Fedora COPR deposu ve GitHub Actions üzerinde otomatik RPM paketleri üretir.

Upstream kaynakta hazır `.deb`, `.rpm` veya `.AppImage` bulunmadığından, bu yapı doğrudan resmi `chrome-lin64.tar.gz` (ör. `v153.0.8010.37-11507ac1061b5ea227806f5e84db5a57df6ccf6a/chrome-lin64.tar.gz`) ikili arşivini indirip standartlara uygun bir RPM paketine dönüştürür.

## Desteklenen Dağıtımlar ve Mimariler

| Dağıtım | Sürüm / Dal | COPR Chroot Adları (`x86_64` & `aarch64`) |
| :--- | :--- | :--- |
| **Fedora** | 44, 45, Rawhide | `fedora-44-x86_64`, `fedora-45-x86_64`, `fedora-rawhide-x86_64` (ve `aarch64`) |
| **openSUSE Tumbleweed** | Rolling | `opensuse-tumbleweed-x86_64`, `opensuse-tumbleweed-aarch64` |
| **openSUSE Leap** | 16.0 | `opensuse-leap-16.0-x86_64`, `opensuse-leap-16.0-aarch64` |
| **AlmaLinux / Alma+EPEL / Kitten** | 9, 10 | Etkin `x86_64`, `x86_64_v2`, `aarch64` hedefleri |
| **CentOS Stream / Stream+EPEL Next** | 8, 9, 10 | Etkin `x86_64`, `aarch64` hedefleri |
| **RHEL / EPEL** | 7, 8, 9, 10 | Etkin hedefler; EL7 bu upstream ikilisini çalıştıramaz |

> **Mimari ve çalışma koşulları:** [Uyumluluk kılavuzu](docs/compatibility.md) 47 etkin chroot'u listeler. Linux upstream payload'ı x86-64'tür; ARM64 paketleri Box64 gerektirir ve yerel ARM64 derlemeleri değildir. İncelenen payload GLIBC 2.25 gerektirir; standart EL7 sistemleri, RPM üretilse bile bu paketi kurup çalıştıramaz.

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
| `VIRUSTOTAL_API_KEY` | Arşiv ve ana Cromite ELF dosyasının zorunlu VirusTotal kontrolü |
| `NOTIFY_WEBHOOK_URL` | Yeni `chrome-lin64.tar.gz` sürümü algılandığında bildirim gönderilecek Discord, Slack, Gotify veya JSON Webhook adresi |

İkinci aşamadaki Fedora konteyneri GitHub Actions sanal makinesinde çalışır. Varsa upstream SHA-256 özeti doğrulanır, kabuk betikleri ve ELF metadata denetlenir, ClamAV güncellenir ve çıkarılan dosyalar `scripts/scan_archive.sh` ile taranır. Güvenlik politikası karşılandıktan sonra aynı arşivden RPM ve SRPM oluşturulur. Veritabanı güncelleme hatası, tarama hatası, zararlı tespiti veya tarama boyutu sınırının aşılması paketlemeyi ve COPR'a gönderimi durdurur. Chromium ikilisinin varsayılan boyut sınırında sessizce atlanmaması için dosya sınırı 2000 MiB olarak ayarlanmıştır.

VirusTotal hem arşivin hem ana ikilinin dosya özetini sorgular. Bilinmeyen ve yükleme sınırına uyan herkese açık upstream dosyaları yüklenir ve tamamlanmış analiz beklenir. Anahtar eksikliği, zararlı tespiti, geçersiz yanıt, API/ağ hatası veya analiz zaman aşımı paketlemeyi durdurur. Kullanıcının seçtiği istisna: VirusTotal'de bilinmeyen 650 MiB üzerindeki dosyada uyarı ve `unavailable_size_limit` kaydı oluşturulur; zorunlu ClamAV ve statik kontroller başarılıysa paketleme devam eder. Bu durum “temiz” sonucu olarak sunulmaz. Ayrıntılar [uyumluluk ve güvenlik kılavuzundadır](docs/compatibility.md). Bu değişikliklerden sonra mevcut upstream sürümünü yeniden paketlemek için iş akışını **force_build = true** ile çalıştırın.

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
