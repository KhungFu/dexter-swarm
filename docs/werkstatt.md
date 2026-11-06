# 🛠 Werkstatt: Agenten arbeiten wie an einem echten Rechner

Mit der Werkstatt arbeitet ein Agent so, als würdest du selbst vor Claude Code oder einem Terminal sitzen. Er führt Befehle
im Projektordner aus, testet, rendert und rüstet fehlende Programme nach, zum Beispiel Remotion, Python-Pakete oder ein
Programm per winget. Das gilt für **alle KIs** und **alle Firmen**, nicht nur für das Animationsstudio.

Jede Installation läuft über einen **Nachrüst-Antrag**: Der Mitarbeiter fragt den CEO, der CEO prüft und legt dir den Antrag vor,
du bestätigst per **Telegram-Knopf** oder im **Web unter ✋ Freigaben**. Danach installiert der Server genau diesen Befehl, der CEO
meldet das Ergebnis zurück und der Mitarbeiter macht mit seiner Aufgabe weiter.

## Einschalten

1. In der `.env` eintragen und Hyperstead neu starten:
   ```
   PCL_ALLOW_WERKSTATT=1
   ```
2. Im Agenten-Fenster beim gewünschten Agenten **„Werkstatt: arbeitet wie an einem echten Rechner“** anhaken, Stufe wählen, speichern.
   Das Recht kann nur der Besitzer vergeben. Ein CEO kann es neuen Mitarbeitern nicht mitgeben.
3. Für Telegram-Knöpfe muss Telegram eingerichtet sein (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`). Ohne Telegram geht alles über das Web.

## Wie jede KI arbeitet

| KI im Agenten | So arbeitet sie in der Werkstatt |
|---|---|
| Claude (Abo-CLI `claude`) | Echte Claude-Code-Werkzeuge im Projektordner: Bash, Read, Write, Edit, Glob, Grep, WebFetch, WebSearch. Installationsbefehle (npm install, pip install, winget, apt, sudo …), `rm -rf`, `git push` und die `.env` sind ihm gesperrt; er beantragt sie mit `nachruesten`. |
| ChatGPT (Abo-CLI `codex`) | Codex mit eigener Abschottung im Projektordner (Stufe 1 nur lesen, Stufe 2 schreiben im Projekt ohne Netz). Netz und Installationen beantragt er. |
| Alle API-KIs (Gemini, Groq, ChatGPT-API, Qwen, DeepSeek, Mistral, OpenRouter …) und Ollama | Server-Werkzeug `befehl`: führt einen Befehl im Projektordner aus (Windows: PowerShell, Linux: bash) und gibt die Ausgabe zurück. |

Alle Agenten mit Werkstatt haben außerdem `befehl` und `nachruesten`.

## Die drei Stufen

| | Stufe 1 vorsichtig | Stufe 2 normal (Standard) | Stufe 3 frei |
|---|---|---|---|
| Befehle im Projektordner (rendern, testen, Dateien bauen) | Antrag | sofort | sofort |
| Installationen (npm, pip, winget, apt, sudo, curl … \| sh) | Antrag | Antrag | sofort, du bekommst eine Meldung |
| Löschen, Eingriffe ins System, `git push` | Antrag | Antrag | sofort, du bekommst eine Meldung |
| Pfade außerhalb des Projektordners | Antrag | Antrag | sofort |
| Zugangsdaten (`.env`, `tokens/`, Umgebungsvariablen mit Keys) | gesperrt | gesperrt | gesperrt |

Stufe 3 gibt es nur mit `PCL_WERKSTATT_FREI=1` in der `.env`. Ohne den Schalter gilt Stufe 3 wie Stufe 2.

**Wichtig:** Die Einteilung in Stufe 2 erkennt die üblichen Befehle an ihrer Form. Sie ist eine Vorsortierung, keine Abschottung.
Ein Agent könnte sie mit Tricks umgehen (z. B. eine Installation in einem selbst geschriebenen Skript verstecken). Gib die Werkstatt
deshalb nur Agenten, denen du vertraust, und lies bei Anträgen den Befehl.

## Ablauf eines Nachrüst-Antrags

1. Der Mitarbeiter merkt, dass ihm etwas fehlt, und ruft `nachruesten` auf (oder ein `befehl` ist eine Installation). Er nennt den
   genauen Befehl, wofür er ihn braucht und die ungefähre Größe.
2. Der **CEO** (oberster Chef des Projekts) bekommt den Antrag und prüft ihn kurz. Offensichtlich Unnötiges lehnt er ab
   (Begründung geht an den Mitarbeiter). Sonst schreibt er seine Empfehlung dazu und leitet ihn an dich weiter.
   Stellt der CEO selbst den Antrag, geht er direkt an dich.
3. **Du** bekommst eine Telegram-Nachricht mit ✅ Ja / ❌ Nein und siehst den Antrag unter ✋ Freigaben. Du kannst auch schon
   entscheiden, während der CEO noch prüft.
4. Nach deinem Ja führt der Server den Befehl im Projektordner aus (Zeitlimit `PCL_NACHRUEST_TIMEOUT`, Standard 30 Minuten).
   Das Ergebnis steht in der Freigabe, in Telegram und im Verlauf.
5. Der CEO meldet dem Mitarbeiter das Ergebnis, die Aufgabe geht automatisch weiter.
6. Was installiert wurde, steht in `wissen/werkzeuge.md` im Projekt, damit niemand dasselbe noch einmal beantragt.

Höchstens `PCL_NACHRUEST_MAX` (6) Anträge je Aufgabe.

## Beispiel: Remotion für das Animationsstudio

Ein Agent mit Werkstatt prüft `node --version`. Fehlt Node.js, beantragt er
`winget install --id OpenJS.NodeJS.LTS -e --scope user --accept-package-agreements --accept-source-agreements`.
Danach beantragt er `npm install remotion @remotion/cli` im Projektordner und rendert mit `npx remotion render …` nach `output/`.
Remotion ist laut seiner Lizenz für Einzelpersonen und kleine Firmen (bis 3 Mitarbeiter) kostenlos, größere Firmen brauchen eine Firmenlizenz.

## Gut zu wissen

- **Windows-UAC:** Manche winget-Installationen öffnen das Fenster „Darf diese App Änderungen vornehmen?“. Das muss jemand am Laptop
  bestätigen. Mit `--scope user` klappt es oft ohne.
- **Pi/Linux:** Als Dienst läuft Hyperstead mit `NoNewPrivileges` (Härtung in `deploy/hyperstead.service`). Darum klappen `sudo`
  und `apt install` aus der Werkstatt **nie**, auch nicht nach deinem Ja. Hyperstead lehnt solche Anträge deshalb sofort ab und sagt dem
  Agenten, wie es ohne sudo geht. Node.js kommt ohne sudo über `deploy/node-ohne-sudo.sh` in deinen Benutzerordner (siehe unten).
  Systembibliotheken (apt) installierst du selbst im Terminal. Nur wenn Hyperstead **nicht** als Dienst läuft und du passwortfreies sudo
  eingerichtet hast, erlaubt `PCL_WERKSTATT_SUDO=1` in der `.env` sudo-Anträge.
- **Was installiert ist, gilt für den ganzen Rechner** (bzw. bei npm/pip im Projektordner für dieses Projekt).
- **Abo-Verbrauch:** Claude Code und Codex mit Werkzeugen verbrauchen mehr von deinem Abo als reine Textantworten.
- **Zeitlimits:** `PCL_BEFEHL_TIMEOUT` (600 s je Befehl), `PCL_WERKSTATT_TIMEOUT` (3600 s je Claude-/Codex-Lauf).
- Es läuft immer nur ein Werkstatt-Befehl gleichzeitig.
- Jeder Befehl und jede Entscheidung steht im Verlauf (Audit-Log).
- Noch nicht gebaut: ein Stopp-Knopf, der einen laufenden Befehl abbricht (das Zeitlimit beendet ihn). Ein Live-Protokoll während
  eines Claude-Code-Laufs gibt es auch noch nicht, die Schritte stehen erst danach im Ergebnis.

## Remotion auf dem Raspberry Pi (ohne sudo)

Remotion braucht Node.js und einen eigenen Chrome. Auf dem Pi geht das so, einmalig im Terminal (SSH), als der Benutzer,
unter dem Hyperstead läuft:

1. Prüfen, dass das System 64 Bit ist: `uname -m` muss `aarch64` zeigen und `getconf LONG_BIT` muss `64` zeigen. Remotion läuft nicht
   auf 32-Bit-Systemen.
2. Node.js ohne sudo installieren (landet in `~/.local/node`, Links in `~/.local/bin`, die der Dienst schon im PATH hat):
   ```
   cd ~/paperclip-lite        # bzw. dein Hyperstead-Ordner
   git pull
   bash deploy/node-ohne-sudo.sh --remotion
   ```
   Das Skript lädt die neueste Node.js-LTS von nodejs.org, prüft die Prüfsumme und meldet am Ende, ob für Remotions Chrome
   Systembibliotheken fehlen. Fehlen welche, zeigt es eine Zeile `sudo apt install …`, die du selbst ausführst (das ist der einzige
   Schritt mit sudo, und er geht nur von dir aus, nicht aus der Werkstatt).
3. Hyperstead neu starten: `sudo systemctl restart hyperstead`.
4. Dem Agenten den Auftrag zurückgeben. Er beantragt dann `npm install remotion @remotion/cli` im Projektordner und danach
   `npx remotion browser ensure` (lädt den Chrome für Remotion). Gerendert wird mit `npx remotion render … output/film.mp4`.

Alternativ kann auch ein Agent mit Werkstatt den Schritt 2 beantragen (`bash <Hyperstead-Ordner>/deploy/node-ohne-sudo.sh`), dann
installiert der Server Node.js nach deinem Ja. Die Systembibliotheken aus Schritt 2 bleiben trotzdem dein Teil.

**„Bad system call“:** Das heißt, ein Programm wurde von einer Abschottung (seccomp) beendet. Prüfe im Terminal `node --version`.
Klappt es dort, kam der Fehler aus der Abschottung der KI-CLI (Codex-Sandbox oder ähnliches), nicht vom Pi. Der Agent soll den Befehl
dann über das Server-Werkzeug `befehl` ausführen, das läuft außerhalb dieser Abschottung (die Agenten-Anweisung sagt ihm das jetzt).
Bricht `node --version` auch im Terminal so ab, passt die Node.js-Version nicht zum System: mit `deploy/node-ohne-sudo.sh` neu
installieren und prüfen, dass `which node` auf `~/.local/bin/node` zeigt.

## Probleme

| Meldung | Was tun |
|---|---|
| „Keine Werkstatt (Recht 'werkstatt' fehlt oder PCL_ALLOW_WERKSTATT ist aus)“ | `PCL_ALLOW_WERKSTATT=1` in `.env`, neu starten, Häkchen beim Agenten setzen. |
| Häkchen ist grau | `PCL_ALLOW_WERKSTATT=1` fehlt oder Hyperstead wurde nicht neu gestartet. |
| Stufe 3 ist grau | `PCL_WERKSTATT_FREI=1` in `.env`. |
| „Zugangsdaten … sind für Agenten gesperrt“ | Gewollt: Agenten dürfen `.env`, Tokens und Keys nie lesen. |
| Antrag hängt bei „Der CEO prüft gerade …“ | Der CEO hat keine KI oder sie antwortet nicht. Du kannst trotzdem entscheiden. |
| Installation „Exit 1“ | Ausgabe in der Freigabe lesen. Oft fehlt die UAC-Bestätigung (Windows). Der Mitarbeiter bekommt die Ausgabe und kann einen anderen Befehl beantragen. |
| „sudo/apt cannot work here“ bzw. „no new privileges“ | Gewollt: der Dienst hat keine Root-Rechte. Node.js mit `deploy/node-ohne-sudo.sh`, Systembibliotheken selbst per `sudo apt install …` im Terminal (Abschnitt „Remotion auf dem Raspberry Pi“). |
| „Bad system call“ bei `node` | Abschnitt „Remotion auf dem Raspberry Pi“, Absatz „Bad system call“. |
| Claude-Code-Fehler „unknown option“ | Claude Code aktualisieren (`npm install -g @anthropic-ai/claude-code`), die Schalter `--tools`/`--allowedTools`/`--disallowedTools` brauchen eine aktuelle Version. |
