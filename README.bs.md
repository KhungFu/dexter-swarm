# Hyperstead

🌐 Jezici: [Deutsch](README.md) · [English](README.en.md) · [Türkçe](README.tr.md) · [Srpski](README.sr.md) · **Bosanski** · [Hrvatski](README.hr.md)

Tim agenata vještačke inteligencije kao uređivač čvorova, samostalno hostovan, dovoljno lagan za Raspberry Pi.
Napravite projekat, prevucite agente na površinu, povežite ih (šef → saradnik), podesite AI provajdera, radno uputstvo i prava po čvoru i dodijelite zadatke.

> Detaljna uputstva u `docs/` su trenutno napisana samo na njemačkom. Nazivi dugmadi i menija u aplikaciji ostaju na njemačkom.

## Instalacija

Hyperstead je Python program (Flask + SQLite) i radi na više sistema. Više instalacija
može raditi paralelno; svaka ima svoje firme i podatke.

| Sistem | Stanje | Uputstvo |
| --- | --- | --- |
| Raspberry Pi / Linux (Debian, Ubuntu) | glavni sistem, pun obim funkcija | dole |
| Windows 10/11 | radi, bez `run_code`, izrada Rust programa samo bez izolacije preko prekidača, neke funkcije traže dodatne programe | [docs/windows.md](docs/windows.md) |
| macOS | testirano (radi) | dole (ručno) |
| Vlastiti računar za slike (npr. stari laptop bez grafičke kartice) | besplatne slike sa referentnim slikama za Hyperstead | [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md) |

Selidba sa jednog računara na drugi: zaustavite Hyperstead i kopirajte `data.db`, folder `workspace/` i `.env`
([primjer Pi → Windows](docs/windows.md)).

### Raspberry Pi / Linux

```bash
git clone https://github.com/KhungFu/hyperstead-neu hyperstead && cd hyperstead
./install.sh --service     # venv, zavisnosti, .env sa nasumičnom lozinkom, systemd servis
nano .env                  # unesite API ključeve, zatim: sudo systemctl restart hyperstead
```

Bez servisa: `./install.sh`, pa `./venv/bin/python app.py` → http://127.0.0.1:8787.
Lozinka za prijavu nalazi se u `.env` (`APP_TOKEN`). Ažuriranje, ponovno pokretanje, rezerva: [Rad](#rad-ko-šta-gdje-kada-i-kako).
Više funkcija (video, OCR, kompajleri, pregledač): `./install.sh --all`.

### Windows

PowerShell u folderu Hyperstead:

```powershell
git clone https://github.com/KhungFu/hyperstead-neu hyperstead; cd hyperstead
powershell -ExecutionPolicy Bypass -File install.ps1
notepad .env
deploy\windows\hyperstead-start.bat
```

`install.ps1` zatim provjerava sve preduslove (video, glas, preglednik, OCR, filmski studio, server za slike, Rust, kompajleri), prikazuje svaki dio koji nedostaje s komandom i veličinom i pita **prije svake instalacije** (j/n = da/ne, a = da za sve ostale, x = ne za sve ostale). Bez „j“ se ništa ne instalira. `hyperstead-start.bat` provjerava ponovo pri svakom pokretanju i postavlja jedno pitanje s 20 sekundi za odgovor; bez odgovora Hyperstead se jednostavno pokreće (autostart nikad ne zastaje). Samo prikaz: `venv\Scripts\python.exe voraussetzungen.py --liste`.

Šta nedostaje na Windowsu, automatsko pokretanje i paralelni rad sa Pi-jem: [docs/windows.md](docs/windows.md).
Kasnije ažuriranje: `git pull`, pa ponovo pokrenite.

### macOS (testirano)

```bash
git clone https://github.com/KhungFu/hyperstead-neu hyperstead && cd hyperstead
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
cp .env.example .env       # upišite APP_TOKEN=<duga lozinka>, dodajte API ključeve
./venv/bin/python app.py   # http://127.0.0.1:8787
```

`install.sh` je napravljen za Debian/Ubuntu (apt), pa na macOS-u radite ručno kao gore. Dodatni programi preko Homebrew-a
(`brew install ffmpeg tesseract poppler`). `run_code` postoji samo na Linuxu.

### Slike na vlastitom računaru

Računar u kućnoj mreži (i bez grafičke kartice, bar 8 GB RAM-a) može za Hyperstead besplatno praviti slike sa
referentnim slikama. U `.env` ostavite aktivne tačno ove dvije linije (samo jedna `IMAGE_PROVIDER=` linija bez `#`):

```
IMAGE_PROVIDER=sdcpp
SDCPP_URL=http://<IP računara za slike>:1234    # na samom računaru za slike: http://127.0.0.1:1234
```

Podešavanje: [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md).

### Animirani filmovi uz Blender

Ako je Blender instaliran na računaru na kojem radi Hyperstead, agenti prave crtane filmove: likove s vlastitim glasovima i
pokretima usta, scene, kameru, titlove, gotov film sa zvukom (alat `film`, predložak firme „🐶 Animationsstudio“).
Ako Hyperstead sam ne pronađe Blender, upišite ga u `.env`:

```
BLENDER_PATH=C:\Program Files\Blender Foundation\Blender 4.2\blender.exe
```

Uputstvo i format scenarija (na njemačkom): [docs/filmstudio.md](docs/filmstudio.md).

## Rad: ko šta, gdje, kada i kako

**Ko:** sve ovo radi vlasnik računara (vi), a ne agenti. Komande se izvršavaju u
folderu Hyperstead: na Pi-ju u terminalu (`cd ~/hyperstead`), na Windowsu u PowerShell-u
(`cd $HOME\hyperstead`, ili gdje god ste stavili folder).

### Kratak pregled

| Šta | Kada | Raspberry Pi / Linux (sa servisom) | Windows |
| --- | --- | --- | --- |
| Pokretanje | poslije instalacije, poslije ponovnog pokretanja bez automatskog starta | `sudo systemctl start hyperstead` | dvoklik na `deploy\windows\hyperstead-start.bat` (prozor ostavite otvoren) |
| Zaustavljanje | prije selidbe, rezerve, ažuriranja | `sudo systemctl stop hyperstead` | zatvorite prozor za pokretanje (ili u njemu Ctrl+C) |
| Ponovno pokretanje | poslije svake promjene u `.env`, poslije ažuriranja | `sudo systemctl restart hyperstead` | zatvorite prozor za pokretanje, ponovo pokrenite `hyperstead-start.bat` |
| Radi li? | kada ima problema | `systemctl status hyperstead` | da li je prozor za pokretanje otvoren? Pregledač: <http://127.0.0.1:8787> |
| Pregled dnevnika | kod grešaka | `journalctl -u hyperstead -f` (Ctrl+C prekida) | prikazuje se u prozoru za pokretanje |
| Ažuriranje | kada postoji nova verzija (npr. poslije spojenog pull requesta) | vidi dolje | vidi dolje |
| Provjera | poslije instalacije, ažuriranja, novih ključeva | `python3 selftest.py` | `python selftest.py` |
| Ključevi / podešavanja | novi ključ, drugi provajder slika | `nano .env`, pa ponovo pokrenite | `notepad .env`, pa ponovo pokrenite |
| Rezerva | redovno, prije selidbe i većih ažuriranja | kopirajte `data.db`, `workspace/`, `.env` (prvo zaustavite) | isto u folderu Hyperstead |

### Ažuriranje (preuzimanje nove verzije)

**Raspberry Pi / Linux**, u terminalu:

```bash
cd ~/hyperstead
git pull
./install.sh               # potrebno samo ako se requirements.txt promijenio; .env ostaje nepromijenjen
sudo systemctl restart hyperstead
python3 selftest.py llm     # kratka provjera da li AI provajderi odgovaraju
```

**Windows**, u PowerShell-u:

1. `cd $HOME\hyperstead`
2. `git pull`
3. Samo ako su se paketi promijenili (ili kada niste sigurni): `powershell -ExecutionPolicy Bypass -File install.ps1`
   (postojeći `.env` ostaje nepromijenjen).
4. Zatvorite crni prozor za pokretanje Hyperstead-a.
5. Ponovo pokrenite `deploy\windows\hyperstead-start.bat` (dvoklik ili upišite u PowerShell).
6. Provjera: `python selftest.py llm`

Ako `git pull` javi „local changes would be overwritten“, sami ste promijenili neki fajl programa.
`git stash` odlaže promjenu na stranu, zatim ponovite `git pull`. Vaši podaci (`data.db`, `workspace/`, `.env`)
nikada nisu ugroženi, jer ih Git ne poznaje.

### Automatsko pokretanje

- **Pi:** `./install.sh --service` podešava servis; on se onda sam pokreće pri svakom podizanju sistema.
- **Windows:** Win+R, upišite `shell:startup` i tamo stavite prečicu do `deploy\windows\hyperstead-start.bat`
  (i do `bildrechner-start.bat`, ako ga koristite). Windows se za to mora sam prijaviti
  ([docs/windows.md](docs/windows.md), odjeljak 4).

### Mijenjanje podešavanja u `.env`

- Svako podešavanje stoji tačno jednom, bez `#` na početku. Redovi sa `#` su isključeni. Kod dupliranih redova
  važi prvi.
- Poslije svake promjene ponovo pokrenite Hyperstead, inače važi stari stanje.
- Ključeve nikada ne kopirajte u četove, snimke ekrana ili repozitorijum. Ako je ključ ipak negdje završio: opozovite ga kod provajdera i unesite novi.
- Zatim provjerite sa `selftest.py`. Pojedinačne oblasti: `selftest.py llm`, `web`, `telegram`, `media`, `ocr`, `code`.

### Čitanje samoprovjere

- **OK:** radi.
- **MISSING (nedostaje):** opciono; red navodi komandu za dodavanje (na Windowsu komandu za Windows).
  Potrebno samo ako to vaši agenti koriste (npr. video, glasovni izlaz, skenirani PDF-ovi).
- **ERROR (greška):** nešto što ste unijeli ne radi, najčešće nevažeći ili istekao ključ ili servis koji
  ne radi (npr. računar za slike). Red navodi razlog.
- Pojedinačni timeout kod web servisa je često samo privremen: pokušajte kasnije.

### Računar za slike (ako se koristi)

- **Gdje:** na računaru koji pravi slike (npr. laptop), u folderu `C:\bildrechner`.
- **Kada:** mora da radi dok agenti trebaju praviti slike.
- **Kako se podešava (jednom):** u PowerShell-u u folderu Hyperstead
  `powershell -ExecutionPolicy Bypass -File deploy\windows\bildrechner-einrichten.ps1` (preuzima program i modele).
- **Kako se pokreće:** pokrenite `C:\bildrechner\bildrechner-start.bat`, prozor ostavite otvoren. U `.env` fajlu Hyperstead-a
  `IMAGE_PROVIDER=sdcpp` i `SDCPP_URL=...` ([uputstvo](docs/laptop-bildrechner.md)), zatim ponovo pokrenite Hyperstead.

### Filmski studio (ako se koristi)

- **Gdje:** na računaru sa Blenderom (npr. laptop). Firma s alatom `film` mora raditi u **ovoj** instanci Hyperstead.
- **Kada:** Blender ne mora biti otvoren, Hyperstead ga za svaku scenu pokreće u pozadini i ponovo zatvara.
- **Provjera:** `python selftest.py film` (Windows) ili `python3 selftest.py film`.
- **Koliko traje:** pri 640×360 i 12 sličica u sekundi, zavisno od laptopa, oko 1 do 5 minuta po 10 sekundi filma. Blender nikad ne radi istovremeno sa računarom za slike.

### Selidba (npr. Pi → laptop)

Korak po korak u [docs/windows.md](docs/windows.md), „Phase 2 – Umzug“ (na njemačkom). Ukratko: zaustavite oba, kopirajte `data.db`,
`workspace/` i `.env`, pokrenite na novom računaru i provjerite, pa tek onda isključite stari.
Telegram unosite samo na jednom računaru.

### Šta se dešava kada nešto nedostaje

Ova lista se dopunjava pri svakoj promjeni programa. Svaki red kaže šta sistem radi i šta vi treba da uradite.

| Nedostaje | Šta sistem radi | Šta vi radite |
| --- | --- | --- |
| `.env` | Hyperstead se pokreće bez ključeva i bez lozinke, dostupan samo sa ovog računara. Sa `HOST=0.0.0.0` pokretanje se prekida dok je `APP_TOKEN` prazan. | `./install.sh` (Pi) odnosno `install.ps1` (Windows) ga pravi sa nasumičnom lozinkom. |
| Dodatni programi za Windows (ffmpeg, Piper/edge-tts, preglednik, Tesseract + jezici, Poppler, Blender, server za slike, Rust + Build Tools, Node/TypeScript, Java, Go, GCC, Git Bash, Ruby, PHP, Lua) | `install.ps1` i `hyperstead-start.bat` prikazuju listu s komandama i pitaju prije svake instalacije. Dijelove odbijene s „n“ pamti `.voraussetzungen-nein`: pokretanje više ne pita, `install.ps1` ponovo pita. Ako se `requirements.txt` promijenio od zadnje instalacije, pokretanje nudi `pip install`. Novo instalirane programe Hyperstead nalazi bez novog prozora (PATH se dopunjava pri pokretanju). Ako server za slike ne radi (`IMAGE_PROVIDER=sdcpp`, lokalno), pokretanje nudi da ga pokrene. | Odgovoriti „j“ u prozoru ili pokrenuti `powershell -ExecutionPolicy Bypass -File install.ps1`. Ako instalacija ne uspije, u ispisu stoji komanda za ručni rad. |
| `data.db` | Pravi se nova i prazna. Firme, zadaci i pošta su nestali. | Prvo napravite rezervu (vidi Rad). Vraćajte samo iz rezerve. |
| API ključ u `.env` | Provajder se u samoprovjeri prijavljuje kao MISSING i agenti ga ne koriste. Ako je unesen, ali nevažeći: ERROR sa HTTP 401. | Unesite ključ ili isključite red sa `#`. |
| Ollama nedostupna ili model prevelik | Zadatak ne uspijeva uz „Ollama not reachable“ odnosno „Not enough RAM for this model“; model koji nedostaje javlja „`ollama pull …`“. Ako Ollama `OLLAMA_TIMEOUT` sekundi ništa ne pošalje, zahtjev se prekida s tom napomenom, bez ponavljanja. | `systemctl status ollama`, preuzmite manji model (`ollama pull qwen2.5:1.5b`) i izaberite ga kod agenta, ili povećajte `OLLAMA_TIMEOUT`. |
| Vlastita veza AI-ja (npr. Canva iz Claude pretplate, vlastiti MCP server) | Hyperstead čita stanje pri svakom Claude pozivu. Ako veza ne radi („FAILED“, „NEEDS SIGN-IN“, „NOT AVAILABLE“) ili je `tokens/claude-mcp.json` neispravan, to se bilježi (`ai_link_failed`), Telegram javlja najviše svakih 6 sati, a CEO ti to iskreno kaže umjesto da se pravi da ju je koristio. Bez podešavanja sve radi kao prije, samo bez veza. | [docs/ki-verbindungen.md](docs/ki-verbindungen.md) (njemački): `PCL_CLAUDE_CONNECTORS=Canva` u `.env` ili serveri u `tokens/claude-mcp.json`, zatim `python selftest.py links`. |
| Slike preko Canve (`IMAGE_PROVIDER=canva` ili Canva konektor) | Hyperstead tada sam ne pravi sliku. Claude CLI agent šalje referentnu sliku u Canvu pomoću `canva_upload` i tamo pravi sliku. Bez Canva konektora `image_generate` javlja „not connected“. Ako drugi pružalac slika ne uspije, greška navodi put preko Canve, a uz referentne slike više nema besplatne zamjenske slike bez reference. | [docs/ki-verbindungen.md](docs/ki-verbindungen.md) (njemački): `PCL_CLAUDE_CONNECTORS=Canva`, agent s pružaocem Claude (CLI) i pravom `images`. Ako Canva pokazuje „NOT AVAILABLE“: prijavi Canvu sa `claude mcp add --scope user canva https://mcp.canva.com/mcp` (odjeljak u uputstvu). |
| Datoteka zvučnog efekta u scenariju (`geraeusche` u filmskom studiju) | Provjera scenarija javlja svaku datoteku koja nedostaje ili ne odgovara, sa scenom i brojem, i ništa se ne snima. Ako se zvuk odnosi na red dijaloga koji ne postoji, izostavlja se samo taj zvuk. | Napravi datoteku sa `sound_generate` (`AUDIO_PROVIDER=elevenlabs`) ili stavi svoju u `film/geraeusche/`, vidi [docs/filmstudio.md](docs/filmstudio.md) (njemački). |
| Atmo ili muzika u scenariju (`atmo`, `musik`, `ducken` u filmskom studiju) | Ako datoteka nedostaje, provjera scenarija javlja scenu i polje, i ništa se ne snima. Bez atmo, muzike i zvučnih efekata `op=check` navodi tihe scene, a film se ipak pravi. Muzika i atmo se automatski stišavaju dok neko govori. | Napravi datoteku sa `sound_generate` (`kind` sfx ili music) ili stavi svoju; `"ducken": false` isključuje stišavanje, vidi [docs/filmstudio.md](docs/filmstudio.md). |
| `SDCPP_URL` (uz `IMAGE_PROVIDER=sdcpp`) | Zahtjevi za slike ne uspijevaju uz poruku „SDCPP_URL is missing“ (nedostaje). Uz `IMAGE_FALLBACK=pollinations` pravi se besplatna zamjenska slika bez referenci, uz napomenu u rezultatu. | Dodajte red u `.env`, ponovo pokrenite Hyperstead. |
| Računar za slike nije dostupan (laptop isključen, firewall, pogrešna IP) | Kao gore: greška „ConnectionError“ (nije dostupan), uz rezervu zamjenska slika. | Uključite laptop, pokrenite `bildrechner-start.bat`, provjerite IP i firewall. |
| `sd-server.exe` (Windows, računar za slike) | `bildrechner-start.bat` prikazuje „sd-server.exe fehlt“ (nedostaje) i ništa ne pokreće. | Pokrenite `deploy\windows\bildrechner-einrichten.ps1`. |
| Fajl modela (Windows, računar za slike) | Startni fajl navodi nedostajući fajl i ne pokreće se. Ako nedostaje samo veliki jezički model (`Qwen3-4B-Q4_K_M.gguf`), koristi manji, ako postoji. | Ponovo pokrenite skriptu za podešavanje; preuzima samo nedostajući fajl. |
| Windows runtime `VCOMP140.DLL` | `sd-server.exe` javlja „VCOMP140.DLL nicht gefunden“ (nije pronađen) i prekida rad. | Ponovo pokrenite skriptu za podešavanje (korak 3 instalira runtime), pa otvorite startni fajl. |
| Pravilo firewall-a za port 1234 (Windows) | Samo Pi ne može doći do računara za slike. Sam laptop radi dalje. | Pokrenite komandu iz [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md), odjeljak 4, kao administrator. |
| Makro u `macros/` ili prijava `macros/<sajt>.json` (uz `PCL_MACROS=1`) | Bez makroa alat `site_macro` ne postoji. Bez sačuvane prijave makro staje uz napomenu. Ako MagicLight ili Flow promijene stranicu, `site_macro` javlja ERROR i stavlja `<sajt>-fehler.png` u `output/`. Samoprovjera (`browser`) prikazuje MISSING. | Makro (ponovo) snimiti prema [macros/README.md](macros/README.md). |
| Raspakovan ZIP (`input/<ime>/`) | Pri učitavanju Hyperstead sigurno raspakuje svaki ZIP u `input/<ime>/` (bez `..` putanja, linkova i `__MACOSX`). Ako je ZIP oštećen ili raspakovan veći od `PCL_UNZIP_MAX_MB` (zadano 2000), ostaje samo ZIP, a dnevnik pokazuje `file_unzip_failed`. Ako agent čita ZIP bez foldera (npr. učitan prije ažuriranja), `read_file` ga tada raspakuje. | Ništa. Za vrlo velike ZIP-ove povećaj `PCL_UNZIP_MAX_MB` ili učitaj u dijelovima. `PCL_UNZIP_UPLOADS=0` isključuje raspakivanje. |
| `ffmpeg`, `tesseract`, `pdftoppm`, glasovni izlaz | Funkcija nedostaje. Agenti koji je traže prijavljuju grešku u rezultatu. Samoprovjera prikazuje ERROR (Pi) odnosno MISSING (Windows). | Instalirajte program (komande u samoprovjeri i u [docs/windows.md](docs/windows.md)). |
| Blender (alat `film`) | `save`, `check`, `voices` i `assemble` i dalje rade. `preview` i `render` javljaju „Blender was not found“ (Blender nije pronađen) uz napomenu o `BLENDER_PATH`. Samoprovjera prikazuje MISSING. | Instalirajte Blender (`winget install BlenderFoundation.Blender`) ili postavite `BLENDER_PATH` u `.env`, ponovo pokrenite. |
| `film/film.json` (scenarij) | `film` javlja „film/film.json is missing“ (nedostaje) i traži da se prvo sa `op=save` sačuva scenarij. Neispravan scenarij se ne čuva, odgovor navodi sve greške. | Ništa, agenti ga sami prave. Možete ga napisati i ručno ([docs/filmstudio.md](docs/filmstudio.md)). |
| Slika, muzika ili `.blend` fajl naveden u scenariju | Provjera navodi scenu, lik i putanju, ništa se ne renderuje. | Stavite fajl u `assets/` ili `input/` ili ispravite putanju u scenariju. |
| Klip scene (`film/clips/`) | `assemble` navodi scene koje nedostaju i ništa ne montira. Ako se `render` prekine (vremensko ograničenje), gotove sličice ostaju sačuvane i sljedeći poziv nastavlja odatle. | Ništa, agenti ponovo pozivaju `render`. |
| Govor za film | `voices`/`render` se prekidaju porukom „No speech output available“ (nema govora). Scene bez dijaloga i dalje rade. | Kao kod „govora“ iznad (na Windowsu `edge-tts` + `TTS_ENGINE=edge`). |
| `cargo` (Rust, alat `rust_project`) | Alat se agentima ne prikazuje; `check_code` i dalje provjerava `.rs` fajlove ako postoji `rustc`. Samoprovjera (`selftest.py rust`) prikazuje MISSING s naredbom za instalaciju. | Instalirajte Rust: Pi `curl https://sh.rustup.rs -sSf \| sh`, Windows `winget install Rustlang.Rustup`. Zatim ponovo pokrenite Hyperstead. |
| bubblewrap pri izradi Rust programa (Pi/Linux) | `rust_project` ostaje skriven, isto kao `run_code`. | `./install.sh --run` |
| `PCL_CARGO_UNSAFE=1` (Windows) | Windows nema izolaciju, zato `rust_project` bez prekidača ostaje skriven. S prekidačem laptop gradi bez izolacije. | Postavite ga samo ako znate rizik ([Rust programi](#-kompletna-izrada-rust-programa)), zatim ponovo pokrenite. |
| `Cargo.toml` u Rust folderu | `rust_project` javlja „Cargo.toml is missing in …“ i navodi fajlove koje agent prvo mora napraviti. | Ništa, agent ih pravi pomoću `write_code`. |
| Internet za Rust zavisnosti (crates.io) | `cargo fetch` ne uspijeva, ništa se ne gradi, agent dobija poruku o grešci. Već preuzete zavisnosti ostaju u `.rust/cargo-home` i rade dalje. | Provjerite internet i ponovo pokrenite zadatak. |
| Položeni testovi za Rust paket | Paket se **ne** pravi („NO PACKAGE“); agent dobija greške s brojem reda i mora ih ispraviti. Bez testova paket nastaje s upozorenjem WARNING u rezultatu. | Ništa, agent ispravlja i ponovo gradi. Ako odustane, vratite zadatak preko šefa. |
| Folder `.rust/` u projektu (folder za izradu) | Pri sljedećoj izradi pravi se ponovo, što tada traje duže (sve se ponovo preuzima i kompajlira). Skriven je i nije dio ZIP preuzimanja. | Ništa. Smijete ga obrisati ako ponestane mjesta. |
| Telegram token ili ID čata | Telegram ostaje isključen, sve ostalo radi. Samoprovjera prikazuje MISSING. | Potrebno samo ako želite poruke na telefonu. |
| Folder ili fajl u projektu (`wissen/`, `input/`) | Folderi koji ne postoje smatraju se praznim. Agenti rade dalje bez znanja o firmi. | Napravite ili otpremite fajl ili folder u projektu. |
| Obrisan fajl ili ispražnjen folder (prikaz fajlova, „🗑 Delete selected“ / „🧹 Empty folder“) | Fajlovi su trajno nestali, nema korpe za otpatke. Sam folder ostaje, agenti rade dalje i nedostajuće fajlove tretiraju kao gore. Ako se obrisani fajl nalazi u scenariju ili je naveden u zadatku, agent ga prijavljuje kao nedostajući. | Ako vam fajlovi još trebaju, prvo preuzmite „⬇ Everything as ZIP“, inače ponovo otpremite fajl. |
| Ključ video provajdera (npr. `KLING_SECRET_KEY`, `HIGGSFIELD_API_KEY_SECRET`) | `video_generate` javlja „VIDEO_PROVIDER=…, but … is missing in .env“ i ništa ne pravi; ostali provajderi sa liste rade dalje. Samoprovjera prikazuje provajdera kao MISSING. | Unesite ključ ([docs/videodienste.md](docs/videodienste.md)) ili uklonite provajdera iz `VIDEO_PROVIDER`, ponovo pokrenite. |
| Kredit kod video provajdera | Provajder odgovara greškom (često HTTP 402/429 ili „insufficient balance“), agent dobija tekst u rezultatu. Nijedan drugi provajder ne uskače. | Dopunite kredit ili izaberite drugog provajdera preko `provider` ili u `VIDEO_PROVIDER`. |
| `FAL_KEY` (uz `VIDEO_PROVIDER=fal`, `VIDEO_AI=fal` ili `AUDIO_PROVIDER=fal`) | `video_generate`, `video_ai` odnosno `sound_generate` javlja „FAL_KEY is missing“ i ništa ne pravi. | Unesite ključ sa fal.ai ili uklonite red `VIDEO_AI`/`AUDIO_PROVIDER`. |
| `ELEVENLABS_API_KEY` (bolji glasovi po potrebi) | Sve radi kao prije s lokalnim glasovima. Ako se ipak koristi `engine: elevenlabs` ili `TTS_ENGINE=elevenlabs`, ili ElevenLabs/OpenAI ne uspije (ključ, kredit, internet), govori lokalni glas, a rezultat počinje s „NOTE: … nicht genutzt“ i razlogom. U filmu se red pri sljedećem `voices` ponovo pokuša s cloud glasom. Sa `TTS_FALLBACK=0` zadatak se umjesto toga prekida. | Ključ sa elevenlabs.io upisati u `.env` i ponovo pokrenuti. Uputstvo: 📖 → „🎙 Voices and ElevenLabs“. |
| Kredit ili internet kod ElevenLabsa, odnosno `OPENAI_API_KEY` (`TTS_ENGINE=openai`) | Uskače lokalni glas, a rezultat sadrži NOTE s HTTP kodom. U filmu se red pri sljedećem `voices` ponovo pokušava s cloud glasom. Sa `TTS_FALLBACK=0` zadatak se umjesto toga prekida. Ako nema ni lokalnog glasa, `speak` javlja "No speech output available". | Dopunite kredit ili provjerite ključ. Za zamjenski glas instalirajte espeak-ng ili Piper. |
| AI saradnika kojeg je CEO tek zaposlio | Novi saradnik se pravi, ali ne dobija zadatke. Ako CEO poslije toga ponovo planira, zadatak se prekida sa „These employees have no AI assigned yet: …“ (još nije dodijeljen AI). U meniju **⚠ Models** stoji kao „No AI yet“. | Dodijelite AI u meniju ⚠ Models i odgovorite „Weiter“ u pošti. |
| Prava saradnika kojeg je zaposlio CEO | Sistem dodaje prava koja nedostaju na osnovu uloge (lista gore). Ako se nijedna ključna riječ ne poklapa, dobija samo *čitanje fajlova* i može odgovoriti samo tekstom. | Označite prava u panelu agenta ili CEO-u preciznije zadajte ulogu. |
| Saradnik kojeg CEO želi otpustiti ili izmijeniti | Ako tog imena nema u njegovom timu (greška u kucanju, drugi tim, već otpušten), uputstvo se preskače i bilježi u rezultatu. Ako saradnik još ima otvoren zadatak, ostaje. | Ništa, ili kasnije ponovo zadajte. |
| `video_providers.py` (programski fajl) | Alati za video, zvuk i cloud glasove nestaju za agente, sve ostalo radi dalje. | Ponovo pokrenite `git pull`, fajl je dio programa. |
| `GITHUB_UPLOAD_TOKEN` ili `GITHUB_UPLOAD_REPO` | GitHub se pod ☁️ Cloud prikazuje kao „not set up”, agentima se ne nudi kao cilj. Sve ostalo radi. | Unesite token i repo ([docs/cloud.md](docs/cloud.md), na njemačkom), ponovo pokrenite. |
| CUPS (`lp`) na Pi-ju, štampač ili pravo CEO-a na štampanje | Pod 🖨 Printer piše „CUPS missing” ili postoji samo testni štampač. 🖨 Print javlja „No printer chosen yet” ili „Printing is blocked” i ništa ne šalje. | `./install.sh --print`, podesite štampač ([docs/drucken.md](docs/drucken.md)), izaberite ga i dozvolite pod 🖨 Printer. |
| Štampač je pronađen, ali papir ne izlazi (zaustavljen, offline, bez drajvera/`raw`, zaglavljen posao) | Nakon slanja Hyperstead nekoliko sekundi provjerava posao (`PCL_PRINT_CHECK_WAIT`, standardno 6) i umjesto „poslano” javlja uzrok. 🩺 Check printer prikazuje stanje, red i drajver. | Otklonite uzrok iz poruke, tabela „Testseite kommt nicht heraus” u [docs/drucken.md](docs/drucken.md) (na njemačkom). |
| `GDRIVE_CLIENT_ID`/`GDRIVE_CLIENT_SECRET` ili `ONEDRIVE_CLIENT_ID` | Servis ostaje „not set up”, dugme „Sign in” ne postoji. | Registrujte aplikaciju i unesite redove ([docs/cloud.md](docs/cloud.md)), ponovo pokrenite. |
| Prijava kod Google-a/Microsoft-a (folder `tokens/`) | Servis stoji na „not signed in”. Otpremanje javlja „not signed in yet” odnosno „sign-in expired” i ništa ne otprema. | ☁️ Cloud → Prijava. Pri selidbi sa Pi-ja na laptop jednostavno se ponovo prijavite na laptopu. |
| Fajl veći od 50 MB za Telegram | Telegram ga ne prima. `/datei` ga označava sa ⚠️ i ne šalje ga, agent dobija napomenu. | Kao cilj izaberite Google Drive, OneDrive ili GitHub. |
| `cloud_upload.py` (programski fajl) | Hyperstead se ne pokreće (greška pri uvozu). | Ponovo pokrenite `git pull`, fajl je dio programa. |
| `YOUTUBE_CLIENT_ID`/`YOUTUBE_CLIENT_SECRET` | Priprema i analiza i dalje rade. Otpremanje javlja „YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET are missing“, agenti saznaju da nijedan kanal nije prijavljen. | Napravite Google Cloud projekat i upišite redove ([docs/youtube.md](docs/youtube.md)), ponovo pokrenite. |
| YouTube prijava (`tokens/youtube-<jezik>.json`) | Nema otpremanja za ovaj kanal („not signed in“). Dok je Google projekat u test režimu, prijava ističe nakon 7 dana („sign-in expired“). | `python youtube_channel.py login de` (ili `en`, `tr`) na računaru na kojem radi Hyperstead. |
| `tzdata` (samo Windows) | Raspored javlja „Unknown time zone“, paketi ne dobijaju termin. | `venv\Scripts\pip install -r requirements.txt` |
| `youtube_channel.py` (programski fajl) | Hyperstead se ne pokreće (greška pri uvozu). | Ponovo pokrenite `git pull`, fajl je dio programa. |
| `PCL_ALLOW_WERKSTATT=1` | Polje „Radionica“ je sivo, nijedan agent ne dobija `befehl` ni `nachruesten`. Sve ostalo radi kao i prije. | Dodajte red u `.env`, ponovo pokrenite, označite polje kod agenta ([docs/werkstatt.md](docs/werkstatt.md)). |
| Program koji je agentu potreban (npr. Node.js, Remotion, Python paket) | Agent sa radionicom podnosi zahtjev za dopunu: CEO ga provjerava, vi dobijate ✅/❌ preko Telegrama i pod ✋ Odobrenja. Nakon vašeg „da“ server instalira i zadatak se nastavlja. Bez radionice agent samo navodi šta nedostaje. | Pročitajte zahtjev i odlučite. Bez Telegrama samo preko weba. |
| Node.js na Pi-ju ili sudo/apt zahtjevi iz radionice | Servis radi bez root prava (`NoNewPrivileges`). Hyperstead odmah odbija zahtjeve `sudo`/`apt install` i agentu daje put bez sudo-a, pa ne dobijate zahtjev koji ne može uspjeti. `./install.sh --all` sada instalira i Node.js. | `./install.sh --node` ili `bash deploy/node-ohne-sudo.sh --remotion`; sistemske biblioteke koje nedostaju instalirajte sami sa `sudo apt install …` ([docs/werkstatt.md](docs/werkstatt.md)). |
| AI CEO-a (kod zahtjeva za dopunu) | Zahtjev stiže direktno vama uz napomenu „No CEO with AI“ ili „CEO not reachable“. | Odlučite sami ili dodijelite CEO-u AI. |
| `werkstatt.py` (programski fajl) | Hyperstead se ne pokreće (greška pri uvozu). | Ponovo pokrenite `git pull`, fajl je dio programa. |
| `growth.py` (programski fajl) | Hyperstead se ne pokreće (greška pri uvozu). | Ponovo pokrenite `git pull`, fajl je dio programa. |
| Svijet projekta nikad nije izabran | Projekat prikazuje svijet svemira s njegovim nivoima i pojmovima. | Ništa ne treba raditi. Svjetovi Svemir i Atom se više ne nude u meniju grafike. |
| Datoteke logotipa u `static/logo/` | Bočna traka i stranica za prijavu prikazuju prazno polje za sliku, kartica preglednika nema ikonu. Sve ostalo radi normalno. | Ponovo pokrenuti `git pull`. Logotip se može ponovo napraviti sa `docs/logo/logo_blender.py` ([uputstvo](docs/logo-prompt.md), na njemačkom). |
| Raniji svijet (Ceh, Tycoon, Gizmo grad) sačuvan u projektu | Projekat automatski prikazuje svemir. Bodovi, nivo i rangovi ostaju isti, mijenjaju se samo nazivi i ikone. | Ništa ne treba raditi. |
| Danas nema poziva vještačke inteligencije (operativni centar, 💶 u traci) | Prikazuje 0 $ odnosno „no calls“. | Ništa ne treba raditi. Troškovi su procjene, vlastite cijene preko `PCL_PRICES` u `.env`. |
| Tabela `firm_links` (starija `data.db`) | Pri pokretanju se automatski pravi prazna: u gradu i kosmosu još nema saradnje. | Ništa. |
| Logotip firme `.logo.png` / `.logo.jpg` / `.logo.webp` u folderu projekta | Firma u gradu i kosmosu nema logotip, sve ostalo radi normalno. | U prozoru s informacijama o firmi (🏙/🌌, dodirni firmu) pod „Logo“ izaberi 🖼 Hochladen: PNG, JPEG ili WebP, najviše 2 MB. |
| Još nema projekta | Grad i kosmos prikazuju "No company yet". | Dugmetom "＋ New project" s lijeve strane napravite firmu (praznu ili iz šablone). |
| Preglednik ništa ne čuva (privatni prozor) | Svijetlo/tamno, izabrana grafika (svemir, vrsta organigrama, atom, nacrt), pomjerene kartice organigrama, pokreti i režim pomoći se pri svakom učitavanju vraćaju na zadano. | Koristite običan prozor; podaci projekata nisu pogođeni. |
| Agenti u nacrtu leže jedan preko drugog (npr. svi na istom mjestu) | Linije veza se ne vide. Pri otvaranju nacrta Hyperstead ih jednom automatski raspoređuje i javlja to. | Ništa, ili pritisnite „🗂 Arrange“. |
| Historija za dugme ← (prethodna grafika) | Historija postoji samo u otvorenoj kartici. Nakon ponovnog učitavanja ili u novoj kartici ← je sivo dok ponovo ne promijenite grafiku. | Ništa. |
| Neki drugi jezik osim engleskog na kontrolnoj ploči | Kontrolna ploča, upute agentima, šabloni i sistemski tekstovi su na engleskom. Ono što sami upisujete u polja ostaje na vašem jeziku, a agenti odgovaraju i izvještavaju na jeziku na kojem pišete. | Neka preglednik prevede (Chrome/Edge: desni klik → „Prevedi“). |
| Nema prave vještačke inteligencije u projektu (samo `mock` ili bez dobavljača) | Fiksne poruke u Telegramu i u poštanskom sandučiću (npr. „✅ Done“, napomene o odobrenju) ostaju na engleskom jer nema ko da ih prevede. Izvještaji agenata ipak stižu na vašem jeziku čim agenti imaju vještačku inteligenciju. | Dajte CEO-u (ili drugom agentu) pravu vještačku inteligenciju; od tada ona automatski prevodi poruke. |
| `PCL_TRANSLATE` u `.env` (zadano `1`) | Sa `PCL_TRANSLATE=0` sve fiksne poruke ostaju na engleskom i nema dodatnih poziva vještačkoj inteligenciji za prijevode. Bez unosa se prevodi. | Uklonite red ili postavite `PCL_TRANSLATE=1`, ponovo pokrenite Hyperstead. |
| Vaš jezik još nije prepoznat (svježa instalacija ili samo kratke poruke kao „ok“) | Do vašeg prvog dužeg teksta (otprilike od 12 slova, ne komanda) fiksne poruke ostaju na engleskom. | Napišite zadatak ili poruku u chatu na svom jeziku. |
| `handover/assignment-<broj>.md` u folderu projekta | Hyperstead pravi datoteku pri prvom koraku zadatka. Ako je obrisana, zadatak se nastavlja, samo sljedeći model ne vidi dosadašnje stanje. | Ništa. Sa `PCL_HANDOVER=0` u `.env` datoteka se ne piše. |
| `PCL_AUTO_RESUME`, `PCL_RETRY_MIN`, `PCL_RETRY_MAX` u `.env` | Zadano: uključeno, prvo čekanje 5 minuta (udvostručuje se, najviše 120), najviše 6 pokušaja. Nakon toga zadatak se smatra neuspješnim. Sa `PCL_AUTO_RESUME=0` zadaci kod greške i nakon ponovnog pokretanja odmah propadaju, kao ranije. | Ništa, ili promijenite vrijednosti u `.env` i ponovo pokrenite Hyperstead. |
| Kolone `retries` i `retry_at` (starija `data.db`) | Dodaju se automatski pri pokretanju. | Ništa. |
| Rust folder za gradnju `.rust/<ime>/target-<verzija>-<oznaka>` | Svaka verzija Rusta gradi u vlastitom folderu, pa stari ostaci gradnje više ne izazivaju grešku E0514. Stari folder `target/` ostaje i više se ne koristi. | Ništa. Ako vam treba prostor, sami obrišite stare foldere `.rust/*/target`. |

## Pristup sa interneta

Aplikacija namjerno sluša samo na `127.0.0.1`. Umjesto otvaranja porta koristite tunel.
Ovo je potrebno i ako vaš mobilni ruter ne dozvoljava dolazne veze (CGNAT).

### Opcija A (preporučeno): Tailscale, privatno, samo za vaše uređaje

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up                    # otvorite link za prijavu u pregledaču
sudo tailscale serve --bg 8787       # HTTPS adresa samo u vašem tailnet-u
```

Instalirajte Tailscale i na telefon/laptop, pa otvorite prikazanu adresu `https://dexter….ts.net`.
U `.env` dodajte: `TRUST_PROXY=1`, zatim ponovo pokrenite servis.
**Ne** koristite `tailscale funnel`, to bi aplikaciju stavilo na javni internet.

### Opcija B: Cloudflare Tunnel, javna adresa sa vlastitim domenom

```bash
# instalirajte cloudflared (vidi developers.cloudflare.com/cloudflare-one/connections/connect-networks)
cloudflared tunnel login
cloudflared tunnel create hyperstead
cloudflared tunnel route dns hyperstead agents.vas-domen.de
# ~/.cloudflared/config.yml:  ingress: - hostname: agents.vas-domen.de  service: http://127.0.0.1:8787
cloudflared tunnel run hyperstead
```

Dodatno se snažno preporučuje: stavite ispred **Cloudflare Access** (prijava e-poštom).
U `.env`: `TRUST_PROXY=1`. Komande se mogu mijenjati; u sumnji vrijedi zvanično uputstvo.

Sa `TRUST_PROXY=1` aplikacija se pokreće samo ako `APP_TOKEN` ima najmanje 12 znakova.

## Rukovanje

| Radnja | Kako se radi |
|---|---|
| Napravite agenta | prevucite stavku iz palete na površinu (ili kliknite na nju) |
| Povežite | prevucite donju tačku čvora na drugi čvor (= šef → saradnik) |
| Prekinite vezu | kliknite na liniju veze |
| Pomjeranje | prevucite čvor; prevlačenje pozadine = pomjeranje prikaza; točkić miša = zumiranje |
| Podešavanje | kliknite čvor → panel desno |
| Dodijelite zadatak | panel → kartica „Aufgaben“ (zadaci) |
| Odobravanje | bočna traka „Freigaben“ (odobrenja) |

## Kako firma radi

Šef dobija zadatak i **planira** (raspoređuje podzadatke) ili ga sam obavlja. Čim su svi
saradnici gotovi, on se ponovo budi, **čita njihove izvještaje**, vraća nedostatke uz povratnu informaciju ili
sažima sve i izvještava svog šefa. Tako se rezultat penje kroz koliko god nivoa.
Status „Waiting for team“ (čeka tim) znači: šef čeka svoje ljude. U kartici zadataka vidite cijelo stablo.

## Svemir i rast

Svaki projekat je mali **univerzum** koji raste sa svojim uspjesima. Svemir mijenja samo riječi, ikone i boje
interfejsa. Agenti uvijek rade s jasnim pojmovima (zadatak, izvještaj, tim), tako da njihov kvalitet ostaje isti.

| U svemiru | Značenje u timu |
| --- | --- |
| ☀️ Sunce | najviše rukovodstvo (npr. CEO) |
| 🪐 Planeta | odjel ili poslovođa, kruži oko Sunca |
| 🌙 Mjesec | uposlenik, kruži oko svoje planete (ko je još niže, mali je mjesec mjeseca) |
| Nivoi | ☄️ Asteroid → 🪐 Planeta → ☀️ Sunčev sistem → ✨ Zvjezdano jato → 🌌 Galaksija |
| Rangovi agenata | ☄️ Kometa → 🌙 Mjesec → 🪐 Planeta → ⭐ Zvijezda |

Bodovi se zovu zvjezdana prašina, zadaci se zovu misije. Raniji svjetovi Ceh, Tycoon i Gizmo grad više ne postoje; postojeći projekti automatski prikazuju svemir, bodovi i nivoi ostaju sačuvani. Interfejs prikazuje nazive na njemačkom.

**Svijet Atom:** Napomena: prikazi Svemir i Atom se više ne nude u meniju grafike (samo Classic i Modern); ovo opisuje crtež koji je još u kodu. Pored svemira postoji i drugi svijet. Ako u izboru grafike izabereš ⚛️ Atom, za projekat važi svijet Atom, a sa 🌌 Weltall ponovo svemir (i u traci rasta, pri proslavi i u Telegramu). Velika kugla = najviše rukovodstvo, srednje kugle = vođe timova, male kugle = uposlenici. Nivoi: ✴️ Kvark → ⚛️ Atom → 🧪 Molekul → 💎 Kristal → 🧬 Ćelija; rangovi: · Neutrino → ⚡ Elektron → 🔴 Proton → 💠 Nukleon (interfejs prikazuje njemačke nazive). Bodovi se zovu energija, zadaci eksperimenti. Bodovi i granice nivoa isti su u oba svijeta. Organigram i nacrt zadržavaju posljednji izabrani svijet.

**Upotreba:** Traka iznad površine prikazuje nivo, napredak do sljedećeg nivoa i najvažnije brojeve. Desno prebacujete između svijetlog i tamnog prikaza (🌓) i sa ⓘ otvarate pregled nivoa, bodova i rangova. Rang svakog agenta je prikazan kao ikona na njegovoj kartici.

**Sunčev sistem:** Padajuće dugme desno u traci (npr. “Org chart: Tree ▾”) bira grafiku: tri organigrama, nacrt (uređivač čvorova) ili pod Modern sve firme kao grad, kosmos ili molekule. Svemir je nacrtan detaljno: sunce sa zracima i pjegama, planete sa noćnom stranom, oblacima ili pojasevima, mjeseci sa kraterima, pojas asteroida, daleke galaksije i Mliječni put. Planete i mjeseci polako kruže, a planete i sunce se pritom okreću i oko vlastite ose (oblaci, pojasevi i sunčeve pjege klize preko površine, sunčev vijenac zraka kruži), a u fazi galaksije okreće se i spirala u pozadini; kada mišem pokažete na jedan od njih, sve se zaustavi da biste ga lako pogodili. Plavi prsten koji pulsira znači "radi", žuti prsten "čeka vaše odobrenje", crveni prsten "greška", ljubičasti isprekidani prsten "čeka svoj tim". Dodir na Sunce ili planetu prikazuje tim i radnje, dodir na mjesec otvara agenta. Sa svakim nivoom nebo je punije, od zvjezdanog jata svijetle magline, a kao galaksija pojavljuje se spirala. Svemir ostaje taman i u svijetlom prikazu. Na telefonu se umjesto mape prikazuje lista: Sunce, ispod njega svaka planeta sa svojim mjesecima. Pokreti se isključuju kada uređaj traži „smanji pokrete“.

**Organigram:** prikazuje tim u tri vrste, svaka je posebna stavka u izboru grafike: ⬇ Baum (stablo odozgo nadolje, uposlenici bez vlastitog tima stoje jedan ispod drugog), ➡ Gliederung (jedan red po agentu, uvučeno po nivou, najbolje za telefon) i ◎ Kreis (krug, rukovodstvo u sredini, svaki nivo jedan prsten). Boja pokazuje stanje: zeleno spremno, plavo radi, žuto čeka vaše odobrenje, crveno greška, ljubičasto čeka tim, sivo pauzirano. Dodir otvara agenta. Kartice se mogu prevlačiti, linije ih prate; uređaj to pamti po projektu i vrsti, „↺ Reset layout“ vraća raspored. Ako karticu spustite na drugu (ili u nacrtu agenta na drugog agenta), Hyperstead prvo pita i tek onda ga stavlja u taj tim.

**Atom:** ⚛️ prikazuje tim kao molekularnu mrežu: sjajne kugle povezane štapićima. Velika plava kugla je najviše rukovodstvo, srednje šarene kugle su vođe timova, male kugle uposlenici. Svaka kugla je štapićem vezana za svog nadređenog, pa se hijerarhija vidi po veličini i vezama; sve je raspoređeno slobodno i prostorno kao model molekula, a ne u krutim redovima. Svaka firma ima vlastiti molekul: oblik i boje proizlaze iz firme, velika kugla nosi boju projekta. U modernom prikazu ⚛️ Molekül prikazuje sve firme kao molekule jedne pored drugih; partnerske firme povezane su svijetlećim štapićem između svojih rukovodstava, po kojem putuju iskre (više kada obje rade). Dodir uvećava molekul, svaka kugla otvara odjel i agenta. Grafika miruje, da bi se mogla čitati na miru. Kao svijet, slika raste s nivoom: kao kvark u jezgru svijetle tri kvarka, od molekula su susjedni atomi povezani vezama, od kristala u pozadini leži atomska rešetka, kao ćelija dodaju se ćelijski zid i dvostruka spirala DNK. Stanje i dodir rade kao u organigramu.

**Engleski interfejs, nazad i mjeseci:** Kontrolna ploča je na međunarodnom engleskom; ostale jezike daje prevodilac preglednika. Neki nazivi dugmadi u ovom uputstvu su još stari njemački (npr. Dugme **←** lijevo od menija grafike vraća na prethodnu grafiku, tačno u dizajnu u kojem ste bili (i nazad u otvorenu firmu ili odjel). U info-kartici firme više nema dugmeta „📐 Firma öffnen“; dodir na ime direktno otvara agenta, a grafika ostaje ista. U 🌌 Kosmosu su saradnici mjeseci koji kruže oko svoje planete (odjela); planete i sunca se uz to okreću oko vlastite ose, a mjeseci samo kruže oko svoje planete.

**Sve na engleskom, komunikacija na vašem jeziku:** Sve što Hyperstead sam piše sada je na engleskom: interfejs, savjeti pri prelasku mišem, poruke o greškama, pitanja za potvrdu, upute agentima, šabloni firmi, poruke alata i samotest. Ono što sami unosite (zadaci, chat, ciljevi, imena) ostaje na vašem jeziku. Agenti odgovaraju, izvještavaju i prave datoteke za vas na jeziku na kojem pišete, bilo da je to njemački, turski, albanski, svahili, ruski ili kineski; zakazani zadaci i kontrolni obilazak također prate vaš posljednji jezik. Fiksne poruke u Telegramu i u poštanskom sandučiću vještačka inteligencija vašeg CEO-a automatski prevodi na vaš jezik (jednom po tekstu, zatim iz keša). Telegram komande se sada zovu /new, /project, /file i /help (stare njemačke i dalje rade). U meniju grafike grupa „Classic“ prikazuje samo tekst bez simbola („Org chart: Tree“, „Org chart: Outline“, „Org chart: Circle“, „Blueprint“). Folderi i ključevi koje agenti već poznaju (npr. `wissen/`, `film/film.json` s njemačkim ključevima) ostali su isti. Rust paket sada sadrži `README.txt`, `TEST_REPORT.txt`, `source/` i `program/`.

**Operativni centar:** 🛰 u bočnoj traci (ili dodir na brojeve u traci rasta) na prvi pogled prikazuje šta trenutno radi i čeka, koja odobrenja su otvorena, šta nije uspjelo u posljednjih 7 dana (sa ↻ Neu), rasporede (sa ▶ Jetzt), poruke o greškama i posljednje događaje. Uz to prikazuje procijenjene troškove vještačke inteligencije za danas i posljednjih 7 dana; današnji trošak stoji i kao 💶 u traci. Svi brojevi dolaze iz postojećih zadataka, odobrenja, rasporeda i historije, ništa nije izmišljeno.

**Napredovanje i rukovanje:** Kada projekat dostigne novi stepen, pojavi se kratka proslava s novim stepenom i sljedećim ciljem (Telegram šalje istu poruku). Kada agent napreduje u rangu, pojavi se kratko obavještenje. Pod ⓘ u traci možete za ovaj uređaj isključiti pokrete i efekte proslave; ako uređaj traži „smanji pokrete“, sve ionako ostaje mirno. Svi prozori se zatvaraju tipkom Esc, Sunce, planete i mjeseci u svemiru mogu se koristiti tipkama Tab i Enter.

**Uputstvo i pomoć:** 📖 Guide na vrhu bočne trake otvara uputstvo za upotrebu direktno u kontrolnoj tabli (poglavlja na rasklapanje, sa pretragom, bez preuzimanja, radi i offline). ⓘ na vrhu prozora vodi do odgovarajućeg poglavlja. Svako dugme pokazuje kratko objašnjenje kada pokažete mišem na njega. Na telefonu u uputstvu uključite režim pomoći: prvi dodir dugmeta ga objašnjava, drugi ga izvršava.

**Bodovi:** isporuka prihvaćena iz prve +10, nakon ispravke +5, zadatak označen kao završen u pošti +20,
neuspješno −3, zatražena dorada −5. Nivoi od 0 / 100 / 300 / 700 / 1500 bodova. Postojeći projekti automatski
dobijaju svoje dosadašnje uspjehe. Prelazak na viši nivo se jednom javlja putem Telegrama.

**Šta nivo ograničava:** samo koliko agenata rukovodstvo smije **samo** zaposliti (8 / 12 / 18 / 25 / neograničeno
u projektu) i koliko duboko (2 / 3 / 4 / 5 / puna dubina). Vi uvijek možete sve napraviti sami. Ograničenje se može
isključiti po projektu.

**Rangovi agenata** prema vlastitim prihvaćenim isporukama: od 0 / 5 / 20 / 60 (npr. šegrt, kalfa, majstor, veliki majstor).

## Mogućnosti agenata (internet, slike, fajlovi)

Agenti rade u krugovima: traže alate, server ih izvršava i vraća rezultate, sve dok nisu
gotovi (najviše `PCL_MAX_TOOL_STEPS`). Prava po agentu: **pretraga interneta**, **slike**, **čitanje fajlova projekta**
(i, kao ranije, pisanje fajlova).

| Alat | Šta radi | Bez ključa |
|---|---|---|
| `web_search` | pretraga weba (zakoni, cijene, konkurencija …) | DuckDuckGo; bolje: `SEARXNG_URL`, `BRAVE_API_KEY` ili `TAVILY_API_KEY` |
| `fetch_url` | čita web stranicu kao tekst | da |
| `browse_page` | otvara stranicu u pravom pregledaču (JavaScript radi), opciono sa snimkom ekrana koju agent vidi kao sliku | da, treba `./install.sh --browser` |
| `image_search` / `image_save` | traži slobodno licencirane fotografije i čuva ih u `assets/`, sa autorom i licencom | Openverse; opciono `PEXELS_API_KEY` |
| `image_generate` | pravi AI sliku kao PNG, opciono sa do 4 referentne slike iz projekta (isti likovi i stil kroz seriju), format kvadrat/vertikalno/horizontalno i ciljna putanja u `assets/`, `output/` ili `karten/`. Pravo **Slike** ili **Mediji** | Pollinations (bez ključa: bez referentnih slika; sa `POLLINATIONS_API_KEY` i Pollen kreditom: model preko `POLLINATIONS_MODEL`, sa referentnim slikama); `IMAGE_STYLE` postavlja fiksni stil crtanja; ostali: `nvidia` (FLUX preko build.nvidia.com), `cloudflare` (Workers AI, FLUX.2 klein sa referentnim slikama), `hf` (Hugging Face), model svakog preko `IMAGE_MODEL`; besplatno sa referentnim slikama na vlastitom računaru: `IMAGE_PROVIDER=sdcpp` ([uputstvo](docs/laptop-bildrechner.md)); bolje `IMAGE_PROVIDER=openai` sa `OPENAI_API_KEY`, `gemini`, ili `openrouter` sa `OPENROUTER_API_KEY` |
| `list_files` / `read_file` | čita fajlove u folderu projekta (npr. tekstove kolega) | da |

Sve što se napravi nalazi se pod `workspace/<id-projekta>/`. U bočnoj traci **📁 Dateien** prikazuje fajlove, otvara `index.html`
kao web stranicu (izolovan sandbox) i preuzima sve kao ZIP. Link sadrži tajni ključ.

**Projekti i prikazi:** U bočnoj traci ispod „Projekte“ veliko dugme „＋ New project“ otvara prozor: prazan projekat ili gotova firma iz šablona. Meni grafika gore desno ima dvije grupe: **Klassik** (tri organigrama stablo, pregled i krug, kao i nacrt) i **Modern** (sve firme kao grad, kosmos ili molekul). Svemir i molekul za pojedinačni projekat više ne postoje; ko ih je posljednji put imao otvorene, dolazi u organigram. Gornja traka s projektom i rastom ostaje i u gradu, kosmosu i molekulu, kao i traka „Add agent“ ispod nje (novi agenti idu u projekat izabran gore). Grad, kosmos i molekul mogu se okretati i naginjati: dugmad ⟲ ⟳ ⤵ ⤴ ⌂ dolje desno, prevlačenje desnom tipkom miša ili dva prsta na telefonu. Kad lijevo izabereš projekat, njegova firma zasvijetli u gradu, kosmosu i molekulu, a ostale se povuku. U gradu je svaka firma zgrada vlastitog stila, a svjetla se pale dok firma radi; kad je otvoriš, svaki nivo hijerarhije ima svoj sprat, koliko god duboko firma ide: na najvišem spratu uprava, ispod rukovodioci odjela, pa svaki sljedeći nivo; svaka osoba ima svoju kancelariju, pa odjel sa 4 osobe na jednom nivou tamo ima 4 kancelarije u svojoj boji; svaki sprat slaže svoje kancelarije centrirano i s jednakim razmacima, odjeli ostaju zajedno, a zgrada je široka koliko i njen najpuniji sprat, a desno je organigram. S uspjehom zgrada raste: više nivoa daje više spratova, od nivoa 2 dolaze aneks i krovna bašta, od nivoa 3 antena, od nivoa 4 helidrom. U kosmosu je svaka firma sunčev sistem (sunce = uprava, planete = odjeli); sunce raste sa nivoom i timom, planete kruže i na telefonu i zaustave se ispod prsta, a imena ostaju čitljiva kad se udalji prikaz. Svaka firma može u prozoru s informacijama pod „Logo“ dobiti vlastiti logotip (🖼 Hochladen, PNG/JPEG/WebP do 2 MB): u gradu stoji kao svijetleći znak na krovu, u kosmosu usred sunca.

**Šabloni firmi** (dugme „＋ New project“): *Web agencija*, *Računovodstvo/poreska kancelarija*, *Uvoz/izvoz trgovina* prave projekat,
organigram, radna uputstva i prava u potpunosti. Vlastite firme: napišite cilj projekta („vi ste …“, zemlja,
djelatnost), podesite agente i prava. Agenti dobijaju datum i cilj projekta i trebaju prvo istražiti stvari koje se mijenjaju (zakoni,
cijene) i navesti izvore.

**Sigurnost alata:** preuzimanje stranica ograničeno je na javne adrese (bez localhost-a, LAN-a, Tailscale-a,
metapodataka iz clouda; preusmjeravanja se provjeravaju pojedinačno). Za agente sadržaj weba vrijedi kao nepouzdan podatak,
ali pripremljena stranica ipak može uticati na model: ne dajte agentima sa pristupom internetu shell i provjeravajte rezultate.
Agenti namjerno **nemaju** alate za kupovine, narudžbe, plaćanja ili slanje e-pošte; daju nacrte i preporuke.
Licence za slike (CC) često traže navođenje autora; urednik slika to upisuje u `bildnachweis.md`.

## Mediji, dokumenti i vlastiti fajlovi

Uz pravo **pravljenje medija i dokumenata** (i `ffmpeg`/fontovi na Pi-ju, vidi `install.sh`):

| Alat | Šta može |
|---|---|
| `video_edit` | seče video (`trim`), spaja (`concat`), **animaciju slajd-šou sa zumom** iz slika (`slideshow`, opciono sa zvukom), dodaje tekst/titlove/logo, mijenja ili miješa zvuk, mijenja brzinu, pretvara u GIF/WebM/MP3, izvlači nepomičan kadar |
| `speak` | pretvara tekst u glas govornika (espeak-ng offline; bolje: Piper; opciono Edge glasovi ili cloud glasovi ElevenLabs/OpenAI preko `TTS_ENGINE`), uz `voice`, `pitch`, `rate` za različite glasove |
| `film` | **animirani film uz Blender**: scenarij kao JSON, likovi (pas, mačka, zec, medvjed, miš, čovjek, vlastite slike ili `.blend` likovi), glasovi sa pokretima usta, pokreti, kamera, slika pregleda, renderovanje scenu po scenu, montaža sa titlovima ([uputstvo](docs/filmstudio.md)) |
| `write_file` | uz pravo **pisanje fajlova**: odmah pravi poglavlja, HTML, CSV itd., tako da se u istom zadatku od njih može napraviti PDF/DOCX/EPUB |
| `make_document` | iz Markdown poglavlja **PDF, DOCX, EPUB ili HTML** (A4/A5, naslovna strana, slike, dijakritici i turski znakovi); sa `html` PDF slobodnog rasporeda iz **HTML+CSS** (pravljenje šablona, preko WeasyPrint-a, učitava samo fajlove iz projekta) |
| `video_generate` | **AI video klip** iz teksta ili početne slike preko 12 provajdera: Google Veo/Omni, OpenAI Sora, OpenRouter, Runway, Luma, **Kling**, **MiniMax Hailuo**, **Wan**, Seedance, **Higgsfield** (podrazumijevano MiniMax H3), fal.ai, Replicate. Podrazumijevano isključeno, uključuje se sa `VIDEO_PROVIDER=…` + ključ, više njih odvojenih zarezom. **Naplaćuje se po klipu** kod provajdera, pretplate na aplikacije se uglavnom ne računaju ([uputstvo](docs/videodienste.md), na njemačkom) |
| `site_macro` | **MagicLight, Google Flow i druge stranice sa vašim nalogom**: robot u pregledniku (Playwright) koristi stranicu, čeka video i stavlja ga u `output/`. Podrazumijevano isključeno (`PCL_MACROS=1`), makroe jednom sami snimite ([macros/README.md](macros/README.md)). Rizik: može kršiti uslove korištenja i prestaje raditi kad se stranica promijeni |
| `video_ai` | AI obrada preko fal.ai: **povećanje rezolucije** videa, **sinhronizacija usana** sa snimkom glasa, **zvučni efekti** za nijemi video. Uključuje se sa `VIDEO_AI=fal` + `FAL_KEY` |
| `sound_generate` | **zvučni efekti ili muzika** iz opisa (ElevenLabs ili fal.ai), uključuje se sa `AUDIO_PROVIDER` |
| `media_info` | trajanje, rezolucija, kodeci |
| `download_file` | preuzima PDF, EPUB, Office, audio, video, ZIP sa interneta u `downloads/` |
| `read_file` | čita tekst, Markdown, HTML, **PDF, DOCX, EPUB**, i duge fajlove po dijelovima |
| `view_image` | **vidi** slike, snimke ekrana, mape, rasporede i stranice skeniranih PDF-ova (treba model sa razumijevanjem slika, npr. Claude, GPT-4o, Gemini) |

**Samokontrola:** kada agent napravi PDF, server ga poslije toga prikaže kao sliku (pregled svih stranica + 1. stranica uvećano) i pošalje
mu uz obavezu da provjeri svaki zahtjev zadatka i ispravi greške prije nego što javi (`PCL_SELF_CHECKS`, podrazumijevano 1, 0 = isključeno).

**Vlastiti fajlovi** (video za obradu, PDF-ovi, slike, rasporedi, tekstovi) otpremate u „📁 Files of this project“ ili ih šaljete
direktno u **💬 Chat** sa agentom (dugme 📎, prevucite ih ili nalijepite sliku, više odjednom). Završe u
`input/` (ime se čisti, postojeći fajlovi se nikada ne prepisuju nego postaju `name-1.png` …, granica `PCL_MAX_UPLOAD_MB`; ZIP fajlovi se odmah raspakuju u `input/<ime>/` da bi agenti mogli čitati sadržaj);
u četu agent dobija **sadržaj** direktno uz poruku (tekstovi, PDF-ovi, Word kao tekst, slike kao slike, ako model razumije slike;
inače prepoznavanje teksta). Sa **📂 aus input/** dodajete fajlove koji već stoje tamo, ili jednostavno upišete ime fajla u poruku, a „Give as task“ (pošalji kao zadatak) to prosljeđuje timu; gotovi rezultati su u `output/`, slike u `assets/`. Iskrena ograničenja: bez `video_generate` **nema AI generisanja videa** (tekst u video);
„animacija“ tada znači: scene kao slike uz AI slike + zum/pomjeranje + govornik + montaža, ili prava animacija likova uz Blender preko alata `film`. Uz `video_generate` nastaju
kratki klipovi; duži filmovi se sastavljaju sa `video_edit op=concat`. MagicLight i Flow nemaju API: sa `site_macro` robot u pregledniku ih koristi sa vašim nalogom, inače videe napravljene tamo otpremite u `input/`. Model iza Flow-a (Veo 3.1) dostupan je i preko fal: `FAL_VIDEO_MODEL=fal-ai/veo3.1/fast`. Na Raspberry Pi-ju
ffmpeg radi sporo (jedan minut 720p videa može trajati nekoliko minuta), vremensko ograničenje `PCL_FFMPEG_TIMEOUT` (podrazumijevano 1 sat po koraku).

**Skenirani PDF-ovi i slike (OCR):** `read_file` automatski čita skenove preko `tesseract` (`sudo apt install tesseract-ocr tesseract-ocr-deu poppler-utils`). To je sporo (oko 5–15 s po stranici na Pi-ju, granica `PCL_OCR_MAX_PAGES`) i može sadržati greške.

**Dobar glas govornika:** `./install.sh --piper` podešava Piper sa njemačkim glasom; poslije toga se automatski koristi za njemačke tekstove (ostali jezici: espeak-ng).

## Čet i šabloni

- **💬 Chat kartica** (u panelu agenta): slobodan razgovor sa svakim agentom, npr. sa vođom *Gedankenwerkstatt*-a, za filozofiranje,
  razvijanje ideja i preispitivanje. „📋 Give as task“ prosljeđuje razgovor agentu i njegovom timu; rezultat se vraća kao objava.
  Čet radi bez alata.
- **Šabloni firmi** (🏢): Web agencija, Računovodstvo/poreska kancelarija, Uvoz/izvoz trgovina, **Animaciona agencija**, **Izdavačka kuća/agencija sadržaja**,
  **Radionica ideja**, **Istraživački biro** (pronalazi i čita PDF-ove). Pri osnivanju birate model za vođu i saradnike.

## Pošta i Telegram

Čim je **zadatak na vrhu** (onaj koji ste dali agentu, obično CEO-u) gotov, neuspješan ili
blokiran, pošta je spremna za vas: u bočnoj traci „📬 Mail“ i, ako je podešeno, poruka na Telegramu sa
vrstom, zadatkom, brojevima tima i rezultatom. Lanac prava i izvještaja ispod radi kao i ranije.
U pošti možete označiti poruke (pojedinačno ili „Select all“) i ukloniti ih sa „🗑 Delete selected“;
„🧹 Empty mailbox“ nakon potvrde briše sve. Briše se samo pošta, zadaci, datoteke i historija ostaju.
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
| Pošaljete fajl, fotografiju, album, video ili glasovnu poruku | završi u `input/` izabranog projekta; natpis postaje zadatak (kao odgovor na objavu: za doradu), bez teksta fajl ide vašem sljedećem zadatku. Telegram botovi smiju preuzeti fajlove do 20 MB, veće otpremite preko weba |
| `/post`, `/status`, `/ok <Br.>`, `/neu <Tekst>`, `/projekt [Br.]` | pregled odnosno kratke komande |
| `/datei [riječ za pretragu]` | šalje vam fajl iz izabranog projekta (najnoviji kao dugmad, jedini pogodak stiže odmah; do 50 MB) |

Aplikacija Telegram samo pita spolja, ne otvara se nijedan port (radi i iza CGNAT-a). Samo ID čata iz
`.env` smije davati komande; koristite privatan čet, ne grupu. Odobrenja za shell komande namjerno
**ne** idu preko Telegrama; tamo stiže samo napomena.

## Prava po agentu

- **Delegiranje**: smije dodjeljivati zadatke *neposrednim* saradnicima (do `PCL_MAX_DEPTH` nivoa, podrazumijevano 8).
  Opciono se sami pokreću, inače ih pokrećete sami.
- **Ocjenjivanje rezultata**: šef smije vratiti posao sa povratnom informacijom na doradu (najviše 2 kruga po saradniku).
- **Čitanje**: šefovi uvijek vide izvještaje svojih saradnika; za to nije potrebno posebno pravo.
- **Pisanje fajlova**: samo u `workspace/<id-projekta>/`; putanje van toga se odbijaju.
- **Pokretanje koda** (podrazumijevano isključeno): `run_code` pokreće Python, JavaScript, Bash, Ruby, PHP ili Lua u sandbox-u, vidi dolje.
  Tu spada i `rust_project`: gradi i testira Rust programe i isporučuje gotov paket ([Rust programi](#-kompletna-izrada-rust-programa)).
- **Otpremanje u cloud** (podrazumijevano isključeno): gotove fajlove na GitHub, Google Drive, OneDrive ili vama preko Telegrama, uvijek tek poslije vašeg odobrenja ([☁️ Otpremanje u cloud](#️-otpremanje-u-cloud-github-google-drive-onedrive-telegram)).
- **Upravljanje YouTubeom** (podrazumijevano isključeno): priprema naslove, opise, ključne riječi, hashtagove i raspored kao fajlove i analizira CSV izvoze iz YouTube Studija. Svaki video se otprema tek nakon vašeg odobrenja ([docs/youtube.md](docs/youtube.md)).
- **Predlaganje shell-a**: samo ako server ima `PCL_ALLOW_SHELL=1`, i tada uvijek tek poslije odobrenja.
- **Radionica** (po defaultu isključena, samo uz `PCL_ALLOW_WERKSTATT=1`): radi sa pravim komandama u folderu projekta i preko CEO-a traži od vas programe koji nedostaju ([docs/werkstatt.md](docs/werkstatt.md), na njemačkom). CEO ovo pravo ne može prenijeti dalje.
- **Pauza**: blokira sve nove zadatke agenta.

Prava se provjeravaju **na serveru**. Ako model u svom odgovoru napiše nedozvoljenu radnju, ona se ignoriše i bilježi u historiji.

## Dobavljači AI-ja i izbor modela

Za svakog agenta birate **dobavljača i model** (panel → Podešavanja). Aplikacija modele uživo preuzima od dobavljača;
sa **▶ Test** odmah provjeravate ključ i model. Tako postavljate odgovarajući model po ulozi: najjači za šefove
(planiranje, provjera, razmišljanje), dobri modeli za tekst ili kod za saradnike, brzi i jeftini za jednostavan posao.

| Dobavljač | Ključ u `.env` | Napomena |
|---|---|---|
| Claude (Anthropic) | `ANTHROPIC_API_KEY` | Sonnet, Haiku, Opus … bira se po agentu |
| ChatGPT (OpenAI) | `OPENAI_API_KEY` | |
| OpenRouter | `OPENROUTER_API_KEY` | jedan ključ za stotine modela (Claude, GPT, Gemini, DeepSeek, Qwen, Llama …) |
| Groq, Gemini, DeepSeek, Qwen | `GROQ_API_KEY`, `GEMINI_API_KEY`, … | više ključeva odvojenih zarezom = rotacija kada se dostigne limit |
| Mistral, NVIDIA NIM, Together, Perplexity | `MISTRAL_API_KEY`, `NVIDIA_API_KEY`, `TOGETHER_API_KEY`, `PERPLEXITY_API_KEY` | Perplexity modeli (`sonar`) sami pretražuju web |
| Hugging Face, Cloudflare Workers AI | `HF_TOKEN` odnosno `CF_ACCOUNT_ID` + `CF_API_TOKEN` | male besplatne kvote |
| Ollama | – | lokalni modeli na Pi-ju |
| Claude (CLI, vaša pretplata) / ChatGPT (Codex CLI, vaša pretplata) | – | ugrađeno: `claude -p --tools "" --strict-mcp-config --no-session-persistence` (Claude bez vlastitih alata i konektora, samo tekst; radno uputstvo zamjenjuje sistemski prompt Claude Code-a) odnosno `codex exec --skip-git-repo-check --ephemeral -` (Codex sam radi u sandbox-u samo za čitanje), model u padajućem meniju (Claude: sonnet/opus/haiku); treba `PCL_ALLOW_CLI=1` i prijavljen program na Pi-ju |
| CLI agent | – | komanda koja čita prompt sa stdin-a, npr. `claude -p --model sonnet`; treba `PCL_ALLOW_CLI=1` |

**Važno:** web prijava (OAuth, „pretplata“) kod ChatGPT-a ili Claude-a ne može se čisto koristiti kao API; preuzimanje
web sesija krši uslove korištenja. Putevi: **API ključ** dobavljača (naplata po potrošnji, ne čet pretplata) ili
**CLI agent** sa zvaničnim CLI-jem, jednom prijavljenim. Aplikacija nema budžet: kod plaćenih API-ja i mnogo krugova sa alatima
mogu nastati troškovi; bilans po agentu vidite na čvoru.

## Sigurnost

- Stranica za prijavu sa potpisanim kolačićem (7 dana, `HttpOnly`, `SameSite=Strict`, `Secure` iza HTTPS-a).
- Poslije 5 pogrešnih lozinki zaključavanje od 10 minuta po IP adresi; svi pokušaji su u dnevniku revizije.
- Pišući API pozivi moraju imati vlastito zaglavlje (CSRF zaštita), uz CSP i dodatna zaglavlja.
- Shell i CLI agenti su podrazumijevano **isključeni**. Ko zna lozinku i ima postavljeno `PCL_ALLOW_SHELL=1`,
  može odobriti komande sa pravima korisnika aplikacije. `workspace/` je radni direktorijum, ali **nije sandbox**.
- `.env`, baza podataka i radni folderi su u `.gitignore`. Ključevi nikada ne pripadaju repozitorijumu.
- Kod botova za trgovanje (NEXUS) agentima nikada ne dozvolite trgovinu bez ljudskog odobrenja.

## Znanje firme i pamćenje

- **🧠 Znanje firme** (bočna traka): ono što svi agenti projekta uvijek trebaju znati (firma, klijenti, stil, cijene, pravila). Stoji u
  `wissen/firmenwissen.md` u folderu projekta. Svi `.md`/`.txt` fajlovi u `wissen/` idu uz svaki zadatak i u čet (zajedno do
  `PCL_KNOWLEDGE_CHARS`, podrazumijevano 8000 znakova); ostale dokumente tamo (PDF, Word …) agenti vide kao spisak i čitaju po potrebi.
- **Pamćenje po agentu**: agent na kraju zadatka može zapamtiti najviše 5 trajnih činjenica (preference, odluke, klijenti,
  šta je radilo). One se prikazuju u panelu agenta pod „🧠 Memory“ (pamćenje); možete ih mijenjati ili brisati. Granica `PCL_MEMORY_CHARS`
  (4000); najstariji unosi prvi ispadaju. Svaka nova bilješka je u dnevniku revizije.

## Ciljevi, odobrenja, upotreba

- **🎯 Ciljevi**: ciljevi i podciljevi po projektu. Pri dodjeljivanju zadatka opciono birate cilj; delegirani zadaci ga nasljeđuju.
  Šefovi vide ciljeve sa napretkom u promptu, a CEO-ov kontrolni obilazak to izvještava. Označeno = ostvareno.
- **Prvo pitaj** (prozor ✋ Approvals, po projektu, podrazumijevano isključeno): *Odobri plan najvišeg šefa* zadržava novi zadatak
  dok ne odobrite plan raspodjele; *Odobri izmjene tima* („Teamänderungen freigeben“) zadržava CEO-ovo zapošljavanje, otpuštanje i mijenjanje saradnika. Odobravanje/odbijanje i preko
  Telegram dugmeta. Odbijeno = zadatak završi kao ❌ u pošti; vaš odgovor na to tjera šefa da ponovo planira.
  Odobrenja za shell i dalje idu samo preko weba.
- **📊 Upotreba i troškovi**: pozivi, tokeni i procijenjeni troškovi po projektu, agentu i modelu (danas, 7, 30 dana). Bez limita.
  Pretplatni CLI-ji i Ollama broje se kao 0 $; od `PCL_ABO_WARN_5H` pretplatnih poziva u 5 sati (podrazumijevano 150, 0 = isključeno) stiže upozorenje na Telegramu.
  Cijene su grube procjene; vlastite zadajte preko `PCL_PRICES='{"sonnet": 5}'` (US$ po 1 milion tokena, dio naziva modela).

## Testovi

```bash
./venv/bin/pip install pytest && ./venv/bin/python -m pytest -q tests
```
Radi bez interneta i bez ključeva (dobavljač `mock`, vlastita baza).

## 🔌 Veze (webhook-ovi)

- **Izlaz:** u prozoru 🔌 Connections unosite adrese (n8n, Zapier, Make, vlastita usluga; i `http://127.0.0.1:…` na Pi-ju),
  sa opisom za agente i opcionim zaglavljima. Tajne pripadaju `.env` i koriste se kao `${NAME}`.
  Agenti sa pravom **„May use connections“** (smije koristiti veze) zovu ih alatom `call_connection`; agent ne može mijenjati
  adresu ni zaglavlja, samo šalje podatke. **„Only call after my approval“** (samo poslije mog odobrenja, podrazumijevano uključeno) svaki poziv prvo stavlja pod ✋ Approvals.
  **„Bei Post benachrichtigen“** (obavijesti u pošti) šalje svaki gotov rezultat zadatka na vrhu kao JSON na adresu. Vremensko ograničenje `PCL_CONN_TIMEOUT` (30 s).
- **Ulaz:** uključite „Aufträge von außen“ (zadaci spolja), zatim `POST /hook/<projekat>/<ključ>` sa `{"text": "…", "agent": "opciono"}`
  prima zadatak za šefa (npr. iz n8n, iOS prečice ili DEXTER-a). Bez prijave; štiti ga samo ključ u adresi.
  „New key“ (novi ključ) poništava staru adresu. Dostupna je samo onoliko koliko je dostupan i sam Hyperstead (npr. samo u tailnet-u).

## ☁️ Otpremanje u cloud (GitHub, Google Drive, OneDrive, Telegram)

- **Podešavanje:** pristupni podaci u `.env` (`GITHUB_UPLOAD_TOKEN` + `GITHUB_UPLOAD_REPO`, `GDRIVE_CLIENT_ID` + `GDRIVE_CLIENT_SECRET`,
  `ONEDRIVE_CLIENT_ID`), korak po korak u [docs/cloud.md](docs/cloud.md) (na njemačkom). Kod Google-a i Microsoft-a se zatim prijavljujete u prozoru
  **☁️ Cloud**: prikazuje kod koji na telefonu unesete na stranici Google-a odnosno Microsoft-a (radi bez HTTPS-a).
  Prijava se čuva u `tokens/` pored `.env`, nikad u bazi podataka.
- **Ciljni folder:** po projektu i servisu u prozoru ☁️ Cloud (podrazumijevano `Hyperstead/<ime projekta>`). Agenti smiju izabrati samo
  podfolder ispod njega, npr. kada ga navedete u zadatku.
- **Sami otpremite:** 📁 Fajlovi → ☁️ pored fajla → izaberite cilj i folder. Dobijate link.
- **Agenti:** pravo **„Smije otpremati u cloud”** (postavljate samo vi). Alat `cloud_upload`; svako otpremanje čeka pod ✋ Odobrenja,
  uz to stiže Telegram poruka. Poslije otpremanja link stoji u zadatku.
- **Podešavanje sa CEO-om:** pitajte glavnog šefa u 💬 Chatu, npr. „Pomozi mi da podesim GitHub”. On zna trenutno stanje svakog servisa i uputstvo i vodi vas korak po korak. Tokene nikad ne pišete u chat, nego ih sami unosite u `.env`.
- **Telegram:** `/datei` vam šalje fajlove do 50 MB na telefon, samo kada kliknete ili odobrite.
- GitHub: do 50 MB kao fajl u repou, veći kao prilog izdanju `paperclip-ablage` (do 2 GB). Google Drive: samo folderi i fajlovi koje je
  Hyperstead sam napravio (pravo `drive.file`). OneDrive: bilo koji folder. Testirano samo na simuliranim servisima.

## ▶️ YouTube kanal

- **Šta Hyperstead radi:** agent s pravom **„May manage YouTube“** popunjava `youtube/kanal.json` (naslov, opis, ključne riječi, hashtagovi po epizodi i jeziku) i od toga pravi po jedan paket za svaki video u `youtube/packages/`, raspored `youtube/schedule.csv` i listu za provjeru `youtube/REVIEW.md`. Na početku 2 do 3 epizode sedmično.
- **Otpremanje:** samo preko zvaničnog YouTube Data API-ja i samo nakon vašeg odobrenja **za svaki video** (✋ Approvals). Uvijek privatno, YouTube ga u zakazano vrijeme čini javnim. Bez skripte u pregledniku, bez automatske prijave.
- **Šta vi radite:** pravite kanale, Google Cloud projekat s `YOUTUBE_CLIENT_ID`/`YOUTUBE_CLIENT_SECRET` i jednom po kanalu `python youtube_channel.py login de|en|tr`. U test režimu prijava ističe nakon 7 dana.
- **Analiza:** otpremite CSV izvoz iz YouTube Studija, agent piše `youtube/reports/analysis-<datum>.md`. Hyperstead nikada sam ne preuzima brojke i ne preuzima tuđe videe.
- Uputstvo s izvorima i ograničenjima: [docs/youtube.md](docs/youtube.md) (na njemačkom). Testirano samo sa simuliranim odgovorima.

## 🖨 Štampanje večernjih izvještaja

👑 Kontrolni obilazak CEO-a na kraju radnog dana piše večernji izvještaj. U 📬 pošti i u zadacima CEO-a stoji dugme **🖨 Print**: jedan klik, kratka potvrda, zatim ide na štampač. Štampač birate pod **🖨 Printer** u bočnoj traci (Pi: mrežni štampač preko CUPS-a, `./install.sh --print`; Windows: dijeljeni štampač pod Štampači i skeneri). U istom prozoru CEO dozvoljava ili zabranjuje štampanje (pravo „May print evening reports”). **Testdrucker (Datei)** samo snima ispis kao tekstualni fajl u `workspace/.druck/`. Uputstvo: [docs/drucken.md](docs/drucken.md) (na njemačkom).

**Pravi štampač?** U prozoru 🖨 Printer izaberite štampač i kliknite **🧾 Testseite drucken** (štampaj probnu stranicu). Stranica navodi štampač, računar i vrijeme i sadrži posebna slova. Ako izađe na pravom štampaču, kliknite **Speichern** (sačuvaj). Sama probna stranica ništa ne čuva i ne treba joj pravo CEO-a na štampanje.

## 🌐 Pravi pregledač i ▶ pokretanje koda

- **Pregledač** (`./install.sh --browser`, instalira Playwright + Chromium, oko 400 MB, samo 64-bitni sistem): agenti sa pravom
  „Internet recherchieren“ (istraživanje interneta) dobijaju `browse_page`. Stranica radi uz JavaScript; agent dobija vidljiv tekst, veze i
  po želji snimak ekrana (vidi ga kao kod `view_image`; `save` ga čuva u `assets/screenshots/`). Svaki zahtjev stranice
  (skripte, okviri, XHR, WebSocket-i) mora ići na javnu adresu; LAN/localhost je blokiran, WebRTC i preuzimanja su isključeni.
  Samo jedan pregledač u isto vrijeme (RAM), vremensko ograničenje `PCL_BROWSER_TIMEOUT` (30 s). Vlastiti Chromium: `PCL_BROWSER_PATH`, isključeno: `PCL_BROWSER=0`.
- **Pokretanje koda** (`./install.sh --run`, instalira bubblewrap): pravo „May run code“ (smije pokretati kod, podrazumijevano isključeno) daje `run_code`.
  Skripta radi izolovano: **bez interneta**, vidljivi su samo `/usr` i folder projekta (samo za čitanje pod `/projekt`),
  bez `.env`-a, bez baze, bez kućnog foldera. Ono što skripta upiše u svoj radni direktorijum završi u `output/run/<vrijeme>/`
  (najviše 50 fajlova/50 MB). Granice: `PCL_RUN_TIMEOUT` (60 s), `PCL_RUN_MEM_MB` (1024). Pokreće Python/Node sistema,
  dakle samo pakete instalirane preko apt-a (npr. `sudo apt install python3-pandas python3-matplotlib`). Globalno isključeno: `PCL_ALLOW_RUN=0`.
  Provjera: `python3 selftest.py run browser`.

## 🦀 Kompletna izrada Rust programa

Agentu s pravima **„May program“**, **„May write files“** i **„May run code“** (smije programirati, pisati fajlove, pokretati kod) dajte zadatak kao
„Napiši mi Rust program koji …, s testovima, i isporuči gotov paket“. Agent tada radi od A do Ž:

1. Pomoću `write_code` pravi Cargo projekat, npr. `rust/rechner/Cargo.toml` i `rust/rechner/src/main.rs` s testovima (`#[test]`).
2. `rust_project` s `op=test` preuzima zavisnosti s crates.io, gradi program i pokreće testove.
   Greške se vraćaju s fajlom i redom, agent ih ispravlja i ponovo testira.
3. `op=package` još jednom testira, gradi release verziju i sprema **`output/<ime>.zip`**. Unutra: `program/` (gotov
   program), `source/` (izvorni kod s `Cargo.lock`), `TEST_REPORT.txt` i `README.txt`. Paket nastaje samo ako svi testovi prođu.

Paket dobijate u pošti ili pod **📁 Dateien** (pojedinačno ili u ZIP-u projekta). Ostale naredbe: `op=build`, `op=run` (s `args`, `stdin`).

- **Za koji sistem?** Program u `program/` odgovara računaru na kojem radi Hyperstead: s Pi-ja Linux program (ARM),
  s Windows laptopa `.exe`. Za drugi sistem sami pokrenite `cargo build --release` u folderu `source/`.
- **Izolacija (Pi/Linux):** Izrada, testiranje i pokretanje idu u bubblewrapu kao `run_code`: bez interneta, bez `.env`, bez home foldera,
  upisiv je samo folder za izradu `.rust/` projekta. Internet ima samo `cargo fetch` (preuzima zavisnosti, ništa ne pokreće).
  Cargo postavke (`.cargo/`) i `rust-toolchain` fajlovi iz projekta se ne koriste.
- **Windows:** Bez bubblewrapa alat ostaje isključen. S `PCL_CARGO_UNSAFE=1` u `.env` laptop gradi **bez izolacije**: kod agenata
  (testovi, `build.rs`) tada radi s vašim pravima i mogao bi čitati ili mijenjati fajlove na laptopu. API ključeve ne dobija u
  okruženju. Uključite samo ako vjerujete agentima i njihovim modelima.
- **Instalacija Rusta:** Pi `curl https://sh.rustup.rs -sSf | sh` (novije od `apt install cargo`), Windows `winget install Rustlang.Rustup`
  i u instalaciji uzmite i „Visual Studio Build Tools (C++)“. Zatim ponovo pokrenite Hyperstead i izvršite `selftest.py rust`.
- **Granice:** `PCL_CARGO_TIMEOUT` (900 s po koraku), `PCL_CARGO_MEM_MB` (3072, samo Linux), `PCL_CARGO_JOBS` (2), uvijek samo jedna
  Rust izrada istovremeno. Prva izrada na Pi-ju traje dugo, nakon toga cargo ponovo gradi samo ono što se promijenilo. Agent ima
  `PCL_MAX_TOOL_STEPS` (podrazumijevano 6) krugova alata po pokretanju; za veće programe pomaže veća vrijednost, npr. 12. Isključeno: `PCL_CARGO=0`.

## 🛠 Radionica: agenti se sami dopunjuju

Sa pravom **„Radionica“** agent radi kao na pravom računaru, za svaku AI i u svakoj firmi. Claude (CLI uz pretplatu) dobija svoje
Claude Code alate u folderu projekta, Codex svoje, a sve API AI i Ollama alat `befehl`. Ako program nedostaje, agent podnosi
**zahtjev za dopunu**: CEO ga provjerava, vi potvrđujete Telegram dugmetom ili pod ✋ Odobrenja, zatim server instalira tačno tu
komandu i zadatak se nastavlja. Ono što je instalirano navedeno je u `wissen/werkzeuge.md`.

- **Uključivanje:** `PCL_ALLOW_WERKSTATT=1` u `.env`, ponovo pokrenite, kod agenta označite polje i izaberite nivo.
- **Nivoi:** 1 = svaka komanda pita, 2 = rad u projektu je slobodan, instalacije i brisanje pitaju (po defaultu), 3 = sve slobodno
  (samo uz `PCL_WERKSTATT_FREI=1`). Pristupni podaci (`.env`, tokeni, ključevi) su uvijek blokirani.
- **Pažnja:** komande rade bez izolacije sa vašim korisničkim pravima. Nivo 2 prepoznaje instalacije po obliku, to nije sandbox.
- Sve ostalo, uključujući Remotion i probleme: [docs/werkstatt.md](docs/werkstatt.md) (na njemačkom).

## Paralelni rad

Istovremeno može raditi do `PCL_WORKERS` zadataka (podrazumijevano 2, najviše 6), npr. više saradnika jednog šefa ili zadaci
različitih projekata. Agent nikada ne radi na dva zadatka odjednom, a istovremeno radi najviše jedan Ollama zadatak
(RAM na Pi-ju). Kod pretplatnih CLI-ja (Claude, Codex) paralelni pozivi brže dostižu limit pretplate; tada postavite `PCL_WORKERS=1`.

## Granice ove verzije

- Nema automatskog heartbeat-a po rasporedu (zadaci se pokreću ručno ili delegiranjem).
- Nema AI za tekst u video, nema OCR za skenirane/slikovne PDF-ove; CEO sam ne zapošljava nove agente (organigram pravite vi).
- Pravi pregledač (`browse_page`) čita stranice, ali ne klikće i ne popunjava formulare (bez prijava, bez kupovina). Pretraga DuckDuckGo-a bez ključa može biti ograničena ili promijenjena.
- Nema budžeta: tokeni i procijenjeni troškovi se samo prikazuju (📊). Limiti krugova (dorade, provjere, dubina) sprječavaju beskonačne petlje.
- Sesije su proste potpisane kolačići; jedan uređaj ne može se posebno odjaviti
  (promjena lozinke poništava sve sesije).


## Samoprovjera

Poslije instalacije i unosa ključeva `python3 selftest.py` provjerava sve stvarne stvari koje se bez interneta nisu mogle testirati:
web pretragu, čitanje stranica, pretragu slika i generator slika, SSRF zaštitu, svakog AI provajdera mini zahtjevom (uključujući Ollama),
Telegram (token bota i probna poruka na vaš ID čata), ffmpeg, glasovni izlaz, PDF sa dijakriticima, OCR. Pojedinačne grupe:
`selftest.py web | llm | telegram | media | ocr | rust | film`. Svaki red prikazuje OK, MISSING (opciono) ili ERROR sa konkretnom napomenom.

## Ollama (lokalni modeli)

Dobavljač „Ollama (lokal)“: ključ nije potreban, lista modela dolazi direktno iz Ollama (`ollama pull qwen2.5:1.5b`). U dijalogu „Firma aus Vorlage“ (firma iz šablona)
postoje dugmad „Everything local (Ollama)“ (sve lokalno) i „Only employees local (Ollama)“ (samo saradnici lokalno); inače Ollama birate po agentu. Ako Ollama radi na drugom računaru
(npr. laptopu), postavite `OLLAMA_URL` na njegovu adresu. Mali modeli (3B) su na Pi-ju spori i često loše drže protokol alata;
za šefove jak model, lokalno prije svega za jednostavne saradnike ili čet.

**Dugi odgovori (Pi):** Hyperstead pita Ollamu sa streamingom. Dok model piše, ništa se ne prekida, čak i ako odgovor traje sat vremena.
`OLLAMA_TIMEOUT` (podrazumijevano 1800 s) je samo vrijeme čekanja **bez novih podataka**, npr. dok Ollama učitava model i čita zadatak;
`OLLAMA_MAX_TIME` (podrazumijevano 7200 s, 0 = bez granice) ograničava ukupno vrijeme. Prekinuti Ollama zahtjev se ne ponavlja.
Dok AI piše, kontrolna tabla dolje lijevo prikazuje „⏳ Agent · Ollama · 4:12 min · 380 Zeichen“. Čet čeka u pozadini,
prozor možete zatvoriti; odgovor je poslije u historiji.

**Malo RAM-a (≈ 2 GB slobodno):** `qwen2.5:3b` sa kontekstom treba oko 2,5 GB i ne staje. Dobro staje `qwen2.5:1.5b`
(preuzimanje ≈ 1 GB, u RAM-u ≈ 1,3–1,6 GB, razumije njemački, turski i engleski); još manji `gemma3:1b` (≈ 0,8 GB preuzimanje, ≈ 1,1 GB RAM).
Za samu Ollamu (`sudo systemctl edit ollama`): `Environment="OLLAMA_CONTEXT_LENGTH=4096"`, `"OLLAMA_NUM_PARALLEL=1"`, `"OLLAMA_MAX_LOADED_MODELS=1"`.
Na Pi 4 računajte s nekoliko riječi u sekundi i nekoliko minuta do prve riječi (dugi sistemski promptovi).

## Claude i ChatGPT preko vaše pretplate (CLI umjesto API ključa)

U `.env`: `PCL_ALLOW_CLI=1`. Programe sami instalirate i jednom prijavljujete na Pi-ju (uputstva proizvođača:
Claude Code `claude`, OpenAI Codex `codex`; prijava sa vašom pretplatom). Poslije toga se „Claude (CLI, your subscription)“ i „ChatGPT (Codex CLI, your subscription)“
pojavljuju u svim listama dobavljača. Server ih poziva bez shell-a, u praznom folderu i **bez naših API ključeva u okruženju**
(inače bi `claude` naplaćivao API ključ umjesto pretplate). Ograničenja: sporije od API-ja (pokretanje programa po odgovoru), vrijede limiti pretplate
(mnogo agenata = brzo do limita), a CLI programi imaju vlastite alate; po potrebi prilagodite komandu preko `PCL_CLI_CLAUDE` / `PCL_CLI_CODEX`.

## Model nestao? Prebacite agente

Hyperstead svakih 6 sati (`PCL_MODEL_CHECK_HOURS`) provjerava da li modeli agenata još postoje kod dobavljača i primjećuje i kada poziv javi „Modell nicht gefunden“ (model nije pronađen). Tada stiže Telegram poruka, zadatak pada uz jasnu napomenu, a u meniju **⚠ Models** sve pogođene agente prebacujete na drugi model jednim klikom.

## Veliki timovi

Šef može imati koliko god hoćete saradnika. U panelu šefa (Podešavanja) pod **Direct reports** (podređeni saradnici) označite sve potvrdnim poljima i sačuvajte dodjelu. Alternativno: prevucite donju tačku šefa na saradnika. Dugme **🗂 Arrange** (poredaj) pravi cijeli organigram (grupe od 6 i više saradnika u redovima po 5).

## CEO sam sastavlja svoj tim

CEO iz palete ima pravo **„May build its own team“** (smije sam sastaviti svoj tim, `recruit`). Ako još nema saradnike i dobije zadatak, analizira ga i pravi saradnike sa ulogom, radnim uputstvom i linijama izvještavanja (do 20, uključujući šefove odjeljenja sa vlastitim timom). Novi saradnici **još nemaju AI**: dodjeljujete ih u meniju **⚠ Models** (svi odjednom) ili po agentu u podešavanjima, pa odgovorite u **Pošti** na zadatak (npr. „Weiter“ = nastavi). Poslije toga CEO raspoređuje posao kao i obično. CEO novim saradnicima može dati samo web, slike, čitanje/pisanje fajlova, medije i programiranje, nikada shell.

**I kada tim već postoji**, CEO s ovim pravom smije pri svakom zadatku prilagoditi svoj tim vašim zadacima i uslovima:
- **Zapošljavanje**: dodatni saradnici, kao gore bez AI. Dobijate poruku na Telegramu i dodjeljujete im AI. Posao dobijaju tek od sljedećeg zadatka ili poslije vašeg „Weiter“.
- **Otpuštanje**: samo saradnici ispod njega, nikada on sam niti agenti izvan njegovog tima. Ljudi otpuštenog se pomjeraju nivo više. Ko još ima otvoren zadatak, ne biva otpušten.
- **Izmjena**: uloga, radno uputstvo i prava (samo gore navedena) saradnika ispod njega.

**Prava prema ulozi**: CEO treba svakome dati tačno ona prava koja mu posao traži. Ako neka zaboravi, sistem ih dodaje na osnovu imena, uloge i radnog uputstva, npr. istraživanje → *web*, slike/ilustracije/grafika/dizajn → *slike* + *pisanje fajlova*, video/zvuk/glas/PDF/prijelom → *mediji* + *pisanje fajlova*, autor/tekst/lektura → *pisanje fajlova*, programiranje/web stranica → *programiranje* + *pisanje fajlova*. Ako promijeni ulogu saradnika, prava se ponovo postavljaju prema njoj. Shell, izvršavanje koda, veze i objavljivanje nikada ne daje; to označavate samo vi.

Ako želite unaprijed vidjeti svaku izmjenu tima, označite u prozoru **Freigaben** *Teamänderungen freigeben* (odobri izmjene tima). Bez označene opcije kod CEO-a ne smije ništa od ovoga. Dnevni zadaci (raspored, kontrolni obilazak) nikada ne mijenjaju tim.

## Predaja: nastavak nakon prekida ili promjene modela
Svaki zadatak dobija datoteku `handover/assignment-<broj>.md` u folderu projekta. Nakon svakog koraka Hyperstead u nju upisuje ko je radio (agent, pružalac, model), koji su alati radili i s kojim rezultatom, rezultat i sljedeći korak (`next_step`). Na vrhu piše gdje se radi: folder projekta, Git repozitoriji u njemu s adresom i postojeće datoteke `STAND.md` ili `HANDOVER.md`.

- Ako se rad prekine greškom (kvota potrošena, pružalac nedostupan, pad), zadatak ostaje otvoren i nastavlja se automatski: nakon 5, 10, 20 … minuta, najviše 6 puta. Telegram to javlja jednom.
- Ako agentu postavite drugi model (agent → postavke, „⚠ Models“ ili promjena za grupu), rad se odmah nastavlja. Tada se ponovo preuzimaju i neuspješni glavni zadaci iz posljednjih 7 dana.
- Nakon ponovnog pokretanja Hypersteada prekinuti zadaci se odmah nastavljaju.
- Sljedeći model dobija stanje iz datoteke s uputom da nastavi odatle i ništa ne radi dvaput. CEO kontrolni obilazak prikazuje zadatke koji čekaju pod „STOPPED BY AN ERROR“.
- Savjet: ako je u folderu projekta repozitorij s vlastitom `STAND.md` (npr. `git clone https://github.com/KhungFu/swarm` u folderu firme), on se navodi na vrhu datoteke i agenti ga prvo čitaju.

## Radno vrijeme i dnevni zadaci

Bočna traka **🕘 Schedule** (raspored): za svaki projekat postavite početak rada, kraj rada i radne dane. Za svakog saradnika možete napraviti **dnevne zadatke** (fiksno vrijeme, na početku ili na kraju rada, na izabranim danima u sedmici), npr. „svaki dan u 15:00 provjeri web stranicu“. Rezultat stiže u prikaz „Post“ kao svaka objava (i preko Telegrama). Ako je posljednji zadatak nekog rasporeda još u toku, ne pokreće se dvaput; ako je Pi u to vrijeme bio isključen, nadoknađuje se do 6 sati.
Na početku rada firma ponovo preuzima zadatke koji su ostali nezavršeni (nepokrenuti se pokreću, neuspješni zadaci na vrhu ponavljaju se do `PCL_MAX_RESUMES`=2 puta). Opciono firma potpuno miruje van radnog vremena. Vrijeme je ono sa Pi-ja; ako nije tačno, u `.env` postavite `PCL_TZ=Europe/Vienna`.

## CEO kontrolni obilazak

U prozoru **🕘 Schedule** **👑 Set up CEO inspection** (CEO kontrolni obilazak) podešava dnevni kontrolni obilazak najvišeg šefa (podrazumijevano: na kraju rada; ostala vremena preko „New daily task“ + potvrdno polje *Kontrollgang*). Sistem mu prilaže **statusni izvještaj** sa činjenicama: po saradniku danas započeto/završeno/neuspješno/otvoreno, početi rada van radnog vremena, otvoreni zadaci bez početka rada, saradnici bez AI, nezavršeni zadaci i da li su dnevni zadaci izvršeni. CEO to procjenjuje, po potrebi raspoređuje naredne zadatke svom timu i u pošti piše kontrolni izvještaj. „📋 View status report“ (pogledaj statusni izvještaj) prikazuje činjenice bez CEO-a.

## Folder projekta

Svaki projekat ima **folder sa svojim imenom** pod `workspace/` (npr. `workspace/Buchverlag-Content-Agentur/`, njemački znakovi se transkribuju). Ostaje isti kada se projekat preimenuje i **nikada se ne briše kada se projekat obriše**. Ako napravite novi projekat istog imena, preuzima postojeći folder sa fajlovima. Stari folderi sa brojevima (`workspace/1`, `workspace/2` …) se pri pokretanju automatski preimenuju po imenu projekta.

## Objavljivanje web stranice

U prozoru **📁 Files of this project** fajlovi su poredani po folderima (`input/`, `output/`, `www/`, `wissen/` …). Svaki fajl ima polje za označavanje, svaki folder jedno za „sve u njemu“, a gore postoji „Select all“; **🗑 Delete selected** nakon pitanja briše sve označene fajlove (podfolderi koji ostanu prazni, npr. od raspakovanog ZIP-a, također nestaju). **🧹 Empty folder** pored svakog foldera nakon pitanja briše sve u njemu; sam folder ostaje. Skriveni folderi (`.rust/`, `.tmp-*`) se nikad ne diraju. Obrisani fajlovi su trajno nestali.

U prozoru **📁 Files of this project** postoji **🚀 Publish website** (objavi). Objavljuje se **samo folder `www/` u folderu projekta** (`www/index.html`, uz CSS, slike … sa relativnim putanjama); sve ostalo u projektu (bilješke, `output/`, `input/`, tačka-fajlovi, simboličke veze ka spoljašnjosti) ostaje nevidljivo. Ako nema foldera `www/`, isporučuje se, kao ranije, `index.html` iz foldera projekta (bez `input/` i skrivenih fajlova). Stranica trajno radi na vlastitom portu (od 8800, `PCL_SITE_PORT_BASE`), podrazumijevano samo na samom Pi-ju: `http://127.0.0.1:8800/`. Za pristup u mreži u `.env` postavite `PCL_SITE_HOST=0.0.0.0`. Agenti sa pravom „May propose the website for publishing“ (smije predložiti web stranicu za objavu) mogu zatražiti odobrenje za „veröffentlichen“; stranicu na mreži tek vaš klik pod **Freigaben** pušta online. Promjene agenata su odmah vidljive; poslije ponovnog pokretanja stranica se sama ponovo pokreće. Za otvoreni internet ispred mora stajati reverzni proksi sa HTTPS-om (npr. Caddy), a ne mali server.
