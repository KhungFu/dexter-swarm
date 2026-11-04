# Filmstudio: Animationsfilme mit Blender

Mit dem Werkzeug `film` (Recht **Medien**) drehen die Agenten kleine Zeichentrickfilme im Stil einer Kinderserie:
Figuren mit eigenen Stimmen und Mundbewegung, Orte, Requisiten, Bewegungen, Kamera, Untertitel, fertiger Film mit Ton.
Gerendert wird mit **Blender** auf dem Rechner, auf dem Hyperstead läuft (bei dir: der Laptop).

## 1. Einrichten (einmal, auf dem Laptop)

1. Blender installieren, falls noch nicht da: `winget install BlenderFoundation.Blender` (oder von blender.org).
   Getestet ist Blender 5.2, das Skript ist für 3.6 bis 5.x geschrieben.
2. Hyperstead findet Blender meist selbst (`C:\Program Files\Blender Foundation\Blender …\blender.exe`).
   Sonst in `.env` eintragen und Hyperstead neu starten:
   ```
   BLENDER_PATH=C:\Program Files\Blender Foundation\Blender 4.2\blender.exe
   ```
3. ffmpeg und eine Sprachausgabe müssen da sein (siehe [windows.md](windows.md)): `winget install Gyan.FFmpeg`,
   für Stimmen `venv\Scripts\pip install edge-tts` und `TTS_ENGINE=edge` (oder Piper/espeak-ng).
   Besonders gute Stimmen: `ELEVENLABS_API_KEY` in `.env`, dann bei einer Figur `"stimme": {"engine": "elevenlabs", "voice": "<Stimmen-ID>"}`.
4. Prüfen: `venv\Scripts\python selftest.py film`. Das rendert ein Vorschaubild und eine 1,5-Sekunden-Szene.
5. Firma anlegen: Vorlage **🐶 Animationsstudio (Blender)**. Oder einem vorhandenen Agenten das Recht „Medien“ geben.

Auf dem Raspberry Pi geht es auch (`sudo apt install blender`), ist aber sehr langsam. Ohne Blender funktionieren
`save`, `check`, `voices` und `assemble`, nur `preview` und `render` melden „Blender wurde nicht gefunden“.

## 2. Ablauf

| Schritt | Aufruf | Ergebnis |
|---|---|---|
| Drehbuch speichern | `{"tool": "film", "op": "save", "film": {...}}` | `film/film.json` (wird vorher geprüft) |
| Prüfen | `op: check` | Fehlerliste oder Übersicht mit geschätzter Länge |
| Stimmen | `op: voices` | `film/ton/<szene>_<nr>.mp3`, nur neue/geänderte Zeilen |
| Vorschau | `op: preview`, `szene: "s01"`, optional `zeit` | `film/vorschau/s01.png`, der Agent sieht das Bild sofort |
| Rendern | `op: render`, `szene: "s01"` oder ohne = alle | `film/clips/s01.mp4`, unveränderte Szenen werden übersprungen |
| Schnitt | `op: assemble`, `name`, `untertitel: true` | `output/<name>.mp4` und `output/<name>.srt` |

Mehrere Filme: `datei: "film/folge2.json"` bei jedem Aufruf mitgeben.

## 3. Drehbuch-Format (`film/film.json`)

```json
{
  "titel": "Bello und der rote Ball",
  "aufloesung": "640x360", "fps": 12, "titelkarte": 3,
  "figuren": {
    "Bello": {"art": "hund", "farbe": "#c8843c", "farbe2": "#f6e7d0", "stimme": {"lang": "de", "voice": "m3", "pitch": 35}},
    "Mimi":  {"art": "katze", "farbe": "#888888", "farbe2": "#ffffff", "stimme": {"lang": "de", "voice": "f2", "pitch": 70}},
    "Fuchs": {"art": "bild", "bild": "assets/fuchs.png", "groesse": 1.6, "blickrichtung": "rechts"}
  },
  "szenen": [
    {"id": "s01",
     "ort": {"himmel": "#9fd7ff", "boden": "#7cc96b", "licht": "tag"},
     "requisiten": [{"typ": "baum", "pos": [-4, 3]}, {"typ": "haus", "pos": [4, 5]}, {"id": "ball", "typ": "ball", "pos": [1, 0]}],
     "figuren": {"Bello": {"pos": [-3, 0]}, "Mimi": {"pos": [2.5, 0], "blick": "links"}},
     "aktionen": [
       {"zeit": 0.5, "figur": "Bello", "tun": "gehen", "nach": [0, 0]},
       {"zeit": 3, "figur": "Mimi", "tun": "winken"},
       {"zeit": 4, "figur": "ball", "tun": "gehen", "nach": [3, 1], "dauer": 0.8}
     ],
     "dialog": [
       {"figur": "Bello", "text": "Hallo Mimi! Spielst du mit mir?"},
       {"figur": "Mimi", "text": "Au ja, wirf den Ball!", "pause": 0.5}
     ],
     "kamera": {"einstellung": "total", "bewegung": "keine"},
     "dauer": 5}
  ]
}
```

- **Figuren:** `art` = `hund`, `katze`, `hase`, `baer`, `maus`, `mensch` (eingebaut, `farbe`, `farbe2`, bei `mensch` auch `haar`),
  `bild` (Bild einer Figur, z. B. von `image_generate` auf weißem Grund; der einfarbige Hintergrund wird automatisch freigestellt,
  `freistellen: false` schaltet das ab) oder `blend` (eigene Figur aus einer `.blend`-Datei: `datei`, `objekt`, `aktion` = Name der
  Bewegung, die in Schleife läuft; ein Formschlüssel `mund`/`mouth` bewegt sich beim Sprechen).
- **Stimme:** `lang`, `voice` (espeak-ng: `m1`–`m7`, `f1`–`f5`; Piper: Dateiname eines Modells in `models/piper/`; Edge: z. B.
  `de-DE-ConradNeural`), `pitch` 0–99 (50 normal), `rate` 0,5–2. Dialogzeilen ohne `figur` spricht der Erzähler (`erzaehler_stimme` in der Szene).
- **Bühne:** `pos` = `[x, tiefe]`. `x` von etwa −6 (links) bis 6 (rechts), `tiefe` 0 vorne bis 8 hinten. `blick`: vorne, links, rechts, hinten.
- **Aktionen:** `gehen` (`nach`, optional `dauer`), `springen` (`hoehe`), `winken`, `drehen` (`richtung`), `nicken`, `erscheinen`,
  `verschwinden`. Requisiten mit `id` lassen sich genauso bewegen.
- **Ort:** `himmel`, `boden` (`false` = kein Boden), `hintergrund` (gemaltes Bild, füllt immer das ganze Bild), `licht` tag/abend/nacht.
- **Kamera:** `einstellung` total/halbtotal/nah, `ziel` (Figur), `bewegung` keine/zoom_rein/zoom_raus/schwenk_links/schwenk_rechts/folgen.
- **Ton:** `musik` und `musik_lautstaerke` je Szene oder für den ganzen Film.
- **Technik:** `renderer` eevee (Standard, Cartoon-Umriss), workbench (am schnellsten), cycles (ohne Grafikchip, langsamer);
  `samples`, `umriss: false`.

Die Szene dauert so lange wie ihr Dialog (plus kurze Pause), mindestens `dauer` Sekunden.

## 4. Laptop schonen (8 GB RAM, ohne Grafikkarte)

- Standard ist **640×360 bei 12 Bildern/s**, das sieht nach Zeichentrick aus und rendert schnell. Für die Endfassung höchstens
  `"aufloesung": "1280x720"`.
- Blender läuft nie parallel zu sich selbst oder zum Bildrechner (gemeinsame Sperre). Szenen werden einzeln gerendert, fertige Bilder
  einer abgebrochenen Szene werden beim nächsten `render` weiterverwendet.
- Grenzen: `PCL_BLENDER_TIMEOUT` (Standard 3600 s je Szene), `PCL_FILM_BUDGET` (2700 s je Aufruf, danach meldet `render`, welche Szenen
  noch fehlen), `BLENDER_THREADS` (z. B. 4, damit der Laptop bedienbar bleibt).
- Weitere `.env`-Schalter: `BLENDER_ENGINE`, `BLENDER_SAMPLES` (16), `FILM_RES` (640x360), `FILM_FPS` (12).

## 5. Was es kann und was nicht

Kann: wiederkehrende Figuren, die in jeder Szene gleich aussehen; Sprechen mit Mundbewegung nach Lautstärke; Gehen mit Wippen und
Armschwung, Springen, Winken, Nicken, Drehen, Auf- und Abtauchen; Blinzeln und Atmen; Kamerafahrten; gemalte Hintergründe; Untertitel.

Kann nicht: echte Gelenk-Animation der eingebauten Figuren (dafür eigene `.blend`-Figuren mit Bewegungen), Gesichtsausdrücke,
Figuren greifen nichts an, kein Lippensync nach Lauten (nur nach Lautstärke). Bildfiguren sind flach (2,5D) und werden beim
Richtungswechsel gespiegelt.
