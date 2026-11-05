# Claude-CLI (Abo) anmelden und erneuern

Der Anbieter „Claude (CLI, your subscription)“ ruft auf dem Rechner, auf dem Hyperstead läuft, `claude -p` auf.
Das klappt nur, solange `claude` dort angemeldet ist. Diese Seite sagt, was kaputtgehen kann, was Hyperstead
selbst erledigt und was nur du machen kannst.

## Woran es meistens liegt

| Meldung in der Aufgabe / im Terminal | Ursache | Lösung |
| --- | --- | --- |
| `Claude CLI is not signed in or its sign-in has expired …`, `Invalid API key · Please run /login`, `OAuth token has expired`, `401` | Anmeldung abgelaufen oder widerrufen (Passwort geändert, auf claude.ai abgemeldet, Abo pausiert) | Skript unten ausführen |
| `'claude' is not installed or not signed in on the server` | `claude` fehlt oder liegt nicht im PATH des Dienstes | Skript unten (installiert auf Wunsch), auf dem Pi nach `~/.local/bin` installieren |
| `unknown option '--tools'` o. ä. | veraltete `claude`-Version | Skript unten (führt `claude update` aus) |
| `CLI agents are off` | `PCL_ALLOW_CLI=1` fehlt in `.env` | eintragen, Hyperstead neu starten |
| `CLI agent: time limit` | Abo-Limit erreicht oder Netz langsam | warten, `PCL_WORKERS=1`, ggf. `PCL_CLI_TIMEOUT` erhöhen |

## Was automatisch geht

- **Langzeit-Token:** `claude setup-token` erzeugt ein Token, das **ein Jahr** gilt (statt der normalen Anmeldung, die
  sich gelegentlich nicht mehr erneuern lässt). Das Skript speichert es in `tokens/claude-oauth-token.txt`
  (nur für deinen Benutzer lesbar, nie im Repo). Hyperstead gibt es bei jedem Aufruf **nur an `claude`** weiter, als
  `CLAUDE_CODE_OAUTH_TOKEN`. Andere Programme, Codex und die Werkzeuge der Agenten bekommen es nicht.
- **Kein Neustart nötig:** Die Datei wird bei jedem Aufruf neu gelesen.
- **Warnungen per Telegram:** schlägt die Anmeldung fehl, kommt höchstens alle 6 Stunden eine Nachricht mit dem
  Befehl zum Erneuern. 30 Tage bevor das Token ein Jahr alt ist, kommt einmal am Tag eine Erinnerung.
- **Updates:** `claude` aktualisiert sich normalerweise selbst. Das Skript ruft zusätzlich `claude update` auf.

## Was nur du machen kannst

Die Anmeldung selbst. Sie läuft im Browser mit deinem Claude-Konto (Pro/Max) und lässt sich aus Sicherheitsgründen
nicht automatisieren. Einmal im Jahr (oder wenn Telegram meldet) also:

**Raspberry Pi / Linux** (per SSH, als der Benutzer, unter dem Hyperstead läuft, nicht mit sudo):

```bash
cd ~/hyperstead        # dein Hyperstead-Ordner
./deploy/claude-erneuern.sh
```

**Windows-Laptop** (PowerShell im Hyperstead-Ordner):

```powershell
powershell -ExecutionPolicy Bypass -File deploy\windows\claude-erneuern.ps1
```

Das Skript
1. sucht `claude` (fehlt es, fragt es, ob es mit dem offiziellen Installer installiert werden soll),
2. führt `claude update` aus,
3. testet `claude -p` genau so, wie Hyperstead es aufruft (ohne API-Keys),
4. startet nur wenn nötig `claude setup-token`: Link öffnen (auf dem Pi am Handy oder PC), anmelden, „Autorisieren“,
   Code zurück ins Terminal, dann das angezeigte Token `sk-ant-oat01-…` kopieren und **unsichtbar** einfügen.
   Danach testet es erneut.

Weitere Schalter: `--pruefen` / `-Pruefen` nur prüfen (Exitcode 0 = ok, 1 = Anmeldung nötig, 2 = `claude` fehlt),
`--neu` / `-Neu` sofort ein neues Token holen (z. B. nach der Telegram-Erinnerung).

**Das Token nie in einen Chat, eine Mail oder ein Repo kopieren.** Wer es hat, nutzt dein Abo. Zum Widerrufen:
auf claude.ai unter Einstellungen die Sitzungen abmelden und das Skript mit `--neu` erneut ausführen.

## Pi und Laptop parallel

Jeder Rechner braucht seine **eigene** Anmeldung: auf beiden einmal das Skript ausführen. Ein Token kann man zwar
kopieren, doch zwei Rechner mit demselben Abo teilen sich auch dasselbe Nutzungslimit; viele Agenten auf beiden
Rechnern erreichen es schneller.

## Hinweise

- Ein `CLAUDE_CODE_OAUTH_TOKEN=` in `.env` geht auch, die Datei `tokens/claude-oauth-token.txt` hat aber Vorrang.
- In der **Werkstatt** (Recht `werkstatt`) läuft Claude Code mit Bash. Das Token steht dort in der Umgebung von
  `claude` und damit theoretisch auch für dessen eigene Befehle bereit. Wer das nicht will, lässt die Werkstatt
  für Claude-Agenten aus oder nutzt statt des Tokens die normale Anmeldung (`claude`, dann `/login`).
- Ohne Token-Datei nutzt `claude` seine normale Anmeldung (`~/.claude/`), wie bisher.
