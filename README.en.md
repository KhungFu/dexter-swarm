# Hyperstead

🌐 Languages: [Deutsch](README.md) · **English** · [Türkçe](README.tr.md) · [Srpski](README.sr.md) · [Bosanski](README.bs.md) · [Hrvatski](README.hr.md)

An agent team as a node editor, self-hosted, light enough for a Raspberry Pi.
Create a project, drag agents onto the canvas, connect them (boss → employee), set the AI provider, work instructions and rights per node, and assign tasks.

> The detailed guides in `docs/` are currently written in German only.

## Installation

Hyperstead is a Python program (Flask + SQLite) and runs on several systems. Several installations
can run in parallel; each has its own companies and data.

| System | Status | Guide |
| --- | --- | --- |
| Raspberry Pi / Linux (Debian, Ubuntu) | main system, full feature set | below |
| Windows 10/11 | works, without `run_code`, building Rust only without isolation via a switch, some features need extra programs | [docs/windows.md](docs/windows.md) |
| macOS | tested (works) | below (by hand) |
| Own image computer (e.g. an old laptop without a graphics card) | free images with reference images for Hyperstead | [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md) |

Moving from one computer to another: stop Hyperstead and copy `data.db`, the folder `workspace/` and `.env`
([example Pi → Windows](docs/windows.md)).

### Raspberry Pi / Linux

```bash
git clone https://github.com/KhungFu/hyperstead-neu hyperstead && cd hyperstead
./install.sh --service     # venv, dependencies, .env with a random password, systemd service
nano .env                  # enter API keys, then: sudo systemctl restart hyperstead
```

Without the service: `./install.sh`, then `./venv/bin/python app.py` → http://127.0.0.1:8787.
The login password is in `.env` (`APP_TOKEN`). Update, restart, backup: [Operations](#operations-who-does-what-where-when-how).
More features (video, OCR, compilers, browser): `./install.sh --all`.

### Windows

PowerShell in the Hyperstead folder:

```powershell
git clone https://github.com/KhungFu/hyperstead-neu hyperstead; cd hyperstead
powershell -ExecutionPolicy Bypass -File install.ps1
notepad .env
deploy\windows\hyperstead-start.bat
```

`install.ps1` then checks all prerequisites (video, voice, browser, OCR, film studio, image server, Rust, compilers), shows every missing part with its command and size and asks **before each installation** (j/n = yes/no, a = yes to all further, x = no to all further). Nothing is installed without “j”. `hyperstead-start.bat` checks again on every start and asks one question with 20 seconds to answer; without an answer Hyperstead simply starts (autostart never hangs). Only show: `venv\Scripts\python.exe voraussetzungen.py --liste`.

What is missing under Windows, autostart and running in parallel with the Pi: [docs/windows.md](docs/windows.md).
Update later: `git pull`, then restart.

### macOS (tested)

```bash
git clone https://github.com/KhungFu/hyperstead-neu hyperstead && cd hyperstead
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
cp .env.example .env       # set APP_TOKEN=<long password>, add API keys
./venv/bin/python app.py   # http://127.0.0.1:8787
```

`install.sh` is built for Debian/Ubuntu (apt), so on macOS do it by hand as above. Extra programs via Homebrew
(`brew install ffmpeg tesseract poppler`). `run_code` only exists on Linux.

### Images on your own computer

A computer on the home network (even without a graphics card, at least 8 GB RAM) can generate free images with
reference images for Hyperstead. In `.env`, keep exactly these two lines active (only one `IMAGE_PROVIDER=` line without `#`):

```
IMAGE_PROVIDER=sdcpp
SDCPP_URL=http://<IP of the image computer>:1234    # on the image computer itself: http://127.0.0.1:1234
```

Setup: [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md).

### Animated films with Blender

If Blender is installed on the computer that runs Hyperstead, the agents make cartoon films: characters with their own
voices and mouth movement, scenes, camera, subtitles, a finished film with sound (tool `film`, company template „🐶 Animationsstudio“).
If Hyperstead does not find Blender by itself, add it to `.env`:

```
BLENDER_PATH=C:\Program Files\Blender Foundation\Blender 4.2\blender.exe
```

Guide and script format (German): [docs/filmstudio.md](docs/filmstudio.md).

## Operations: who does what, where, when, how

**Who:** the owner of the computer (you) does all of this, not the agents. The commands run in the
Hyperstead folder: on the Pi in the terminal (`cd ~/hyperstead`), on Windows in PowerShell
(`cd $HOME\hyperstead`, or wherever you put the folder).

### Quick overview

| What | When | Raspberry Pi / Linux (with service) | Windows |
| --- | --- | --- | --- |
| Start | after installation, after a restart without autostart | `sudo systemctl start hyperstead` | double-click `deploy\windows\hyperstead-start.bat` (keep the window open) |
| Stop | before a move, a backup, an update | `sudo systemctl stop hyperstead` | close the start window (or press Ctrl+C in it) |
| Restart | after every change to `.env`, after an update | `sudo systemctl restart hyperstead` | close the start window, start `hyperstead-start.bat` again |
| Is it running? | when there are problems | `systemctl status hyperstead` | is the start window open? Browser: <http://127.0.0.1:8787> |
| View the log | on errors | `journalctl -u hyperstead -f` (Ctrl+C stops it) | shown in the start window |
| Update | when there is a new version (e.g. after a merged pull request) | see below | see below |
| Check | after installation, an update, new keys | `python3 selftest.py` | `python selftest.py` |
| Keys / settings | new key, other image provider | `nano .env`, then restart | `notepad .env`, then restart |
| Back up | regularly, before a move and big updates | copy `data.db`, `workspace/`, `.env` (stop first) | the same in the Hyperstead folder |

### Update (get the new version)

**Raspberry Pi / Linux**, in the terminal:

```bash
cd ~/hyperstead
git pull
./install.sh               # only needed if requirements.txt changed; .env stays unchanged
sudo systemctl restart hyperstead
python3 selftest.py llm     # quick check that the AI providers answer
```

**Windows**, in PowerShell:

1. `cd $HOME\hyperstead`
2. `git pull`
3. Only if packages changed (or when in doubt): `powershell -ExecutionPolicy Bypass -File install.ps1`
   (the existing `.env` stays unchanged).
4. Close the black start window of Hyperstead.
5. Start `deploy\windows\hyperstead-start.bat` again (double-click or type it in PowerShell).
6. Check: `python selftest.py llm`

If `git pull` says „local changes would be overwritten“, you changed a file of the program yourself.
`git stash` sets the change aside, then repeat `git pull`. Your data (`data.db`, `workspace/`, `.env`)
is never affected, because Git does not know them.

### Start automatically

- **Pi:** `./install.sh --service` sets up the service; it then starts by itself at every boot.
- **Windows:** Win+R, type `shell:startup`, and put a shortcut to `deploy\windows\hyperstead-start.bat` there
  (and to `bildrechner-start.bat`, if you use it). Windows must sign in by itself for this
  ([docs/windows.md](docs/windows.md), section 4).

### Change settings in `.env`

- Each setting appears exactly once, without `#` at the start. Lines starting with `#` are switched off. With duplicate lines
  the first one counts.
- After every change, restart Hyperstead, otherwise the old state still applies.
- Never copy keys into chats, screenshots or the repository. If a key has ended up somewhere by accident: revoke it with the provider and enter a new one.
- Then check with `selftest.py`. Single areas: `selftest.py llm`, `web`, `telegram`, `media`, `ocr`, `code`.

### Reading the self-test

- **OK:** works.
- **MISSING (missing):** optional; the line names the command to install it (on Windows the Windows command).
  Only needed if your agents use it (e.g. video, speech output, scanned PDFs).
- **ERROR (error):** something you entered does not work, usually an invalid or expired key or a service that is not
  running (e.g. the image computer). The line gives the reason.
- A single timeout at a web service is often only temporary: try again later.

### Image computer (if used)

- **Where:** on the computer that makes the images (e.g. a laptop), folder `C:\bildrechner`.
- **When:** it must run as long as agents should generate images.
- **Set up (once):** in PowerShell in the Hyperstead folder
  `powershell -ExecutionPolicy Bypass -File deploy\windows\bildrechner-einrichten.ps1` (downloads the program and the models).
- **How:** start `C:\bildrechner\bildrechner-start.bat`, keep the window open. In the `.env` of Hyperstead
  `IMAGE_PROVIDER=sdcpp` and `SDCPP_URL=...` ([guide](docs/laptop-bildrechner.md)), then restart Hyperstead.

### Film studio (if used)

- **Where:** on the computer with Blender (e.g. the laptop). The company with the `film` tool must run in **this** Hyperstead instance.
- **When:** Blender does not need to be open, Hyperstead starts it in the background for each scene and closes it again.
- **Check:** `python selftest.py film` (Windows) or `python3 selftest.py film`.
- **How long:** at 640×360 and 12 frames/s, depending on the laptop, about 1 to 5 minutes per 10 seconds of film. Blender never runs at the same time as the image computer.

### Moving (e.g. Pi → laptop)

Step by step in [docs/windows.md](docs/windows.md), „Phase 2 – Umzug“ (German). In short: stop both, copy `data.db`,
`workspace/` and `.env`, start on the new computer and check, and only then switch off the old one.
Only enter Telegram on one computer.

### What happens when something is missing

This list is extended with every change to the program. Each row says what the system does and what you have to do.

| Missing | What the system does | What you do |
| --- | --- | --- |
| `.env` | Hyperstead starts without keys and without a password, reachable only from this computer. With `HOST=0.0.0.0` the start is aborted as long as `APP_TOKEN` is empty. | `./install.sh` (Pi) or `install.ps1` (Windows) creates it with a random password. |
| Windows add-on programs (ffmpeg, Piper/edge-tts, browser, Tesseract + languages, Poppler, Blender, image server, Rust + Build Tools, Node/TypeScript, Java, Go, GCC, Git Bash, Ruby, PHP, Lua) | `install.ps1` and `hyperstead-start.bat` show the list with commands and ask before each installation. Parts declined with “n” are remembered in `.voraussetzungen-nein`: the start no longer asks, `install.ps1` asks again. If `requirements.txt` changed since the last installation, the start offers `pip install`. Hyperstead finds newly installed programs without a new window (PATH is extended at start). If the image server is not running (`IMAGE_PROVIDER=sdcpp`, local), the start offers to start it. | Answer “j” in the window or run `powershell -ExecutionPolicy Bypass -File install.ps1`. If an installation fails, the output shows the command to do it by hand. |
| `data.db` | Is created new and empty. Companies, tasks and posts are gone. | Back it up first (see Operations). Only copy back from a backup. |
| API key in `.env` | The provider is reported as MISSING in the self-test and the agents do not use it. If it is set but invalid: ERROR with HTTP 401. | Enter the key, or switch the line off with `#`. |
| Ollama not reachable or model too big | The task fails with „Ollama not reachable“ or „Not enough RAM for this model“; a missing model reports „`ollama pull …`“. If Ollama delivers nothing for `OLLAMA_TIMEOUT` seconds, the request stops with this hint, without repetition. | `systemctl status ollama`, pull a smaller model (`ollama pull qwen2.5:1.5b`) and choose it in the agent, or raise `OLLAMA_TIMEOUT`. |
| Own connection of the AI (e.g. Canva from the Claude subscription, own MCP server) | Hyperstead reads the status on every Claude call. If a connection does not work („FAILED“, „NEEDS SIGN-IN“, „NOT AVAILABLE“) or `tokens/claude-mcp.json` is broken, it is logged (`ai_link_failed`), Telegram reports it at most every 6 hours, and the CEO tells you honestly instead of pretending to have used it. Without setup everything runs as before, just without connections. | [docs/ki-verbindungen.md](docs/ki-verbindungen.md) (German): `PCL_CLAUDE_CONNECTORS=Canva` in `.env` or servers in `tokens/claude-mcp.json`, then `python selftest.py links`. |
| Images through Canva (`IMAGE_PROVIDER=canva` or Canva connector) | Hyperstead itself then creates no image. A Claude CLI agent uploads the reference image to Canva with `canva_upload` and creates the image there. Without the Canva connector, `image_generate` reports „not connected“. If another image provider fails, the error names the Canva route, and with reference images there is no free fallback image without reference any more. | [docs/ki-verbindungen.md](docs/ki-verbindungen.md) (German): `PCL_CLAUDE_CONNECTORS=Canva`, agent with provider Claude (CLI) and right `images`. If Canva shows „NOT AVAILABLE“: register Canva with `claude mcp add --scope user canva https://mcp.canva.com/mcp` (section in the guide). |
| Sound effect file in the script (`geraeusche` in the film studio) | The script check reports every missing or unsuitable file with scene and number, nothing is saved. If a sound refers to a dialogue line that does not exist, only that sound is left out. | Create the file with `sound_generate` (`AUDIO_PROVIDER=elevenlabs`) or put your own into `film/geraeusche/`, see [docs/filmstudio.md](docs/filmstudio.md) (German). |
| Atmo or music in the script (`atmo`, `musik`, `ducken` in the film studio) | If the file is missing, the script check reports scene and field, nothing is saved. Without atmo, music and sound effects, `op=check` names the silent scenes, the film is built anyway. Music and atmo get quieter under speech automatically. | Create the file with `sound_generate` (`kind` sfx or music) or put your own there; `"ducken": false` turns the ducking off, see [docs/filmstudio.md](docs/filmstudio.md). |
| `SDCPP_URL` (with `IMAGE_PROVIDER=sdcpp`) | Image requests fail with „SDCPP_URL is missing“ (SDCPP_URL missing). With `IMAGE_FALLBACK=pollinations` a free replacement image without references is made, with a note in the result. | Add the line to `.env`, restart Hyperstead. |
| Image computer not reachable (laptop off, firewall, wrong IP) | As above: error „ConnectionError“ (not reachable), with the fallback a replacement image. | Switch on the laptop, start `bildrechner-start.bat`, check the IP and the firewall. |
| `sd-server.exe` (Windows, image computer) | `bildrechner-start.bat` shows „sd-server.exe fehlt“ (missing) and starts nothing. | Run `deploy\windows\bildrechner-einrichten.ps1`. |
| Model file (Windows, image computer) | The start file names the missing file and does not start. If only the large language model (`Qwen3-4B-Q4_K_M.gguf`) is missing, it uses the smaller one if present. | Run the set-up script again; it only downloads the missing file. |
| Windows runtime `VCOMP140.DLL` | `sd-server.exe` reports „VCOMP140.DLL nicht gefunden“ (not found) and aborts. | Run the set-up script again (step 3 installs the runtime), then open the start file. |
| Firewall rule for port 1234 (Windows) | Only the Pi cannot reach the image computer. The laptop itself keeps working. | Run the command from [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md), section 4, as administrator. |
| Macro in `macros/` or login `macros/<site>.json` (with `PCL_MACROS=1`) | Without a macro the `site_macro` tool does not exist. Without a saved login the macro stops with a hint. If MagicLight or Flow change their page, `site_macro` reports ERROR and puts `<site>-fehler.png` into `output/`. The self-test (`browser`) shows MISSING. | Record the macro (again) as described in [macros/README.md](macros/README.md). |
| Unpacked ZIP (`input/<name>/`) | On upload Hyperstead safely unpacks every ZIP to `input/<name>/` (no `..` paths, links or `__MACOSX`). If the ZIP is broken or larger than `PCL_UNZIP_MAX_MB` (default 2000) unpacked, only the ZIP stays and the log shows `file_unzip_failed`. If an agent reads a ZIP without a folder (e.g. uploaded before the update), `read_file` unpacks it then. | Nothing. For very large ZIPs raise `PCL_UNZIP_MAX_MB` or upload in parts. `PCL_UNZIP_UPLOADS=0` turns unpacking off. |
| `ffmpeg`, `tesseract`, `pdftoppm`, speech output | The function is missing. Agents that need it report the error in the result. The self-test shows ERROR (Pi) or MISSING (Windows). | Install the program (commands in the self-test and in [docs/windows.md](docs/windows.md)). |
| Blender (tool `film`) | `save`, `check`, `voices` and `assemble` still work. `preview` and `render` report „Blender was not found“ (Blender not found) with a hint about `BLENDER_PATH`. The self-test shows MISSING. | Install Blender (`winget install BlenderFoundation.Blender`) or set `BLENDER_PATH` in `.env`, restart. |
| `film/film.json` (script) | `film` reports „film/film.json is missing“ (missing) and asks to save a script with `op=save` first. A faulty script is not saved, the answer lists all errors. | Nothing, the agents create it themselves. You can also write it by hand ([docs/filmstudio.md](docs/filmstudio.md)). |
| Image, music or `.blend` file named in the script | The check names scene, character and path, nothing is rendered. | Put the file into `assets/` or `input/` or fix the path in the script. |
| Clip of a scene (`film/clips/`) | `assemble` names the missing scenes and cuts nothing. If `render` stops (time limit), the finished frames are kept and the next call continues there. | Nothing, the agents call `render` again. |
| Speech output for the film | `voices`/`render` stop with „No speech output available“ (no speech output). Scenes without any dialogue still work. | As for „speech output“ above (on Windows `edge-tts` + `TTS_ENGINE=edge`). |
| `cargo` (Rust, tool `rust_project`) | The tool is not shown to the agents; `check_code` keeps checking `.rs` files if `rustc` is there. The self-test (`selftest.py rust`) shows MISSING with the install command. | Install Rust: Pi `curl https://sh.rustup.rs -sSf \| sh`, Windows `winget install Rustlang.Rustup`. Then restart Hyperstead. |
| bubblewrap when building Rust (Pi/Linux) | `rust_project` stays hidden, just like `run_code`. | `./install.sh --run` |
| `PCL_CARGO_UNSAFE=1` (Windows) | Windows has no isolation, so `rust_project` stays hidden without the switch. With the switch the laptop builds without isolation. | Only set it if you know the risk ([Rust programs](#-building-complete-rust-programs)), then restart. |
| `Cargo.toml` in the Rust folder | `rust_project` reports "Cargo.toml is missing in …" and names the files the agent has to create first. | Nothing, the agent creates them with `write_code`. |
| Internet for Rust dependencies (crates.io) | `cargo fetch` fails, nothing is built, the agent gets the error message. Dependencies already downloaded are kept in `.rust/cargo-home` and keep working. | Check the internet connection and start the task again. |
| Passing tests for the Rust package | **No** package is created ("NO PACKAGE"); the agent gets the errors with line numbers and has to fix them. Without tests the package is created with a WARNING in the result. | Nothing, the agent fixes and builds again. Send it back via the boss if it gives up. |
| Folder `.rust/` in the project (build folder) | Recreated on the next build, which then takes longer (everything is downloaded and compiled again). It is hidden and not part of the ZIP download. | Nothing. You may delete it if space runs out. |
| Telegram token or chat ID | Telegram stays off, everything else runs. The self-test shows MISSING. | Only needed if you want messages on your phone. |
| A folder or file in the project (`wissen/`, `input/`) | Folders that do not exist count as empty. The agents keep working without company knowledge. | Create or upload the file or folder in the project. |
| Deleted file or emptied folder (file view, “🗑 Delete selected” / “🧹 Empty folder”) | The files are gone for good, there is no recycle bin. The folder itself stays, the agents keep working and treat missing files as above. If a deleted file is in the screenplay or named in the task, the agent reports it as missing. | Download “⬇ Everything as ZIP” first if you still need the files, otherwise upload the file again. |
| Key of a video provider (e.g. `KLING_SECRET_KEY`, `HIGGSFIELD_API_KEY_SECRET`) | `video_generate` reports “VIDEO_PROVIDER=…, but … is missing in .env” and creates nothing; the other providers in the list keep working. The self-test shows the provider as MISSING. | Enter the key ([docs/videodienste.md](docs/videodienste.md)) or remove the provider from `VIDEO_PROVIDER`, restart. |
| Credit with the video provider | The provider answers with an error (often HTTP 402/429 or “insufficient balance”); the agent gets the text in its result. No other provider steps in. | Top up the credit, or choose another provider with `provider` or in `VIDEO_PROVIDER`. |
| `FAL_KEY` (with `VIDEO_PROVIDER=fal`, `VIDEO_AI=fal` or `AUDIO_PROVIDER=fal`) | `video_generate`, `video_ai` or `sound_generate` reports “FAL_KEY is missing” and creates nothing. | Enter the key from fal.ai, or remove the `VIDEO_AI`/`AUDIO_PROVIDER` line. |
| `ELEVENLABS_API_KEY` (better voices when needed) | Everything runs as before with the local voices. If `engine: elevenlabs` or `TTS_ENGINE=elevenlabs` is used anyway, or ElevenLabs/OpenAI fails (key, credit, internet), the local voice speaks and the result starts with “NOTE: … nicht genutzt” and the reason. In a film the line is retried with the cloud voice on the next `voices`. `TTS_FALLBACK=0` makes the task stop instead. | Put the key from elevenlabs.io into `.env` and restart. Guide: 📖 → “🎙 Voices and ElevenLabs”. |
| Credit or internet at ElevenLabs, or `OPENAI_API_KEY` (`TTS_ENGINE=openai`) | The local voice steps in and the result carries a NOTE with the HTTP code. In a film the line is tried again with the cloud voice at the next `voices`. With `TTS_FALLBACK=0` the task aborts instead. If there is no local voice either, `speak` reports "No speech output available". | Top up the credit or check the key. Install espeak-ng or Piper for the substitute voice. |
| AI of an employee newly hired by the CEO | The new one is created but gets no tasks. If the CEO plans again afterwards, the task stops with „These employees have no AI assigned yet: …“ (no AI assigned yet). In the menu **⚠ Models** he is listed as „No AI yet“. | Assign an AI in the menu ⚠ Models and reply „Weiter“ in the post. |
| Rights of an employee hired by the CEO | The system adds missing rights based on the role (list above). If no keyword matches, he only gets *read files* and can only answer with text. | Set the ticks in the agent panel or give the CEO the role more precisely. |
| Employee the CEO wants to fire or change | If the name is not in his team (typo, other team, already fired), the instruction is skipped and noted in the result. If the employee still has an open task, he stays. | Nothing, or assign it again later. |
| `video_providers.py` (program file) | The video, sound and cloud voice tools disappear for the agents; everything else keeps running. | Run `git pull` again, the file is part of the program. |
| `GITHUB_UPLOAD_TOKEN` or `GITHUB_UPLOAD_REPO` | GitHub shows as "not set up" under ☁️ Cloud and agents are not offered it as a target. Everything else keeps running. | Enter token and repo ([docs/cloud.md](docs/cloud.md), German), restart. |
| CUPS (`lp`) on the Pi, a printer or the CEO's print right | 🖨 Printer shows "CUPS missing" or only the test printer. 🖨 Print reports "No printer chosen yet" or "Printing is blocked" and sends nothing. | `./install.sh --print`, set up the printer ([docs/drucken.md](docs/drucken.md)), choose and allow it under 🖨 Printer. |
| Printer found, but no paper comes out (stopped, offline, no driver/`raw`, stuck job) | After sending, Hyperstead checks the job for a few seconds (`PCL_PRINT_CHECK_WAIT`, default 6) and reports the cause instead of "sent". 🩺 Check printer shows state, queue and driver. | Fix the cause named in the message, see the table "Testseite kommt nicht heraus" in [docs/drucken.md](docs/drucken.md) (German). |
| Pi: printer only found on the network, not set up in CUPS | The list shows "(found on the network, not set up)". Printing on it fails, Hyperstead names the cause and shows **🔧 Set up printer**. | Click **🔧 Set up printer** once (driverless, shared) or `sudo lpadmin … -m everywhere` ([docs/drucken.md](docs/drucken.md)). |
| Windows: printers of other devices are missing on this computer | Windows only lists its own printers. Hyperstead says so when there are none or only virtual ones (PDF, OneNote) and shows `Get-Printer` errors. Without PowerShell in PATH it uses the one in `System32`. | Add the printer in Windows, or enter its IP, address or e-mail address under 🖨 Printer › **Remote printers**. |
| Remote printers (IP, address, e-mail) | Under 🖨 Printer › **Remote printers** one address per line: network printer by IP/name/`ipp://` (directly via IPP, PDF or JPEG, no driver), a computer with CUPS ("Name @ address") or the printer's e-mail address (Epson Connect, HP ePrint: PDF attachment). Unreachable = "not reachable", own printers stay selectable. | E-mail needs `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` (optional `SMTP_PORT`, `SMTP_FROM`) in the `.env`, allow the sender in the cloud service ([docs/drucken.md](docs/drucken.md)). |
| Linux: printer from cups-browsed without address ("No destination host name supplied by cups-browsed") | 🩺 Check printer detects this and shows the command to set the printer up with a fixed address. | `sudo lpadmin -p Epson -E -v ipp://PRINTER-IP/ipp/print -m everywhere` |
| Windows: PowerShell slow, broken or not in PATH | The laptop's own printers come straight from the Windows print spooler (`winspool`), default printer first. Printing uses PowerShell (time limit `PCL_PRINT_WIN_TIMEOUT`, default 120 s), without PowerShell Notepad. | Nothing needed. If a printer is missing, check under Settings › Printers & scanners that Windows knows it. |
| `GDRIVE_CLIENT_ID`/`GDRIVE_CLIENT_SECRET` or `ONEDRIVE_CLIENT_ID` | The service stays "not set up", the "Sign in" button is missing. | Register the app and enter the lines ([docs/cloud.md](docs/cloud.md)), restart. |
| Sign-in at Google/Microsoft (folder `tokens/`) | The service shows "not signed in". An upload reports "not signed in yet" or "sign-in expired" and uploads nothing. | ☁️ Cloud → Sign in. When moving from Pi to laptop, simply sign in again on the laptop. |
| File over 50 MB for Telegram | Telegram does not accept it. `/datei` marks it with ⚠️ and does not send it, the agent gets a notice. | Choose Google Drive, OneDrive or GitHub as the target. |
| `cloud_upload.py` (program file) | Hyperstead does not start (import error). | Run `git pull` again, the file is part of the program. |
| `YOUTUBE_CLIENT_ID`/`YOUTUBE_CLIENT_SECRET` | Preparing and analysing keep working. Uploading reports “YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET are missing”, agents are told that no channel is signed in. | Create a Google Cloud project and add the lines ([docs/youtube.md](docs/youtube.md)), restart. |
| YouTube sign-in (`tokens/youtube-<lang>.json`) | No upload for this channel (“not signed in”). While the Google project is in testing mode the sign-in expires after 7 days (“sign-in expired”). | `python youtube_channel.py login de` (or `en`, `tr`) on the computer running Hyperstead. |
| `tzdata` (Windows only) | The schedule reports “Unknown time zone”, packages get no date. | `venv\Scripts\pip install -r requirements.txt` |
| Python packages for the self-test (`requests`, `flask` …) | `python selftest.py` (Windows) or `python3 selftest.py` (Pi) switches to the Hyperstead venv by itself. If there is no venv yet or a package is missing in it, it says which package is missing and what to do instead of a Python error (exit code 2). | Windows: `powershell -ExecutionPolicy Bypass -File install.ps1`, Pi: `./install.sh` or `./install.sh --update`. Then run `python selftest.py` again. |
| `youtube_channel.py` (program file) | Hyperstead does not start (import error). | Run `git pull` again, the file is part of the program. |
| `PCL_ALLOW_WERKSTATT=1` | The “Workshop” checkbox is grey, no agent gets `befehl` or `nachruesten`. Everything else works as before. | Add the line to `.env`, restart, tick the box for the agent ([docs/werkstatt.md](docs/werkstatt.md)). |
| A program an agent needs (e.g. Node.js, Remotion, a Python package) | With the workshop the agent files an upgrade request: the CEO checks it, you get ✅/❌ via Telegram and under ✋ Approvals. After your yes the server installs it and the task continues. Without the workshop the agent only names what is missing. | Read the request and decide. Without Telegram only on the web. |
| Node.js on the Pi, or sudo/apt requests from the workshop | The service runs without root rights (`NoNewPrivileges`). Hyperstead rejects `sudo`/`apt install` requests at once and gives the agent the way without sudo, so you never get a request that cannot work. `./install.sh --all` now installs Node.js too. | `./install.sh --node` or `bash deploy/node-ohne-sudo.sh --remotion`; install missing system libraries yourself with `sudo apt install …` ([docs/werkstatt.md](docs/werkstatt.md)). |
| The CEO's AI (for an upgrade request) | The request comes straight to you with the note “No CEO with AI” or “CEO not reachable”. | Decide yourself or assign an AI to the CEO. |
| `werkstatt.py` (program file) | Hyperstead does not start (import error). | Run `git pull` again, the file is part of the program. |
| `growth.py` (program file) | Hyperstead does not start (import error). | Run `git pull` again, the file is part of the program. |
| World of a project never chosen | The project shows the space world with its stages and terms. | Nothing to do. The Space and Atom worlds are no longer offered in the graphic menu. |
| Logo files in `static/logo/` | The sidebar and the login page show an empty image box, the browser tab shows no icon. Everything else works normally. | Run `git pull` again. The logo can be recreated with `docs/logo/logo_blender.py` ([guide](docs/logo-prompt.md), German). |
| Former world (Guild, Tycoon, Gizmo City) saved in a project | The project shows space automatically. Points, stage and ranks stay the same, only names and icons change. | Nothing to do. |
| No AI calls today (operations centre, 💶 in the bar) | Shows 0 $ or “no calls”. | Nothing to do. Costs are estimates, set your own prices with `PCL_PRICES` in `.env`. |
| Table `firm_links` (older `data.db`) | Created automatically at start, empty: city and cosmos show no collaboration yet. | Nothing. |
| Company logo `.logo.png` / `.logo.jpg` / `.logo.webp` in the project folder | The company shows no logo in city and cosmos, everything else works normally. | In the company's info window (🏙/🌌, tap the company) choose 🖼 Hochladen under „Logo“: PNG, JPEG or WebP, at most 2 MB. |
| No project yet | City and cosmos show "No company yet". | Create a company with the "＋ New project" button on the left (empty or from a template). |
| Browser stores nothing (private window) | Light/dark, the chosen graphic (space, org chart style, atom, blueprint), dragged org chart cards, expanded/collapsed sidebar categories (including the project list), motion and help mode fall back to the default on every load. | Use a normal window; the project data is not affected. |
| Agents in the blueprint lie on top of each other (e.g. all in the same spot) | The connecting lines cannot be seen. When the blueprint opens, Hyperstead arranges them once automatically and says so. | Nothing, or press “🗂 Arrange”. |
| History for the ← button (previous graphic) | The history lives only in the open tab. After reloading or in a new tab ← is grey until you switch graphics again. | Nothing to do. |
| A language other than English in the dashboard | Dashboard, agent instructions, templates and system texts are in English. What you type into fields yourself stays in your language, and the agents answer and report in the language you write in. | Let the browser translate (Chrome/Edge: right-click → “Translate”). |
| No real AI in the project (only `mock` or no provider) | Fixed notices in Telegram and the mailbox (e.g. “✅ Done”, approval notes) stay in English because nobody can translate them. Agent reports still come in your language as soon as the agents have an AI. | Give the CEO (or another agent) a real AI; from then on that AI translates the notices automatically. |
| `PCL_TRANSLATE` in `.env` (default `1`) | With `PCL_TRANSLATE=0` all fixed notices stay in English and there are no extra AI calls for translations. Without the entry, notices are translated. | Remove the line or set `PCL_TRANSLATE=1`, restart Hyperstead. |
| Your language not detected yet (fresh install or only short messages like “ok”) | Until your first longer text (about 12 letters or more, not a command), fixed notices stay in English. | Write an assignment or a chat message in your language. |
| `handover/assignment-<no>.md` in the project folder | Hyperstead creates the file at the first step of an assignment. If it was deleted, the assignment carries on, only the next model lacks the state so far. | Nothing to do. With `PCL_HANDOVER=0` in `.env` no file is written. |
| `PCL_AUTO_RESUME`, `PCL_RETRY_MIN`, `PCL_RETRY_MAX` in `.env` | Default: on, first wait 5 minutes (doubles, at most 120), at most 6 attempts. After that the task counts as failed. With `PCL_AUTO_RESUME=0` tasks fail right away on errors and after a restart, as before. | Nothing to do, or change the values in `.env` and restart Hyperstead. |
| Columns `retries` and `retry_at` (older `data.db`) | Added automatically at start. | Nothing. |
| Rust build folder `.rust/<name>/target-<version>-<id>` | Every Rust version builds in its own folder, so old build leftovers no longer cause error E0514. The old `target/` folder stays and is no longer used. | Nothing. If you need space, delete old `.rust/*/target` folders yourself. |

## Access from the internet

The app deliberately listens only on `127.0.0.1`. Instead of opening a port, you use a tunnel.
This is also needed if your mobile router does not allow incoming connections (CGNAT).

### Option A (recommended): Tailscale, private, only for your devices

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up                    # open the login link in the browser
sudo tailscale serve --bg 8787       # HTTPS address only inside your own tailnet
```

Install Tailscale on your phone/laptop too, then open the shown address `https://dexter….ts.net`.
Add to `.env`: `TRUST_PROXY=1`, then restart the service.
**Do not** use `tailscale funnel`, that would put the app on the public internet.

### Option B: Cloudflare Tunnel, public address with your own domain

```bash
# install cloudflared (see developers.cloudflare.com/cloudflare-one/connections/connect-networks)
cloudflared tunnel login
cloudflared tunnel create hyperstead
cloudflared tunnel route dns hyperstead agents.your-domain.de
# ~/.cloudflared/config.yml:  ingress: - hostname: agents.your-domain.de  service: http://127.0.0.1:8787
cloudflared tunnel run hyperstead
```

Strongly recommended in addition: put **Cloudflare Access** (e-mail login) in front.
In `.env`: `TRUST_PROXY=1`. The commands may change; in doubt, the official guide applies.

With `TRUST_PROXY=1` the app only starts if `APP_TOKEN` has at least 12 characters.

## Operation

| Action | How |
|---|---|
| Create an agent | drag the entry from the palette onto the canvas (or click it) |
| Connect | drag the lower dot of a node onto another node (= boss → employee) |
| Disconnect | click the connecting line |
| Move | drag a node; drag the background = move the view; mouse wheel = zoom |
| Settings | click a node → panel on the right |
| Assign a task | panel → tab „Aufgaben“ (tasks) |
| Approve | sidebar „Freigaben“ (approvals) |

## How the company works

A boss receives a task and **plans** (distributes sub-tasks) or does it himself. As soon as all
employees are finished, he wakes up again, **reads their reports**, returns defects with feedback or
summarises everything and reports to his own boss. This is how the result moves up through any number of levels.
The status „Waiting for team“ (waiting for team) means: the boss is waiting for his people. In the tasks tab you see the whole tree.

## Space and growth

Every project is a small **universe** that grows with its successes. Space only changes words, icons and colours
of the interface. The agents always work with clear terms (task, report, team), so their quality stays the same.

| In space | Meaning in the team |
| --- | --- |
| ☀️ Sun | top lead (e.g. the CEO) |
| 🪐 Planet | department or foreman, orbits the sun |
| 🌙 Moon | team member, orbits their own planet (anyone further down is a small moon of a moon) |
| Stages | ☄️ Asteroid → 🪐 Planet → ☀️ Solar system → ✨ Star cluster → 🌌 Galaxy |
| Agent ranks | ☄️ Comet → 🌙 Moon → 🪐 Planet → ⭐ Star |

Points are called stardust, tasks are called missions. The former worlds Guild, Tycoon and Gizmo City no longer exist; existing projects show space automatically, and points and stages are kept. The interface shows the names in German.

**Atom world:** Note: the Space and Atom views are no longer offered in the graphic menu (Classic and Modern only); this describes the drawing that is still in the code. Besides space there is a second world. If you pick ⚛️ Atom in the graphic selection, the project uses the Atom world, 🌌 Weltall switches back to space (also in the growth bar, the celebration and Telegram). Large sphere = top lead, medium spheres = team leads, small spheres = employees. Stages: ✴️ Quark → ⚛️ Atom → 🧪 Molecule → 💎 Crystal → 🧬 Cell; ranks: · Neutrino → ⚡ Electron → 🔴 Proton → 💠 Nucleon (the interface shows the German names). Points are called energy, tasks experiments. Points and stage limits are the same in both worlds. Org chart and blueprint keep the last chosen world.

**Usage:** The bar above the canvas shows the stage, progress to the next stage and the key numbers. On the right you switch between light and dark (🌓) and open the overview of stages, points and ranks with ⓘ. Each agent's rank is shown as an icon on its card.

**Solar system:** The drop-down button on the right of the bar (e.g. “Org chart: Tree ▾”) picks the graphic: three org charts, blueprint (node editor), or under Modern all companies as city, cosmos or molecules. Space is drawn in detail: a sun with rays and spots, planets with a night side, clouds or bands, moons with craters, an asteroid belt, distant galaxies and the Milky Way. Planets and moons orbit slowly, and the planets and the sun also spin on their own axis (clouds, bands and sunspots drift across the surface, the sun's ray crown turns), and at the galaxy stage the spiral in the background turns as well; when you point at one with the mouse, everything stops so you can hit it easily. A pulsing blue ring means "working", a yellow ring "waiting for your approval", a red ring "error", a dashed purple ring "waiting for its team". Tapping the sun or a planet shows the team and actions, tapping a moon opens the agent. With every stage the sky gets fuller, from star cluster on nebulae glow, and as a galaxy a spiral appears. Space stays dark even in the light theme. On the phone a list replaces the map: the sun, below it each planet with its moons. Motion is turned off when the device asks for "reduce motion".

**Org chart:** shows the team in three styles, each its own entry in the graphic menu: ⬇ Baum (tree from top to bottom, members without their own team are stacked), ➡ Gliederung (outline, one row per agent, indented by level, best on the phone) and ◎ Kreis (circle, the lead in the middle, each level a ring). Colour shows the state: green ready, blue working, yellow waiting for your approval, red error, purple waiting for the team, grey paused. Tapping opens the agent. Cards can be dragged and the lines follow; the device remembers this per project and style, “↺ Reset layout” restores the order. If you drop a card onto another one (or, in the blueprint, an agent onto another agent), Hyperstead asks first and only then moves it into that team.

**Atom:** ⚛️ shows the team as a molecular network: glossy spheres connected by rods. The large blue sphere is the top lead, medium coloured spheres are the team leads, small spheres the members. Every sphere hangs on its superior by a rod, so size and connections show the hierarchy; everything is arranged loosely and spatially like a molecular model, not in rigid rows. Every company has its own molecule: shape and colours come from the company, the large sphere carries the project colour. In the modern view, ⚛️ Molekül shows all companies as molecules side by side; partner companies are connected by a glowing rod between their leads, with sparks travelling along it (more when both are working). Tapping zooms into the molecule, every sphere opens its department and agent. The graphic stands still so you can read it calmly. As a world, the picture grows with the stage: as a quark three quarks glow in the nucleus, from molecule on neighbouring atoms are attached by bonds, from crystal an atomic lattice lies in the background, as a cell a cell wall and a DNA double helix are added. State and tapping work as in the org chart.

**English interface, back and moons:** The dashboard is in international English; other languages come from the browser's translator. The **←** button to the left of the graphic menu returns to the previous graphic, in exactly the design you were in (also back into an opened company or department). The company info card no longer has the button “📐 Firma öffnen”; tapping a name opens the agent directly and the graphic stays the same. In 🌌 Cosmos the employees are moons that orbit their planet (department); planets and suns also spin on their own axis, the moons only orbit their planet.

**Everything in English, communication in your language:** Everything Hyperstead writes itself is now in English: interface, hover hints, error messages, confirmations, instructions to the agents, company templates, tool messages and the self-test. What you enter yourself (assignments, chat, goals, names) stays in your language. The agents answer, report and write files for you in the language you write in, whether German, Turkish, Albanian, Swahili, Russian or Chinese; scheduled tasks and the inspection round also follow your latest language. Fixed notices in Telegram and the mailbox are translated into your language automatically by your CEO's AI (once per text, then from the cache). The Telegram commands are now /new, /project, /file and /help (the old German ones still work). In the graphic menu the “Classic” group shows text only, without symbols (“Org chart: Tree”, “Org chart: Outline”, “Org chart: Circle”, “Blueprint”). Folders and keys the agents already know (e.g. `wissen/`, `film/film.json` with German keys) are unchanged. The Rust package now contains `README.txt`, `TEST_REPORT.txt`, `source/` and `program/`.

**Operations centre:** 🛰 in the sidebar (or a tap on the numbers in the growth bar) shows at a glance what is running and waiting, which approvals are open, what failed in the last 7 days (with ↻ Neu), the schedules (with ▶ Jetzt), error messages and the latest events. It also shows the estimated AI costs for today and the last 7 days; today's cost also appears as 💶 in the bar. All numbers come from the existing tasks, approvals, schedules and the history, nothing is made up.

**Level-ups and controls:** When a project reaches a new stage, a short celebration shows the new stage and the next goal (Telegram sends the same message). When an agent rises in rank, a short notice appears. Under ⓘ in the bar you can turn off motion and celebration effects for this device; if the device asks for “reduce motion”, everything stays still anyway. All windows close with Esc, the sun, planets and moons in space can be used with Tab and Enter.

**Guide and help:** 📖 Guide at the top of the sidebar opens the user guide right in the dashboard (expandable chapters, with search, no download, works offline). ⓘ at the top of a window jumps to the matching chapter. Every button shows a short explanation when you point at it with the mouse. On the phone, turn on help mode in the guide: the first tap on a button explains it, the second runs it.

**Points:** delivery accepted the first time +10, after revision +5, task marked as done in the mail +20,
failed −3, rework requested −5. Stages from 0 / 100 / 300 / 700 / 1500 points. Existing projects get
their past successes counted automatically. A stage-up is announced once via Telegram.

**What the stage limits:** only how many agents the management may recruit **by itself** (8 / 12 / 18 / 25 / unlimited
in the project) and how deep (2 / 3 / 4 / 5 / full depth). You can always create anything yourself. The limit can be
switched off per project.

**Agent ranks** by their own accepted deliveries: from 0 / 5 / 20 / 60 (e.g. apprentice, journeyman, master, grandmaster).

## Agent abilities (internet, images, files)

Agents work in rounds: they request tools, the server runs them and returns the results, until they
are finished (max. `PCL_MAX_TOOL_STEPS`). Rights per agent: **research the internet**, **images**, **read project files**
(plus, as before, write files).

| Tool | What it does | Without key |
|---|---|---|
| `web_search` | web search (laws, prices, competition …) | DuckDuckGo; better: `SEARXNG_URL`, `BRAVE_API_KEY` or `TAVILY_API_KEY` |
| `fetch_url` | read a web page as text | yes |
| `browse_page` | open a page in a real browser (JavaScript runs), optionally with a screenshot the agent sees as an image | yes, needs `./install.sh --browser` |
| `image_search` / `image_save` | search freely licensed photos and save them in `assets/`, with author and licence | Openverse; optional `PEXELS_API_KEY` |
| `image_generate` | create an AI image as PNG, optionally with up to 4 reference images from the project (same characters and style across a series), format square/portrait/landscape and target path in `assets/`, `output/` or `karten/`. Right **Images** or **Media** | Pollinations (without key: no reference images; with `POLLINATIONS_API_KEY` and Pollen credit: model via `POLLINATIONS_MODEL`, with reference images); `IMAGE_STYLE` sets a fixed drawing style; others: `nvidia` (FLUX via build.nvidia.com), `cloudflare` (Workers AI, FLUX.2 klein with reference images), `hf` (Hugging Face), model each via `IMAGE_MODEL`; free with reference images on your own computer: `IMAGE_PROVIDER=sdcpp` ([guide](docs/laptop-bildrechner.md)); better `IMAGE_PROVIDER=openai` with `OPENAI_API_KEY`, `gemini`, or `openrouter` with `OPENROUTER_API_KEY` |
| `list_files` / `read_file` | read files in the project folder (e.g. colleagues' texts) | yes |

Everything created lies under `workspace/<project-id>/`. In the sidebar, **📁 Dateien** shows the files, opens `index.html`
as a web page (isolated sandbox) and downloads everything as a ZIP. The link contains a secret key. Videos and sound (MP4, WebM, MOV, MP3, WAV, OGG, M4A, FLAC) play right in the file view (▶️, box “🎬 Finished videos” for the newest film in `output/`), ⬇ downloads any single file.

**Projects and views:** In the sidebar under „Projekte“, the large button „＋ New project“ opens a window: empty project or a ready-made company from a template. Below it are the created companies under „🏢 Projects“; tapping the heading collapses or expands the list. The graphics menu at the top right has two groups: **Klassik** (the three org charts tree, outline and circle, plus the blueprint) and **Modern** (all companies as city, cosmos or molecule). Space and molecule for a single project are gone; whoever had them open last lands in the org chart. The top bar with project and growth also stays in city, cosmos and molecule, and so does the „Add agent“ bar below it (new agents go into the project selected at the top). City, cosmos and molecule can be rotated and tilted: buttons ⟲ ⟳ ⤵ ⤴ ⌂ at the bottom right, dragging with the right mouse button, or two fingers on a phone. Selecting a project on the left makes its company light up in city, cosmos and molecule while the others fade back. In the city every company is a building with its own style, and its lights go on while it is working; opening it shows one floor per hierarchy level, as deep as the company goes: management at the top floor, then the department heads, then every further level; each person has their own room, so a department with 4 people on one level has 4 rooms there in its colour; every floor lines up its rooms centred and evenly spaced, departments stay together, and the building is as wide as its fullest floor, with an org chart on the right. With success the building grows: more levels add floors, from stage 2 an annex and a roof garden appear, from stage 3 an antenna, from stage 4 a helipad. In the cosmos every company is a solar system (sun = management, planets = departments); the sun grows with the stage and the team, the planets orbit on phones too and stop under your finger, and names stay readable when you zoom out. Every company can get its own logo in the info window under „Logo“ (🖼 Hochladen, PNG/JPEG/WebP up to 2 MB): in the city it stands as a glowing sign on the roof, in the cosmos in the middle of the sun.

**Company templates** (button „＋ New project“): *Web agency*, *Accounting/tax office*, *Import/export trade* create project,
organisation chart, work instructions and rights completely. Your own companies: write a project goal („you are a …“, country,
industry), set agents and rights. The agents receive the date and the project goal and should first research things that change (laws,
prices) and name their sources.

**Tool security:** page fetches are limited to public addresses (no localhost, LAN, Tailscale,
cloud metadata; redirects are checked one by one). For the agents, web content counts as untrusted data,
but a prepared page can still influence a model: do not give agents with internet access a shell, and check results.
Agents deliberately have **no** tools for purchases, orders, payments or sending e-mail; they deliver drafts and recommendations.
Image licences (CC) often require attribution; the picture editor writes it into `bildnachweis.md`.

## Media, documents and your own files

With the right **create media & documents** (and `ffmpeg`/fonts on the Pi, see `install.sh`):

| Tool | What it can do |
|---|---|
| `video_edit` | cut a video (`trim`), join (`concat`), **slideshow animation with zoom** from images (`slideshow`, optionally with sound), overlay text/subtitles/logo, replace or mix sound, change speed, convert to GIF/WebM/MP3, extract a still frame |
| `speak` | text to speaker audio (espeak-ng offline; better: Piper; optional Edge voices or cloud voices from ElevenLabs/OpenAI via `TTS_ENGINE`), with `voice`, `pitch`, `rate` for different voices |
| `film` | **animated film with Blender**: script as JSON, characters (dog, cat, rabbit, bear, mouse, human, your own images or `.blend` characters), voices with mouth movement, movements, camera, preview image, rendering scene by scene, editing with subtitles ([guide](docs/filmstudio.md)) |
| `write_file` | with the right **write files**: creates chapters, HTML, CSV etc. immediately, so that a PDF/DOCX/EPUB can be made from them in the same task |
| `make_document` | from Markdown chapters **PDF, DOCX, EPUB or HTML** (A4/A5, cover, images, umlauts and Turkish characters); with `html` a PDF with free layout from **HTML+CSS** (rebuild templates, via WeasyPrint, loads only files from the project) |
| `video_generate` | **AI video clip** from text or a start image via 12 providers: Google Veo/Omni, OpenAI Sora, OpenRouter, Runway, Luma, **Kling**, **MiniMax Hailuo**, **Wan**, Seedance, **Higgsfield** (default MiniMax H3), fal.ai, Replicate. Off by default, switch on with `VIDEO_PROVIDER=…` + key, several separated by commas. **Costs per clip** with the provider, app subscriptions usually do not count ([guide](docs/videodienste.md), German) |
| `site_macro` | **MagicLight, Google Flow and other sites with your own account**: a browser robot (Playwright) operates the page, waits for the video and puts it into `output/`. Off by default (`PCL_MACROS=1`), you record the macros once yourself ([macros/README.md](macros/README.md)). Risk: may break the terms of service and stops working when the page changes |
| `video_ai` | AI post-processing via fal.ai: **upscale** a video, **lip sync** to a voice recording, **sound effects** for a silent video. Switch on with `VIDEO_AI=fal` + `FAL_KEY` |
| `sound_generate` | **sound effects or music** from a description (ElevenLabs or fal.ai), switch on with `AUDIO_PROVIDER` |
| `media_info` | duration, resolution, codecs |
| `download_file` | download PDFs, EPUB, Office, audio, video, ZIP from the internet into `downloads/` |
| `read_file` | reads text, Markdown, HTML, **PDF, DOCX, EPUB**, also long files in sections |
| `view_image` | **sees** images, screenshots, maps, layouts and pages of scanned PDFs (needs a model with image understanding, e.g. Claude, GPT-4o, Gemini) |

**Self-check:** if an agent creates a PDF, the server then renders it as an image (overview of all pages + page 1 large) and sends it
back to him with the duty to check every requirement of the task and fix errors before he reports (`PCL_SELF_CHECKS`, default 1, 0 = off).

**Your own files** (videos to edit, PDFs, images, layouts, texts) you upload in „📁 Files of this project“ or send
directly in the **💬 Chat** with an agent (📎 button, drag them in or paste an image, several at once). They land in
`input/` (name cleaned up, existing files are never overwritten but become `name-1.png` …, limit `PCL_MAX_UPLOAD_MB`; ZIP files are unpacked right away to `input/<name>/` so the agents can read their content); in the chat
the agent gets the **content** directly with the message (texts, PDFs, Word as text, images as images, if the model understands images;
otherwise text recognition). With **📂 aus input/** you attach files that are already there, or you simply write the file name into the message, and „Give as task“ (give as task) passes it to the team; finished results lie in `output/`, images in `assets/`. Honest limits: without `video_generate` there is **no AI video generation**
(text to video); „animation“ then means: scene images by image AI + zoom/pan + speaker + cut, or real character animation with Blender via `film`. With `video_generate`
short clips arise; longer films are put together with `video_edit op=concat`. MagicLight and Flow have no API: with `site_macro` a browser robot operates them with your account, otherwise upload videos made there to `input/`. The model behind Flow (Veo 3.1) is also available via fal: `FAL_VIDEO_MODEL=fal-ai/veo3.1/fast`. On the Raspberry Pi
ffmpeg is slow (one minute of 720p video can take several minutes), time limit `PCL_FFMPEG_TIMEOUT` (default 1 hour per step).

**Scanned PDFs and images (OCR):** `read_file` reads scans automatically via `tesseract` (`sudo apt install tesseract-ocr tesseract-ocr-deu poppler-utils`). This is slow (about 5–15 s per page on the Pi, limit `PCL_OCR_MAX_PAGES`) and can contain errors.

**Good speaker voice:** `./install.sh --piper` sets up Piper with a German voice; it is then used automatically for German texts (other languages: espeak-ng).

## Chat and templates

- **💬 Chat tab** (in the agent panel): free conversation with any agent, e.g. with the head of the *Gedankenwerkstatt*, for philosophising,
  developing ideas and questioning. „📋 Give as task“ hands the conversation to the agent and his team; the result comes back as a post.
  The chat runs without tools.
- **Company templates** (🏢): Web agency, Accounting/tax office, Import/export trade, **Animation agency**, **Book publisher/content agency**,
  **Thought workshop**, **Research office** (finds and reads PDFs). When founding, you choose the model for the head and the employees.

## Post and Telegram

As soon as a **top-level task** (the one you gave to an agent, usually the CEO) is finished, failed or
blocked, a post is ready for you: sidebar „📬 Mail“ and, if set up, a Telegram message with the
type, the task, team figures and the result. The chain of rights and reports underneath runs as before.
In the post you can tick messages (one by one or „Select all“) and remove them with „🗑 Delete selected“;
„🧹 Empty mailbox“ deletes all of them after a confirmation. Only the post is deleted, tasks, files and history stay.
The sidebar is grouped into collapsible categories (Tagesgeschäft, Team & KI, Dateien & Verbindungen, Auswertung, Projekte).
The list of created companies under „🏢 Projects (number)“ can be collapsed as well; „＋ New project“ always stays visible.
Every device remembers which categories are open.

**Set up Telegram (about 2 minutes):**
1. In Telegram: `@BotFather` → `/newbot` → copy the token → `.env`: `TELEGRAM_BOT_TOKEN=…`
2. `sudo systemctl restart hyperstead`, write `/start` to the new bot → it tells you your chat ID.
3. `.env`: enter `TELEGRAM_CHAT_ID=…`, restart the service. In the web under „Post“ there is a test message.

**Using Telegram:**

| You do | Result |
|---|---|
| Just write text | new task to the head of the chosen project (`@Name Text` = a specific agent) |
| **Reply** to a post message | the task is reworked with your text as instruction |
| Button ✅ or reply „ok“ | task marked as done |
| Send a file, photo, album, video or voice message | lands in `input/` of the chosen project; the caption becomes the task (when replying to a post: for revision); without text the file goes to your next task. Telegram bots may only download files up to 20 MB, larger ones: upload on the web |
| `/post`, `/status`, `/ok <no.>`, `/neu <Text>`, `/projekt [no.]` | overview or short commands |
| `/datei [search word]` | sends you a file from the selected project (newest as buttons, a single match comes right away; up to 50 MB) |

The app only polls Telegram outwards, no port is opened (works behind CGNAT too). Only the chat ID from
`.env` may give commands; use a private chat, not a group. Approvals for shell commands deliberately do
**not** go through Telegram; there only a note arrives.

## Rights per agent

- **Delegate**: may hand tasks to *direct* employees (up to `PCL_MAX_DEPTH` levels, default 8).
  Optionally they start automatically, otherwise you start them yourself.
- **Judge results**: the boss may return work with feedback for revision (max. 2 rounds per employee).
- **Read**: bosses always see the reports of their employees; no separate right is needed for this.
- **Write files**: only in `workspace/<project-id>/`; paths outside are refused.
- **Run code** (default off): `run_code` starts Python, JavaScript, Bash, Ruby, PHP or Lua in a sandbox, see below.
  This includes `rust_project`: build and test Rust programs and deliver a finished package ([Rust programs](#-building-complete-rust-programs)).
- **Upload to the cloud** (off by default): finished files to GitHub, Google Drive, OneDrive or to you via Telegram, always only after your approval ([☁️ Cloud upload](#️-cloud-upload-github-google-drive-onedrive-telegram)).
- **Manage YouTube** (off by default): prepares titles, descriptions, keywords, hashtags and the schedule as files and evaluates CSV exports from YouTube Studio. Each video is only uploaded after your approval ([docs/youtube.md](docs/youtube.md)).
- **Suggest shell**: only if the server has `PCL_ALLOW_SHELL=1`, and then always only after approval.
- **Workshop** (off by default, only with `PCL_ALLOW_WERKSTATT=1`): works with real commands in the project folder and requests missing programs from you through the CEO ([docs/werkstatt.md](docs/werkstatt.md), German). A CEO cannot pass this right on.
- **Pause**: blocks all new tasks of the agent.

The rights are checked **on the server**. If a model writes a forbidden action into its
answer, it is ignored and logged in the history.

## AI providers and model choice

For each agent you choose **provider and model** (panel → settings). The app fetches the model list live from the provider;
with **▶ Test** you check key and model immediately. This is how you set the right model per role: the strongest for bosses
(planning, checking, thinking), good text or code models for employees, fast cheap ones for simple work.

| Provider | Key in `.env` | Note |
|---|---|---|
| Claude (Anthropic) | `ANTHROPIC_API_KEY` | Sonnet, Haiku, Opus … selectable per agent |
| ChatGPT (OpenAI) | `OPENAI_API_KEY` | |
| OpenRouter | `OPENROUTER_API_KEY` | one key for hundreds of models (Claude, GPT, Gemini, DeepSeek, Qwen, Llama …) |
| Groq, Gemini, DeepSeek, Qwen | `GROQ_API_KEY`, `GEMINI_API_KEY`, … | several keys separated by commas = rotation when a limit is hit |
| Mistral, NVIDIA NIM, Together, Perplexity | `MISTRAL_API_KEY`, `NVIDIA_API_KEY`, `TOGETHER_API_KEY`, `PERPLEXITY_API_KEY` | Perplexity models (`sonar`) search the web themselves |
| Hugging Face, Cloudflare Workers AI | `HF_TOKEN` or `CF_ACCOUNT_ID` + `CF_API_TOKEN` | small free quotas |
| Ollama | – | local models on the Pi |
| Claude (CLI, your subscription) / ChatGPT (Codex CLI, your subscription) | – | built in: `claude -p --tools "" --strict-mcp-config --no-session-persistence` (Claude without its own tools, connectors only on request via [docs/ki-verbindungen.md](docs/ki-verbindungen.md); the work instruction replaces the Claude Code system prompt) or `codex exec --skip-git-repo-check --ephemeral -` (Codex runs in a read-only sandbox by itself), model in the drop-down (Claude: sonnet/opus/haiku); needs `PCL_ALLOW_CLI=1` and the signed-in program on the Pi |
| CLI agent | – | a command that reads the prompt from stdin, e.g. `claude -p --model sonnet`; needs `PCL_ALLOW_CLI=1` |

**Important:** A web login (OAuth, „subscription“) of ChatGPT or Claude cannot be used cleanly as an API; taking over
web sessions violates the terms of use. Ways: the provider's **API key** (billed per use, not the chat subscription) or the
**CLI agent** with the official CLI, signed in once. The app has no budget: with paid APIs and many tool rounds
costs can arise; you see the tokens per agent on the node.

## Security

- Login page with a signed cookie (7 days, `HttpOnly`, `SameSite=Strict`, `Secure` behind HTTPS).
- After 5 wrong passwords a 10-minute lock per IP; all attempts are in the audit log.
- Writing API calls need their own header (CSRF protection), plus CSP and further headers.
- Shell and CLI agents are **off** by default. Anyone who knows the password and has set `PCL_ALLOW_SHELL=1`
  can approve commands with the rights of the app user. `workspace/` is the working directory, but **no sandbox**.
- `.env`, database and work folders are in `.gitignore`. Keys never belong in the repository.
- For trading bots (NEXUS): never let agents trade without human approval.

## Company knowledge and memory

- **🧠 Company knowledge** (sidebar): what all agents of a project should always know (company, customers, style, prices, rules). It is stored in
  `wissen/firmenwissen.md` in the project folder. All `.md`/`.txt` files in `wissen/` go into every task and into the chat (together up to
  `PCL_KNOWLEDGE_CHARS`, default 8000 characters); other documents there (PDF, Word …) the agents see as a list and read when needed.
- **Memory per agent**: at the end of a task an agent can remember up to 5 lasting facts (preferences, decisions, customers,
  what worked). They are shown in the agent panel under „🧠 Memory“ (memory); you can change or clear them. Limit `PCL_MEMORY_CHARS`
  (4000); the oldest entries drop out first. Every new note is in the audit log.

## Goals, approvals, usage

- **🎯 Goals**: goals and sub-goals per project. When assigning a task you optionally choose the goal; delegated tasks inherit it.
  Bosses see the goals with progress in the prompt, the CEO's inspection round reports it. Tick off = reached.
- **Ask first** (window ✋ Approvals, per project, default off): *Approve the plan of the top boss* holds a new task
  until you approve the distribution plan; *Approve team changes* („Teamänderungen freigeben“) holds the CEO's hiring, firing and changing of employees. Approve/reject also via a
  Telegram button. Rejected = the task lands as ❌ in the post; your reply to it makes the boss plan again.
  Shell approvals still only go through the web.
- **📊 Usage & costs**: calls, tokens and estimated costs per project, agent and model (today, 7, 30 days). No limit.
  Subscription CLIs and Ollama count as 0 $; from `PCL_ABO_WARN_5H` subscription calls in 5 hours (default 150, 0 = off) a Telegram warning arrives.
  Prices are rough estimates; your own via `PCL_PRICES='{"sonnet": 5}'` (US$ per 1 million tokens, part of the model name).

## Tests

```bash
./venv/bin/pip install pytest && ./venv/bin/python -m pytest -q tests
```
Runs without internet and without keys (provider `mock`, own database).

## 🔌 Connections (webhooks)

- **Outgoing:** in the window 🔌 Connections you enter addresses (n8n, Zapier, Make, your own service; also `http://127.0.0.1:…` on the Pi),
  with a description for the agents and optional headers. Secrets belong in `.env` and are used as `${NAME}`.
  Agents with the right **„May use connections“** (may use connections) call them with the tool `call_connection`; the agent cannot change
  the address or headers, it only sends data. **„Only call after my approval“** (only after my approval, default on) puts every call first under ✋ Approvals.
  **„Bei Post benachrichtigen“** (notify on post) sends every finished result of a top-level task as JSON to the address. Time limit `PCL_CONN_TIMEOUT` (30 s).
- **Incoming:** switch on „Aufträge von außen“ (tasks from outside); then `POST /hook/<project>/<key>` with `{"text": "…", "agent": "optional"}`
  accepts a task for the boss (e.g. from n8n, iOS shortcuts or DEXTER). No login; protected only by the key in the address.
  „New key“ (new key) invalidates the old address. It is only reachable as far as Hyperstead itself is (e.g. only in the tailnet).

## ☁️ Cloud upload (GitHub, Google Drive, OneDrive, Telegram)

- **Setup:** credentials in `.env` (`GITHUB_UPLOAD_TOKEN` + `GITHUB_UPLOAD_REPO`, `GDRIVE_CLIENT_ID` + `GDRIVE_CLIENT_SECRET`,
  `ONEDRIVE_CLIENT_ID`), step by step in [docs/cloud.md](docs/cloud.md) (German). For Google and Microsoft you then sign in in the
  **☁️ Cloud** window: it shows a code that you enter on your phone on the Google or Microsoft page (works without HTTPS).
  The sign-in is stored in `tokens/` next to `.env`, never in the database.
- **Target folder:** per project and service in the ☁️ Cloud window (default `Hyperstead/<project name>`). Agents may only choose a
  subfolder below it, e.g. when you name one in the task.
- **Upload yourself:** 📁 Files → ☁️ next to the file → choose target and folder. You get the link.
- **Agents:** permission **"May upload to the cloud"** (only you set it). Tool `cloud_upload`; every upload waits under ✋ Approvals,
  plus a Telegram message. After the upload the link is in the task.
- **Setup with the CEO:** ask the top boss in 💬 Chat, e.g. "Help me set up GitHub". It knows the current status of each service and the guide and walks you through step by step. You never write tokens into the chat, you enter them in `.env` yourself.
- **Telegram:** `/datei` sends you files up to 50 MB on your phone, only when you click or approve it.
- GitHub: up to 50 MB as a file in the repo, larger ones as an attachment to the release `paperclip-ablage` (up to 2 GB). Google Drive: only
  folders and files that Hyperstead created itself (scope `drive.file`). OneDrive: any folder. Only tested against simulated services.

## ▶️ YouTube channel

- **What Hyperstead does:** the agent with the permission **“May manage YouTube”** fills `youtube/kanal.json` (title, description, keywords, hashtags per episode and language) and builds one package per video in `youtube/packages/`, the schedule `youtube/schedule.csv` and the review list `youtube/REVIEW.md`. 2 to 3 episodes per week at the start.
- **Uploading:** only through the official YouTube Data API and only after your approval **per video** (✋ Approvals). Always private, YouTube makes it public at the planned time. No browser script, no automatic sign-in.
- **What you do:** create the channels, a Google Cloud project with `YOUTUBE_CLIENT_ID`/`YOUTUBE_CLIENT_SECRET`, and once per channel `python youtube_channel.py login de|en|tr`. In testing mode the sign-in expires after 7 days.
- **Analysis:** upload a CSV export from YouTube Studio, the agent writes `youtube/reports/analysis-<date>.md`. Hyperstead never fetches numbers itself and never downloads other people's videos.
- Guide with sources and limits: [docs/youtube.md](docs/youtube.md) (German). Only tested against simulated responses.

## 🖨 Printing evening reports

The 👑 CEO inspection writes an evening report at closing time. In 📬 Mail and in the CEO's tasks it has a **🖨 Print** button: one click, a short confirmation, then it goes to the printer. Choose the printer under **🖨 Printer** in the sidebar (Pi: network printer via CUPS, `./install.sh --print`; Windows: shared printer under Printers & scanners). In the same window the CEO allows or blocks printing (right "May print evening reports"). The **Testdrucker (Datei)** only saves the printout as a text file in `workspace/.druck/`. Guide: [docs/drucken.md](docs/drucken.md) (German).

**Right printer?** In the 🖨 Printer window choose a printer and click **🧾 Testseite drucken** (print test page). The page names the printer, computer and time and contains umlauts. If it comes out of the right printer, click **Speichern** (save). The test page alone saves nothing and needs no print right from the CEO.

## 🌐 Real browser and ▶ run code

- **Browser** (`./install.sh --browser`, installs Playwright + Chromium, about 400 MB, 64-bit system only): agents with the right
  „Internet recherchieren“ get `browse_page`. The page runs with JavaScript; the agent gets the visible text, the links and
  on request a screenshot (it sees it as with `view_image`; `save` puts it in `assets/screenshots/`). Every request of the page
  (scripts, frames, XHR, WebSockets) must go to a public address; LAN/localhost is blocked, WebRTC and downloads are off.
  Only one browser at a time (RAM), time limit `PCL_BROWSER_TIMEOUT` (30 s). Own Chromium: `PCL_BROWSER_PATH`, off: `PCL_BROWSER=0`.
- **Run code** (`./install.sh --run`, installs bubblewrap): the right „May run code“ (may run code, default off) gives `run_code`.
  The script runs sealed off: **no internet**, only `/usr` and the project folder (read-only under `/projekt`) are visible,
  no `.env`, no database, no home. What the script writes into its work directory lands in `output/run/<time>/`
  (max. 50 files/50 MB). Limits: `PCL_RUN_TIMEOUT` (60 s), `PCL_RUN_MEM_MB` (1024). It runs the system's Python/Node,
  so only packages installed via apt (e.g. `sudo apt install python3-pandas python3-matplotlib`). Off globally: `PCL_ALLOW_RUN=0`.
  Check: `python3 selftest.py run browser`.

## 🦀 Building complete Rust programs

Give an agent with the rights **„May program“**, **„May write files“** and **„May run code“** (may program, write files, run code) a task like
"Write me a Rust program that …, with tests, and deliver the finished package". The agent then works from A to Z:

1. With `write_code` it creates a Cargo project, e.g. `rust/rechner/Cargo.toml` and `rust/rechner/src/main.rs` with tests (`#[test]`).
2. `rust_project` with `op=test` downloads the dependencies from crates.io, builds the program and runs the tests.
   Errors come back with file and line, the agent fixes them and tests again.
3. `op=package` tests once more, builds the release version and stores **`output/<name>.zip`**. Inside: `program/` (the finished
   program), `source/` (source code with `Cargo.lock`), `TEST_REPORT.txt` and `README.txt`. A package is only created if all tests pass.

You get the package in the inbox or under **📁 Dateien** (single file or in the project ZIP). More commands: `op=build`, `op=run` (with `args`, `stdin`).

- **For which system?** The program in `program/` fits the computer Hyperstead runs on: from the Pi a Linux program (ARM),
  from the Windows laptop an `.exe`. For another system run `cargo build --release` yourself in the `source/` folder.
- **Isolation (Pi/Linux):** Building, testing and running happen in bubblewrap like `run_code`: no internet, no `.env`, no home,
  only the project's build folder `.rust/` is writable. Only `cargo fetch` (downloads dependencies, runs nothing) has internet.
  Cargo settings (`.cargo/`) and `rust-toolchain` files from the project are not used.
- **Windows:** Without bubblewrap the tool stays off. With `PCL_CARGO_UNSAFE=1` in `.env` the laptop builds **without isolation**: the agents'
  code (tests, `build.rs`) then runs with your rights and could read or change files on the laptop. It does not get API keys in its
  environment. Only switch it on if you trust the agents and their models.
- **Installing Rust:** Pi `curl https://sh.rustup.rs -sSf | sh` (newer than `apt install cargo`), Windows `winget install Rustlang.Rustup`
  and include the "Visual Studio Build Tools (C++)" in the installer. Then restart Hyperstead and run `selftest.py rust`.
- **Limits:** `PCL_CARGO_TIMEOUT` (900 s per step), `PCL_CARGO_MEM_MB` (3072, Linux only), `PCL_CARGO_JOBS` (2), only one Rust build
  at a time. The first build on the Pi takes long, after that cargo only rebuilds what changed. An agent has `PCL_MAX_TOOL_STEPS`
  (default 6) tool rounds per run; for bigger programs a higher value helps, e.g. 12. Off: `PCL_CARGO=0`.

## 🛠 Workshop: agents upgrade themselves

With the **“Workshop”** right an agent works like on a real computer, for every AI and in every company. Claude (subscription CLI)
gets its Claude Code tools in the project folder, Codex its own, all API AIs and Ollama the `befehl` tool. If a program is missing,
the agent files an **upgrade request**: the CEO checks it, you confirm with the Telegram button or under ✋ Approvals, then the
server installs exactly that command and the task continues. What is installed is listed in `wissen/werkzeuge.md`.

- **Switch on:** `PCL_ALLOW_WERKSTATT=1` in `.env`, restart, tick the box for the agent and choose a level.
- **Levels:** 1 = every command asks, 2 = work in the project is free, installing and deleting ask (default), 3 = everything free
  (only with `PCL_WERKSTATT_FREI=1`). Credentials (`.env`, tokens, keys) are always blocked.
- **Caution:** commands run without isolation with your user rights. Level 2 recognises installations by their form, it is not a sandbox.
- Everything else, including Remotion and troubleshooting: [docs/werkstatt.md](docs/werkstatt.md) (German).

## Parallel work

Up to `PCL_WORKERS` tasks run at the same time (default 2, at most 6), e.g. several employees of one boss or tasks
of different projects. An agent never works on two tasks at once, and at most one Ollama task runs at a time
(RAM on the Pi). With subscription CLIs (Claude, Codex) parallel calls hit the subscription limit faster; then set `PCL_WORKERS=1`.

## Limits of this version

- No automatic heartbeat by schedule (tasks start manually or by delegation).
- No text-to-video AI, no scanned/image PDFs (OCR), no hiring of new agents by the CEO on his own (you create the organisation chart).
- The real browser (`browse_page`) reads pages but does not click and does not fill in forms (no logins, no purchases). The DuckDuckGo search without key can be limited or changed.
- No budget: tokens and estimated costs are only shown (📊). The round limits (revisions, check passes, depth) prevent endless loops.
- Sessions are simple signed cookies; a single device cannot be signed out specifically
  (changing the password invalidates all sessions).


## Self-test

After installation and entering the keys, `python selftest.py` (Windows) or `python3 selftest.py` (Pi) checks everything real that could not be tested without internet:
web search, reading pages, image search and image generator, SSRF protection, every AI provider with a mini request (incl. Ollama), Telegram
(bot token and test message to your chat ID), ffmpeg, speech output, PDF with umlauts, OCR. Single groups:
`selftest.py web | llm | telegram | media | ocr | rust | film`. Each line shows OK, MISSING (optional) or ERROR with a concrete note.

You do not need to know the venv path: on Windows `python selftest.py` is enough, on the Pi `python3 selftest.py`. Started with the normal system Python, the self-test restarts itself with `venv\Scripts\python.exe` (Windows) or `./venv/bin/python` (Pi) and prints “(using Hyperstead venv: …)”. Without a venv it tells you which install command to run. The old way `venv\Scripts\python.exe selftest.py` still works.

## Ollama (local models)

Provider „Ollama (lokal)“: no key needed, the model list comes directly from Ollama (`ollama pull qwen2.5:1.5b`). In the dialog „Firma aus Vorlage“
there are the buttons „Everything local (Ollama)“ (everything local) and „Only employees local (Ollama)“ (only employees local); otherwise you choose Ollama per agent. If Ollama runs on another computer
(e.g. the laptop), set `OLLAMA_URL` to its address. Small models (3B) are slow on the Pi and often keep the tool protocol
poorly; for bosses a strong model, locally rather for simple employees or the chat.

**Long answers (Pi):** Hyperstead asks Ollama with streaming. As long as the model is writing, nothing is cut off, even if the answer takes an hour.
`OLLAMA_TIMEOUT` (default 1800 s) is only the waiting time **without new data**, e.g. while Ollama loads the model and reads the task;
`OLLAMA_MAX_TIME` (default 7200 s, 0 = no limit) limits the total time. An aborted Ollama request is not repeated.
While an AI is writing, the dashboard shows „⏳ Agent · Ollama · 4:12 min · 380 Zeichen“ at the bottom left. The chat waits in the background,
you can close the window; the answer is in the history afterwards.

**Little RAM (≈ 2 GB free):** `qwen2.5:3b` needs about 2.5 GB with context and does not fit. `qwen2.5:1.5b` fits well
(download ≈ 1 GB, in RAM ≈ 1.3–1.6 GB, understands German, Turkish and English); even smaller `gemma3:1b` (≈ 0.8 GB download, ≈ 1.1 GB RAM).
For Ollama itself (`sudo systemctl edit ollama`): `Environment="OLLAMA_CONTEXT_LENGTH=4096"`, `"OLLAMA_NUM_PARALLEL=1"`, `"OLLAMA_MAX_LOADED_MODELS=1"`.
On a Pi 4 expect a few words per second and several minutes before the first word (long system prompts).

## Claude and ChatGPT via your subscription (CLI instead of API key)

In `.env`: `PCL_ALLOW_CLI=1`. You install the programs yourself on the Pi and sign in once (manufacturers' guides:
Claude Code `claude`, OpenAI Codex `codex`; sign-in with your subscription). Then „Claude (CLI, your subscription)“ and „ChatGPT (Codex CLI, your subscription)“
appear in all provider lists. The server calls them without a shell, in an empty folder and **without our API keys in the environment**
(otherwise `claude` would bill the API key instead of the subscription). Limits: slower than the API (program start per answer), subscription limits apply
(many agents = quickly at the limit), and the CLI programs have their own tools – adjust the command if needed via `PCL_CLI_CLAUDE` / `PCL_CLI_CODEX`.


**Tools of the AI itself (Canva, Drive, own MCP servers):** normally Claude and Codex run without their connectors.
If you put `PCL_CLAUDE_CONNECTORS=Canva` into `.env` (connectors of your claude.ai subscription) or add own MCP servers to
`tokens/claude-mcp.json`, all Claude CLI agents get exactly these connections. Codex uses the servers from `~/.codex/config.toml`.
The CEO sees in its prompt which connection works and reports errors. Credentials live only in these files, never in the chat.
Images: if you mention an image in the chat („reference image“, „photo“ …) without 📎, the newest image from `input/` is attached automatically.
Details: [docs/ki-verbindungen.md](docs/ki-verbindungen.md) (German).

## Model gone? Switch agents

Hyperstead checks every 6 hours (`PCL_MODEL_CHECK_HOURS`) whether the agents' models still exist at the provider, and also notices when a call reports „model not found“. Then a Telegram message arrives, the task fails with a clear note, and in the menu **⚠ Models** you switch all affected agents to another model with one click.

## Large teams

A boss can have any number of employees. In the boss's panel (settings) you select all of them under **Direct reports** (subordinate employees) with tick boxes and save the assignment. Alternatively: drag the lower dot of the boss onto an employee. The button **🗂 Arrange** (arrange) creates the whole organisation chart (groups of 6 or more employees in rows of 5).

## CEO assembles his team himself

The CEO from the palette has the right **„May build its own team“** (may assemble his team himself, `recruit`). If he has no employees yet and gets a task, he analyses it and creates employees with role, work instruction and reporting lines (up to 20, also department heads with their own team). The new ones have **no AI yet**: you assign them in the menu **⚠ Models** (all at once) or per agent in the settings, and then reply in the **Post** to the task (e.g. „Weiter“ = continue). After that the CEO distributes the work as usual. The CEO can give the new ones only web, images, read/write files, media and programming, never shell.

**Even when the team already exists**, a CEO with this right may adapt his team to your tasks and conditions with every task:
- **Hire**: more employees, as above without AI. You get a Telegram message and assign them an AI. They only get work from the next task or after your „Weiter“.
- **Fire**: only employees below him, never himself or agents outside his team. The fired person's people move up one level. Anyone who still has an open task is not fired.
- **Change**: role, work instruction and rights (only those named above) of employees below him.

**Rights to match the role**: The CEO should give everyone exactly the rights their work needs. If he forgets some, the system adds them from name, role and work instruction, e.g. research → *web*, images/illustration/graphics/design → *images* + *write files*, video/sound/voice/PDF/layout → *media* + *write files*, author/text/proofreading → *write files*, programming/website → *programming* + *write files*. If he changes an employee's role, the rights are set again to match. Shell, running code, connections and publishing he never gives; only you tick those.

If you want to see every team change beforehand, tick *Teamänderungen freigeben* (approve team changes) in the **Freigaben** window. Without the tick at the CEO he may do none of this. Daily tasks (schedule, inspection round) never change the team.

## Handover: continue after an abort or a model change
Every assignment gets the file `handover/assignment-<no>.md` in the project folder. After every step Hyperstead writes into it who worked (agent, provider, model), which tools ran with which result, the result and the next step (`next_step`). At the top it says where the work happens: the project folder, Git repositories in it with their address, and existing `STAND.md` or `HANDOVER.md` files.

- If a run stops with an error (quota used up, provider unreachable, crash), the task stays open and continues automatically: after 5, 10, 20 … minutes, at most 6 times. Telegram reports this once.
- If you give the agent another model (agent → settings, "⚠ Models" or group change), it continues right away. Failed top-level assignments of the last 7 days are then picked up again too.
- After a restart of Hyperstead, interrupted tasks continue right away.
- The next model receives the state from the file with the instruction to continue there and not to do anything twice. The CEO inspection round lists waiting tasks under "STOPPED BY AN ERROR".
- Tip: if a repository with its own `STAND.md` is in the project folder (e.g. `git clone https://github.com/KhungFu/swarm` in the company's folder), it is named at the top of the file and the agents read it first.

## Opening hours and daily tasks

Sidebar **🕘 Schedule** (schedule): for each project set start of work, end of work and working days. For each employee you can create **daily tasks** (fixed time, at start of work or at end of work, on chosen weekdays), e.g. „every day at 15:00 check the website“. The result comes into the view „Post“ like every post (and via Telegram). If the last task of a schedule is still running, it is not started twice; if the Pi was off at the time, up to 6 hours are caught up.
At the start of work the company takes up unfinished tasks again (not started ones start, failed top-level tasks are retried up to `PCL_MAX_RESUMES`=2 times). Optionally the company rests completely outside opening hours. The time is that of the Pi; if it is wrong, set `PCL_TZ=Europe/Vienna` in `.env`.

## CEO inspection round

In the window **🕘 Schedule** the **👑 Set up CEO inspection** (CEO inspection round) sets up a daily inspection round of the top boss (default: at end of work; further times via „New daily task“ + tick *Kontrollgang*). The system attaches a **status report** with facts: per employee today started/finished/failed/open, starts outside opening hours, open tasks without a start of work, employees without AI, unfinished tasks and whether the daily tasks ran. The CEO assesses this, distributes follow-up tasks to his team if needed and writes an inspection report into the post. „📋 View status report“ (view status report) shows the facts without the CEO.

## Project folder

Each project has a **folder with its name** under `workspace/` (e.g. `workspace/Buchverlag-Content-Agentur/`, umlauts are transcribed). It stays the same when the project is renamed and is **never deleted when a project is deleted**. If you create a new project with the same name, it takes over the existing folder with its files. Old number folders (`workspace/1`, `workspace/2` …) are renamed automatically to the project name at start.

## Publish a web page

In the window **📁 Files of this project** the files are sorted by folder (`input/`, `output/`, `www/`, `wissen/` …). Every file has a checkbox, every folder has one for “everything in it”, and at the top there is “Select all”; **🗑 Delete selected** deletes all ticked files after asking first (subfolders left empty, e.g. from an unpacked ZIP, disappear too). **🧹 Empty folder** next to each folder deletes everything in it after asking first; the folder itself stays. Hidden folders (`.rust/`, `.tmp-*`) are never touched. Deleted files are gone for good.

In the window **📁 Files of this project** there is **🚀 Publish website** (publish). Only the folder `www/` in the project folder is published (`www/index.html`, plus CSS, images … with relative paths); everything else in the project (notes, `output/`, `input/`, dotfiles, symlinks to the outside) stays invisible. If there is no `www/` folder, the `index.html` of the project folder is served as before (without `input/` and hidden files). The page runs permanently on its own port (from 8800, `PCL_SITE_PORT_BASE`), by default only on the Pi itself: `http://127.0.0.1:8800/`. For access on the network set `PCL_SITE_HOST=0.0.0.0` in `.env`. Agents with the right „May propose the website for publishing“ (may propose the web page for publication) can request an approval for „publish“; only your click under **Freigaben** puts the page online. Changes by the agents are visible immediately; after a restart the page runs again automatically. For the open internet a reverse proxy with HTTPS belongs in front (e.g. Caddy), not the small server.
