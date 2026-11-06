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

### Canva meldet „NOT AVAILABLE“ (2026-11-06 auf dem Laptop so gesehen)

Mit dem Langzeit-Token aus `claude setup-token` lädt `claude` die claude.ai-Konnektoren offenbar nicht. Zwei Auswege:

**A (empfohlen, Token bleibt):** Canva als eigenen MCP-Server bei Claude Code anmelden, einmal auf dem Laptop:

```
claude mcp add --transport http --scope user canva https://mcp.canva.com/mcp
claude
```

In Claude `/mcp` eingeben, `canva` wählen, „Authenticate“, im Browser bei Canva anmelden, Claude mit `/exit` beenden.
`PCL_CLAUDE_CONNECTORS=Canva` bleibt in `.env`. Hyperstead erlaubt dann auch den Server `canva` (Werkzeuge `mcp__canva__…`).
Danach Hyperstead neu starten und `python selftest.py links`.

**B:** Ohne Langzeit-Token: `tokens/claude-oauth-token.txt` umbenennen (und `CLAUDE_CODE_OAUTH_TOKEN` aus `.env` nehmen), dann
`claude` → `/login` mit dem claude.ai-Konto. Die normale Anmeldung erneuert sich selbst, kann aber ablaufen
(siehe [claude-anmeldung.md](claude-anmeldung.md)).

Beides ist ungeprüft, weil es nur auf dem Laptop geht.

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

## Bilder über Canva (mit Referenzbild)

Canva erreicht nur die Claude-CLI, nicht der Hyperstead-Server selbst. Darum erzeugt ein Claude-CLI-Agent die Bilder mit seinem
Canva-Konnektor, und Hyperstead hilft mit zwei Werkzeugen (Recht `images`, sichtbar nur mit `PCL_CLAUDE_CONNECTORS=Canva`):

1. Agent ruft Canva `create-upload-url` auf (einmal nutzbarer Upload-Link).
2. `canva_upload {"path": "input/referenz.jpg", "upload_url": "…"}`: Hyperstead schickt das Referenzbild roh an Canva und gibt
   die Antwort mit der Media-ID zurück. Erlaubt sind nur https-Links von `canva.com`, `canva-api.com`, `canva.cn`; weitere Hosts
   mit `PCL_CANVA_UPLOAD_HOSTS=` in `.env`, falls Canva den Upload über einen anderen Host schickt (die Fehlermeldung nennt ihn).
3. Canva `generate-image` mit dem Prompt und `imageReferences` = Media-ID, dann `get-generate-image-job` bis `SUCCESS`.
4. `image_save {"url": "…", "path": "karten/bilder/k01.png"}` holt das Bild in den Projektordner, danach `view_image`.

So nutzt du es:

- `IMAGE_PROVIDER=canva` in `.env`: `image_generate` erzeugt dann selbst nichts, sondern erklärt dem Agenten diesen Weg.
- Bleibt ein anderer Anbieter eingestellt und scheitert er (z. B. OpenRouter ohne Guthaben, HTTP 402), nennt die Fehlermeldung
  den Canva-Weg. Ist `IMAGE_FALLBACK=pollinations` gesetzt und gibt es Referenzbilder, aber keinen `POLLINATIONS_API_KEY`, gibt es
  **kein** Gratis-Ersatzbild mehr, denn das würde ohne Referenzbild Figuren und Stil verfehlen.
- Der Agent, der die Bilder macht, muss den Anbieter „Claude (CLI, your subscription)“ und das Recht `images` haben.

**Ungeprüft:** Der echte Canva-Upload und die Bildgröße. Aus der Cloud-Testumgebung kam das Canva-Bild nur als kleine Vorschau
(ca. 200 px) an. Ist das Bild auf dem Laptop auch so klein, kann der Agent es in ein Canva-Design legen und mit `export-design` als
PNG exportieren.

## Grenzen

- Getestet: Durchreichen eines eigenen MCP-Servers an `claude -p` mit echtem Claude-Aufruf (Werkzeugaufruf und Status kamen an),
  Fehler- und Statusmeldungen mit Tests. **Nicht getestet:** echte claude.ai-Konnektoren (Canva) auf dem Pi/Laptop, Codex mit MCP.
- Jeder Aufruf startet die MCP-Server neu. Langsame Server machen jede Antwort langsamer.
- Die Verbindungen gelten für alle Claude-CLI-Agenten aller Firmen gleich, nicht je Firma.
