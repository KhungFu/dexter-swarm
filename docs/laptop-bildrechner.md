# Eigener Bildrechner auf einem Windows-Laptop

Hyperstead kann Bilder auf einem eigenen Rechner im Heimnetz erzeugen lassen. Das kostet nichts, geht mit
Referenzbildern (gleiche Figuren über eine Serie) und braucht keine Grafikkarte. Dafür ist es langsam:
auf einem Laptop mit i5-8250U und 8 GB RAM sind mehrere Minuten je Bild zu erwarten.

Software: [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp) (`sd-server`).
Modell: FLUX.2 klein 4B (Apache 2.0, auch kommerziell nutzbar), auf 4 Bit verkleinert.

## Was du brauchst

- Windows 10/11, 64 Bit, mindestens 8 GB RAM, etwa 6 GB freier Platz auf `C:`
- Hyperstead-Ordner auf dem Laptop (für das Einrichtungsskript), z. B. `C:\Users\<Name>\hyperstead` (ältere Installationen: `paperclip-lite`)
- Laptop am Strom, Energiesparen aus

Wichtig: Auf der GitHub-Seite von stable-diffusion.cpp **nicht** die Ordner (`assets`, `docs`, `examples`) anklicken.
Das sind nur Beispielbilder und Quelltext. Das fertige Programm liegt unter „Releases“, und das Skript unten lädt es
von selbst.

## 1. Automatisch einrichten (empfohlen)

1. Startmenü → „PowerShell“ eingeben → **Windows PowerShell** öffnen (normal, nicht als Administrator).
2. Diese Zeilen eingeben, jeweils mit Enter:

   ```powershell
   cd $HOME\hyperstead
   git pull
   powershell -ExecutionPolicy Bypass -File deploy\windows\bildrechner-einrichten.ps1
   ```

3. Das Skript macht sechs Schritte und schreibt zu jedem „ok“ oder einen FEHLER mit Erklärung:
   1. prüft RAM und freien Platz,
   2. lädt das Programm (`sd-server.exe`, Datei `...-bin-win-cpu-x64.zip` aus den Releases) und entpackt es nach `C:\bildrechner\`,
   3. installiert die Microsoft-Laufzeit (VCOMP140.DLL), falls sie fehlt,
   4. lädt die drei Modelldateien (zusammen ca. 5 GB) nach `C:\bildrechner\modelle\`,
   5. legt `C:\bildrechner\bildrechner-start.bat` ab,
   6. fragt nach Administrator-Rechten für die Firewall-Regel (Ja klicken; nur nötig, wenn der Pi Bilder bestellt).
4. Bricht der Download ab: denselben Befehl noch einmal starten. Fertige Dateien werden übersprungen, angefangene
   fortgesetzt.
5. Stürzt der Bildrechner später wegen Speichermangel ab: Skript mit `-Klein` am Ende erneut starten (kleineres
   Sprachmodell, die Startdatei nimmt es dann von selbst).

Danach sieht der Ordner so aus:

```
C:\bildrechner\
  sd-server.exe            (+ weitere .dll/.exe aus der ZIP-Datei)
  bildrechner-start.bat
  modelle\
    flux-2-klein-4b-Q4_0.gguf                 2,46 GB
    Qwen3-4B-Q4_K_M.gguf                      2,5 GB   (mit -Klein: Qwen3-4B-Q3_K_M.gguf, 2,08 GB)
    full_encoder_small_decoder.safetensors    250 MB
```

## 2. Starten und prüfen

1. Doppelklick auf `C:\bildrechner\bildrechner-start.bat`. Ein schwarzes Fenster geht auf, **offen lassen**.
2. 1–2 Minuten warten, bis die Modelle geladen sind. Vorher keine Bilder bestellen: Eine Anfrage während des Ladens
   kann hängen bleiben ([bekannter Fehler](https://github.com/leejet/stable-diffusion.cpp/issues/2081)), dann
   Fenster schließen und neu starten.
3. Test im Browser auf dem Laptop: <http://127.0.0.1:1234> muss eine Seite zeigen.
4. In der `.env` von Hyperstead auf dem Laptop (`notepad .env`) genau diese zwei Zeilen aktiv:

   ```
   IMAGE_PROVIDER=sdcpp
   SDCPP_URL=http://127.0.0.1:1234
   ```

5. Hyperstead neu starten (Startfenster schließen, `deploy\windows\hyperstead-start.bat`) und prüfen:
   `venv\Scripts\python.exe selftest.py web`. Das erzeugt zwei Testbilder und dauert mehrere Minuten.

Meldet die Startdatei „sd-server.exe fehlt“ oder „Modelldatei fehlt“: Schritt 1 wiederholen.

Meldet Windows „VCOMP140.DLL nicht gefunden“: Dem Programm fehlt die Microsoft-Laufzeit. Das Einrichtungsskript
installiert sie seit diesem Stand selbst (Schritt 3 von 6). Vorhandene Einrichtung reparieren: `git pull`, dann das
Skript erneut starten, danach die Startdatei öffnen. Den Fehlerdialog schließt du mit OK. Dabei geht nichts verloren,
das Fenster war nur der Dialog von `sd-server.exe`.

Autostart: Win+R, `shell:startup` eingeben, eine Verknüpfung zu `C:\bildrechner\bildrechner-start.bat` hineinlegen.

## 3. Von Hand einrichten (nur falls das Skript nicht geht)

1. <https://github.com/leejet/stable-diffusion.cpp/releases> öffnen, beim obersten Eintrag „Assets“ aufklappen.
2. Die Datei mit **`bin-win-cpu-x64.zip`** im Namen laden (nicht `cuda`, `rocm`, `vulkan`, nicht „Source code“).
3. Rechtsklick → „Alle extrahieren…“ → Ziel `C:\bildrechner`. Darin muss direkt `sd-server.exe` liegen
   (liegt sie in einem Unterordner: dessen Inhalt nach `C:\bildrechner` verschieben).
4. Ordner `C:\bildrechner\modelle` anlegen und diese drei Dateien hineinladen:

   | Datei | Größe | Link |
   | --- | --- | --- |
   | `flux-2-klein-4b-Q4_0.gguf` | 2,46 GB | <https://huggingface.co/leejet/FLUX.2-klein-4B-GGUF/resolve/main/flux-2-klein-4b-Q4_0.gguf> |
   | `Qwen3-4B-Q4_K_M.gguf` | 2,5 GB | <https://huggingface.co/unsloth/Qwen3-4B-GGUF/resolve/main/Qwen3-4B-Q4_K_M.gguf> |
   | `full_encoder_small_decoder.safetensors` | 250 MB | <https://huggingface.co/black-forest-labs/FLUX.2-small-decoder/resolve/main/full_encoder_small_decoder.safetensors> |

5. `deploy\windows\bildrechner-start.bat` aus dem Hyperstead-Ordner nach `C:\bildrechner\` kopieren.
6. Weiter mit Abschnitt 2.

## 4. Firewall und Energiesparen

Das Skript legt die Firewall-Regel an. Von Hand: Startmenü → „cmd“ → Rechtsklick → **Als Administrator ausführen**,
dann (ohne `cd` davor):

```bat
netsh advfirewall firewall add rule name="Bildrechner sd-server" dir=in action=allow protocol=TCP localport=1234 profile=private
powercfg /change standby-timeout-ac 0
```

Das Heimnetz muss in Windows als **privates** Netzwerk eingestellt sein. `sd-server` hat kein Passwort:
den Port 1234 nie im Router freigeben.

## 5. IP-Adresse des Laptops

`ipconfig` in der Eingabeaufforderung, Zeile „IPv4-Adresse“, z. B. `192.168.1.50`. Im Router am besten
eine feste Adresse für den Laptop einstellen, sonst ändert sie sich irgendwann.

## 6. Hyperstead auf dem Pi (bestellt beim Laptop)

In `.env`:

```
IMAGE_PROVIDER=sdcpp
SDCPP_URL=http://192.168.1.50:1234
IMAGE_STYLE=farbige Buntstiftzeichnung auf Pastellflaeche, sichtbare Strichstruktur
# optional, wenn der Laptop aus ist:
# IMAGE_FALLBACK=pollinations
```

Dann `sudo systemctl restart hyperstead` und `./venv/bin/python selftest.py web`.
Der Selbsttest erzeugt ein Bild und eins mit Referenz, das dauert entsprechend.

## 7. Bildrechner nur als Ersatz (wenn der Hauptanbieter ausfällt)

Du kannst einen anderen Bildanbieter als Standard behalten (z. B. Gemini) und den Bildrechner nur einspringen lassen,
wenn der Hauptanbieter scheitert (Guthaben leer, Kontingent aufgebraucht, Netz). In `.env`:

```
IMAGE_PROVIDER=gemini
SDCPP_URL=http://127.0.0.1:1234      # auf dem Pi: IP des Laptops
IMAGE_FALLBACK=sdcpp                 # oder sdcpp,pollinations: ist auch der Laptop aus, kommt das Gratis-Bild
```

Der Bildrechner bekommt dieselben Referenzbilder, das Ergebnis beginnt mit „NOTE: switched to your own image computer (sdcpp)“.
Ist er aus, steht der Grund in der Meldung. Unter Windows bietet `hyperstead-start.bat` auch in diesem Fall an, ihn zu starten.
Hyperstead neu starten, damit die `.env` gilt.

Weitere Schalter: `SDCPP_SIZE` (längste Bildseite, Standard 1024; 768 ist etwa doppelt so schnell),
`SDCPP_STEPS` (Standard 4), `SDCPP_CFG` (Standard 1.0), `SDCPP_TIMEOUT` (Sekunden, Standard 1800).

## Grenzen

- Die verkleinerte 4B-Fassung zeichnet einfacher als Gemini oder GPT-Image. Für Buntstift-Illustrationen
  reicht sie meist, feine Details und Schrift im Bild gelingen schlecht.
- Referenzbilder halten Figuren ähnlich, aber nicht perfekt gleich. Ein klares Referenzbild je Figur
  (Ganzkörper, neutraler Hintergrund) hilft am meisten.
- Mit Referenzbildern rechnet er länger als ohne.
- Hyperstead schickt immer nur ein Bild gleichzeitig an den Laptop.
