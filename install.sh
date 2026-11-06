#!/usr/bin/env bash
# Hyperstead Installer (Raspberry Pi / Debian / Ubuntu / MX Linux)
#   ./install.sh            -> venv + Abhaengigkeiten + .env mit zufaelligem Passwort, dazu automatisch
#                              Browser (Chromium), Piper-Stimme und Rust (cargo). Schon Vorhandenes wird uebersprungen.
#   ./install.sh --update   -> neue Version holen (git pull) und ALLES aktualisieren: Python-Pakete, Browser, Piper,
#                              Rust (rustup update), Node.js (falls per --node installiert), danach Dienst neu starten
#   ./install.sh --minimal  -> nur das Noetigste, ohne Browser, Piper und Rust
#   ./install.sh --service  -> zusaetzlich systemd-Dienst einrichten und starten (braucht sudo)
#   ./install.sh --system   -> fehlende Systemprogramme fuer Video, Sprache, OCR, PDF-Schriften per apt installieren (sudo)
#   ./install.sh --code     -> Compiler/Pruefer fuer das Recht "Programmieren" per apt installieren (sudo, ca. 1,5 GB)
#   ./install.sh --run      -> bubblewrap fuer das Recht "Code ausfuehren" (abgeschottet, ohne Internet)
#   ./install.sh --node     -> Node.js LTS ohne sudo nach ~/.local (fuer Remotion & Co., deploy/node-ohne-sudo.sh --remotion)
#   ./install.sh --print    -> CUPS-Programme (lp, lpstat) zum Drucken der Abendberichte auf einem Netzwerkdrucker
#   ./install.sh --all      -> alles oben zusammen (system + code + run + print + service, dazu Browser, Piper, Rust)
#   Optionen sind kombinierbar. Danach pruefen:  ./venv/bin/python selftest.py
#   Nicht mit sudo starten: wo sudo noetig ist, fragt das Skript selbst danach.
set -euo pipefail
cd "$(dirname "$0")"
DIR="$(pwd)"
OPT=" $* "
case "$OPT" in *" --all "*) OPT="$OPT --system --code --run --print --service ";; esac
has() { case "$OPT" in *" $1 "*) return 0;; esac; return 1; }

# --update: neue Version holen und danach das NEUE install.sh mit denselben Optionen starten
if has --update && ! has --nach-pull; then
  if [ -d .git ]; then
    echo "Neue Version holen (git pull) ..."
    git pull --ff-only || { echo "git pull ging nicht. Eigene Aenderungen? Dann: git stash  und danach erneut ./install.sh --update"; exit 1; }
  fi
  exec bash "$0" "$@" --nach-pull
fi
# Standard (Wunsch ABI 2026-11-06): Browser, Piper und Rust gehoeren zur Installation. --minimal laesst sie weg.
has --minimal || OPT="$OPT --browser --piper --rust "
UPD=""; if has --update; then UPD="--upgrade"; fi
# Befehle mit apt bekommen kein stdin: sonst "verschluckt" apt/needrestart Zeilen, die man danach ins Terminal eingefuegt hat

command -v python3 >/dev/null || { echo "python3 fehlt: sudo apt install python3 python3-venv"; exit 1; }
[ -d venv ] || python3 -m venv venv || { echo "Tipp: sudo apt install python3-venv"; exit 1; }
./venv/bin/pip install -q --upgrade pip
./venv/bin/pip install -q $UPD -r requirements.txt
./venv/bin/pip install -q $UPD "weasyprint>=60" || echo "Hinweis: WeasyPrint (HTML -> PDF) liess sich nicht installieren, make_document mit Markdown geht trotzdem."
echo "Abhaengigkeiten installiert."
# Systemprogramme fuer Video/Sprache/Schriften (optional, aber noetig fuer Medien-Agenten)
MISSING=""
command -v ffmpeg >/dev/null || MISSING="$MISSING ffmpeg"
command -v espeak-ng >/dev/null || MISSING="$MISSING espeak-ng"
command -v tesseract >/dev/null || MISSING="$MISSING tesseract-ocr tesseract-ocr-deu tesseract-ocr-tur poppler-utils"
command -v tesseract >/dev/null && ! tesseract --list-langs 2>/dev/null | grep -qx deu && MISSING="$MISSING tesseract-ocr-deu"
command -v tesseract >/dev/null && ! tesseract --list-langs 2>/dev/null | grep -qx tur && MISSING="$MISSING tesseract-ocr-tur"
command -v pdftoppm >/dev/null || case "$MISSING" in *poppler-utils*) ;; *) MISSING="$MISSING poppler-utils";; esac
fc-list 2>/dev/null | grep -qi dejavu || MISSING="$MISSING fonts-dejavu-core"
ldconfig -p 2>/dev/null | grep -q libpangoft2-1.0 || MISSING="$MISSING libpango-1.0-0 libpangoft2-1.0-0"
if [ -n "$MISSING" ]; then
  if has --system; then
    echo "Installiere Systemprogramme:$MISSING"
    sudo apt-get update -qq && sudo apt-get install -y $MISSING </dev/null
  else
    echo "Fuer Video, Sprache, OCR (gescannte PDFs) und Sonderzeichen in PDFs empfohlen:  ./install.sh --system  (oder: sudo apt install$MISSING)"
  fi
fi

# Programmieren (Recht "code"): Pruefer/Compiler je Sprache. Python und Bash sind immer da.
# Befehl -> Debian-Paket (Raspberry Pi OS / Debian / Ubuntu)
CODE_PKGS="node:nodejs tsc:node-typescript javac:default-jdk-headless rustc:rustc cargo:cargo gofmt:golang-go gcc:gcc g++:g++ ruby:ruby php:php-cli luac:lua5.4"
CMISS=""
for e in $CODE_PKGS; do command -v "${e%%:*}" >/dev/null || CMISS="$CMISS ${e#*:}"; done
if [ -n "$CMISS" ]; then
  if has --code; then
    echo "Installiere Programmiersprachen:$CMISS"
    sudo apt-get update -qq && sudo apt-get install -y $CMISS </dev/null
  else
    echo "Fuer das Recht 'Programmieren' (Code pruefen/kompilieren) fehlen:$CMISS  -> ./install.sh --code"
  fi
fi

# Drucken der Abendberichte (Knopf 🖨 Drucken): CUPS-Befehle lp/lpstat
if ! command -v lp >/dev/null; then
  if has --print; then
    sudo apt-get update -qq && sudo apt-get install -y cups cups-client </dev/null
    echo "Netzwerkdrucker einrichten: siehe docs/drucken.md (z. B. sudo lpadmin -p Buero -E -v ipp://DRUCKER-IP/ipp/print -m everywhere)"
  else
    echo "Zum Drucken der Abendberichte fehlt CUPS  -> ./install.sh --print"
  fi
fi

# Code ausfuehren (Recht "run_code"): bubblewrap schottet jedes Skript ab (kein Netz, nur /usr + Projekt lesbar)
if ! command -v bwrap >/dev/null; then
  if has --run; then
    sudo apt-get update -qq && sudo apt-get install -y bubblewrap </dev/null
  else
    echo "Fuer das Recht 'Code ausfuehren' fehlt bubblewrap  -> ./install.sh --run"
  fi
fi

# Echter Browser fuer browse_page: Playwright + Chromium (nur 64-Bit; sonst PCL_BROWSER_PATH=/usr/bin/chromium in .env)
browser_da() {
  ./venv/bin/python - <<'PY' 2>/dev/null
import os, sys
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    sys.exit(0 if os.path.exists(p.chromium.executable_path) else 1)
PY
}
# Reihenfolge: PCL_BROWSER_PATH aus .env > Chromium von Playwright > Chromium vom System (nichts herunterladen) > Chromium laden
if has --browser; then
  if ./venv/bin/pip install -q $UPD playwright; then
    ENV_CHROMIUM="$(sed -n 's/^PCL_BROWSER_PATH=//p' .env 2>/dev/null | tail -n1)"
    for c in chromium chromium-browser; do command -v "$c" >/dev/null && { SYS_CHROMIUM="$(command -v "$c")"; break; }; done
    if [ -n "$ENV_CHROMIUM" ] && [ -x "$ENV_CHROMIUM" ]; then
      echo "Browser bereit: $ENV_CHROMIUM (PCL_BROWSER_PATH, Aktualisierung ueber apt)."; SYS_CHROMIUM=""
    elif browser_da; then
      # Eigenes Chromium von Playwright: bei --update auf die passende Version bringen
      if has --update; then ./venv/bin/python -m playwright install chromium </dev/null || echo "Chromium-Update ging nicht (Internet?), die alte Version bleibt."; fi
      echo "Browser bereit (Chromium von Playwright)."; SYS_CHROMIUM=""
    elif [ -n "${SYS_CHROMIUM:-}" ]; then
      echo "Browser bereit: Chromium vom System $SYS_CHROMIUM (wird als PCL_BROWSER_PATH in .env eingetragen, kein Download)."
    else
      echo "Browser wird eingerichtet (Playwright + Chromium, ca. 400 MB) ..."
      sudo ./venv/bin/python -m playwright install-deps chromium </dev/null || echo "Hinweis: Systembibliotheken fuer Chromium bitte pruefen (playwright install-deps)."
      ./venv/bin/python -m playwright install chromium </dev/null || true
      if browser_da; then echo "Browser bereit (Chromium von Playwright)."
      else echo "WARNUNG: Chromium fehlt, browse_page bleibt aus. Abhilfe: sudo apt install chromium, danach ./install.sh erneut."; fi
    fi
  else
    echo "Playwright liess sich nicht installieren (32-Bit-System?). browse_page bleibt aus, fetch_url funktioniert weiter."
  fi
fi

# Node.js ohne sudo (Werkstatt/Remotion). Optional:  ./install.sh --node
# Bei --update wird ein vorhandenes ~/.local/node auf die neueste LTS gebracht
if has --node || { has --update && [ -x "$HOME/.local/node/bin/node" ]; }; then
  bash deploy/node-ohne-sudo.sh --remotion || echo "Node.js-Installation fehlgeschlagen, siehe docs/werkstatt.md (Remotion auf dem Raspberry Pi)."
fi

# Piper: gute Offline-Stimme (deutsch). Standard, abschalten mit --minimal
if has --piper; then
  if ./venv/bin/pip install -q $UPD piper-tts; then
    mkdir -p models/piper
    if ls models/piper/*.onnx >/dev/null 2>&1; then
      echo "Piper bereit: $(basename "$(ls models/piper/*.onnx | head -n1)")"
    else
      echo "Piper-Stimme wird geladen (ca. 100 MB) ..."
      ./venv/bin/python -m piper.download_voices de_DE-thorsten-medium --download-dir models/piper \
        && echo "Piper fertig: Stimme in models/piper/ (wird automatisch genutzt)." \
        || echo "Stimme konnte nicht geladen werden (Internet?). Erneut versuchen: ./install.sh"
    fi
  else
    echo "Piper liess sich nicht installieren, die Sprachausgabe nutzt espeak-ng."
  fi
fi

# Rust (cargo) fuer das Werkzeug rust_project: rustup OHNE sudo nach ~/.cargo. Hyperstead findet cargo dort auch ohne PATH.
if has --rust; then
  CB="${CARGO_HOME:-$HOME/.cargo}/bin"
  if [ "$(id -u)" = "0" ]; then
    echo "Rust uebersprungen: install.sh bitte als normaler Benutzer starten (nicht mit sudo), sonst landet Rust bei root."
  elif [ -x "$CB/rustup" ]; then
    if has --update; then
      echo "Rust aktualisieren (rustup update) ..."
      "$CB/rustup" update stable </dev/null || echo "rustup update ging nicht (Internet?). Rust bleibt auf der alten Version."
    fi
    echo "Rust bereit: $("$CB/cargo" --version 2>/dev/null || echo cargo)"
  elif command -v cargo >/dev/null || [ -x "$CB/cargo" ]; then
    echo "Rust bereit (cargo vom System, Aktualisierung ueber apt)."
  elif ! command -v curl >/dev/null; then
    echo "Fuer Rust fehlt curl: sudo apt install curl, danach ./install.sh erneut."
  else
    echo "Rust wird eingerichtet (rustup nach ~/.cargo, ohne sudo, ca. 500 MB) ..."
    if curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal; then
      echo "Rust fertig: $("$CB/cargo" --version 2>/dev/null || echo cargo). Neues Terminal oeffnen, damit cargo dort im PATH ist."
    else
      echo "Rust-Installation fehlgeschlagen (Internet?). Erneut versuchen: ./install.sh"
    fi
  fi
fi

if [ ! -f .env ]; then
  cp .env.example .env
  PW="$(./venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(18))')"
  sed -i "s|^APP_TOKEN=.*|APP_TOKEN=${PW}|" .env
  chmod 600 .env
  echo
  echo "============================================================"
  echo " .env angelegt. Dein Login-Passwort (jetzt notieren):"
  echo "   ${PW}"
  echo " API-Keys eintragen:  nano .env"
  echo "============================================================"
else
  echo ".env existiert bereits - unveraendert gelassen."
fi
if [ -n "${SYS_CHROMIUM:-}" ] && ! grep -q '^PCL_BROWSER_PATH=' .env; then
  printf '\n# Chromium vom System (install.sh, Playwright hatte keins)\nPCL_BROWSER_PATH=%s\n' "$SYS_CHROMIUM" >> .env
fi

if has --service; then
  # Umzug vom alten Dienstnamen (PaperclipLite) auf hyperstead: alten Dienst stoppen und entfernen
  if [ -f /etc/systemd/system/paperclip-lite.service ]; then
    echo "Alter Dienst paperclip-lite gefunden - wird durch hyperstead ersetzt."
    sudo systemctl disable --now paperclip-lite || true
    sudo rm -f /etc/systemd/system/paperclip-lite.service
  fi
  sed -e "s|__USER__|$(id -un)|g" -e "s|__DIR__|${DIR}|g" -e "s|__HOME__|${HOME}|g" deploy/hyperstead.service \
    | sudo tee /etc/systemd/system/hyperstead.service >/dev/null
  sudo systemctl daemon-reload
  sudo systemctl enable --now hyperstead
  sleep 2
  systemctl --no-pager --lines=5 status hyperstead || true
  echo "Dienst laeuft. Logs: journalctl -u hyperstead -f"
elif has --update; then
  # Laufenden Dienst neu starten, damit die neue Version gilt (auf aelteren Pis heisst er noch paperclip-lite)
  RESTARTED=""
  for svc in hyperstead paperclip-lite; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
      echo "Dienst $svc wird neu gestartet ..."
      sudo systemctl restart "$svc" </dev/null && RESTARTED="$svc" || echo "Neustart ging nicht: sudo systemctl restart $svc"
      break
    fi
  done
  [ -n "$RESTARTED" ] || echo "Kein laufender Dienst gefunden. Hyperstead selbst neu starten (Startfenster schliessen und neu starten)."
  echo
  echo "Update fertig. Pruefen:  ./venv/bin/python selftest.py"
else
  echo
  echo "Manuell starten:   ./venv/bin/python app.py     (http://127.0.0.1:8787)"
  echo "Als Dienst:        ./install.sh --service"
fi
