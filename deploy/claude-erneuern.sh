#!/usr/bin/env bash
# Claude-CLI (dein Abo) fuer Hyperstead pruefen, aktualisieren und bei Bedarf neu anmelden (Raspberry Pi / Linux).
#
# Aufruf im Hyperstead-Ordner, als DERSELBE Benutzer, unter dem Hyperstead laeuft (nicht mit sudo):
#   ./deploy/claude-erneuern.sh             pruefen, aktualisieren, bei Bedarf neu anmelden
#   ./deploy/claude-erneuern.sh --pruefen   nur pruefen (z. B. fuer cron), Exitcode 0 = ok, 1 = Anmeldung noetig, 2 = claude fehlt
#   ./deploy/claude-erneuern.sh --neu       sofort ein neues Langzeit-Token holen (z. B. kurz vor Ablauf)
#
# Das Langzeit-Token aus "claude setup-token" gilt ein Jahr. Es landet in tokens/claude-oauth-token.txt (nur fuer dich lesbar).
# Hyperstead liest die Datei bei jedem Aufruf, ein Neustart ist nicht noetig.
set -u
cd "$(dirname "$0")/.." || exit 1
TOKDIR="${PCL_TOKENS_DIR:-$PWD/tokens}"
TOKFILE="$TOKDIR/claude-oauth-token.txt"
export PATH="$HOME/.local/bin:$PATH"
MODUS="${1:-}"

schritt() { [ "$MODUS" = "--pruefen" ] || printf '\n== %s\n' "$1"; }
ok() { [ "$MODUS" = "--pruefen" ] || printf '   ok: %s\n' "$1"; }

if [ "$(id -u)" = "0" ]; then
  echo "Bitte nicht mit sudo/root starten: claude meldet sich je Benutzer an. Als der Benutzer starten, unter dem Hyperstead laeuft."
  exit 1
fi

teste() {
  # Wie Hyperstead: ohne API-Keys in der Umgebung (sonst rechnet claude ueber den Key statt ueber das Abo ab)
  local envs=(env -u ANTHROPIC_API_KEY -u ANTHROPIC_AUTH_TOKEN)
  if [ -s "$TOKFILE" ]; then
    envs+=("CLAUDE_CODE_OAUTH_TOKEN=$(tr -d '\r\n ' < "$TOKFILE")")
  fi
  ANTWORT="$(cd /tmp && echo "Antworte nur mit dem Wort OK" | timeout 180 "${envs[@]}" claude -p --strict-mcp-config --no-session-persistence --model haiku 2>&1)"
  local rc=$?
  [ $rc -eq 0 ] && echo "$ANTWORT" | grep -qi "ok"
}

token_alter() {
  [ -s "$TOKFILE" ] || return 0
  local tage=$(( ( $(date +%s) - $(stat -c %Y "$TOKFILE") ) / 86400 ))
  ok "Langzeit-Token ist $tage Tage alt (gilt 365 Tage, Hyperstead warnt per Telegram 30 Tage vorher)"
}

# 1. Ist claude installiert?
schritt "1/4 Claude-CLI suchen"
if ! command -v claude >/dev/null 2>&1; then
  [ "$MODUS" = "--pruefen" ] && exit 2
  echo "   claude ist nicht installiert."
  read -rp "   Jetzt mit dem offiziellen Installer installieren (curl -fsSL https://claude.ai/install.sh | bash)? [j/N] " a
  case "$a" in
    j|J|y|Y) curl -fsSL https://claude.ai/install.sh | bash || { echo "Installation fehlgeschlagen."; exit 2; } ;;
    *) echo "Abgebrochen."; exit 2 ;;
  esac
  hash -r
  command -v claude >/dev/null 2>&1 || { echo "claude nach der Installation nicht gefunden. Neue Shell oeffnen und erneut starten."; exit 2; }
fi
ok "$(command -v claude), Version $(claude --version 2>/dev/null | head -1)"

# 2. Aktualisieren (alte Versionen kennen manche Schalter nicht)
if [ "$MODUS" != "--pruefen" ]; then
  schritt "2/4 Aktualisieren"
  if claude update 2>&1 | tail -3; then
    ok "Version jetzt $(claude --version 2>/dev/null | head -1)"
  else
    echo "   Update ging nicht. Bei einer npm-Installation: sudo npm install -g @anthropic-ai/claude-code@latest"
    echo "   oder auf den eigenen Installer umsteigen: claude install"
  fi
fi

# 3. Funktioniert claude -p?
schritt "3/4 claude -p testen (wie Hyperstead)"
if [ "$MODUS" != "--neu" ] && teste; then
  ok "claude -p antwortet"
  token_alter
  [ "$MODUS" = "--pruefen" ] || echo -e "\nAlles in Ordnung. Nichts zu tun."
  exit 0
fi
[ "$MODUS" = "--pruefen" ] && { echo "claude -p geht nicht: $(echo "$ANTWORT" | tail -2)"; exit 1; }
[ "$MODUS" = "--neu" ] || { echo "   claude -p geht nicht. Meldung:"; echo "$ANTWORT" | tail -5 | sed 's/^/     /'; }

# 4. Neu anmelden: Langzeit-Token holen (das kann nur der Mensch, im Browser)
schritt "4/4 Neu anmelden (Langzeit-Token, 1 Jahr)"
cat <<'TXT'
   Gleich startet "claude setup-token". Es zeigt einen Link.
   - Link am Handy oder PC oeffnen, mit deinem Claude-Konto (Pro/Max) anmelden und "Autorisieren" klicken.
   - Den angezeigten Code hier einfuegen und Enter druecken.
   - Am Ende zeigt claude ein Token, das mit sk-ant-oat01- beginnt. Dieses Token kopieren.
   Das Token NIEMANDEM schicken und nirgends hochladen, auch nicht in einen Chat.
TXT
read -rp "   Weiter mit Enter ... " _
claude setup-token || echo "   claude setup-token meldete einen Fehler. Du kannst es erneut versuchen."
echo
read -rsp "   Token einfuegen (die Eingabe bleibt unsichtbar) und Enter: " TOK; echo
TOK="$(printf '%s' "$TOK" | tr -d '\r\n ')"
case "$TOK" in
  sk-ant-*) ;;
  *) echo "   Das sieht nicht wie ein Claude-Token aus (beginnt nicht mit sk-ant-). Nichts gespeichert."; exit 1 ;;
esac
mkdir -p "$TOKDIR"
chmod 700 "$TOKDIR"
( umask 077; printf '%s\n' "$TOK" > "$TOKFILE" )
chmod 600 "$TOKFILE"
unset TOK
ok "gespeichert in $TOKFILE (nur fuer dich lesbar)"

if teste; then
  ok "claude -p antwortet mit dem neuen Token"
  echo -e "\nFertig. Hyperstead nutzt das Token ab dem naechsten Aufruf, ohne Neustart."
  exit 0
fi
echo "   Auch mit dem neuen Token kommt keine Antwort:"
echo "$ANTWORT" | tail -5 | sed 's/^/     /'
echo "   Pruefe Internet und Abo (claude.ai -> Einstellungen) und starte das Skript erneut."
exit 1
