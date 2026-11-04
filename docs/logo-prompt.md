# Logo von Hyperstead

Das Logo zeigt ein Molekülnetz aus glänzenden Kugeln und Stäben. Es steht für das Team aus KI-Agenten:

- **Große Kugel in der Mitte (Elektrisch-Blau):** der leitende Agent, der alles koordiniert.
- **Vier mittlere Kugeln (Orange, Türkis, Violett, Grün):** die Teamleitungen.
- **Kleine Kugeln in kräftigen Farben:** die einzelnen Agenten.
- **Weiße, leicht durchscheinende Stäbe:** wer wem unterstellt ist. Jede Verbindung läuft von der Mitte über eine Teamleitung zu ihren Agenten.

Das Netz ist absichtlich unregelmäßig im Raum verteilt wie ein echtes Molekülmodell, nicht als starrer Baum. Hintergrund ist ein dunkles Navy. Es gibt keinen Text und keine Atombahnen.

## Dateien

| Datei | Zweck |
|---|---|
| `static/logo/hyperstead-1024.png` | Großes Logo (z. B. für Präsentationen, Profilbild) |
| `static/logo/hyperstead-512.png` | App-Symbol |
| `static/logo/hyperstead-192.png` | Logo in der Seitenleiste, auf der Anmeldeseite und als Symbol auf dem Handy-Startbildschirm |
| `static/logo/hyperstead-180.png` | Symbol auf iPhone/iPad (Zum Home-Bildschirm) |
| `static/logo/hyperstead-32.png` | Symbol im Browser-Tab |
| `docs/logo/logo_blender.py` | Blender-Skript, das das Logo erzeugt |

## Logo neu erzeugen

Das Logo ist mit Blender (Cycles) gerendert, nicht mit einem Bildgenerator. So lässt es sich jederzeit genau gleich oder mit anderen Farben neu bauen. Farben, Positionen und Größen stehen oben im Skript.

```bash
pip install bpy            # Blender als Python-Paket (Python 3.13), alternativ: blender -b --python ...
python docs/logo/logo_blender.py -- 160 1024 $PWD/logo-1024.png   # Samples, Größe, Zieldatei
```

Danach die kleineren Größen daraus verkleinern (z. B. mit Pillow) und nach `static/logo/` legen.

## Ursprünglicher Auftrag (Prompt)

Mit diesem Text lässt sich das Logo auch in einem Bildgenerator neu entwerfen:

```text
Create a premium, modern 3D molecular network logo for "Hyperstead", an AI agent orchestration platform.
Core concept:
A colorful molecular structure made of glossy spherical nodes connected by smooth cylindrical rods. The structure represents a hierarchical team of autonomous AI agents.
Hierarchy and connections:

* One large central sphere represents the main coordinating AI agent.
* Medium-sized spheres represent subordinate team leaders.
* Smaller spheres represent individual AI agents.
* All spheres are connected through a clear parent-child hierarchy, like an organizational chart.
* Despite the hierarchy, the overall structure should look organically scattered, asymmetrical and spatially interconnected, like a real molecular model.
* Avoid a rigid tree layout, straight horizontal rows or a symmetrical pyramid.
* Connections should be clearly traceable from the central leader to subordinate nodes and their agents.

Colors and appearance:

* Give spheres different vibrant colors according to their size and role.
* Large sphere: bright cyan / electric blue.
* Medium spheres: orange, turquoise, violet and green.
* Small spheres: complementary vivid colors.
* Use glossy 3D surfaces, subtle reflections, soft highlights and smooth white or translucent connecting rods.
* Distinct sphere sizes should make the hierarchy immediately recognizable.

Visual style:
Elegant, clean, futuristic, premium technology branding.
Deep dark navy background.
Beautiful depth and subtle lighting.
Compact, recognizable silhouette suitable for an application icon.
No text, no letters, no atom orbit lines, no chemical symbols, no flat network diagram, no rigid organizational chart, no unnecessary decorative elements.
```
