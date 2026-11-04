# KI-Videodienste in Hyperstead

Agenten mit dem Recht **Medien & Dokumente erstellen** können über diese Werkzeuge Videos und Ton erzeugen:

| Werkzeug | Was es macht | Einschalten in `.env` |
| --- | --- | --- |
| `video_generate` | Text zu Video oder Bild zu Video (Startbild aus dem Projekt) | `VIDEO_PROVIDER=…` + Key des Anbieters |
| `video_ai` | Video hochskalieren (`upscale`), Lippen passend zur Sprache bewegen (`lipsync`), Geräusche zum stummen Video (`sound`) | `VIDEO_AI=fal` + `FAL_KEY` |
| `sound_generate` | Geräusche (`kind: sfx`) oder Musik (`kind: music`) aus einer Beschreibung | `AUDIO_PROVIDER=elevenlabs` oder `fal` |
| `speak` | Sprecherstimme; zusätzlich zu espeak/Piper/Edge jetzt auch Cloud-Stimmen | `TTS_ENGINE=elevenlabs` oder `openai` |

Alles ist **standardmäßig aus**, weil jeder Clip Geld kostet. Ohne passende Zeile sehen die Agenten das Werkzeug gar nicht.

## Videoanbieter (`VIDEO_PROVIDER`)

Mehrere Anbieter gehen gleichzeitig, mit Komma getrennt: `VIDEO_PROVIDER=kling,wan,higgsfield`. Der erste ist der Standard,
die Agenten können mit `"provider": "wan"` einen anderen aus der Liste wählen. Nicht eingeschaltete Anbieter sind für sie gesperrt.

| `VIDEO_PROVIDER` | Dienst | Key(s) in `.env` | Standardmodell | Konto |
| --- | --- | --- | --- | --- |
| `gemini` | Google Veo / Gemini Omni | `GEMINI_API_KEY` | `gemini-omni-1.1-flash` | Google-AI-Studio-Key mit Abrechnung. Flow-/Google-One-Abo zählt nicht. |
| `openai` | OpenAI Sora | `OPENAI_API_KEY` | `sora-2` | API-Guthaben. ChatGPT-Abo zählt nicht. |
| `openrouter` | Viele Modelle über einen Key (Veo, Seedance, Wan, Hailuo 3, Runway u. a.) | `OPENROUTER_API_KEY` | `google/veo-3.1` | OpenRouter-Guthaben. Modellname z. B. `minimax/hailuo-3`, `alibaba/wan-2.7`, `bytedance/seedance-2.0`. |
| `runway` | Runway Gen-4.5 | `RUNWAYML_API_SECRET` | `gen4.5` | Konto auf dev.runwayml.com, API-Credits kaufen (getrennt vom App-Abo). |
| `luma` | Luma Dream Machine (Ray) | `LUMAAI_API_KEY` | `ray-2` | API-Guthaben bei Luma. Startbilder nur als https-Adresse. |
| `kling` | Kling AI | `KLING_ACCESS_KEY` + `KLING_SECRET_KEY` | `kling-v2-5-turbo` | Kling-Entwicklerplattform, Ressourcenpaket kaufen. App-Abo zählt nicht. |
| `minimax` | MiniMax Hailuo | `MINIMAX_API_KEY` | `MiniMax-Hailuo-2.3` | platform.minimax.io, Guthaben. Hailuo-App-Abo zählt nicht. |
| `wan` | Alibaba Wan (DashScope / Model Studio) | `DASHSCOPE_API_KEY` | `wan2.2-t2v-plus`, mit Bild `wan2.2-i2v-plus` | Alibaba Cloud Model Studio (international). Derselbe Key wie für Qwen über DashScope. |
| `seedance` | ByteDance Seedance (BytePlus ModelArk) | `ARK_API_KEY` | `seedance-1-0-pro-250528` | BytePlus-Konto. |
| `higgsfield` | Higgsfield (MiniMax H3, Kling, Wan, Seedance, Hailuo …) | `HIGGSFIELD_API_KEY_ID` + `HIGGSFIELD_API_KEY_SECRET` | `minimax/h3/text-to-video`, mit Bild `minimax/h3/image-to-video` | Key auf console.higgsfield.ai, API-Credits. Ob Abo-Credits der Web-App für die API gelten, vorher prüfen. |
| `fal` | fal.ai (Hunderte Modelle: Kling, Wan, Hailuo, Pika, LTX, PixVerse, Vidu …) | `FAL_KEY` | `minimax/h3-max/text-to-video` (MiniMax H3 Max, 0,03 $/s), mit Bild `fal-ai/wan/v2.2-a14b/image-to-video` | fal.ai-Guthaben. |
| `replicate` | Replicate (viele offene Modelle) | `REPLICATE_API_TOKEN` | `wan-video/wan-2.2-t2v-fast`, mit Bild `…-i2v-fast` | Replicate-Guthaben. Startbild-Feld je Modell: `REPLICATE_IMAGE_FIELD` (Standard `image`). |

**Modell ändern:** `<ANBIETER>_VIDEO_MODEL`, z. B. `KLING_VIDEO_MODEL=kling-v2-1-master` oder `HIGGSFIELD_VIDEO_MODEL=kling/…`.
Für Bild-zu-Video gibt es bei wan/higgsfield/fal/replicate eigene Modelle: `<ANBIETER>_I2V_MODEL`. Das alte `VIDEO_MODEL` gilt weiter für den
ersten Anbieter. Bei Higgsfield ist der Modellname der Pfad aus der Higgsfield-Doku (z. B. `alibaba/wan-3.0/reference-to-video`).
**Zusatzparameter** für fal, replicate, openrouter und higgsfield (jedes Modell hat andere): `FAL_VIDEO_PARAMS={"num_frames": 81}`
(je Anbieter) oder `VIDEO_PARAMS=…` (für alle diese Anbieter). Higgsfield lehnt unbekannte Felder ab, dort nur Felder eintragen, die die Modellseite nennt.

**MiniMax H3 (Hailuo 3):** erreichbar über `fal` (Standard, H3 Max), `higgsfield` (Standard) oder `openrouter` (`OPENROUTER_VIDEO_MODEL=minimax/hailuo-3`).
Auf der eigenen MiniMax-API war der Modellname bei Redaktionsschluss nicht dokumentiert; sobald MiniMax ihn nennt: `MINIMAX_VIDEO_MODEL=…`.

**Was die Agenten angeben:** `prompt`, optional `provider`, `aspect` (16:9, 9:16, 1:1), `resolution` (720p/1080p), `seconds`, `image`
(Startbild im Projekt oder https-Adresse), `name`, `continue_id` (nur gemini und openai). Nicht jeder Anbieter kann alles:
nicht unterstützte Angaben werden weggelassen oder auf den nächsten erlaubten Wert gerundet (z. B. Kling 5 oder 10 s, Sora 4/8/12 s).

## Zusatzdienste

- `video_ai` (fal.ai): Modelle `FAL_UPSCALE_MODEL` (Std. `fal-ai/video-upscaler`), `FAL_LIPSYNC_MODEL` (Std. `fal-ai/sync-lipsync/v2`),
  `FAL_SOUND_MODEL` (Std. `fal-ai/mmaudio-v2`). Videos und Ton gehen als Datei mit (max. 50 MB), vorher mit `video_edit` kürzen.
- `sound_generate`: `AUDIO_PROVIDER=elevenlabs` (`ELEVENLABS_API_KEY`, Geräusche bis 30 s, Musik bis 5 Min) oder `fal`
  (`FAL_AUDIO_MODEL`, Std. `fal-ai/stable-audio`, bis 47 s).
- `speak` mit `TTS_ENGINE=elevenlabs` (`ELEVENLABS_API_KEY`, Stimme `ELEVENLABS_VOICE` oder je Figur als `voice` = Stimmen-ID) oder
  `TTS_ENGINE=openai` (`OPENAI_API_KEY`, Stimme `OPENAI_TTS_VOICE`, z. B. nova, onyx, coral). Damit klingen auch die Figuren im Filmstudio besser.
- **ElevenLabs nur bei Bedarf:** Steht nur `ELEVENLABS_API_KEY` in der `.env` (ohne `TTS_ENGINE=elevenlabs`), bleibt die lokale Stimme
  Standard. Die Agenten sehen dann einen Hinweis und setzen `"engine": "elevenlabs"` im `speak`-Aufruf bzw. in `stimme`/`erzaehler_stimme`
  einer Filmfigur, wenn es gut klingen muss. `{"tool": "speak", "list_voices": true}` listet die Stimmen des Kontos mit ID.
  Scheitert eine Cloud-Stimme, spricht die lokale Stimme mit HINWEIS im Ergebnis (abschaltbar mit `TTS_FALLBACK=0`).

## Was nicht über eine API geht

| Dienst | Stand | Weg |
| --- | --- | --- |
| MagicLight.ai | Keine öffentliche API. | Manuell: Agenten schreiben das Drehbuch, du erzeugst dort und lädst das Video nach `input/` hoch. Oder Browser-Roboter mit deinem Abo (nicht gebaut). |
| Google Flow | Keine API, Abo-Credits gelten nicht für die API. | Das Modell dahinter (Veo) über `gemini` oder `openrouter`. |
| Pika | Keine eigene öffentliche API. | Pika-Modelle über `fal`. |
| Higgsfield-Web-App (Funktionen, die nicht in der API stehen) | Nur in der App. | Browser-Roboter (nicht gebaut) oder manuell. |
| Stability AI (Stable Video) | Kein aktuelles Video-API bekannt. | Offene Modelle über `fal` oder `replicate`. |
| Avatar-Dienste (HeyGen, Synthesia, D-ID) | APIs vorhanden, aber nicht eingebaut. | Sprechende Figuren: `speak` + `video_ai op=lipsync`. Bei Bedarf als eigenen Anbieter nachrüsten. |

## Prüfen

`python selftest.py` zeigt jeden eingeschalteten Videoanbieter mit OK oder FEHLT (Key vorhanden?). Ein echter Clip wird im Selbsttest **nicht**
erzeugt, weil das Geld kostet. Ersten Test bitte selbst anstoßen: im Chat einem Agenten mit Medienrecht „Erzeuge mit video_generate einen
5-Sekunden-Clip: rotes Auto fährt durch eine Pfütze“ schreiben.

**Ehrlich:** Alle Anbieter sind nach der Dokumentation der Anbieter gebaut und nur gegen simulierte Antworten getestet (auch der ältere
Gemini-Weg). Beim ersten echten Aufruf kann ein Feldname oder Modellname abweichen; die Fehlermeldung des Anbieters steht dann im Ergebnis
des Agenten (HTTP-Code + Text), damit lässt es sich schnell anpassen.
