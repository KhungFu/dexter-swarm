# Browser-Makros (MagicLight, Google Flow ...)

MagicLight und Google Flow haben keine Schnittstelle für Programme. Ein Makro ist ein kleines Playwright-Skript, das die
Webseite mit **deinem** Konto bedient wie ein Mensch: Text eingeben, Start klicken, warten, Video herunterladen.
Agenten mit dem Recht „Medien“ rufen es über das Werkzeug `site_macro` auf (`site` = Dateiname ohne `.py`).

**Ehrliche Risiken:** Automatische Bedienung verstößt bei vielen Diensten gegen die Nutzungsbedingungen, im schlimmsten
Fall wird das Konto gesperrt. Nimm kein wichtiges Hauptkonto. Ändert die Seite ihr Aussehen, bricht das Makro ab und
muss neu aufgenommen werden. Google erkennt automatische Browser manchmal und verlangt eine neue Anmeldung.
Chromium braucht viel Speicher (auf dem Pi mit 4 GB knapp, ein Makro läuft immer allein).

## Einrichten (einmal je Seite)

1. Browser installieren: `./install.sh --browser`
2. In `.env`: `PCL_MACROS=1` (Standard aus), PaperclipLite neu starten.
3. Aufnehmen, auf einem Rechner mit Bildschirm (Pi mit Desktop oder Laptop):
   ```bash
   ./venv/bin/playwright codegen --save-storage macros/magiclight.json https://magiclight.ai
   ```
   Anmelden, dann einen Auftrag einmal von Hand durchklicken bis zum Download. Das Aufnahmefenster schreibt jeden
   Klick als Python-Zeile mit.
4. `macros/vorlage_magiclight.py` nach `macros/magiclight.py` kopieren und die Zeilen im Block „Klickweg“ durch die
   aufgenommenen ersetzen. Den getippten Text ersetzt du durch `PROMPT`. Für Flow genauso mit `vorlage_flow.py`.
   Du kannst die Aufnahme auch Claude schicken und das einbauen lassen.
5. Prüfen: `./venv/bin/python selftest.py browser` zeigt die gefundenen Makros.
   Ein Testlauf von Hand: `PCL_PROMPT="Ein Fuchs im Schnee" PCL_OUTPUT=/tmp/t PCL_STORAGE=macros/magiclight.json ./venv/bin/python macros/magiclight.py`

Aufgenommen auf dem Laptop? Dann `magiclight.py` und `magiclight.json` nach `macros/` auf dem Pi kopieren.

## Sicherheit

- Die `.json`-Dateien enthalten deine Anmelde-Cookies. Sie sind per `.gitignore` vom Repo ausgeschlossen, nie weitergeben.
- Agenten wählen nur den Namen des Makros und den Text, das Skript selbst schreibst nur du. Das Skript bekommt keine
  Schlüssel aus `.env`.
- Schlägt ein Makro fehl, legt die Vorlage `<seite>-fehler.png` in `output/`, damit du siehst, wo es hängt.
