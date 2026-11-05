# YouTube-Kanal mit Hyperstead verwalten

Hyperstead bereitet deine Uploads vor, rechnet den Veröffentlichungsplan, wertet deine Zahlen aus und lädt ein Video
erst hoch, wenn du es **einzeln freigegeben** hast. Es nutzt dafür nur die offizielle **YouTube Data API v3**, kein
Browser-Skript und keine automatische Anmeldung.

## Was du selbst machst und was Hyperstead macht

| Schritt | Du | Hyperstead |
| --- | --- | --- |
| Google-Konto und Kanäle | Kanäle anlegen (z. B. Deutsch, Englisch, Türkisch), Name, Logo, Banner hochladen, Telefonnummer bestätigen | Schreibt Kanalname, Kanalbeschreibung und Bildideen, wenn du es beauftragst |
| Google-Cloud-Projekt (einmal) | Projekt anlegen, API einschalten, Zugang erzeugen (Anleitung unten) | – |
| Anmeldung je Kanal | `python youtube_channel.py login de` usw., im eigenen Browser anmelden, Kanal wählen | Merkt sich den Zugang in `tokens/youtube-<sprache>.json` (nie im Repo, nie im Chat) |
| Kanal-Datei | Prüfen und freigeben | Agenten füllen `youtube/kanal.json`: Titel, Beschreibung, Keywords, Hashtags je Folge und Sprache |
| Vorbereiten | `youtube/REVIEW.md` lesen | Je Folge und Sprache ein Paket in `youtube/packages/`, dazu `youtube/schedule.csv` (Terminliste) |
| Hochladen | **Jedes Video einzeln freigeben** (✋ Approvals) oder selbst mit `python youtube_channel.py upload …` | Lädt nur das freigegebene Video hoch, immer **privat**, mit Termin. YouTube schaltet es zum Termin öffentlich |
| Untertitel | Sind ins Video eingebrannt. Zusätzliche `.srt` lädst du in YouTube Studio hoch | Liefert `.srt` aus dem Filmstudio |
| Zahlen | In YouTube Studio → Analytics → Erweiterter Modus → Export „Tabellendaten (CSV)“, Datei in Hyperstead hochladen | Werkzeug `analyze` schreibt `youtube/reports/analysis-<datum>.md` |

Fremde Videos, die dir gefallen: Hyperstead lädt sie **nie** herunter und lädt sie nie neu hoch. Gib den Agenten den Link,
sie beschreiben die Machart (Aufbau, Länge, Schnitt, Pointe). Eigene Kopien entstehen nicht.

## Rhythmus

Anfangs **2 bis 3 Folgen pro Woche** (z. B. Dienstag und Samstag), nicht täglich. Jede Folge erscheint in allen
Sprachen am selben Tag, je Kanal zur eigenen Uhrzeit. Voreinstellung (änderbar in `kanaele.<sprache>.uhrzeit`):
Deutsch 18:00 Europe/Berlin, Türkisch 20:00 Europe/Istanbul, Englisch 17:00 America/New_York. Plant die Kanal-Datei
mehr als 3 Tage pro Woche, steht eine Warnung in `REVIEW.md`. Nach den ersten Wochen entscheidest du anhand der Zahlen.

Diese Uhrzeiten sind Annahmen, keine YouTube-Empfehlung. Sobald es Zahlen gibt, zeigt YouTube Studio unter
„Zielgruppe“, wann deine Zuschauer online sind.

## Einrichtung (einmal)

1. **Google-Cloud-Projekt:** [console.cloud.google.com](https://console.cloud.google.com/) → Neues Projekt, z. B. „Hyperstead YouTube“.
2. **API einschalten:** APIs & Dienste → Bibliothek → „YouTube Data API v3“ → Aktivieren.
3. **OAuth-Zustimmungsbildschirm:** Nutzertyp „Extern“, App-Name, deine E-Mail. Unter „Testnutzer“ dein Google-Konto eintragen.
4. **Zugang erzeugen:** Anmeldedaten → OAuth-Client-ID → Anwendungstyp **„Desktop-App“**. Client-ID und Client-Secret in die
   `.env` von Hyperstead:
   ```
   YOUTUBE_CLIENT_ID=…apps.googleusercontent.com
   YOUTUBE_CLIENT_SECRET=…
   ```
   Danach Hyperstead neu starten.
5. **Kanäle anmelden** (auf dem Rechner, auf dem Hyperstead läuft, im Hyperstead-Ordner):
   ```
   python youtube_channel.py login de
   python youtube_channel.py login en
   python youtube_channel.py login tr
   python youtube_channel.py status
   ```
   Es öffnet sich dein Browser. Du meldest dich selbst an und wählst den passenden Kanal (bei mehreren Kanälen
   im selben Konto erscheint eine Auswahl). Zugriff: nur „Videos hochladen“ (`youtube.upload`).
   Unter Windows: `venv\Scripts\python youtube_channel.py login de`.
   **Pi ohne Bildschirm:** `python youtube_channel.py login de --device` zeigt einen Code, den du am Handy eingibst.
   Google erlaubt bei diesem Weg nur den breiteren Zugriff `youtube` (Kanal verwalten), nicht `youtube.upload`.
   Darum besser auf dem Laptop anmelden.
   Dieser Weg braucht in Schritt 4 einen Client vom Typ „Fernseher und Geräte mit begrenzter Eingabe“ statt „Desktop-App“.
   Entscheide dich für einen Weg: Die Anmeldung gehört immer zu der Client-ID, die beim Anmelden in der `.env` stand.
6. **Recht vergeben:** beim Agenten, der den Kanal betreut, Haken **„May manage YouTube“** setzen.

### Wichtig: Anmeldung läuft im Testmodus nach 7 Tagen ab

Solange dein Google-Projekt im Status „Testing“ steht, gilt die Anmeldung nur **7 Tage**. Dann meldet ein Upload
„sign-in expired“, und du führst `login` erneut aus. Dauerhaft: im Zustimmungsbildschirm „App veröffentlichen“.
Ohne Prüfung durch Google zeigt die Anmeldung dann eine Warnung „Google hat diese App nicht überprüft“, du klickst
„Erweitert → Weiter“. Für dich allein reicht das. Ob Google für den Upload-Zugriff trotzdem eine Prüfung verlangt,
konnte ich nicht feststellen. Prüfe das in der Console beim Veröffentlichen.

## Die Kanal-Datei `youtube/kanal.json`

Das Werkzeug `template` legt ein Beispiel an. Schlüssel sind Deutsch (wie beim Filmstudio):

```json
{
  "serie": "WOBBLER 9",
  "sprachen": ["de", "en", "tr"],
  "kanaele": {"de": {"name": "…", "zeitzone": "Europe/Berlin", "uhrzeit": "18:00", "hashtags": ["#Shorts"], "fuss": "Neue Folgen Di + Sa."}},
  "rhythmus": {"start": "2026-11-24", "tage": ["di", "sa"]},
  "kategorie": "23",
  "fuer_kinder": false,
  "ki_inhalt": false,
  "folgen": [{"nr": 1, "datei": {"de": "output/wobbler9-01-de.mp4"}, "titel": {"de": "…"}, "beschreibung": {"de": "…"},
              "keywords": {"de": ["…"]}, "hashtags": {"de": ["#WOBBLER9"]}, "thumbnail": {"de": "assets/thumb01-de.png"}}]
}
```

- `kategorie` 23 = Comedy.
- `fuer_kinder` bleibt `false`: die Serie richtet sich an Erwachsene.
- `ki_inhalt` = Kennzeichnung „veränderte oder synthetische Inhalte“. YouTube verlangt sie für **realistisch wirkende**
  KI-Inhalte. Für Strichmännchen-Zeichentrick ist sie nach meinem Verständnis nicht nötig. Prüfe die aktuelle Regel in YouTube Studio.
- Wochentage: `mo di mi do fr sa so` oder `mon … sun`.

Geprüft wird beim Vorbereiten: Titel höchstens 100 Zeichen, Beschreibung höchstens 5000 Bytes, keine `<` `>`,
Keywords zusammen höchstens 500 Zeichen (wie YouTube zählt), Hashtags ohne Leerzeichen (über 60 ignoriert YouTube alle),
Video 9:16 und 45–60 s (per `ffprobe`), Termin nicht in der Vergangenheit.

## Hochladen

- Agent: `{"tool": "youtube", "op": "upload", "package": "ep01-de"}` legt eine Freigabe an. Erst dein Klick auf
  „Approve & upload to YouTube“ startet den Upload. Der Link erscheint danach im Auftrag und in Telegram.
- Selbst: `python youtube_channel.py upload <Projektordner> ep01-de`. Das Programm zeigt Titel, Video und Termin und lädt erst,
  wenn du die Paket-ID eintippst.
- Hochgeladen wird immer **privat**. Mit Termin (`publishAt`) macht YouTube das Video zum Termin öffentlich, das kannst du in
  YouTube Studio bis dahin noch ändern. Ist der Termin schon vorbei, bleibt es privat.
- Ein Paket wird nur einmal hochgeladen (`uploaded` in `package.json`).
- Thumbnail: wird gesetzt, wenn `thumbnail` angegeben ist. Bei Shorts zeigt YouTube eigene Thumbnails nur eingeschränkt.

## Grenzen der API (Stand 5.11.2026, mit Quellen)

- **Kontingent:** Standard sind 100 Uploads pro Tag (`videos.insert`) und 10.000 Einheiten für den Rest; Thumbnail 50 Einheiten.
  Zwei bis drei Folgen in drei Sprachen pro Woche liegen weit darunter. Mehr Kontingent gibt es nur nach einer Prüfung durch Google.
  Quelle: <https://developers.google.com/youtube/v3/determine_quota_cost>, <https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits>
- **Ungeprüfte API-Projekte:** Von 28.7.2020 bis 2.11.2026 blieben Uploads aus ungeprüften Projekten privat, bis Google das
  Projekt geprüft hatte. Laut Änderungsprotokoll vom **2.11.2026** gilt das nicht mehr: „Videos uploaded through the
  videos.insert method from unverified API projects are no longer restricted to private viewing mode.“
  Quelle: <https://developers.google.com/youtube/v3/revision_history>, <https://developers.google.com/youtube/v3/docs/videos/insert>.
  Ich habe die Seiten über einen Abruf-Dienst gelesen, nicht selbst im Browser. Sollte ein Termin-Video trotzdem privat
  bleiben, liegt es an dieser Regel: dann Prüfung beantragen oder das Video in YouTube Studio selbst veröffentlichen.
- **Anmeldung per Code (Gerät):** nur Zugriff `youtube` oder `youtube.readonly` möglich.
  Quelle: <https://developers.google.com/identity/protocols/oauth2/limited-input-device>
- **Testmodus = 7 Tage Anmeldung.** Quelle: <https://developers.google.com/identity/protocols/oauth2#expiration>
- **Hashtags:** über 60 werden alle ignoriert; bis zu drei erscheinen beim Titel.
  Quelle: <https://support.google.com/youtube/answer/6390658>
- **Titel/Beschreibung/Tags:** 100 Zeichen / 5000 Bytes / 500 Zeichen. Quelle: <https://developers.google.com/youtube/v3/docs/videos>

## Auswertung

1. YouTube Studio → Analytics → **Erweiterter Modus** → Zeitraum wählen → oben rechts Export → **„Tabellendaten (CSV)“**.
   Bei mehreren Kanälen je Kanal eine Datei.
2. Die CSV in Hyperstead hochladen (📁 Files → `input/`).
3. Auftrag an den Kanal-Agenten, z. B. „Werte input/Tabellendaten.csv aus“. Das Werkzeug `analyze` erkennt
   englische, deutsche und (soweit bekannt) türkische Spaltennamen und schreibt `youtube/reports/analysis-<datum>.md`.

Die Hinweise im Bericht sind Faustregeln, keine Aussagen von YouTube. Echte Kanalstatistiken holt Hyperstead nie selbst ab.
**Ungetestet:** die genauen Spaltennamen des deutschen und türkischen Studio-Exports. Passt eine Spalte nicht, steht im Bericht
„Columns found“. Schick mir dann die erste Zeile der CSV.

## Probleme

| Meldung | Bedeutung | Was du tust |
| --- | --- | --- |
| `YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET are missing` | `.env` ohne Zugang | Schritt 4 oben, neu starten |
| `Channel 'de' is not signed in` | Kein Token für diesen Kanal | `python youtube_channel.py login de` |
| `Sign-in for channel 'de' has expired` | Testmodus, 7 Tage um | `login` erneut, oder App veröffentlichen |
| `has errors` | Paket verletzt eine YouTube-Grenze | `youtube/REVIEW.md` lesen, Kanal-Datei ändern, neu vorbereiten |
| `Unknown time zone` (Windows) | Paket `tzdata` fehlt | `venv\Scripts\pip install tzdata` |
| `HTTP 403 … quota` | Tageskontingent verbraucht | Am nächsten Tag (Mitternacht pazifische Zeit) erneut freigeben |
| `HTTP 403 … forbidden` beim Thumbnail | Kanal darf keine eigenen Thumbnails | Telefonnummer im Kanal bestätigen, Thumbnail in YouTube Studio setzen |

Nur gegen simulierte Antworten getestet. Echter Upload, Anmeldung und Studio-Export sind auf Pi und Laptop ungetestet.
