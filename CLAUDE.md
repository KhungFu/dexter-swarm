# Hyperstead – Projektnotizen für die Weiterarbeit

Selbst gehosteter Knoten-Editor für ein Team aus KI-Agenten (früher PaperclipLite), läuft auf einem Raspberry Pi 4
(Hostname `dexter`).

## Sprache (Wunsch ABI 2026-11-05)
- ALLES, was Hyperstead selbst schreibt, ist Englisch: Oberflaeche (auch title/aria/Platzhalter/confirm), Server- und Werkzeugmeldungen (`ERROR:`/`NOTE:`/`WARNING:`),
  Agenten-Prompts, Firmenvorlagen, Telegram-Texte, Selbsttest, Druck-/Rust-Dateinamen (`print-*.txt`, `README.txt`, `TEST_REPORT.txt`, `source/`, `program/`).
  Was der Besitzer eintraegt, bleibt in seiner Sprache. Deutsch bleiben nur Code-Kommentare, `docs/`, Bezeichner, die Agenten/Daten schon nutzen
  (Werkstatt-Werkzeuge `befehl`/`nachruesten` mit `wozu`/`groesse`, film.json-Schluessel, `wissen/`, Audit-Ereignisse, interne Werte wie `antrag`/`besitzer`).
- Kommunikationssprache: `note_owner_text` (Chat, Auftrag, Rework, neue Post, Telegram) merkt `settings owner_text` und leert `owner_lang`;
  `language_line()` in `build_system` verlangt Antworten/Berichte/Dateien in der Sprache des Besitzers (mit seinen letzten Worten).
- `tr(text)`: feste Meldungen (Telegram `tg_send_now`/`tg_notify` mit `translate=True`, Buttons, Kopf/Fuss in `tg_notify_post`, Systemnotizen im Postkorb)
  uebersetzt die KI von `translator_agent()` (CEO des aktiven Projekts, sonst erster Agent mit echtem Anbieter). `owner_lang()` erkennt die Sprache per KI,
  Cache `_tr_cache`. Ohne KI, bei Englisch oder `PCL_TRANSLATE=0` unveraendert. Tests setzen `PCL_TRANSLATE=0` (conftest), Test `tests/test_sprache.py`.
- Alte deutsche Marker werden weiter erkannt (`REPORT_HEADS`, CEO-JSON `weiterleiten`/`empfehlung`, Telegram /neu /projekt /datei /hilfe, `OK_WORDS`).
- Grafik-Menue „Classic“ ohne Symbole (Wunsch ABI): „Org chart: Tree/Outline/Circle“, „Blueprint“.

## Aufbau
- `app.py`: komplettes Backend (Flask + SQLite, `PCL_WORKERS` Worker-Threads). Abschnitte: Konfiguration/.env, Datenbank,
  LLM-Anbieter (`call_llm`, alle über OpenAI-kompatibles Format), Prompt-Bau, `execute_task`, Worker, Login/Sitzung, REST-API.
- `static/index.html`: komplette Oberfläche in einer Datei (Vanilla JS, SVG-Kanten, Pan/Zoom, Drag & Drop).
- `agent_tools.py`: Werkzeuge der Agenten (Suche, Seiten, Bilder, Dateien), eigenständig, mit SSRF-Schutz (`check_public`, `safe_get`).
- `company_templates.py`: Firmenvorlagen (reine Daten).
- `deploy/` + `install.sh`: systemd-Dienst und Installer. `README.md`: Bedienung, Internetzugriff, Sicherheit.

## Wichtige Regeln im Code
- Rechte der Agenten werden **serverseitig** in `execute_task` geprüft, nie dem Modell vertrauen.
- Shell/CLI sind per Umgebungsvariable global gesperrt (`PCL_ALLOW_SHELL`, `PCL_ALLOW_CLI`).
- Schreibende `/api/`-Aufrufe brauchen den Header `X-PCL: 1` (CSRF), das Frontend sendet ihn in `api()`.
- Keys nur in `.env`, nie ins Repo. Audit-Log ist append-only (nur Insert).
- Anbieter `mock` liefert Testantworten ohne Key und delegiert an Mitarbeiter, praktisch für Tests.

## Unternehmens-Workflow (`execute_task`)
- Modi: `work` (Blatt), `plan` (Chef delegiert), `review` (Chef nach Abschluss aller Kinder: liest Berichte, kann per `review`
  zurückgeben, weiter delegieren oder abschließen). Status `waiting_subtasks`; `finish`/`wake_parent` wecken den Chef.
- Limits: `MAX_REVISIONS` 2 je Kind, `MAX_REVIEW_PASSES` 4 (danach `final_only`), `PCL_MAX_DEPTH` 8. Kein Budget.
- Rechte: delegate, judge, auto_run, write_files, shell, recruit.
- Modus `recruit`: Agent mit Recht `recruit`, ohne Mitarbeiter, oberste Aufgabe → `recruit_team` legt Agenten mit `provider=''` an (Rechte nur aus `RECRUIT_PERMS`, max. `RECRUIT_MAX`). Plan-Modus bricht ab, solange Kinder ohne KI existieren. Teamumbau bei bestehendem Team: in plan/review (nicht `final_only`, nicht geplant) darf ein Agent mit `recruit` `recruit`/`dismiss`/`change` liefern → `change_team` (nur `descendants`, Entlassene per `delete_agent` mit Hochruecken, nicht bei offenen Aufgaben; `change` setzt nur `RECRUIT_PERMS`). `tools_for_role` (Stichwoerter `ROLE_TOOLS`) ergaenzt Rechte anhand Name/Rolle/Anweisung, beim Einstellen und bei geaenderter Rolle. Schranke `recruit` gilt auch dafuer (approval-`data` ist dann ein Dict). Zuweisung über `/api/models/replace` (provider `''`, optional `project_id`), `model_health` meldet sie als `unassigned`.
- Zeitplan: Tabelle `schedules` (`at` = HH:MM | `open` | `close`, `days` Mo=0), Öffnungszeiten in `settings` (`hours:<pid>`). `schedule_tick` (Worker, alle 20 s) startet fällige Zeitpläne (`tasks.schedule_id`, Nachholfenster 6 h, kein Doppelstart) und nimmt bei Arbeitsbeginn liegengebliebene Aufgaben wieder auf (`resume_open_tasks`, `tasks.resumed` ≤ `PCL_MAX_RESUMES`). `gate_all` hält Queue außerhalb der Öffnungszeiten an. API: `/api/projects/<id>/hours|schedules`, `/api/schedules/<id>[/run]`. Zeitzone `PCL_TZ`. Kontrollgang: `schedules.kind='inspect'` → `fire_schedule` hängt `inspection_report(pid)` (Fakten aus tasks/audit/schedules) + `INSPECT_TASK` an die Beschreibung; `/api/projects/<id>/report`. Geplante Aufgaben lösen nie den Modus `recruit` aus.
- Projektordner: `projects.folder` (Slug des Namens), `proj_dir(pid)` überall statt `WORKSPACE/<id>`; `assign_folder` bei Neuanlage, `migrate_folders` benennt alte Nummernordner um. Löschen eines Projekts lässt den Ordner stehen, ein gleichnamiges neues Projekt übernimmt ihn.
- Veröffentlichen: `site_start/site_stop` starten je Projekt einen `ThreadingHTTPServer` (`PCL_SITE_HOST`, Ports ab `PCL_SITE_PORT_BASE`), liefert `site_root(pid)` = `www/` im Projektordner (existiert er nicht: Rückfall auf den Projektordner ohne `input/`), nie Dotfiles/Symlinks nach außen; Einstellung `site:<pid>`, Start in `start_sites()`. Recht `publish` → Aktion `publish` erzeugt Freigabe (`approvals.kind='publish'`), Klick startet die Seite. API `/api/projects/<id>/site`.

- Ollama (`_call_ollama`/`_ollama_stream`): immer Streaming (OpenAI-SSE), `OLLAMA_TIMEOUT` = Wartezeit ohne neue Daten (1800), `OLLAMA_MAX_TIME`
  = Gesamtzeit (7200, 0 = aus), keine Wiederholung. `call_llm` traegt jede laufende Anfrage in `LLM_LIVE` ein (`live_list`, im Graph als `live`,
  Dashboard `#livebar`). Chat mit echten Modellen laeuft als Hintergrund-Job (`CHAT_JOBS`, `GET /api/agents/<id>/chat/job`), mock antwortet sofort.

## Werkzeuge der Agenten
- `run_with_tools` (app.py): Modell antwortet mit `{"tools":[...]}` → Server führt `agent_tools.run_tool` aus → nächste Runde, max. `MAX_TOOL_STEPS`, danach erzwungene Endantwort. Ältere Ergebnisse werden gekürzt (kleine Kontextfenster).
- `copy_files` (Recht `write_files`): kopiert/verschiebt Datei oder Ordner im Projektordner (z. B. `site/`→`www/`), nie nach `input/`/Dotordner, Limits 500 Dateien/100 MB. Das Teamlisting im Prompt (`build_system`) nennt die Rechte jedes Mitarbeiters; `publish` per Agent verlangt `www/index.html`. CLI-Anbieter haben keine eigenen Werkzeuge (Arbeitsordner `workspace/.cli-run/`), Dateien entstehen über die Server-Werkzeuge.
- Programmieren (Recht `code`, Standard aus): `write_code` schreibt Quelltext jeder Sprache (nicht `input/`/Dotdateien, max. 500 KB), `check_code` prüft ohne Ausführung: Python per `compile()`, JSON intern, sonst `CODE_CHECKERS` (node --check, rustc --emit=metadata, javac -proc:none, gcc/g++ -fsyntax-only, gofmt -e, bash -n, ruby -c, php -l, luac -p, tsc, kotlinc, mcs, swiftc) mit minimaler Umgebung (keine Keys) und `PCL_CODE_TIMEOUT`. Fehlt der Compiler, meldet es das. `perl -c`/ghc bewusst nicht (führen Code aus).
- Ausführen (Recht `run_code`, Standard aus, nur mit `bwrap`, `PCL_ALLOW_RUN=0` sperrt): `tools.run_code` startet `RUNNERS` (py/js/sh/rb/php/lua)
  per `_sandbox_cmd` (bubblewrap: `--unshare-all` = kein Netz, nur `/usr` + Teile von `/etc`, Projekt ro unter `/projekt`, Temp-Arbeitsordner
  `/arbeit`, `--clearenv`) mit rlimits (`PCL_RUN_MEM_MB`, CPU, Dateigröße) und `PCL_RUN_TIMEOUT` (killpg). Neue Dateien → `output/run/<zeit>/`.
- Rust komplett (`rust_builder.py`, Werkzeug `rust_project`, Recht `run_code`, sichtbar nur mit `cargo_enabled`): Crate (Ordner mit Cargo.toml) wird
  ohne Dotdateien/`target`/`rust-toolchain*` nach `.rust/<name>/crate` kopiert (copy2 = Zeitstempel bleiben, inkrementell), `cargo fetch` OHNE Sandbox
  (Netz, fuehrt nichts aus, CARGO_HOME `.rust/cargo-home`), dann build/test/run `--release --offline` in bubblewrap (`T._sandbox_cmd` + Toolchain-sysroot ro,
  `/cargo` rw, `CARGO_TARGET_DIR=/arbeit/target`, rlimits `PCL_CARGO_MEM_MB`). Toolchain-Programme direkt aus `rustc --print sysroot` (nicht rustup-Huelle).
  Ohne bwrap (Windows) nur mit `PCL_CARGO_UNSAFE=1` direkt mit Minimal-Umgebung (ABI hat das am 2026-11-02 so gewaehlt). `op=package` nur bei gruenen
  Tests -> `output/<name>.zip` (README.txt, TEST_REPORT.txt, source/, program/). `_lock` = ein Bau gleichzeitig. Projekt-ZIP (`_projekt.zip`) laesst Dotordner aus.
  `/api/info` liefert `rust` = Modus, `allow_run` = run_code ODER rust. Tests `tests/test_rust.py` (echtes cargo), `selftest.py rust`. Auf Pi/Windows ungetestet.
- Echter Browser: `browse_page` (Recht `web`, nur wenn Playwright importierbar und `PCL_BROWSER`≠0): Chromium je Aufruf, `_browser_lock` (1 Instanz),
  `ctx.route` + `route_web_socket` prüfen JEDE Anfrage mit `check_public` (Restrisiko DNS-Rebinding), WebRTC/Downloads/Service Worker aus.
  Screenshot fängt `run_with_tools` ab wie `view_image` (geht in `seen`). `install.sh --browser|--run`, `selftest.py browser|run`.
- Rechte `web`, `images`, `read_files` (Standard an) + `PCL_ALLOW_WEB=0` global. Webinhalte sind Daten, nie Anweisungen.
- Dateien: `/files/<pid>/<token>/<pfad>` (Link-Token per HMAC, ohne Cookie, weil Sandbox-Seiten Bilder nachladen), mit CSP `sandbox`; Ausnahme Video/Ton
  (`MEDIA_TYPES`): ohne Sandbox (Chrome blockt Medien mit Herkunft null per CORS), CSP `default-src 'none'; media-src 'self'`, feste MIME-Typen.
  `?download=1` = Anhang. Dateiansicht: Kasten „🎬 Finished videos“ (output/*.mp4…), ▶️ je Medienzeile, ⬇ je Datei. Test `tests/test_medien_abspielen.py`.
- Medien-Werkzeuge (`video_edit` per ffmpeg-Argumentlisten ohne Shell, `speak`, `make_document`, `download_file`, PDF/DOCX/EPUB lesen) liegen ebenfalls in `agent_tools.py`, Recht `media`. Pfade immer per `_inside` auf den Projektordner begrenzt, Temp-Ordner `.tmp-*` sind versteckt.
- `site_macro` (Recht `media`, nur sichtbar mit `PCL_MACROS=1`, Playwright und einem Skript `macros/<site>.py`, Vorlagen `vorlage_*` zaehlen nicht):
  startet das vom Besitzer aufgenommene Playwright-Skript als Subprozess mit minimaler Umgebung (keine Keys), `PCL_PROMPT`, `PCL_OUTPUT`
  (Temp-Ordner `output/.tmp-macro-*`), `PCL_STORAGE` (`macros/<site>.json`, Cookies, gitignored). Groesste Dateien -> `output/`. `_macro_lock`
  (eine Instanz), `PCL_MACRO_TIMEOUT` (3600). Fuer MagicLight/Google Flow (keine API). Agenten waehlen nur Name + Text. Doku `macros/README.md`.
- `video_generate` (Recht `media`, nur sichtbar mit `VIDEO_PROVIDER`): Anbieter in `video_providers.py` (`VIDEO` = Keys + Standardmodelle,
  `GEN` = je Anbieter `gen_*` -> (bytes, url, download_headers, fortsetzen_id)). `VIDEO_PROVIDER` ist eine Liste, der erste ist Standard, `call.provider`
  waehlt nur aus der Liste. Modelle `<ANBIETER>_VIDEO_MODEL` / `<ANBIETER>_I2V_MODEL`, altes `VIDEO_MODEL` gilt fuer den ersten. Gemini: Standardmodell
  `gemini-omni-1.1-flash` (Interactions-API, `continue_id` = `previous_interaction_id`), `veo-*` per `:predictLongRunning`, Code weiter in agent_tools
  (`_omni_video`/`_veo_video`). openai = Sora `/videos` (Startbild per `_fit_image` auf Videogroesse, `continue_id` = Remix), openrouter `/api/v1/videos`
  (`frame_images`), runway (`X-Runway-Version`), luma (Startbild nur https), kling (JWT HS256 aus Access/Secret Key, `kling_token`), minimax
  (query + files/retrieve), wan (DashScope async), seedance (BytePlus, Parameter als `--ratio/--duration` im Text), higgsfield (`Key id:secret`,
  Startbild ueber `files/generate-upload-url`, `Idempotency-Key`, Status `nsfw`), fal (Queue, `fal_run`, Std. `minimax/h3-max/text-to-video` = 0,03 $/s,
  Modellname ohne `/` faellt auf den Standard zurueck), replicate. `save_url` laedt nur https,
  prueft jeden Host per `check_public` und schickt Zugangsdaten nur an den ersten Host. `<ANBIETER>_VIDEO_PARAMS`/`VIDEO_PARAMS` = Zusatzfelder.
  `video_ai` (`VIDEO_AI=fal`: upscale/lipsync/sound, Dateien als data-URL max. 50 MB), `sound_generate` (`AUDIO_PROVIDER` elevenlabs|fal),
  `speak` mit `TTS_ENGINE=elevenlabs|openai` (`cloud_tts`). `engine` je Aufruf bzw. je Filmfigur (`stimme.engine`, `tts_engine`) waehlt
  ElevenLabs nur bei Bedarf; `describe` zeigt den Agenten `TTS_PREMIUM_HINT` nur mit `ELEVENLABS_API_KEY`. Cloud-Fehler -> lokale Stimme mit
  `HINWEIS:` (ausser `TTS_FALLBACK=0`), im Film Hash `ersatz` = beim naechsten `voices` neu. `speak` mit `list_voices` -> `VP.elevenlabs_voices`.
  Tests `tests/test_elevenlabs.py`. Doku `docs/videodienste.md`. Alles nur gegen Mocks getestet (`tests/test_video_providers.py`).
- `image_generate` (Recht `images` ODER `media`): `IMAGE_PROVIDER` pollinations (Std.; ohne Key alter Gratis-Endpunkt `image.pollinations.ai` ohne Referenzen, mit `POLLINATIONS_API_KEY`
  `gen.pollinations.ai/v1/images/generations`, `image` als LISTE von data-URLs, Std.-Modell `POLLINATIONS_MODEL` = `black-forest-labs/flux.2-klein-4b`; seit 2026-07 kein laufendes Gratis-Guthaben mehr) | openai (`/images/edits` mit `image[]` bei `refs`) |
  gemini (`generateContent`, Text + `inline_data`, `imageConfig.aspectRatio`/`IMAGE_SIZE`, Std.-Modell `GEMINI_IMAGE_MODEL` = `gemini-2.5-flash-image`; Modellnamen per `_model_env` bereinigt, leer = Standard) | openrouter (`/api/v1/images`, `input_references` als data-URL, Std. `google/gemini-2.5-flash-image`). `IMAGE_FALLBACK=pollinations` (Std. aus): Anbieterfehler -> Ersatzbild ohne refs (mit Pollinations-Key mit refs), Hinweis im Ergebnis. `IMAGE_STYLE` wird jedem Prompt vorangestellt. sdcpp = eigener Rechner mit stable-diffusion.cpp `sd-server` (`SDCPP_URL`, `POST /sdapi/v1/txt2img`, refs als `extra_images`, `_sdcpp_size` laengste Seite `SDCPP_SIZE`, `_sdcpp_lock` = ein Bild gleichzeitig, Zeitlimit `SDCPP_TIMEOUT` 1800 s; Anleitung `docs/laptop-bildrechner.md`, Einrichtung `deploy/windows/bildrechner-einrichten.ps1`: GitHub-Release `*-bin-win-cpu-x64.zip` + 3 Modelle per curl.exe mit `.part`, UTF-8 mit BOM und CRLF wegen PowerShell 5.1; `.bat` bleibt ASCII, cmd.exe kann kein UTF-8). nvidia = `ai.api.nvidia.com/v1/genai/<IMAGE_MODEL>` (Std. flux.1-schnell nur 1024², kontext-dev mit 1 `image` als data-URL) | cloudflare = `accounts/<CF_ACCOUNT_ID>/ai/run/<IMAGE_MODEL>`, FLUX.2 per Multipart mit `input_image_N` (unter 512 px per `_small_ref`), sonst JSON | hf = `router.huggingface.co/<HF_IMAGE_PROVIDER>/models/<IMAGE_MODEL>`, Antwort Bilddatei. `_b64_image` holt Bilder aus artifacts/result/data. `refs` max. 4,
  `format` quadrat/hoch/quer, `path` nur in assets/output/karten (ueberschreibt). Eingabefehler vor dem API-Aufruf. Nur mit Mocks getestet.
- Anbieter: `PROVIDERS` mit `kind` (openai/anthropic) und `models_url` (None + `models` = feste Liste, z. B. perplexity/cloudflare; `needs_env` = zusaetzliche Pflicht-Variable wie `CF_ACCOUNT_ID`; Together liefert die Modellliste als reines Array). Neben den grossen: mistral, nvidia, together, perplexity, huggingface (`HF_TOKEN`), cloudflare. `:free`-Modelle kosten in `est_cost` 0; `list_models` (Cache 10 min), `/api/providers/<id>/models`, `/api/providers/test`.
- Chat: Tabelle `chats`, `/api/agents/<id>/chat` (+`/order`). Uploads: `/api/projects/<id>/upload` → `input/` über `save_input`
  (Name bereinigt, nie überschreiben, `renamed` in der Antwort). Chat-POST nimmt `files` (nur Pfade in `input/`, dazu automatisch Dateien aus `input/`, deren Name in der Nachricht steht), stellt `files_note` vor die Nachricht
  und hängt den INHALT an (`chat_attachment_block`: Text/PDF/DOCX über `tools.read_file`, Bilder als Bild über `call_llm(..., images=)`:
  API als image_url/image-Block, `claude_cli` per `--input-format stream-json`, `codex_cli` per `-i`; lehnt das Modell Bilder ab, Text-Retry mit Hinweis).
  `chats.files` merkt die Anhänge, ältere Nachrichten bekommen den Text gekürzt. `chat_system` listet die Dateien in `input/`.
- Bilder in Aufgaben: Werkzeug `view_image` (Recht `read_files`, Bilder und Seiten gescannter PDFs über `tools.pdf_page_images`:
  pdftoppm, sonst eingebettete Scanbilder per pypdf). `run_with_tools` fängt es ab und schickt alle Bilder des Laufs (`seen`, max.
  `PCL_RUN_MAX_IMAGES`) in jeder Runde mit; `task_images` hängt im Auftrag genannte Bilder/Scans aus `input/` gleich an. `call_llm_img` = mit Text-Rückfall.
  `read_file` liest PDFs bis `PCL_MAX_READ_MB` (200). UI: Ergebnisse mit 📋 Kopieren (`resHtml`/`copyText`, Fallback ohne HTTPS),
  `loadTasks` zeichnet nur bei Änderungen neu und nie während einer Markierung.
- Selbstkontrolle: `run_with_tools` rendert neue PDFs aus `made` (`tools.pdf_overview` = alle Seiten auf einem Bild + Seite 1) und erzwingt eine
  Runde „SELBSTKONTROLLE“ (`PCL_SELF_CHECKS`, Standard 1). `build_system` hat den Absatz ARBEITSWEISE (max. 2 Rückfragen, sonst ANNAHME, nachrechnen).
- Dateien in Aufgaben: Werkzeug `write_file` (Recht `write_files`, intern `write_code`, nicht `input/`/Dotpfade) schreibt SOFORT im Werkzeug-Schritt,
  damit `make_document` im selben Lauf daraus bauen kann (die Aktion `write_file` im End-JSON greift erst nach dem Lauf). `make_document` gibt es mit
  `media` ODER `write_files`. Teamlisting zeigt auch die Rechte des Teams darunter (`descendants`). Keine Hinweise mehr „CLI liefert nur Text“:
  CLI-Agenten erzeugen Dateien genauso über die Server-Werkzeuge (der Hinweis hatte Chefs zum Blockieren gebracht).
- `make_document` mit `html` (Pfad oder HTML-Text → `work/<name>.html`): WeasyPrint (optional, `install.sh` installiert es, braucht libpango),
  eigener URL-Fetcher erlaubt nur `data:` und Dateien im Projektordner ohne Dotpfade (kein Netz, kein SSRF). Chromium-Rückfall bewusst nicht.
- Eigene Verbindungen der Herkunfts-KI (`ai_links.py`, Doku `docs/ki-verbindungen.md`): `tokens/claude-mcp.json` (`PCL_CLAUDE_MCP`) -> `--mcp-config`
  + `--allowedTools mcp__<name>`; `PCL_CLAUDE_CONNECTORS=Canva` (claude.ai-Abo) entfernt `--strict-mcp-config` und erlaubt `mcp__claude_ai_<Name>`
  (abweichender Name aus der init-Zeile -> `LEARNED`). Mit Verbindungen laeuft claude immer per stream-json (`_run_claude_stream`), Status aus der
  init-Zeile (`parse_init`/`record`, `STATE`), Fehler -> `_links_report` (Audit `ai_link_failed`, Telegram je Verbindung alle 6 h). `prompt_block` in
  `build_system`/`chat_system`. Codex: nur Namen aus `~/.codex/config.toml`. API `/api/ai_links`(+`/check`), `selftest.py links`. Chat: `auto_image`
  haengt das neueste Bild aus `input/` an, wenn `IMG_WORDS` passt und kein Bild dabei ist. Tests `tests/test_ki_verbindungen.py`.
- Canva-Bilder (Wunsch ABI 2026-11-05, nur mit Referenzbild): Server kommt nicht an Canva, der Claude-CLI-Agent ruft Canva nativ auf. `canva_upload`
  (Recht `images`, nur mit Konnektor Canva) POSTet ein Projektbild roh an den Upload-Link (nur https `CANVA_UPLOAD_HOSTS` + `PCL_CANVA_UPLOAD_HOSTS`).
  `IMAGE_PROVIDER=canva` -> `image_generate` wirft `CANVA_HOWTO`; scheitert ein anderer Anbieter, haengt der Fehler den Weg an, und mit Referenzbildern
  gibt es dann kein Pollinations-Ersatzbild ohne Referenz. `image_save` kann `path`. Prompt-Absatz `_canva_block` in ai_links. Tests `tests/test_canva.py`.
- `claude_cli`: läuft mit `--strict-mcp-config` (keine Konnektoren wie Gmail/Drive aus dem Abo) und bekommt die System-Nachricht als
  `--system-prompt` statt des Claude-Code-Prompts. Ohne beides hielt sich das Modell für werkzeuglos und ignorierte die JSON-Werkzeuge.
  Kann ein Modell keine Bilder, sagt `call_llm_img` ihm das (Bericht nennt Agent/Modell). Angeworbene Mitarbeiter haben immer `read_files`.
  Telegram: Datei-Nachrichten (`tg_file_of`) → `tg_save_file` → Bildunterschrift = Auftrag/Überarbeitung, ohne Text in `_tg_pending` für den nächsten Auftrag, Alben über `_tg_groups`/`tg_flush_groups`.
- Oberfläche responsive: unter 820 px Menü ☰ (`#app.side-open`), Panel als Vollbild, Canvas per Pointer-Events (Touch, zwei Finger = Zoom).
- Installer: `install.sh --system` (Medien/OCR per apt), `--code` (Compiler aus `CODE_PKGS`), `--all` (alles inkl. Piper + Dienst). `selftest.py code` prüft alle Sprachen, `selftest.py film` Blender.
- OCR: `ocr_pdf`/`ocr_image` (tesseract + pdftoppm) als Rückfall in `_doc_text`/`read_file`. Piper: `_piper()` sucht im venv und in `models/piper/`. `selftest.py` prüft auf dem Pi alle externen Dienste (Suche, Bilder, LLMs, Telegram, Medien, OCR). Ollama-Zeitlimit `OLLAMA_TIMEOUT`.
- `call_llm`: bei 429/5xx oder leerer Antwort (`EmptyReply` aus `_parse_reply`, z. B. Gemini ohne `content` bei Filter) erst alle Keys, dann `PCL_LLM_RETRIES` (3) weitere Runden mit Pause `PCL_LLM_RETRY_WAIT` (8 s, verdoppelt, Retry-After beachtet). Abgeschnittene leere Antworten (`length`) werden nicht wiederholt.
- Gruppen-Umstellung: Menü „🔀 KI für Gruppe“, `GET /api/agents/all`, `POST /api/models/assign` (`agent_ids`, `provider`, `model`).
- Standardmodelle: `default_model(pid)` nimmt `PROVIDERS[pid]['model']`, ersetzt es aber, wenn die Live-Liste es nicht mehr führt (`_MODEL_PREF`). OpenRouter-Bezahlmodelle bekommen ohne `PCL_MAX_OUTPUT` `max_tokens=8192` (sonst 402 bei wenig Guthaben). Windows: Schriften aus `%WINDIR%\Fonts`, `selftest.py` gibt Windows-Hinweise (`fix()`). README-Abschnitt „Betrieb“ = Bedienanleitung je System.
- Modell-Überwachung: `model_health` (Agenten-Modell nicht mehr in der Live-Liste oder Aufruf mit 404/„model not found“ → `_bad_models`), Worker prüft alle `PCL_MODEL_CHECK_HOURS` (6) und meldet Änderungen einmalig (Audit + Telegram, Marker `settings.model_alert_sig`). UI: Menü „⚠ Modelle“, `GET /api/model_health`, `POST /api/models/replace` (Sammel-Umstellung).
- Nur gegen simulierte Antworten getestet, in der Entwicklungsumgebung gab es kein Internet: echte Suche/Bildanbieter zuerst auf dem Pi prüfen.

## Filmstudio (Werkzeug `film`, Recht `media`)
- `film_studio.py`: Drehbuch `film/film.json` (deutsche Schluessel: figuren/szenen/aktionen/dialog/kamera), `normalize` prueft und sammelt ALLE Fehler.
  Ops: save (prueft vor dem Schreiben), check, voices (`film/ton/`, Cache per Hash in `index.json`), preview (`film/vorschau/<id>.png`, app.run_with_tools haengt
  es wie view_image an), render (`film/clips/<id>.mp4`, Hash in `clips/index.json`, unveraenderte Szenen uebersprungen, `PCL_FILM_BUDGET`), assemble (`output/<name>.mp4` + `.srt`).
- Die ganze Zeitlogik (Gehen, Springen, Winken, Blick, Kamera, Mund aus Lautstaerke per ffmpeg-Rohdaten, Blinzeln) rechnet `entity_frames`/`camera_frames`
  in Python; `blender/pcl_film.py` baut nur die Szene und setzt je Bild die Werte (Bild fuer Bild rendern, fertige PNGs in `film/.frames/` werden
  bei Abbruch weiterverwendet). Bei Aenderungen am Blender-Skript `SCRIPT_VERSION` erhoehen.
- Blender-Aufruf: `-b --factory-startup --disable-autoexec -noaudio --python-exit-code 3`, Umgebung ohne KEY/TOKEN/SECRET/PASSWORD, `T._heavy_lock`
  (gleiche Sperre wie sdcpp). `blender_exe`: `BLENDER_PATH`, PATH, Windows-Standardordner (neueste Version). Erfolg nur mit `PCL_FERTIG` in der Ausgabe.
- Geraeusche je Szene (Wunsch ABI 2026-11-06): `geraeusche` [{datei, zeit, zeile, lautstaerke, schleife, dauer}], `sound_times` (zeile = Start der
  Dialogzeile + zeit, fehlende Zeile -> weg), `scene_audio` mischt sie (adelay, -stream_loop, atrim), Dateien im `_scene_hash`. MAX_GERAEUSCHE 40.
  `atmo`/`atmo_lautstaerke` je Szene (Schleife ueber die ganze Szene). Ducking: `ducken` (Drehbuch, Std. an, in jede Szene kopiert) ->
  Musik+Atmo per `DUCK` (sidechaincompress, Schluessel = Sprachmix) in `scene_audio` und Filmmusik in `op_assemble` (Schluessel = Filmton).
  `sound_notes` (in `op_check`) meldet Szenen ohne Ton, damit das Studio selbst entscheidet. Tests in `tests/test_film.py`.
- Bildfiguren drehen sich nie (werden gespiegelt), Hintergrundbild haengt an der Kamera. `speak` hat `voice/pitch/rate/target`.
- Getestet mit Blender 5.2 als pip-Paket `bpy` (Huellskript als BLENDER_PATH, `PCL_TEST_BLENDER`), eevee/workbench/cycles rendern; echtes Windows-Blender ungetestet.

## Gedaechtnis, Firmenwissen, parallele Worker
- `agents.memory`: Agent liefert optional `remember` (max. `REMEMBER_MAX`), `save_memory` haengt datiert an, dedupliziert, kuerzt auf `PCL_MEMORY_CHARS`.
  `memory_block` + `knowledge_block` (Ordner `wissen/`, `.md/.txt` in den Prompt bis `PCL_KNOWLEDGE_CHARS`, Rest als Liste) stehen in `build_system` und `chat_system`.
  API `/api/projects/<id>/knowledge` (GET/PUT `wissen/firmenwissen.md`), Upload mit `?dir=wissen`. Agent-PUT nimmt `memory`.
- Worker: `start_worker` startet `WORKERS` Threads; `claim_next` setzt unter `_claim_lock` atomar `queued`->`running` (nie zwei Aufgaben je Agent,
  max. eine Ollama-Aufgabe). Nur Worker 0 macht `schedule_tick`/Modellpruefung. `wake_parent` weckt per bedingtem UPDATE genau einmal.
  `run_claimed` setzt bei Ausnahme `failed` statt `running` haengen zu lassen.

## Uebergabe und automatisches Weitermachen (Wunsch ABI 2026-11-06)
- `handover.py`: je oberstem Auftrag `handover/assignment-<id>.md` im Projektordner (Kopf: Auftrag + Arbeitsort = Projektordner, Git-Repos bis Tiefe 2
  mit origin-URL ohne Zugangsdaten, `STAND.md`/`HANDOVER.md` bis Tiefe 4; dann `## Log`). `handover_note` (app.py) schreibt: start, jede Werkzeugrunde
  (`trail` in `run_with_tools`, sofort nach der Runde), Ergebnis + Dateien + `next_step` (neues optionales JSON-Feld), Fehler, Neustart, Modellwechsel.
  Gekuerzt ab `PCL_HANDOVER_KB` (64), Kopf bleibt. `handover_block` haengt Arbeitsort + Log-Ende (`PCL_HANDOVER_PROMPT`) an work/review_prompt, wenn die
  Aufgabe schon Eintraege hat oder `feedback` mit `RESUME_MARK` beginnt. Aus mit `PCL_HANDOVER=0`.
- `retry_later`: Ausnahme in `execute_task` -> Aufgabe bleibt `queued` mit `retry_at` (RETRY_MIN 5 min, verdoppelt, max 120) und `retries` bis
  `PCL_RETRY_MAX` (6), danach `failed` wie frueher; Eltern warten weiter (kein `finish`). `claim_next` ueberspringt `retry_at` in der Zukunft.
  Neustart (`init_db`): `running` -> `queued` mit RESUME-Feedback (nur wenn feedback leer, Revisionswuensche bleiben). `model_changed(ids)` aus
  `api_agent_put`/`models/replace`/`models/assign`: wartende sofort, gescheiterte oberste Auftraege (`Error:`, 7 Tage) wieder `queued`.
  `PCL_AUTO_RESUME=0` = altes Verhalten. Kontrollgang zeigt wartende unter „STOPPED BY AN ERROR“. Tests `tests/test_handover.py`.
- `rust_builder._target_name`: Bauordner je Toolchain `.rust/<name>/target-<release>-<sha1(rustc -vV)[:8]>` gegen E0514 durch alte Baureste
  (NEXORA, 2026-11-06, Pi hatte rustc/rustdoc/cargo 1.98.0 einheitlich). Alter `target/` bleibt liegen, nie automatisch loeschen.

## Ziele, Freigabe-Schranken, Nutzung
- `goals` (parent_id 0 = oberstes), `tasks.goal_id` (vererbt in `create_subtasks`). `goal_tree` (Tiefe + Fortschritt inkl. Unterziele),
  `goals_block` in `build_system` (nur Chefs/oberste) und `inspection_report`, `goal_line` in work/review_prompt. API `/api/projects/<id>/goals`, `/api/goals/<id>`.
- Schranken `settings gates:<pid>` (`plan`, `recruit`, Standard aus): `request_gate` legt `approvals.kind='plan'|'recruit'` mit `data` (JSON) an,
  Aufgabe `waiting_approval`; `decide_gate` (Web + Telegram `ga:`/`gd:` mit Approval-ID, atomar) erzeugt dann die Teilaufgaben bzw. ruft `recruit_team`.
  Ablehnen = `failed` -> Post -> Antwort = neu planen. Nur oberste, nicht geplante Aufgaben im Modus `plan`. Shell nie ueber Telegram.
- `call_llm` = Huelle um `_call_llm`, schreibt jeden Aufruf in `llm_calls` (`record_call`, `est_cost` mit `PRICES`/`PCL_PRICES`, Abo/lokal = 0).
  Abo-Warnung `PCL_ABO_WARN_5H` einmal je 5 h (`settings abo_warn:<anbieter>`). API `/api/usage?days=`.
- Tests: `tests/` (pytest, `conftest.drain()` arbeitet die Queue synchron ab). Neue Funktionen dort mit abdecken.

## Weltall und Wachstum (Hyperstead)
- `growth.py` (reine Daten + Rechnung): `WORLDS` = `kosmos` (Std.) und `atom` (Wunsch ABI 2026-11-04: Quark/Atom/Molekuel/Kristall/Zelle,
  Raenge Neutrino/Elektron/Proton/Nukleon, Energie, Experimente; je Welt `explain`). Gilde/Tycoon/Gizmo-Stadt gestrichen, alte Werte faengt `world_ok` ab.
  UI `syncWorld`: Grafik Weltall -> PUT world kosmos, Atom -> atom (Organigramm/Bauplan behalten die Welt). `atomSky` = ruhiger Atom-Hintergrund je Stufe. Stufen Asteroid/Planet/Sonnensystem/Sternhaufen/Galaxie, Raenge Komet/Mond/Planet/Stern,
  Begriffe Sonne/Planet/Mond/Mission/Sternenstaub. `STAGE_POINTS`, `STAGE_TEAM`/`STAGE_DEPTH` (Grenzen nur fuers SELBST-Anwerben), `RANK_AT`, `POINTS`.
  Welt nur Oberflaeche: Agenten-Prompts nie mit Spielbegriffen (Test `test_prompts_ohne_spielbegriffe`).
- app.py: `project_world` (`settings world:<pid>`), `growth_limits_on` (`growth_limits:<pid>`, Std. an), `project_points` aus dem Audit-Log
  (task_done mit tasks.rounds, inbox_closed, task_failed, inbox_rework; dadurch automatisch nachgeruestet), `agent_ranks`, `growth_check`
  (aus `log()` bei GROWTH_EVENTS; erster Aufruf merkt `stage:<pid>` still, Aufstieg -> audit `stage_up` + Telegram einmal).
  `recruit_team` kuerzt nach Stufe (Notiz an den Chef). API `/api/worlds`, `/api/projects/<id>/growth`, PUT `/api/projects/<id>/world` (nur noch `limits` sinnvoll).
  Tests `tests/test_growth.py`.
- UI (index.html): Wachstumsleiste `#growth` (`loadGrowth` alle 10 s, `renderGrowth`), Farben per CSS-Variablen, Hell/Dunkel `data-theme`
  (localStorage `hs-theme`), keine Weltauswahl mehr. Sonnensystem `#map` (SVG im selben `#world`-Transform wie die Knoten, Weltall immer dunkel):
  `teamsOf` (Team = Wurzel oder Agent mit Unterstellten, members = alle direkt Unterstellten), `sysLayout` (Sonne = Wurzel, Planeten = ihre Kinder,
  bis 5 Planeten je eigene Bahn, sonst geteilte Bahnen; Bahnen als Ellipsen `MAP.TILT`), `systemSvg`/`moonSvg` (Monde = Kinder der Planeten, alle
  tieferen als Mini-Monde `allBelow`), `skySvg` (Sterne/Nebel/Spirale je Stufe, Zufall mit Projekt-ID als Saat). Mehrere Wurzeln = mehrere Sonnen
  nebeneinander. Eigendrehung: `bands` liefert die Oberflaeche ueber `spinWrap` zweimal nebeneinander in `.spin`, `placeMovers` verschiebt sie (`spinSpeed`, 10–20 s je Drehung, Monde ohne). Sonne (`sunSpots` mit `.spin` data-w/data-period), Strahlenkranz und Galaxie-Spirale (`.rot` data-period) sammelt `MAP.spinners`, `placeMovers` bewegt sie mit. Bewegung per `requestAnimationFrame` (`orbitTick`/`placeMovers`, Winkel = a0 + Zeit*w, ~25 fps), nur mit Bewegung an, nicht auf
  dem Handy, haelt bei Maus ueber einem Koerper (`MAP.hold`). `drawMap` baut nur neu, wenn sich `MAP.sig` (Agenten, Zaehler, Stufe, Auswahl) aendert.
  Zustandsringe `agentState` (appr > run > fail > wait). Klick ueber `mapPick`: Sonne/Planet mit Team -> `#bcard`, Mond -> Agent. Handy <=820 px `#wlist`
  (Sonne, Planeten, Monde als eingerueckte Karten). Ansicht `VIEW` world|plan (localStorage `hs-view`).
- Grafik-Auswahl: aufklappbares Menue `#gViewBtn`/`#gViewMenu` (world, org+baum/gliederung/kreis, atom, plan; `markView`, `viewMenu`).
  Dunkle Farbvariablen in `:root` NIE auf sich selbst zeigen lassen (`--edge:var(--edge)` machte die Bauplan-Linien unsichtbar). `untangle`: liegen
  Agenten im Bauplan aufeinander, einmal je Projekt `autoLayout`. Verbinden (Port ziehen, Agent/Karte auf anderen ziehen) immer ueber `connectAsk` (confirm, Zyklus-Pruefung).
- Atom (`VIEW='atom'`, `#atomsvg`, `drawAtom`/`atomPlace`): Molekuel-Netzwerk (Wunsch ABI 2026-11-04): `atomLayout` = Faecher um den Vorgesetzten + Abstossen/Federn, Saat = Projekt-ID; Kugelgroesse nach Ebene (Wurzel cyan, Ebene 1 `ATOM_MID`, tiefer `ATOM_SMALL`), Staebe `.abond` = parent-Beziehung, mehrere Wurzeln lose verbunden. Steht still, keine Animation, keine Pulsringe; `atomPlace` ist leer.
- Logo: `static/logo/hyperstead-{32,180,192,512,1024}.png` (Favicon, Seitenleiste `.brand img.logo`, Login-Seite), `/static/logo/` ohne Anmeldung (guard).
  Gerendert mit `docs/logo/logo_blender.py` (bpy/Cycles, Molekuelnetz), Prompt und Anleitung `docs/logo-prompt.md`.
- Organigramm (Ansicht `VIEW='org'`): `#orgsvg` im `#world`-Transform, drei Arten
  (`ORG.style` baum|gliederung|kreis, localStorage `hs-org`), Layouts liefern nur `nodes`, `orgRender` wendet Verschiebungen `ORG.off` an
  (localStorage `hs-orgpos`, je Projekt+Art, `#orgReset`) und zeichnet Linien neu: `orgBaum` (oben nach unten, mehr als 2 Mitarbeiter ohne Team werden gestapelt),
  `orgGliederung` (eine Zeile je Agent, eingerueckt; `fit` nur nach Breite), `orgKreis` (Wurzel in der Mitte, Ringe je Ebene, Winkel nach Blattzahl,
  mehrere Wurzeln -> Projektname in der Mitte). Karten `orgCard` mit Zustandsfarbe `ORG_COL`, Klick -> `selectAgent`. `drawOrg` baut nur bei neuer `ORG.sig`.
- Betriebszentrale: `project_ops(pid)` / `GET /api/projects/<id>/ops` (aktive + fehlgeschlagene Aufgaben 7 Tage, offene Freigaben, Zeitplaene,
  Kosten heute/7 Tage aus `llm_calls`, Fehler-Ereignisse und letzte Ereignisse aus `audit`, `open` = `is_open`). UI `showOps` (🛰, Klick auf `#gStats`),
  Knoepfe nutzen vorhandene APIs (`/tasks/<id>/run`, `/schedules/<id>/run`). Growth-API liefert zusaetzlich `cost_today`/`calls_today` (💶 in der Leiste).
- Feinschliff: `celebrate(g)` (`#party`, Konfetti nur ohne `motionOff()`), Rang-Aufstieg als Toast (Vergleich alter `WORLD.g.ranks`), Schalter Bewegung
  im ⓘ-Fenster (`setMotion`, localStorage `hs-motion`, `data-motion=off`). `#ov` ist `role=dialog`, `openOv`/`closeOv` setzen den Fokus, Esc schliesst
  Feier/Fenster/Gebaeudekarte, `:focus-visible`-Rahmen. Pruefskript (nicht im Repo): alle sichtbaren Bedienelemente brauchen Text, title oder aria-label.
- Anleitung/Hilfe: `HELP` (Kapitel als HTML, offline), `showHelp(kapitel)` (📖, Suche, `<details>`), `HELP_MAP` ordnet Fenstertitel einem Kapitel zu
  (ⓘ `#ovhelp` in `openOv`). `TIPS` (Selektor -> Text oder Funktion) setzt per `applyTips` + MutationObserver `title` auf jeden Knopf/Link ohne
  eigenen Hinweis; Hilfe-Modus (`data-helpmode`, localStorage `hs-helpmode`) faengt den ersten Klick ab und zeigt `#tipbox`. Neue Knoepfe brauchen
  `title` oder einen TIPS-Eintrag, sonst schlaegt `tests/test_ui_hilfe.py` fehl. Neue Funktionen auch in `HELP` beschreiben.
- Postkorb: `inbox_delete(ids|None)` setzt `tasks.inbox='deleted'` (nur oberste Aufgaben mit new/closed, Audit `inbox_deleted`, Aufgabe bleibt).
  API `POST /api/inbox/delete` (`ids`), `POST /api/inbox/clear` nur mit `confirm: true` (UI fragt per `confirm()`). UI: Haken `data-sel`, `#in_all`/`#in_del`/`#in_clear`.
- Seitenleiste `#sidemenu`: Kategorien als `<details class="side-grp" data-grp=…>` (arbeit offen, team/daten/auswertung zu), Zustand localStorage `hs-side`,
  `sideDots()` (aus `refresh`) zeigt einen Punkt an zugeklappten Kategorien mit sichtbarem Zaehler. Neue Menueknoepfe in eine Kategorie einsortieren.

## Alle Firmen (Uebersicht, Plan `docs/ebenen-plan.md`)
- Firma = Projekt. `firms_overview()` / `GET /api/firms`: je Projekt Stufe, Agenten (nur id/name/role/parent_id/busy, keine Rechte/Anbieter),
  `busy` (running+queued), `partners`; dazu `links`. Partnerschaften setzt nur der Besitzer: Tabelle `firm_links` (a<b, UNIQUE),
  `POST /api/firms/links` (a, b, note; doppelt -> `exists`), `DELETE /api/firms/links/<id>`, Audit `firm_link`/`firm_unlink`, Projekt loeschen
  entfernt seine Links. Agenten sehen davon nichts. Tests `tests/test_firmen.py`.
- Seitenleiste (Wunsch ABI 2026-11-04, mit Bildern): unter „Projekte“ grosser Knopf „＋ Neues Projekt“ `#btnNewProj` (-> `newProjectDialog`: leer oder Vorlage), KEIN 🏙 und keine Ansichtsknoepfe. Grafik-Menue `#gViewMenu` in zwei Gruppen `.vgrp`: Klassik (Organigramm baum/gliederung/kreis, Bauplan) und Modern (nur hub stadt/kosmos/molekuel per `data-hubworld`). Weltall/Atom je Projekt aus dem Menue entfernt (Wunsch ABI 2026-11-04 abends, Code `drawMap`/`drawAtom` noch da), `setView` mappt world/atom -> org. In `VIEW='hub'` bleiben Kopfzeile und `#growth` sichtbar; `#hubbar` hat nur noch 🤝/← Alle Firmen/Suche (kein eigener Welt-Umschalter, kein `#hubClassic`). `#palette` (Agent hinzufuegen) ist in JEDER Ansicht sichtbar (Wunsch ABI): ausserhalb des Bauplans legt `addAgent(k)` ohne x/y rechts neben allen an, Hinweis je Ansicht (`.hint-plan/-org/-hub`), „Ordnen“ im Organigramm = Anordnung zuruecksetzen, im Hub = Drehung/Neigung zuruecksetzen + `fit` (Wunsch ABI).
- Drehen/Neigen im Hub (Wunsch ABI 2026-11-04): `HUB.cam[welt]` = {rot, tilt 0–60} (localStorage `hs-hubcam`), `hubCamApply` setzt CSS `perspective rotateX rotateZ` auf `#hubsvg` (Ursprung = Mitte `HUB.box`) und `--hrot`; `text` dreht per CSS zurueck um seinen Anker (transform-origin = x/y-Attribut, `transform-box:view-box`, darum Texte im Hub nie mit eigenem `transform`), `.hlogo` um die Mitte. `hubTurn(dr,dt)`; Knoepfe `.cam` (#hRotL/#hRotR/#hTiltUp/#hTiltDn/#hCam0) in `.zoom` nur im Hub, rechte Maustaste/Shift-Ziehen = `drag.type='turn'`, Touch: zwei Finger drehen/gemeinsam schieben im `pinch`. `fit` passt den gedrehten Umriss ein. Klicks laufen ueber DOM-Treffer, funktionieren gedreht.
- Links gewaehlte Firma im Hub (Wunsch ABI 2026-11-04): `hubMarkCur` (Ende von `drawHub` und in `openProject`) setzt `.firm.cur` (Leuchten, pulsiert ohne `motionOff`) und `#hubsvg.has-cur` (andere 50 %), nur aussen und ab 2 Firmen; `hubShowCur` faehrt sanft hin (Zoom bleibt). `openProject` verlaesst im Hub eine andere geoeffnete Firma.
- UI moderne Ebene (`VIEW='hub'`, `#hubsvg`, `#hubbar` Umschalter 📐 Klassisch = zurueck zu `HUB.back` / `data-hubworld` stadt|kosmos,
  localStorage `hs-hubworld`/`hs-hubback`): `loadFirms` (alle 4,5 s), `drawHub` -> `HUB_DRAW[welt]()` (neue Welt = neuer Eintrag), `hubTeams`
  (Leitung + Abteilungen wie im Weltall). Stadt `hubCity`/`hubBuilding` (isometrisch, Fenster nur bei `busy` hell (sonst 7 %), Fensterfarbe per `style` weil CSS `.win` das fill-Attribut ueberdeckt, Baustil je Firma `hubStyle` turm|buero|zwilling|campus aus `isoBox`, Hoehe nach Stufe, Box nach `HUB.zmax`, Beschriftungen in eigener Ebene obenauf),
  Kosmos `hubCosmos`/`hubSystem` (Planeten kreisen per rAF nur mit Bewegung, seit 2026-11-04 auch auf dem Handy mit ~15 fps und im Innern; `HUB.hold` haelt unter Maus/Finger an; Sonne `hubSunR` waechst mit Stufe+Team; keine Firmensymbole (Wunsch ABI); Beschriftungen per CSS-Variable `--lz` aus `applyView` gegen Herauszoomen vergroessert, zweite Zeile per `dy` in em). Klick -> `hubSelect` -> `#hubcard`
  (Leitung/Abteilungen, Name -> `hubOpenFirm` = klassische Ansicht + `selectAgent`). JS steht VOR dem Atom-Abschnitt (Atom-Test verbietet rAF dort).
- Innen (Phase 2): Klick auf Firma -> `hubEnter(pid, dep, agent)` (`hubZoomTo` faehrt 380 ms hin, dann `HUB.inside`). `hubInsideCity` (Etagen,
  eine Etage je Hierarchie-Ebene aus `hubLevels` (beliebig tief, Leitung ganz oben in der Chefetage, Wunsch ABI 2026-11-04), je Person ein Raum `.room` in Abteilungsspalten, Dach waechst mit der Stufe, `hubBuilding` bekommt Etagen nach Tiefe + Anbau ab Stufe 2; `--lz` innen max. 1,25; rechts `hubOrgChart`, `data-dep` -1 = Leitung, sonst Index in `hubTeams().deps`) bzw. `hubInsideCosmos` (statisch, damit man trifft). `#hubdeps` Liste,
  `hubDep` -> `#hubcard` zeigt Team (`hubAgRow`). `HUB.cardOff` = Infofenster zu (Handy beim Hineingehen). `hubLeave`/Esc/`#hubOut`. Suche `#hubSearch`
  -> `#hubResults` (Firmen + Agenten nach Name/Rolle). `fit` laesst im Innern links 226 px und bei offenem Infofenster rechts 346 px frei.
- Zusammenarbeit (Phase 3): nur `links` erzeugen Verbindungen. `hubTraffic` (Anzahl/Tempo aus `busy` beider Firmen, ruhend = 1 langsames
  Fahrzeug), Stadt `hubCityRoads`/`hubRoadPath` (Strasse nur durch die Gassen zwischen den Grundstuecken, orange Leuchtkanten, Fahrzeuge vor den Gebaeuden gezeichnet), Kosmos
  `hubCosmosRoutes` (Bogen zwischen den Sonnen, nur Raumschiffe; zarte Spur `.sroute` nur bei aktiver Zusammenarbeit). Abteilungssymbole `hubDepIcon` (Stichwoerter aus Name/Rolle). Canva-Bilder kommen in der Cloud-Sitzung nur als 200-px-Vorschau an, darum alles SVG. `HUB.tr` + `.veh`, `hubAlong` hin und zurueck, `hubPlaceTraffic`
  (Schiffe drehen in Flugrichtung). Dialog `showFirmLinks(pid)` (🤝 `#hubLink` oben, `#hubCardLink` im Infofenster).
- Molekuel-Welt (Wunsch ABI 2026-11-04, `HUB_DRAW.molekuel`): `molStyle(seed,farbe)` (Saat = Projekt-ID -> Spreizung/Stablaenge/Streckung/Drehung/Farbreihe), `molLayout`/`molSvg` im Atom-Abschnitt (ohne rAF) gemeinsam fuer Atom-Ansicht und Hub; `firmTree(f)`, `hubMolecules` (statisch, `hubMolBonds` = Stab zwischen den Leitungen von Partnern + Funken `.veh.spark` ueber `HUB.tr`), innen `hubInsideMol` (data-agent/data-dep). `#hubcard` ausserhalb von `view-hub` per CSS versteckt.
- Zurück/Monde (Wunsch ABI 2026-11-04): `#gBack` (← vor `#gViews`) + `GHIST` (`gState` = view/org/world/inside/dep/pid, `gNote` am Ende von setView/hubWorld/hubEnter/hubLeave/hubDep/openProject, max. 40, nur im Tab), `gBack` stellt genau das Design wieder her (`busy` verhindert neue Einträge). Knopf „📐 Firma öffnen“ (`#hubOpen`) entfernt, `hubOpenFirm` öffnet den Agenten ohne Ansichtswechsel. Kosmos: `hubMoons` (Mitarbeiter = Monde um den Planeten, `HUB.moons`/`HUB.moonEls`, innen klickbar mit data-agent), `hubSpin` (Oberfläche in `.hspin` mit data-w/data-p, dreifach nebeneinander, geclippt) = Eigendrehung von Sonnen und Planeten; `hubPlace` bewegt beides.
- Firmenlogo (Wunsch ABI 2026-11-04): `/api/projects/<id>/logo` GET/POST/DELETE, nur PNG/JPEG/WebP nach Magic Bytes (`logo_kind`, kein SVG), `LOGO_MAX` 2 MB,
  Datei `.logo.<art>` im Projektordner (Dotdatei = fuer Agenten/Webseite/ZIP unsichtbar), GET mit CSP sandbox. `firms_overview` liefert `logo` = mtime (Cache-Brecher).
  UI `hubLogo(f,x,y,groesse,rund)` (Schild auf dem Dach, in der Sonne, innen am Dachaufbau), Knoepfe `#hubLogoUp`/`#hubLogoDel` im Infofenster, `hubLogoPick`.

## Verbindungen (Webhooks)
- Tabelle `connections` (Besitzer legt URL/Methode/Kopfzeilen fest, `${ENV}` in Kopfzeilen aus .env, `confirm`, `on_post`). Recht `connect`
  -> `connections_doc` im Werkzeugblock, `call_connection` in `run_with_tools` (confirm -> `approvals.kind='connect'`, Task endet `waiting_approval`).
  `conn_request` ohne Redirects, max. 200 KB, `PCL_CONN_TIMEOUT`. Private Adressen erlaubt (nur Besitzer setzt sie).
  `notify_connections_post` aus `inbox_arrived` (Thread). Eingang `POST /hook/<pid>/<hook_token>` (guard-Ausnahme, `settings hook:<pid>`,
  Schluessel per `hook_nonce:<pid>` erneuerbar) -> `inbox_new_order`. Generische Freigabe beendet nur Aufgaben in `waiting_approval`.

## Cloud-Upload (`cloud_upload.py`, Recht `upload`, Standard aus, nicht in `RECRUIT_PERMS`)
- Dienste github (Contents-API bis `GITHUB_CONTENTS_MAX` 50 MB, sonst Release-Asset `GITHUB_UPLOAD_RELEASE`), gdrive (Scope `drive.file`, Ordner
  per Name suchen/anlegen, resumable in `DRIVE_CHUNK`), onedrive (Graph `Files.ReadWrite`, bis 4 MB PUT, sonst Upload-Session). Google/Microsoft per
  Geraete-Code (`device_start`/`device_poll`, Poll-Thread in `api_cloud_login`, Status in `_cloud_logins`), Refresh-Token in `tokens/<dienst>.json`
  (`PCL_TOKENS_DIR`, gitignored, chmod 600; Microsoft rotiert das Token bei jedem Refresh).
- app.py: `cloud_ready()` (+ telegram), `cloud_folders(pid)` = Zielordner je Projekt (`settings cloud:<pid>`, Std. `Hyperstead/<Projekt>`),
  `project_file` (keine Dotpfade), `do_upload`/`start_upload_job` (Thread, `_cloud_jobs`). Werkzeug `cloud_upload` (`cloud_doc`, `request_upload`)
  legt IMMER `approvals.kind='upload'` an (Wunsch ABI), Agent waehlt nur Unterordner. Freigabe startet den Upload im Thread, `approval_add_result`
  haengt den Link an und beendet die Aufgabe erst, wenn kein Upload mehr laeuft. Web: Fenster ☁️ Cloud, Knopf ☁️ je Datei (Ordner aus dem Dialog
  gilt absolut). Telegram `/datei [suche]` + Knoepfe `sf:<n>` (`_tg_filelist`), `tg_send_file` (sendDocument, max. 50 MB).
- `cloud_setup_block` (nur oberster Chef, nur im Chat): Status je Dienst + Kurzanleitung `CLOUD_GUIDE`, damit der CEO ABI durch die Einrichtung fuehrt
  (ABI-Wahl 2026-11-04 statt Repo-Anlegen per Werkzeug). Nie Tokens im Chat erfragen.
- Tests `tests/test_cloud.py` nur gegen Mocks, Anleitung `docs/cloud.md`.

## YouTube (`youtube_channel.py`, Recht `youtube`, Standard aus, nicht in `RECRUIT_PERMS`)
- Wunsch ABI 2026-11-05: Kanal mitverwalten. Rahmen: nur offizielle YouTube Data API, KEIN Browser-Skript bei Google, Upload nur nach Freigabe
  JE VIDEO, immer `private` (+ `publishAt` = YouTube veroeffentlicht zum Termin), keine fremden Videos herunterladen, Zahlen nur aus CSV-Export.
- Kanal-Datei `youtube/kanal.json` (deutsche Schluessel: serie/sprachen/kanaele/rhythmus/folgen mit titel/beschreibung/keywords/hashtags/datei je Sprache).
  `prepare` -> `youtube/packages/<epNN-lang>/package.json` (Feld `body` = videos.insert-Body, `uploaded` bleibt beim Neu-Vorbereiten), `title.txt`,
  `description.txt`, `keywords.txt`, `youtube/schedule.csv` (`;`, BOM), `youtube/REVIEW.md`. Pruefungen: Titel 100, Beschreibung 5000 Bytes, `<>`,
  Tags 500 (YouTube-Zaehlung `tags_length`), Hashtags, ffprobe 9:16 + 45-60 s, Rhythmus >3/Woche = Warnung. `analyze` liest Studio-CSV (Spalten per Stichwort EN/DE/TR, `_num` fuer 1.234/1,234/0:00:48).
- app.py: `youtube_doc`, `youtube_tool` (op upload -> `approvals.kind='youtube'`, data `{"package"}`), Entscheidung startet `yt.upload(root, pkg, pkg)` im Thread
  (`output='running …'` zaehlt wie upload in `approval_add_result`). UI: Haken `#p_youtube`, Freigabe-Text, HELP-Eintrag.
- Anmeldung nur per CLI durch den Besitzer: `python youtube_channel.py login <lang>` (Loopback + PKCE, Scope `youtube.upload`) oder `--device`
  (Google erlaubt dort nur Scope `youtube`). Tokens `tokens/youtube-<lang>.json`, je Sprache ein Kanal. Testmodus = 7 Tage. `.env`: `YOUTUBE_CLIENT_ID/SECRET`.
- Tests `tests/test_youtube.py` (Mocks), Doku `docs/youtube.md` (mit Quellen). Echter Upload/Studio-Spalten DE/TR ungetestet.

## Werkstatt (`werkstatt.py`, Recht `werkstatt`, Standard aus, nicht in `RECRUIT_PERMS`, Schalter `PCL_ALLOW_WERKSTATT=1`)
- ABI-Wunsch 2026-11-04: alle KIs sollen wie am Terminal arbeiten und Werkzeuge nachruesten; jeder Antrag Mitarbeiter -> CEO -> ABI (Web + Telegram) -> zurueck.
- Stufe je Agent in `perms.werkstatt_stufe` (1 alles Antrag, 2 Std. = `W.classify` 'frei' laeuft sofort, 'antrag' = Installation/Loeschen/Pfad ausserhalb,
  3 alles frei nur mit `PCL_WERKSTATT_FREI=1`); 'verboten' (.env, tokens/, Keys, printenv) immer. `werkstatt_level(agent)` = 0 ohne Recht/Schalter.
  `classify` ist Mustererkennung, keine Sandbox (so in Doku gesagt).
- Werkzeuge `befehl`/`nachruesten` in `run_with_tools` (`werkstatt_tool`), Doku `W.doc` in `build_system`. `W.run`: PowerShell (Windows) bzw. bash,
  Argumentliste ohne shell=True, `clean_env` (ohne KEY/TOKEN/SECRET/PASSWORD, `npm_config_yes=false`), ein Befehl gleichzeitig (`W._lock`), killpg/taskkill bei Zeitlimit.
- Antrag: `approvals.kind='werkstatt'`, `data` = cmd/shell/wozu/groesse/grund/stufe(ceo|besitzer|ceo_abgelehnt)/ceo. `werkstatt_ceo` (per `_bg`) fragt `top_agent`
  per `W.ceo_prompt` (JSON weiterleiten/empfehlung), dann Telegram-Knoepfe `wa:`/`wd:`. `decide_werkstatt` (Web + Telegram, atomar) fuehrt im Hintergrund aus,
  `W.note_installed` -> `wissen/werkzeuge.md`, `werkstatt_resume` setzt die Aufgabe mit `feedback` = `WERKSTATT_MARK ...` wieder auf queued (work/review_prompt
  zeigen das als eigenen Block). Laeuft die Aufgabe noch, holt das Ende von `execute_task` es nach (`_werkstatt_notes`). Max `PCL_NACHRUEST_MAX` je Aufgabe.
- Claude/Codex: `werkstatt_cli_args` in `_call_llm` (auch im Chat): claude ohne `--tools ""`, `--tools/--allowedTools` (Stufe 1 Read/Glob/Grep, ab 2 + Bash/Edit/Write/Web),
  `--disallowedTools` .env/tokens + Installationsbefehle, Stufe 3 `--permission-mode bypassPermissions`; codex `--sandbox read-only|workspace-write` bzw. bypass, `-C`.
  cwd = Projektordner, Zeitlimit `PCL_WERKSTATT_TIMEOUT`. Gegen echte CLIs ungetestet. Tests `tests/test_werkstatt.py`, Doku `docs/werkstatt.md`.
- Nicht gebaut: Stopp-Knopf fuer laufende Befehle, Live-Protokoll eines CLI-Laufs.

## Post / Telegram
- `tasks.inbox`: `''` / `new` / `closed`, nur für oberste Aufgaben. `finish()` → `inbox_arrived()` → Telegram-Nachricht.
- `inbox_close`, `inbox_rework` (setzt feedback/prev_result, passes=0), `inbox_new_order` werden von Web-API und Telegram geteilt.
- Telegram: Long-Polling (`tg_poll`), eigener Sender-Thread (`tg_notify` ist threadsicher), `tg_msgs` mappt Nachricht→Auftrag
  für Antworten. Nur `TELEGRAM_CHAT_ID` darf steuern. Token nie loggen (`_safe`). Test: `TELEGRAM_API` auf Fake-Server setzen.

## Starten und testen
```bash
./install.sh && ./venv/bin/python app.py      # http://127.0.0.1:8787
```
Windows: `install.ps1` + `deploy/windows/hyperstead-start.bat`, Doku `docs/windows.md`. Subprozesse mit `text=True` immer `encoding="utf-8", errors="replace"` (Windows-Standard ist cp1252), `.env` mit `utf-8-sig`, `_run_cli` loest das Programm per `shutil.which` auf (`claude.cmd`). Auf echtem Windows ungetestet.
Tests: `python -m pytest -q tests` (mock-Anbieter, ohne Internet). UI-Prüfung weiter per Playwright (nicht im Repo).

## Roadmap (Reihenfolge nach Wunsch des Besitzers)
1. Betrieb stabilisieren: echte Provider-Keys testen, Tunnel (Tailscale) einrichten.
2. Heartbeat: Agenten wachen nach Zeitplan auf (Tabelle `schedules`, Worker prüft fällige Einträge).
3. Agenten können Dateien lesen; optional Web-Zugriff.
4. **Zuletzt:** Anbindung an `swarm.py` (DEXTER) als Agent, z. B. über Anbieter `webhook`/`cli`.

## Pflicht bei jedem Merge
- Nach jedem Update die README aktualisieren: Die Tabelle „Was passiert, wenn etwas fehlt“ im Abschnitt Betrieb bekommt eine Zeile für jede neue oder geänderte Datei, jeden Schlüssel oder jede Abhängigkeit. Der Besitzer verlangt das ausdrücklich.
- Jeden Text (README, Anleitungen, Antworten im Thread) vor dem Merge oder Senden auf Rechtschreibfehler prüfen. Der Besitzer verlangt das ausdrücklich.
- Die README gibt es in sechs Sprachen, je eine Datei: `README.md` (Deutsch, Hauptdatei), `README.en.md`, `README.tr.md`, `README.sr.md`, `README.bs.md`, `README.hr.md`. Jede Änderung an der README wird in allen sechs Dateien gleich umgesetzt (gleiche Abschnitte, gleiche Tabellen, gleiche Zeilen für „Was passiert, wenn etwas fehlt“). Alle Sprachdateien verlinken oben die anderen. Nach der Übersetzung auf Rechtschreibung prüfen und Anker-Links kontrollieren.
- Nur die README wird übersetzt. Dashboard, Oberfläche und Anleitungen in `docs/` bleiben Deutsch bzw. unübersetzt.

## Claude-CLI-Anmeldung
- `claude_oauth_token()` liest `tokens/claude-oauth-token.txt` (`PCL_TOKENS_DIR`), sonst `CLAUDE_CODE_OAUTH_TOKEN`; `_call_llm` gibt es per
  `_run_cli(extra_env=...)` NUR an Programme `claude*` weiter (`_run_cli` filtert sonst alle `*_TOKEN`). Anmeldefehler (`_CLAUDE_AUTH_RE`) ->
  `CLAUDE_LOGIN_HINT` + Telegram max. alle 6 h; Token-Datei aelter als 335 Tage -> Telegram taeglich. Skripte `deploy/claude-erneuern.sh`,
  `deploy/windows/claude-erneuern.ps1` (claude setup-token, Token unsichtbar einlesen). Doku `docs/claude-anmeldung.md`, Test `tests/test_claude_anmeldung.py`.
- Dateiansicht (`showFiles`): Dateien nach Ordnern der ersten Ebene gruppiert, Kästchen je Datei/Ordner + „Select all“ → `POST /api/projects/<id>/files/delete` {paths} (`delete_project_files`, keine Dot-Pfade, leere Unterordner weg); „🧹 Empty folder“ → `POST …/files/clear` {folder, confirm:true} (`clear_project_folder`, nur erste Ebene, Dot-Dateien bleiben).

## Windows-Voraussetzungen (2026-11-06, Wunsch ABI)
- `voraussetzungen.py` (nur Windows): `teile()` = Liste aller Zusatzprogramme mit `da()`/`install()` (winget, pip im venv, Downloads nach `tools/`).
  NIE ohne Rueckfrage installieren (`frage`: j/n/a/x). `install.ps1` ruft es ohne Option (fragt alles), `hyperstead-start.bat` mit `--start`
  (eine Frage, 20 s, Standard n, damit der Autostart nie haengt; mit n Abgelehntes in `.voraussetzungen-nein`). `--liste` zeigt nur.
- `win_pfade.erweitern()` (Import in agent_tools) liest PATH aus der Registry neu und haengt bekannte Ordner an (WinGet Links/Packages,
  Tesseract, Git\bin, .cargo\bin, npm, JDK, Ruby, Lua, tools\poppler), setzt TESSDATA_PREFIX auf tools\tessdata. Tests `tests/test_voraussetzungen.py`.
