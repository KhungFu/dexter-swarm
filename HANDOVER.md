# Hyperstead – Übergabe an einen anderen Claude-Chat

Dieses Dokument fasst Projekt, Stand und Entscheidungen zusammen, damit du ohne den ursprünglichen Chat weiterarbeiten kannst.
Dazu gehört der Quellcode (`hyperstead-quellcode.zip`, nur versionierte Dateien, keine Zugangsdaten).
Sprache der Oberfläche, Doku und der Zusammenarbeit mit dem Besitzer: **Deutsch**, knapp und praktisch.

## Worum geht es
Hyperstead ist ein selbst gehosteter Knoten-Editor für ein **Team aus KI-Agenten** (früher PaperclipLite). Der Besitzer baut Firmen
als Organigramm (CEO → Abteilungsleiter → Mitarbeiter), gibt dem CEO Aufträge, das Team arbeitet, der Chef prüft und gibt ggf. zurück,
das Ergebnis landet in der „Post“ (Web + Telegram). Läuft auf einem **Raspberry Pi 4 (4 GB RAM, Hostname `dexter`)**, Flask + SQLite,
mehrere Worker-Threads (`PCL_WORKERS`, Standard 2), Oberfläche als eine HTML-Datei (Vanilla JS). Repo: `KhungFu/hyperstead-neu` (früher `KhungFu/paperclip-lite`, privat, Branch `main`).

## Dateien
| Datei | Inhalt |
|---|---|
| `app.py` (~2500 Zeilen) | Gesamtes Backend: .env, DB, LLM-Anbieter (`call_llm`), Prompt-Bau, `execute_task`, Worker, Login, REST-API, Telegram |
| `static/index.html` | Gesamte Oberfläche (Knoten, Panels, Overlays), alle Texte deutsch |
| `agent_tools.py` | Werkzeuge der Agenten: Suche, Webseiten, Bilder, Dateien, ffmpeg, TTS, PDF/DOCX/EPUB, OCR; SSRF-Schutz |
| `company_templates.py` | Firmenvorlagen (reine Daten) |
| `selftest.py` | Prüft auf dem Pi alle externen Dienste (Suche, Bilder, LLMs, Telegram, Medien, OCR) |
| `install.sh`, `deploy/` | Installer, systemd-Dienst (`--service`, `--piper`) |
| `CLAUDE.md` | Technische Projektnotizen (zuerst lesen), `README.md` Bedienung |

## Was es kann (Stand)
- Knoten-Editor mit Drag & Drop, Pan/Zoom, beliebig viele Mitarbeiter je Vorgesetztem (Mehrfachauswahl im Panel, Knopf „Ordnen“).
- Pro Agent: Anbieter, Modell, Arbeitsanweisung, **Rechte** (delegate, judge, auto_run, write_files, shell, web, images, read_files, media, recruit). Rechte werden **serverseitig** geprüft, nie dem Modell vertraut.
- Unternehmens-Workflow: Modi `work` / `plan` / `review`; Rückgaben (max. 2 je Kind), Prüfrunden (max. 4), Tiefe max. 8.
- Anbieter: OpenAI-kompatibel (Groq, Gemini, DeepSeek, Qwen, OpenAI, OpenRouter, Ollama), nativ Anthropic, `mock` (Tests ohne Key), generischer `cli` sowie feste CLI-Anbieter `claude_cli` (Claude-Abo) und `codex_cli` (ChatGPT-Abo).
- **Echter Browser** (`browse_page`, JavaScript + Screenshot, LAN blockiert) und **Code ausführen** (`run_code`, bubblewrap ohne Netz, Zeit/RAM-Limit).
- Werkzeuge: Websuche, Seiten lesen, Bilder suchen/erzeugen, Dateien lesen/schreiben, Video (ffmpeg ohne Shell), Sprache (Piper/espeak), Dokumente, OCR für gescannte PDFs.
- Post/Telegram: Ergebnisse oberster Aufgaben, Antworten = Überarbeitung; nur die erlaubte Chat-ID darf steuern.
- Chat mit einzelnen Agenten, Uploads in `input/`, Firmenvorlagen inkl. „alles lokal (Ollama)“.
- **Modell-Überwachung:** Prüfung gegen die Live-Modellliste (alle 6 h), Telegram-Warnung, Menü „⚠ Modelle“ zum Sammel-Umstellen.
- **CEO stellt Team selbst ein** (Recht `recruit`): legt Mitarbeiter ohne KI an, Besitzer weist KI/Modell zu, dann „Weiter“ in der Post.
- **Öffnungszeiten + tägliche Aufgaben** je Mitarbeiter (feste Uhrzeit / bei Arbeitsbeginn / bei Feierabend), Wiederaufnahme liegengebliebener Aufgaben bei Arbeitsbeginn.
- **CEO-Kontrollgang:** systemerzeugter Statusbericht (fertig/offen, Öffnungszeiten eingehalten, wer hat gearbeitet) als tägliche CEO-Aufgabe.

## Regeln, die der Besitzer wichtig findet
- Keys nur in `.env`, nie ins Repo, nie im Chat. Shell/CLI sind global per Umgebungsvariable gesperrt (`PCL_ALLOW_SHELL`, `PCL_ALLOW_CLI`).
- Schreibende API-Aufrufe brauchen Header `X-PCL: 1`. Audit-Log ist append-only. Kein `tailscale funnel`; bei Zugriff von außen `APP_TOKEN` mit mindestens 12 Zeichen.
- **Bestehendes nicht verändern**, wenn neue Funktionen ergänzt werden („bloß nichts ändern an dem anderen“): neue Dinge standardmäßig aus bzw. additiv.
- Anbindung an `swarm.py` (sein Telegram-Bot „DEXTER“) kommt **zuletzt** (z. B. über `webhook`/`cli`).
- Am Ende jeder Arbeit: Tests laufen lassen, committen, pushen, keine unversionierten Dateien liegen lassen; dem Besitzer den `git pull`-Befehl für den Pi geben.

## Getestet / nicht getestet
- Backend und UI laufen gegen simulierte Antworten (`mock`, Fake-Server, Flask-`test_client`, Playwright). In der Entwicklungsumgebung gab es **kein Internet**.
- Auf dem Pi bestätigt: Suche, Seitenabruf, Bildsuche, SSRF-Sperre, Ollama (`qwen2.5:1.5b` antwortet, ist für das JSON-Werkzeugprotokoll aber zu schwach), Claude-CLI und Codex-CLI, Piper, ffmpeg, PDF, OCR.
- Offen: echte Provider-Keys (Groq, Gemini …) noch nicht eingetragen; Telegram noch nicht eingerichtet; Zeitpläne/Kontrollgang/Recruit noch nicht mit echten Modellen erprobt.
- Bekannte Grenzen: Codex im Read-only-Modus kann Dateien lesen (nicht für Web-verarbeitende Agenten nutzen); 4 GB RAM sind mit Ollama plus Claude Code knapp; Abo-CLIs sind langsamer und haben Kontingente.

## Roadmap (Reihenfolge des Besitzers)
1. Betrieb stabilisieren: echte Keys testen (`selftest.py`), Tunnel (Tailscale Serve), systemd-Dienst.
2. pytest-Tests anlegen (Zyklussperre, Workflow, Überarbeitungslimit, Pfadschutz, Login-Sperre, Zeitpläne).
3. **Zuletzt:** swarm.py/DEXTER als Agent anbinden.

## Starten
```bash
./install.sh && ./venv/bin/python app.py          # http://127.0.0.1:8787
./install.sh --service                             # als systemd-Dienst
./venv/bin/python selftest.py                      # externe Dienste prüfen
```

## Startprompt für den neuen Chat
> Lies HANDOVER.md und CLAUDE.md und verschaffe dir mit app.py einen Überblick. Wir entwickeln Hyperstead weiter.
> Antworte auf Deutsch, ändere Bestehendes nicht ohne Not und sag mir vor größeren Umbauten kurz, was du vorhast. Mein Ziel für heute: …
