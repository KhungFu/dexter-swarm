#!/usr/bin/env bash
# Hyperstead Installer (Raspberry Pi / Debian / Ubuntu / MX Linux)
#   ./install.sh            -> venv + Abhaengigkeiten + .env mit zufaelligem Passwort
#   ./install.sh --service  -> zusaetzlich systemd-Dienst einrichten und starten (braucht sudo)
#   ./install.sh --piper    -> zusaetzlich Piper (gute deutsche Offline-Stimme) einrichten
#   ./install.sh --system   -> fehlende Systemprogramme fuer Video, Sprache, OCR, PDF-Schriften per apt installieren (sudo)
#   ./install.sh --code     -> Compiler/Pruefer fuer das Recht "Programmieren" per apt installieren (sudo, ca. 1,5 GB)
#   ./install.sh --browser  -> echter Browser (Chromium ueber Playwright) fuer Seiten mit JavaScript (ca. 400 MB)
#   ./install.sh --run      -> bubblewrap fuer das Recht "Code ausfuehren" (abgeschottet, ohne Internet)
#   ./install.sh --print    -> CUPS-Programme (lp, lpstat) zum Drucken der Abendberichte auf einem Netzwerkdrucker
#   ./install.sh --all      -> alles oben zusammen (system + code + piper + browser + run + print + service)
#   Optionen sind kombinierbar. Danach pruefen:  ./venv/bin/python selftest.py
set -euo pipefail
cd "$(dirname "$0")"
DIR="$(pwd)"
OPT=" $* "
case "$OPT" in *" --all "*) OPT="$OPT --system --code --piper --browser --run --print --service ";; esac
has() { case "$OPT" in *" $1 "*) return 0;; esac; return 1; }

command -v python3 >/dev/null || { echo "python3 fehlt: sudo apt install python3 python3-venv"; exit 1; }
[ -d venv ] || python3 -m venv venv || { echo "Tipp: sudo apt install python3-venv"; exit 1; }
./venv/bin/pip install -q --upgrade pip
./venv/bin/pip install -q -r requirements.txt
./venv/bin/pip install -q "weasyprint>=60" || echo "Hinweis: WeasyPrint (HTML -> PDF) liess sich nicht installieren, make_document mit Markdown geht trotzdem."
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
    sudo apt-get update -qq && sudo apt-get install -y $MISSING
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
    sudo apt-get update -qq && sudo apt-get install -y $CMISS
  else
    echo "Fuer das Recht 'Programmieren' (Code pruefen/kompilieren) fehlen:$CMISS  -> ./install.sh --code"
  fi
fi

# Drucken der Abendberichte (Knopf 🖨 Drucken): CUPS-Befehle lp/lpstat
if ! command -v lp >/dev/null; then
  if has --print; then
    sudo apt-get update -qq && sudo apt-get install -y cups cups-client
    echo "Netzwerkdrucker einrichten: siehe docs/drucken.md (z. B. sudo lpadmin -p Buero -E -v ipp://DRUCKER-IP/ipp/print -m everywhere)"
  else
    echo "Zum Drucken der Abendberichte fehlt CUPS  -> ./install.sh --print"
  fi
fi

# Code ausfuehren (Recht "run_code"): bubblewrap schottet jedes Skript ab (kein Netz, nur /usr + Projekt lesbar)
if ! command -v bwrap >/dev/null; then
  if has --run; then
    sudo apt-get update -qq && sudo apt-get install -y bubblewrap
  else
    echo "Fuer das Recht 'Code ausfuehren' fehlt bubblewrap  -> ./install.sh --run"
  fi
fi

# Echter Browser fuer browse_page: Playwright + Chromium (nur 64-Bit; sonst PCL_BROWSER_PATH=/usr/bin/chromium in .env)
if has --browser; then
  echo "Browser wird eingerichtet (Playwright + Chromium, ca. 400 MB) ..."
  if ./venv/bin/pip install -q playwright; then
    sudo ./venv/bin/python -m playwright install-deps chromium || echo "Hinweis: Systembibliotheken fuer Chromium bitte pruefen (playwright install-deps)."
    ./venv/bin/python -m playwright install chromium \
      || echo "Chromium von Playwright nicht verfuegbar. Alternative: sudo apt install chromium und in .env PCL_BROWSER_PATH=/usr/bin/chromium"
  else
    echo "Playwright liess sich nicht installieren (32-Bit-System?). browse_page bleibt aus, fetch_url funktioniert weiter."
  fi
fi

# Piper: gute Offline-Stimme (deutsch). Optional:  ./install.sh --piper
if has --piper; then
  echo "Piper-Sprachausgabe wird eingerichtet (ca. 100 MB) ..."
  ./venv/bin/pip install -q piper-tts
  mkdir -p models/piper
  ./venv/bin/python -m piper.download_voices de_DE-thorsten-medium --download-dir models/piper \
    && echo "Piper fertig: Stimme in models/piper/ (wird automatisch genutzt)." \
    || echo "Stimme konnte nicht geladen werden (Internet?). Erneut versuchen: ./install.sh --piper"
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
else
  echo
  echo "Manuell starten:   ./venv/bin/python app.py     (http://127.0.0.1:8787)"
  echo "Als Dienst:        ./install.sh --service"
fi
