# Hyperstead

🌐 Jezici: [Deutsch](README.md) · [English](README.en.md) · [Türkçe](README.tr.md) · [Srpski](README.sr.md) · [Bosanski](README.bs.md) · **Hrvatski**

Tim agenata umjetne inteligencije kao uređivač čvorova, samostalno hostan, dovoljno lagan za Raspberry Pi.
Napravite projekt, povucite agente na površinu, povežite ih (nadređeni → suradnik), postavite AI pružatelja, radne upute i prava po čvoru te dodijelite zadatke.

> Detaljne upute u `docs/` trenutno su napisane samo na njemačkom. Nazivi gumba i izbornika u aplikaciji ostaju na njemačkom.

## Instalacija

Hyperstead je Python program (Flask + SQLite) i radi na više sustava. Više instalacija
može raditi paralelno; svaka ima svoje tvrtke i podatke.

| Sustav | Stanje | Upute |
| --- | --- | --- |
| Raspberry Pi / Linux (Debian, Ubuntu) | glavni sustav, puni opseg funkcija | dolje |
| Windows 10/11 | radi, bez `run_code`, izrada Rust programa samo bez izolacije preko prekidača, neke funkcije traže dodatne programe | [docs/windows.md](docs/windows.md) |
| macOS | nije testirano, osnovne funkcije bi trebale raditi | dolje (ručno) |
| Vlastito računalo za slike (npr. stari laptop bez grafičke kartice) | besplatne slike s referentnim slikama za Hyperstead | [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md) |

Selidba s jednog računala na drugo: zaustavite Hyperstead i kopirajte `data.db`, mapu `workspace/` i `.env`
([primjer Pi → Windows](docs/windows.md)).

### Raspberry Pi / Linux

```bash
git clone https://github.com/KhungFu/hyperstead && cd hyperstead
./install.sh --service     # venv, ovisnosti, .env s nasumičnom lozinkom, systemd servis
nano .env                  # unesite API ključeve, zatim: sudo systemctl restart hyperstead
```

Bez servisa: `./install.sh`, pa `./venv/bin/python app.py` → http://127.0.0.1:8787.
Lozinka za prijavu nalazi se u `.env` (`APP_TOKEN`). Ažuriranje, ponovno pokretanje, sigurnosna kopija: [Rad](#rad-tko-što-gdje-kada-i-kako).
Više funkcija (video, OCR, prevoditelji, preglednik): `./install.sh --all`.

### Windows

PowerShell u mapi Hyperstead:

```powershell
git clone https://github.com/KhungFu/hyperstead; cd hyperstead
powershell -ExecutionPolicy Bypass -File install.ps1
notepad .env
deploy\windows\hyperstead-start.bat
```

Što nedostaje na Windowsu, automatsko pokretanje i paralelni rad s Pi-jem: [docs/windows.md](docs/windows.md).
Kasnije ažuriranje: `git pull`, pa ponovno pokrenite.

### macOS (nije testirano)

```bash
git clone https://github.com/KhungFu/hyperstead && cd hyperstead
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
cp .env.example .env       # upišite APP_TOKEN=<duga lozinka>, dodajte API ključeve
./venv/bin/python app.py   # http://127.0.0.1:8787
```

`install.sh` je napravljen za Debian/Ubuntu (apt), pa na macOS-u radite ručno kao gore. Dodatni programi preko Homebrewa
(`brew install ffmpeg tesseract poppler`). `run_code` postoji samo na Linuxu.

### Slike na vlastitom računalu

Računalo u kućnoj mreži (i bez grafičke kartice, barem 8 GB RAM-a) može za Hyperstead besplatno raditi slike s
referentnim slikama. U `.env` ostavite aktivne točno ova dva retka (samo jedan redak `IMAGE_PROVIDER=` bez `#`):

```
IMAGE_PROVIDER=sdcpp
SDCPP_URL=http://<IP računala za slike>:1234    # na samom računalu za slike: http://127.0.0.1:1234
```

Postavljanje: [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md).

### Animirani filmovi uz Blender

Ako je Blender instaliran na računalu na kojem radi Hyperstead, agenti izrađuju crtane filmove: likove s vlastitim glasovima i
pokretima usta, scene, kameru, titlove, gotov film sa zvukom (alat `film`, predložak tvrtke „🐶 Animationsstudio“).
Ako Hyperstead sam ne pronađe Blender, upišite ga u `.env`:

```
BLENDER_PATH=C:\Program Files\Blender Foundation\Blender 4.2\blender.exe
```

Upute i format scenarija (na njemačkom): [docs/filmstudio.md](docs/filmstudio.md).

## Rad: tko što, gdje, kada i kako

**Tko:** sve ovo radi vlasnik računala (vi), a ne agenti. Naredbe se izvršavaju u
mapi Hyperstead: na Pi-ju u terminalu (`cd ~/hyperstead`), na Windowsu u PowerShellu
(`cd $HOME\hyperstead`, ili gdje god ste stavili mapu).

### Kratki pregled

| Što | Kada | Raspberry Pi / Linux (sa servisom) | Windows |
| --- | --- | --- | --- |
| Pokretanje | nakon instalacije, nakon ponovnog pokretanja bez automatskog starta | `sudo systemctl start hyperstead` | dvostruki klik na `deploy\windows\hyperstead-start.bat` (prozor ostavite otvoren) |
| Zaustavljanje | prije selidbe, sigurnosne kopije, ažuriranja | `sudo systemctl stop hyperstead` | zatvorite prozor za pokretanje (ili u njemu Ctrl+C) |
| Ponovno pokretanje | nakon svake promjene u `.env`, nakon ažuriranja | `sudo systemctl restart hyperstead` | zatvorite prozor za pokretanje, ponovno pokrenite `hyperstead-start.bat` |
| Radi li? | kada ima problema | `systemctl status hyperstead` | je li prozor za pokretanje otvoren? Preglednik: <http://127.0.0.1:8787> |
| Pregled dnevnika | kod pogrešaka | `journalctl -u hyperstead -f` (Ctrl+C prekida) | prikazuje se u prozoru za pokretanje |
| Ažuriranje | kada postoji nova verzija (npr. nakon spojenog pull requesta) | vidi dolje | vidi dolje |
| Provjera | nakon instalacije, ažuriranja, novih ključeva | `./venv/bin/python selftest.py` | `venv\Scripts\python.exe selftest.py` |
| Ključevi / postavke | novi ključ, drugi pružatelj slika | `nano .env`, pa ponovno pokrenite | `notepad .env`, pa ponovno pokrenite |
| Sigurnosna kopija | redovito, prije selidbe i većih ažuriranja | kopirajte `data.db`, `workspace/`, `.env` (prvo zaustavite) | isto u mapi Hyperstead |

### Ažuriranje (preuzimanje nove verzije)

**Raspberry Pi / Linux**, u terminalu:

```bash
cd ~/hyperstead
git pull
./install.sh               # potrebno samo ako se requirements.txt promijenio; .env ostaje nepromijenjen
sudo systemctl restart hyperstead
./venv/bin/python selftest.py llm     # kratka provjera odgovaraju li AI pružatelji
```

**Windows**, u PowerShellu:

1. `cd $HOME\hyperstead`
2. `git pull`
3. Samo ako su se paketi promijenili (ili kada niste sigurni): `powershell -ExecutionPolicy Bypass -File install.ps1`
   (postojeći `.env` ostaje nepromijenjen).
4. Zatvorite crni prozor za pokretanje Hypersteada.
5. Ponovno pokrenite `deploy\windows\hyperstead-start.bat` (dvostruki klik ili upišite u PowerShell).
6. Provjera: `venv\Scripts\python.exe selftest.py llm`

Ako `git pull` javi „local changes would be overwritten“, sami ste promijenili neku datoteku programa.
`git stash` odlaže promjenu na stranu, zatim ponovite `git pull`. Vaši podaci (`data.db`, `workspace/`, `.env`)
nikada nisu ugroženi, jer ih Git ne poznaje.

### Automatsko pokretanje

- **Pi:** `./install.sh --service` postavlja servis; on se tada sam pokreće pri svakom podizanju sustava.
- **Windows:** Win+R, upišite `shell:startup` i tamo stavite prečac do `deploy\windows\hyperstead-start.bat`
  (i do `bildrechner-start.bat`, ako ga koristite). Windows se za to mora sam prijaviti
  ([docs/windows.md](docs/windows.md), odjeljak 4).

### Mijenjanje postavki u `.env`

- Svaka postavka stoji točno jednom, bez `#` na početku. Reci s `#` su isključeni. Kod dupliciranih redaka
  vrijedi prvi.
- Nakon svake promjene ponovno pokrenite Hyperstead, inače vrijedi staro stanje.
- Ključeve nikada ne kopirajte u chatove, snimke zaslona ili repozitorij. Ako je ključ ipak negdje završio: opozovite ga kod pružatelja i unesite novi.
- Zatim provjerite sa `selftest.py`. Pojedina područja: `selftest.py llm`, `web`, `telegram`, `media`, `ocr`, `code`.

### Čitanje samoprovjere

- **OK:** radi.
- **FEHLT (nedostaje):** neobavezno; redak navodi naredbu za dodavanje (na Windowsu naredbu za Windows).
  Potrebno samo ako to vaši agenti koriste (npr. video, glasovni izlaz, skenirani PDF-ovi).
- **FEHLER (pogreška):** nešto što ste unijeli ne radi, najčešće nevažeći ili istekao ključ ili servis koji
  ne radi (npr. računalo za slike). Redak navodi razlog.
- Pojedinačni timeout kod web servisa često je samo privremen: pokušajte kasnije.

### Računalo za slike (ako se koristi)

- **Gdje:** na računalu koje pravi slike (npr. laptop), u mapi `C:\bildrechner`.
- **Kada:** mora raditi dok agenti trebaju praviti slike.
- **Kako se postavlja (jednom):** u PowerShellu u mapi Hyperstead
  `powershell -ExecutionPolicy Bypass -File deploy\windows\bildrechner-einrichten.ps1` (preuzima program i modele).
- **Kako se pokreće:** pokrenite `C:\bildrechner\bildrechner-start.bat`, prozor ostavite otvoren. U `.env` datoteci Hypersteada
  `IMAGE_PROVIDER=sdcpp` i `SDCPP_URL=...` ([upute](docs/laptop-bildrechner.md)), zatim ponovno pokrenite Hyperstead.

### Filmski studio (ako se koristi)

- **Gdje:** na računalu s Blenderom (npr. laptop). Tvrtka s alatom `film` mora raditi u **ovoj** instanci Hyperstead.
- **Kada:** Blender ne mora biti otvoren, Hyperstead ga za svaku scenu pokreće u pozadini i ponovno zatvara.
- **Provjera:** `venv\Scripts\python.exe selftest.py film` (Windows) ili `./venv/bin/python selftest.py film`.
- **Koliko traje:** pri 640×360 i 12 sličica u sekundi, ovisno o laptopu, oko 1 do 5 minuta po 10 sekundi filma. Blender nikad ne radi istovremeno s računalom za slike.

### Selidba (npr. Pi → laptop)

Korak po korak u [docs/windows.md](docs/windows.md), „Phase 2 – Umzug“ (na njemačkom). Ukratko: zaustavite oba, kopirajte `data.db`,
`workspace/` i `.env`, pokrenite na novom računalu i provjerite, pa tek onda isključite stari.
Telegram unosite samo na jednom računalu.

### Što se događa kada nešto nedostaje

Ovaj popis se dopunjuje pri svakoj promjeni programa. Svaki redak kaže što sustav radi i što vi trebate učiniti.

| Nedostaje | Što sustav radi | Što vi radite |
| --- | --- | --- |
| `.env` | Hyperstead se pokreće bez ključeva i bez lozinke, dostupan samo s ovog računala. S `HOST=0.0.0.0` pokretanje se prekida dok je `APP_TOKEN` prazan. | `./install.sh` (Pi) odnosno `install.ps1` (Windows) ga stvara s nasumičnom lozinkom. |
| `data.db` | Stvara se nova i prazna. Tvrtke, zadaci i pošta su nestali. | Prvo napravite sigurnosnu kopiju (vidi Rad). Vraćajte samo iz kopije. |
| API ključ u `.env` | Pružatelj se u samoprovjeri prijavljuje kao FEHLT i agenti ga ne koriste. Ako je unesen, ali nevažeći: FEHLER s HTTP 401. | Unesite ključ ili isključite redak s `#`. |
| `SDCPP_URL` (uz `IMAGE_PROVIDER=sdcpp`) | Zahtjevi za slike ne uspijevaju uz poruku „SDCPP_URL fehlt“ (nedostaje). Uz `IMAGE_FALLBACK=pollinations` izrađuje se besplatna nadomjesna slika bez referenci, uz napomenu u rezultatu. | Dodajte redak u `.env`, ponovno pokrenite Hyperstead. |
| Računalo za slike nije dostupno (laptop isključen, vatrozid, kriva IP) | Kao gore: pogreška „Bildrechner … nicht erreichbar“ (nije dostupno), uz nadomjesnu sliku. | Uključite laptop, pokrenite `bildrechner-start.bat`, provjerite IP i vatrozid. |
| `sd-server.exe` (Windows, računalo za slike) | `bildrechner-start.bat` prikazuje „sd-server.exe fehlt“ (nedostaje) i ništa ne pokreće. | Pokrenite `deploy\windows\bildrechner-einrichten.ps1`. |
| Datoteka modela (Windows, računalo za slike) | Startna datoteka navodi nedostajuću datoteku i ne pokreće se. Ako nedostaje samo veliki jezični model (`Qwen3-4B-Q4_K_M.gguf`), koristi se manji, ako postoji. | Ponovno pokrenite skriptu za postavljanje; preuzima samo nedostajuću datoteku. |
| Windows runtime `VCOMP140.DLL` | `sd-server.exe` javlja „VCOMP140.DLL nicht gefunden“ (nije pronađen) i prekida rad. | Ponovno pokrenite skriptu za postavljanje (korak 3 instalira runtime), pa otvorite startnu datoteku. |
| Pravilo vatrozida za port 1234 (Windows) | Samo Pi ne može doći do računala za slike. Sam laptop radi dalje. | Pokrenite naredbu iz [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md), odjeljak 4, kao administrator. |
| Makro u `macros/` ili prijava `macros/<stranica>.json` (uz `PCL_MACROS=1`) | Bez makroa alat `site_macro` ne postoji. Bez sačuvane prijave makro staje uz napomenu. Ako MagicLight ili Flow promijene stranicu, `site_macro` javlja FEHLER i stavlja `<sajt>-fehler.png` u `output/`. Samoprovjera (`browser`) prikazuje FEHLT. | Makro (ponovo) snimiti prema [macros/README.md](macros/README.md). |
| `ffmpeg`, `tesseract`, `pdftoppm`, glasovni izlaz | Funkcija nedostaje. Agenti koji je traže javljaju pogrešku u rezultatu. Samoprovjera prikazuje FEHLER (Pi) odnosno FEHLT (Windows). | Instalirajte program (naredbe u samoprovjeri i u [docs/windows.md](docs/windows.md)). |
| Blender (alat `film`) | `save`, `check`, `voices` i `assemble` i dalje rade. `preview` i `render` javljaju „Blender wurde nicht gefunden“ (Blender nije pronađen) uz napomenu o `BLENDER_PATH`. Samoprovjera prikazuje FEHLT. | Instalirajte Blender (`winget install BlenderFoundation.Blender`) ili postavite `BLENDER_PATH` u `.env`, ponovno pokrenite. |
| `film/film.json` (scenarij) | `film` javlja „film/film.json fehlt“ (nedostaje) i traži da se prvo s `op=save` spremi scenarij. Neispravan scenarij se ne sprema, odgovor navodi sve pogreške. | Ništa, agenti ga sami izrađuju. Možete ga napisati i ručno ([docs/filmstudio.md](docs/filmstudio.md)). |
| Slika, glazba ili `.blend` datoteka navedena u scenariju | Provjera navodi scenu, lik i putanju, ništa se ne renderira. | Stavite datoteku u `assets/` ili `input/` ili ispravite putanju u scenariju. |
| Klip scene (`film/clips/`) | `assemble` navodi scene koje nedostaju i ništa ne montira. Ako se `render` prekine (vremensko ograničenje), gotove sličice ostaju spremljene i sljedeći poziv nastavlja odatle. | Ništa, agenti ponovno pozivaju `render`. |
| Govor za film | `voices`/`render` se prekidaju porukom „Keine Sprachausgabe verfügbar“ (nema govora). Scene bez dijaloga i dalje rade. | Kao kod „govora“ iznad (na Windowsu `edge-tts` + `TTS_ENGINE=edge`). |
| `cargo` (Rust, alat `rust_project`) | Alat se agentima ne prikazuje; `check_code` i dalje provjerava `.rs` datoteke ako postoji `rustc`. Samoprovjera (`selftest.py rust`) prikazuje FEHLT s naredbom za instalaciju. | Instalirajte Rust: Pi `curl https://sh.rustup.rs -sSf \| sh`, Windows `winget install Rustlang.Rustup`. Zatim ponovno pokrenite Hyperstead. |
| bubblewrap pri izradi Rust programa (Pi/Linux) | `rust_project` ostaje skriven, isto kao `run_code`. | `./install.sh --run` |
| `PCL_CARGO_UNSAFE=1` (Windows) | Windows nema izolaciju, zato `rust_project` bez prekidača ostaje skriven. S prekidačem laptop gradi bez izolacije. | Postavite ga samo ako znate rizik ([Rust programi](#-potpuna-izrada-rust-programa)), zatim ponovno pokrenite. |
| `Cargo.toml` u Rust mapi | `rust_project` javlja „In … fehlt Cargo.toml“ i navodi datoteke koje agent prvo mora napraviti. | Ništa, agent ih pravi pomoću `write_code`. |
| Internet za Rust ovisnosti (crates.io) | `cargo fetch` ne uspijeva, ništa se ne gradi, agent dobiva poruku o grešci. Već preuzete ovisnosti ostaju u `.rust/cargo-home` i rade dalje. | Provjerite internet i ponovno pokrenite zadatak. |
| Položeni testovi za Rust paket | Paket se **ne** pravi („KEIN PAKET“); agent dobiva greške s brojem reda i mora ih ispraviti. Bez testova paket nastaje s upozorenjem WARNUNG u rezultatu. | Ništa, agent ispravlja i ponovno gradi. Ako odustane, vratite zadatak preko šefa. |
| Mapa `.rust/` u projektu (mapa za izradu) | Pri sljedećoj izradi pravi se ponovno, što tada traje duže (sve se ponovno preuzima i kompajlira). Skrivena je i nije dio ZIP preuzimanja. | Ništa. Smijete je obrisati ako ponestane mjesta. |
| Telegram token ili ID chata | Telegram ostaje isključen, sve ostalo radi. Samoprovjera prikazuje FEHLT. | Potrebno samo ako želite poruke na telefonu. |
| Mapa ili datoteka u projektu (`wissen/`, `input/`) | Mape koje ne postoje smatraju se praznima. Agenti rade dalje bez znanja o tvrtki. | Stvorite ili otpremite datoteku ili mapu u projektu. |
| Ključ video pružatelja (npr. `KLING_SECRET_KEY`, `HIGGSFIELD_API_KEY_SECRET`) | `video_generate` javlja „VIDEO_PROVIDER=…, aber … fehlt“ i ništa ne stvara; ostali pružatelji s popisa rade dalje. Samoprovjera prikazuje pružatelja kao FEHLT. | Unesite ključ ([docs/videodienste.md](docs/videodienste.md)) ili uklonite pružatelja iz `VIDEO_PROVIDER`, ponovno pokrenite. |
| Kredit kod video pružatelja | Pružatelj odgovara pogreškom (često HTTP 402/429 ili „insufficient balance“), agent dobiva tekst u rezultatu. Nijedan drugi pružatelj ne uskače. | Nadoplatite kredit ili odaberite drugog pružatelja preko `provider` ili u `VIDEO_PROVIDER`. |
| `FAL_KEY` (uz `VIDEO_PROVIDER=fal`, `VIDEO_AI=fal` ili `AUDIO_PROVIDER=fal`) | `video_generate`, `video_ai` odnosno `sound_generate` javlja „FAL_KEY fehlt“ i ništa ne stvara. | Unesite ključ s fal.ai ili uklonite redak `VIDEO_AI`/`AUDIO_PROVIDER`. |
| `ELEVENLABS_API_KEY` (bolji glasovi po potrebi) | Sve radi kao prije s lokalnim glasovima. Ako se ipak koristi `engine: elevenlabs` ili `TTS_ENGINE=elevenlabs`, ili ElevenLabs/OpenAI ne uspije (ključ, kredit, internet), govori lokalni glas, a rezultat počinje s „HINWEIS: … nicht genutzt” i razlogom. U filmu se redak pri sljedećem `voices` ponovno pokuša s cloud glasom. S `TTS_FALLBACK=0` zadatak se umjesto toga prekida. | Ključ s elevenlabs.io upisati u `.env` i ponovno pokrenuti. Upute: 📖 → „🎙 Stimmen und ElevenLabs”. |
| AI suradnika kojeg je CEO tek zaposlio | Novi suradnik se stvara, ali ne dobiva zadatke. Ako CEO nakon toga ponovno planira, zadatak se prekida s „Diesen Mitarbeitern ist noch keine KI zugewiesen: …“ (još nije dodijeljen AI). U izborniku **⚠ Modelle** stoji kao „Noch keine KI“. | Dodijelite AI u izborniku ⚠ Modelle i odgovorite „Weiter“ u pošti. |
| Prava suradnika kojeg je zaposlio CEO | Sustav dodaje prava koja nedostaju na temelju uloge (popis gore). Ako se nijedna ključna riječ ne poklapa, dobiva samo *čitanje datoteka* i može odgovoriti samo tekstom. | Označite prava u panelu agenta ili CEO-u preciznije zadajte ulogu. |
| Suradnik kojeg CEO želi otpustiti ili izmijeniti | Ako tog imena nema u njegovu timu (tipfeler, drugi tim, već otpušten), uputa se preskače i bilježi u rezultatu. Ako suradnik još ima otvoren zadatak, ostaje. | Ništa, ili kasnije ponovno zadajte. |
| `video_providers.py` (programska datoteka) | Alati za video, zvuk i glasove iz oblaka nestaju za agente, sve ostalo radi dalje. | Ponovno pokrenite `git pull`, datoteka je dio programa. |
| `GITHUB_UPLOAD_TOKEN` ili `GITHUB_UPLOAD_REPO` | GitHub se pod ☁️ Cloud prikazuje kao „nije postavljeno”, agentima se ne nudi kao cilj. Sve ostalo radi. | Unesite token i repozitorij ([docs/cloud.md](docs/cloud.md), na njemačkom), ponovno pokrenite. |
| `GDRIVE_CLIENT_ID`/`GDRIVE_CLIENT_SECRET` ili `ONEDRIVE_CLIENT_ID` | Usluga ostaje „nije postavljeno”, gumb „Prijava” ne postoji. | Registrirajte aplikaciju i unesite retke ([docs/cloud.md](docs/cloud.md)), ponovno pokrenite. |
| Prijava kod Googlea/Microsofta (mapa `tokens/`) | Usluga stoji na „nije prijavljeno”. Prijenos javlja „još niste prijavljeni” odnosno „prijava je istekla” i ništa ne prenosi. | ☁️ Cloud → Prijava. Pri selidbi s Pi-ja na laptop jednostavno se ponovno prijavite na laptopu. |
| Datoteka veća od 50 MB za Telegram | Telegram je ne prima. `/datei` je označava s ⚠️ i ne šalje je, agent dobiva napomenu. | Kao cilj odaberite Google Drive, OneDrive ili GitHub. |
| `cloud_upload.py` (programska datoteka) | Hyperstead se ne pokreće (pogreška pri uvozu). | Ponovno pokrenite `git pull`, datoteka je dio programa. |
| `PCL_ALLOW_WERKSTATT=1` | Polje „Radionica” je sivo, nijedan agent ne dobiva `befehl` ni `nachruesten`. Sve ostalo radi kao i prije. | Dodajte redak u `.env`, ponovno pokrenite, označite polje kod agenta ([docs/werkstatt.md](docs/werkstatt.md)). |
| Program koji je agentu potreban (npr. Node.js, Remotion, Python paket) | Agent s radionicom podnosi zahtjev za nadogradnju: CEO ga provjerava, vi dobivate ✅/❌ preko Telegrama i pod ✋ Odobrenja. Nakon vašeg „da” poslužitelj instalira i zadatak se nastavlja. Bez radionice agent samo navodi što nedostaje. | Pročitajte zahtjev i odlučite. Bez Telegrama samo preko weba. |
| AI CEO-a (kod zahtjeva za nadogradnju) | Zahtjev stiže izravno vama uz napomenu „Nema CEO-a s AI” ili „CEO nije dostupan”. | Odlučite sami ili dodijelite CEO-u AI. |
| `werkstatt.py` (programska datoteka) | Hyperstead se ne pokreće (pogreška pri uvozu). | Ponovno pokrenite `git pull`, datoteka je dio programa. |
| `growth.py` (programska datoteka) | Hyperstead se ne pokreće (pogreška pri uvozu). | Ponovno pokrenite `git pull`, datoteka je dio programa. |
| Svijet projekta nikad nije odabran | Projekt prikazuje svijet svemira s njegovim razinama i pojmovima. | Ništa ne treba raditi. ⚛️ Atom u izboru grafike prebacuje na svijet Atom, 🌌 Weltall natrag. |
| Datoteke logotipa u `static/logo/` | Bočna traka i stranica za prijavu prikazuju prazno polje za sliku, kartica preglednika nema ikonu. Sve ostalo radi normalno. | Ponovno pokrenuti `git pull`. Logotip se može ponovno izraditi s `docs/logo/logo_blender.py` ([upute](docs/logo-prompt.md), na njemačkom). |
| Raniji svijet (Ceh, Tycoon, Gizmo grad) spremljen u projektu | Projekt automatski prikazuje svemir. Bodovi, razina i rangovi ostaju isti, mijenjaju se samo nazivi i ikone. | Ništa ne treba raditi. |
| Danas nema poziva umjetne inteligencije (operativni centar, 💶 u traci) | Prikazuje 0 $ odnosno „keine Aufrufe“. | Ništa nije potrebno. Troškovi su procjene, vlastite cijene putem `PCL_PRICES` u `.env`. |
| Preglednik ništa ne sprema (privatni prozor) | Svijetlo/tamno, odabrana grafika (svemir, vrsta organigrama, atom, nacrt), pomaknute kartice organigrama, pokreti i način pomoći pri svakom se učitavanju vraćaju na zadano. | Koristite običan prozor; podaci projekata nisu pogođeni. |
| Agenti u nacrtu leže jedan preko drugoga (npr. svi na istom mjestu) | Linije veza se ne vide. Pri otvaranju nacrta Hyperstead ih jednom automatski razmješta i to javlja. | Ništa, ili pritisnite „🗂 Ordnen“. |

## Pristup s interneta

Aplikacija namjerno sluša samo na `127.0.0.1`. Umjesto otvaranja porta koristite tunel.
Ovo je potrebno i ako vaš mobilni usmjerivač ne dopušta dolazne veze (CGNAT).

### Opcija A (preporučeno): Tailscale, privatno, samo za vaše uređaje

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up                    # otvorite poveznicu za prijavu u pregledniku
sudo tailscale serve --bg 8787       # HTTPS adresa samo u vašem tailnetu
```

Instalirajte Tailscale i na telefon/laptop, pa otvorite prikazanu adresu `https://dexter….ts.net`.
U `.env` dodajte: `TRUST_PROXY=1`, zatim ponovno pokrenite servis.
**Ne** koristite `tailscale funnel`, to bi aplikaciju stavilo na javni internet.

### Opcija B: Cloudflare Tunnel, javna adresa s vlastitom domenom

```bash
# instalirajte cloudflared (vidi developers.cloudflare.com/cloudflare-one/connections/connect-networks)
cloudflared tunnel login
cloudflared tunnel create hyperstead
cloudflared tunnel route dns hyperstead agents.vas-domen.de
# ~/.cloudflared/config.yml:  ingress: - hostname: agents.vas-domen.de  service: http://127.0.0.1:8787
cloudflared tunnel run hyperstead
```

Dodatno se snažno preporučuje: stavite ispred **Cloudflare Access** (prijava e-poštom).
U `.env`: `TRUST_PROXY=1`. Naredbe se mogu mijenjati; u sumnji vrijedi službena uputa.

S `TRUST_PROXY=1` aplikacija se pokreće samo ako `APP_TOKEN` ima najmanje 12 znakova.

## Rukovanje

| Radnja | Kako se radi |
|---|---|
| Napravite agenta | povucite stavku iz palete na površinu (ili kliknite na nju) |
| Povežite | povucite donju točku čvora na drugi čvor (= nadređeni → suradnik) |
| Prekinite vezu | kliknite na liniju veze |
| Pomicanje | povucite čvor; povlačenje pozadine = pomicanje prikaza; kotačić miša = zumiranje |
| Postavke | kliknite čvor → panel desno |
| Dodijelite zadatak | panel → kartica „Aufgaben“ (zadaci) |
| Odobravanje | bočna traka „Freigaben“ (odobrenja) |

## Kako tvrtka radi

Nadređeni dobiva zadatak i **planira** (raspoređuje podzadatke) ili ga sam obavlja. Čim su svi
suradnici gotovi, on se ponovno budi, **čita njihova izvješća**, vraća nedostatke uz povratnu informaciju ili
sažima sve i izvještava svog nadređenog. Tako se rezultat penje kroz koliko god razina.
Status „Wartet auf Team“ (čeka tim) znači: nadređeni čeka svoje ljude. U kartici zadataka vidite cijelo stablo.

## Svemir i rast

Svaki je projekt mali **svemir** koji raste sa svojim uspjesima. Svemir mijenja samo riječi, ikone i boje
sučelja. Agenti uvijek rade s jasnim pojmovima (zadatak, izvješće, tim), tako da njihova kvaliteta ostaje ista.

| U svemiru | Značenje u timu |
| --- | --- |
| ☀️ Sunce | najviše vodstvo (npr. CEO) |
| 🪐 Planet | odjel ili poslovođa, kruži oko Sunca |
| 🌙 Mjesec | zaposlenik, kruži oko svojeg planeta (tko je još niže, mali je mjesec mjeseca) |
| Razine | ☄️ Asteroid → 🪐 Planet → ☀️ Sunčev sustav → ✨ Zvjezdani skup → 🌌 Galaktika |
| Rangovi agenata | ☄️ Komet → 🌙 Mjesec → 🪐 Planet → ⭐ Zvijezda |

Bodovi se zovu zvjezdana prašina, zadaci se zovu misije. Raniji svjetovi Ceh, Tycoon i Gizmo grad više ne postoje; postojeći projekti automatski prikazuju svemir, bodovi i razine ostaju sačuvani. Sučelje prikazuje nazive na njemačkom.

**Svijet Atom:** Osim svemira postoji i drugi svijet. Ako u izboru grafike odabereš ⚛️ Atom, za projekt vrijedi svijet Atom, a s 🌌 Weltall ponovno svemir (i u traci rasta, pri proslavi i u Telegramu). Jezgra = najviše vodstvo, elektronska ljuska = odjel, elektron = zaposlenik. Razine: ✴️ Kvark → ⚛️ Atom → 🧪 Molekula → 💎 Kristal → 🧬 Stanica; rangovi: · Neutrino → ⚡ Elektron → 🔴 Proton → 💠 Nukleon (sučelje prikazuje njemačke nazive). Bodovi se zovu energija, zadaci pokusi. Bodovi i granice razina isti su u oba svijeta. Organigram i nacrt zadržavaju posljednji odabrani svijet.

**Upotreba:** Traka iznad površine prikazuje razinu, napredak do sljedeće razine i najvažnije brojeve. Desno prebacujete između svijetlog i tamnog prikaza (🌓) i s ⓘ otvarate pregled razina, bodova i rangova. Rang svakog agenta prikazan je kao ikona na njegovoj kartici.

**Sunčev sustav:** Padajući gumb desno u traci (npr. „🌌 Weltall ▾“) bira grafiku: 🌌 svemir, tri organigrama, ⚛️ atom ili 📐 nacrt (uređivač čvorova). Svemir je nacrtan detaljno: sunce sa zrakama i pjegama, planeti s noćnom stranom, oblacima ili pojasevima, mjeseci s kraterima, pojas asteroida, daleke galaktike i Mliječni put. Planeti i mjeseci polako kruže, a planeti i sunce pritom se okreću i oko vlastite osi (oblaci, pojasevi i sunčeve pjege klize preko površine, sunčev vijenac zraka kruži), a u fazi galaktike okreće se i spirala u pozadini; kad mišem pokažete na jedan od njih, sve se zaustavi da biste ga lako pogodili. Plavi prsten koji pulsira znači "radi", žuti prsten "čeka vaše odobrenje", crveni prsten "pogreška", ljubičasti isprekidani prsten "čeka svoj tim". Dodir na Sunce ili planet prikazuje tim i radnje, dodir na mjesec otvara agenta. Sa svakom razinom nebo je punije, od zvjezdanog skupa svijetle maglice, a kao galaktika pojavljuje se spirala. Svemir ostaje taman i u svijetlom prikazu. Na telefonu se umjesto karte prikazuje popis: Sunce, ispod njega svaki planet sa svojim mjesecima. Pokreti se isključuju kad uređaj traži „smanji pokrete“.

**Organigram:** prikazuje tim u tri vrste, svaka je zasebna stavka u izboru grafike: ⬇ Baum (stablo odozgo prema dolje, zaposlenici bez vlastitog tima stoje jedan ispod drugoga), ➡ Gliederung (jedan redak po agentu, uvučeno po razini, najbolje za telefon) i ◎ Kreis (krug, vodstvo u sredini, svaka razina jedan prsten). Boja pokazuje stanje: zeleno spremno, plavo radi, žuto čeka vaše odobrenje, crveno pogreška, ljubičasto čeka tim, sivo pauzirano. Dodir otvara agenta. Kartice se mogu povlačiti, linije ih prate; uređaj to pamti po projektu i vrsti, „↺ Anordnung zurücksetzen“ vraća raspored. Ako karticu spustite na drugu (ili u nacrtu agenta na drugog agenta), Hyperstead najprije pita i tek ga onda stavlja u taj tim.

**Atom:** ⚛️ prikazuje tim kao atom iz filmova: u jezgri od crvenih i sivih kuglica sjedi najviše vodstvo, svaki odjel ima vlastitu elektronsku putanju, a zaposlenici stoje na njoj kao manji elektroni. Grafika miruje kako bi se mogla čitati na miru. Kao svijet, slika raste s razinom: kao kvark u jezgri svijetle tri kvarka, od molekule su susjedni atomi povezani vezama, od kristala u pozadini leži atomska rešetka, kao stanica dodaju se stanična stijenka i dvostruka spirala DNK. Stanje i dodir rade kao u organigramu.

**Operativni centar:** 🛰 u bočnoj traci (ili dodir na brojeve u traci rasta) na prvi pogled prikazuje što trenutačno radi i čeka, koja su odobrenja otvorena, što nije uspjelo u posljednjih 7 dana (s ↻ Neu), rasporede (s ▶ Jetzt), poruke o pogreškama i posljednje događaje. Uz to prikazuje procijenjene troškove umjetne inteligencije za danas i posljednjih 7 dana; današnji trošak stoji i kao 💶 u traci. Svi brojevi dolaze iz postojećih zadataka, odobrenja, rasporeda i povijesti, ništa nije izmišljeno.

**Napredovanje i upravljanje:** Kad projekt dosegne novi stupanj, pojavi se kratka proslava s novim stupnjem i sljedećim ciljem (Telegram šalje istu poruku). Kad agent napreduje u rangu, pojavi se kratka obavijest. Pod ⓘ u traci možete za ovaj uređaj isključiti pokrete i efekte proslave; ako uređaj traži „smanji pokrete“, sve ionako ostaje mirno. Svi se prozori zatvaraju tipkom Esc, Sunce, planeti i mjeseci u svemiru mogu se koristiti tipkama Tab i Enter.

**Upute i pomoć:** 📖 Anleitung na vrhu bočne trake otvara upute za uporabu izravno na nadzornoj ploči (poglavlja na rasklapanje, s pretraživanjem, bez preuzimanja, radi i izvanmrežno). ⓘ na vrhu prozora vodi do odgovarajućeg poglavlja. Svaki gumb prikazuje kratko objašnjenje kad mišem pokažete na njega. Na mobitelu u uputama uključite način pomoći: prvi dodir gumba ga objašnjava, drugi ga izvršava.

**Bodovi:** isporuka prihvaćena iz prve +10, nakon ispravka +5, zadatak označen kao završen u pošti +20,
neuspješno −3, zatražena dorada −5. Razine od 0 / 100 / 300 / 700 / 1500 bodova. Postojeći projekti automatski
dobivaju svoje dosadašnje uspjehe. Prelazak na višu razinu javlja se jednom putem Telegrama.

**Što razina ograničava:** samo koliko agenata uprava smije **sama** zaposliti (8 / 12 / 18 / 25 / neograničeno
u projektu) i koliko duboko (2 / 3 / 4 / 5 / puna dubina). Vi uvijek možete sve napraviti sami. Ograničenje se može
isključiti po projektu.

**Rangovi agenata** prema vlastitim prihvaćenim isporukama: od 0 / 5 / 20 / 60 (npr. šegrt, kalfa, majstor, veliki majstor).

## Mogućnosti agenata (internet, slike, datoteke)

Agenti rade u krugovima: traže alate, poslužitelj ih izvršava i vraća rezultate, sve dok nisu
gotovi (najviše `PCL_MAX_TOOL_STEPS`). Prava po agentu: **pretraga interneta**, **slike**, **čitanje datoteka projekta**
(i, kao ranije, pisanje datoteka).

| Alat | Što radi | Bez ključa |
|---|---|---|
| `web_search` | pretraga weba (zakoni, cijene, konkurencija …) | DuckDuckGo; bolje: `SEARXNG_URL`, `BRAVE_API_KEY` ili `TAVILY_API_KEY` |
| `fetch_url` | čita web stranicu kao tekst | da |
| `browse_page` | otvara stranicu u pravom pregledniku (JavaScript radi), neobavezno sa snimkom zaslona koju agent vidi kao sliku | da, treba `./install.sh --browser` |
| `image_search` / `image_save` | traži slobodno licencirane fotografije i sprema ih u `assets/`, s autorom i licencom | Openverse; neobavezno `PEXELS_API_KEY` |
| `image_generate` | izrađuje AI sliku kao PNG, neobavezno s do 4 referentne slike iz projekta (isti likovi i stil kroz seriju), format kvadrat/okomito/vodoravno i ciljna putanja u `assets/`, `output/` ili `karten/`. Pravo **Slike** ili **Mediji** | Pollinations (bez ključa: bez referentnih slika; s `POLLINATIONS_API_KEY` i Pollen kreditom: model preko `POLLINATIONS_MODEL`, s referentnim slikama); `IMAGE_STYLE` postavlja fiksni stil crtanja; ostali: `nvidia` (FLUX preko build.nvidia.com), `cloudflare` (Workers AI, FLUX.2 klein s referentnim slikama), `hf` (Hugging Face), model svakoga preko `IMAGE_MODEL`; besplatno s referentnim slikama na vlastitom računalu: `IMAGE_PROVIDER=sdcpp` ([upute](docs/laptop-bildrechner.md)); bolje `IMAGE_PROVIDER=openai` s `OPENAI_API_KEY`, `gemini`, ili `openrouter` s `OPENROUTER_API_KEY` |
| `list_files` / `read_file` | čita datoteke u mapi projekta (npr. tekstove kolega) | da |

Sve što se napravi nalazi se pod `workspace/<id-projekta>/`. U bočnoj traci **📁 Dateien** prikazuju se datoteke, otvara se `index.html`
kao web stranica (izolirani sandbox) i preuzima sve kao ZIP. Poveznica sadrži tajni ključ.

**Projekti i prikazi:** U bočnoj traci pod „Projekte“ na vrhu su tri prikaza 📐 Klassisch · 🏙 Stadt · 🌌 Kosmos, zatim „＋ Neues Projekt“ (jedan prozor: prazan projekt ili gotova tvrtka iz predloška) i popis projekata. Izbornik grafika gore desno podijeljen je isto: „Alle Projekte · modern“ (grad, kozmos) i „Dieses Projekt · klassisch“. U gradu je svaka tvrtka zgrada vlastitog stila; kad je otvoriš, uprava je na najvišem katu, ispod je po jedan kat za svaki odjel, a desno organigram. U kozmosu je svaka tvrtka Sunčev sustav (Sunce = uprava, planeti = odjeli); Sunce raste s razinom i timom, planeti kruže i na mobitelu i zaustave se ispod prsta, a imena ostaju čitljiva kad se prikaz udalji.

**Predlošci tvrtki** („＋ Neues Projekt“ ispod „Projekte“): *Web agencija*, *Računovodstvo/porezni ured*, *Uvoz/izvoz trgovina* stvaraju projekt,
organigram, radne upute i prava u potpunosti. Vlastite tvrtke: napišite cilj projekta („vi ste …“, zemlja,
djelatnost), postavite agente i prava. Agenti dobivaju datum i cilj projekta i trebaju prvo istražiti stvari koje se mijenjaju (zakoni,
cijene) i navesti izvore.

**Sigurnost alata:** preuzimanje stranica ograničeno je na javne adrese (bez localhosta, LAN-a, Tailscalea,
metapodataka iz clouda; preusmjeravanja se provjeravaju pojedinačno). Za agente sadržaj weba vrijedi kao nepouzdan podatak,
ali pripremljena stranica ipak može utjecati na model: ne dajte agentima s pristupom internetu shell i provjeravajte rezultate.
Agenti namjerno **nemaju** alate za kupnje, narudžbe, plaćanja ili slanje e-pošte; daju nacrte i preporuke.
Licence za slike (CC) često traže navođenje autora; urednik slika to upisuje u `bildnachweis.md`.

## Mediji, dokumenti i vlastite datoteke

Uz pravo **izrade medija i dokumenata** (i `ffmpeg`/fontovi na Pi-ju, vidi `install.sh`):

| Alat | Što može |
|---|---|
| `video_edit` | reže video (`trim`), spaja (`concat`), **animaciju slideshowa sa zumom** iz slika (`slideshow`, neobavezno sa zvukom), dodaje tekst/titlove/logo, mijenja ili miješa zvuk, mijenja brzinu, pretvara u GIF/WebM/MP3, izvlači nepomičan kadar |
| `speak` | pretvara tekst u glas govornika (espeak-ng offline; bolje: Piper; neobavezno Edge glasovi ili glasovi iz oblaka ElevenLabs/OpenAI preko `TTS_ENGINE`), uz `voice`, `pitch`, `rate` za različite glasove |
| `film` | **animirani film uz Blender**: scenarij kao JSON, likovi (pas, mačka, zec, medvjed, miš, čovjek, vlastite slike ili `.blend` likovi), glasovi s pokretima usta, pokreti, kamera, slika pregleda, renderiranje scenu po scenu, montaža s titlovima ([upute](docs/filmstudio.md)) |
| `write_file` | uz pravo **pisanje datoteka**: odmah izrađuje poglavlja, HTML, CSV itd., tako da se u istom zadatku od njih može napraviti PDF/DOCX/EPUB |
| `make_document` | iz Markdown poglavlja **PDF, DOCX, EPUB ili HTML** (A4/A5, naslovna stranica, slike, dijakritici i turski znakovi); s `html` PDF slobodnog rasporeda iz **HTML+CSS** (izrada predložaka, preko WeasyPrinta, učitava samo datoteke iz projekta) |
| `video_generate` | **AI video isječak** iz teksta ili početne slike preko 12 pružatelja: Google Veo/Omni, OpenAI Sora, OpenRouter, Runway, Luma, **Kling**, **MiniMax Hailuo**, **Wan**, Seedance, **Higgsfield** (zadano MiniMax H3), fal.ai, Replicate. Zadano isključeno, uključuje se s `VIDEO_PROVIDER=…` + ključ, više njih odvojenih zarezom. **Naplaćuje se po isječku** kod pružatelja, pretplate na aplikacije se uglavnom ne računaju ([upute](docs/videodienste.md), na njemačkom) |
| `site_macro` | **MagicLight, Google Flow i druge stranice sa vašim računom**: robot u pregledniku (Playwright) koristi stranicu, čeka video i stavlja ga u `output/`. Zadano isključeno (`PCL_MACROS=1`), makroe jednom sami snimite ([macros/README.md](macros/README.md)). Rizik: može kršiti uvjete korištenja i prestaje raditi kad se stranica promijeni |
| `video_ai` | AI obrada preko fal.ai: **povećanje razlučivosti** videa, **sinkronizacija usana** sa snimkom glasa, **zvučni efekti** za nijemi video. Uključuje se s `VIDEO_AI=fal` + `FAL_KEY` |
| `sound_generate` | **zvučni efekti ili glazba** iz opisa (ElevenLabs ili fal.ai), uključuje se s `AUDIO_PROVIDER` |
| `media_info` | trajanje, rezolucija, kodeci |
| `download_file` | preuzima PDF, EPUB, Office, audio, video, ZIP s interneta u `downloads/` |
| `read_file` | čita tekst, Markdown, HTML, **PDF, DOCX, EPUB**, i duge datoteke po dijelovima |
| `view_image` | **vidi** slike, snimke zaslona, karte, rasporede i stranice skeniranih PDF-ova (treba model s razumijevanjem slika, npr. Claude, GPT-4o, Gemini) |

**Samokontrola:** kada agent napravi PDF, poslužitelj ga nakon toga prikaže kao sliku (pregled svih stranica + 1. stranica uvećano) i pošalje
mu uz obvezu da provjeri svaki zahtjev zadatka i ispravi pogreške prije nego što javi (`PCL_SELF_CHECKS`, zadano 1, 0 = isključeno).

**Vlastite datoteke** (video za obradu, PDF-ovi, slike, rasporedi, tekstovi) otpremate u „📁 Dateien dieses Projekts“ ili ih šaljete
izravno u **💬 Chat** s agentom (gumb 📎, povucite ih ili zalijepite sliku, više odjednom). Završe u
`input/` (ime se čisti, postojeće datoteke se nikada ne prepisuju nego postaju `name-1.png` …, granica `PCL_MAX_UPLOAD_MB`);
u chatu agent dobiva **sadržaj** izravno uz poruku (tekstovi, PDF-ovi, Word kao tekst, slike kao slike, ako model razumije slike;
inače prepoznavanje teksta). S **📂 aus input/** dodajete datoteke koje već stoje tamo, ili jednostavno upišete ime datoteke u poruku, a „Als Auftrag erteilen“ (pošalji kao zadatak) to prosljeđuje timu; gotovi rezultati su u `output/`, slike u `assets/`. Iskrena ograničenja: bez `video_generate` **nema AI generiranja videa** (tekst u video);
„animacija“ tada znači: scene kao slike uz AI slike + zum/pomicanje + govornik + montaža, ili prava animacija likova uz Blender preko alata `film`. Uz `video_generate` nastaju
kratki isječci; duži filmovi se sastavljaju s `video_edit op=concat`. MagicLight i Flow nemaju API: sa `site_macro` robot u pregledniku ih koristi sa vašim računom, inače videe napravljene tamo otpremite u `input/`. Model iza Flow-a (Veo 3.1) dostupan je i preko fal: `FAL_VIDEO_MODEL=fal-ai/veo3.1/fast`. Na Raspberry Pi-ju
ffmpeg radi sporo (jedna minuta 720p videa može trajati nekoliko minuta), vremensko ograničenje `PCL_FFMPEG_TIMEOUT` (zadano 1 sat po koraku).

**Skenirani PDF-ovi i slike (OCR):** `read_file` automatski čita skenove preko `tesseracta` (`sudo apt install tesseract-ocr tesseract-ocr-deu poppler-utils`). To je sporo (oko 5–15 s po stranici na Pi-ju, granica `PCL_OCR_MAX_PAGES`) i može sadržavati pogreške.

**Dobar glas govornika:** `./install.sh --piper` postavlja Piper s njemačkim glasom; nakon toga se automatski koristi za njemačke tekstove (ostali jezici: espeak-ng).

## Chat i predlošci

- **💬 Chat kartica** (u panelu agenta): slobodan razgovor sa svakim agentom, npr. s voditeljem *Gedankenwerkstatt*-a, za filozofiranje,
  razvijanje ideja i preispitivanje. „📋 Als Auftrag erteilen“ prosljeđuje razgovor agentu i njegovom timu; rezultat se vraća kao objava.
  Chat radi bez alata.
- **Predlošci tvrtki** (🏢): Web agencija, Računovodstvo/porezni ured, Uvoz/izvoz trgovina, **Animacijska agencija**, **Nakladnička kuća/agencija sadržaja**,
  **Radionica ideja**, **Istraživački ured** (pronalazi i čita PDF-ove). Pri osnivanju birate model za voditelja i suradnike.

## Pošta i Telegram

Čim je **zadatak na vrhu** (onaj koji ste dali agentu, obično CEO-u) gotov, neuspješan ili
blokiran, pošta je spremna za vas: u bočnoj traci „📬 Post“ i, ako je postavljeno, poruka na Telegramu s
vrstom, zadatkom, brojevima tima i rezultatom. Lanac prava i izvješća ispod radi kao i prije.
U pošti možete označiti poruke (pojedinačno ili „Alle auswählen“) i ukloniti ih sa „🗑 Ausgewählte löschen“;
„🧹 Postkorb leeren“ nakon potvrde briše sve. Briše se samo pošta, zadaci, datoteke i povijest ostaju.
Bočna traka je podijeljena u kategorije koje se otvaraju i zatvaraju (Tagesgeschäft, Team & KI, Dateien & Verbindungen, Auswertung).

**Postavljanje Telegrama (oko 2 minute):**
1. U Telegramu `@BotFather` → `/newbot` → kopirajte token → `.env`: `TELEGRAM_BOT_TOKEN=…`
2. `sudo systemctl restart hyperstead`, novom botu pošaljite `/start` → on vam kaže vaš ID chata.
3. `.env`: upišite `TELEGRAM_CHAT_ID=…`, ponovno pokrenite servis. Na webu pod „Post“ postoji probna poruka.

**Rad u Telegramu:**

| Vi radite | Rezultat |
|---|---|
| Samo napišete tekst | novi zadatak nadređenom odabranog projekta (`@Ime Tekst` = određeni agent) |
| **Odgovorite** na poruku pošte | zadatak se ponovno obrađuje s vašim tekstom kao uputom |
| Gumb ✅ ili odgovor „ok“ | zadatak se označava kao završen |
| Pošaljete datoteku, fotografiju, album, video ili glasovnu poruku | završi u `input/` odabranog projekta; natpis postaje zadatak (kao odgovor na objavu: za doradu), bez teksta datoteka ide vašem sljedećem zadatku. Telegram botovi smiju preuzeti datoteke do 20 MB, veće otpremite preko weba |
| `/post`, `/status`, `/ok <Br.>`, `/neu <Tekst>`, `/projekt [Br.]` | pregled odnosno kratke naredbe |
| `/datei [riječ za pretraživanje]` | šalje vam datoteku iz odabranog projekta (najnovije kao gumbi, jedini pogodak stiže odmah; do 50 MB) |

Aplikacija Telegram samo pita izvana, ne otvara se nijedan port (radi i iza CGNAT-a). Samo ID chata iz
`.env` smije davati naredbe; koristite privatni chat, ne grupu. Odobrenja za shell naredbe namjerno
**ne** idu preko Telegrama; tamo stiže samo napomena.

## Prava po agentu

- **Delegiranje**: smije dodjeljivati zadatke *neposrednim* suradnicima (do `PCL_MAX_DEPTH` razina, zadano 8).
  Neobavezno se sami pokreću, inače ih pokrećete sami.
- **Ocjenjivanje rezultata**: nadređeni smije vratiti posao s povratnom informacijom na doradu (najviše 2 kruga po suradniku).
- **Čitanje**: nadređeni uvijek vide izvješća svojih suradnika; za to nije potrebno posebno pravo.
- **Pisanje datoteka**: samo u `workspace/<id-projekta>/`; putanje izvan toga se odbijaju.
- **Pokretanje koda** (zadano isključeno): `run_code` pokreće Python, JavaScript, Bash, Ruby, PHP ili Lua u sandboxu, vidi dolje.
  Tu spada i `rust_project`: gradi i testira Rust programe i isporučuje gotov paket ([Rust programi](#-potpuna-izrada-rust-programa)).
- **Prijenos u oblak** (zadano isključeno): gotove datoteke na GitHub, Google Drive, OneDrive ili vama preko Telegrama, uvijek tek nakon vašeg odobrenja ([☁️ Prijenos u oblak](#️-prijenos-u-oblak-github-google-drive-onedrive-telegram)).
- **Predlaganje shella**: samo ako poslužitelj ima `PCL_ALLOW_SHELL=1`, i tada uvijek tek nakon odobrenja.
- **Radionica** (zadano isključena, samo uz `PCL_ALLOW_WERKSTATT=1`): radi sa stvarnim naredbama u mapi projekta i preko CEO-a traži od vas programe koji nedostaju ([docs/werkstatt.md](docs/werkstatt.md), na njemačkom). CEO ovo pravo ne može prenijeti dalje.
- **Pauza**: blokira sve nove zadatke agenta.

Prava se provjeravaju **na poslužitelju**. Ako model u svom odgovoru napiše nedopuštenu radnju, ona se zanemaruje i bilježi u povijesti.

## Pružatelji AI-ja i izbor modela

Za svakog agenta birate **pružatelja i model** (panel → Postavke). Aplikacija modele uživo preuzima od pružatelja;
sa **▶ Test** odmah provjeravate ključ i model. Tako postavljate odgovarajući model po ulozi: najjači za nadređene
(planiranje, provjera, razmišljanje), dobri modeli za tekst ili kod za suradnike, brzi i jeftini za jednostavan posao.

| Pružatelj | Ključ u `.env` | Napomena |
|---|---|---|
| Claude (Anthropic) | `ANTHROPIC_API_KEY` | Sonnet, Haiku, Opus … bira se po agentu |
| ChatGPT (OpenAI) | `OPENAI_API_KEY` | |
| OpenRouter | `OPENROUTER_API_KEY` | jedan ključ za stotine modela (Claude, GPT, Gemini, DeepSeek, Qwen, Llama …) |
| Groq, Gemini, DeepSeek, Qwen | `GROQ_API_KEY`, `GEMINI_API_KEY`, … | više ključeva odvojenih zarezom = rotacija kada se dostigne limit |
| Mistral, NVIDIA NIM, Together, Perplexity | `MISTRAL_API_KEY`, `NVIDIA_API_KEY`, `TOGETHER_API_KEY`, `PERPLEXITY_API_KEY` | Perplexity modeli (`sonar`) sami pretražuju web |
| Hugging Face, Cloudflare Workers AI | `HF_TOKEN` odnosno `CF_ACCOUNT_ID` + `CF_API_TOKEN` | male besplatne kvote |
| Ollama | – | lokalni modeli na Pi-ju |
| Claude (CLI, vaša pretplata) / ChatGPT (Codex CLI, vaša pretplata) | – | ugrađeno: `claude -p --tools "" --strict-mcp-config --no-session-persistence` (Claude bez vlastitih alata i konektora, samo tekst; radne upute zamjenjuju sistemski prompt Claude Codea) odnosno `codex exec --skip-git-repo-check --ephemeral -` (Codex sam radi u sandboxu samo za čitanje), model u padajućem izborniku (Claude: sonnet/opus/haiku); treba `PCL_ALLOW_CLI=1` i prijavljen program na Pi-ju |
| CLI agent | – | naredba koja čita prompt sa stdin-a, npr. `claude -p --model sonnet`; treba `PCL_ALLOW_CLI=1` |

**Važno:** web prijava (OAuth, „pretplata“) kod ChatGPT-a ili Claudea ne može se čisto koristiti kao API; preuzimanje
web sesija krši uvjete korištenja. Putovi: **API ključ** pružatelja (naplata po potrošnji, ne chat pretplata) ili
**CLI agent** sa službenim CLI-jem, jednom prijavljenim. Aplikacija nema proračun: kod plaćenih API-ja i mnogo krugova s alatima
mogu nastati troškovi; bilancu po agentu vidite na čvoru.

## Sigurnost

- Stranica za prijavu s potpisanim kolačićem (7 dana, `HttpOnly`, `SameSite=Strict`, `Secure` iza HTTPS-a).
- Nakon 5 pogrešnih lozinki zaključavanje od 10 minuta po IP adresi; svi pokušaji su u dnevniku revizije.
- Pišući API pozivi moraju imati vlastito zaglavlje (CSRF zaštita), uz CSP i dodatna zaglavlja.
- Shell i CLI agenti su zadano **isključeni**. Tko zna lozinku i ima postavljeno `PCL_ALLOW_SHELL=1`,
  može odobriti naredbe s pravima korisnika aplikacije. `workspace/` je radni direktorij, ali **nije sandbox**.
- `.env`, baza podataka i radne mape su u `.gitignore`. Ključevi nikada ne pripadaju repozitoriju.
- Kod botova za trgovanje (NEXUS) agentima nikada ne dopustite trgovinu bez ljudskog odobrenja.

## Znanje tvrtke i pamćenje

- **🧠 Znanje tvrtke** (bočna traka): ono što svi agenti projekta uvijek trebaju znati (tvrtka, klijenti, stil, cijene, pravila). Stoji u
  `wissen/firmenwissen.md` u mapi projekta. Svi `.md`/`.txt` datoteke u `wissen/` idu uz svaki zadatak i u chat (zajedno do
  `PCL_KNOWLEDGE_CHARS`, zadano 8000 znakova); ostale dokumente tamo (PDF, Word …) agenti vide kao popis i čitaju po potrebi.
- **Pamćenje po agentu**: agent na kraju zadatka može zapamtiti najviše 5 trajnih činjenica (preference, odluke, klijenti,
  što je radilo). One se prikazuju u panelu agenta pod „🧠 Gedächtnis“ (pamćenje); možete ih mijenjati ili brisati. Granica `PCL_MEMORY_CHARS`
  (4000); najstariji unosi prvi ispadaju. Svaka nova bilješka je u dnevniku revizije.

## Ciljevi, odobrenja, upotreba

- **🎯 Ciljevi**: ciljevi i podciljevi po projektu. Pri dodjeljivanju zadatka neobavezno birate cilj; delegirani zadaci ga nasljeđuju.
  Nadređeni vide ciljeve s napretkom u promptu, a CEO-ov kontrolni obilazak to izvješćuje. Označeno = ostvareno.
- **Prvo pitaj** (prozor ✋ Freigaben, po projektu, zadano isključeno): *Odobri plan najvišeg nadređenog* zadržava novi zadatak
  dok ne odobrite plan raspodjele; *Odobri izmjene tima* („Teamänderungen freigeben“) zadržava CEO-ovo zapošljavanje, otpuštanje i mijenjanje suradnika. Odobravanje/odbijanje i preko
  Telegram gumba. Odbijeno = zadatak završi kao ❌ u pošti; vaš odgovor na to tjera nadređenog da ponovno planira.
  Odobrenja za shell i dalje idu samo preko weba.
- **📊 Upotreba i troškovi**: pozivi, tokeni i procijenjeni troškovi po projektu, agentu i modelu (danas, 7, 30 dana). Bez limita.
  Pretplatni CLI-ji i Ollama broje se kao 0 $; od `PCL_ABO_WARN_5H` pretplatnih poziva u 5 sati (zadano 150, 0 = isključeno) stiže upozorenje na Telegramu.
  Cijene su grube procjene; vlastite zadajte preko `PCL_PRICES='{"sonnet": 5}'` (US$ po 1 milijun tokena, dio naziva modela).

## Testovi

```bash
./venv/bin/pip install pytest && ./venv/bin/python -m pytest -q tests
```
Radi bez interneta i bez ključeva (pružatelj `mock`, vlastita baza).

## 🔌 Veze (webhookovi)

- **Izlaz:** u prozoru 🔌 Verbindungen unosite adrese (n8n, Zapier, Make, vlastita usluga; i `http://127.0.0.1:…` na Pi-ju),
  s opisom za agente i neobaveznim zaglavljima. Tajne pripadaju `.env` i koriste se kao `${NAME}`.
  Agenti s pravom **„Darf Verbindungen nutzen“** (smije koristiti veze) zovu ih alatom `call_connection`; agent ne može mijenjati
  adresu ni zaglavlja, samo šalje podatke. **„Nur nach meiner Freigabe“** (samo nakon mog odobrenja, zadano uključeno) svaki poziv prvo stavlja pod ✋ Freigaben.
  **„Bei Post benachrichtigen“** (obavijesti u pošti) šalje svaki gotov rezultat zadatka na vrhu kao JSON na adresu. Vremensko ograničenje `PCL_CONN_TIMEOUT` (30 s).
- **Ulaz:** uključite „Aufträge von außen“ (zadaci izvana), zatim `POST /hook/<projekt>/<ključ>` s `{"text": "…", "agent": "neobavezno"}`
  prima zadatak za nadređenog (npr. iz n8n, iOS prečaca ili DEXTER-a). Bez prijave; štiti ga samo ključ u adresi.
  „Neuen Schlüssel“ (novi ključ) poništava staru adresu. Dostupna je samo onoliko koliko je dostupan i sam Hyperstead (npr. samo u tailnetu).

## ☁️ Prijenos u oblak (GitHub, Google Drive, OneDrive, Telegram)

- **Postavljanje:** pristupni podaci u `.env` (`GITHUB_UPLOAD_TOKEN` + `GITHUB_UPLOAD_REPO`, `GDRIVE_CLIENT_ID` + `GDRIVE_CLIENT_SECRET`,
  `ONEDRIVE_CLIENT_ID`), korak po korak u [docs/cloud.md](docs/cloud.md) (na njemačkom). Kod Googlea i Microsofta se zatim prijavljujete u prozoru
  **☁️ Cloud**: prikazuje kod koji na mobitelu unesete na stranici Googlea odnosno Microsofta (radi bez HTTPS-a).
  Prijava se čuva u `tokens/` pokraj `.env`, nikad u bazi podataka.
- **Ciljna mapa:** po projektu i usluzi u prozoru ☁️ Cloud (zadano `Hyperstead/<ime projekta>`). Agenti smiju odabrati samo
  podmapu ispod nje, npr. kada je navedete u zadatku.
- **Sami prenesite:** 📁 Datoteke → ☁️ pokraj datoteke → odaberite cilj i mapu. Dobivate poveznicu.
- **Agenti:** pravo **„Smije prenositi u oblak”** (postavljate samo vi). Alat `cloud_upload`; svaki prijenos čeka pod ✋ Odobrenja,
  uz to stiže Telegram poruka. Nakon prijenosa poveznica stoji u zadatku.
- **Postavljanje s CEO-om:** pitajte glavnog šefa u 💬 Chatu, npr. „Pomozi mi postaviti GitHub”. On zna trenutačno stanje svake usluge i upute te vas vodi korak po korak. Tokene nikad ne pišete u chat, nego ih sami unosite u `.env`.
- **Telegram:** `/datei` vam šalje datoteke do 50 MB na mobitel, samo kada kliknete ili odobrite.
- GitHub: do 50 MB kao datoteka u repozitoriju, veće kao privitak izdanju `paperclip-ablage` (do 2 GB). Google Drive: samo mape i datoteke koje je
  Hyperstead sam napravio (pravo `drive.file`). OneDrive: bilo koja mapa. Testirano samo na simuliranim uslugama.

## 🌐 Pravi preglednik i ▶ pokretanje koda

- **Preglednik** (`./install.sh --browser`, instalira Playwright + Chromium, oko 400 MB, samo 64-bitni sustav): agenti s pravom
  „Internet recherchieren“ (istraživanje interneta) dobivaju `browse_page`. Stranica radi uz JavaScript; agent dobiva vidljivi tekst, poveznice i
  po želji snimku zaslona (vidi je kao kod `view_image`; `save` je sprema u `assets/screenshots/`). Svaki zahtjev stranice
  (skripte, okviri, XHR, WebSocketi) mora ići na javnu adresu; LAN/localhost je blokiran, WebRTC i preuzimanja su isključeni.
  Samo jedan preglednik u isto vrijeme (RAM), vremensko ograničenje `PCL_BROWSER_TIMEOUT` (30 s). Vlastiti Chromium: `PCL_BROWSER_PATH`, isključeno: `PCL_BROWSER=0`.
- **Pokretanje koda** (`./install.sh --run`, instalira bubblewrap): pravo „Darf Code ausführen“ (smije pokretati kod, zadano isključeno) daje `run_code`.
  Skripta radi izolirano: **bez interneta**, vidljivi su samo `/usr` i mapa projekta (samo za čitanje pod `/projekt`),
  bez `.env`-a, bez baze, bez kućne mape. Ono što skripta upiše u svoj radni direktorij završi u `output/run/<vrijeme>/`
  (najviše 50 datoteka/50 MB). Granice: `PCL_RUN_TIMEOUT` (60 s), `PCL_RUN_MEM_MB` (1024). Pokreće Python/Node sustava,
  dakle samo pakete instalirane preko apta (npr. `sudo apt install python3-pandas python3-matplotlib`). Globalno isključeno: `PCL_ALLOW_RUN=0`.
  Provjera: `./venv/bin/python selftest.py run browser`.

## 🦀 Potpuna izrada Rust programa

Agentu s pravima **„Darf programmieren“**, **„Darf Dateien schreiben“** i **„Darf Code ausführen“** (smije programirati, pisati datoteke, pokretati kod) dajte zadatak kao
„Napiši mi Rust program koji …, s testovima, i isporuči gotov paket“. Agent tada radi od A do Ž:

1. Pomoću `write_code` pravi Cargo projekt, npr. `rust/rechner/Cargo.toml` i `rust/rechner/src/main.rs` s testovima (`#[test]`).
2. `rust_project` s `op=test` preuzima ovisnosti s crates.io, gradi program i pokreće testove.
   Greške se vraćaju s datotekom i redom, agent ih ispravlja i ponovno testira.
3. `op=package` još jednom testira, gradi release verziju i sprema **`output/<ime>.zip`**. Unutra: `programm/` (gotov
   program), `quelle/` (izvorni kod s `Cargo.lock`), `TESTBERICHT.txt` i `LIESMICH.txt`. Paket nastaje samo ako svi testovi prođu.

Paket dobivate u pošti ili pod **📁 Dateien** (pojedinačno ili u ZIP-u projekta). Ostale naredbe: `op=build`, `op=run` (s `args`, `stdin`).

- **Za koji sustav?** Program u `programm/` odgovara računalu na kojem radi Hyperstead: s Pi-ja Linux program (ARM),
  s Windows laptopa `.exe`. Za drugi sustav sami pokrenite `cargo build --release` u mapi `quelle/`.
- **Izolacija (Pi/Linux):** Izrada, testiranje i pokretanje idu u bubblewrapu kao `run_code`: bez interneta, bez `.env`, bez home mape,
  upisiva je samo mapa za izradu `.rust/` projekta. Internet ima samo `cargo fetch` (preuzima ovisnosti, ništa ne pokreće).
  Cargo postavke (`.cargo/`) i `rust-toolchain` datoteke iz projekta se ne koriste.
- **Windows:** Bez bubblewrapa alat ostaje isključen. S `PCL_CARGO_UNSAFE=1` u `.env` laptop gradi **bez izolacije**: kod agenata
  (testovi, `build.rs`) tada radi s vašim pravima i mogao bi čitati ili mijenjati datoteke na laptopu. API ključeve ne dobiva u
  okruženju. Uključite samo ako vjerujete agentima i njihovim modelima.
- **Instalacija Rusta:** Pi `curl https://sh.rustup.rs -sSf | sh` (novije od `apt install cargo`), Windows `winget install Rustlang.Rustup`
  i u instalaciji uzmite i „Visual Studio Build Tools (C++)“. Zatim ponovno pokrenite Hyperstead i izvršite `selftest.py rust`.
- **Granice:** `PCL_CARGO_TIMEOUT` (900 s po koraku), `PCL_CARGO_MEM_MB` (3072, samo Linux), `PCL_CARGO_JOBS` (2), uvijek samo jedna
  Rust izrada istovremeno. Prva izrada na Pi-ju traje dugo, nakon toga cargo ponovno gradi samo ono što se promijenilo. Agent ima
  `PCL_MAX_TOOL_STEPS` (zadano 6) krugova alata po pokretanju; za veće programe pomaže veća vrijednost, npr. 12. Isključeno: `PCL_CARGO=0`.

## 🛠 Radionica: agenti se sami nadograđuju

S pravom **„Radionica”** agent radi kao na stvarnom računalu, za svaku AI i u svakoj tvrtki. Claude (CLI uz pretplatu) dobiva svoje
Claude Code alate u mapi projekta, Codex svoje, a sve API AI i Ollama alat `befehl`. Ako program nedostaje, agent podnosi
**zahtjev za nadogradnju**: CEO ga provjerava, vi potvrđujete Telegram gumbom ili pod ✋ Odobrenja, zatim poslužitelj instalira točno tu
naredbu i zadatak se nastavlja. Ono što je instalirano navedeno je u `wissen/werkzeuge.md`.

- **Uključivanje:** `PCL_ALLOW_WERKSTATT=1` u `.env`, ponovno pokrenite, kod agenta označite polje i odaberite razinu.
- **Razine:** 1 = svaka naredba pita, 2 = rad u projektu je slobodan, instalacije i brisanje pitaju (zadano), 3 = sve slobodno
  (samo uz `PCL_WERKSTATT_FREI=1`). Pristupni podaci (`.env`, tokeni, ključevi) uvijek su blokirani.
- **Pozor:** naredbe se izvršavaju bez izolacije s vašim korisničkim pravima. Razina 2 prepoznaje instalacije po obliku, to nije sandbox.
- Sve ostalo, uključujući Remotion i probleme: [docs/werkstatt.md](docs/werkstatt.md) (na njemačkom).

## Paralelni rad

Istodobno može raditi do `PCL_WORKERS` zadataka (zadano 2, najviše 6), npr. više suradnika jednog nadređenog ili zadaci
različitih projekata. Agent nikada ne radi na dva zadatka odjednom, a istodobno radi najviše jedan Ollama zadatak
(RAM na Pi-ju). Kod pretplatnih CLI-ja (Claude, Codex) paralelni pozivi brže dostižu limit pretplate; tada postavite `PCL_WORKERS=1`.

## Granice ove verzije

- Nema automatskog heartbeata po rasporedu (zadaci se pokreću ručno ili delegiranjem).
- Nema AI za tekst u video, nema OCR za skenirane/slikovne PDF-ove; CEO sam ne zapošljava nove agente (organigram izrađujete vi).
- Pravi preglednik (`browse_page`) čita stranice, ali ne klikće i ne popunjava obrasce (bez prijava, bez kupnji). Pretraga DuckDuckGo-a bez ključa može biti ograničena ili promijenjena.
- Nema proračuna: tokeni i procijenjeni troškovi se samo prikazuju (📊). Limiti krugova (dorade, provjere, dubina) sprječavaju beskonačne petlje.
- Sesije su jednostavni potpisani kolačići; jedan uređaj ne može se posebno odjaviti
  (promjena lozinke poništava sve sesije).


## Samoprovjera

Nakon instalacije i unosa ključeva `./venv/bin/python selftest.py` provjerava sve stvarne stvari koje se bez interneta nisu mogle testirati:
web pretragu, čitanje stranica, pretragu slika i generator slika, SSRF zaštitu, svakog AI pružatelja mini zahtjevom (uključujući Ollama),
Telegram (token bota i probna poruka na vaš ID chata), ffmpeg, glasovni izlaz, PDF s dijakriticima, OCR. Pojedinačne skupine:
`selftest.py web | llm | telegram | media | ocr | rust | film`. Svaki redak prikazuje OK, FEHLT (neobavezno) ili FEHLER s konkretnom napomenom.

## Ollama (lokalni modeli)

Pružatelj „Ollama (lokal)“: ključ nije potreban, popis modela dolazi izravno iz Ollama (`ollama pull qwen2.5:3b`). U dijalogu „Firma aus Vorlage“ (tvrtka iz predloška)
postoje gumbi „Alles lokal“ (sve lokalno) i „Nur Mitarbeiter lokal“ (samo suradnici lokalno); inače Ollamu birate po agentu. Ako Ollama radi na drugom računalu
(npr. laptopu), postavite `OLLAMA_URL` na njegovu adresu. Mali modeli (3B) su na Pi-ju spori i često loše drže protokol alata;
za nadređene jak model, lokalno prije svega za jednostavne suradnike ili chat.

## Claude i ChatGPT preko vaše pretplate (CLI umjesto API ključa)

U `.env`: `PCL_ALLOW_CLI=1`. Programe sami instalirate i jednom prijavljujete na Pi-ju (upute proizvođača:
Claude Code `claude`, OpenAI Codex `codex`; prijava s vašom pretplatom). Nakon toga se „Claude (CLI, dein Abo)“ i „ChatGPT (Codex-CLI, dein Abo)“
pojavljuju u svim popisima pružatelja. Poslužitelj ih poziva bez shella, u praznoj mapi i **bez naših API ključeva u okruženju**
(inače bi `claude` naplaćivao API ključ umjesto pretplate). Ograničenja: sporije od API-ja (pokretanje programa po odgovoru), vrijede limiti pretplate
(mnogo agenata = brzo do limita), a CLI programi imaju vlastite alate; po potrebi prilagodite naredbu preko `PCL_CLI_CLAUDE` / `PCL_CLI_CODEX`.

## Model nestao? Prebacite agente

Hyperstead svakih 6 sati (`PCL_MODEL_CHECK_HOURS`) provjerava postoje li modeli agenata još kod pružatelja i primjećuje i kada poziv javi „Modell nicht gefunden“ (model nije pronađen). Tada stiže Telegram poruka, zadatak pada uz jasnu napomenu, a u izborniku **⚠ Modelle** sve pogođene agente prebacujete na drugi model jednim klikom.

## Veliki timovi

Nadređeni može imati koliko god želite suradnika. U panelu nadređenog (Postavke) pod **Unterstellte Mitarbeiter** (podređeni suradnici) označite sve potvrdnim poljima i spremite dodjelu. Alternativno: povucite donju točku nadređenog na suradnika. Gumb **🗂 Ordnen** (poredaj) izrađuje cijeli organigram (skupine od 6 i više suradnika u redovima po 5).

## CEO sam sastavlja svoj tim

CEO iz palete ima pravo **„Darf sein Team selbst zusammenstellen“** (smije sam sastaviti svoj tim, `recruit`). Ako još nema suradnike i dobije zadatak, analizira ga i stvara suradnike s ulogom, radnim uputama i linijama izvješćivanja (do 20, uključujući voditelje odjela s vlastitim timom). Novi suradnici **još nemaju AI**: dodjeljujete ih u izborniku **⚠ Modelle** (svi odjednom) ili po agentu u postavkama, pa odgovorite u **Pošti** na zadatak (npr. „Weiter“ = nastavi). Nakon toga CEO raspoređuje posao kao i obično. CEO novim suradnicima može dati samo web, slike, čitanje/pisanje datoteka, medije i programiranje, nikada shell.

**I kada tim već postoji**, CEO s ovim pravom smije pri svakom zadatku prilagoditi svoj tim vašim zadacima i uvjetima:
- **Zapošljavanje**: dodatni suradnici, kao gore bez AI. Dobivate poruku na Telegramu i dodjeljujete im AI. Posao dobivaju tek od sljedećeg zadatka ili nakon vašeg „Weiter“.
- **Otpuštanje**: samo suradnici ispod njega, nikada on sam niti agenti izvan njegova tima. Ljudi otpuštenoga pomiču se razinu više. Tko još ima otvoren zadatak, ne biva otpušten.
- **Izmjena**: uloga, radne upute i prava (samo gore navedena) suradnika ispod njega.

**Prava prema ulozi**: CEO treba svakome dati točno ona prava koja mu posao traži. Ako neka zaboravi, sustav ih dodaje na temelju imena, uloge i radnih uputa, npr. istraživanje → *web*, slike/ilustracije/grafika/dizajn → *slike* + *pisanje datoteka*, video/zvuk/glas/PDF/prijelom → *mediji* + *pisanje datoteka*, autor/tekst/lektura → *pisanje datoteka*, programiranje/web-stranica → *programiranje* + *pisanje datoteka*. Ako promijeni ulogu suradnika, prava se ponovno postavljaju prema njoj. Shell, izvršavanje koda, veze i objavljivanje nikada ne daje; to označavate samo vi.

Ako želite unaprijed vidjeti svaku izmjenu tima, označite u prozoru **Freigaben** *Teamänderungen freigeben* (odobri izmjene tima). Bez označene opcije kod CEO-a ne smije ništa od ovoga. Dnevni zadaci (raspored, kontrolni obilazak) nikada ne mijenjaju tim.

## Radno vrijeme i dnevni zadaci

Bočna traka **🕘 Zeitplan** (raspored): za svaki projekt postavite početak rada, kraj rada i radne dane. Za svakog suradnika možete napraviti **dnevne zadatke** (fiksno vrijeme, na početku ili na kraju rada, na odabranim danima u tjednu), npr. „svaki dan u 15:00 provjeri web stranicu“. Rezultat stiže u prikaz „Post“ kao svaka objava (i preko Telegrama). Ako je posljednji zadatak nekog rasporeda još u tijeku, ne pokreće se dvaput; ako je Pi u to vrijeme bio isključen, nadoknađuje se do 6 sati.
Na početku rada tvrtka ponovno preuzima zadatke koji su ostali nedovršeni (nepokrenuti se pokreću, neuspješni zadaci na vrhu ponavljaju se do `PCL_MAX_RESUMES`=2 puta). Neobavezno tvrtka potpuno miruje izvan radnog vremena. Vrijeme je ono s Pi-ja; ako nije točno, u `.env` postavite `PCL_TZ=Europe/Vienna`.

## CEO kontrolni obilazak

U prozoru **🕘 Zeitplan** **👑 CEO-Kontrollgang** (CEO kontrolni obilazak) postavlja se dnevni kontrolni obilazak najvišeg nadređenog (zadano: na kraju rada; ostala vremena preko „Neue tägliche Aufgabe“ + potvrdno polje *Kontrollgang*). Sustav mu prilaže **statusno izvješće** s činjenicama: po suradniku danas započeto/završeno/neuspješno/otvoreno, početci rada izvan radnog vremena, otvoreni zadaci bez početka rada, suradnici bez AI, nedovršeni zadaci i jesu li dnevni zadaci izvršeni. CEO to procjenjuje, po potrebi raspoređuje naredne zadatke svom timu i u pošti piše kontrolno izvješće. „📋 Statusbericht ansehen“ (pogledaj statusno izvješće) prikazuje činjenice bez CEO-a.

## Projektna mapa

Svaki projekt ima **mapu sa svojim imenom** pod `workspace/` (npr. `workspace/Buchverlag-Content-Agentur/`, njemački znakovi se transkribiraju). Ostaje ista kada se projekt preimenuje i **nikada se ne briše kada se projekt obriše**. Ako napravite novi projekt istog imena, preuzima postojeću mapu s datotekama. Stare mape s brojevima (`workspace/1`, `workspace/2` …) se pri pokretanju automatski preimenuju po imenu projekta.

## Objavljivanje web stranice

U prozoru **📁 Dateien dieses Projekts** postoji **🚀 Veröffentlichen** (objavi). Objavljuje se **samo mapa `www/` u mapi projekta** (`www/index.html`, uz CSS, slike … s relativnim putanjama); sve ostalo u projektu (bilješke, `output/`, `input/`, datoteke s točkom, simboličke veze prema vanjskome) ostaje nevidljivo. Ako nema mape `www/`, isporučuje se, kao i prije, `index.html` iz mape projekta (bez `input/` i skrivenih datoteka). Stranica trajno radi na vlastitom portu (od 8800, `PCL_SITE_PORT_BASE`), zadano samo na samom Pi-ju: `http://127.0.0.1:8800/`. Za pristup u mreži u `.env` postavite `PCL_SITE_HOST=0.0.0.0`. Agenti s pravom „Darf die Webseite zur Veröffentlichung vorschlagen“ (smije predložiti web stranicu za objavu) mogu zatražiti odobrenje za „veröffentlichen“; stranicu na mreži tek vaš klik pod **Freigaben** pušta online. Promjene agenata su odmah vidljive; nakon ponovnog pokretanja stranica se sama ponovno pokreće. Za otvoreni internet ispred mora stajati obrnuti proxy s HTTPS-om (npr. Caddy), a ne mali poslužitelj.
