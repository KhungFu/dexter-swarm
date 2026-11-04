# Hyperstead

🌐 Diller: [Deutsch](README.md) · [English](README.en.md) · **Türkçe** · [Srpski](README.sr.md) · [Bosanski](README.bs.md) · [Hrvatski](README.hr.md)

Düğüm editörü olarak bir yapay zekâ ajan ekibi; kendi sunucunuzda çalışır ve Raspberry Pi için yeterince hafiftir.
Proje oluşturun, ajanları sürükleyip alana bırakın, bağlayın (patron → çalışan), her düğüm için yapay zekâ sağlayıcısını, çalışma talimatını ve yetkileri ayarlayın ve görev atayın.

> `docs/` klasöründeki ayrıntılı kılavuzlar şu an yalnızca Almanca yazılmıştır. Uygulamadaki düğme ve menü adları Almanca olarak kalır.

## Kurulum

Hyperstead bir Python programıdır (Flask + SQLite) ve birçok sistemde çalışır. Birden çok kurulum
paralel çalışabilir; her birinin kendi şirketleri ve verileri vardır.

| Sistem | Durum | Kılavuz |
| --- | --- | --- |
| Raspberry Pi / Linux (Debian, Ubuntu) | ana sistem, tam özellik kapsamı | aşağıda |
| Windows 10/11 | çalışır, `run_code` olmadan, Rust derleme yalnızca bir anahtarla yalıtımsız, bazı özellikler ek programlar gerektirir | [docs/windows.md](docs/windows.md) |
| macOS | test edilmedi, temel işlevler çalışmalı | aşağıda (elle) |
| Kendi görüntü bilgisayarı (ör. ekran kartı olmayan eski bir dizüstü) | referans görselleriyle ücretsiz görseller | [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md) |

Bir bilgisayardan diğerine taşıma: Hyperstead'i durdurun ve `data.db`, `workspace/` klasörünü ve `.env` dosyasını kopyalayın
([Pi → Windows örneği](docs/windows.md)).

### Raspberry Pi / Linux

```bash
git clone https://github.com/KhungFu/hyperstead && cd hyperstead
./install.sh --service     # venv, bağımlılıklar, rastgele şifreli .env, systemd hizmeti
nano .env                  # API anahtarlarını girin, ardından: sudo systemctl restart hyperstead
```

Hizmet olmadan: `./install.sh` ve sonra `./venv/bin/python app.py` → http://127.0.0.1:8787.
Giriş şifresi `.env` içindedir (`APP_TOKEN`). Güncelleme, yeniden başlatma, yedekleme: [İşletim](#işletim-kim-neyi-nerede-ne-zaman-nasıl-yapar).
Daha fazla özellik (video, OCR, derleyiciler, tarayıcı): `./install.sh --all`.

### Windows

Hyperstead klasöründe PowerShell:

```powershell
git clone https://github.com/KhungFu/hyperstead; cd hyperstead
powershell -ExecutionPolicy Bypass -File install.ps1
notepad .env
deploy\windows\hyperstead-start.bat
```

Windows'ta eksik olanlar, otomatik başlatma ve Pi ile paralel çalışma: [docs/windows.md](docs/windows.md).
Sonradan güncelleme: `git pull`, ardından yeniden başlatın.

### macOS (test edilmedi)

```bash
git clone https://github.com/KhungFu/hyperstead && cd hyperstead
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
cp .env.example .env       # APP_TOKEN=<uzun şifre> girin, API anahtarlarını ekleyin
./venv/bin/python app.py   # http://127.0.0.1:8787
```

`install.sh` Debian/Ubuntu için yapılmıştır (apt), bu yüzden macOS'ta yukarıdaki gibi elle kurun. Ek programlar Homebrew ile
(`brew install ffmpeg tesseract poppler`). `run_code` yalnızca Linux'ta vardır.

### Kendi bilgisayarınızda görseller

Ev ağındaki bir bilgisayar (ekran kartı olmasa bile en az 8 GB RAM ile) Hyperstead için referans görselleriyle
ücretsiz görseller üretebilir. `.env` dosyasında tam olarak bu iki satırı etkin bırakın (`#` olmadan yalnızca bir `IMAGE_PROVIDER=` satırı):

```
IMAGE_PROVIDER=sdcpp
SDCPP_URL=http://<görsel bilgisayarının IP'si>:1234    # görsel bilgisayarının kendisinde: http://127.0.0.1:1234
```

Kurulum: [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md).

### Blender ile animasyon filmleri

Hyperstead'in çalıştığı bilgisayarda Blender kuruluysa, ajanlar çizgi film çeker: kendi sesi ve ağız hareketi olan karakterler,
sahneler, kamera, altyazı, sesli bitmiş film (`film` aracı, „🐶 Animationsstudio“ şirket şablonu).
Hyperstead Blender'ı kendisi bulamazsa `.env` dosyasına ekleyin:

```
BLENDER_PATH=C:\Program Files\Blender Foundation\Blender 4.2\blender.exe
```

Kılavuz ve senaryo biçimi (Almanca): [docs/filmstudio.md](docs/filmstudio.md).

## İşletim: kim neyi, nerede, ne zaman, nasıl yapar

**Kim:** Bunların hepsini bilgisayarın sahibi (siz) yapar, ajanlar değil. Komutlar Hyperstead klasöründe çalışır: Pi'de terminalde (`cd ~/hyperstead`), Windows'ta PowerShell'de
(`cd $HOME\hyperstead`, ya da klasörü nereye koyduysanız orada).

### Kısa genel bakış

| Ne | Ne zaman | Raspberry Pi / Linux (hizmetle) | Windows |
| --- | --- | --- | --- |
| Başlatma | kurulumdan sonra, otomatik başlatma olmadan yeniden başlatmadan sonra | `sudo systemctl start hyperstead` | `deploy\windows\hyperstead-start.bat` dosyasına çift tıklayın (pencereyi açık bırakın) |
| Durdurma | taşımadan, yedeklemeden, güncellemeden önce | `sudo systemctl stop hyperstead` | başlatma penceresini kapatın (ya da içinde Ctrl+C) |
| Yeniden başlatma | `.env` her değiştiğinde, güncellemeden sonra | `sudo systemctl restart hyperstead` | başlatma penceresini kapatın, `hyperstead-start.bat` dosyasını yeniden çalıştırın |
| Çalışıyor mu? | sorun olduğunda | `systemctl status hyperstead` | başlatma penceresi açık mı? Tarayıcı: <http://127.0.0.1:8787> |
| Günlüğe bakma | hatalarda | `journalctl -u hyperstead -f` (Ctrl+C ile çıkılır) | başlatma penceresinde görünür |
| Güncelleme | yeni bir sürüm olduğunda (ör. birleştirilmiş bir pull request'ten sonra) | aşağıya bakın | aşağıya bakın |
| Kontrol | kurulumdan, güncellemeden, yeni anahtarlardan sonra | `./venv/bin/python selftest.py` | `venv\Scripts\python.exe selftest.py` |
| Anahtarlar / ayarlar | yeni anahtar, başka görsel sağlayıcısı | `nano .env`, sonra yeniden başlatın | `notepad .env`, sonra yeniden başlatın |
| Yedekleme | düzenli olarak, taşımadan ve büyük güncellemelerden önce | `data.db`, `workspace/`, `.env` kopyalayın (önce durdurun) | Hyperstead klasöründe aynısı |

### Güncelleme (yeni sürümü alma)

**Raspberry Pi / Linux**, terminalde:

```bash
cd ~/hyperstead
git pull
./install.sh               # yalnızca requirements.txt değiştiyse gerekir; .env değişmez
sudo systemctl restart hyperstead
./venv/bin/python selftest.py llm     # yapay zekâ sağlayıcılarının yanıt verdiğini kısaca kontrol edin
```

**Windows**, PowerShell'de:

1. `cd $HOME\hyperstead`
2. `git pull`
3. Yalnızca paketler değiştiyse (ya da emin değilseniz): `powershell -ExecutionPolicy Bypass -File install.ps1`
   (mevcut `.env` değişmez).
4. Hyperstead'in siyah başlatma penceresini kapatın.
5. `deploy\windows\hyperstead-start.bat` dosyasını yeniden başlatın (çift tıklayın ya da PowerShell'e yazın).
6. Kontrol: `venv\Scripts\python.exe selftest.py llm`

`git pull` „local changes would be overwritten“ diyorsa, programın bir dosyasını kendiniz değiştirmişsiniz demektir.
`git stash` değişikliği kenara koyar, ardından `git pull` komutunu tekrarlayın. Verileriniz (`data.db`, `workspace/`, `.env`)
bundan asla etkilenmez, çünkü Git bunları bilmez.

### Otomatik başlatma

- **Pi:** `./install.sh --service` hizmeti kurar; böylece her açılışta kendiliğinden başlar.
- **Windows:** Win+R tuşlarına basın, `shell:startup` yazın ve oraya `deploy\windows\hyperstead-start.bat` dosyasının bir kısayolunu koyun
  (kullanıyorsanız `bildrechner-start.bat` dosyasının da). Bunun için Windows'un kendiliğinden oturum açması gerekir
  ([docs/windows.md](docs/windows.md), bölüm 4).

### `.env` ayarlarını değiştirme

- Her ayar tam olarak bir kez, başında `#` olmadan yazılır. `#` ile başlayan satırlar kapalıdır. Yinelenen satırlarda
  ilki geçerlidir.
- Her değişiklikten sonra Hyperstead'i yeniden başlatın, yoksa eski durum geçerli kalır.
- Anahtarları asla sohbetlere, ekran görüntülerine ya da depoya kopyalamayın. Bir anahtar bir yere yanlışlıkla düştüyse: sağlayıcıda iptal edin ve yenisini girin.
- Sonra `selftest.py` ile kontrol edin. Tek tek alanlar: `selftest.py llm`, `web`, `telegram`, `media`, `ocr`, `code`.

### Selbsttest sonuçlarını okumak

- **OK:** çalışıyor.
- **FEHLT (eksik):** isteğe bağlıdır; satır, eklemek için komutu verir (Windows'ta Windows komutunu).
  Yalnızca ajanlarınız bunu kullanıyorsa gerekir (ör. video, sesli okuma, taranmış PDF'ler).
- **FEHLER (hata):** girdiğiniz bir şey çalışmıyor; çoğu zaman geçersiz ya da süresi dolmuş bir anahtar ya da çalışmayan bir hizmet
  (ör. görsel bilgisayarı). Satır nedenini gösterir.
- Bir web hizmetinde tek bir zaman aşımı (Timeout) genellikle geçicidir: daha sonra yeniden deneyin.

### Görsel bilgisayarı (kullanılıyorsa)

- **Nerede:** görselleri üreten bilgisayarda (ör. dizüstü), klasör `C:\bildrechner`.
- **Ne zaman:** ajanların görsel üretmesi gerektiği sürece çalışmalı.
- **Nasıl:** Kurulum bir kez yapılır: Hyperstead klasöründe PowerShell içinde
  `powershell -ExecutionPolicy Bypass -File deploy\windows\bildrechner-einrichten.ps1` (program ve modelleri indirir).
- **Nasıl çalıştırılır:** `C:\bildrechner\bildrechner-start.bat` dosyasını başlatın, pencereyi açık bırakın. Hyperstead'in `.env` dosyasında
  `IMAGE_PROVIDER=sdcpp` ve `SDCPP_URL=...` ([kılavuz](docs/laptop-bildrechner.md)), ardından Hyperstead'i yeniden başlatın.

### Film stüdyosu (kullanılıyorsa)

- **Nerede:** Blender'ın kurulu olduğu bilgisayarda (ör. dizüstü). `film` aracını kullanan şirket **bu** Hyperstead kurulumunda çalışmalıdır.
- **Ne zaman:** Blender'ın açık olması gerekmez, Hyperstead onu her sahne için arka planda başlatır ve yeniden kapatır.
- **Kontrol:** `venv\Scripts\python.exe selftest.py film` (Windows) ya da `./venv/bin/python selftest.py film`.
- **Ne kadar sürer:** 640×360 ve saniyede 12 karede, dizüstüne göre 10 saniyelik film başına yaklaşık 1 ila 5 dakika. Blender hiçbir zaman görsel bilgisayarıyla aynı anda çalışmaz.

### Taşınma (ör. Pi → dizüstü)

Adım adım [docs/windows.md](docs/windows.md) dosyasında, „Phase 2 – Umzug“ bölümünde (Almanca). Kısaca: ikisini de durdurun, `data.db`,
`workspace/` ve `.env` dosyalarını kopyalayın, yeni bilgisayarda başlatıp kontrol edin ve ancak ondan sonra eskisini kapatın.
Telegram'ı yalnızca tek bir bilgisayarda kaydedin.

### Bir şey eksik olduğunda ne olur

Bu liste programda her değişiklikle genişletilir. Her satır sistemin ne yaptığını ve sizin ne yapmanız gerektiğini söyler.

| Eksik | Sistem ne yapar | Siz ne yaparsınız |
| --- | --- | --- |
| `.env` | Hyperstead anahtarsız ve şifresiz başlar; yalnızca bu bilgisayardan erişilebilir. `HOST=0.0.0.0` ile `APP_TOKEN` boş olduğu sürece başlatma iptal edilir. | `./install.sh` (Pi) ya da `install.ps1` (Windows) rastgele şifreli bir tane oluşturur. |
| `data.db` | Boş olarak yeniden oluşturulur. Şirketler, görevler ve gönderiler kaybolur. | Önce yedekleyin (İşletim bölümüne bakın). Yalnızca bir yedekten geri kopyalayın. |
| `.env` içindeki API anahtarı | Sağlayıcı selbsttest'te FEHLT olarak gösterilir ve ajanlar kullanmaz. Girilmiş ama geçersizse: HTTP 401 ile FEHLER. | Anahtarı girin ya da satırı `#` ile kapatın. |
| `SDCPP_URL` (`IMAGE_PROVIDER=sdcpp` ile) | Görsel istekleri „SDCPP_URL fehlt“ (eksik) hatasıyla başarısız olur. `IMAGE_FALLBACK=pollinations` ile referanssız, ücretsiz bir yedek görsel üretilir ve sonuçta bir not yer alır. | `.env` dosyasına satırı ekleyin, Hyperstead'i yeniden başlatın. |
| Görsel bilgisayarına ulaşılamıyor (dizüstü kapalı, güvenlik duvarı, yanlış IP) | Yukarıdaki gibi: „Bildrechner … nicht erreichbar“ (erişilemiyor) hatası; yedekle bir yedek görsel. | Dizüstünü açın, `bildrechner-start.bat` dosyasını başlatın, IP'yi ve güvenlik duvarını kontrol edin. |
| `sd-server.exe` (Windows, görsel bilgisayarı) | `bildrechner-start.bat` „sd-server.exe fehlt“ (eksik) gösterir ve hiçbir şey başlatmaz. | `deploy\windows\bildrechner-einrichten.ps1` dosyasını çalıştırın. |
| Model dosyası (Windows, görsel bilgisayarı) | Başlatma dosyası eksik dosyayı adıyla belirtir ve başlamaz. Yalnızca büyük dil modeli (`Qwen3-4B-Q4_K_M.gguf`) eksikse ve daha küçüğü varsa, onu kullanır. | Kurulum betiğini yeniden çalıştırın; yalnızca eksik dosyayı indirir. |
| Windows çalışma zamanı `VCOMP140.DLL` | `sd-server.exe` „VCOMP140.DLL nicht gefunden“ (bulunamadı) bildirir ve kapanır. | Kurulum betiğini yeniden çalıştırın (3. adım çalışma zamanını kurar), sonra başlatma dosyasını açın. |
| Port 1234 için güvenlik duvarı kuralı (Windows) | Yalnızca Pi görsel bilgisayarına ulaşamaz. Dizüstünün kendisi çalışmaya devam eder. | [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md) dosyasındaki 4. bölümden komutu yönetici olarak çalıştırın. |
| `macros/` içinde makro veya `macros/<site>.json` oturumu (`PCL_MACROS=1` ile) | Makro yoksa `site_macro` aracı görünmez. Kayıtlı oturum yoksa makro bir uyarıyla durur. MagicLight veya Flow sayfasını değiştirirse `site_macro` FEHLER verir ve `output/` içine `<site>-fehler.png` koyar. Kendi denetimi (`browser`) FEHLT gösterir. | Makroyu [macros/README.md](macros/README.md) açıklamasına göre (yeniden) kaydedin. |
| `ffmpeg`, `tesseract`, `pdftoppm`, sesli çıktı | İşlev eksiktir. Bunu kullanması gereken ajanlar hatayı sonuçta bildirir. Selbsttest FEHLER (Pi) ya da FEHLT (Windows) gösterir. | Programı kurun (komutlar selbsttest'te ve [docs/windows.md](docs/windows.md) dosyasında). |
| Blender (`film` aracı) | `save`, `check`, `voices` ve `assemble` yine çalışır. `preview` ve `render`, `BLENDER_PATH` ipucuyla „Blender wurde nicht gefunden“ (Blender bulunamadı) bildirir. Selbsttest FEHLT gösterir. | Blender'ı kurun (`winget install BlenderFoundation.Blender`) ya da `.env` içinde `BLENDER_PATH` ayarlayın, yeniden başlatın. |
| `film/film.json` (senaryo) | `film`, „film/film.json fehlt“ (eksik) bildirir ve önce `op=save` ile bir senaryo kaydedilmesini ister. Hatalı bir senaryo kaydedilmez, yanıt tüm hataları listeler. | Hiçbir şey, ajanlar onu kendileri oluşturur. Elle de yazabilirsiniz ([docs/filmstudio.md](docs/filmstudio.md)). |
| Senaryoda adı geçen görsel, müzik ya da `.blend` dosyası | Kontrol sahneyi, karakteri ve yolu bildirir, hiçbir şey render edilmez. | Dosyayı `assets/` ya da `input/` klasörüne koyun veya senaryodaki yolu düzeltin. |
| Bir sahnenin klibi (`film/clips/`) | `assemble` eksik sahneleri bildirir ve kurgu yapmaz. `render` yarıda kalırsa (zaman sınırı), biten kareler korunur ve sonraki çağrı oradan devam eder. | Hiçbir şey, ajanlar `render` komutunu yeniden çağırır. |
| Film için sesli okuma | `voices`/`render`, „Keine Sprachausgabe verfügbar“ (sesli okuma yok) ile durur. Hiç diyaloğu olmayan sahneler yine çalışır. | Yukarıdaki „sesli okuma“ satırındaki gibi (Windows'ta `edge-tts` + `TTS_ENGINE=edge`). |
| `cargo` (Rust, `rust_project` aracı) | Araç ajanlara gösterilmez; `rustc` varsa `check_code` `.rs` dosyalarını denetlemeye devam eder. Selbsttest (`selftest.py rust`) kurulum komutuyla FEHLT gösterir. | Rust kurun: Pi `curl https://sh.rustup.rs -sSf \| sh`, Windows `winget install Rustlang.Rustup`. Ardından Hyperstead'ı yeniden başlatın. |
| Rust derlerken bubblewrap (Pi/Linux) | `rust_project`, tıpkı `run_code` gibi gizli kalır. | `./install.sh --run` |
| `PCL_CARGO_UNSAFE=1` (Windows) | Windows'ta yalıtım yoktur, bu yüzden anahtar olmadan `rust_project` gizli kalır. Anahtarla dizüstü bilgisayar yalıtımsız derler. | Yalnızca riski biliyorsanız ayarlayın ([Rust programları](#-rust-programlarını-eksiksiz-derleme)), sonra yeniden başlatın. |
| Rust klasöründe `Cargo.toml` | `rust_project` "In … fehlt Cargo.toml" bildirir ve ajanın önce oluşturması gereken dosyaları adlandırır. | Hiçbir şey, ajan bunları `write_code` ile oluşturur. |
| Rust bağımlılıkları için internet (crates.io) | `cargo fetch` başarısız olur, hiçbir şey derlenmez, ajan hata mesajını alır. Daha önce indirilen bağımlılıklar `.rust/cargo-home` içinde kalır ve çalışmaya devam eder. | İnternet bağlantısını kontrol edin ve görevi yeniden başlatın. |
| Rust paketi için geçen testler | Paket **oluşturulmaz** ("KEIN PAKET"); ajan hataları satır numarasıyla alır ve düzeltmek zorundadır. Test yoksa paket, sonuçta bir WARNUNG ile oluşturulur. | Hiçbir şey, ajan düzeltir ve yeniden derler. Vazgeçerse şef üzerinden geri gönderin. |
| Projede `.rust/` klasörü (derleme klasörü) | Bir sonraki derlemede yeniden oluşturulur, o zaman daha uzun sürer (her şey yeniden indirilir ve derlenir). Gizlidir ve ZIP indirmesine dahil değildir. | Hiçbir şey. Yer kalmazsa silebilirsiniz. |
| Telegram belirteci ya da sohbet kimliği | Telegram kapalı kalır, diğer her şey çalışır. Selbsttest FEHLT gösterir. | Yalnızca mesajları telefonunuza almak istiyorsanız gerekir. |
| Projede bir klasör ya da dosya (`wissen/`, `input/`) | Var olmayan klasörler boş sayılır. Ajanlar şirket bilgisi olmadan çalışmaya devam eder. | Projede dosyayı ya da klasörü oluşturun veya yükleyin. |
| Bir video sağlayıcısının anahtarı (ör. `KLING_SECRET_KEY`, `HIGGSFIELD_API_KEY_SECRET`) | `video_generate` „VIDEO_PROVIDER=…, aber … fehlt“ (eksik) der ve hiçbir şey üretmez; listedeki diğer sağlayıcılar çalışmaya devam eder. Öz test sağlayıcıyı FEHLT olarak gösterir. | Anahtarı girin ([docs/videodienste.md](docs/videodienste.md)) ya da sağlayıcıyı `VIDEO_PROVIDER` satırından silin, yeniden başlatın. |
| Video sağlayıcısındaki bakiye | Sağlayıcı bir hatayla yanıt verir (çoğunlukla HTTP 402/429 ya da „insufficient balance“), ajan bu metni sonucunda görür. Yerine başka bir sağlayıcı devreye girmez. | Bakiye yükleyin ya da `provider` ile veya `VIDEO_PROVIDER` içinde başka bir sağlayıcı seçin. |
| `FAL_KEY` (`VIDEO_PROVIDER=fal`, `VIDEO_AI=fal` ya da `AUDIO_PROVIDER=fal` ile) | `video_generate`, `video_ai` ya da `sound_generate` „FAL_KEY fehlt“ der ve hiçbir şey üretmez. | fal.ai anahtarını girin ya da `VIDEO_AI`/`AUDIO_PROVIDER` satırını kaldırın. |
| `ELEVENLABS_API_KEY` (gerektiğinde daha iyi sesler) | Her şey yerel seslerle eskisi gibi çalışır. Yine de `engine: elevenlabs` ya da `TTS_ENGINE=elevenlabs` kullanılırsa veya ElevenLabs/OpenAI başarısız olursa (anahtar, bakiye, internet), yerel ses konuşur ve sonuç “HINWEIS: … nicht genutzt” ve nedeniyle başlar. Filmde satır bir sonraki `voices` çağrısında bulut sesiyle yeniden denenir. `TTS_FALLBACK=0` ile görev bunun yerine durur. | elevenlabs.io anahtarını `.env` dosyasına yazın ve yeniden başlatın. Kılavuz: 📖 → “🎙 Stimmen und ElevenLabs”. |
| CEO'nun yeni aldığı çalışanın yapay zekâsı | Yeni çalışan oluşturulur ama görev almaz. CEO sonra yeniden plan yaparsa görev „Diesen Mitarbeitern ist noch keine KI zugewiesen: …“ (henüz yapay zekâ atanmadı) ile durur. **⚠ Modelle** menüsünde „Noch keine KI“ olarak görünür. | ⚠ Modelle menüsünde yapay zekâ atayın ve gönderide „Weiter“ yanıtını verin. |
| CEO'nun aldığı çalışanın hakları | Sistem eksik hakları role göre ekler (yukarıdaki liste). Hiçbir anahtar kelime uymazsa yalnızca *dosya okuma* alır ve yalnızca metinle yanıt verebilir. | Ajan panelinde kutuları işaretleyin ya da CEO'ya rolü daha net verin. |
| CEO'nun çıkarmak veya değiştirmek istediği çalışan | Ad ekibinde yoksa (yazım hatası, başka ekip, zaten çıkarılmış) talimat atlanır ve sonuçta not edilir. Çalışanın hâlâ açık görevi varsa kalır. | Hiçbir şey, ya da daha sonra yeniden görevlendirin. |
| `video_providers.py` (program dosyası) | Video, ses ve bulut sesi araçları ajanlar için görünmez olur, geri kalan her şey çalışmaya devam eder. | `git pull` komutunu yeniden çalıştırın, dosya programın parçasıdır. |
| `GITHUB_UPLOAD_TOKEN` veya `GITHUB_UPLOAD_REPO` | GitHub, ☁️ Cloud altında "kurulmamış" görünür, ajanlara hedef olarak sunulmaz. Geri kalan her şey çalışır. | Token ve repoyu girin ([docs/cloud.md](docs/cloud.md), Almanca), yeniden başlatın. |
| `GDRIVE_CLIENT_ID`/`GDRIVE_CLIENT_SECRET` veya `ONEDRIVE_CLIENT_ID` | Hizmet "kurulmamış" kalır, "Oturum aç" düğmesi görünmez. | Uygulamayı kaydedin ve satırları girin ([docs/cloud.md](docs/cloud.md)), yeniden başlatın. |
| Google/Microsoft oturumu (`tokens/` klasörü) | Hizmet "oturum açılmamış" görünür. Yükleme "henüz oturum açılmadı" ya da "oturumun süresi doldu" der ve hiçbir şey yüklemez. | ☁️ Cloud → Oturum aç. Pi'den dizüstüne taşırken dizüstünde yeniden oturum açın. |
| Telegram için 50 MB üstü dosya | Telegram kabul etmez. `/datei` dosyayı ⚠️ ile işaretler ve göndermez, ajan bir uyarı alır. | Hedef olarak Google Drive, OneDrive veya GitHub seçin. |
| `cloud_upload.py` (program dosyası) | Hyperstead başlamaz (içe aktarma hatası). | `git pull` komutunu yeniden çalıştırın, dosya programın parçasıdır. |
| `PCL_ALLOW_WERKSTATT=1` | “Atölye” onay kutusu gri olur, hiçbir ajan `befehl` veya `nachruesten` almaz. Diğer her şey eskisi gibi çalışır. | Satırı `.env` dosyasına ekleyin, yeniden başlatın, ajanda kutuyu işaretleyin ([docs/werkstatt.md](docs/werkstatt.md)). |
| Bir ajanın ihtiyaç duyduğu program (ör. Node.js, Remotion, bir Python paketi) | Atölyesi olan ajan bir kurulum talebi oluşturur: CEO kontrol eder, siz Telegram’da ve ✋ Onaylar altında ✅/❌ alırsınız. Onayınızdan sonra sunucu kurar ve görev devam eder. Atölye yoksa ajan yalnızca neyin eksik olduğunu yazar. | Talebi okuyup karar verin. Telegram yoksa yalnızca web üzerinden. |
| CEO’nun yapay zekâsı (kurulum talebinde) | Talep “Yapay zekâlı CEO yok” veya “CEO’ya ulaşılamıyor” notuyla doğrudan size gelir. | Kendiniz karar verin veya CEO’ya bir yapay zekâ atayın. |
| `werkstatt.py` (program dosyası) | Hyperstead başlamaz (içe aktarma hatası). | `git pull` komutunu yeniden çalıştırın, dosya programın parçasıdır. |
| `growth.py` (program dosyası) | Hyperstead başlamaz (içe aktarma hatası). | `git pull` komutunu yeniden çalıştırın, dosya programın parçasıdır. |
| Bir projenin dünyası hiç seçilmemiş | Proje, aşamaları ve terimleriyle uzay dünyasını gösterir. | Yapılacak bir şey yok. Grafik seçimindeki ⚛️ Atom, Atom dünyasına geçirir, 🌌 Weltall geri döndürür. |
| `static/logo/` içindeki logo dosyaları | Kenar çubuğu ve giriş sayfası boş bir resim alanı gösterir, tarayıcı sekmesinde simge görünmez. Geri kalan her şey normal çalışır. | `git pull` komutunu tekrar çalıştırın. Logo `docs/logo/logo_blender.py` ile yeniden oluşturulabilir ([kılavuz](docs/logo-prompt.md), Almanca). |
| Bir projede kayıtlı eski dünya (Lonca, Tycoon, Gizmo Şehri) | Proje otomatik olarak uzayı gösterir. Puanlar, aşama ve rütbeler aynı kalır, yalnızca adlar ve simgeler değişir. | Yapılacak bir şey yok. |
| Bugün yapay zekâ çağrısı yok (operasyon merkezi, çubukta 💶) | 0 $ veya „keine Aufrufe“ gösterir. | Yapılacak bir şey yok. Maliyetler tahminidir, kendi fiyatlarınızı `.env` içinde `PCL_PRICES` ile belirleyin. |
| `firm_links` tablosu (eski `data.db`) | Başlangıçta otomatik ve boş oluşturulur: şehir ve kozmosta henüz iş birliği görünmez. | Hiçbir şey. |
| Proje klasöründeki şirket logosu `.logo.png` / `.logo.jpg` / `.logo.webp` | Şirket şehirde ve kozmosta logo göstermez, geri kalan her şey normal çalışır. | Şirketin bilgi penceresinde (🏙/🌌, şirkete dokun) „Logo“ altında 🖼 Hochladen seç: PNG, JPEG veya WebP, en fazla 2 MB. |
| Tarayıcı hiçbir şey kaydetmiyor (gizli pencere) | Açık/koyu, seçilen grafik (uzay, şema türü, atom, plan), taşınan şema kartları, hareket ve yardım modu her yüklemede varsayılana döner. | Normal pencere kullanın; proje verileri bundan etkilenmez. |
| Plandaki ajanlar üst üste duruyor (ör. hepsi aynı yerde) | Bağlantı çizgileri görünmez. Plan açıldığında Hyperstead onları bir kez otomatik olarak düzenler ve bunu bildirir. | Hiçbir şey yapmayın veya „🗂 Ordnen“ düğmesine basın. |

## İnternetten erişim

Uygulama kasıtlı olarak yalnızca `127.0.0.1` üzerinden dinler. Bir port açmak yerine bir tünel kullanırsınız.
Bu, mobil yönlendiriciniz gelen bağlantılara izin vermiyorsa (CGNAT) da gereklidir.

### Seçenek A (önerilen): Tailscale, özel, yalnızca kendi cihazlarınız için

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up                    # tarayıcıda giriş bağlantısını açın
sudo tailscale serve --bg 8787       # yalnızca kendi tailnet'inizde HTTPS adresi
```

Tailscale'i telefonunuza/dizüstünüze de kurun, sonra gösterilen `https://dexter….ts.net` adresini açın.
`.env` dosyasına ekleyin: `TRUST_PROXY=1`, ardından hizmeti yeniden başlatın.
**`tailscale funnel` kullanmayın**; bu uygulamayı internete açık hale getirir.

### Seçenek B: Cloudflare Tunnel, kendi alan adınızla herkese açık adres

```bash
# cloudflared kurun (bkz. developers.cloudflare.com/cloudflare-one/connections/connect-networks)
cloudflared tunnel login
cloudflared tunnel create hyperstead
cloudflared tunnel route dns hyperstead agents.sizin-alaniniz.de
# ~/.cloudflared/config.yml:  ingress: - hostname: agents.sizin-alaniniz.de  service: http://127.0.0.1:8787
cloudflared tunnel run hyperstead
```

Buna ek olarak şiddetle önerilir: önüne **Cloudflare Access** (e-posta girişi) koyun.
`.env` dosyasında: `TRUST_PROXY=1`. Komutlar değişebilir; emin değilseniz resmî kılavuz geçerlidir.

`TRUST_PROXY=1` ile uygulama yalnızca `APP_TOKEN` en az 12 karakter içeriyorsa başlar.

## Kullanım

| İşlem | Nasıl yapılır |
|---|---|
| Ajan oluşturma | paletteki girdiyi alana sürükleyin (ya da tıklayın) |
| Bağlama | bir düğümün alt noktasını başka bir düğüme sürükleyin (= patron → çalışan) |
| Bağlantıyı kesme | bağlantı çizgisine tıklayın |
| Taşıma | düğümü sürükleyin; arka planı sürüklemek görünümü kaydırır; fare tekerleği = yakınlaştırma |
| Ayarlama | düğüme tıklayın → sağdaki panel |
| Görev atama | Panel → „Aufgaben“ sekmesi (görevler) |
| Onaylama | kenar çubuğu „Freigaben“ (onaylar) |

## Şirket nasıl çalışır

Bir patron bir görev alır ve **planlar** (alt görevleri dağıtır) ya da işi kendisi yapar. Tüm
çalışanları bitirir bitirmez yeniden uyanır, **raporlarını okur**, eksikleri geri bildirimle iade eder ya da
her şeyi özetleyip kendi patronuna bildirir. Sonuç böylece istediğiniz kadar seviye yukarı çıkar.
„Wartet auf Team“ durumu (ekibi bekliyor) şu anlama gelir: patron ekibini bekliyor. Görevler sekmesinde tüm ağacı görürsünüz.

## Uzay ve büyüme

Her proje, başarılarıyla büyüyen küçük bir **evrendir**. Uzay yalnızca arayüzün kelimelerini, simgelerini ve renklerini
değiştirir. Ajanlar her zaman açık terimlerle (görev, rapor, ekip) çalışır, böylece kaliteleri aynı kalır.

| Uzayda | Ekipteki anlamı |
| --- | --- |
| ☀️ Güneş | en üst yönetim (ör. CEO) |
| 🪐 Gezegen | departman veya ustabaşı, güneşin etrafında döner |
| 🌙 Ay | çalışan, kendi gezegeninin etrafında döner (daha alttaki herkes bir ayın küçük ayıdır) |
| Aşamalar | ☄️ Asteroit → 🪐 Gezegen → ☀️ Güneş sistemi → ✨ Yıldız kümesi → 🌌 Galaksi |
| Ajan rütbeleri | ☄️ Kuyruklu yıldız → 🌙 Ay → 🪐 Gezegen → ⭐ Yıldız |

Puanlara yıldız tozu, görevlere görev (Mission) denir. Eski Lonca, Tycoon ve Gizmo Şehri dünyaları artık yok; mevcut projeler uzayı otomatik olarak gösterir, puanlar ve aşamalar korunur. Arayüz adları Almanca gösterir.

**Atom dünyası:** Uzayın yanında ikinci bir dünya vardır. Grafik seçiminde ⚛️ Atom'u seçersen proje için Atom dünyası geçerli olur, 🌌 Weltall ile tekrar uzaya dönülür (büyüme çubuğunda, kutlamada ve Telegram'da da). Büyük küre = en üst yönetim, orta küreler = ekip liderleri, küçük küreler = çalışanlar. Aşamalar: ✴️ Kuark → ⚛️ Atom → 🧪 Molekül → 💎 Kristal → 🧬 Hücre; rütbeler: · Nötrino → ⚡ Elektron → 🔴 Proton → 💠 Nükleon (arayüz Almanca adları gösterir). Puanlara enerji, görevlere deney denir. Puanlar ve aşama sınırları iki dünyada da aynıdır. Organizasyon şeması ve plan en son seçilen dünyayı korur.

**Kullanım:** Çalışma alanının üstündeki çubuk aşamayı, bir sonraki aşamaya ilerlemeyi ve önemli sayıları gösterir. Sağda açık ve koyu arasında geçiş yapar (🌓) ve ⓘ ile aşamalar, puanlar ve rütbeler hakkındaki özeti açarsınız. Her ajanın rütbesi kartında simge olarak görünür.

**Güneş sistemi:** Çubuğun sağındaki açılır düğme (ör. „🌌 Weltall ▾“) grafiği seçer: 🌌 uzay, üç organizasyon şeması, ⚛️ atom veya 📐 plan (düğüm editörü). Uzay ayrıntılı çizilir: ışınları ve lekeleri olan bir güneş, gece yüzü, bulutları veya kuşakları olan gezegenler, kraterli aylar, bir asteroit kuşağı, uzak galaksiler ve Samanyolu. Gezegenler ve aylar yavaşça döner, gezegenler ve güneş ayrıca kendi eksenleri etrafında da döner (bulutlar, kuşaklar ve güneş lekeleri yüzeyde kayar, güneşin ışın tacı döner), galaksi aşamasında arka plandaki sarmal da döner; fareyle birinin üzerine geldiğinizde kolayca tıklayabilmeniz için her şey durur. Mavi yanıp sönen halka "çalışıyor", sarı halka "onayınızı bekliyor", kırmızı halka "hata", mor kesikli halka "ekibini bekliyor" demektir. Güneşe veya bir gezegene dokunmak ekibi ve eylemleri gösterir, bir aya dokunmak ajanı açar. Her aşamada gökyüzü dolar, yıldız kümesinden itibaren bulutsular parlar, galakside bir sarmal belirir. Uzay açık temada da karanlık kalır. Telefonda harita yerine bir liste görünür: güneş, altında her gezegen ve ayları. Cihaz „hareketi azalt“ isterse hareket kapanır.

**Organizasyon şeması:** ekibi üç şekilde gösterir, her biri grafik menüsünde ayrı bir seçenektir: ⬇ Baum (yukarıdan aşağıya ağaç, kendi ekibi olmayan çalışanlar alt alta durur), ➡ Gliederung (her ajan için bir satır, seviyeye göre girintili, telefon için en iyisi) ve ◎ Kreis (daire, yönetim ortada, her seviye bir halka). Renk durumu gösterir: yeşil hazır, mavi çalışıyor, sarı onayınızı bekliyor, kırmızı hata, mor ekibi bekliyor, gri duraklatıldı. Dokunmak ajanı açar. Kartlar sürüklenebilir, çizgiler onları takip eder; cihaz bunu her proje ve şema için hatırlar, „↺ Anordnung zurücksetzen“ düzeni geri getirir. Bir kartı başka bir kartın üzerine bırakırsanız (planda da bir ajanı başka bir ajanın üzerine), Hyperstead önce sorar ve ancak onaydan sonra onu o ekibe ekler.

**Atom:** ⚛️ ekibi bir molekül ağı olarak gösterir: çubuklarla bağlı parlak küreler. Büyük mavi küre en üst yönetimdir, orta boy renkli küreler ekip liderleri, küçük küreler çalışanlardır. Her küre bir çubukla üstüne bağlıdır, böylece hiyerarşi boyut ve bağlantılardan anlaşılır; her şey katı sıralar halinde değil, bir molekül modeli gibi gevşek ve uzamsal olarak dizilir. Her şirketin kendine ait bir molekülü vardır: biçim ve renkler şirketten gelir, büyük küre projenin rengini taşır. Modern görünümde ⚛️ Molekül tüm şirketleri yan yana moleküller olarak gösterir; ortak şirketler yöneticileri arasındaki parlak bir çubukla bağlıdır ve üzerinde kıvılcımlar dolaşır (ikisi de çalışıyorsa daha fazla). Dokunmak moleküle yakınlaştırır, her küre departmanını ve ajanını açar. Grafik hareketsizdir, böylece rahatça okunur. Bir dünya olarak resim aşamayla birlikte büyür: kuark aşamasında çekirdekte üç kuark parlar, molekülden itibaren komşu atomlar bağlarla bağlanır, kristalden itibaren arka planda bir atom kafesi bulunur, hücre aşamasında hücre duvarı ve DNA çift sarmalı eklenir. Durum ve dokunma organizasyon şemasındaki gibidir.

**Operasyon merkezi:** Kenar çubuğundaki 🛰 (veya büyüme çubuğundaki sayılara dokunmak) şu anda neyin çalıştığını ve beklediğini, hangi onayların açık olduğunu, son 7 günde neyin başarısız olduğunu (↻ Neu ile), zaman planlarını (▶ Jetzt ile), hata mesajlarını ve son olayları bir bakışta gösterir. Ayrıca bugünün ve son 7 günün tahmini yapay zekâ maliyetlerini gösterir; bugünkü maliyet çubukta 💶 olarak da görünür. Tüm sayılar mevcut görevlerden, onaylardan, zaman planlarından ve geçmişten gelir, hiçbir şey uydurulmaz.

**Yükselme ve kullanım:** Bir proje yeni bir aşamaya ulaştığında, yeni aşamayı ve bir sonraki hedefi gösteren kısa bir kutlama görünür (Telegram aynı mesajı gönderir). Bir ajan rütbe atladığında kısa bir bildirim çıkar. Çubuktaki ⓘ altında bu cihaz için hareket ve kutlama efektlerini kapatabilirsiniz; cihaz „hareketi azalt“ isterse zaten her şey durağan kalır. Tüm pencereler Esc ile kapanır, uzaydaki güneş, gezegenler ve aylar Tab ve Enter ile kullanılabilir.

**Kılavuz ve yardım:** Kenar çubuğunun en üstündeki 📖 Anleitung, kullanım kılavuzunu doğrudan panoda açar (açılır bölümler, arama, indirme yok, çevrimdışı da çalışır). Bir pencerenin üstündeki ⓘ ilgili bölüme atlar. Her düğme fareyle üzerine gelindiğinde kısa bir açıklama gösterir. Telefonda kılavuzda yardım modunu açın: bir düğmeye ilk dokunuş onu açıklar, ikincisi çalıştırır.

**Puanlar:** teslimat ilk seferde kabul +10, düzeltmeden sonra +5, görev postada tamamlandı olarak işaretlendi +20,
başarısız −3, yeniden çalışma istendi −5. Aşamalar 0 / 100 / 300 / 700 / 1500 puandan başlar. Mevcut projelerin
geçmiş başarıları otomatik olarak sayılır. Bir aşama atlaması Telegram ile bir kez bildirilir.

**Aşamanın sınırladığı şey:** yalnızca yönetimin **kendi başına** kaç ajan alabileceği (projede 8 / 12 / 18 / 25 / sınırsız)
ve ne kadar derine (2 / 3 / 4 / 5 / tam derinlik). Siz her zaman her şeyi kendiniz oluşturabilirsiniz. Sınır proje başına
kapatılabilir.

**Ajan rütbeleri** kendi kabul edilen teslimatlarına göre: 0 / 5 / 20 / 60'tan itibaren (ör. çırak, kalfa, usta, büyük usta).

## Ajanların yetenekleri (internet, görseller, dosyalar)

Ajanlar turlar halinde çalışır: araç ister, sunucu çalıştırır ve sonuçları geri verir; bitene kadar böyle devam eder
(en fazla `PCL_MAX_TOOL_STEPS`). Ajan başına haklar: **internette araştırma**, **görseller**, **proje dosyalarını okuma**
(ve eskisi gibi dosya yazma).

| Araç | Ne yapar | Anahtarsız |
|---|---|---|
| `web_search` | web araması (yasalar, fiyatlar, rekabet …) | DuckDuckGo; daha iyisi: `SEARXNG_URL`, `BRAVE_API_KEY` ya da `TAVILY_API_KEY` |
| `fetch_url` | bir web sayfasını metin olarak okur | evet |
| `browse_page` | sayfayı gerçek bir tarayıcıda açar (JavaScript çalışır), isteğe bağlı olarak ajanın bir görsel olarak gördüğü bir ekran görüntüsüyle | evet, `./install.sh --browser` gerekir |
| `image_search` / `image_save` | özgür lisanslı fotoğrafları arar ve yazar ve lisansıyla birlikte `assets/` içine kaydeder | Openverse; isteğe bağlı `PEXELS_API_KEY` |
| `image_generate` | PNG olarak bir yapay zekâ görseli üretir; isteğe bağlı olarak projeden en fazla 4 referans görselle (bir dizide aynı figürler ve aynı stil), kare/dikey/yatay biçimle ve `assets/`, `output/` ya da `karten/` içinde hedef yolla. Hak **Görseller** veya **Medya** | Pollinations (anahtarsız: referans görselsiz; `POLLINATIONS_API_KEY` ve Pollen kredisiyle: model `POLLINATIONS_MODEL` ile, referans görsellerle); `IMAGE_STYLE` sabit bir çizim stili belirler; diğerleri: `nvidia` (build.nvidia.com üzerinden FLUX), `cloudflare` (Workers AI, referans görselli FLUX.2 klein), `hf` (Hugging Face), her biri için model `IMAGE_MODEL` ile; kendi bilgisayarınızda referans görselli ücretsiz: `IMAGE_PROVIDER=sdcpp` ([kılavuz](docs/laptop-bildrechner.md)); daha iyisi `OPENAI_API_KEY` ile `IMAGE_PROVIDER=openai`, `gemini`, ya da `OPENROUTER_API_KEY` ile `openrouter` |
| `list_files` / `read_file` | proje klasöründeki dosyaları okur (ör. meslektaşların metinleri) | evet |

Üretilen her şey `workspace/<proje-kimliği>/` altında durur. Kenar çubuğunda **📁 Dateien** (dosyalar) dosyaları gösterir, `index.html` dosyasını
bir web sayfası olarak açar (yalıtılmış sandbox) ve her şeyi ZIP olarak indirir. Bağlantı gizli bir anahtar içerir.

**Projeler ve görünümler:** Kenar çubuğunda „Projekte“ altındaki büyük „＋ Neues Projekt“ düğmesi bir pencere açar: boş proje veya şablondan hazır şirket. Sağ üstteki grafik menüsünün iki grubu vardır: **Klassik** (üç organizasyon şeması ağaç, liste ve daire ile plan) ve **Modern** (tüm şirketler şehir, kozmos veya molekül olarak). Tek bir proje için uzay ve molekül artık yok; bunları en son açık bırakan organizasyon şemasına düşer. Proje ve büyüme bilgilerini gösteren üst çubuk şehir, kozmos ve molekülde de yerinde kalır; altındaki „Agent hinzufügen“ çubuğu da öyle (yeni ajanlar üstte seçili projeye eklenir). Şehir, kozmos ve molekül döndürülüp eğilebilir: sağ alttaki ⟲ ⟳ ⤵ ⤴ ⌂ düğmeleri, sağ fare tuşuyla sürükleme veya telefonda iki parmak. Solda bir proje seçtiğinde şirketi şehirde, kozmosta ve molekülde parlar, diğerleri soluklaşır. Şehirde her şirket kendine özgü bir binadır ve çalıştığı sürece ışıkları yanar; içine girildiğinde her hiyerarşi seviyesi için bir kat görünür, şirket ne kadar derinse o kadar: en üst katta yönetim, altında departman yöneticileri, sonra diğer her seviye; herkesin kendi odası vardır, yani bir seviyede 4 kişisi olan departmanın orada kendi renginde 4 odası olur; her kat odalarını ortalanmış ve eşit aralıklarla dizer, departmanlar bir arada kalır ve bina en kalabalık katı kadar geniştir, sağda organizasyon şeması. Başarıyla bina büyür: daha fazla seviye daha fazla kat demektir, 2. seviyeden itibaren ek bina ve çatı bahçesi, 3. seviyeden itibaren anten, 4. seviyeden itibaren helikopter pisti eklenir. Kozmosta her şirket bir güneş sistemidir (güneş = yönetim, gezegenler = departmanlar); güneş seviye ve ekiple büyür, gezegenler telefonda da döner ve parmağın altında durur, uzaklaştırınca isimler okunabilir kalır. Her şirket bilgi penceresinde „Logo“ altında kendi logosunu alabilir (🖼 Hochladen, 2 MB'a kadar PNG/JPEG/WebP): şehirde çatıda parlayan bir tabela, kozmosta güneşin ortasında görünür.

**Şirket şablonları** („＋ Neues Projekt“ düğmesi): *Web ajansı*, *Muhasebe/Mali müşavirlik*, *İthalat/İhracat ticareti* proje, organizasyon şeması, çalışma talimatları ve hakları eksiksiz oluşturur. Kendi şirketleriniz: proje hedefini yazın („siz bir …sınız“, ülke, sektör), ajanları ve hakları ayarlayın. Ajanlar tarihi ve proje hedefini alır; değişken bilgileri (yasalar, fiyatlar) önce araştırmalı ve kaynak göstermelidir.

**Araç güvenliği:** Sayfa çağrıları yalnızca genel adreslerle sınırlıdır (localhost, yerel ağ, Tailscale,
bulut meta verileri yok; yönlendirmeler tek tek denetlenir). Ajanlar için web içeriği güvenilmeyen veri sayılır,
ama hazırlanmış bir sayfa yine de bir modeli etkileyebilir: internet erişimi olan ajanlara kabuk (shell) vermeyin ve sonuçları kontrol edin.
Ajanların satın alma, sipariş, ödeme ya da e-posta gönderme için **hiçbir** aracı yoktur; yalnızca taslak ve öneri üretirler.
Görsel lisansları (CC) çoğu zaman atıf ister; görsel editörü bunu `bildnachweis.md` dosyasına yazar.

## Medya, belgeler ve kendi dosyalarınız

**Medya ve belge oluşturma** hakkıyla (ve Pi'de `ffmpeg`/yazı tipleriyle, bkz. `install.sh`):

| Araç | Neler yapabilir |
|---|---|
| `video_edit` | videoyu kesme (`trim`), birleştirme (`concat`), görsellerden **zoom'lu slayt gösterisi animasyonu** (`slideshow`, isteğe bağlı sesle), metin/altyazı/logo ekleme, sesi değiştirme ya da karıştırma, hızı değiştirme, GIF/WebM/MP3'e dönüştürme, durağan kare çıkarma |
| `speak` | metni konuşmacı sesine çevirir (espeak-ng çevrimdışı; daha iyisi: Piper; isteğe bağlı Edge sesleri ya da `TTS_ENGINE` ile ElevenLabs/OpenAI bulut sesleri), farklı sesler için `voice`, `pitch`, `rate` ile |
| `film` | **Blender ile animasyon filmi**: JSON olarak senaryo, karakterler (köpek, kedi, tavşan, ayı, fare, insan, kendi görselleriniz ya da `.blend` karakterleri), ağız hareketli sesler, hareketler, kamera, önizleme görseli, sahne sahne render, altyazılı kurgu ([kılavuz](docs/filmstudio.md)) |
| `write_file` | **dosya yazma** hakkıyla: bölümleri, HTML, CSV vb. hemen oluşturur; böylece aynı görevde bunlardan bir PDF/DOCX/EPUB üretilebilir |
| `make_document` | Markdown bölümlerinden **PDF, DOCX, EPUB ya da HTML** (A4/A5, kapak, görseller, Almanca ve Türkçe karakterler); `html` ile **HTML+CSS**'ten serbest düzenli bir PDF (şablonları yeniden oluşturma, WeasyPrint ile, yalnızca proje dosyalarını yükler) |
| `video_generate` | metinden ya da başlangıç görselinden **yapay zekâ video klibi**, 12 sağlayıcı üzerinden: Google Veo/Omni, OpenAI Sora, OpenRouter, Runway, Luma, **Kling**, **MiniMax Hailuo**, **Wan**, Seedance, **Higgsfield** (varsayılan MiniMax H3), fal.ai, Replicate. Varsayılan kapalı, `VIDEO_PROVIDER=…` + anahtar ile açılır, birden fazlası virgülle ayrılır. Sağlayıcıda **klip başına ücretlidir**, uygulama abonelikleri genellikle geçmez ([kılavuz](docs/videodienste.md), Almanca) |
| `site_macro` | **Kendi hesabınızla MagicLight, Google Flow ve diğer siteler**: bir tarayıcı robotu (Playwright) sayfayı kullanır, videoyu bekler ve `output/` içine koyar. Varsayılan kapalı (`PCL_MACROS=1`), makroları bir kez kendiniz kaydedersiniz ([macros/README.md](macros/README.md)). Risk: kullanım koşullarına aykırı olabilir ve sayfa değişince bozulur |
| `video_ai` | fal.ai üzerinden yapay zekâ ile son işlem: videoyu **büyütme** (upscale), bir ses kaydına **dudak senkronu**, sessiz videoya **ses efektleri**. `VIDEO_AI=fal` + `FAL_KEY` ile açılır |
| `sound_generate` | bir tariften **ses efekti ya da müzik** (ElevenLabs veya fal.ai), `AUDIO_PROVIDER` ile açılır |
| `media_info` | süre, çözünürlük, kodekler |
| `download_file` | PDF, EPUB, Office, ses, video, ZIP dosyalarını internetten `downloads/` klasörüne indirir |
| `read_file` | metin, Markdown, HTML, **PDF, DOCX, EPUB** okur; uzun dosyaları da bölümler halinde |
| `view_image` | görselleri, ekran görüntülerini, haritaları, düzenleri ve taranmış PDF sayfalarını **görür** (görsel anlayışı olan bir model gerekir, ör. Claude, GPT-4o, Gemini) |

**Öz denetim:** Bir ajan PDF oluşturduğunda sunucu bunu bir görsel olarak işler (tüm sayfaların genel görünümü + 1. sayfa büyük)
ve ajana gönderir; ajan bildirmeden önce görevin her gereksinimini kontrol edip hataları düzeltmekle yükümlüdür (`PCL_SELF_CHECKS`, varsayılan 1, 0 = kapalı).

**Kendi dosyalarınız** (düzenlenecek videolar, PDF'ler, görseller, düzenler, metinler) „📁 Dateien dieses Projekts“ bölümünde yüklenir ya da
doğrudan **💬 Chat** içinde bir ajana gönderilir (📎 düğmesi, sürükleyip bırakma ya da görsel yapıştırma, birden çok birden). Dosyalar
`input/` klasörüne düşer (adı temizlenir, mevcut dosyalar asla üzerine yazılmaz, bunun yerine `name-1.png` … olur, sınır `PCL_MAX_UPLOAD_MB`);
sohbette ajan **içeriği** doğrudan mesajla birlikte alır (metinler, PDF'ler, Word metin olarak, görseller görsel olarak, model görselleri anlıyorsa;
aksi halde metin tanıma). **📂 aus input/** ile zaten orada duran dosyaları ekleyebilir ya da mesajın içine dosya adını yazabilirsiniz; „Als Auftrag erteilen“ (görev olarak ver) bunu ekibe iletir. Biten sonuçlar `output/` içinde, görseller `assets/` içinde durur. Dürüst sınırlar: `video_generate` olmadan **yapay zekâ ile video üretimi yoktur** (metinden videoya); „Animation“ o zaman şu demektir: yapay zekâ görselleriyle sahne görüntüleri + zoom/kaydırma + konuşmacı + kurgu ya da `film` ile Blender üzerinden gerçek karakter animasyonu. `video_generate` ile kısa klipler oluşur; daha uzun filmler `video_edit op=concat` ile birleştirilir. MagicLight ve Flow'un API'si yoktur: `site_macro` ile bir tarayıcı robotu bunları sizin hesabınızla kullanır, aksi halde orada üretilen videoları `input/` klasörüne yükleyin. Flow'un arkasındaki model (Veo 3.1) fal üzerinden de kullanılabilir: `FAL_VIDEO_MODEL=fal-ai/veo3.1/fast`. Raspberry Pi'de
ffmpeg yavaş çalışır (720p videonun bir dakikası birkaç dakika sürebilir), zaman sınırı `PCL_FFMPEG_TIMEOUT` (adım başına varsayılan 1 saat).

**Taranmış PDF'ler ve görseller (OCR):** `read_file` taramaları `tesseract` ile otomatik okur (`sudo apt install tesseract-ocr tesseract-ocr-deu poppler-utils`). Bu yavaştır (Pi'de sayfa başına yaklaşık 5–15 sn, sınır `PCL_OCR_MAX_PAGES`) ve hatalar içerebilir.

**İyi bir konuşmacı sesi:** `./install.sh --piper` Piper'ı Almanca bir sesle kurar; bundan sonra Almanca metinler için otomatik kullanılır (diğer diller: espeak-ng).

## Sohbet ve şablonlar

- **💬 Chat sekmesi** (ajan panelinde): her ajanla serbest sohbet; örneğin *Düşünce atölyesi*'nin başıyla felsefe yapmak,
  fikir geliştirmek ve sorgulamak için. „📋 Als Auftrag erteilen“ sohbeti ajana ve ekibine devreder; sonuç bir gönderi olarak geri gelir.
  Sohbet araçsız çalışır.
- **Şirket şablonları** (🏢): Web ajansı, Muhasebe/Mali müşavirlik, İthalat/İhracat ticareti, **Animasyon ajansı**, **Kitap yayıncılığı/İçerik ajansı**,
  **Düşünce atölyesi**, **Araştırma bürosu** (PDF'leri bulur ve okur). Kurarken patron ve çalışanlar için model seçersiniz.

## Gönderi ve Telegram

Size ait bir **üst düzey görev** (bir ajana, genellikle CEO'ya verdiğiniz görev) bittiğinde, başarısız olduğunda ya da
engellendiğinde, sizin için bir gönderi hazır olur: kenar çubuğunda „📬 Post“ ve kuruluysa bir Telegram mesajı;
tür, görev, ekip rakamları ve sonuçla. Altındaki hak ve rapor zinciri eskisi gibi işler.
Post'ta mesajları işaretleyebilir (tek tek ya da „Alle auswählen“) ve „🗑 Ausgewählte löschen“ ile silebilirsiniz;
„🧹 Postkorb leeren“ onaydan sonra hepsini siler. Yalnızca gönderi silinir, görevler, dosyalar ve geçmiş kalır.
Kenar çubuğu açılır kapanır kategorilere ayrılmıştır (Tagesgeschäft, Team & KI, Dateien & Verbindungen, Auswertung).

**Telegram'ı kurma (yaklaşık 2 dakika):**
1. Telegram'da `@BotFather` → `/newbot` → belirteci kopyalayın → `.env`: `TELEGRAM_BOT_TOKEN=…`
2. `sudo systemctl restart hyperstead`, yeni bota `/start` yazın → sohbet kimliğinizi size söyler.
3. `.env`: `TELEGRAM_CHAT_ID=…` girin, hizmeti yeniden başlatın. Web'de „Post“ altında bir test mesajı vardır.

**Telegram'da kullanım:**

| Siz yaparsınız | Sonuç |
|---|---|
| Yalnızca metin yazın | seçilen projenin patronuna yeni görev (`@Name Text` = belirli bir ajan) |
| Bir gönderi mesajına **yanıt verin** | görev, metninizi talimat olarak alıp yeniden işlenir |
| ✅ düğmesi ya da „ok“ yanıtı | görev tamamlandı olarak işaretlenir |
| Dosya, fotoğraf, albüm, video ya da sesli mesaj gönderin | seçilen projenin `input/` klasörüne düşer; resim altyazısı görev olur (bir gönderiye yanıt olarak: düzeltme için), metin yoksa dosya bir sonraki göreviniz için beklenir. Telegram botları yalnızca 20 MB'a kadar dosya indirebilir; daha büyüklerini web'den yükleyin |
| `/post`, `/status`, `/ok <No>`, `/neu <Metin>`, `/projekt [No]` | genel bakış ya da kısa komutlar |
| `/datei [arama kelimesi]` | seçili projeden size bir dosya gönderir (en yeniler düğme olarak, tek eşleşme hemen gelir; 50 MB'a kadar) |

Uygulama Telegram'ı yalnızca dışarıdan yoklar; hiçbir port açılmaz (CGNAT arkasında da çalışır). Yalnızca
`.env` içindeki sohbet kimliği komut verebilir; özel bir sohbet kullanın, grup değil. Kabuk komutları için onaylar bilerek
Telegram üzerinden **geçmez**; orada yalnızca bir uyarı gelir.

## Ajan başına haklar

- **Devretme**: görevleri *doğrudan* çalışanlara dağıtabilir (`PCL_MAX_DEPTH` seviyeye kadar, varsayılan 8).
  İsteğe bağlı olarak otomatik başlarlar; yoksa onları siz başlatırsınız.
- **Sonuçları değerlendirme**: patron işi geri bildirimle revizyona gönderebilir (çalışan başına en fazla 2 tur).
- **Okuma**: patronlar çalışanlarının raporlarını her zaman görür; bunun için ayrı bir hak gerekmez.
- **Dosya yazma**: yalnızca `workspace/<proje-kimliği>/` içinde; dışarıdaki yollar reddedilir.
- **Kod çalıştırma** (varsayılan kapalı): `run_code` bir sandbox'ta Python, JavaScript, Bash, Ruby, PHP ya da Lua başlatır, aşağıya bakın.
  Buna `rust_project` de dahildir: Rust programlarını derler, test eder ve bitmiş paket olarak teslim eder ([Rust programları](#-rust-programlarını-eksiksiz-derleme)).
- **Buluta yükleme** (varsayılan kapalı): bitmiş dosyaları GitHub, Google Drive, OneDrive'a ya da Telegram ile size gönderir, her zaman ancak sizin onayınızdan sonra ([☁️ Bulut yükleme](#️-bulut-yükleme-github-google-drive-onedrive-telegram)).
- **Kabuk önerme**: yalnızca sunucuda `PCL_ALLOW_SHELL=1` varsa ve ancak onaydan sonra.
- **Atölye** (varsayılan olarak kapalı, yalnızca `PCL_ALLOW_WERKSTATT=1` ile): proje klasöründe gerçek komutlarla çalışır ve eksik programları CEO üzerinden sizden ister ([docs/werkstatt.md](docs/werkstatt.md), Almanca). CEO bu yetkiyi başkasına veremez.
- **Duraklatma**: ajanın tüm yeni görevlerini engeller.

Haklar **sunucuda** denetlenir. Bir model yanıtına izin verilmeyen bir eylem yazarsa, bu yok sayılır ve geçmişte kaydedilir.

## Yapay zekâ sağlayıcıları ve model seçimi

Ajan başına **sağlayıcı ve model** seçersiniz (panel → Ayarlar). Uygulama model listesini sağlayıcıdan canlı olarak çeker;
**▶ Test** ile anahtarı ve modeli hemen kontrol edersiniz. Her rol için doğru modeli böyle ayarlarsınız: patronlar için en güçlüsü
(planlama, kontrol, düşünme), çalışanlar için iyi metin ya da kod modelleri, basit işler için hızlı ve ucuz olanlar.

| Sağlayıcı | `.env` içinde anahtar | Not |
|---|---|---|
| Claude (Anthropic) | `ANTHROPIC_API_KEY` | Sonnet, Haiku, Opus … ajan başına seçilebilir |
| ChatGPT (OpenAI) | `OPENAI_API_KEY` | |
| OpenRouter | `OPENROUTER_API_KEY` | yüzlerce model için tek anahtar (Claude, GPT, Gemini, DeepSeek, Qwen, Llama …) |
| Groq, Gemini, DeepSeek, Qwen | `GROQ_API_KEY`, `GEMINI_API_KEY`, … | virgülle ayrılmış birden çok anahtar = sınıra gelince döndürme |
| Mistral, NVIDIA NIM, Together, Perplexity | `MISTRAL_API_KEY`, `NVIDIA_API_KEY`, `TOGETHER_API_KEY`, `PERPLEXITY_API_KEY` | Perplexity modelleri (`sonar`) webde kendileri arar |
| Hugging Face, Cloudflare Workers AI | `HF_TOKEN` ya da `CF_ACCOUNT_ID` + `CF_API_TOKEN` | küçük ücretsiz kotalar |
| Ollama | – | Pi üzerindeki yerel modeller |
| Claude (CLI, aboneliğiniz) / ChatGPT (Codex CLI, aboneliğiniz) | – | yerleşik: `claude -p --tools "" --strict-mcp-config --no-session-persistence` (Claude kendi araçları ve bağlayıcıları olmadan, yalnızca metin; çalışma talimatı Claude Code sistem istemini değiştirir) ya da `codex exec --skip-git-repo-check --ephemeral -` (Codex kendi başına salt okunur bir sandbox'ta çalışır), model açılır listede (Claude: sonnet/opus/haiku); `PCL_ALLOW_CLI=1` ve Pi'de oturumu açılmış program gerekir |
| CLI ajanı | – | istemi stdin'den okuyan bir komut, ör. `claude -p --model sonnet`; `PCL_ALLOW_CLI=1` gerekir |

**Önemli:** ChatGPT ya da Claude'un web girişi (OAuth, „abonelik“) temiz bir API olarak kullanılamaz; web oturumlarını ele geçirmek
kullanım koşullarını ihlal eder. Yollar: sağlayıcının **API anahtarı** (kullanıma göre faturalandırılır, sohbet aboneliği değil) ya da
bir kez oturum açılmış resmî CLI ile **CLI ajanı**. Uygulamada bütçe yoktur: ücretli API'lerde ve çok araç turunda
maliyet doğabilir; belirteçleri düğümde ajan başına görürsünüz.

## Güvenlik

- İmzalı çerezli giriş sayfası (7 gün, `HttpOnly`, `SameSite=Strict`, HTTPS arkasında `Secure`).
- 5 yanlış şifreden sonra IP başına 10 dakikalık kilit; tüm denemeler denetim günlüğünde durur.
- Yazma yapan API çağrılarının kendi başlığı olmalıdır (CSRF koruması), ayrıca CSP ve diğer başlıklar.
- Kabuk ve CLI ajanları varsayılan olarak **kapalıdır**. Şifreyi bilen ve `PCL_ALLOW_SHELL=1` ayarlayan biri,
  komutları uygulama kullanıcısının haklarıyla onaylayabilir. `workspace/` çalışma dizinidir, ama **sandbox değildir**.
- `.env`, veritabanı ve çalışma klasörleri `.gitignore` içindedir. Anahtarlar asla depoya ait değildir.
- Ticaret botlarında (NEXUS) ajanlara asla insan onayı olmadan işlem yaptırmayın.

## Şirket bilgisi ve hafıza

- **🧠 Şirket bilgisi** (kenar çubuğu): bir projenin tüm ajanlarının her zaman bilmesi gerekenler (şirket, müşteriler, stil, fiyatlar, kurallar). Projenin
  `wissen/firmenwissen.md` dosyasında durur. `wissen/` içindeki tüm `.md`/`.txt` dosyaları her görevde ve sohbette yer alır (toplam
  `PCL_KNOWLEDGE_CHARS` sınırına, varsayılan 8000 karaktere kadar); oradaki diğer belgeleri (PDF, Word …) ajanlar bir liste olarak görür ve gerektiğinde okur.
- **Ajan başına hafıza**: bir ajan bir görevin sonunda en fazla 5 kalıcı bilgiyi hatırlayabilir (tercihler, kararlar, müşteriler,
  işe yarayan şeyler). Bunlar ajan panelinde „🧠 Gedächtnis“ altında görünür; değiştirebilir ya da temizleyebilirsiniz. Sınır `PCL_MEMORY_CHARS`
  (4000); en eski kayıtlar önce çıkar. Her yeni not denetim günlüğündedir.

## Hedefler, onaylar, kullanım

- **🎯 Hedefler**: proje başına hedefler ve alt hedefler. Bir görev atarken isteğe bağlı olarak hedefi seçersiniz; devredilen görevler onu devralır.
  Patronlar hedefleri ilerlemeyle birlikte istemde görür, CEO'nun kontrol turu bunu raporlar. İşaretlenmesi = ulaşıldı.
- **Önce sorun** (✋ Freigaben penceresi, proje başına, varsayılan kapalı): *En üst patronun planını onayla* yeni bir görevi,
  siz dağıtım planını onaylayana kadar bekletir; *Ekip değişikliklerini onayla* („Teamänderungen freigeben“) CEO'nun çalışan almasını, çıkarmasını ve değiştirmesini bekletir. Onaylama/reddetme Telegram düğmesiyle de yapılır.
  Reddedilen görev gönderide ❌ olarak düşer; ona yanıtınız patronun yeniden planlamasını sağlar.
  Kabuk onayları yalnızca web'de yapılır.
- **📊 Kullanım ve maliyetler**: proje, ajan ve model başına çağrılar, belirteçler ve tahmini maliyetler (bugün, 7, 30 gün). Sınır yoktur.
  Abonelik CLI'leri ve Ollama 0 $ sayılır; `PCL_ABO_WARN_5H` değerinden (varsayılan 150, 0 = kapalı) itibaren 5 saatte abonelik çağrıları için Telegram uyarısı gelir.
  Fiyatlar kabaca tahmindir; kendi fiyatlarınızı `PCL_PRICES='{"sonnet": 5}'` ile girebilirsiniz (1 milyon belirteç başına US$, model adının parçası).

## Testler

```bash
./venv/bin/pip install pytest && ./venv/bin/python -m pytest -q tests
```
İnternet ve anahtar olmadan çalışır (sağlayıcı `mock`, kendi veritabanı).

## 🔌 Bağlantılar (webhook'lar)

- **Çıkış:** 🔌 Verbindungen penceresinde adresleri girersiniz (n8n, Zapier, Make, kendi hizmetiniz; Pi'de `http://127.0.0.1:…` de dahil),
  ajanlar için bir açıklama ve isteğe bağlı başlıklarla. Gizli bilgiler `.env` içinde durur ve `${NAME}` olarak kullanılır.
  **„Darf Verbindungen nutzen“** (bağlantıları kullanabilir) hakkı olan ajanlar bunları `call_connection` aracıyla çağırır; ajan adresi
  ya da başlıkları değiştiremez, yalnızca veri gönderir. **„Nur nach meiner Freigabe“** (yalnızca benim onayımdan sonra, varsayılan açık) her çağrıyı önce ✋ Freigaben altına koyar.
  **„Bei Post benachrichtigen“** (gönderide bildir), üst düzey bir görevin her biten sonucunu JSON olarak adrese yollar. Zaman sınırı `PCL_CONN_TIMEOUT` (30 sn).
- **Giriş:** „Aufträge von außen“ (dışarıdan görevler) açılırsa `POST /hook/<proje>/<anahtar>` ile `{"text": "…", "agent": "isteğe bağlı"}` gönderilerek
  patron için bir görev kabul edilir (ör. n8n, iOS kısayollarından ya da DEXTER'dan). Giriş gerektirmez; yalnızca adresteki anahtarla korunur.
  „Neuen Schlüssel“ (yeni anahtar) eski adresi geçersiz kılar. Adrese yalnızca Hyperstead'in kendisi kadar erişilebilir (ör. yalnızca tailnet içinde).

## ☁️ Bulut yükleme (GitHub, Google Drive, OneDrive, Telegram)

- **Kurulum:** erişim bilgileri `.env` içinde (`GITHUB_UPLOAD_TOKEN` + `GITHUB_UPLOAD_REPO`, `GDRIVE_CLIENT_ID` + `GDRIVE_CLIENT_SECRET`,
  `ONEDRIVE_CLIENT_ID`), adım adım [docs/cloud.md](docs/cloud.md) içinde (Almanca). Google ve Microsoft için ardından **☁️ Cloud**
  penceresinde oturum açarsınız: bir kod gösterir, bu kodu telefonunuzda Google ya da Microsoft sayfasına girersiniz (HTTPS olmadan çalışır).
  Oturum `.env` dosyasının yanındaki `tokens/` klasöründe durur, asla veritabanında değil.
- **Hedef klasör:** ☁️ Cloud penceresinde proje ve hizmet başına (varsayılan `Hyperstead/<proje adı>`). Ajanlar yalnızca bunun altında
  bir alt klasör seçebilir, örneğin siz görevde bir klasör adı verdiğinizde.
- **Kendiniz yükleme:** 📁 Dosyalar → dosyanın yanındaki ☁️ → hedef ve klasör seçin. Bağlantıyı alırsınız.
- **Ajanlar:** **"Buluta yükleyebilir"** yetkisi (yalnızca siz verirsiniz). Araç `cloud_upload`; her yükleme ✋ Onaylar altında bekler,
  ayrıca bir Telegram mesajı gelir. Yüklemeden sonra bağlantı görevde yer alır.
- **CEO ile kurulum:** 💬 Sohbet'te en üst yöneticiye sorun, örneğin "GitHub'ı kurmama yardım et". Her hizmetin güncel durumunu ve kılavuzu bilir, sizi adım adım yönlendirir. Token'ları asla sohbete yazmazsınız, kendiniz `.env` dosyasına girersiniz.
- **Telegram:** `/datei` 50 MB'a kadar dosyaları telefonunuza gönderir, yalnızca siz tıkladığınızda ya da onayladığınızda.
- GitHub: 50 MB'a kadar repoda dosya olarak, daha büyükler `paperclip-ablage` sürümüne ek olarak (2 GB'a kadar). Google Drive: yalnızca
  Hyperstead'ın kendisinin oluşturduğu klasör ve dosyalar (`drive.file` yetkisi). OneDrive: her klasör. Yalnızca taklit hizmetlere karşı test edildi.

## 🌐 Gerçek tarayıcı ve ▶ kod çalıştırma

- **Tarayıcı** (`./install.sh --browser`, Playwright + Chromium kurar, yaklaşık 400 MB, yalnızca 64 bit sistem): „Internet recherchieren“ (internette araştırma) hakkı olan ajanlar `browse_page` aracını alır.
  Sayfa JavaScript ile çalışır; ajan görünür metni, bağlantıları ve isteğe bağlı bir ekran görüntüsünü alır (`view_image` gibi bir görsel olarak görür; `save` onu `assets/screenshots/` içine kaydeder).
  Sayfanın her isteği (betikler, çerçeveler, XHR, WebSocket'ler) genel bir adrese gitmelidir; LAN/localhost engellenir, WebRTC ve indirmeler kapalıdır.
  Aynı anda yalnızca bir tarayıcı (RAM), zaman sınırı `PCL_BROWSER_TIMEOUT` (30 sn). Kendi Chromium'unuz: `PCL_BROWSER_PATH`; kapalı: `PCL_BROWSER=0`.
- **Kod çalıştırma** (`./install.sh --run`, bubblewrap kurar): „Darf Code ausführen“ (kod çalıştırabilir, varsayılan kapalı) hakkı `run_code` aracını verir.
  Betik yalıtılmış çalışır: **internet yok**, yalnızca `/usr` ve proje klasörü görünür (`/projekt` altında salt okunur),
  `.env` yok, veritabanı yok, ev klasörü yok. Betiğin çalışma dizinine yazdığı her şey `output/run/<zaman>/` içine düşer
  (en fazla 50 dosya/50 MB). Sınırlar: `PCL_RUN_TIMEOUT` (60 sn), `PCL_RUN_MEM_MB` (1024). Sistemin Python/Node'unu çalıştırır,
  yani yalnızca apt ile kurulmuş paketler (ör. `sudo apt install python3-pandas python3-matplotlib`). Genel olarak kapatmak: `PCL_ALLOW_RUN=0`.
  Kontrol: `./venv/bin/python selftest.py run browser`.

## 🦀 Rust programlarını eksiksiz derleme

**„Darf programmieren“**, **„Darf Dateien schreiben“** ve **„Darf Code ausführen“** (programlama yapabilir, dosya yazabilir, kod çalıştırabilir) haklarına sahip bir ajana
"Bana …, testleriyle birlikte bir Rust programı yaz ve bitmiş paketi teslim et" gibi bir görev verin. Ajan işi baştan sona yapar:

1. `write_code` ile bir Cargo projesi oluşturur, ör. testleriyle (`#[test]`) `rust/rechner/Cargo.toml` ve `rust/rechner/src/main.rs`.
2. `op=test` ile `rust_project` bağımlılıkları crates.io'dan indirir, programı derler ve testleri çalıştırır.
   Hatalar dosya ve satırla geri gelir, ajan düzeltir ve yeniden test eder.
3. `op=package` bir kez daha test eder, sürüm (release) hâlini derler ve **`output/<ad>.zip`** dosyasını kaydeder. İçinde: `programm/` (bitmiş
   program), `quelle/` (`Cargo.lock` ile kaynak kod), `TESTBERICHT.txt` ve `LIESMICH.txt`. Paket yalnızca tüm testler geçerse oluşturulur.

Paketi gelen kutusunda ya da **📁 Dateien** altında (tek dosya ya da proje ZIP'inde) alırsınız. Diğer komutlar: `op=build`, `op=run` (`args`, `stdin` ile).

- **Hangi sistem için?** `programm/` içindeki program, Hyperstead'ın çalıştığı bilgisayara uyar: Pi'den bir Linux programı (ARM),
  Windows dizüstünden bir `.exe`. Başka bir sistem için `quelle/` klasöründe kendiniz `cargo build --release` çalıştırın.
- **Yalıtım (Pi/Linux):** Derleme, test ve çalıştırma `run_code` gibi bubblewrap içinde olur: internet yok, `.env` yok, ev klasörü yok,
  yalnızca projenin derleme klasörü `.rust/` yazılabilir. Yalnızca `cargo fetch` (bağımlılıkları indirir, hiçbir şey çalıştırmaz) internete erişir.
  Projedeki Cargo ayarları (`.cargo/`) ve `rust-toolchain` dosyaları kullanılmaz.
- **Windows:** bubblewrap olmadan araç kapalı kalır. `.env` içinde `PCL_CARGO_UNSAFE=1` ile dizüstü **yalıtımsız** derler: Ajanların
  kodu (testler, `build.rs`) o zaman sizin haklarınızla çalışır ve dizüstündeki dosyaları okuyabilir ya da değiştirebilir. Ortamında API anahtarlarını
  almaz. Yalnızca ajanlara ve modellerine güveniyorsanız açın.
- **Rust kurulumu:** Pi `curl https://sh.rustup.rs -sSf | sh` (`apt install cargo`'dan daha yeni), Windows `winget install Rustlang.Rustup`
  ve kurulumda "Visual Studio Build Tools (C++)" seçeneğini de alın. Ardından Hyperstead'ı yeniden başlatın ve `selftest.py rust` çalıştırın.
- **Sınırlar:** `PCL_CARGO_TIMEOUT` (adım başına 900 sn), `PCL_CARGO_MEM_MB` (3072, yalnızca Linux), `PCL_CARGO_JOBS` (2), aynı anda yalnızca
  bir Rust derlemesi. Pi'deki ilk derleme uzun sürer, sonra cargo yalnızca değişenleri yeniden derler. Bir ajanın çalışma başına `PCL_MAX_TOOL_STEPS`
  (varsayılan 6) araç turu vardır; büyük programlar için daha yüksek bir değer, ör. 12, yardımcı olur. Kapatmak: `PCL_CARGO=0`.

## 🛠 Atölye: ajanlar kendilerini donatır

**“Atölye”** yetkisiyle bir ajan, her yapay zekâ için ve her şirkette gerçek bir bilgisayardaymış gibi çalışır. Claude (abonelik CLI)
proje klasöründe kendi Claude Code araçlarını, Codex kendi araçlarını, tüm API yapay zekâları ve Ollama `befehl` aracını alır. Bir program
eksikse ajan bir **kurulum talebi** oluşturur: CEO kontrol eder, siz Telegram düğmesiyle veya ✋ Onaylar altında onaylarsınız, ardından
sunucu tam olarak bu komutu çalıştırır ve görev devam eder. Kurulanlar `wissen/werkzeuge.md` dosyasında listelenir.

- **Açma:** `.env` içine `PCL_ALLOW_WERKSTATT=1`, yeniden başlatın, ajanda kutuyu işaretleyip bir seviye seçin.
- **Seviyeler:** 1 = her komut sorar, 2 = proje içindeki işler serbest, kurulum ve silme sorar (varsayılan), 3 = her şey serbest
  (yalnızca `PCL_WERKSTATT_FREI=1` ile). Erişim bilgileri (`.env`, token’lar, anahtarlar) her zaman engellidir.
- **Dikkat:** Komutlar yalıtım olmadan sizin kullanıcı haklarınızla çalışır. Seviye 2 kurulumları biçimlerinden tanır, bir sanal alan (sandbox) değildir.
- Diğer her şey, Remotion ve sorunlar dahil: [docs/werkstatt.md](docs/werkstatt.md) (Almanca).

## Paralel çalışma

Aynı anda en fazla `PCL_WORKERS` görev çalışır (varsayılan 2, en fazla 6); örneğin bir patronun birden çok çalışanı ya da
farklı projelerin görevleri. Bir ajan asla aynı anda iki görev üzerinde çalışmaz ve aynı anda en fazla bir Ollama görevi çalışır
(Pi'deki RAM). Abonelik CLI'lerinde (Claude, Codex) paralel çağrılar abonelik sınırına daha hızlı ulaşır; bu durumda `PCL_WORKERS=1` ayarlayın.

## Bu sürümün sınırları

- Zamanlamaya göre otomatik bir heartbeat yoktur (görevler elle ya da devretmeyle başlar).
- Metinden videoya yapay zekâ yoktur, taranmış/görsel PDF'ler için OCR yoktur; CEO kendi başına yeni ajan işe almaz (organizasyon şemasını siz oluşturursunuz).
- Gerçek tarayıcı (`browse_page`) sayfaları okur ama tıklamaz ve form doldurmaz (giriş yok, satın alma yok). Anahtarsız DuckDuckGo araması sınırlı olabilir ya da değişebilir.
- Bütçe yoktur: belirteçler ve tahmini maliyetler yalnızca gösterilir (📊). Tur sınırları (revizyonlar, kontrol geçişleri, derinlik) sonsuz döngüleri önler.
- Oturumlar basit imzalı çerezlerdir; tek bir cihazın oturumu özel olarak kapatılamaz
  (şifre değiştirmek tüm oturumları geçersiz kılar).


## Selbsttest (öz test)

Kurulum ve anahtarların girilmesinden sonra `./venv/bin/python selftest.py` internet olmadan test edilemeyen her gerçek şeyi kontrol eder:
web araması, sayfa okuma, görsel araması ve görsel üretici, SSRF koruması, her yapay zekâ sağlayıcısı mini bir istekle (Ollama dahil),
Telegram (bot belirteci ve sohbet kimliğinize test mesajı), ffmpeg, sesli çıktı, Almanca karakterli PDF, OCR. Tek tek gruplar:
`selftest.py web | llm | telegram | media | ocr | rust | film`. Her satır OK, FEHLT (isteğe bağlı) ya da somut bir notla FEHLER gösterir.

## Ollama (yerel modeller)

Sağlayıcı „Ollama (lokal)“: anahtar gerekmez, model listesi doğrudan Ollama'dan gelir (`ollama pull qwen2.5:3b`). „Firma aus Vorlage“ (şablondan şirket) penceresinde
„Alles lokal“ (her şey yerel) ve „Nur Mitarbeiter lokal“ (yalnızca çalışanlar yerel) düğmeleri vardır; aksi halde Ollama'yı ajan başına seçersiniz. Ollama başka bir bilgisayarda
çalışıyorsa (ör. dizüstü) `OLLAMA_URL` değerini onun adresine ayarlayın. Küçük modeller (3B) Pi'de yavaştır ve araç protokolüne çoğu zaman zayıf uyar;
patronlar için güçlü bir model, yerel olarak daha çok basit çalışanlar ya da sohbet için uygundur.

## Claude ve ChatGPT aboneliğinizle (API anahtarı yerine CLI)

`.env` içinde: `PCL_ALLOW_CLI=1`. Programları Pi'de kendiniz kurup bir kez oturum açarsınız (üreticilerin kılavuzları:
Claude Code `claude`, OpenAI Codex `codex`; aboneliğinizle giriş). Bundan sonra „Claude (CLI, dein Abo)“ ve „ChatGPT (Codex-CLI, dein Abo)“
tüm sağlayıcı listelerinde görünür. Sunucu bunları bir kabuk olmadan, boş bir klasörde ve **ortamda API anahtarlarımız olmadan** çağırır
(aksi halde `claude` aboneliği değil API anahtarını faturalandırırdı). Sınırlar: API'den yavaştır (her yanıtta program başlatma), abonelik sınırları geçerlidir
(çok ajan = hızla sınıra), ve CLI programlarının kendi araçları vardır; gerekirse komutu `PCL_CLI_CLAUDE` / `PCL_CLI_CODEX` ile uyarlayın.

## Model gitti mi? Ajanları değiştirin

Hyperstead her 6 saatte bir (`PCL_MODEL_CHECK_HOURS`) ajanların modellerinin sağlayıcıda hâlâ var olup olmadığını kontrol eder ve bir çağrı „Modell nicht gefunden“ (model bulunamadı) bildirdiğinde de fark eder. O zaman bir Telegram mesajı gelir, görev açık bir notla başarısız olur ve **⚠ Modelle** (modeller) menüsünde etkilenen tüm ajanları tek tıkla başka bir modele çevirirsiniz.

## Büyük ekipler

Bir patronun istediği kadar çalışanı olabilir. Patronun panelinde (Ayarlar) **Unterstellte Mitarbeiter** (bağlı çalışanlar) altında onay kutularıyla hepsini seçer ve atamayı kaydedersiniz. Alternatif olarak: patronun alt noktasını bir çalışanın üzerine sürükleyin. **🗂 Ordnen** (düzenle) düğmesi her şeyi bir organizasyon şeması olarak oluşturur (6 ve üzeri çalışanlı gruplar, 5'erli sıralar halinde).

## CEO ekibini kendisi kurar

Palettedeki CEO, **„Darf sein Team selbst zusammenstellen“** (kendi ekibini kurabilir, `recruit`) hakkına sahiptir. Henüz çalışanı yoksa ve bir görev alırsa, görevi analiz eder ve rol, çalışma talimatı ve raporlama hatlarıyla çalışanlar oluşturur (20'ye kadar; kendi ekibi olan bölüm başkanları da dahil). Yeni çalışanların **henüz yapay zekâsı yoktur**: bunları **⚠ Modelle** menüsünde (hepsini birden) ya da ajan başına ayarlarda atarsınız; sonra görevin altındaki **Post**'a yanıt verirsiniz (ör. „Weiter“ = devam). Bundan sonra CEO işi her zamanki gibi dağıtır. CEO yeni çalışanlara yalnızca web, görseller, dosya okuma/yazma, medya ve programlama verebilir, asla kabuk vermez.

**Ekip zaten kurulmuş olsa bile**, bu hakka sahip bir CEO her görevde ekibini sizin görevlerinize ve koşullarınıza göre uyarlayabilir:
- **İşe alma**: ek çalışanlar, yukarıdaki gibi yapay zekâsız. Telegram mesajı alırsınız ve onlara yapay zekâ atarsınız. İş ancak bir sonraki görevden ya da sizin „Weiter“ yanıtınızdan sonra alırlar.
- **İşten çıkarma**: yalnızca altındaki çalışanlar; asla kendisi ya da ekibi dışındaki ajanlar değil. Çıkarılan kişinin çalışanları bir kademe yukarı çıkar. Hâlâ açık görevi olan biri çıkarılmaz.
- **Değiştirme**: altındaki çalışanların rolü, çalışma talimatı ve hakları (yalnızca yukarıda sayılanlar).

**Role uygun haklar**: CEO herkese tam olarak işinin gerektirdiği hakları vermelidir. Bazılarını unutursa sistem bunları ad, rol ve çalışma talimatına göre ekler, ör. araştırma → *web*, görsel/illüstrasyon/grafik/tasarım → *görseller* + *dosya yazma*, video/ses/seslendirme/PDF/mizanpaj → *medya* + *dosya yazma*, yazar/metin/redaksiyon → *dosya yazma*, programlama/web sitesi → *programlama* + *dosya yazma*. Bir çalışanın rolünü değiştirirse haklar yeniden role uygun ayarlanır. Kabuk, kod çalıştırma, bağlantılar ve yayınlama hakkını asla vermez; bunları yalnızca siz işaretlersiniz.

Her ekip değişikliğini önceden görmek istiyorsanız **Freigaben** penceresinde *Teamänderungen freigeben* (ekip değişikliklerini onayla) kutusunu işaretleyin. CEO'da bu işaret yoksa bunların hiçbirini yapamaz. Günlük görevler (zaman planı, denetim turu) ekibi asla değiştirmez.

## Çalışma saatleri ve günlük görevler

Kenar çubuğunda **🕘 Zeitplan** (zamanlama): proje başına iş başlangıcı, mesai bitişi ve çalışma günlerini belirleyin. Her çalışan için **günlük görevler** oluşturabilirsiniz (sabit saat, iş başlangıcında ya da mesai bitişinde, seçilebilir haftanın günlerinde), ör. „her gün 15:00'te web sitesini kontrol et“. Sonuç her gönderi gibi „Post“ görünümüne (ve Telegram'a) gelir. Bir zamanlamanın son görevi hâlâ çalışıyorsa tekrar başlatılmaz; saatte Pi kapalıysa 6 saate kadar telafi edilir.
İş başlangıcında şirket yarım kalan görevleri yeniden alır (başlamamış olanlar başlar, başarısız üst düzey görevler `PCL_MAX_RESUMES`=2 kereye kadar yeniden denenir). İsteğe bağlı olarak şirket çalışma saatleri dışında tamamen dinlenir. Saat Pi'nin saatidir; yanlışsa `.env` içine `PCL_TZ=Europe/Vienna` yazın.

## CEO kontrol turu

**🕘 Zeitplan** penceresinde **👑 CEO-Kontrollgang** (CEO kontrol turu) en üst patron için günlük bir kontrol turu kurar (varsayılan: mesai bitişinde; diğer saatler „Neue tägliche Aufgabe“ + *Kontrollgang* onay kutusuyla). Sistem ona olgularla bir **durum raporu** ekler: çalışan başına bugün başlayan/biten/başarısız olan/açık kalan işler, çalışma saatleri dışındaki başlangıçlar, iş başlangıcı olmayan açık görevler, yapay zekâsı olmayan çalışanlar, yarım kalan görevler ve günlük görevlerin çalışıp çalışmadığı. CEO bunu değerlendirir, gerekirse ekibine takip görevleri dağıtır ve gönderiye bir kontrol raporu yazar. „📋 Statusbericht ansehen“ (durum raporunu gör) CEO olmadan olguları gösterir.

## Proje klasörü

Her projenin `workspace/` altında **kendi adını taşıyan bir klasörü** vardır (ör. `workspace/Buchverlag-Content-Agentur/`, Almanca karakterler dönüştürülür). Proje yeniden adlandırıldığında aynı kalır ve bir proje silindiğinde **asla silinmez**. Aynı adla yeni bir proje oluşturursanız, mevcut klasörü dosyalarıyla birlikte devralır. Eski numara klasörleri (`workspace/1`, `workspace/2` …) başlangıçta otomatik olarak proje adına yeniden adlandırılır.

## Web sayfası yayınlama

**📁 Dateien dieses Projekts** penceresinde **🚀 Veröffentlichen** (yayınla) vardır. Yalnızca proje klasöründeki `www/` klasörü yayınlanır (`www/index.html`, bununla birlikte CSS, görseller … göreli yollarla); projedeki diğer her şey (notlar, `output/`, `input/`, nokta dosyaları, dışarıya simgesel bağlantılar) görünmez kalır. `www/` klasörü yoksa proje klasörünün `index.html` dosyası eskisi gibi sunulur (`input/` ve gizli dosyalar olmadan). Sayfa kendi bağlantı noktasında (8800'den itibaren, `PCL_SITE_PORT_BASE`) kalıcı olarak çalışır; varsayılan olarak yalnızca Pi'nin kendisinde: `http://127.0.0.1:8800/`. Ağdan erişim için `.env` içinde `PCL_SITE_HOST=0.0.0.0` ayarlayın. „Darf die Webseite zur Veröffentlichung vorschlagen“ (web sayfasını yayınlamayı önerebilir) hakkına sahip ajanlar „veröffentlichen“ için bir onay isteyebilir; sayfayı çevrimiçi yapan yalnızca **Freigaben** altındaki tıklamanızdır. Ajanların değişiklikleri hemen görünür; yeniden başlatmadan sonra sayfa otomatik olarak yeniden çalışır. Açık internet için önüne HTTPS'li bir ters vekil (ör. Caddy) konmalıdır; küçük sunucunun kendisi değil.
