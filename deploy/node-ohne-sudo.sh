#!/usr/bin/env bash
# Node.js (LTS) OHNE sudo in den eigenen Benutzerordner installieren, z. B. fuer Remotion auf dem Raspberry Pi.
#
#   bash deploy/node-ohne-sudo.sh            -> neuestes Node.js LTS nach ~/.local/node, Links node/npm/npx in ~/.local/bin
#   bash deploy/node-ohne-sudo.sh --remotion -> zusaetzlich pruefen, ob die Systembibliotheken fuer Remotions Chrome da sind
#   NODE_VERSION=v22.11.0 bash deploy/node-ohne-sudo.sh  -> bestimmte Version statt der neuesten LTS
#
# Als DERSELBE Benutzer starten, unter dem Hyperstead laeuft (nicht mit sudo). Der Dienst hat ~/.local/bin schon im PATH.
# Braucht nur curl (oder wget), tar und python3. Laedt von nodejs.org und prueft die SHA256-Pruefsumme.
set -euo pipefail

if [ "$(id -u)" = "0" ]; then
  echo "Bitte nicht als root/mit sudo starten: Node.js soll im Ordner des Hyperstead-Benutzers landen."; exit 1
fi

case "$(uname -m)" in
  aarch64|arm64) ARCH=arm64 ;;
  armv7l|armv8l) ARCH=armv7l ;;
  x86_64|amd64)  ARCH=x64 ;;
  *) echo "Unbekannte Prozessorart $(uname -m): bitte Node.js selbst installieren."; exit 1 ;;
esac
# Ein 64-Bit-Kernel mit 32-Bit-System meldet aarch64, kann aber keine arm64-Programme starten
if [ "$ARCH" = arm64 ] && [ "$(getconf LONG_BIT 2>/dev/null || echo 64)" = "32" ]; then ARCH=armv7l; fi

fetch() {  # fetch URL ZIEL
  if command -v curl >/dev/null; then curl -fsSL --retry 3 -o "$2" "$1"; else wget -q -O "$2" "$1"; fi
}

BASE="https://nodejs.org/dist"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

VER="${NODE_VERSION:-}"
if [ -z "$VER" ]; then
  fetch "$BASE/index.json" "$TMP/index.json"
  VER="$(python3 - "$TMP/index.json" "linux-$ARCH" <<'PY'
import json, sys
rel = json.load(open(sys.argv[1]))
for r in rel:  # neueste zuerst
    if r.get("lts") and sys.argv[2] in r.get("files", []):
        print(r["version"]); break
PY
)"
fi
[ -n "$VER" ] || { echo "Keine Node.js-LTS fuer linux-$ARCH gefunden. Bei 32-Bit-Systemen: 64-Bit-Raspberry-Pi-OS installieren."; exit 1; }

NAME="node-$VER-linux-$ARCH"
echo "Lade $NAME von nodejs.org ..."
fetch "$BASE/$VER/$NAME.tar.xz" "$TMP/$NAME.tar.xz"
fetch "$BASE/$VER/SHASUMS256.txt" "$TMP/SHASUMS256.txt"
( cd "$TMP" && grep " $NAME.tar.xz\$" SHASUMS256.txt | sha256sum -c - >/dev/null ) \
  || { echo "Pruefsumme stimmt nicht, Abbruch."; exit 1; }

mkdir -p "$HOME/.local/bin"
rm -rf "$HOME/.local/$NAME"
tar -xJf "$TMP/$NAME.tar.xz" -C "$HOME/.local"
ln -sfn "$HOME/.local/$NAME" "$HOME/.local/node"
for b in node npm npx corepack; do
  [ -e "$HOME/.local/node/bin/$b" ] && ln -sfn "$HOME/.local/node/bin/$b" "$HOME/.local/bin/$b"
done

if ! "$HOME/.local/bin/node" --version >/dev/null 2>&1; then
  echo "node startet nicht (falsche Prozessorart oder Bibliothek fehlt):"; "$HOME/.local/bin/node" --version || true; exit 1
fi
echo "Fertig: node $("$HOME/.local/bin/node" --version), npm $("$HOME/.local/bin/npm" --version) in ~/.local/bin"
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *)
  echo "Hinweis: ~/.local/bin ist in DIESEM Terminal nicht im PATH. Einmal ausfuehren:"
  echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc && source ~/.bashrc" ;;
esac

case " $* " in *" --remotion "*)
  # Remotion rendert mit einem eigenen Chrome (Headless Shell). Der braucht diese Systembibliotheken.
  LIBS="libnss3 libdbus-1-3 libatk1.0-0 libgbm1 libasound2 libxrandr2 libxkbcommon0 libxfixes3 libxcomposite1 libxdamage1 libatk-bridge2.0-0 libpango-1.0-0 libcairo2 libcups2"
  MISS=""
  for l in $LIBS; do
    dpkg -s "$l" >/dev/null 2>&1 || dpkg -s "${l}t64" >/dev/null 2>&1 || MISS="$MISS $l"
  done
  if [ "$ARCH" != arm64 ] && [ "$ARCH" != x64 ]; then
    echo "WARNUNG: Remotion braucht ein 64-Bit-System (arm64 oder x64). Auf $ARCH gibt es keinen passenden Chrome."
  fi
  if [ -n "$MISS" ]; then
    echo "Fuer Remotions Chrome fehlen Systembibliotheken. Das geht nur mit sudo, also einmal SELBST im Terminal:"
    echo "  sudo apt install$MISS"
  else
    echo "Systembibliotheken fuer Remotions Chrome sind da."
  fi ;;
esac
