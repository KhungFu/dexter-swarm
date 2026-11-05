# Werkzeuge der eigenen KI (Canva, Drive, eigene MCP-Server)

Agenten mit dem Anbieter „Claude (CLI, your subscription)“ oder „ChatGPT (Codex CLI, your subscription)“ laufen über das
Programm `claude` bzw. `codex` auf dem Rechner, auf dem Hyperstead läuft. Diese Programme können eigene Verbindungen
(MCP-Server, bei Claude auch die Konnektoren aus deinem claude.ai-Abo wie Canva) nutzen. Standardmäßig sind sie für Claude
**aus**. Hier schaltest du sie gezielt ein. Zugangsdaten gehören nur in `.env` bzw. `tokens/` (beides nie im Repo), nie in den Chat.

## 1. Konnektoren aus dem claude.ai-Abo (z. B. Canva)

1. Auf claude.ai unter Einstellungen → Konnektoren den Konnektor (z. B. Canva) verbinden.
2. In `.env` eintragen (Namen wie auf claude.ai, mehrere mit Komma):

   ```
   PCL_CLAUDE_CONNECTORS=Canva
   ```

3. Hyperstead neu starten und prüfen: `python selftest.py links` (Windows: `venv\Scripts\python selftest.py links`).

Mit Konnektoren läuft `claude` ohne `--strict-mcp-config`. Erlaubt sind aber nur die eingetragenen Konnektoren und die
Server aus `tokens/claude-mcp.json`, andere Werkzeuge werden abgelehnt (Ausnahme: Werkstatt Stufe 3 erlaubt ohnehin alles).

**Ungeprüft:** Ob claude.ai-Konnektoren auch mit dem Langzeit-Token aus `claude setup-token`
(`tokens/claude-oauth-token.txt`, siehe [claude-anmeldung.md](claude-anmeldung.md)) geladen werden, konnte ich nicht testen.
Zeigt der Selbsttest „NOT AVAILABLE“, liegt es vermutlich daran. Dann melde dich auf dem Rechner einmal normal mit
`claude` → `/login` an und benenne `tokens/claude-oauth-token.txt` testweise um.

## 2. Eigene MCP-Server

Datei `tokens/claude-mcp.json` (anderer Ort: `PCL_CLAUDE_MCP=` in `.env`), Format wie bei Claude Code:

```json
{
  "mcpServers": {
    "dateien": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/pi/bilder"]},
    "mein-dienst": {"type": "http", "url": "https://example.com/mcp", "headers": {"Authorization": "Bearer DEIN_TOKEN"}}
  }
}
```

Jeder Eintrag braucht `command` oder `url`. Ist die Datei fehlerhaft, wird sie ignoriert, und das steht im Protokoll, in
Telegram und im Prompt des CEO („CONFIGURATION ERROR“). Die Datei wird bei jedem Aufruf neu gelesen, ein Neustart ist nicht nötig.

## 3. Codex (ChatGPT)

Codex lädt seine MCP-Server selbst aus `~/.codex/config.toml` (bzw. `CODEX_HOME`), z. B.:

```toml
[mcp_servers.dateien]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/home/pi/bilder"]
```

Hyperstead liest nur die Namen und nennt sie dem Agenten. Ob sie laufen, prüft Hyperstead bei Codex nicht.

## Was der CEO davon sieht

- Im Systemprompt (Chat und Aufgaben) steht der Abschnitt „OWN CONNECTIONS OF YOUR AI“ mit jedem Server und seinem letzten
  Status: `connected`, `FAILED to start`, `NEEDS SIGN-IN`, `NOT AVAILABLE` oder „not checked yet“. Der Status kommt bei jedem
  Claude-Aufruf aus der Startzeile von `claude` (stream-json).
- Er soll Ergebnisse aus den Verbindungen (Links, IDs, Texte) in seine Antwort schreiben, denn nur die sieht das Team. Dateien,
  die z. B. Canva erzeugt, bleiben bei Canva, bis ein Agent sie mit `download_file` in den Projektordner holt.
- Geht eine Verbindung nicht, kommt das ins Protokoll (`ai_link_failed`) und per Telegram (je Verbindung höchstens alle 6 Stunden).
- Ohne Verbindungen bekommt nur der oberste Chef einen kurzen Hinweis auf diese Anleitung.
- API: `GET /api/ai_links` (Stand), `POST /api/ai_links/check` (kurzer Probelauf mit `haiku`, anderes Modell: `PCL_LINKS_CHECK_MODEL`).

## Bilder

Bilder kommen schon länger als echtes Bild beim Modell an: im Chat per 📎 oder wenn der Dateiname aus `input/` in der Nachricht
steht, in Aufträgen, wenn der Pfad `input/…` genannt wird, sonst über das Werkzeug `view_image`. Neu: Erwähnt der Besitzer im Chat
ein Bild („Bild“, „Referenzbild“, „Foto“, „image“, „resim“, „görsel“ …), ohne eines anzuhängen, schickt Hyperstead das
**neueste Bild aus `input/`** automatisch mit und sagt dem Agenten, dass es automatisch gewählt wurde.

## Grenzen

- Getestet: Durchreichen eines eigenen MCP-Servers an `claude -p` mit echtem Claude-Aufruf (Werkzeugaufruf und Status kamen an),
  Fehler- und Statusmeldungen mit Tests. **Nicht getestet:** echte claude.ai-Konnektoren (Canva) auf dem Pi/Laptop, Codex mit MCP.
- Jeder Aufruf startet die MCP-Server neu. Langsame Server machen jede Antwort langsamer.
- Die Verbindungen gelten für alle Claude-CLI-Agenten aller Firmen gleich, nicht je Firma.
