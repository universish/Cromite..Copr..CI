# COPR hedefleri ve çalışma koşulları

GitHub Actions, resmi `chrome-lin64.tar.gz` dosyasını indirir ve tarar; aynı dosyadan oluşturulan SRPM'i COPR'a gönderir. `copr-cli build` komutuna `--chroot` sınırlaması verilmediği için COPR projede etkin olan bütün chroot'larda paketleme yapar. Zararlı yazılım taraması ve VirusTotal istekleri yalnızca GitHub Actions sanal makinesinde çalışır.

25 Ekim 2026 tarihinde açık proje API'si ile doğrulanan 47 hedef:

| Dağıtım | Sürüm | Mimariler |
| --- | --- | --- |
| Alma+EPEL | 10 | x86_64_v2 |
| Alma+EPEL | 9 | aarch64, x86_64 |
| Alma Kitten+EPEL | 10 | aarch64, x86_64, x86_64_v2 |
| AlmaLinux | 10 | x86_64_v2 |
| AlmaLinux | 9 | aarch64, x86_64 |
| AlmaLinux Kitten | 10 | aarch64, x86_64, x86_64_v2 |
| CentOS Stream+EPEL Next | 8, 9 | aarch64, x86_64 |
| CentOS Stream | 8, 9, 10 | aarch64, x86_64 |
| EPEL | 7 | x86_64 |
| EPEL | 8, 9, 10 | aarch64, x86_64 |
| Fedora | 44, 45, Rawhide | aarch64, x86_64 |
| openSUSE Leap | 16.0 | aarch64, x86_64 |
| openSUSE Tumbleweed | rolling | aarch64, x86_64 |
| RHEL+EPEL | 10 | aarch64 |
| RHEL | 7 | x86_64 |
| RHEL | 8, 9, 10 | aarch64, x86_64 |

Tam chroot adları [test verisinde](../tests/fixtures/copr_chroots.json) kayıtlıdır. Testler her hedefin mimari ve dağıtım makrolarıyla spec'i ayrıştırır; bu kontrol, gerçek chroot derlemesinin veya tarayıcının o sistemde çalıştırılmasının yerine geçmez.

## Paketleme ve çalışma uyumluluğu

- RPM v4 ve gzip kaynak/ikili payload, eski RPM okuyucularıyla paket biçimi uyumluluğu içindir. SONAME bağımlılıkları Fedora, EL ve openSUSE arasındaki paket adı farklarını giderir; RPM 4.13 öncesinde bulunmayan boolean bağımlılıklar kullanılmaz.
- Resmi Linux payload'ı **x86-64** mimarisindedir. `x86_64_v2` hedefleri aynı upstream ikilisini paketler; yeniden v2 derlemesi yapılmaz.
- **aarch64 paketleri Box64 gerektirir.** Bunlar yerel ARM64 tarayıcı derlemesi değildir. Paket kurulumu için erişilebilir bir `box64` paketi gerekir; Box64 bu depo tarafından sağlanmaz. Gerçek ARM cihazında çalışma ayrıca doğrulanmalıdır.
- İncelenen `v153.0.8010.37-11507ac1061b5ea227806f5e84db5a57df6ccf6a` arşivindeki ana ikili **GLIBC 2.25** ister. GitHub tarama raporundan belirlenen GLIBC alt sınırı her paketlemede spec'e yazılır.
- **Standart EL7 sistemleri GLIBC 2.17 kullandığından bu upstream ikilisini çalıştıramaz.** EL7 için RPM üretilebilmesi, tarayıcının çalıştığı anlamına gelmez. `Requires: glibc >= 2.25` uyumsuz sistemlere kurulumu engeller; EL7 çalışma desteği için ayrı bir uyumlu upstream derlemesi gerekir.
- COPR'da etkin olması, bir dağıtımın eski/EOL chroot depolarının erişilebilir olduğunu garanti etmez. Gerçek chroot sonuçları COPR derleme sayfasından kontrol edilmelidir.

## GitHub güvenlik adımları

1. GitHub sürüm bilgisinde SHA-256 özeti varsa indirilen arşivle eşleştirilir. Paketleme, sürüm kontrolünün seçtiği upstream etiketine sabitlenir.
2. Arşiv güvenli tar filtresiyle çıkarılır. Cromite ana ELF mimarisi, kabuk betiklerindeki şüpheli örüntüler ve ELF RPATH/RUNPATH içindeki yazılabilir konumlar kontrol edilir. Bunlar heuristik kontrollerdir; tek başlarına arka kapı olmadığını kanıtlamaz.
3. ClamAV'ın güncel veritabanıyla tam çıkarılmış içerik taranır. Büyük Chromium ikilisi için dosya/scan sınırı 2000 MiB'dir; sınır aşımı ve tarama hatası yayınlamayı durdurur.
4. `VIRUSTOTAL_API_KEY` zorunludur. Upstream arşivinin ve ana `chrome` ELF dosyasının SHA-256 özetleri sorgulanır. Bilinmeyen ve yükleme sınırına uyan **herkese açık upstream dosyaları** VirusTotal'a yüklenir; tamamlanmış analiz beklenir. Zararlı tespiti, API/ağ hatası, geçersiz yanıt veya analiz zaman aşımı paketlemeyi durdurur.
5. Kullanıcının seçtiği istisna: özeti VirusTotal'de bulunmayan **650 MiB üzerindeki** dosya için uyarı ve `unavailable_size_limit` kaydı oluşturulur. Bu dosya “temiz” sayılmaz; zorunlu ClamAV ve statik kontroller başarılıysa paketleme devam eder. Ana ikili yaklaşık 822 MiB olduğundan bu istisna gerekebilir. Dosya parçalara bölünmez.

`dist/security-report.json` upstream ve ana ikili özetlerini, mimariyi, GLIBC alt sınırını ve VirusTotal durumlarını içerir; GitHub Actions artifact'ına eklenir. COPR'a gönderilen spec tarayıcı çalıştırmaz, VirusTotal anahtarı taşımaz ve tarama için ağ erişimi istemez.

Kaynaklar: [COPR CLI](https://developer.fedoraproject.org/deployment/copr/copr-cli.html), [RPM boolean bağımlılıkları](https://rpm.org/docs/latest/manual/boolean_dependencies), [VirusTotal yükleme sınırları](https://docs.virustotal.com/reference/files-upload-url), [Box64](https://github.com/ptitSeb/box64).
