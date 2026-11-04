# Hyperstead

🌐 Jezici: [Deutsch](README.md) · [English](README.en.md) · [Türkçe](README.tr.md) · **Srpski** · [Bosanski](README.bs.md) · [Hrvatski](README.hr.md)

Tim agenata veštačke inteligencije kao uređivač čvorova, samostalno hostovan, dovoljno lagan za Raspberry Pi.
Napravite projekat, prevucite agente na površinu, povežite ih (šef → saradnik), podesite AI provajdera, radno uputstvo i prava po čvoru i dodelite zadatke.

> Detaljna uputstva u `docs/` su trenutno napisana samo na nemačkom. Nazivi dugmadi i menija u aplikaciji ostaju na nemačkom.

## Instalacija

Hyperstead je Python program (Flask + SQLite) i radi na više sistema. Više instalacija
može raditi paralelno; svaka ima svoje firme i podatke.

| Sistem | Stanje | Uputstvo |
| --- | --- | --- |
| Raspberry Pi / Linux (Debian, Ubuntu) | glavni sistem, pun obim funkcija | dole |
| Windows 10/11 | radi, bez `run_code`, izrada Rust programa samo bez izolacije preko prekidača, neke funkcije traže dodatne programe | [docs/windows.md](docs/windows.md) |
| macOS | nije testirano, osnovne funkcije bi trebalo da rade | dole (ručno) |
| Sopstveni računar za slike (npr. stari laptop bez grafičke kartice) | besplatne slike sa referentnim slikama za Hyperstead | [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md) |

Selidba sa jednog računara na drugi: zaustavite Hyperstead i kopirajte `data.db`, folder `workspace/` i `.env`
([primer Pi → Windows](docs/windows.md)).

### Raspberry Pi / Linux

```bash
git clone https://github.com/KhungFu/hyperstead && cd hyperstead
./install.sh --service     # venv, zavisnosti, .env sa nasumičnom lozinkom, systemd servis
nano .env                  # unesite API ključeve, zatim: sudo systemctl restart hyperstead
```

Bez servisa: `./install.sh`, pa `./venv/bin/python app.py` → http://127.0.0.1:8787.
Lozinka za prijavu nalazi se u `.env` (`APP_TOKEN`). Ažuriranje, ponovno pokretanje, rezerva: [Rad](#rad-ko-šta-gde-kada-i-kako).
Više funkcija (video, OCR, kompajleri, pregledač): `./install.sh --all`.

### Windows

PowerShell u folderu Hyperstead:

```powershell
git clone https://github.com/KhungFu/hyperstead; cd hyperstead
powershell -ExecutionPolicy Bypass -File install.ps1
notepad .env
deploy\windows\hyperstead-start.bat
```

Šta nedostaje na Windowsu, automatsko pokretanje i paralelni rad sa Pi-jem: [docs/windows.md](docs/windows.md).
Kasnije ažuriranje: `git pull`, pa ponovo pokrenite.

### macOS (nije testirano)

```bash
git clone https://github.com/KhungFu/hyperstead && cd hyperstead
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
cp .env.example .env       # upišite APP_TOKEN=<dugačka lozinka>, dodajte API ključeve
./venv/bin/python app.py   # http://127.0.0.1:8787
```

`install.sh` je napravljen za Debian/Ubuntu (apt), pa na macOS-u radite ručno kao gore. Dodatni programi preko Homebrew-a
(`brew install ffmpeg tesseract poppler`). `run_code` postoji samo na Linuxu.

### Slike na sopstvenom računaru

Računar u kućnoj mreži (i bez grafičke kartice, bar 8 GB RAM-a) može za Hyperstead besplatno da pravi slike sa
referentnim slikama. U `.env` ostavite aktivne tačno ove dve linije (samo jedna `IMAGE_PROVIDER=` linija bez `#`):

```
IMAGE_PROVIDER=sdcpp
SDCPP_URL=http://<IP računara za slike>:1234    # na samom računaru za slike: http://127.0.0.1:1234
```

Podešavanje: [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md).

### Animirani filmovi uz Blender

Ako je Blender instaliran na računaru na kojem radi Hyperstead, agenti prave crtane filmove: likove sa sopstvenim glasovima i
pokretima usta, scene, kameru, titlove, gotov film sa zvukom (alat `film`, predložak firme „🐶 Animationsstudio“).
Ako Hyperstead sam ne pronađe Blender, upišite ga u `.env`:

```
BLENDER_PATH=C:\Program Files\Blender Foundation\Blender 4.2\blender.exe
```

Uputstvo i format scenarija (na nemačkom): [docs/filmstudio.md](docs/filmstudio.md).

## Rad: ko šta, gde, kada i kako

**Ko:** sve ovo radi vlasnik računara (vi), a ne agenti. Komande se izvršavaju u
folderu Hyperstead: na Pi-ju u terminalu (`cd ~/hyperstead`), na Windowsu u PowerShell-u
(`cd $HOME\hyperstead`, ili gde god ste stavili folder).

### Kratak pregled

| Šta | Kada | Raspberry Pi / Linux (sa servisom) | Windows |
| --- | --- | --- | --- |
| Pokretanje | posle instalacije, posle ponovnog pokretanja bez automatskog starta | `sudo systemctl start hyperstead` | dvoklik na `deploy\windows\hyperstead-start.bat` (prozor ostavite otvoren) |
| Zaustavljanje | pre selidbe, rezerve, ažuriranja | `sudo systemctl stop hyperstead` | zatvorite prozor za pokretanje (ili u njemu Ctrl+C) |
| Ponovno pokretanje | posle svake promene u `.env`, posle ažuriranja | `sudo systemctl restart hyperstead` | zatvorite prozor za pokretanje, ponovo pokrenite `hyperstead-start.bat` |
| Radi li? | kada ima problema | `systemctl status hyperstead` | da li je prozor za pokretanje otvoren? Pregledač: <http://127.0.0.1:8787> |
| Pregled dnevnika | kod grešaka | `journalctl -u hyperstead -f` (Ctrl+C prekida) | prikazuje se u prozoru za pokretanje |
| Ažuriranje | kada postoji nova verzija (npr. posle spojenog pull request-a) | vidi dole | vidi dole |
| Provera | posle instalacije, ažuriranja, novih ključeva | `./venv/bin/python selftest.py` | `venv\Scripts\python.exe selftest.py` |
| Ključevi / podešavanja | novi ključ, drugi provajder slika | `nano .env`, pa ponovo pokrenite | `notepad .env`, pa ponovo pokrenite |
| Rezerva | redovno, pre selidbe i većih ažuriranja | kopirajte `data.db`, `workspace/`, `.env` (prvo zaustavite) | isto u folderu Hyperstead |

### Ažuriranje (preuzimanje nove verzije)

**Raspberry Pi / Linux**, u terminalu:

```bash
cd ~/hyperstead
git pull
./install.sh               # potrebno samo ako se requirements.txt promenio; .env ostaje nepromenjen
sudo systemctl restart hyperstead
./venv/bin/python selftest.py llm     # kratka provera da li AI provajderi odgovaraju
```

**Windows**, u PowerShell-u:

1. `cd $HOME\hyperstead`
2. `git pull`
3. Samo ako su se paketi promenili (ili kada niste sigurni): `powershell -ExecutionPolicy Bypass -File install.ps1`
   (postojeći `.env` ostaje nepromenjen).
4. Zatvorite crni prozor za pokretanje Hyperstead-a.
5. Ponovo pokrenite `deploy\windows\hyperstead-start.bat` (dvoklik ili upišite u PowerShell).
6. Provera: `venv\Scripts\python.exe selftest.py llm`

Ako `git pull` javi „local changes would be overwritten“, sami ste promenili neki fajl programa.
`git stash` odlaže promenu na stranu, zatim ponovite `git pull`. Vaši podaci (`data.db`, `workspace/`, `.env`)
nikada nisu ugroženi, jer ih Git ne poznaje.

### Automatsko pokretanje

- **Pi:** `./install.sh --service` podešava servis; on se onda sam pokreće pri svakom podizanju sistema.
- **Windows:** Win+R, upišite `shell:startup` i tamo stavite prečicu do `deploy\windows\hyperstead-start.bat`
  (i do `bildrechner-start.bat`, ako ga koristite). Windows se za to mora sam prijaviti
  ([docs/windows.md](docs/windows.md), odeljak 4).

### Menjanje podešavanja u `.env`

- Svako podešavanje stoji tačno jednom, bez `#` na početku. Redovi sa `#` su isključeni. Kod dupliranih redova
  važi prvi.
- Posle svake promene ponovo pokrenite Hyperstead, inače važi stari stanje.
- Ključeve nikada ne kopirajte u četove, snimke ekrana ili repozitorijum. Ako je ključ ipak negde završio: opozovite ga kod provajdera i unesite novi.
- Zatim proverite sa `selftest.py`. Pojedinačne oblasti: `selftest.py llm`, `web`, `telegram`, `media`, `ocr`, `code`.

### Čitanje samoprovere

- **OK:** radi.
- **FEHLT (nedostaje):** opciono; red navodi komandu za dodavanje (na Windowsu komandu za Windows).
  Potrebno samo ako to vaši agenti koriste (npr. video, glasovni izlaz, skenirani PDF-ovi).
- **FEHLER (greška):** nešto što ste uneli ne radi, najčešće nevažeći ili istekao ključ ili servis koji
  ne radi (npr. računar za slike). Red navodi razlog.
- Pojedinačni timeout kod web servisa je često samo privremen: pokušajte kasnije.

### Računar za slike (ako se koristi)

- **Gde:** na računaru koji pravi slike (npr. laptop), u folderu `C:\bildrechner`.
- **Kada:** mora da radi dok agenti treba da prave slike.
- **Kako se podešava (jednom):** u PowerShell-u u folderu Hyperstead
  `powershell -ExecutionPolicy Bypass -File deploy\windows\bildrechner-einrichten.ps1` (preuzima program i modele).
- **Kako se pokreće:** pokrenite `C:\bildrechner\bildrechner-start.bat`, prozor ostavite otvoren. U `.env` fajlu Hyperstead-a
  `IMAGE_PROVIDER=sdcpp` i `SDCPP_URL=...` ([uputstvo](docs/laptop-bildrechner.md)), zatim ponovo pokrenite Hyperstead.

### Filmski studio (ako se koristi)

- **Gde:** na računaru sa Blenderom (npr. laptop). Firma sa alatom `film` mora raditi u **ovoj** instanci Hyperstead.
- **Kada:** Blender ne mora biti otvoren, Hyperstead ga za svaku scenu pokreće u pozadini i ponovo zatvara.
- **Provera:** `venv\Scripts\python.exe selftest.py film` (Windows) ili `./venv/bin/python selftest.py film`.
- **Koliko traje:** pri 640×360 i 12 sličica u sekundi, zavisno od laptopa, oko 1 do 5 minuta po 10 sekundi filma. Blender nikad ne radi istovremeno sa računarom za slike.

### Selidba (npr. Pi → laptop)

Korak po korak u [docs/windows.md](docs/windows.md), „Phase 2 – Umzug“ (na nemačkom). Ukratko: zaustavite oba, kopirajte `data.db`,
`workspace/` i `.env`, pokrenite na novom računaru i proverite, pa tek onda isključite stari.
Telegram unosite samo na jednom računaru.

### Šta se dešava kada nešto nedostaje

Ova lista se dopunjuje pri svakoj promeni programa. Svaki red kaže šta sistem radi i šta vi treba da uradite.

| Nedostaje | Šta sistem radi | Šta vi radite |
| --- | --- | --- |
| `.env` | Hyperstead se pokreće bez ključeva i bez lozinke, dostupan samo sa ovog računara. Sa `HOST=0.0.0.0` pokretanje se prekida dok je `APP_TOKEN` prazan. | `./install.sh` (Pi) odnosno `install.ps1` (Windows) ga pravi sa nasumičnom lozinkom. |
| `data.db` | Pravi se nov i prazan. Firme, zadaci i pošta su nestali. | Prvo napravite rezervu (vidi Rad). Vraćajte samo iz rezerve. |
| API ključ u `.env` | Provajder se u samoproveri prijavljuje kao FEHLT i agenti ga ne koriste. Ako je unet, ali nevažeći: FEHLER sa HTTP 401. | Unesite ključ ili isključite red sa `#`. |
| `SDCPP_URL` (uz `IMAGE_PROVIDER=sdcpp`) | Zahtevi za slike ne uspevaju uz poruku „SDCPP_URL fehlt“ (nedostaje). Uz `IMAGE_FALLBACK=pollinations` pravi se besplatna zamenska slika bez referenci, uz napomenu u rezultatu. | Dodajte red u `.env`, ponovo pokrenite Hyperstead. |
| Računar za slike nije dostupan (laptop isključen, firewall, pogrešna IP) | Kao gore: greška „Bildrechner … nicht erreichbar“ (nije dostupan), uz rezervu zamenska slika. | Uključite laptop, pokrenite `bildrechner-start.bat`, proverite IP i firewall. |
| `sd-server.exe` (Windows, računar za slike) | `bildrechner-start.bat` prikazuje „sd-server.exe fehlt“ (nedostaje) i ništa ne pokreće. | Pokrenite `deploy\windows\bildrechner-einrichten.ps1`. |
| Fajl modela (Windows, računar za slike) | Startni fajl navodi nedostajući fajl i ne pokreće se. Ako nedostaje samo veliki jezički model (`Qwen3-4B-Q4_K_M.gguf`), koristi manji, ako postoji. | Ponovo pokrenite skriptu za podešavanje; preuzima samo nedostajući fajl. |
| Windows runtime `VCOMP140.DLL` | `sd-server.exe` javlja „VCOMP140.DLL nicht gefunden“ (nije pronađen) i prekida rad. | Ponovo pokrenite skriptu za podešavanje (korak 3 instalira runtime), pa otvorite startni fajl. |
| Pravilo firewall-a za port 1234 (Windows) | Samo Pi ne može da dođe do računara za slike. Sam laptop radi dalje. | Pokrenite komandu iz [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md), odeljak 4, kao administrator. |
| Makro u `macros/` ili prijava `macros/<sajt>.json` (uz `PCL_MACROS=1`) | Bez makroa alat `site_macro` ne postoji. Bez sačuvane prijave makro staje uz napomenu. Ako MagicLight ili Flow promene stranicu, `site_macro` javlja FEHLER i stavlja `<sajt>-fehler.png` u `output/`. Samoprovera (`browser`) prikazuje FEHLT. | Makro (ponovo) snimiti prema [macros/README.md](macros/README.md). |
| `ffmpeg`, `tesseract`, `pdftoppm`, glasovni izlaz | Funkcija nedostaje. Agenti koji je traže prijavljuju grešku u rezultatu. Samoprovera prikazuje FEHLER (Pi) odnosno FEHLT (Windows). | Instalirajte program (komande u samoproveri i u [docs/windows.md](docs/windows.md)). |
| Blender (alat `film`) | `save`, `check`, `voices` i `assemble` i dalje rade. `preview` i `render` javljaju „Blender wurde nicht gefunden“ (Blender nije pronađen) uz napomenu o `BLENDER_PATH`. Samoprovera prikazuje FEHLT. | Instalirajte Blender (`winget install BlenderFoundation.Blender`) ili postavite `BLENDER_PATH` u `.env`, ponovo pokrenite. |
| `film/film.json` (scenario) | `film` javlja „film/film.json fehlt“ (nedostaje) i traži da se prvo sa `op=save` sačuva scenario. Neispravan scenario se ne čuva, odgovor navodi sve greške. | Ništa, agenti ga sami prave. Možete ga napisati i ručno ([docs/filmstudio.md](docs/filmstudio.md)). |
| Slika, muzika ili `.blend` fajl naveden u scenariju | Provera navodi scenu, lik i putanju, ništa se ne renderuje. | Stavite fajl u `assets/` ili `input/` ili ispravite putanju u scenariju. |
| Klip scene (`film/clips/`) | `assemble` navodi scene koje nedostaju i ništa ne montira. Ako se `render` prekine (vremensko ograničenje), gotove sličice ostaju sačuvane i sledeći poziv nastavlja odatle. | Ništa, agenti ponovo pozivaju `render`. |
| Govor za film | `voices`/`render` se prekidaju porukom „Keine Sprachausgabe verfügbar“ (nema govora). Scene bez dijaloga i dalje rade. | Kao kod „govora“ iznad (na Windowsu `edge-tts` + `TTS_ENGINE=edge`). |
| `cargo` (Rust, alat `rust_project`) | Alat se agentima ne prikazuje; `check_code` i dalje proverava `.rs` fajlove ako postoji `rustc`. Samoprovera (`selftest.py rust`) prikazuje FEHLT s naredbom za instalaciju. | Instalirajte Rust: Pi `curl https://sh.rustup.rs -sSf \| sh`, Windows `winget install Rustlang.Rustup`. Zatim ponovo pokrenite Hyperstead. |
| bubblewrap pri izradi Rust programa (Pi/Linux) | `rust_project` ostaje skriven, isto kao `run_code`. | `./install.sh --run` |
| `PCL_CARGO_UNSAFE=1` (Windows) | Windows nema izolaciju, zato `rust_project` bez prekidača ostaje skriven. S prekidačem laptop gradi bez izolacije. | Postavite ga samo ako znate rizik ([Rust programi](#-kompletna-izrada-rust-programa)), zatim ponovo pokrenite. |
| `Cargo.toml` u Rust folderu | `rust_project` javlja „In … fehlt Cargo.toml“ i navodi fajlove koje agent prvo mora napraviti. | Ništa, agent ih pravi pomoću `write_code`. |
| Internet za Rust zavisnosti (crates.io) | `cargo fetch` ne uspeva, ništa se ne gradi, agent dobija poruku o grešci. Već preuzete zavisnosti ostaju u `.rust/cargo-home` i rade dalje. | Proverite internet i ponovo pokrenite zadatak. |
| Položeni testovi za Rust paket | Paket se **ne** pravi („KEIN PAKET“); agent dobija greške s brojem reda i mora ih ispraviti. Bez testova paket nastaje s upozorenjem WARNUNG u rezultatu. | Ništa, agent ispravlja i ponovo gradi. Ako odustane, vratite zadatak preko šefa. |
| Folder `.rust/` u projektu (folder za izradu) | Pri sledećoj izradi pravi se ponovo, što tada traje duže (sve se ponovo preuzima i kompajlira). Skriven je i nije deo ZIP preuzimanja. | Ništa. Smete ga obrisati ako ponestane mesta. |
| Telegram token ili ID čata | Telegram ostaje isključen, sve ostalo radi. Samoprovera prikazuje FEHLT. | Potrebno samo ako želite poruke na telefonu. |
| Folder ili fajl u projektu (`wissen/`, `input/`) | Folderi koji ne postoje smatraju se praznim. Agenti rade dalje bez znanja o firmi. | Napravite ili otpremite fajl ili folder u projektu. |
| Ključ video provajdera (npr. `KLING_SECRET_KEY`, `HIGGSFIELD_API_KEY_SECRET`) | `video_generate` javlja „VIDEO_PROVIDER=…, aber … fehlt“ i ništa ne pravi; ostali provajderi sa liste rade dalje. Samoprovera prikazuje provajdera kao FEHLT. | Unesite ključ ([docs/videodienste.md](docs/videodienste.md)) ili uklonite provajdera iz `VIDEO_PROVIDER`, ponovo pokrenite. |
| Kredit kod video provajdera | Provajder odgovara greškom (često HTTP 402/429 ili „insufficient balance“), agent dobija tekst u rezultatu. Nijedan drugi provajder ne uskače. | Dopunite kredit ili izaberite drugog provajdera preko `provider` ili u `VIDEO_PROVIDER`. |
| `FAL_KEY` (uz `VIDEO_PROVIDER=fal`, `VIDEO_AI=fal` ili `AUDIO_PROVIDER=fal`) | `video_generate`, `video_ai` odnosno `sound_generate` javlja „FAL_KEY fehlt“ i ništa ne pravi. | Unesite ključ sa fal.ai ili uklonite red `VIDEO_AI`/`AUDIO_PROVIDER`. |
| `ELEVENLABS_API_KEY` (bolji glasovi po potrebi) | Sve radi kao ranije sa lokalnim glasovima. Ako se ipak koristi `engine: elevenlabs` ili `TTS_ENGINE=elevenlabs`, ili ElevenLabs/OpenAI ne uspe (ključ, kredit, internet), govori lokalni glas, a rezultat počinje sa „HINWEIS: … nicht genutzt“ i razlogom. U filmu se red pri sledećem `voices` ponovo pokuša sa cloud glasom. Sa `TTS_FALLBACK=0` zadatak se umesto toga prekida. | Ključ sa elevenlabs.io upisati u `.env` i ponovo pokrenuti. Uputstvo: 📖 → „🎙 Stimmen und ElevenLabs“. |
| AI saradnika kog je CEO tek zaposlio | Novi saradnik se pravi, ali ne dobija zadatke. Ako CEO posle toga ponovo planira, zadatak se prekida sa „Diesen Mitarbeitern ist noch keine KI zugewiesen: …“ (još nije dodeljen AI). U meniju **⚠ Modelle** stoji kao „Noch keine KI“. | Dodelite AI u meniju ⚠ Modelle i odgovorite „Weiter“ u pošti. |
| Prava saradnika kog je zaposlio CEO | Sistem dodaje prava koja nedostaju na osnovu uloge (lista gore). Ako se nijedna ključna reč ne poklapa, dobija samo *čitanje fajlova* i može da odgovori samo tekstom. | Štiklirajte prava u panelu agenta ili CEO-u preciznije zadajte ulogu. |
| Saradnik kog CEO želi da otpusti ili izmeni | Ako tog imena nema u njegovom timu (greška u kucanju, drugi tim, već otpušten), uputstvo se preskače i beleži u rezultatu. Ako saradnik još ima otvoren zadatak, ostaje. | Ništa, ili kasnije ponovo zadajte. |
| `video_providers.py` (programski fajl) | Alati za video, zvuk i cloud glasove nestaju za agente, sve ostalo radi dalje. | Ponovo pokrenite `git pull`, fajl je deo programa. |
| `GITHUB_UPLOAD_TOKEN` ili `GITHUB_UPLOAD_REPO` | GitHub se pod ☁️ Cloud prikazuje kao „nije podešeno”, agentima se ne nudi kao cilj. Sve ostalo radi. | Unesite token i repo ([docs/cloud.md](docs/cloud.md), na nemačkom), ponovo pokrenite. |
| `GDRIVE_CLIENT_ID`/`GDRIVE_CLIENT_SECRET` ili `ONEDRIVE_CLIENT_ID` | Servis ostaje „nije podešeno”, dugme „Prijava” ne postoji. | Registrujte aplikaciju i unesite redove ([docs/cloud.md](docs/cloud.md)), ponovo pokrenite. |
| Prijava kod Google-a/Microsoft-a (folder `tokens/`) | Servis stoji na „nije prijavljeno”. Otpremanje javlja „još niste prijavljeni” odnosno „prijava je istekla” i ništa ne otprema. | ☁️ Cloud → Prijava. Pri selidbi sa Pi-ja na laptop jednostavno se ponovo prijavite na laptopu. |
| Fajl veći od 50 MB za Telegram | Telegram ga ne prima. `/datei` ga označava sa ⚠️ i ne šalje ga, agent dobija napomenu. | Kao cilj izaberite Google Drive, OneDrive ili GitHub. |
| `cloud_upload.py` (programski fajl) | Hyperstead se ne pokreće (greška pri uvozu). | Ponovo pokrenite `git pull`, fajl je deo programa. |
| `PCL_ALLOW_WERKSTATT=1` | Polje „Radionica“ je sivo, nijedan agent ne dobija `befehl` ni `nachruesten`. Sve ostalo radi kao i ranije. | Dodajte red u `.env`, ponovo pokrenite, označite polje kod agenta ([docs/werkstatt.md](docs/werkstatt.md)). |
| Program koji je agentu potreban (npr. Node.js, Remotion, Python paket) | Agent sa radionicom podnosi zahtev za dopunu: CEO ga proverava, vi dobijate ✅/❌ preko Telegrama i pod ✋ Odobrenja. Posle vašeg „da“ server instalira i zadatak se nastavlja. Bez radionice agent samo navodi šta nedostaje. | Pročitajte zahtev i odlučite. Bez Telegrama samo preko veba. |
| AI CEO-a (kod zahteva za dopunu) | Zahtev stiže direktno vama uz napomenu „Nema CEO-a sa AI“ ili „CEO nije dostupan“. | Odlučite sami ili dodelite CEO-u AI. |
| `werkstatt.py` (programski fajl) | Hyperstead se ne pokreće (greška pri uvozu). | Ponovo pokrenite `git pull`, fajl je deo programa. |
| `growth.py` (programski fajl) | Hyperstead se ne pokreće (greška pri uvozu). | Ponovo pokrenite `git pull`, fajl je deo programa. |
| Raniji svet (Ceh, Tycoon, Gizmo grad) sačuvan u projektu | Projekat automatski prikazuje svemir. Poeni, nivo i rangovi ostaju isti, menjaju se samo nazivi i ikone. | Ništa ne treba raditi. |
| Danas nema poziva veštačke inteligencije (operativni centar, 💶 u traci) | Prikazuje 0 $ odnosno „keine Aufrufe“. | Ništa ne treba raditi. Troškovi su procene, sopstvene cene preko `PCL_PRICES` u `.env`. |
| Pregledač ništa ne čuva (privatni prozor) | Svetlo/tamno, prikaz (svemir/organigram/nacrt), vrsta organigrama, pokreti i režim pomoći se pri svakom učitavanju vraćaju na podrazumevano. | Koristite običan prozor; podaci projekata nisu pogođeni. |

## Pristup sa interneta

Aplikacija namerno sluša samo na `127.0.0.1`. Umesto otvaranja porta koristite tunel.
Ovo je potrebno i ako vaš mobilni ruter ne dozvoljava dolazne veze (CGNAT).

### Opcija A (preporučeno): Tailscale, privatno, samo za vaše uređaje

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up                    # otvorite link za prijavu u pregledaču
sudo tailscale serve --bg 8787       # HTTPS adresa samo u sopstvenom tailnet-u
```

Instalirajte Tailscale i na telefon/laptop, pa otvorite prikazanu adresu `https://dexter….ts.net`.
U `.env` dodajte: `TRUST_PROXY=1`, zatim ponovo pokrenite servis.
**Ne** koristite `tailscale funnel`, to bi aplikaciju stavilo na javni internet.

### Opcija B: Cloudflare Tunnel, javna adresa sa sopstvenim domenom

```bash
# instalirajte cloudflared (vidi developers.cloudflare.com/cloudflare-one/connections/connect-networks)
cloudflared tunnel login
cloudflared tunnel create hyperstead
cloudflared tunnel route dns hyperstead agents.vas-domen.de
# ~/.cloudflared/config.yml:  ingress: - hostname: agents.vas-domen.de  service: http://127.0.0.1:8787
cloudflared tunnel run hyperstead
```

Dodatno se snažno preporučuje: stavite ispred **Cloudflare Access** (prijava e-poštom).
U `.env`: `TRUST_PROXY=1`. Komande se mogu menjati; u sumnji važi zvanično uputstvo.

Sa `TRUST_PROXY=1` aplikacija se pokreće samo ako `APP_TOKEN` ima najmanje 12 znakova.

## Rukovanje

| Radnja | Kako se radi |
|---|---|
| Napravite agenta | prevucite stavku iz palete na površinu (ili kliknite na nju) |
| Povežite | prevucite donju tačku čvora na drugi čvor (= šef → saradnik) |
| Prekinite vezu | kliknite na liniju veze |
| Pomeranje | prevucite čvor; prevlačenje pozadine = pomeranje prikaza; točkić miša = zumiranje |
| Podešavanje | kliknite čvor → panel desno |
| Dodelite zadatak | panel → kartica „Aufgaben“ (zadaci) |
| Odobravanje | bočna traka „Freigaben“ (odobrenja) |

## Kako firma radi

Šef dobija zadatak i **planira** (raspoređuje podzadatke) ili ga sam obavlja. Čim su svi
saradnici gotovi, on se ponovo budi, **čita njihove izveštaje**, vraća nedostatke uz povratnu informaciju ili
sažima sve i izveštava svog šefa. Tako se rezultat penje kroz koliko god nivoa.
Status „Wartet auf Team“ (čeka tim) znači: šef čeka svoje ljude. U kartici zadataka vidite celo stablo.

## Svemir i rast

Svaki projekat je mali **univerzum** koji raste sa svojim uspesima. Svemir menja samo reči, ikone i boje
interfejsa. Agenti uvek rade sa jasnim pojmovima (zadatak, izveštaj, tim), tako da njihov kvalitet ostaje isti.

| U svemiru | Značenje u timu |
| --- | --- |
| ☀️ Sunce | najviše rukovodstvo (npr. CEO) |
| 🪐 Planeta | odeljenje ili poslovođa, kruži oko Sunca |
| 🌙 Mesec | zaposleni, kruži oko svoje planete (ko je još niže, mali je mesec meseca) |
| Nivoi | ☄️ Asteroid → 🪐 Planeta → ☀️ Sunčev sistem → ✨ Zvezdano jato → 🌌 Galaksija |
| Rangovi agenata | ☄️ Kometa → 🌙 Mesec → 🪐 Planeta → ⭐ Zvezda |

Poeni se zovu zvezdana prašina, zadaci se zovu misije. Raniji svetovi Ceh, Tycoon i Gizmo grad više ne postoje; postojeći projekti automatski prikazuju svemir, poeni i nivoi ostaju sačuvani. Interfejs prikazuje nazive na nemačkom.

**Upotreba:** Traka iznad površine prikazuje nivo, napredak do sledećeg nivoa i najvažnije brojeve. Desno prebacujete između svetlog i tamnog prikaza (🌓) i sa ⓘ otvarate pregled nivoa, poena i rangova. Rang svakog agenta je prikazan kao ikona na njegovoj kartici.

**Sunčev sistem:** Sa 🌌 / 📐 u traci prelazite između svemira i nacrta (uređivač čvorova). Planete i meseci polako kruže; kada mišem pokažete na jedan od njih, sve se zaustavi da biste ga lako pogodili. Plavi prsten koji pulsira znači "radi", žuti prsten "čeka vaše odobrenje", crveni prsten "greška", ljubičasti isprekidani prsten "čeka svoj tim". Dodir na Sunce ili planetu prikazuje tim i radnje, dodir na mesec otvara agenta. Sa svakim nivoom nebo je punije, od zvezdanog jata svetle magline, a kao galaksija pojavljuje se spirala. Svemir ostaje taman i u svetlom prikazu. Na telefonu se umesto mape prikazuje lista: Sunce, ispod njega svaka planeta sa svojim mesecima. Pokreti se isključuju kada uređaj traži „smanji pokrete“.

**Organigram:** 🏢 u traci prikazuje tim kao organigram u tri vrste, koje se menjaju gore u sredini: ⬇ Baum (stablo odozgo nadole, zaposleni bez sopstvenog tima stoje jedan ispod drugog), ➡ Gliederung (jedan red po agentu, uvučeno po nivou, najbolje za telefon) i ◎ Kreis (krug, rukovodstvo u sredini, svaki nivo jedan prsten). Boja pokazuje stanje: zeleno spremno, plavo radi, žuto čeka vaše odobrenje, crveno greška, ljubičasto čeka tim, sivo pauzirano. Dodir otvara agenta; uređaj pamti izabranu vrstu.

**Operativni centar:** 🛰 u bočnoj traci (ili dodir na brojeve u traci rasta) na prvi pogled prikazuje šta trenutno radi i čeka, koja odobrenja su otvorena, šta nije uspelo u poslednjih 7 dana (sa ↻ Neu), rasporede (sa ▶ Jetzt), poruke o greškama i poslednje događaje. Uz to prikazuje procenjene troškove veštačke inteligencije za danas i poslednjih 7 dana; današnji trošak stoji i kao 💶 u traci. Svi brojevi dolaze iz postojećih zadataka, odobrenja, rasporeda i istorije, ništa nije izmišljeno.

**Napredovanje i rukovanje:** Kada projekat dostigne novi stepen, pojavi se kratka proslava sa novim stepenom i sledećim ciljem (Telegram šalje istu poruku). Kada agent napreduje u rangu, pojavi se kratko obaveštenje. Pod ⓘ u traci možete za ovaj uređaj isključiti pokrete i efekte proslave; ako uređaj traži „smanji pokrete“, sve ionako ostaje mirno. Svi prozori se zatvaraju tasterom Esc, Sunce, planete i meseci u svemiru mogu se koristiti tasterima Tab i Enter.

**Uputstvo i pomoć:** 📖 Anleitung na vrhu bočne trake otvara uputstvo za upotrebu direktno u kontrolnoj tabli (poglavlja na rasklapanje, sa pretragom, bez preuzimanja, radi i oflajn). ⓘ na vrhu prozora vodi do odgovarajućeg poglavlja. Svako dugme pokazuje kratko objašnjenje kada pokažete mišem na njega. Na telefonu u uputstvu uključite režim pomoći: prvi dodir dugmeta ga objašnjava, drugi ga izvršava.

**Poeni:** isporuka prihvaćena iz prve +10, posle ispravke +5, zadatak označen kao završen u pošti +20,
neuspešno −3, zatražena dorada −5. Nivoi od 0 / 100 / 300 / 700 / 1500 poena. Postojeći projekti automatski
dobijaju svoje dosadašnje uspehe. Prelazak na viši nivo se jednom javlja preko Telegrama.

**Šta nivo ograničava:** samo koliko agenata rukovodstvo sme **samo** da zaposli (8 / 12 / 18 / 25 / neograničeno
u projektu) i koliko duboko (2 / 3 / 4 / 5 / puna dubina). Vi uvek možete sve da napravite sami. Ograničenje može da se
isključi po projektu.

**Rangovi agenata** prema sopstvenim prihvaćenim isporukama: od 0 / 5 / 20 / 60 (npr. šegrt, kalfa, majstor, veliki majstor).

## Mogućnosti agenata (internet, slike, fajlovi)

Agenti rade u krugovima: traže alate, server ih izvršava i vraća rezultate, sve dok nisu
gotovi (najviše `PCL_MAX_TOOL_STEPS`). Prava po agentu: **pretraga interneta**, **slike**, **čitanje fajlova projekta**
(i, kao ranije, pisanje fajlova).

| Alat | Šta radi | Bez ključa |
|---|---|---|
| `web_search` | pretraga weba (zakoni, cene, konkurencija …) | DuckDuckGo; bolje: `SEARXNG_URL`, `BRAVE_API_KEY` ili `TAVILY_API_KEY` |
| `fetch_url` | čita web stranicu kao tekst | da |
| `browse_page` | otvara stranicu u pravom pregledaču (JavaScript radi), opciono sa snimkom ekrana koju agent vidi kao sliku | da, treba `./install.sh --browser` |
| `image_search` / `image_save` | traži slobodno licencirane fotografije i čuva ih u `assets/`, sa autorom i licencom | Openverse; opciono `PEXELS_API_KEY` |
| `image_generate` | pravi AI sliku kao PNG, opciono sa do 4 referentne slike iz projekta (isti likovi i stil kroz seriju), format kvadrat/vertikalno/horizontalno i ciljna putanja u `assets/`, `output/` ili `karten/`. Pravo **Slike** ili **Mediji** | Pollinations (bez ključa: bez referentnih slika; sa `POLLINATIONS_API_KEY` i Pollen kreditom: model preko `POLLINATIONS_MODEL`, sa referentnim slikama); `IMAGE_STYLE` postavlja fiksni stil crtanja; ostali: `nvidia` (FLUX preko build.nvidia.com), `cloudflare` (Workers AI, FLUX.2 klein sa referentnim slikama), `hf` (Hugging Face), model svakog preko `IMAGE_MODEL`; besplatno sa referentnim slikama na sopstvenom računaru: `IMAGE_PROVIDER=sdcpp` ([uputstvo](docs/laptop-bildrechner.md)); bolje `IMAGE_PROVIDER=openai` sa `OPENAI_API_KEY`, `gemini`, ili `openrouter` sa `OPENROUTER_API_KEY` |
| `list_files` / `read_file` | čita fajlove u folderu projekta (npr. tekstove kolega) | da |

Sve što se napravi nalazi se pod `workspace/<id-projekta>/`. U bočnoj traci **📁 Dateien** prikazuje fajlove, otvara `index.html`
kao web stranicu (izolovan sandbox) i preuzima sve kao ZIP. Link sadrži tajni ključ.

**Šabloni firmi** (🏢 pored „Projekte“): *Web agencija*, *Računovodstvo/poreska kancelarija*, *Uvoz/izvoz trgovina* prave projekat,
organigram, radna uputstva i prava u potpunosti. Sopstvene firme: napišite cilj projekta („vi ste …“, zemlja,
delatnost), podesite agente i prava. Agenti dobijaju datum i cilj projekta i treba da prvo istraže stvari koje se menjaju (zakoni,
cene) i navedu izvore.

**Bezbednost alata:** preuzimanje stranica ograničeno je na javne adrese (bez localhost-a, LAN-a, Tailscale-a,
metapodataka iz clouda; preusmeravanja se proveravaju pojedinačno). Za agente sadržaj weba važi kao nepouzdan podatak,
ali pripremljena stranica ipak može uticati na model: ne dajte agentima sa pristupom internetu shell i proveravajte rezultate.
Agenti namerno **nemaju** alate za kupovine, narudžbine, plaćanja ili slanje e-pošte; daju nacrte i preporuke.
Licence za slike (CC) često traže navođenje autora; urednik slika to upisuje u `bildnachweis.md`.

## Mediji, dokumenti i sopstveni fajlovi

Uz pravo **pravljenje medija i dokumenata** (i `ffmpeg`/fontovi na Pi-ju, vidi `install.sh`):

| Alat | Šta može |
|---|---|
| `video_edit` | seče video (`trim`), spaja (`concat`), **animaciju slajd-šou sa zumom** iz slika (`slideshow`, opciono sa zvukom), dodaje tekst/titlove/logo, menja ili meša zvuk, menja brzinu, pretvara u GIF/WebM/MP3, izvlači nepomičan kadar |
| `speak` | pretvara tekst u glas govornika (espeak-ng offline; bolje: Piper; opciono Edge glasovi ili cloud glasovi ElevenLabs/OpenAI preko `TTS_ENGINE`), uz `voice`, `pitch`, `rate` za različite glasove |
| `film` | **animirani film uz Blender**: scenario kao JSON, likovi (pas, mačka, zec, medved, miš, čovek, sopstvene slike ili `.blend` likovi), glasovi sa pokretima usta, pokreti, kamera, slika pregleda, renderovanje scenu po scenu, montaža sa titlovima ([uputstvo](docs/filmstudio.md)) |
| `write_file` | uz pravo **pisanje fajlova**: odmah pravi poglavlja, HTML, CSV itd., tako da se u istom zadatku od njih može napraviti PDF/DOCX/EPUB |
| `make_document` | iz Markdown poglavlja **PDF, DOCX, EPUB ili HTML** (A4/A5, naslovna strana, slike, dijakritici i turski znakovi); sa `html` PDF slobodnog rasporeda iz **HTML+CSS** (pravljenje šablona, preko WeasyPrint-a, učitava samo fajlove iz projekta) |
| `video_generate` | **AI video klip** iz teksta ili početne slike preko 12 provajdera: Google Veo/Omni, OpenAI Sora, OpenRouter, Runway, Luma, **Kling**, **MiniMax Hailuo**, **Wan**, Seedance, **Higgsfield** (podrazumevano MiniMax H3), fal.ai, Replicate. Podrazumevano isključeno, uključuje se sa `VIDEO_PROVIDER=…` + ključ, više njih odvojenih zarezom. **Naplaćuje se po klipu** kod provajdera, pretplate na aplikacije se uglavnom ne računaju ([uputstvo](docs/videodienste.md), na nemačkom) |
| `site_macro` | **MagicLight, Google Flow i druge stranice sa vašim nalogom**: robot u pregledaču (Playwright) koristi stranicu, čeka video i stavlja ga u `output/`. Podrazumevano isključeno (`PCL_MACROS=1`), makroe jednom sami snimite ([macros/README.md](macros/README.md)). Rizik: može kršiti uslove korišćenja i prestaje raditi kad se stranica promeni |
| `video_ai` | AI obrada preko fal.ai: **povećanje rezolucije** videa, **sinhronizacija usana** sa snimkom glasa, **zvučni efekti** za nemi video. Uključuje se sa `VIDEO_AI=fal` + `FAL_KEY` |
| `sound_generate` | **zvučni efekti ili muzika** iz opisa (ElevenLabs ili fal.ai), uključuje se sa `AUDIO_PROVIDER` |
| `media_info` | trajanje, rezolucija, kodeci |
| `download_file` | preuzima PDF, EPUB, Office, audio, video, ZIP sa interneta u `downloads/` |
| `read_file` | čita tekst, Markdown, HTML, **PDF, DOCX, EPUB**, i duge fajlove po delovima |
| `view_image` | **vidi** slike, snimke ekrana, mape, rasporede i stranice skeniranih PDF-ova (treba model sa razumevanjem slika, npr. Claude, GPT-4o, Gemini) |

**Samokontrola:** kada agent napravi PDF, server ga posle toga prikaže kao sliku (pregled svih stranica + 1. stranica uvećano) i pošalje
mu uz obavezu da proveri svaki zahtev zadatka i ispravi greške pre nego što javi (`PCL_SELF_CHECKS`, podrazumevano 1, 0 = isključeno).

**Sopstveni fajlovi** (video za obradu, PDF-ovi, slike, rasporedi, tekstovi) otpremate u „📁 Dateien dieses Projekts“ ili ih šaljete
direktno u **💬 Chat** sa agentom (dugme 📎, prevucite ih ili nalepite sliku, više odjednom). Završe u
`input/` (ime se čisti, postojeći fajlovi se nikada ne prepisuju nego postaju `name-1.png` …, granica `PCL_MAX_UPLOAD_MB`);
u četu agent dobija **sadržaj** direktno uz poruku (tekstovi, PDF-ovi, Word kao tekst, slike kao slike, ako model razume slike;
inače prepoznavanje teksta). Sa **📂 aus input/** dodajete fajlove koji već stoje tamo, ili jednostavno upišete ime fajla u poruku, a „Als Auftrag erteilen“ (pošalji kao zadatak) to prosleđuje timu; gotovi rezultati su u `output/`, slike u `assets/`. Iskrena ograničenja: bez `video_generate` **nema AI generisanja videa** (tekst u video);
„animacija“ tada znači: scene kao slike uz AI slike + zum/pomeranje + govornik + montaža, ili prava animacija likova uz Blender preko alata `film`. Uz `video_generate` nastaju
kratki klipovi; duži filmovi se sastavljaju sa `video_edit op=concat`. MagicLight i Flow nemaju API: sa `site_macro` robot u pregledaču ih koristi sa vašim nalogom, inače videe napravljene tamo otpremite u `input/`. Model iza Flow-a (Veo 3.1) dostupan je i preko fal: `FAL_VIDEO_MODEL=fal-ai/veo3.1/fast`. Na Raspberry Pi-ju
ffmpeg radi sporo (jedan minut 720p videa može trajati nekoliko minuta), vremensko ograničenje `PCL_FFMPEG_TIMEOUT` (podrazumevano 1 sat po koraku).

**Skenirani PDF-ovi i slike (OCR):** `read_file` automatski čita skenove preko `tesseract` (`sudo apt install tesseract-ocr tesseract-ocr-deu poppler-utils`). To je sporo (oko 5–15 s po stranici na Pi-ju, granica `PCL_OCR_MAX_PAGES`) i može sadržati greške.

**Dobar glas govornika:** `./install.sh --piper` podešava Piper sa nemačkim glasom; posle toga se automatski koristi za nemačke tekstove (ostali jezici: espeak-ng).

## Čet i šabloni

- **💬 Chat kartica** (u panelu agenta): slobodan razgovor sa svakim agentom, npr. sa vođom *Gedankenwerkstatt*-a, za filozofiranje,
  razvijanje ideja i preispitivanje. „📋 Als Auftrag erteilen“ prosleđuje razgovor agentu i njegovom timu; rezultat se vraća kao objava.
  Čet radi bez alata.
- **Šabloni firmi** (🏢): Web agencija, Računovodstvo/poreska kancelarija, Uvoz/izvoz trgovina, **Animaciona agencija**, **Izdavačka kuća/agencija sadržaja**,
  **Radionica ideja**, **Istraživački biro** (pronalazi i čita PDF-ove). Pri osnivanju birate model za vođu i saradnike.

## Pošta i Telegram

Čim je **zadatak na vrhu** (onaj koji ste dali agentu, obično CEO-u) gotov, neuspešan ili
blokiran, pošta je spremna za vas: u bočnoj traci „📬 Post“ i, ako je podešeno, poruka na Telegramu sa
vrstom, zadatkom, brojevima tima i rezultatom. Lanac prava i izveštaja ispod radi kao i ranije.
U pošti možete označiti poruke (pojedinačno ili „Alle auswählen“) i ukloniti ih sa „🗑 Ausgewählte löschen“;
„🧹 Postkorb leeren“ nakon potvrde briše sve. Briše se samo pošta, zadaci, datoteke i istorija ostaju.
Bočna traka je podijeljena u kategorije koje se otvaraju i zatvaraju (Tagesgeschäft, Team & KI, Dateien & Verbindungen, Auswertung).

**Podešavanje Telegrama (oko 2 minuta):**
1. U Telegramu `@BotFather` → `/newbot` → kopirajte token → `.env`: `TELEGRAM_BOT_TOKEN=…`
2. `sudo systemctl restart hyperstead`, novom botu pošaljite `/start` → on vam kaže vaš ID čata.
3. `.env`: upišite `TELEGRAM_CHAT_ID=…`, ponovo pokrenite servis. Na webu pod „Post“ postoji probna poruka.

**Rad u Telegramu:**

| Vi radite | Rezultat |
|---|---|
| Samo napišete tekst | novi zadatak šefu izabranog projekta (`@Ime Tekst` = određeni agent) |
| **Odgovorite** na poruku pošte | zadatak se ponovo obrađuje sa vašim tekstom kao uputstvom |
| Dugme ✅ ili odgovor „ok“ | zadatak se označava kao završen |
| Pošaljete fajl, fotografiju, album, video ili glasovnu poruku | završi u `input/` izabranog projekta; natpis postaje zadatak (kao odgovor na objavu: za doradu), bez teksta fajl ide vašem sledećem zadatku. Telegram botovi smeju da preuzmu fajlove do 20 MB, veće otpremite preko weba |
| `/post`, `/status`, `/ok <Br.>`, `/neu <Tekst>`, `/projekt [Br.]` | pregled odnosno kratke komande |
| `/datei [reč za pretragu]` | šalje vam fajl iz izabranog projekta (najnoviji kao dugmad, jedini pogodak stiže odmah; do 50 MB) |

Aplikacija Telegram samo pita spolja, ne otvara se nijedan port (radi i iza CGNAT-a). Samo ID čata iz
`.env` sme da daje komande; koristite privatan čet, ne grupu. Odobrenja za shell komande namerno
**ne** idu preko Telegrama; tamo stiže samo napomena.

## Prava po agentu

- **Delegiranje**: sme da dodeljuje zadatke *neposrednim* saradnicima (do `PCL_MAX_DEPTH` nivoa, podrazumevano 8).
  Opciono se sami pokreću, inače ih pokrećete sami.
- **Ocenjivanje rezultata**: šef sme da vrati posao sa povratnom informacijom na doradu (najviše 2 kruga po saradniku).
- **Čitanje**: šefovi uvek vide izveštaje svojih saradnika; za to nije potrebno posebno pravo.
- **Pisanje fajlova**: samo u `workspace/<id-projekta>/`; putanje van toga se odbijaju.
- **Pokretanje koda** (podrazumevano isključeno): `run_code` pokreće Python, JavaScript, Bash, Ruby, PHP ili Lua u sandbox-u, vidi dole.
  Tu spada i `rust_project`: gradi i testira Rust programe i isporučuje gotov paket ([Rust programi](#-kompletna-izrada-rust-programa)).
- **Otpremanje u cloud** (podrazumevano isključeno): gotove fajlove na GitHub, Google Drive, OneDrive ili vama preko Telegrama, uvek tek posle vašeg odobrenja ([☁️ Otpremanje u cloud](#️-otpremanje-u-cloud-github-google-drive-onedrive-telegram)).
- **Predlaganje shell-a**: samo ako server ima `PCL_ALLOW_SHELL=1`, i tada uvek tek posle odobrenja.
- **Radionica** (podrazumevano isključena, samo uz `PCL_ALLOW_WERKSTATT=1`): radi sa pravim komandama u folderu projekta i preko CEO-a traži od vas programe koji nedostaju ([docs/werkstatt.md](docs/werkstatt.md), na nemačkom). CEO ovo pravo ne može da prenese dalje.
- **Pauza**: blokira sve nove zadatke agenta.

Prava se proveravaju **na serveru**. Ako model u svom odgovoru napiše nedozvoljenu radnju, ona se ignoriše i beleži u istoriji.

## Dobavljači AI-ja i izbor modela

Za svakog agenta birate **dobavljača i model** (panel → Podešavanja). Aplikacija modele uživo preuzima od dobavljača;
sa **▶ Test** odmah proveravate ključ i model. Tako postavljate odgovarajući model po ulozi: najjači za šefove
(planiranje, provera, razmišljanje), dobri modeli za tekst ili kod za saradnike, brzi i jeftini za jednostavan posao.

| Dobavljač | Ključ u `.env` | Napomena |
|---|---|---|
| Claude (Anthropic) | `ANTHROPIC_API_KEY` | Sonnet, Haiku, Opus … bira se po agentu |
| ChatGPT (OpenAI) | `OPENAI_API_KEY` | |
| OpenRouter | `OPENROUTER_API_KEY` | jedan ključ za stotine modela (Claude, GPT, Gemini, DeepSeek, Qwen, Llama …) |
| Groq, Gemini, DeepSeek, Qwen | `GROQ_API_KEY`, `GEMINI_API_KEY`, … | više ključeva odvojenih zarezom = rotacija kada se dostigne limit |
| Mistral, NVIDIA NIM, Together, Perplexity | `MISTRAL_API_KEY`, `NVIDIA_API_KEY`, `TOGETHER_API_KEY`, `PERPLEXITY_API_KEY` | Perplexity modeli (`sonar`) sami pretražuju web |
| Hugging Face, Cloudflare Workers AI | `HF_TOKEN` odnosno `CF_ACCOUNT_ID` + `CF_API_TOKEN` | male besplatne kvote |
| Ollama | – | lokalni modeli na Pi-ju |
| Claude (CLI, vaša pretplata) / ChatGPT (Codex CLI, vaša pretplata) | – | ugrađeno: `claude -p --tools "" --strict-mcp-config --no-session-persistence` (Claude bez sopstvenih alata i konektora, samo tekst; radno uputstvo zamenjuje sistemski prompt Claude Code-a) odnosno `codex exec --skip-git-repo-check --ephemeral -` (Codex sam radi u sandbox-u samo za čitanje), model u padajućem meniju (Claude: sonnet/opus/haiku); treba `PCL_ALLOW_CLI=1` i prijavljen program na Pi-ju |
| CLI agent | – | komanda koja čita prompt sa stdin-a, npr. `claude -p --model sonnet`; treba `PCL_ALLOW_CLI=1` |

**Važno:** web prijava (OAuth, „pretplata“) kod ChatGPT-a ili Claude-a ne može se čisto koristiti kao API; preuzimanje
web sesija krši uslove korišćenja. Putevi: **API ključ** dobavljača (naplata po potrošnji, ne čet pretplata) ili
**CLI agent** sa zvaničnim CLI-jem, jednom prijavljenim. Aplikacija nema budžet: kod plaćenih API-ja i mnogo krugova sa alatima
mogu nastati troškovi; belehe po agentu vidite na čvoru.

## Bezbednost

- Stranica za prijavu sa potpisanim kolačićem (7 dana, `HttpOnly`, `SameSite=Strict`, `Secure` iza HTTPS-a).
- Posle 5 pogrešnih lozinki zaključavanje od 10 minuta po IP adresi; svi pokušaji su u dnevniku revizije.
- Pišući API pozivi moraju imati sopstveno zaglavlje (CSRF zaštita), uz CSP i dodatna zaglavlja.
- Shell i CLI agenti su podrazumevano **isključeni**. Ko zna lozinku i ima postavljeno `PCL_ALLOW_SHELL=1`,
  može da odobri komande sa pravima korisnika aplikacije. `workspace/` je radni direktorijum, ali **nije sandbox**.
- `.env`, baza podataka i radni folderi su u `.gitignore`. Ključevi nikada ne pripadaju repozitorijumu.
- Kod botova za trgovanje (NEXUS) agentima nikada ne dozvolite trgovinu bez ljudskog odobrenja.

## Znanje firme i pamćenje

- **🧠 Znanje firme** (bočna traka): ono što svi agenti projekta uvek treba da znaju (firma, klijenti, stil, cene, pravila). Stoji u
  `wissen/firmenwissen.md` u folderu projekta. Svi `.md`/`.txt` fajlovi u `wissen/` idu uz svaki zadatak i u čet (zajedno do
  `PCL_KNOWLEDGE_CHARS`, podrazumevano 8000 znakova); ostale dokumente tamo (PDF, Word …) agenti vide kao spisak i čitaju po potrebi.
- **Pamćenje po agentu**: agent na kraju zadatka može da zapamti najviše 5 trajnih činjenica (preference, odluke, klijenti,
  šta je radilo). One se prikazuju u panelu agenta pod „🧠 Gedächtnis“ (pamćenje); možete ih menjati ili brisati. Granica `PCL_MEMORY_CHARS`
  (4000); najstariji unosi prvi ispadaju. Svaka nova beleška je u dnevniku revizije.

## Ciljevi, odobrenja, upotreba

- **🎯 Ciljevi**: ciljevi i podciljevi po projektu. Pri dodeljivanju zadatka opciono birate cilj; delegirani zadaci ga nasleđuju.
  Šefovi vide ciljeve sa napretkom u promptu, a CEO-ov kontrolni obilazak to izveštava. Označeno = ostvareno.
- **Prvo pitaj** (prozor ✋ Freigaben, po projektu, podrazumevano isključeno): *Odobri plan najvišeg šefa* zadržava novi zadatak
  dok ne odobrite plan raspodele; *Odobri izmene tima* („Teamänderungen freigeben“) zadržava CEO-ovo zapošljavanje, otpuštanje i menjanje saradnika. Odobravanje/odbijanje i preko
  Telegram dugmeta. Odbijeno = zadatak završi kao ❌ u pošti; vaš odgovor na to tera šefa da ponovo planira.
  Odobrenja za shell i dalje idu samo preko weba.
- **📊 Upotreba i troškovi**: pozivi, tokeni i procenjeni troškovi po projektu, agentu i modelu (danas, 7, 30 dana). Bez limita.
  Pretplatni CLI-ji i Ollama broje se kao 0 $; od `PCL_ABO_WARN_5H` pretplatnih poziva u 5 sati (podrazumevano 150, 0 = isključeno) stiže upozorenje na Telegramu.
  Cene su grube procene; sopstvene zadajte preko `PCL_PRICES='{"sonnet": 5}'` (US$ po 1 milion tokena, deo naziva modela).

## Testovi

```bash
./venv/bin/pip install pytest && ./venv/bin/python -m pytest -q tests
```
Radi bez interneta i bez ključeva (dobavljač `mock`, sopstvena baza).

## 🔌 Veze (webhook-ovi)

- **Izlaz:** u prozoru 🔌 Verbindungen unosite adrese (n8n, Zapier, Make, sopstvena usluga; i `http://127.0.0.1:…` na Pi-ju),
  sa opisom za agente i opcionim zaglavljima. Tajne pripadaju `.env` i koriste se kao `${NAME}`.
  Agenti sa pravom **„Darf Verbindungen nutzen“** (sme da koristi veze) zovu ih alatom `call_connection`; agent ne može da menja
  adresu ni zaglavlja, samo šalje podatke. **„Nur nach meiner Freigabe“** (samo posle mog odobrenja, podrazumevano uključeno) svaki poziv prvo stavlja pod ✋ Freigaben.
  **„Bei Post benachrichtigen“** (obavesti u pošti) šalje svaki gotov rezultat zadatka na vrhu kao JSON na adresu. Vremensko ograničenje `PCL_CONN_TIMEOUT` (30 s).
- **Ulaz:** uključite „Aufträge von außen“ (zadaci spolja), zatim `POST /hook/<projekat>/<ključ>` sa `{"text": "…", "agent": "opciono"}`
  prima zadatak za šefa (npr. iz n8n, iOS prečica ili DEXTER-a). Bez prijave; štiti ga samo ključ u adresi.
  „Neuen Schlüssel“ (novi ključ) poništava staru adresu. Dostupna je samo onoliko koliko je dostupan i sam Hyperstead (npr. samo u tailnet-u).

## ☁️ Otpremanje u cloud (GitHub, Google Drive, OneDrive, Telegram)

- **Podešavanje:** pristupni podaci u `.env` (`GITHUB_UPLOAD_TOKEN` + `GITHUB_UPLOAD_REPO`, `GDRIVE_CLIENT_ID` + `GDRIVE_CLIENT_SECRET`,
  `ONEDRIVE_CLIENT_ID`), korak po korak u [docs/cloud.md](docs/cloud.md) (na nemačkom). Kod Google-a i Microsoft-a se zatim prijavljujete u prozoru
  **☁️ Cloud**: prikazuje kod koji na telefonu unesete na stranici Google-a odnosno Microsoft-a (radi bez HTTPS-a).
  Prijava se čuva u `tokens/` pored `.env`, nikad u bazi podataka.
- **Ciljni folder:** po projektu i servisu u prozoru ☁️ Cloud (podrazumevano `Hyperstead/<ime projekta>`). Agenti smeju da izaberu samo
  podfolder ispod njega, npr. kada ga navedete u zadatku.
- **Sami otpremite:** 📁 Fajlovi → ☁️ pored fajla → izaberite cilj i folder. Dobijate link.
- **Agenti:** pravo **„Sme da otprema u cloud”** (postavljate samo vi). Alat `cloud_upload`; svako otpremanje čeka pod ✋ Odobrenja,
  uz to stiže Telegram poruka. Posle otpremanja link stoji u zadatku.
- **Podešavanje sa CEO-om:** pitajte glavnog šefa u 💬 Chatu, npr. „Pomozi mi da podesim GitHub”. On zna trenutno stanje svakog servisa i uputstvo i vodi vas korak po korak. Tokene nikad ne pišete u chat, nego ih sami unosite u `.env`.
- **Telegram:** `/datei` vam šalje fajlove do 50 MB na telefon, samo kada kliknete ili odobrite.
- GitHub: do 50 MB kao fajl u repou, veći kao prilog izdanju `paperclip-ablage` (do 2 GB). Google Drive: samo folderi i fajlovi koje je
  Hyperstead sam napravio (pravo `drive.file`). OneDrive: bilo koji folder. Testirano samo na simuliranim servisima.

## 🌐 Pravi pregledač i ▶ pokretanje koda

- **Pregledač** (`./install.sh --browser`, instalira Playwright + Chromium, oko 400 MB, samo 64-bitni sistem): agenti sa pravom
  „Internet recherchieren“ (istraživanje interneta) dobijaju `browse_page`. Stranica radi uz JavaScript; agent dobija vidljiv tekst, veze i
  po želji snimak ekrana (vidi ga kao kod `view_image`; `save` ga čuva u `assets/screenshots/`). Svaki zahtev stranice
  (skripte, okviri, XHR, WebSocket-i) mora da ide na javnu adresu; LAN/localhost je blokiran, WebRTC i preuzimanja su isključeni.
  Samo jedan pregledač u isto vreme (RAM), vremensko ograničenje `PCL_BROWSER_TIMEOUT` (30 s). Sopstveni Chromium: `PCL_BROWSER_PATH`, isključeno: `PCL_BROWSER=0`.
- **Pokretanje koda** (`./install.sh --run`, instalira bubblewrap): pravo „Darf Code ausführen“ (sme da pokreće kod, podrazumevano isključeno) daje `run_code`.
  Skripta radi izolovano: **bez interneta**, vidljivi su samo `/usr` i folder projekta (samo za čitanje pod `/projekt`),
  bez `.env`-a, bez baze, bez kućnog foldera. Ono što skripta upiše u svoj radni direktorijum završi u `output/run/<vreme>/`
  (najviše 50 fajlova/50 MB). Granice: `PCL_RUN_TIMEOUT` (60 s), `PCL_RUN_MEM_MB` (1024). Pokreće Python/Node sistema,
  dakle samo pakete instalirane preko apt-a (npr. `sudo apt install python3-pandas python3-matplotlib`). Globalno isključeno: `PCL_ALLOW_RUN=0`.
  Provera: `./venv/bin/python selftest.py run browser`.

## 🦀 Kompletna izrada Rust programa

Agentu sa pravima **„Darf programmieren“**, **„Darf Dateien schreiben“** i **„Darf Code ausführen“** (sme da programira, piše fajlove, pokreće kod) dajte zadatak kao
„Napiši mi Rust program koji …, sa testovima, i isporuči gotov paket“. Agent tada radi od A do Ž:

1. Pomoću `write_code` pravi Cargo projekat, npr. `rust/rechner/Cargo.toml` i `rust/rechner/src/main.rs` sa testovima (`#[test]`).
2. `rust_project` s `op=test` preuzima zavisnosti s crates.io, gradi program i pokreće testove.
   Greške se vraćaju s fajlom i redom, agent ih ispravlja i ponovo testira.
3. `op=package` još jednom testira, gradi release verziju i sprema **`output/<ime>.zip`**. Unutra: `programm/` (gotov
   program), `quelle/` (izvorni kod s `Cargo.lock`), `TESTBERICHT.txt` i `LIESMICH.txt`. Paket nastaje samo ako svi testovi prođu.

Paket dobijate u pošti ili pod **📁 Dateien** (pojedinačno ili u ZIP-u projekta). Ostale naredbe: `op=build`, `op=run` (s `args`, `stdin`).

- **Za koji sistem?** Program u `programm/` odgovara računaru na kojem radi Hyperstead: s Pi-ja Linux program (ARM),
  s Windows laptopa `.exe`. Za drugi sistem sami pokrenite `cargo build --release` u folderu `quelle/`.
- **Izolacija (Pi/Linux):** Izrada, testiranje i pokretanje idu u bubblewrapu kao `run_code`: bez interneta, bez `.env`, bez home foldera,
  upisiv je samo folder za izradu `.rust/` projekta. Internet ima samo `cargo fetch` (preuzima zavisnosti, ništa ne pokreće).
  Cargo postavke (`.cargo/`) i `rust-toolchain` fajlovi iz projekta se ne koriste.
- **Windows:** Bez bubblewrapa alat ostaje isključen. S `PCL_CARGO_UNSAFE=1` u `.env` laptop gradi **bez izolacije**: kod agenata
  (testovi, `build.rs`) tada radi sa vašim pravima i mogao bi čitati ili menjati fajlove na laptopu. API ključeve ne dobija u
  okruženju. Uključite samo ako verujete agentima i njihovim modelima.
- **Instalacija Rusta:** Pi `curl https://sh.rustup.rs -sSf | sh` (novije od `apt install cargo`), Windows `winget install Rustlang.Rustup`
  i u instalaciji uzmite i „Visual Studio Build Tools (C++)“. Zatim ponovo pokrenite Hyperstead i izvršite `selftest.py rust`.
- **Granice:** `PCL_CARGO_TIMEOUT` (900 s po koraku), `PCL_CARGO_MEM_MB` (3072, samo Linux), `PCL_CARGO_JOBS` (2), uvek samo jedna
  Rust izrada istovremeno. Prva izrada na Pi-ju traje dugo, nakon toga cargo ponovo gradi samo ono što se promenilo. Agent ima
  `PCL_MAX_TOOL_STEPS` (podrazumevano 6) krugova alata po pokretanju; za veće programe pomaže veća vrednost, npr. 12. Isključeno: `PCL_CARGO=0`.

## 🛠 Radionica: agenti se sami dopunjuju

Sa pravom **„Radionica“** agent radi kao na pravom računaru, za svaku AI i u svakoj firmi. Claude (CLI uz pretplatu) dobija svoje
Claude Code alate u folderu projekta, Codex svoje, a sve API AI i Ollama alat `befehl`. Ako program nedostaje, agent podnosi
**zahtev za dopunu**: CEO ga proverava, vi potvrđujete Telegram dugmetom ili pod ✋ Odobrenja, zatim server instalira tačno tu
komandu i zadatak se nastavlja. Ono što je instalirano navedeno je u `wissen/werkzeuge.md`.

- **Uključivanje:** `PCL_ALLOW_WERKSTATT=1` u `.env`, ponovo pokrenite, kod agenta označite polje i izaberite nivo.
- **Nivoi:** 1 = svaka komanda pita, 2 = rad u projektu je slobodan, instalacije i brisanje pitaju (podrazumevano), 3 = sve slobodno
  (samo uz `PCL_WERKSTATT_FREI=1`). Pristupni podaci (`.env`, tokeni, ključevi) su uvek blokirani.
- **Pažnja:** komande rade bez izolacije sa vašim korisničkim pravima. Nivo 2 prepoznaje instalacije po obliku, to nije sandbox.
- Sve ostalo, uključujući Remotion i probleme: [docs/werkstatt.md](docs/werkstatt.md) (na nemačkom).

## Paralelni rad

Istovremeno može da radi do `PCL_WORKERS` zadataka (podrazumevano 2, najviše 6), npr. više saradnika jednog šefa ili zadaci
različitih projekata. Agent nikada ne radi na dva zadatka odjednom, a istovremeno radi najviše jedan Ollama zadatak
(RAM na Pi-ju). Kod pretplatnih CLI-ja (Claude, Codex) paralelni pozivi brže dostižu limit pretplate; tada postavite `PCL_WORKERS=1`.

## Granice ove verzije

- Nema automatskog heartbeat-a po rasporedu (zadaci se pokreću ručno ili delegiranjem).
- Nema AI za tekst u video, nema OCR za skenirane/slikovne PDF-ove; CEO sam ne zapošljava nove agente (organigram pravite vi).
- Pravi pregledač (`browse_page`) čita stranice, ali ne klikće i ne popunjava formulare (bez prijava, bez kupovina). Pretraga DuckDuckGo-a bez ključa može biti ograničena ili promenjena.
- Nema budžeta: tokeni i procenjeni troškovi se samo prikazuju (📊). Limiti krugova (dorade, provere, dubina) sprečavaju beskonačne petlje.
- Sesije su proste potpisane kolačići; jedan uređaj ne može se posebno odjaviti
  (promena lozinke poništava sve sesije).


## Samoprovera

Posle instalacije i unosa ključeva `./venv/bin/python selftest.py` proverava sve stvarne stvari koje se bez interneta nisu mogle testirati:
web pretragu, čitanje stranica, pretragu slika i generator slika, SSRF zaštitu, svakog AI provajdera mini zahtevom (uključujući Ollama),
Telegram (token bota i probna poruka na vaš ID čata), ffmpeg, glasovni izlaz, PDF sa dijakriticima, OCR. Pojedinačne grupe:
`selftest.py web | llm | telegram | media | ocr | rust | film`. Svaki red prikazuje OK, FEHLT (opciono) ili FEHLER sa konkretnom napomenom.

## Ollama (lokalni modeli)

Dobavljač „Ollama (lokal)“: ključ nije potreban, lista modela dolazi direktno iz Ollama (`ollama pull qwen2.5:3b`). U dijalogu „Firma aus Vorlage“ (firma iz šablona)
postoje dugmad „Alles lokal“ (sve lokalno) i „Nur Mitarbeiter lokal“ (samo saradnici lokalno); inače Ollama birate po agentu. Ako Ollama radi na drugom računaru
(npr. laptopu), postavite `OLLAMA_URL` na njegovu adresu. Mali modeli (3B) su na Pi-ju spori i često loše drže protokol alata;
za šefove jak model, lokalno pre svega za jednostavne saradnike ili čet.

## Claude i ChatGPT preko vaše pretplate (CLI umesto API ključa)

U `.env`: `PCL_ALLOW_CLI=1`. Programe sami instalirate i jednom prijavljujete na Pi-ju (uputstva proizvođača:
Claude Code `claude`, OpenAI Codex `codex`; prijava sa vašom pretplatom). Posle toga se „Claude (CLI, dein Abo)“ i „ChatGPT (Codex-CLI, dein Abo)“
pojavljuju u svim listama dobavljača. Server ih poziva bez shell-a, u praznom folderu i **bez naših API ključeva u okruženju**
(inače bi `claude` naplaćivao API ključ umesto pretplate). Ograničenja: sporije od API-ja (pokretanje programa po odgovoru), važe limiti pretplate
(mnogo agenata = brzo do limita), a CLI programi imaju sopstvene alate; po potrebi prilagodite komandu preko `PCL_CLI_CLAUDE` / `PCL_CLI_CODEX`.

## Model nestao? Prebacite agente

Hyperstead svakih 6 sati (`PCL_MODEL_CHECK_HOURS`) proverava da li modeli agenata još postoje kod dobavljača i primećuje i kada poziv javi „Modell nicht gefunden“ (model nije pronađen). Tada stiže Telegram poruka, zadatak pada uz jasnu napomenu, a u meniju **⚠ Modelle** sve pogođene agente prebacujete na drugi model jednim klikom.

## Veliki timovi

Šef može da ima koliko god hoćete saradnika. U panelu šefa (Podešavanja) pod **Unterstellte Mitarbeiter** (podređeni saradnici) označite sve potvrdnim poljima i sačuvajte dodelu. Alternativno: prevucite donju tačku šefa na saradnika. Dugme **🗂 Ordnen** (poredaj) pravi ceo organigram (grupe od 6 i više saradnika u redovima po 5).

## CEO sam sastavlja svoj tim

CEO iz palete ima pravo **„Darf sein Team selbst zusammenstellen“** (sme sam da sastavi svoj tim, `recruit`). Ako još nema saradnike i dobije zadatak, analizira ga i pravi saradnike sa ulogom, radnim uputstvom i linijama izveštavanja (do 20, uključujući šefove odeljenja sa sopstvenim timom). Novi saradnici **još nemaju AI**: dodeljujete ih u meniju **⚠ Modelle** (svi odjednom) ili po agentu u podešavanjima, pa odgovorite u **Pošti** na zadatak (npr. „Weiter“ = nastavi). Posle toga CEO raspoređuje posao kao i obično. CEO novim saradnicima može da da samo web, slike, čitanje/pisanje fajlova, medije i programiranje, nikada shell.

**I kada tim već postoji**, CEO sa ovim pravom sme pri svakom zadatku da prilagodi svoj tim vašim zadacima i uslovima:
- **Zapošljavanje**: dodatni saradnici, kao gore bez AI. Dobijate poruku na Telegramu i dodeljujete im AI. Posao dobijaju tek od sledećeg zadatka ili posle vašeg „Weiter“.
- **Otpuštanje**: samo saradnici ispod njega, nikada on sam niti agenti van njegovog tima. Ljudi otpuštenog se pomeraju nivo više. Ko još ima otvoren zadatak, ne biva otpušten.
- **Izmena**: uloga, radno uputstvo i prava (samo gore navedena) saradnika ispod njega.

**Prava prema ulozi**: CEO treba svakome da da tačno ona prava koja mu posao traži. Ako neka zaboravi, sistem ih dodaje na osnovu imena, uloge i radnog uputstva, npr. istraživanje → *web*, slike/ilustracije/grafika/dizajn → *slike* + *pisanje fajlova*, video/zvuk/glas/PDF/prelom → *mediji* + *pisanje fajlova*, autor/tekst/lektura → *pisanje fajlova*, programiranje/veb-sajt → *programiranje* + *pisanje fajlova*. Ako promeni ulogu saradnika, prava se ponovo podešavaju prema njoj. Shell, izvršavanje koda, veze i objavljivanje nikada ne daje; to štiklirate samo vi.

Ako želite da unapred vidite svaku izmenu tima, štiklirajte u prozoru **Freigaben** *Teamänderungen freigeben* (odobri izmene tima). Bez štiklirane opcije kod CEO-a ne sme ništa od ovoga. Dnevni zadaci (raspored, kontrolni obilazak) nikada ne menjaju tim.

## Radno vreme i dnevni zadaci

Bočna traka **🕘 Zeitplan** (raspored): za svaki projekat postavite početak rada, kraj rada i radne dane. Za svakog saradnika možete napraviti **dnevne zadatke** (fiksno vreme, na početku ili na kraju rada, na izabranim danima u nedelji), npr. „svaki dan u 15:00 proveri web sajt“. Rezultat stiže u prikaz „Post“ kao svaka objava (i preko Telegrama). Ako je poslednji zadatak nekog rasporeda još u toku, ne pokreće se dvaput; ako je Pi u to vreme bio isključen, nadoknađuje se do 6 sati.
Na početku rada firma ponovo preuzima zadatke koji su ostali nezavršeni (nepokrenuti se pokreću, neuspešni zadaci na vrhu ponavljaju se do `PCL_MAX_RESUMES`=2 puta). Opciono firma potpuno miruje van radnog vremena. Vreme je ono sa Pi-ja; ako nije tačno, u `.env` postavite `PCL_TZ=Europe/Vienna`.

## CEO kontrolni obilazak

U prozoru **🕘 Zeitplan** **👑 CEO-Kontrollgang** (CEO kontrolni obilazak) podešava dnevni kontrolni obilazak najvišeg šefa (podrazumevano: na kraju rada; ostala vremena preko „Neue tägliche Aufgabe“ + potvrdno polje *Kontrollgang*). Sistem mu prilaže **statusni izveštaj** sa činjenicama: po saradniku danas započeto/završeno/neuspešno/otvoreno, počeci rada van radnog vremena, otvoreni zadaci bez početka rada, saradnici bez AI, nezavršeni zadaci i da li su dnevni zadaci izvršeni. CEO to procenjuje, po potrebi raspoređuje naredne zadatke svom timu i u pošti piše kontrolni izveštaj. „📋 Statusbericht ansehen“ (pogledaj statusni izveštaj) prikazuje činjenice bez CEO-a.

## Folder projekta

Svaki projekat ima **folder sa svojim imenom** pod `workspace/` (npr. `workspace/Buchverlag-Content-Agentur/`, nemački znaci se transkribuju). Ostaje isti kada se projekat preimenuje i **nikada se ne briše kada se projekat obriše**. Ako napravite novi projekat istog imena, preuzima postojeći folder sa fajlovima. Stari folderi sa brojevima (`workspace/1`, `workspace/2` …) se pri pokretanju automatski preimenuju po imenu projekta.

## Objavljivanje web stranice

U prozoru **📁 Dateien dieses Projekts** postoji **🚀 Veröffentlichen** (objavi). Objavljuje se **samo folder `www/` u folderu projekta** (`www/index.html`, uz CSS, slike … sa relativnim putanjama); sve ostalo u projektu (beleške, `output/`, `input/`, tačka-fajlovi, simboličke veze ka spoljašnjosti) ostaje nevidljivo. Ako nema foldera `www/`, isporučuje se, kao ranije, `index.html` iz foldera projekta (bez `input/` i skrivenih fajlova). Stranica trajno radi na sopstvenom portu (od 8800, `PCL_SITE_PORT_BASE`), podrazumevano samo na samom Pi-ju: `http://127.0.0.1:8800/`. Za pristup u mreži u `.env` postavite `PCL_SITE_HOST=0.0.0.0`. Agenti sa pravom „Darf die Webseite zur Veröffentlichung vorschlagen“ (sme da predloži web stranicu za objavu) mogu da zatraže odobrenje za „veröffentlichen“; stranicu na mreži tek vaš klik pod **Freigaben** pušta online. Promene agenata su odmah vidljive; posle ponovnog pokretanja stranica se sama ponovo pokreće. Za otvoreni internet ispred mora da stoji reverzni proksi sa HTTPS-om (npr. Caddy), a ne mali server.
