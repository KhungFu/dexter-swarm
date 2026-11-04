# Hyperstead

🌐 Sprachen: **Deutsch** · [English](README.en.md) · [Türkçe](README.tr.md) · [Srpski](README.sr.md) · [Bosanski](README.bs.md) · [Hrvatski](README.hr.md)

Ein Agenten-Team als Knoten-Editor, selbst gehostet, leicht genug für den Raspberry Pi.
Projekt anlegen, Agenten per Drag & Drop auf die Fläche ziehen, verbinden (Chef → Mitarbeiter),
pro Knoten KI-Anbieter, Arbeitsanweisung und Rechte einstellen und Aufgaben zuweisen.

## Installation

Hyperstead ist ein Python-Programm (Flask + SQLite) und läuft auf mehreren Systemen. Mehrere Installationen
können parallel laufen, jede hat ihre eigenen Firmen und Daten.

| System | Stand | Anleitung |
| --- | --- | --- |
| Raspberry Pi / Linux (Debian, Ubuntu) | Hauptsystem, voller Funktionsumfang | unten |
| Windows 10/11 | läuft, ohne `run_code`, Rust bauen nur ohne Abschottung per Schalter, manches braucht Zusatzprogramme | [docs/windows.md](docs/windows.md) |
| macOS | ungetestet, Grundfunktionen sollten laufen | unten (von Hand) |
| Eigener Bildrechner (z. B. alter Laptop ohne Grafikkarte) | gratis Bilder mit Referenzbildern für Hyperstead | [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md) |

Umzug von einem Rechner auf einen anderen: Hyperstead beenden und `data.db`, den Ordner `workspace/` und `.env`
kopieren ([Beispiel Pi → Windows](docs/windows.md)).

### Raspberry Pi / Linux

```bash
git clone https://github.com/KhungFu/hyperstead && cd hyperstead
./install.sh --service     # venv, Abhängigkeiten, .env mit Zufallspasswort, systemd-Dienst
nano .env                  # API-Keys eintragen, danach: sudo systemctl restart hyperstead
```

Ohne Dienst: `./install.sh` und dann `./venv/bin/python app.py` → http://127.0.0.1:8787.
Das Login-Passwort steht in `.env` (`APP_TOKEN`). Update, Neustart, Sicherung: [Betrieb](#betrieb-wer-macht-was-wo-wann-wie).
Mehr Funktionen (Video, OCR, Compiler, Browser): `./install.sh --all`.

### Windows

PowerShell im Hyperstead-Ordner:

```powershell
git clone https://github.com/KhungFu/hyperstead; cd hyperstead
powershell -ExecutionPolicy Bypass -File install.ps1
notepad .env
deploy\windows\hyperstead-start.bat
```

Was unter Windows fehlt, Autostart und Parallelbetrieb mit dem Pi: [docs/windows.md](docs/windows.md).
Update, Neustart, Autostart: [Betrieb](#betrieb-wer-macht-was-wo-wann-wie).

### macOS (ungetestet)

```bash
git clone https://github.com/KhungFu/hyperstead && cd hyperstead
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
cp .env.example .env       # APP_TOKEN=<langes Passwort> eintragen, API-Keys ergänzen
./venv/bin/python app.py   # http://127.0.0.1:8787
```

`install.sh` ist für Debian/Ubuntu gebaut (apt), unter macOS daher von Hand wie oben. Zusatzprogramme per Homebrew
(`brew install ffmpeg tesseract poppler`). `run_code` gibt es nur unter Linux.

### Bilder auf einem eigenen Rechner

Ein Rechner im Heimnetz (auch ohne Grafikkarte, mind. 8 GB RAM) kann für Hyperstead gratis Bilder mit
Referenzbildern erzeugen. In `.env` genau diese zwei Zeilen aktiv lassen (nur eine `IMAGE_PROVIDER=`-Zeile ohne `#`):

```
IMAGE_PROVIDER=sdcpp
SDCPP_URL=http://<IP des Bildrechners>:1234    # auf dem Bildrechner selbst: http://127.0.0.1:1234
```

Einrichtung: [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md).

### Animationsfilme mit Blender

Ist Blender auf dem Rechner installiert, auf dem Hyperstead läuft, drehen die Agenten Zeichentrickfilme: Figuren mit eigenen
Stimmen und Mundbewegung, Szenen, Kamera, Untertitel, fertiger Film mit Ton (Werkzeug `film`, Firmenvorlage „🐶 Animationsstudio“).
Findet Hyperstead Blender nicht selbst, in `.env` eintragen:

```
BLENDER_PATH=C:\Program Files\Blender Foundation\Blender 4.2\blender.exe
```

Anleitung und Drehbuch-Format: [docs/filmstudio.md](docs/filmstudio.md).

## Betrieb: wer macht was, wo, wann, wie

**Wer:** alles hier erledigt der Besitzer des Rechners (du), nicht die Agenten. Die Befehle laufen im
Hyperstead-Ordner: auf dem Pi im Terminal (`cd ~/hyperstead`), unter Windows in PowerShell
(`cd $HOME\hyperstead`, oder wo du den Ordner hingelegt hast).

### Kurzübersicht

| Was | Wann | Raspberry Pi / Linux (mit Dienst) | Windows |
| --- | --- | --- | --- |
| Starten | nach der Installation, nach einem Neustart ohne Autostart | `sudo systemctl start hyperstead` | Doppelklick `deploy\windows\hyperstead-start.bat` (Fenster offen lassen) |
| Beenden | vor Umzug, Sicherung, Update | `sudo systemctl stop hyperstead` | Startfenster schließen (oder darin Strg+C) |
| Neu starten | nach jeder Änderung an `.env`, nach einem Update | `sudo systemctl restart hyperstead` | Startfenster schließen, `hyperstead-start.bat` neu starten |
| Läuft es? | bei Problemen | `systemctl status hyperstead` | Startfenster offen? Browser: <http://127.0.0.1:8787> |
| Protokoll ansehen | bei Fehlern | `journalctl -u hyperstead -f` (Strg+C beendet) | steht im Startfenster |
| Aktualisieren | wenn es eine neue Version gibt (z. B. nach einem gemergten Pull Request) | siehe unten | siehe unten |
| Prüfen | nach Installation, Update, neuen Keys | `./venv/bin/python selftest.py` | `venv\Scripts\python.exe selftest.py` |
| Keys / Einstellungen | neuer Key, anderer Bildanbieter | `nano .env`, dann neu starten | `notepad .env`, dann neu starten |
| Sichern | regelmäßig, vor Umzug und großen Updates | `data.db`, `workspace/`, `.env` kopieren (vorher beenden) | dasselbe im Hyperstead-Ordner |

### Aktualisieren (neue Version holen)

**Raspberry Pi / Linux**, im Terminal:

```bash
cd ~/hyperstead
git pull
./install.sh               # nur nötig, wenn sich requirements.txt geändert hat; .env bleibt unverändert
sudo systemctl restart hyperstead
./venv/bin/python selftest.py llm     # kurz prüfen, ob die KI-Anbieter antworten
```

**Windows**, in PowerShell:

1. `cd $HOME\hyperstead`
2. `git pull`
3. Nur wenn sich Pakete geändert haben (oder im Zweifel): `powershell -ExecutionPolicy Bypass -File install.ps1`
   (die vorhandene `.env` bleibt unverändert).
4. Das schwarze Startfenster von Hyperstead schließen.
5. `deploy\windows\hyperstead-start.bat` wieder starten (Doppelklick oder in PowerShell eingeben).
6. Prüfen: `venv\Scripts\python.exe selftest.py llm`

Meldet `git pull` „local changes would be overwritten“, hast du eine Datei im Programm selbst geändert.
`git stash` legt die Änderung beiseite, danach `git pull` wiederholen. Deine Daten (`data.db`, `workspace/`, `.env`)
sind davon nie betroffen, Git kennt sie nicht.

### Automatisch starten

- **Pi:** `./install.sh --service` richtet den Dienst ein, er startet dann bei jedem Hochfahren von selbst.
- **Windows:** Win+R, `shell:startup` eingeben, dort eine Verknüpfung zu `deploy\windows\hyperstead-start.bat`
  ablegen (und zu `bildrechner-start.bat`, falls genutzt). Windows muss sich dafür selbst anmelden
  ([docs/windows.md](docs/windows.md), Abschnitt 4).

### Einstellungen in `.env` ändern

- Jede Einstellung steht genau einmal ohne `#` am Anfang. Zeilen mit `#` sind abgeschaltet. Bei doppelten Zeilen
  gilt die erste.
- Nach jeder Änderung Hyperstead neu starten, sonst gilt noch der alte Stand.
- Keys nie in Chats, Screenshots oder ins Repo kopieren. Ist ein Key doch irgendwo gelandet: beim Anbieter
  widerrufen und einen neuen eintragen.
- Danach mit `selftest.py` prüfen. Einzelne Bereiche: `selftest.py llm`, `web`, `telegram`, `media`, `ocr`, `code`.

### Selbsttest lesen

- **OK:** funktioniert.
- **FEHLT:** optional, die Zeile nennt den Befehl zum Nachinstallieren (unter Windows den Windows-Befehl).
  Nur nötig, wenn deine Agenten das brauchen (z. B. Video, Vorlesen, gescannte PDFs).
- **FEHLER:** etwas Eingetragenes geht nicht, meistens ein ungültiger oder abgelaufener Key oder ein Dienst, der
  nicht läuft (z. B. der Bildrechner). Die Zeile nennt den Grund.
- Ein einzelner Zeitüberschreitungs-Fehler (Timeout) bei einem Webdienst ist oft nur vorübergehend: später wiederholen.

### Bildrechner (falls genutzt)

- **Wo:** auf dem Rechner, der die Bilder macht (z. B. Laptop), Ordner `C:\bildrechner`.
- **Wann:** muss laufen, solange Agenten Bilder erzeugen sollen.
- **Einrichten (einmal):** in PowerShell im Hyperstead-Ordner
  `powershell -ExecutionPolicy Bypass -File deploy\windows\bildrechner-einrichten.ps1` (lädt Programm und Modelle).
- **Wie:** `C:\bildrechner\bildrechner-start.bat` starten, Fenster offen lassen. In der `.env` von Hyperstead
  `IMAGE_PROVIDER=sdcpp` und `SDCPP_URL=...` ([Anleitung](docs/laptop-bildrechner.md)), danach Hyperstead neu starten.

### Filmstudio (falls genutzt)

- **Wo:** auf dem Rechner mit Blender (z. B. Laptop). Die Firma mit dem Werkzeug `film` muss in **dieser** Hyperstead-Instanz laufen.
- **Wann:** Blender muss nicht offen sein, Hyperstead startet es für jede Szene im Hintergrund und beendet es wieder.
- **Prüfen:** `venv\Scripts\python.exe selftest.py film` (Windows) bzw. `./venv/bin/python selftest.py film`.
- **Wie lange:** bei 640×360 und 12 Bildern/s je nach Laptop etwa 1 bis 5 Minuten pro 10 Sekunden Film. Blender läuft nie gleichzeitig mit dem Bildrechner.

### Umziehen (z. B. Pi → Laptop)

Schritt für Schritt in [docs/windows.md](docs/windows.md), „Phase 2 – Umzug“. Kurz: beide beenden, `data.db`,
`workspace/` und `.env` kopieren, auf dem neuen Rechner starten und prüfen, erst dann den alten abschalten.
Telegram immer nur auf einem Rechner eintragen.

### Was passiert, wenn etwas fehlt

Diese Liste wird bei jeder Änderung am Programm ergänzt. Jede Zeile sagt, was das System tut, und was du tun musst.

| Fehlt | Was das System macht | Was du tust |
| --- | --- | --- |
| `.env` | Hyperstead startet ohne Keys und ohne Passwort, nur für diesen Rechner erreichbar. Mit `HOST=0.0.0.0` bricht der Start ab, solange `APP_TOKEN` leer ist. | `./install.sh` (Pi) bzw. `install.ps1` (Windows) erzeugt sie mit Zufallspasswort. |
| `data.db` | Wird leer neu angelegt. Firmen, Aufträge und Post sind weg. | Vorher sichern (siehe Betrieb). Nur aus einer Sicherung zurückkopieren. |
| API-Key in `.env` | Der Anbieter wird im Selbsttest als FEHLT gemeldet und von den Agenten nicht benutzt. Ist er gesetzt, aber ungültig: FEHLER mit HTTP 401. | Key eintragen oder die Zeile mit `#` abschalten. |
| Ollama nicht erreichbar oder Modell zu groß | Die Aufgabe scheitert mit „Ollama nicht erreichbar“ bzw. „Zu wenig RAM für dieses Modell“; ein fehlendes Modell meldet „`ollama pull …`“. Liefert Ollama `OLLAMA_TIMEOUT` Sekunden lang nichts, bricht die Anfrage mit diesem Hinweis ab, ohne Wiederholung. | `systemctl status ollama`, kleineres Modell ziehen (`ollama pull qwen2.5:1.5b`) und im Agenten wählen, oder `OLLAMA_TIMEOUT` erhöhen. |
| `SDCPP_URL` (bei `IMAGE_PROVIDER=sdcpp`) | Bildanfragen schlagen mit „SDCPP_URL fehlt“ fehl. Mit `IMAGE_FALLBACK=pollinations` kommt ein kostenloses Ersatzbild ohne Referenzen, mit Hinweis im Ergebnis. | Zeile in `.env` ergänzen, Hyperstead neu starten. |
| Bildrechner nicht erreichbar (Laptop aus, Firewall, falsche IP) | Wie oben: Fehler „Bildrechner … nicht erreichbar“, mit Fallback ein Ersatzbild. | Laptop einschalten, `bildrechner-start.bat` starten, IP und Firewall prüfen. |
| `sd-server.exe` (Windows, Bildrechner) | `bildrechner-start.bat` zeigt „sd-server.exe fehlt“ und startet nichts. | `deploy\windows\bildrechner-einrichten.ps1` ausführen. |
| Modelldatei (Windows, Bildrechner) | Die Startdatei nennt die fehlende Datei und startet nicht. Fehlt nur das große Sprachmodell (`Qwen3-4B-Q4_K_M.gguf`), nimmt sie das kleinere, falls vorhanden. | Einrichtungsskript erneut starten, es lädt nur die fehlende Datei. |
| Windows-Laufzeit `VCOMP140.DLL` | `sd-server.exe` meldet „VCOMP140.DLL nicht gefunden“ und bricht ab. | Einrichtungsskript erneut starten (Schritt 3 installiert die Laufzeit), dann Startdatei öffnen. |
| Firewall-Regel Port 1234 (Windows) | Nur der Pi erreicht den Bildrechner nicht. Der Laptop selbst funktioniert weiter. | Befehl aus [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md), Abschnitt 4, als Administrator ausführen. |
| Makro in `macros/` oder Anmeldung `macros/<seite>.json` (mit `PCL_MACROS=1`) | Ohne Makro gibt es das Werkzeug `site_macro` nicht. Ohne gespeicherte Anmeldung bricht das Makro mit einem Hinweis ab. Ändert MagicLight oder Flow die Seite, meldet `site_macro` FEHLER und legt `<seite>-fehler.png` in `output/`. Der Selbsttest (`browser`) zeigt FEHLT. | Makro nach [macros/README.md](macros/README.md) aufnehmen bzw. neu aufnehmen. |
| `ffmpeg`, `tesseract`, `pdftoppm`, Sprachausgabe | Die Funktion fehlt. Agenten, die sie brauchen, melden den Fehler im Ergebnis. Der Selbsttest zeigt FEHLER (Pi) bzw. FEHLT (Windows). | Programm nachinstallieren (Befehle im Selbsttest und in [docs/windows.md](docs/windows.md)). |
| Blender (Werkzeug `film`) | `save`, `check`, `voices` und `assemble` gehen trotzdem. `preview` und `render` melden „Blender wurde nicht gefunden“ mit dem Hinweis auf `BLENDER_PATH`. Der Selbsttest zeigt FEHLT. | Blender installieren (`winget install BlenderFoundation.Blender`) oder `BLENDER_PATH` in `.env` setzen, neu starten. |
| `film/film.json` (Drehbuch) | `film` meldet „film/film.json fehlt“ und bittet, zuerst mit `op=save` ein Drehbuch zu speichern. Ein fehlerhaftes Drehbuch wird nicht gespeichert, die Antwort listet alle Fehler auf. | Nichts, die Agenten legen es selbst an. Du kannst es auch von Hand schreiben ([docs/filmstudio.md](docs/filmstudio.md)). |
| Bild-, Musik- oder `.blend`-Datei, die im Drehbuch steht | Die Prüfung nennt Szene, Figur und Pfad, es wird nichts gerendert. | Datei nach `assets/` oder `input/` legen oder den Pfad im Drehbuch korrigieren. |
| Clip einer Szene (`film/clips/`) | `assemble` nennt die fehlenden Szenen und schneidet nichts. Bricht `render` ab (Zeitlimit), bleiben die fertigen Bilder erhalten und der nächste Aufruf macht dort weiter. | Nichts, die Agenten rufen `render` erneut auf. |
| Sprachausgabe beim Film | `voices`/`render` brechen mit „Keine Sprachausgabe verfügbar“ ab. Szenen ganz ohne Dialog gehen trotzdem. | Wie bei „Sprachausgabe“ oben (unter Windows `edge-tts` + `TTS_ENGINE=edge`). |
| `cargo` (Rust, Werkzeug `rust_project`) | Das Werkzeug wird den Agenten nicht angezeigt, `check_code` prüft `.rs`-Dateien weiter, wenn `rustc` da ist. Der Selbsttest (`selftest.py rust`) zeigt FEHLT mit dem Installationsbefehl. | Rust installieren: Pi `curl https://sh.rustup.rs -sSf \| sh`, Windows `winget install Rustlang.Rustup`. Danach Hyperstead neu starten. |
| bubblewrap beim Rust-Bauen (Pi/Linux) | `rust_project` bleibt ausgeblendet, genau wie `run_code`. | `./install.sh --run` |
| `PCL_CARGO_UNSAFE=1` (Windows) | Unter Windows gibt es keine Abschottung, deshalb bleibt `rust_project` ohne den Schalter ausgeblendet. Mit Schalter baut der Laptop ohne Abschottung. | Nur setzen, wenn du das Risiko kennst ([Rust-Programme](#-rust-programme-komplett-bauen)), dann neu starten. |
| `Cargo.toml` im Rust-Ordner | `rust_project` meldet „In … fehlt Cargo.toml“ und nennt die Dateien, die der Agent zuerst anlegen muss. | Nichts, der Agent legt sie mit `write_code` an. |
| Internet für Rust-Abhängigkeiten (crates.io) | `cargo fetch` schlägt fehl, es wird nichts gebaut, der Agent bekommt die Fehlermeldung. Schon geladene Abhängigkeiten liegen in `.rust/cargo-home` und gehen weiter. | Internet prüfen und den Auftrag erneut starten. |
| Bestandene Tests beim Rust-Paket | Es entsteht **kein** Paket („KEIN PAKET“), der Agent bekommt die Fehler mit Zeile und muss sie beheben. Ohne Tests entsteht das Paket mit einer WARNUNG im Ergebnis. | Nichts, der Agent korrigiert und baut erneut. Beim Chef „zurückgeben“, falls er aufgibt. |
| Ordner `.rust/` im Projekt (Bauordner) | Wird beim nächsten Bau neu angelegt, das dauert dann länger (alles wird neu geladen und kompiliert). Er ist versteckt und nicht im ZIP-Download. | Nichts. Löschen ist erlaubt, wenn Platz fehlt. |
| Telegram-Token oder Chat-ID | Telegram bleibt aus, alles andere läuft. Der Selbsttest zeigt FEHLT. | Nur nötig, wenn du Nachrichten aufs Handy willst. |
| Ein Ordner oder eine Datei im Projekt (`wissen/`, `input/`) | Nicht vorhandene Ordner gelten als leer. Die Agenten arbeiten ohne Firmenwissen weiter. | Datei oder Ordner im Projekt anlegen oder hochladen. |
| Key eines Videoanbieters (z. B. `KLING_SECRET_KEY`, `HIGGSFIELD_API_KEY_SECRET`) | `video_generate` meldet „VIDEO_PROVIDER=…, aber … fehlt“ und erzeugt nichts, die anderen Anbieter aus der Liste gehen weiter. Der Selbsttest zeigt den Anbieter als FEHLT. | Key eintragen ([docs/videodienste.md](docs/videodienste.md)) oder den Anbieter aus `VIDEO_PROVIDER` streichen, neu starten. |
| Guthaben beim Videoanbieter | Der Anbieter antwortet mit einem Fehler (oft HTTP 402/429 oder „insufficient balance“), der Agent bekommt den Text ins Ergebnis. Es springt kein anderer Anbieter ein. | Guthaben aufladen oder mit `provider` bzw. in `VIDEO_PROVIDER` einen anderen Anbieter wählen. |
| `FAL_KEY` (bei `VIDEO_PROVIDER=fal`, `VIDEO_AI=fal` oder `AUDIO_PROVIDER=fal`) | `video_generate`, `video_ai` bzw. `sound_generate` meldet „FAL_KEY fehlt“ und erzeugt nichts. | Key von fal.ai eintragen oder die Zeile `VIDEO_AI`/`AUDIO_PROVIDER` entfernen. |
| `ELEVENLABS_API_KEY` (bessere Stimmen bei Bedarf) | Alles läuft wie bisher mit den lokalen Stimmen, die Agenten sehen keinen ElevenLabs-Hinweis. Wählt trotzdem jemand `engine: elevenlabs` oder steht `TTS_ENGINE=elevenlabs` in der `.env`, spricht die lokale Stimme und das Ergebnis beginnt mit „HINWEIS: ElevenLabs nicht genutzt (… fehlt)“. | Key von elevenlabs.io in `.env` eintragen und neu starten. Anleitung: 📖 → „🎙 Stimmen und ElevenLabs“. |
| Guthaben oder Internet bei ElevenLabs bzw. `OPENAI_API_KEY` (`TTS_ENGINE=openai`) | Die lokale Stimme springt ein, im Ergebnis steht ein HINWEIS mit HTTP-Code. Im Film wird die Zeile beim nächsten `voices` erneut mit der Cloud-Stimme versucht. Mit `TTS_FALLBACK=0` bricht die Aufgabe stattdessen ab. Gibt es auch keine lokale Stimme, meldet `speak` „Keine Sprachausgabe verfügbar“. | Guthaben aufladen bzw. Key prüfen. Für die Ersatzstimme espeak-ng oder Piper installieren. |
| KI eines vom CEO neu eingestellten Mitarbeiters | Der Neue wird angelegt, bekommt aber keine Aufgaben. Plant der CEO danach wieder, bricht der Auftrag mit „Diesen Mitarbeitern ist noch keine KI zugewiesen: …“ ab. Im Menü **⚠ Modelle** steht er als „Noch keine KI“. | KI im Menü ⚠ Modelle zuweisen und in der Post „Weiter“ antworten. |
| Rechte bei einem vom CEO eingestellten Mitarbeiter | Das System ergänzt fehlende Rechte anhand der Rolle (Tabelle oben). Passt kein Stichwort, bekommt er nur *Dateien lesen* und kann nur mit Text antworten. | Im Agenten-Panel die Häkchen setzen oder dem CEO die Rolle genauer vorgeben. |
| Mitarbeiter, den der CEO entlassen oder ändern will | Gibt es den Namen in seinem Team nicht (Tippfehler, anderes Team, schon entlassen), wird die Anweisung übersprungen und im Ergebnis vermerkt. Hat der Mitarbeiter noch eine offene Aufgabe, bleibt er. | Nichts, oder später erneut beauftragen. |
| `video_providers.py` (Programmdatei) | Die Video-, Ton- und Cloud-Stimmen-Werkzeuge verschwinden für die Agenten, alles andere läuft weiter. | `git pull` erneut ausführen, die Datei gehört zum Programm. |
| `GITHUB_UPLOAD_TOKEN` oder `GITHUB_UPLOAD_REPO` | GitHub erscheint unter ☁️ Cloud als „nicht eingerichtet“, Agenten bekommen es nicht als Ziel angeboten. Alles andere läuft. | Token und Repo eintragen ([docs/cloud.md](docs/cloud.md)), neu starten. |
| CUPS (`lp`) auf dem Pi, Drucker oder Druckrecht des CEO | Unter 🖨 Drucker steht „CUPS fehlt“ bzw. nur der Testdrucker. 🖨 Drucken meldet „kein Drucker gewählt“ oder „Drucken ist gesperrt“ und sendet nichts. | `./install.sh --print`, Drucker einrichten ([docs/drucken.md](docs/drucken.md)), unter 🖨 Drucker wählen und erlauben. |
| `GDRIVE_CLIENT_ID`/`GDRIVE_CLIENT_SECRET` oder `ONEDRIVE_CLIENT_ID` | Der Dienst bleibt „nicht eingerichtet“, der Knopf „Anmelden“ fehlt. | App registrieren und die Zeilen eintragen ([docs/cloud.md](docs/cloud.md)), neu starten. |
| Anmeldung bei Google/Microsoft (Ordner `tokens/`) | Der Dienst steht auf „nicht angemeldet“. Ein Upload meldet „noch nicht angemeldet“ bzw. „Anmeldung abgelaufen“ und lädt nichts hoch. | ☁️ Cloud → Anmelden. Beim Umzug Pi → Laptop einfach auf dem Laptop neu anmelden. |
| Datei über 50 MB für Telegram | Telegram nimmt sie nicht. `/datei` markiert sie mit ⚠️ und schickt sie nicht, der Agent bekommt den Hinweis. | Google Drive, OneDrive oder GitHub als Ziel nehmen. |
| `cloud_upload.py` (Programmdatei) | Hyperstead startet nicht (Fehler beim Import). | `git pull` erneut ausführen, die Datei gehört zum Programm. |
| `PCL_ALLOW_WERKSTATT=1` | Das Häkchen „Werkstatt“ ist grau, kein Agent bekommt `befehl` oder `nachruesten`. Alles andere läuft wie bisher. | Zeile in `.env` eintragen, neu starten, beim Agenten das Häkchen setzen ([docs/werkstatt.md](docs/werkstatt.md)). |
| Ein Programm, das ein Agent braucht (z. B. Node.js, Remotion, ein Python-Paket) | Mit Werkstatt stellt der Agent einen Nachrüst-Antrag: CEO prüft, du bekommst ✅/❌ per Telegram und unter ✋ Freigaben. Nach deinem Ja installiert der Server, die Aufgabe geht weiter. Ohne Werkstatt nennt der Agent nur, was fehlt. | Antrag lesen und entscheiden. Ohne Telegram nur im Web. |
| KI des CEO (bei einem Nachrüst-Antrag) | Der Antrag kommt mit dem Hinweis „Kein CEO mit KI“ bzw. „CEO nicht erreichbar“ direkt zu dir. | Selbst entscheiden oder dem CEO eine KI zuweisen. |
| `werkstatt.py` (Programmdatei) | Hyperstead startet nicht (Fehler beim Import). | `git pull` erneut ausführen, die Datei gehört zum Programm. |
| `growth.py` (Programmdatei) | Hyperstead startet nicht (Fehler beim Import). | `git pull` erneut ausführen, die Datei gehört zum Programm. |
| Welt eines Projekts nie gewählt | Das Projekt zeigt die Welt Weltall mit ihren Stufen und Begriffen. | Nichts zu tun. ⚛️ Atom in der Grafik-Auswahl stellt auf die Welt Atom um, 🌌 Weltall zurück. |
| Logo-Dateien in `static/logo/` | Seitenleiste und Anmeldeseite zeigen ein leeres Bildfeld, der Browser-Tab zeigt kein Symbol. Alles andere läuft normal. | `git pull` erneut ausführen. Neu erzeugen lässt sich das Logo mit `docs/logo/logo_blender.py` ([Anleitung](docs/logo-prompt.md)). |
| Frühere Welt (Gilde, Tycoon, Gizmo-Stadt) in einem Projekt gespeichert | Das Projekt zeigt automatisch das Weltall. Punkte, Stufe und Ränge bleiben gleich, nur Namen und Symbole ändern sich. | Nichts zu tun. |
| Keine KI-Aufrufe heute (Betriebszentrale, 💶 in der Leiste) | Zeigt 0 $ bzw. „keine Aufrufe“. | Nichts zu tun. Kosten sind Schätzungen, eigene Preise per `PCL_PRICES` in `.env`. |
| Tabelle `firm_links` (ältere `data.db`) | Wird beim Start automatisch angelegt, leer: in Stadt und Kosmos gibt es dann noch keine Zusammenarbeit. | Nichts. |
| Firmenlogo `.logo.png` / `.logo.jpg` / `.logo.webp` im Projektordner | Die Firma zeigt in Stadt und Kosmos kein Logo, alles andere läuft normal. | Im Infofenster der Firma (🏙/🌌, Firma antippen) unter „Logo“ 🖼 Hochladen wählen: PNG, JPEG oder WebP, höchstens 2 MB. |
| Noch kein Projekt | Stadt und Kosmos zeigen „Noch keine Firma“. | Links mit dem Knopf „＋ Neues Projekt“ eine Firma anlegen (leer oder aus Vorlage). |
| Browser speichert nichts (privates Fenster) | Hell/Dunkel, gewählte Grafik (Weltall, Organigramm-Art, Atom, Bauplan, Stadt/Kosmos), verschobene Organigramm-Karten, Bewegung und Hilfe-Modus fallen bei jedem Laden auf den Standard zurück. | Normales Fenster verwenden; die Daten der Projekte sind davon nicht betroffen. |
| Agenten im Bauplan liegen übereinander (z. B. alle auf derselben Stelle) | Die Verbindungslinien sind nicht zu sehen. Beim Öffnen des Bauplans ordnet Hyperstead sie einmal automatisch und meldet das. | Nichts, oder „🗂 Ordnen“ drücken. |

## Zugriff aus dem Internet

Die App lauscht absichtlich nur auf `127.0.0.1`. Statt einen Port zu öffnen, nutzt du einen Tunnel.
Das ist auch nötig, wenn dein Mobilfunk-Router keine eingehenden Verbindungen erlaubt (CGNAT).

### Option A (empfohlen): Tailscale, privat nur für deine Geräte

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up                    # Login-Link im Browser öffnen
sudo tailscale serve --bg 8787       # HTTPS-Adresse nur im eigenen Tailnet
```

Tailscale auch auf Handy/Laptop installieren, dann die angezeigte `https://dexter….ts.net`-Adresse öffnen.
In `.env` ergänzen: `TRUST_PROXY=1`, danach Dienst neu starten.
**Nicht** `tailscale funnel` benutzen, das würde die App öffentlich ins Netz stellen.

### Option B: Cloudflare Tunnel, öffentliche Adresse mit eigener Domain

```bash
# cloudflared installieren (siehe developers.cloudflare.com/cloudflare-one/connections/connect-networks)
cloudflared tunnel login
cloudflared tunnel create hyperstead
cloudflared tunnel route dns hyperstead agents.deine-domain.de
# ~/.cloudflared/config.yml:  ingress: - hostname: agents.deine-domain.de  service: http://127.0.0.1:8787
cloudflared tunnel run hyperstead
```

Zusätzlich dringend empfohlen: **Cloudflare Access** (E-Mail-Login) davor schalten.
In `.env`: `TRUST_PROXY=1`. Die Befehle können sich ändern, im Zweifel gilt die offizielle Anleitung.

Mit `TRUST_PROXY=1` startet die App nur, wenn `APP_TOKEN` mindestens 12 Zeichen hat.

## Bedienung

| Aktion | So geht's |
|---|---|
| Agent anlegen | Eintrag aus der Palette auf die Fläche ziehen (oder anklicken) |
| Verbinden | unteren Punkt eines Knotens auf einen anderen Knoten ziehen (= Chef → Mitarbeiter) |
| Trennen | Verbindungslinie anklicken |
| Verschieben | Knoten ziehen; Hintergrund ziehen = Ansicht verschieben; Mausrad = Zoom |
| Einstellen | Knoten anklicken → Panel rechts |
| Aufgabe zuweisen | Panel → Tab „Aufgaben" |
| Freigeben | Sidebar „Freigaben" |

## Wie das Unternehmen arbeitet

Ein Chef bekommt eine Aufgabe und **plant** (verteilt Teilaufgaben) oder erledigt sie selbst. Sobald alle
Mitarbeiter fertig sind, wacht er wieder auf, **liest ihre Berichte**, gibt Mängel mit Feedback zurück oder
fasst alles zusammen und berichtet an seinen Chef. So wandert das Ergebnis über beliebig viele Ebenen nach oben.
Status „Wartet auf Team“ heißt: der Chef wartet auf seine Leute. Im Aufgaben-Tab siehst du den ganzen Baum.

## Weltall und Wachstum

Jedes Projekt ist ein kleines **Universum**, das mit seinen Erfolgen wächst. Das Weltall ändert nur Begriffe, Symbole und Farben
der Oberfläche. Die Agenten arbeiten immer mit klaren Begriffen (Auftrag, Bericht, Team), damit ihre Qualität gleich bleibt.

| Im Weltall | Bedeutung im Team |
| --- | --- |
| ☀️ Sonne | oberste Leitung (z. B. der CEO) |
| 🪐 Planet | Abteilung bzw. Vorarbeiter:in, kreist um die Sonne |
| 🌙 Mond | Mitarbeiter:in, kreist um den eigenen Planeten (wer noch tiefer steht, ist ein kleiner Mond am Mond) |
| Stufen | ☄️ Asteroid → 🪐 Planet → ☀️ Sonnensystem → ✨ Sternhaufen → 🌌 Galaxie |
| Ränge der Agenten | ☄️ Komet → 🌙 Mond → 🪐 Planet → ⭐ Stern |

Punkte heißen Sternenstaub, Aufträge heißen Missionen. Die früheren Welten Gilde, Tycoon und Gizmo-Stadt gibt es nicht mehr; bestehende Projekte zeigen automatisch das Weltall, Punkte und Stufen bleiben erhalten.

**Welt Atom:** Neben dem Weltall gibt es eine zweite Welt. Wählst du in der Grafik-Auswahl ⚛️ Atom, gilt für das Projekt die Welt Atom, mit 🌌 Weltall wieder das Weltall (auch in der Wachstumsleiste, bei der Feier und in Telegram). Große Kugel = oberste Leitung, mittlere Kugeln = Teamleitungen, kleine Kugeln = Mitarbeiter:innen. Stufen: ✴️ Quark → ⚛️ Atom → 🧪 Molekül → 💎 Kristall → 🧬 Zelle; Ränge: · Neutrino → ⚡ Elektron → 🔴 Proton → 💠 Nukleon. Punkte heißen Energie, Aufträge Experimente. Punkte und Stufengrenzen sind in beiden Welten gleich. Organigramm und Bauplan behalten die zuletzt gewählte Welt.

**Bedienung:** Die Leiste über der Fläche zeigt Stufe, Fortschritt zur nächsten Stufe und die wichtigsten Zahlen. Rechts schaltest du zwischen Hell und Dunkel um (🌓) und öffnest mit ⓘ die Übersicht über Stufen, Punkte und Ränge. Der Rang jedes Agenten steht als Symbol auf seiner Karte.

**Sonnensystem:** Der aufklappbare Knopf rechts in der Leiste (z. B. „🌌 Weltall ▾“) wählt die Grafik: 🌌 Weltall, drei Organigramme, ⚛️ Atom oder 📐 Bauplan (Knoten-Editor). Das Weltall ist detailreich gezeichnet: Sonne mit Strahlen und Flecken, Planeten mit Schattenseite, Wolken oder Bändern, Monde mit Kratern, ein Asteroidengürtel, ferne Galaxien und die Milchstraße. Planeten und Monde kreisen langsam, die Planeten und die Sonne drehen sich dabei auch um die eigene Achse (Wolken, Streifen und Sonnenflecken wandern über die Oberfläche, der Strahlenkranz der Sonne kreist), als Galaxie dreht sich auch die Spirale im Hintergrund; zeigst du mit der Maus auf einen, bleibt alles stehen, damit du ihn gut triffst. Ein blau pulsierender Ring heißt „arbeitet“, ein gelber Ring „wartet auf deine Freigabe“, ein roter Ring „Fehler“, ein lila gestrichelter Ring „wartet auf sein Team“. Ein Tipp auf Sonne oder Planet zeigt das Team und Aktionen, ein Tipp auf einen Mond öffnet den Agenten. Mit jeder Stufe wird der Himmel voller, ab Sternhaufen leuchten Nebel, als Galaxie erscheint eine Spirale. Das Weltall bleibt auch im hellen Aussehen dunkel. Auf dem Handy erscheint statt der Karte eine Liste: Sonne, darunter jeder Planet mit seinen Monden. Bewegung wird abgeschaltet, wenn das Gerät „Bewegung reduzieren“ verlangt.

**Organigramm:** zeigt das Team in drei Arten, jede als eigener Punkt in der Grafik-Auswahl: ⬇ Baum (von oben nach unten, Mitarbeiter ohne eigenes Team stehen untereinander), ➡ Gliederung (eine Zeile je Agent, eingerückt nach Ebene, am besten fürs Handy) und ◎ Kreis (Leitung in der Mitte, jede Ebene ein Ring). Farbe zeigt den Zustand: grün bereit, blau arbeitet, gelb wartet auf deine Freigabe, rot Fehler, lila wartet auf das Team, grau pausiert. Antippen öffnet den Agenten. Karten lassen sich verschieben, die Linien gehen mit; das Gerät merkt sich das je Projekt und Art, „↺ Anordnung zurücksetzen“ stellt die Ordnung wieder her. Ziehst du eine Karte auf eine andere (auch im Bauplan einen Agenten auf einen anderen), fragt Hyperstead nach und stellt ihn erst dann in dieses Team.

**Atom:** ⚛️ zeigt das Team als Molekül-Netzwerk: glänzende Kugeln, verbunden durch Stäbe. Die große blaue Kugel ist die oberste Leitung, mittlere bunte Kugeln sind die Teamleitungen, kleine Kugeln die Mitarbeiter. Jede Kugel hängt per Stab an ihrem Vorgesetzten, die Hierarchie erkennt man an Größe und Verbindungen; angeordnet ist alles locker und räumlich wie ein Molekülmodell, nicht in starren Reihen. Jede Firma hat ihr eigenes Molekül: Form und Farben ergeben sich aus der Firma, die große Kugel trägt die Farbe des Projekts. In der modernen Ansicht zeigt ⚛️ Molekül alle Firmen als Moleküle nebeneinander; Partner-Firmen sind über einen leuchtenden Stab zwischen ihren Leitungen verbunden, auf dem Funken wandern (mehr, wenn beide arbeiten). Antippen zoomt in das Molekül, jede Kugel öffnet Abteilung und Agent. Die Grafik steht still, damit man in Ruhe lesen kann. Als Welt wächst das Bild mit der Stufe: als Quark leuchten drei Quarks im Kern, ab Molekül hängen Nachbaratome mit Bindungen daran, ab Kristall liegt ein Atomgitter im Hintergrund, als Zelle kommen Zellwand und Erbgut-Doppelhelix dazu. Zustand und Antippen wie im Organigramm.

**Projekte und Ansichten:** Links unter „Projekte“ öffnet der große Knopf „＋ Neues Projekt“ ein Fenster: leeres Projekt oder fertige Firma aus Vorlage. Die Grafik-Auswahl oben rechts hat zwei Gruppen: **Klassik** (die drei Organigramme Baum, Gliederung und Kreis sowie der Bauplan) und **Modern** (alle Firmen als Stadt, Kosmos oder Molekül). Weltall und Molekül für ein einzelnes Projekt gibt es nicht mehr; wer sie zuletzt offen hatte, landet im Organigramm. Die obere Leiste mit Projekt und Wachstum bleibt auch in Stadt, Kosmos und Molekül stehen, ebenso die Leiste „Agent hinzufügen“ darunter (neue Agenten kommen in das oben gewählte Projekt). Stadt, Kosmos und Molekül lassen sich drehen und neigen: Knöpfe ⟲ ⟳ ⤵ ⤴ ⌂ rechts unten, rechte Maustaste ziehen oder auf dem Handy zwei Finger. Wählst du links ein Projekt, leuchtet seine Firma in Stadt, Kosmos und Molekül auf, die anderen treten zurück.

**Alle Firmen (moderne Ebene):** 🏙 Stadt oder 🌌 Kosmos zeigt alle Projekte auf einmal. In der Grafik-Auswahl unter „Modern“ wählst du: 🏙 Stadt (jede Firma ein Gebäude, je größer die Firma, desto höher; die Lichter gehen an, sobald die Firma arbeitet, ruhige Firmen sind fast dunkel) und 🌌 Kosmos (jede Firma ein Sonnensystem, Planeten = Abteilungen, keine Linien zwischen Firmen). Antippen zoomt in die Firma hinein: in der Stadt das aufgeschnittene Gebäude (eine Etage je Hierarchie-Ebene, beliebig tief: ganz oben die Leitung in der Chefetage, darunter die Abteilungsleitungen, dann jede weitere Ebene; jede Person hat ihren eigenen Raum, eine Abteilung mit 4 Leuten auf einer Ebene hat dort 4 Räume nebeneinander in ihrer Farbe; jede Etage stellt ihre Räume mittig und in gleichen Abständen auf, Abteilungen bleiben beieinander, und das Gebäude ist so breit wie die vollste Etage; leuchtender Bildschirm = arbeitet; rechts das Organigramm). Mit Erfolg wächst das Gebäude: mehr Ebenen geben mehr Etagen, ab Stufe 2 kommen ein Anbau und ein Dachgarten dazu, ab Stufe 3 eine Antenne, ab Stufe 4 ein Hubschrauberlandeplatz, im Kosmos das große Sonnensystem (Sonne = Leitung, Planeten mit Symbol je Abteilung, Monde = Agenten). Jede Firma hat in der Stadt einen eigenen Baustil (Turm, Bürohaus, Zwillingstürme, Campus). Im Kosmos wächst die Sonne mit Stufe und Team. Die Planeten kreisen auch auf dem Handy und im geöffneten Sonnensystem (unter dem Finger oder der Maus halten sie an, damit man sie trifft); abschalten lässt sich das unter ⓘ „Bewegung“. Namen bleiben beim Herauszoomen lesbar. Links steht die Liste der Abteilungen, ein Tipp zeigt rechts das Team mit Zustand und laufenden Aufgaben; ein Name öffnet den Agenten klassisch. Oben sucht 🔍 nach Firmen und Agenten, „← Alle Firmen“ oder Esc führt hinaus. **🤝 Zusammenarbeit** (oben oder im Infofenster) verbindet zwei Firmen als Partner: nur dann gibt es in der Stadt eine Straße mit Lieferwagen und im Kosmos Raumschiffe zwischen den Sonnen. Ruhen beide, ist nur ein langsames Fahrzeug unterwegs; arbeiten sie, leuchtet die Straße und es wird mehr Verkehr. Firmen ohne Partnerschaft bleiben unverbunden, die Agenten merken davon nichts. Jede Firma kann im Infofenster unter „Logo“ ein eigenes Logo bekommen (🖼 Hochladen, PNG/JPEG/WebP bis 2 MB): in der Stadt steht es als leuchtendes Schild auf dem Dach, im Kosmos mitten in der Sonne. Beide Welten zeigen dieselben echten Daten. Plan: `docs/ebenen-plan.md`.

**Betriebszentrale:** 🛰 in der Seitenleiste (oder ein Tipp auf die Zahlen in der Wachstumsleiste) zeigt auf einen Blick, was gerade läuft und wartet, welche Freigaben offen sind, was in den letzten 7 Tagen fehlgeschlagen ist (mit ↻ Neu), die Zeitpläne (mit ▶ Jetzt), Fehlermeldungen und die letzten Ereignisse. Dazu die geschätzten KI-Kosten von heute und den letzten 7 Tagen; heute steht auch als 💶 in der Leiste. Alle Zahlen kommen aus den vorhandenen Aufgaben, Freigaben, Zeitplänen und dem Verlauf, nichts wird erfunden.

**Aufstieg und Bedienung:** Erreicht ein Projekt eine neue Stufe, erscheint eine kurze Feier mit der neuen Stufe und dem nächsten Ziel (per Telegram kommt dieselbe Nachricht). Steigt ein Agent im Rang auf, meldet das eine kurze Einblendung. Unter ⓘ in der Leiste lassen sich Bewegung und Feier-Effekte für dieses Gerät abschalten; verlangt das Gerät „Bewegung reduzieren“, bleibt ohnehin alles ruhig. Alle Fenster schließen mit Esc, Sonne, Planeten und Monde im Weltall lassen sich mit Tab und Enter bedienen.

**Anleitung und Hilfe:** 📖 Anleitung ganz oben in der Seitenleiste öffnet die Bedienungsanleitung direkt im Dashboard (Kapitel zum Aufklappen, mit Suche, ohne Download, auch offline). ⓘ oben in einem Fenster springt zum passenden Kapitel. Jeder Knopf zeigt beim Draufzeigen mit der Maus eine kurze Erklärung. Auf dem Handy schaltest du in der Anleitung den Hilfe-Modus ein: Das erste Tippen auf einen Knopf erklärt ihn, das zweite führt ihn aus.

**Punkte:** Lieferung beim ersten Mal abgenommen +10, nach Überarbeitung +5, Auftrag in der Post als erledigt markiert +20,
fehlgeschlagen −3, Nacharbeit angefordert −5. Stufen ab 0 / 100 / 300 / 700 / 1500 Punkten. Bestehende Projekte bekommen
ihre bisherigen Erfolge automatisch angerechnet. Ein Aufstieg kommt einmal per Telegram.

**Was die Stufe begrenzt:** nur, wie viele Agenten die Führung **selbst** anwerben darf (8 / 12 / 18 / 25 / unbegrenzt
im Projekt) und wie tief (2 / 3 / 4 / 5 / volle Tiefe). Du selbst kannst immer alles anlegen. Die Grenze lässt sich je
Projekt abschalten.

**Ränge der Agenten** nach eigenen abgenommenen Lieferungen: ab 0 / 5 / 20 / 60 (z. B. Lehrling, Geselle, Meister, Großmeister).

## Fähigkeiten der Agenten (Internet, Bilder, Dateien)

Agenten arbeiten in Runden: Sie fordern Werkzeuge an, der Server führt sie aus und gibt die Ergebnisse zurück, bis sie
fertig sind (max. `PCL_MAX_TOOL_STEPS`). Rechte pro Agent: **Internet recherchieren**, **Bilder**, **Projektdateien lesen**
(plus wie bisher Dateien schreiben).

| Werkzeug | Was es tut | Ohne Key |
|---|---|---|
| `web_search` | Websuche (Gesetze, Preise, Wettbewerb …) | DuckDuckGo; besser: `SEARXNG_URL`, `BRAVE_API_KEY` oder `TAVILY_API_KEY` |
| `fetch_url` | Webseite als Text lesen | ja |
| `browse_page` | Seite in einem echten Browser öffnen (JavaScript läuft), optional mit Screenshot, den der Agent als Bild sieht | ja, braucht `./install.sh --browser` |
| `image_search` / `image_save` | frei lizenzierte Fotos suchen und in `assets/` speichern, mit Urheber und Lizenz | Openverse; optional `PEXELS_API_KEY` |
| `image_generate` | KI-Bild als PNG erzeugen, optional mit bis zu 4 Referenzbildern aus dem Projekt (gleiche Figuren und gleicher Stil über eine Serie), Format quadrat/hoch/quer und Zielpfad in `assets/`, `output/` oder `karten/`. Recht **Bilder** oder **Medien** | Pollinations (ohne Key: ohne Referenzbilder; mit `POLLINATIONS_API_KEY` und Pollen-Guthaben: Modell per `POLLINATIONS_MODEL`, mit Referenzbildern); `IMAGE_STYLE` legt einen festen Zeichenstil fest; weitere: `nvidia` (FLUX über build.nvidia.com), `cloudflare` (Workers AI, FLUX.2 klein mit Referenzbildern), `hf` (Hugging Face), Modell jeweils per `IMAGE_MODEL`; gratis mit Referenzbildern auf eigenem Rechner: `IMAGE_PROVIDER=sdcpp` ([Anleitung](docs/laptop-bildrechner.md)); besser `IMAGE_PROVIDER=openai` mit `OPENAI_API_KEY`, `gemini` oder `openrouter` mit `OPENROUTER_API_KEY` |
| `list_files` / `read_file` | Dateien im Projektordner lesen (z. B. Texte der Kollegen) | ja |

Alles Erzeugte liegt unter `workspace/<projekt-id>/`. In der Sidebar zeigt **📁 Dateien** die Dateien, öffnet `index.html`
als Webseite (isolierte Sandbox) und lädt alles als ZIP. Der Link enthält einen geheimen Schlüssel.

**Firmenvorlagen** (Knopf „＋ Neues Projekt“): *Webagentur*, *Buchhaltung/Steuerkanzlei*, *Import/Export-Handel* legen Projekt,
Organigramm, Arbeitsanweisungen und Rechte komplett an. Eigene Firmen: Projektziel schreiben („ihr seid eine …“, Land,
Branche), Agenten und Rechte setzen. Die Agenten bekommen Datum und Projektziel mit und sollen Veränderliches (Gesetze,
Preise) erst recherchieren und Quellen nennen.

**Sicherheit der Werkzeuge:** Seitenabrufe sind auf öffentliche Adressen beschränkt (kein localhost, LAN, Tailscale,
Cloud-Metadaten; Weiterleitungen werden einzeln geprüft). Webinhalte gelten für die Agenten als unvertrauenswürdige Daten,
trotzdem kann eine präparierte Seite ein Modell beeinflussen: gib Agenten mit Internet keine Shell und prüfe Ergebnisse.
Agenten haben bewusst **keine** Werkzeuge für Käufe, Orders, Zahlungen oder E-Mail-Versand, sie liefern Entwürfe und Empfehlungen.
Bildlizenzen (CC) verlangen oft eine Namensnennung, der Bildredakteur schreibt dafür `bildnachweis.md`.

## Medien, Dokumente und eigene Dateien

Mit dem Recht **Medien & Dokumente erstellen** (und `ffmpeg`/Schriften auf dem Pi, siehe `install.sh`):

| Werkzeug | Was es kann |
|---|---|
| `video_edit` | Video schneiden (`trim`), zusammenfügen (`concat`), **Diashow-Animation mit Zoom** aus Bildern (`slideshow`, optional mit Ton), Text/Untertitel/Logo einblenden, Ton ersetzen/mischen, Tempo ändern, in GIF/WebM/MP3 umwandeln, Standbild ziehen |
| `speak` | Text zu Sprecher-Audio (espeak-ng offline; besser: Piper; optional Edge-Stimmen oder Cloud-Stimmen von ElevenLabs/OpenAI über `TTS_ENGINE`), mit `voice`, `pitch`, `rate` für verschiedene Stimmen. Mit `ELEVENLABS_API_KEY` nehmen die Agenten ElevenLabs gezielt dort, wo es gut klingen muss (`engine: elevenlabs`, auch je Filmfigur), `list_voices` zeigt die Stimmen des Kontos |
| `film` | **Animationsfilm mit Blender**: Drehbuch als JSON, Figuren (Hund, Katze, Hase, Bär, Maus, Mensch, eigene Bilder oder `.blend`-Figuren), Stimmen mit Mundbewegung, Bewegungen, Kamera, Vorschaubild, Rendern Szene für Szene, Schnitt mit Untertiteln ([Anleitung](docs/filmstudio.md)) |
| `write_file` | mit dem Recht **Dateien schreiben**: legt Kapitel, HTML, CSV usw. sofort an, damit im selben Auftrag daraus ein PDF/DOCX/EPUB wird |
| `make_document` | aus Markdown-Kapiteln **PDF, DOCX, EPUB oder HTML** (A4/A5, Cover, Bilder, Umlaute und türkische Zeichen); mit `html` aus **HTML+CSS** ein PDF mit freiem Layout (Vorlagen nachbauen, per WeasyPrint, lädt nur Dateien aus dem Projekt) |
| `video_generate` | **KI-Videoclip** aus Text oder Startbild über 12 Anbieter: Google Veo/Omni, OpenAI Sora, OpenRouter, Runway, Luma, **Kling**, **MiniMax Hailuo**, **Wan**, Seedance, **Higgsfield** (Standard MiniMax H3), fal.ai, Replicate. Standard aus, einschalten mit `VIDEO_PROVIDER=…` + Key, mehrere mit Komma getrennt. **Kostet pro Clip** beim Anbieter, App-Abos zählen meist nicht ([Anleitung](docs/videodienste.md)) |
| `site_macro` | **MagicLight, Google Flow und andere Seiten mit deinem Konto**: Ein Browser-Roboter (Playwright) bedient die Seite, wartet aufs Video und legt es in `output/`. Standard aus (`PCL_MACROS=1`), die Makros nimmst du einmal selbst auf ([macros/README.md](macros/README.md)). Risiko: kann gegen die Nutzungsbedingungen verstoßen und bricht, wenn die Seite sich ändert |
| `video_ai` | KI-Nachbearbeitung über fal.ai: Video **hochskalieren**, **Lippensync** zu einer Sprachaufnahme, **Geräusche** zum stummen Video. Einschalten mit `VIDEO_AI=fal` + `FAL_KEY` |
| `sound_generate` | **Geräusche oder Musik** aus einer Beschreibung (ElevenLabs oder fal.ai), einschalten mit `AUDIO_PROVIDER` |
| `media_info` | Dauer, Auflösung, Codecs |
| `download_file` | PDFs, EPUB, Office, Audio, Video, ZIP aus dem Netz in `downloads/` laden |
| `read_file` | liest Text, Markdown, HTML, **PDF, DOCX, EPUB**, auch lange Dateien in Abschnitten |
| `view_image` | **sieht** Bilder, Screenshots, Karten, Layouts und Seiten gescannter PDFs an (braucht ein Modell mit Bildverständnis, z. B. Claude, GPT-4o, Gemini) |

**Selbstkontrolle:** Erzeugt ein Agent ein PDF, rendert der Server es danach als Bild (Übersicht aller Seiten + Seite 1 groß) und schickt es
ihm mit der Pflicht, jede Anforderung des Auftrags zu prüfen und Fehler zu beheben, bevor er meldet (`PCL_SELF_CHECKS`, Standard 1, 0 = aus).

**Eigene Dateien** (Videos zum Bearbeiten, PDFs, Bilder, Layouts, Texte) lädst du in „📁 Dateien dieses Projekts“ hoch oder schickst sie
direkt im **💬 Chat** mit einem Agenten mit (📎-Knopf, hineinziehen oder Bild einfügen, mehrere auf einmal). Sie landen in
`input/` (Name bereinigt, vorhandene Dateien werden nie überschrieben, sondern `name-1.png` …, Grenze `PCL_MAX_UPLOAD_MB`); im Chat
bekommt der Agent den **Inhalt** direkt mit der Nachricht (Texte, PDFs, Word als Text, Bilder als Bild, sofern das Modell Bilder versteht;
sonst Texterkennung). Mit **📂 aus input/** hängst du Dateien an, die schon dort liegen, oder du schreibst einfach den Dateinamen in die Nachricht, und „Als Auftrag erteilen“ gibt ihn ans Team weiter; fertige Ergebnisse liegen in `output/`, Bilder in `assets/`. Ehrliche Grenzen: Ohne `video_generate` gibt es **keine KI-Videogenerierung**
(Text-zu-Video), „Animation“ heißt dann: Szenenbilder per Bild-KI + Zoom/Schwenk + Sprecher + Schnitt, oder mit Blender echte Figurenanimation über `film`. Mit `video_generate` entstehen
kurze Clips, längere Filme setzt `video_edit op=concat` zusammen. MagicLight und Flow haben keine API: Mit `site_macro` bedient ein Browser-Roboter sie mit deinem Konto, sonst lädst du dort erzeugte Videos nach `input/` hoch. Das Modell hinter Flow (Veo 3.1) geht auch über fal: `FAL_VIDEO_MODEL=fal-ai/veo3.1/fast`. Auf dem Raspberry Pi
rechnet ffmpeg langsam (eine Minute 720p-Video kann mehrere Minuten dauern), Zeitlimit `PCL_FFMPEG_TIMEOUT` (Standard 1 Stunde je Schritt).

**Gescannte PDFs und Bilder (OCR):** `read_file` liest Scans automatisch per `tesseract` (`sudo apt install tesseract-ocr tesseract-ocr-deu poppler-utils`). Das ist langsam (ca. 5–15 s je Seite auf dem Pi, Limit `PCL_OCR_MAX_PAGES`) und kann Fehler enthalten.

**Gute Sprecherstimme:** `./install.sh --piper` richtet Piper mit deutscher Stimme ein; sie wird danach automatisch für deutsche Texte genutzt (andere Sprachen: espeak-ng).

## Chat und Vorlagen

- **💬 Chat-Tab** (im Agenten-Panel): freies Gespräch mit jedem Agenten, z. B. mit der Leitung der *Gedankenwerkstatt*, zum Philosophieren,
  Ideen entwickeln und Hinterfragen. „📋 Als Auftrag erteilen“ übergibt das Gespräch dem Agenten und seinem Team, das Ergebnis kommt als Post.
  Der Chat läuft ohne Werkzeuge.
- **Firmenvorlagen** (🏢): Webagentur, Buchhaltung/Steuerkanzlei, Import/Export-Handel, **Animationsagentur**, **Buchverlag/Content-Agentur**,
  **Gedankenwerkstatt**, **Recherchebüro** (findet und liest PDFs). Beim Gründen wählst du Modell für Leitung und Mitarbeiter.

## Post und Telegram

Sobald ein **oberster Auftrag** (den du einem Agenten, meist dem CEO, gegeben hast) fertig, fehlgeschlagen oder
blockiert ist, liegt Post für dich bereit: Sidebar „📬 Post“ und, wenn eingerichtet, eine Telegram-Nachricht mit
Art, Auftrag, Team-Kennzahlen und dem Ergebnis. Die Rechte-/Berichtskette darunter läuft wie gehabt.
In der Post lassen sich Nachrichten anhaken (einzeln oder „Alle auswählen“) und mit „🗑 Ausgewählte löschen“ entfernen;
„🧹 Postkorb leeren“ löscht nach einer Rückfrage alle. Gelöscht wird nur die Post, Aufgaben, Dateien und Verlauf bleiben.
Die Seitenleiste ist in aufklappbare Kategorien geordnet (Tagesgeschäft, Team & KI, Dateien & Verbindungen, Auswertung).

**Telegram einrichten (ca. 2 Minuten):**
1. In Telegram `@BotFather` → `/newbot` → Token kopieren → `.env`: `TELEGRAM_BOT_TOKEN=…`
2. `sudo systemctl restart hyperstead`, dem neuen Bot `/start` schreiben → er nennt deine Chat-ID.
3. `.env`: `TELEGRAM_CHAT_ID=…` eintragen, Dienst neu starten. Im Web unter „Post“ gibt es eine Testnachricht.

**Bedienung in Telegram:**

| Du tust | Ergebnis |
|---|---|
| Einfach Text schreiben | neuer Auftrag an den Chef des gewählten Projekts (`@Name Text` = bestimmter Agent) |
| Auf eine Post-Nachricht **antworten** | Auftrag wird mit deinem Text als Anweisung neu bearbeitet |
| Button ✅ oder Antwort „ok“ | Auftrag als erledigt markiert |
| Datei, Foto, Album, Video oder Sprachnachricht senden | landet in `input/` des gewählten Projekts; die Bildunterschrift wird zum Auftrag (als Antwort auf Post: zur Überarbeitung), ohne Text geht die Datei an deinen nächsten Auftrag. Telegram-Bots dürfen nur Dateien bis 20 MB laden, größere im Web hochladen |
| `/post`, `/status`, `/ok <Nr>`, `/neu <Text>`, `/projekt [Nr]` | Übersicht bzw. Kurzbefehle |
| `/datei [Suchwort]` | schickt dir eine Datei aus dem gewählten Projekt (die neuesten als Knöpfe, ein einziger Treffer kommt sofort; bis 50 MB) |

Die App fragt Telegram nur nach außen ab, es wird kein Port geöffnet (geht auch hinter CGNAT). Nur die Chat-ID aus
`.env` darf Befehle geben, nimm einen privaten Chat, keine Gruppe. Freigaben für Shell-Befehle laufen bewusst
**nicht** über Telegram, dort kommt nur ein Hinweis.

## Rechte pro Agent

- **Delegieren**: darf Aufgaben an *direkte* Mitarbeiter verteilen (bis `PCL_MAX_DEPTH` Ebenen, Standard 8).
  Optional starten sie automatisch, sonst startest du sie selbst.
- **Ergebnisse beurteilen**: der Chef darf Arbeit mit Feedback zur Überarbeitung zurückgeben (max. 2 Runden je Mitarbeiter).
- **Lesen**: Chefs sehen immer die Berichte ihrer Mitarbeiter, dafür ist kein eigenes Recht nötig.
- **Dateien schreiben**: nur in `workspace/<projekt-id>/`, Pfade außerhalb werden abgelehnt.
- **Code ausführen** (Standard aus): `run_code` startet Python, JavaScript, Bash, Ruby, PHP oder Lua in einer Sandbox, siehe unten.
  Dazu gehört `rust_project`: Rust-Programme bauen, testen und als fertiges Paket abliefern ([Rust-Programme](#-rust-programme-komplett-bauen)).
- **In die Cloud hochladen** (Standard aus): fertige Dateien zu GitHub, Google Drive, OneDrive oder per Telegram an dich, immer erst nach deiner Freigabe ([☁️ Cloud-Upload](#️-cloud-upload-github-google-drive-onedrive-telegram)).
- **Shell vorschlagen**: nur wenn der Server `PCL_ALLOW_SHELL=1` hat, und dann immer erst nach Freigabe.
- **Werkstatt** (Standard aus, nur mit `PCL_ALLOW_WERKSTATT=1`): arbeitet mit echten Befehlen im Projektordner und beantragt fehlende Programme über den CEO bei dir ([docs/werkstatt.md](docs/werkstatt.md)). Ein CEO kann dieses Recht nicht weitergeben.
- **Pause**: blockiert alle neuen Aufgaben des Agenten.

Die Rechte werden **serverseitig** geprüft. Schreibt ein Modell eine nicht erlaubte Aktion in seine
Antwort, wird sie ignoriert und im Verlauf protokolliert.

## KI-Anbieter und Modellwahl

Pro Agent wählst du **Anbieter und Modell** (Panel → Einstellungen). Die Modellliste holt die App live vom Anbieter,
mit **▶ Testen** prüfst du Key und Modell sofort. So setzt du das passende Modell pro Rolle: stärkstes für Chefs
(Planen, Prüfen, Denken), gute Text- oder Code-Modelle für Mitarbeiter, schnelle günstige für einfache Arbeit.

| Anbieter | Key in `.env` | Hinweis |
|---|---|---|
| Claude (Anthropic) | `ANTHROPIC_API_KEY` | Sonnet, Haiku, Opus … je Agent wählbar |
| ChatGPT (OpenAI) | `OPENAI_API_KEY` | |
| OpenRouter | `OPENROUTER_API_KEY` | ein Key für hunderte Modelle (Claude, GPT, Gemini, DeepSeek, Qwen, Llama …) |
| Groq, Gemini, DeepSeek, Qwen | `GROQ_API_KEY`, `GEMINI_API_KEY`, … | mehrere Keys mit Komma = Rotation bei Limit |
| Mistral, NVIDIA NIM, Together, Perplexity | `MISTRAL_API_KEY`, `NVIDIA_API_KEY`, `TOGETHER_API_KEY`, `PERPLEXITY_API_KEY` | Perplexity-Modelle (`sonar`) suchen selbst im Netz |
| Hugging Face, Cloudflare Workers AI | `HF_TOKEN` bzw. `CF_ACCOUNT_ID` + `CF_API_TOKEN` | kleine Gratis-Kontingente |
| Ollama | – | lokale Modelle auf dem Pi |
| Claude (CLI, dein Abo) / ChatGPT (Codex-CLI, dein Abo) | – | fest eingebaut: `claude -p --tools "" --strict-mcp-config --no-session-persistence` (Claude ohne eigene Werkzeuge und ohne Konnektoren, nur Text; die Arbeitsanweisung ersetzt den Claude-Code-Systemprompt) bzw. `codex exec --skip-git-repo-check --ephemeral -` (Codex läuft von sich aus im Nur-Lesen-Sandkasten), Modell im Dropdown (Claude: sonnet/opus/haiku); braucht `PCL_ALLOW_CLI=1` und das angemeldete Programm auf dem Pi |
| CLI-Agent | – | Befehl, der den Prompt von stdin liest, z. B. `claude -p --model sonnet`; braucht `PCL_ALLOW_CLI=1` |

**Wichtig:** Ein Web-Login (OAuth, „Abo“) von ChatGPT oder Claude lässt sich nicht sauber als API nutzen, das Abgreifen von
Web-Sitzungen verstößt gegen die Nutzungsbedingungen. Wege: der **API-Key** des Anbieters (Abrechnung nach Verbrauch, nicht
das Chat-Abo) oder der **CLI-Agent** mit der offiziellen, einmalig angemeldeten CLI. Es gibt kein Budget in der App: bei
bezahlten APIs und vielen Werkzeug-Runden können Kosten entstehen, die Tokens siehst du pro Agent am Knoten.

## Sicherheit

- Login-Seite mit signiertem Cookie (7 Tage, `HttpOnly`, `SameSite=Strict`, `Secure` hinter HTTPS).
- Nach 5 falschen Passwörtern 10 Minuten Sperre pro IP, alle Versuche stehen im Audit-Log.
- Schreibende API-Aufrufe brauchen einen eigenen Header (CSRF-Schutz), dazu CSP und weitere Header.
- Shell und CLI-Agenten sind standardmäßig **aus**. Wer das Passwort kennt und `PCL_ALLOW_SHELL=1` gesetzt hat,
  kann Befehle mit den Rechten des App-Benutzers freigeben. `workspace/` ist das Arbeitsverzeichnis, aber **keine Sandbox**.
- `.env`, Datenbank und Arbeitsordner stehen in `.gitignore`. Keys gehören nie ins Repo.
- Bei Trading-Bots (NEXUS) Agenten nie ohne menschliche Freigabe handeln lassen.

## Firmenwissen und Gedächtnis

- **🧠 Firmenwissen** (Seitenleiste): Was alle Agenten eines Projekts immer wissen sollen (Firma, Kunden, Stil, Preise, Regeln). Steht in
  `wissen/firmenwissen.md` im Projektordner. Alle `.md`/`.txt` in `wissen/` gehen bei jedem Auftrag und im Chat mit (zusammen bis
  `PCL_KNOWLEDGE_CHARS`, Standard 8000 Zeichen); andere Unterlagen (PDF, Word …) dort sehen die Agenten als Liste und lesen sie bei Bedarf.
- **Gedächtnis je Agent**: Ein Agent kann sich am Ende eines Auftrags bis zu 5 dauerhafte Fakten merken (Vorlieben, Entscheidungen, Kunden,
  was funktioniert hat). Sie stehen im Agenten-Panel unter „🧠 Gedächtnis“, du kannst sie ändern oder leeren. Grenze `PCL_MEMORY_CHARS`
  (4000), die ältesten Einträge fallen zuerst heraus. Jede neue Notiz steht im Audit-Log.

## Ziele, Freigaben, Nutzung

- **🎯 Ziele**: Ziele und Unterziele je Projekt. Beim Zuweisen einer Aufgabe wählst du optional das Ziel, delegierte Aufgaben erben es.
  Chefs sehen die Ziele mit Fortschritt im Prompt, der CEO-Kontrollgang berichtet ihn. Abhaken = erreicht.
- **Vorher fragen** (Fenster ✋ Freigaben, je Projekt, Standard aus): *Plan des obersten Chefs freigeben* hält einen neuen Auftrag an,
  bis du den Verteilungsplan freigibst; *Teamänderungen freigeben* hält das Einstellen, Entlassen und Ändern von Mitarbeitern durch den CEO an. Freigeben/Ablehnen auch per
  Telegram-Knopf. Abgelehnt = der Auftrag landet als ❌ in der Post, deine Antwort darauf lässt den Chef neu planen.
  Shell-Freigaben gehen weiterhin nur im Web.
- **📊 Nutzung & Kosten**: Aufrufe, Tokens und geschätzte Kosten je Projekt, Agent und Modell (heute, 7, 30 Tage). Kein Limit.
  Abo-CLIs und Ollama zählen als 0 $; ab `PCL_ABO_WARN_5H` Abo-Aufrufen in 5 Stunden (Standard 150, 0 = aus) kommt eine Telegram-Warnung.
  Preise sind grobe Schätzungen, eigene per `PCL_PRICES='{"sonnet": 5}'` (US-$ je 1 Mio. Tokens, Teil des Modellnamens).

## Tests

```bash
./venv/bin/pip install pytest && ./venv/bin/python -m pytest -q tests
```
Läuft ohne Internet und ohne Keys (Anbieter `mock`, eigene Datenbank).

## 🔌 Verbindungen (Webhooks)

- **Ausgang:** Im Fenster 🔌 Verbindungen trägst du Adressen ein (n8n, Zapier, Make, eigener Dienst; auch `http://127.0.0.1:…` auf dem Pi),
  mit Beschreibung für die Agenten und optional Kopfzeilen. Geheimnisse gehören in `.env` und werden als `${NAME}` eingesetzt.
  Agenten mit dem Recht **„Darf Verbindungen nutzen“** rufen sie per Werkzeug `call_connection` auf; Adresse und Kopfzeilen kann der Agent
  nicht ändern, er schickt nur Daten. **„Nur nach meiner Freigabe“** (Standard an) legt jeden Aufruf erst unter ✋ Freigaben vor.
  **„Bei Post benachrichtigen“** schickt jedes fertige Ergebnis eines obersten Auftrags als JSON an die Adresse. Zeitlimit `PCL_CONN_TIMEOUT` (30 s).
- **Eingang:** „Aufträge von außen“ einschalten, dann nimmt `POST /hook/<projekt>/<schlüssel>` mit `{"text": "…", "agent": "optional"}`
  einen Auftrag an den Chef an (z. B. aus n8n, iOS-Kurzbefehlen oder DEXTER). Ohne Login, geschützt nur durch den Schlüssel in der Adresse:
  „Neuen Schlüssel“ macht die alte Adresse ungültig. Erreichbar ist sie nur so weit wie Hyperstead selbst (z. B. nur im Tailnet).

## ☁️ Cloud-Upload (GitHub, Google Drive, OneDrive, Telegram)

- **Einrichten:** Zugangsdaten in `.env` (`GITHUB_UPLOAD_TOKEN` + `GITHUB_UPLOAD_REPO`, `GDRIVE_CLIENT_ID` + `GDRIVE_CLIENT_SECRET`,
  `ONEDRIVE_CLIENT_ID`), Schritt für Schritt in [docs/cloud.md](docs/cloud.md). Bei Google und Microsoft meldest du dich danach im Fenster
  **☁️ Cloud** an: Es zeigt einen Code, den du am Handy auf der Seite von Google bzw. Microsoft eingibst (klappt ohne HTTPS).
  Die Anmeldung liegt in `tokens/` neben `.env`, nie in der Datenbank.
- **Zielordner:** je Projekt und Dienst im Fenster ☁️ Cloud (Standard `Hyperstead/<Projektname>`). Agenten dürfen nur einen
  Unterordner darunter wählen, z. B. wenn du ihn im Auftrag nennst.
- **Selbst hochladen:** 📁 Dateien → ☁️ neben der Datei → Ziel und Ordner wählen. Du bekommst den Link.
- **Agenten:** Recht **„Darf in die Cloud hochladen“** (setzt nur du). Werkzeug `cloud_upload`; jeder Upload wartet unter ✋ Freigaben,
  dazu kommt eine Telegram-Nachricht. Nach dem Upload steht der Link im Auftrag.
- **Einrichtung mit dem CEO:** Frag den obersten Chef im 💬 Chat, z. B. „Hilf mir, GitHub einzurichten“. Er kennt den aktuellen Stand jedes Dienstes und die Anleitung und führt dich Schritt für Schritt durch. Tokens schreibst du nie in den Chat, sondern selbst in `.env`.
- **Telegram:** `/datei` schickt dir Dateien bis 50 MB aufs Handy, nur wenn du es anklickst oder freigibst.
- GitHub: bis 50 MB als Datei im Repo, größere als Anhang an das Release `paperclip-ablage` (bis 2 GB). Google Drive: nur Ordner und
  Dateien, die Hyperstead selbst angelegt hat (Recht `drive.file`). OneDrive: jeder Ordner. Nur gegen simulierte Dienste getestet.

## 🖨 Abendberichte drucken

Der 👑 CEO-Kontrollgang schreibt bei Feierabend einen Abendbericht. In der 📬 Post und in den Aufgaben des CEO steht dabei **🖨 Drucken**: ein Klick, kurze Rückfrage, dann geht er an den Drucker. Drucker wählen unter **🖨 Drucker** in der Seitenleiste (Pi: Netzwerkdrucker über CUPS, `./install.sh --print`; Windows: freigegebener Drucker unter Drucker & Scanner). Im selben Fenster erlaubt oder sperrt der CEO das Drucken (Recht „Darf Abendberichte drucken“). Der **Testdrucker (Datei)** speichert den Ausdruck nur als Textdatei in `workspace/.druck/`. Anleitung: [docs/drucken.md](docs/drucken.md).

## 🌐 Echter Browser und ▶ Code ausführen

- **Browser** (`./install.sh --browser`, installiert Playwright + Chromium, ca. 400 MB, nur 64-Bit-System): Agenten mit dem Recht
  „Internet recherchieren“ bekommen `browse_page`. Die Seite läuft mit JavaScript, der Agent bekommt den sichtbaren Text, die Links und
  auf Wunsch einen Screenshot (sieht ihn wie bei `view_image`, `save` legt ihn in `assets/screenshots/` ab). Jede Anfrage der Seite
  (Skripte, Frames, XHR, WebSockets) muss an eine öffentliche Adresse gehen, LAN/localhost wird blockiert, WebRTC und Downloads sind aus.
  Immer nur ein Browser gleichzeitig (RAM), Zeitlimit `PCL_BROWSER_TIMEOUT` (30 s). Eigenes Chromium: `PCL_BROWSER_PATH`, aus: `PCL_BROWSER=0`.
- **Code ausführen** (`./install.sh --run`, installiert bubblewrap): Recht „Darf Code ausführen“ (Standard aus) gibt `run_code`.
  Das Skript läuft abgeschottet: **kein Internet**, nur `/usr` und der Projektordner (schreibgeschützt unter `/projekt`) sichtbar,
  keine `.env`, keine Datenbank, kein Home. Was das Skript in sein Arbeitsverzeichnis schreibt, landet in `output/run/<zeit>/`
  (max. 50 Dateien/50 MB). Grenzen: `PCL_RUN_TIMEOUT` (60 s), `PCL_RUN_MEM_MB` (1024). Es läuft das Python/Node des Systems,
  also nur Pakete, die per apt installiert sind (z. B. `sudo apt install python3-pandas python3-matplotlib`). Global aus: `PCL_ALLOW_RUN=0`.
  Prüfen: `./venv/bin/python selftest.py run browser`.

## 🦀 Rust-Programme komplett bauen

Gib einem Agenten mit den Rechten **„Darf programmieren“**, **„Darf Dateien schreiben“** und **„Darf Code ausführen“** einen Auftrag
wie „Schreib mir ein Rust-Programm, das …, mit Tests, und liefere das fertige Paket“. Der Agent arbeitet dann von A bis Z:

1. Er legt mit `write_code` ein Cargo-Projekt an, z. B. `rust/rechner/Cargo.toml` und `rust/rechner/src/main.rs` mit Tests (`#[test]`).
2. `rust_project` mit `op=test` lädt die Abhängigkeiten aus crates.io, baut das Programm und lässt die Tests laufen.
   Fehler kommen mit Datei und Zeile zurück, der Agent korrigiert und testet erneut.
3. `op=package` testet noch einmal, baut die Release-Fassung und legt **`output/<name>.zip`** ab. Darin: `programm/` (das fertige
   Programm), `quelle/` (Quelltext mit `Cargo.lock`), `TESTBERICHT.txt` und `LIESMICH.txt`. Ein Paket entsteht nur, wenn alle Tests bestehen.

Du bekommst das Paket in der Post bzw. unter **📁 Dateien** (einzeln oder im Projekt-ZIP). Weitere Befehle: `op=build`, `op=run` (mit `args`, `stdin`).

- **Für welches System?** Das Programm in `programm/` passt zu dem Rechner, auf dem Hyperstead läuft: vom Pi ein Linux-Programm (ARM),
  vom Windows-Laptop eine `.exe`. Für ein anderes System im Ordner `quelle/` selbst `cargo build --release` ausführen.
- **Abschottung (Pi/Linux):** Bauen, Testen und Ausführen laufen in bubblewrap wie `run_code`: kein Internet, keine `.env`, kein Home,
  nur der Bauordner `.rust/` des Projekts ist beschreibbar. Nur `cargo fetch` (lädt Abhängigkeiten, führt nichts aus) hat Internet.
  Eigene Cargo-Einstellungen (`.cargo/`) und `rust-toolchain`-Dateien aus dem Projekt werden nicht übernommen.
- **Windows:** Ohne bubblewrap bleibt das Werkzeug aus. Mit `PCL_CARGO_UNSAFE=1` in `.env` baut der Laptop **ohne Abschottung**: Der Code der
  Agenten (Tests, `build.rs`) läuft dann mit deinen Rechten und könnte Dateien auf dem Laptop lesen oder ändern. API-Keys bekommt er nicht
  in die Umgebung. Nur einschalten, wenn du den Agenten und ihren Modellen vertraust.
- **Rust installieren:** Pi `curl https://sh.rustup.rs -sSf | sh` (aktueller als `apt install cargo`), Windows `winget install Rustlang.Rustup`
  und im Installer die „Visual Studio Build Tools (C++)“ mitnehmen. Danach Hyperstead neu starten und `selftest.py rust` ausführen.
- **Grenzen:** `PCL_CARGO_TIMEOUT` (900 s je Schritt), `PCL_CARGO_MEM_MB` (3072, nur Linux), `PCL_CARGO_JOBS` (2), immer nur ein Rust-Bau
  gleichzeitig. Der erste Bau auf dem Pi dauert lange, danach baut cargo nur Geändertes neu. Ein Agent hat `PCL_MAX_TOOL_STEPS`
  (Standard 6) Werkzeug-Runden je Lauf; für größere Programme hilft ein höherer Wert, z. B. 12. Aus: `PCL_CARGO=0`.

## 🛠 Werkstatt: Agenten rüsten selbst nach

Mit dem Recht **„Werkstatt“** arbeitet ein Agent wie an einem echten Rechner, für jede KI und in jeder Firma. Claude (Abo-CLI) bekommt
seine Claude-Code-Werkzeuge im Projektordner, Codex seine eigenen, alle API-KIs und Ollama das Werkzeug `befehl`. Fehlt ein Programm,
stellt der Agent einen **Nachrüst-Antrag**: Der CEO prüft ihn, du bestätigst per Telegram-Knopf oder unter ✋ Freigaben, danach
installiert der Server genau diesen Befehl und die Aufgabe geht weiter. Was installiert ist, steht in `wissen/werkzeuge.md`.

- **Einschalten:** `PCL_ALLOW_WERKSTATT=1` in `.env`, neu starten, beim Agenten das Häkchen setzen und eine Stufe wählen.
- **Stufen:** 1 = jeder Befehl fragt, 2 = Arbeit im Projekt frei, Installationen und Löschen fragen (Standard), 3 = alles frei
  (nur mit `PCL_WERKSTATT_FREI=1`). Zugangsdaten (`.env`, Tokens, Keys) sind immer gesperrt.
- **Achtung:** Befehle laufen ohne Abschottung mit deinen Benutzerrechten. Stufe 2 erkennt Installationen an ihrer Form, sie ist keine Sandbox.
- Alles Weitere, auch Remotion und Probleme: [docs/werkstatt.md](docs/werkstatt.md).

## Parallele Arbeit

Bis zu `PCL_WORKERS` Aufgaben laufen gleichzeitig (Standard 2, höchstens 6), z. B. mehrere Mitarbeiter eines Chefs oder Aufträge
verschiedener Projekte. Ein Agent bearbeitet nie zwei Aufgaben auf einmal, und es läuft höchstens eine Ollama-Aufgabe gleichzeitig
(RAM auf dem Pi). Bei Abo-CLIs (Claude, Codex) zählen parallele Aufrufe schneller gegen das Abo-Limit; dann `PCL_WORKERS=1` setzen.

## Grenzen dieser Version

- Kein automatischer Heartbeat nach Zeitplan (Aufgaben starten manuell oder per Delegation).
- Keine Text-zu-Video-KI, keine Scan-/Bild-PDFs (OCR), keine eigene Anstellung neuer Agenten durch den CEO (Organigramm legst du an).
- Der echte Browser (`browse_page`) liest Seiten, klickt aber nicht und füllt keine Formulare aus (keine Logins, keine Käufe). Die DuckDuckGo-Suche ohne Key kann begrenzt oder geändert werden.
- Kein Budget: Tokens und geschätzte Kosten werden nur angezeigt (📊). Die Rundenlimits (Überarbeitungen, Prüfdurchgänge, Tiefe) verhindern Endlosschleifen.
- Sitzungen sind einfache signierte Cookies, ein einzelnes Gerät lässt sich nicht gezielt abmelden
  (Passwort ändern macht alle Sitzungen ungültig).


## Selbsttest

Nach Installation und Eintragen der Keys prüft `./venv/bin/python selftest.py` alles Echte, was sich ohne Internet nicht testen ließ:
Websuche, Seiten lesen, Bildsuche und Bildgenerator, SSRF-Schutz, jeder KI-Anbieter mit Mini-Anfrage (inkl. Ollama), Telegram
(Bot-Token und Testnachricht an deine Chat-ID), ffmpeg, Sprachausgabe, PDF mit Umlauten, OCR. Einzelne Gruppen:
`selftest.py web | llm | telegram | media | ocr | rust | film`. Jede Zeile zeigt OK, FEHLT (optional) oder FEHLER mit konkretem Hinweis.

## Ollama (lokale Modelle)

Anbieter „Ollama (lokal)“: kein Key nötig, die Modellliste kommt direkt von Ollama (`ollama pull qwen2.5:1.5b`). Im Dialog „Firma aus Vorlage“
gibt es die Knöpfe „Alles lokal“ und „Nur Mitarbeiter lokal“; sonst wählst du Ollama je Agent. Läuft Ollama auf einem anderen Rechner
(z. B. dem Laptop), setze `OLLAMA_URL` auf dessen Adresse. Kleine Modelle (3B) sind auf dem Pi langsam und halten das Werkzeug-Protokoll
oft schlecht ein; für Chefs ein starkes Modell, lokal eher für einfache Mitarbeiter oder den Chat.

**Lange Antworten (Pi):** Hyperstead fragt Ollama mit Streaming. Solange das Modell schreibt, bricht nichts ab, auch wenn die Antwort eine Stunde dauert.
`OLLAMA_TIMEOUT` (Standard 1800 s) ist nur die Wartezeit **ohne neue Daten**, z. B. während Ollama das Modell lädt und den Auftrag liest;
`OLLAMA_MAX_TIME` (Standard 7200 s, 0 = ohne Grenze) begrenzt die Gesamtzeit. Eine abgebrochene Ollama-Anfrage wird nicht wiederholt.
Im Dashboard steht unten links „⏳ Agent · Ollama · 4:12 min · 380 Zeichen“, solange eine KI schreibt. Der Chat wartet im Hintergrund,
du kannst das Fenster schließen; die Antwort steht danach im Verlauf.

**Wenig RAM (≈ 2 GB frei):** `qwen2.5:3b` braucht mit Kontext etwa 2,5 GB und passt dann nicht. Gut passt `qwen2.5:1.5b`
(Download ≈ 1 GB, im RAM ≈ 1,3–1,6 GB, versteht Deutsch, Türkisch und Englisch); noch kleiner `gemma3:1b` (≈ 0,8 GB Download, ≈ 1,1 GB RAM).
Für Ollama selbst (`sudo systemctl edit ollama`): `Environment="OLLAMA_CONTEXT_LENGTH=4096"`, `"OLLAMA_NUM_PARALLEL=1"`, `"OLLAMA_MAX_LOADED_MODELS=1"`.
Rechne auf einem Pi 4 mit wenigen Wörtern pro Sekunde und mehreren Minuten, bis das erste Wort kommt (lange Systemprompts).

## Claude und ChatGPT über dein Abo (CLI statt API-Key)

In `.env`: `PCL_ALLOW_CLI=1`. Die Programme installierst und meldest du einmal selbst auf dem Pi an (Anleitungen der Hersteller:
Claude Code `claude`, OpenAI Codex `codex`; Anmeldung mit deinem Abo). Danach erscheinen „Claude (CLI, dein Abo)“ und „ChatGPT (Codex-CLI, dein Abo)“
in allen Anbieter-Listen. Der Server ruft sie ohne Shell auf, in einem leeren Ordner und **ohne unsere API-Keys in der Umgebung**
(sonst würde `claude` den API-Key statt des Abos abrechnen). Grenzen: langsamer als die API (Programmstart je Antwort), Abo-Limits gelten
(viele Agenten = schnell am Limit), und die CLI-Programme haben eigene Werkzeuge – Befehl bei Bedarf über `PCL_CLI_CLAUDE` / `PCL_CLI_CODEX` anpassen.

## Modell weg? Agenten umstellen
Hyperstead prüft alle 6 Stunden (`PCL_MODEL_CHECK_HOURS`), ob die Modelle der Agenten beim Anbieter noch existieren, und merkt es auch, wenn ein Aufruf „Modell nicht gefunden“ meldet. Dann kommt eine Telegram-Nachricht, die Aufgabe scheitert mit klarem Hinweis, und im Menü **⚠ Modelle** stellst du alle betroffenen Agenten mit einem Klick auf ein anderes Modell um.

## Große Teams
Ein Vorgesetzter kann beliebig viele Mitarbeiter haben. Im Panel des Vorgesetzten (Einstellungen) wählst du unter **Unterstellte Mitarbeiter** per Häkchen alle aus und speicherst die Zuweisung. Alternativ: unteren Punkt des Vorgesetzten auf einen Mitarbeiter ziehen. Der Knopf **🗂 Ordnen** legt alles als Organigramm an (Gruppen ab 6 Mitarbeitern in Reihen zu je 5).

## CEO stellt sein Team selbst zusammen
Der CEO aus der Palette hat das Recht **„Darf sein Team selbst zusammenstellen“** (`recruit`). Hat er noch keine Mitarbeiter und bekommt einen Auftrag, analysiert er ihn und legt Mitarbeiter mit Rolle, Arbeitsanweisung und Berichtslinien an (bis 20, auch Abteilungsleiter mit eigenem Team). Die Neuen haben **noch keine KI**: Du weist sie im Menü **⚠ Modelle** (alle auf einmal) oder je Agent in den Einstellungen zu und antwortest dann in der **Post** auf den Auftrag (z. B. „Weiter“). Danach verteilt der CEO die Arbeit wie gewohnt. Der CEO kann Neuen nur Web, Bilder, Dateien lesen/schreiben, Medien und Programmieren mitgeben, nie Shell.

**Auch wenn das Team schon steht**, darf ein CEO mit diesem Recht sein Team bei jedem Auftrag an deine Aufgaben und Vorgaben anpassen:
- **Einstellen**: weitere Mitarbeiter, wie oben ohne KI. Du bekommst eine Telegram-Nachricht und weist ihnen die KI zu. Arbeit bekommen sie erst ab dem nächsten Auftrag bzw. nach deinem „Weiter“.
- **Entlassen**: nur Mitarbeiter unter ihm, nie sich selbst oder Agenten außerhalb seines Teams. Die Leute des Entlassenen rücken eine Ebene hoch. Wer noch eine offene Aufgabe hat, wird nicht entlassen.
- **Ändern**: Rolle, Arbeitsanweisung und Rechte (nur die oben genannten) von Mitarbeitern unter ihm.

**Rechte passend zur Rolle**: Der CEO soll jedem genau die Rechte geben, die seine Arbeit braucht. Vergisst er welche, ergänzt das System sie anhand von Name, Rolle und Arbeitsanweisung, z. B. Recherche → *Web*, Bilder/Illustration/Grafik/Design → *Bilder* + *Dateien schreiben*, Video/Ton/Stimme/PDF/Layout → *Medien* + *Dateien schreiben*, Autor/Text/Lektorat → *Dateien schreiben*, Programmierung/Webseite → *Programmieren* + *Dateien schreiben*. Ändert er die Rolle eines Mitarbeiters, werden die Rechte neu passend gesetzt. Shell, Code ausführen, Verbindungen und Veröffentlichen gibt er nie, die hakst nur du an.

Willst du jede Teamänderung vorher sehen, hake im Fenster **Freigaben** *Teamänderungen freigeben* an. Ohne das Häkchen beim CEO darf er nichts davon. Tägliche Aufgaben (Zeitplan, Kontrollgang) ändern das Team nie.

## Öffnungszeiten und tägliche Aufgaben
Seitenleiste **🕘 Zeitplan**: Pro Projekt Arbeitsbeginn, Feierabend und Arbeitstage festlegen. Je Mitarbeiter lassen sich **tägliche Aufgaben** anlegen (feste Uhrzeit, bei Arbeitsbeginn oder bei Feierabend, an wählbaren Wochentagen), z. B. „jeden Tag um 15:00 die Website kontrollieren“. Das Ergebnis kommt wie jede Post in die Ansicht „Post“ (und per Telegram). Läuft die letzte Aufgabe eines Zeitplans noch, wird nicht doppelt gestartet; war der Pi zur Uhrzeit aus, wird bis zu 6 Stunden nachgeholt.
Bei Arbeitsbeginn nimmt die Firma liegengebliebene Aufgaben wieder auf (nicht gestartete starten, gescheiterte oberste Aufgaben bis zu `PCL_MAX_RESUMES`=2 mal erneut). Optional ruht die Firma außerhalb der Öffnungszeiten ganz. Die Uhrzeit ist die des Pi; stimmt sie nicht, `PCL_TZ=Europe/Vienna` in `.env` setzen.

## CEO-Kontrollgang
Im Fenster **🕘 Zeitplan** richtet **👑 CEO-Kontrollgang** einen täglichen Kontrollgang des obersten Chefs ein (Standard: bei Feierabend; weitere Zeiten über „Neue tägliche Aufgabe“ + Häkchen *Kontrollgang*). Das System legt ihm einen **Statusbericht** mit Fakten bei: je Mitarbeiter heute gestartet/fertig/fehlgeschlagen/offen, Arbeitsstarts außerhalb der Öffnungszeiten, offene Aufgaben ohne Arbeitsbeginn, Mitarbeiter ohne KI, liegengebliebene Aufträge und ob die täglichen Aufgaben gelaufen sind. Der CEO bewertet das, verteilt bei Bedarf Folgeaufgaben an sein Team und schreibt einen Kontrollbericht in die Post. „📋 Statusbericht ansehen“ zeigt die Fakten ohne CEO.

## Projektordner
Jedes Projekt hat einen **Ordner mit seinem Namen** unter `workspace/` (z. B. `workspace/Buchverlag-Content-Agentur/`, Umlaute werden umschrieben). Er bleibt beim Umbenennen des Projekts gleich und wird beim **Löschen eines Projekts nie gelöscht**. Legst du ein Projekt mit gleichem Namen neu an, übernimmt es den vorhandenen Ordner samt Dateien. Alte Nummernordner (`workspace/1`, `workspace/2` …) werden beim Start automatisch auf den Projektnamen umbenannt.

## Webseite veröffentlichen
Im Fenster **📁 Dateien dieses Projekts** gibt es **🚀 Veröffentlichen**: Veröffentlicht wird **nur der Ordner `www/` im Projektordner** (`www/index.html`, dazu CSS, Bilder … mit relativen Pfaden); alles andere im Projekt (Notizen, `output/`, `input/`, Dotfiles, Symlinks nach außen) bleibt unsichtbar. Gibt es keinen `www/`-Ordner, wird wie bisher die `index.html` des Projektordners (ohne `input/` und versteckte Dateien) ausgeliefert. Die Seite läuft dauerhaft auf einem eigenen Port (ab 8800, `PCL_SITE_PORT_BASE`) ausgeliefert, standardmäßig nur auf dem Pi selbst: `http://127.0.0.1:8800/`. Für Zugriff im Netz `PCL_SITE_HOST=0.0.0.0` in `.env`. Agenten mit dem Recht „Darf die Webseite zur Veröffentlichung vorschlagen“ können auf „veröffentlichen“ eine Freigabe anfordern; erst dein Klick unter **Freigaben** schaltet die Seite online. Änderungen der Agenten sind sofort sichtbar, nach einem Neustart läuft die Seite automatisch wieder. Für das offene Internet gehört ein Reverse-Proxy mit HTTPS davor (z. B. Caddy), nicht der Mini-Server.
