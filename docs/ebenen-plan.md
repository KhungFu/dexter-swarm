# Plan: Alle Firmen auf einen Blick (Stadt, Weltall, Molekül)

Wunsch ABI (2026-11-04): eine Ansicht wie SimCity. Jede Firma (= jedes Projekt in Hyperstead) ist ein eigenes Gebäude,
die Gebäude hängen an Straßen. Klick auf eine Firma führt hinein, innen sieht man die Abteilungen. Dasselbe Prinzip im
Weltall: jede Firma ist ein eigenes Sonnensystem, Verbindungen sind zuerst unsichtbar. Arbeiten Firmen zusammen, fliegen
kleine Raumschiffe hin und her. Ähnlich für die anderen Grafiken, nur nicht für das normale Organigramm. Jede dieser
Ansichten gibt es in zwei Aussehen: **klassisch** und **modern**.

## Zwei Ebenen

| Ebene | Was man sieht | Wo |
|---|---|---|
| **Außen: Übersicht** | alle Firmen gleichzeitig | neuer Knopf „🏙 Alle Firmen“ über der Projektliste |
| **Innen: eine Firma** | ihre Abteilungen und Agenten | Klick auf eine Firma in der Übersicht |

## Die Übersicht in drei Welten

| Welt | Firma | Verbindung | Zusammenarbeit | Innen |
|---|---|---|---|---|
| 🏙 Stadt | Gebäude; Höhe nach Wachstumsstufe (Garage bis Hochhaus), Fenster leuchten, wenn gearbeitet wird | Straßen, immer sichtbar | Lieferwagen fahren über die Straße | Querschnitt des Gebäudes: eine Etage je Abteilung, Agenten als Figuren an Tischen |
| 🌌 Weltall | eigenes Sonnensystem (Sonne + Planeten je Abteilung) | unsichtbar | Raumschiffe fliegen zwischen den Sonnen | die bekannte Weltall-Ansicht der Firma |
| ⚛️ Molekül | ein Atom (Kern + Elektronen je Abteilung) | keine | Bindungen zu einem Molekül | die bekannte Atom-Ansicht der Firma |

Das Organigramm bekommt keine Übersicht (Wunsch ABI). Der Bauplan bleibt Werkzeug zum Bearbeiten.

## Klassisch und modern

Ein Schalter in der Übersicht (und in der Gebäude-Innenansicht), gespeichert pro Gerät:

- **Klassisch**: kräftige, flache Farben, dicke Umrisse, Klötzchen-Optik wie ein altes Aufbauspiel; Weltall als
  gezeichnete Sterne, Atom als Lehrbuch-Modell.
- **Modern**: dunkler Grund, Glas und Leuchtkanten, weiche Verläufe; Weltall mit Leuchten, Atom mit Lichtbahnen.

## Was „Zusammenarbeit“ heißt

Bisher arbeiten Firmen in Hyperstead nicht miteinander, jede Firma ist ein abgeschlossenes Projekt. Darum gibt es zuerst
**Partnerschaften, die ABI selbst setzt**: in der Übersicht zwei Firmen wählen und „🤝 Zusammenarbeit“ antippen. Erst dann
erscheinen Raumschiffe, Lieferwagen oder Bindungen. Arbeiten beide Firmen gerade an Aufgaben, wird es lebhafter (mehr
Verkehr). Wenn später Agenten wirklich über Firmengrenzen hinweg arbeiten, hängt sich das an dieselbe Tabelle.

## Technik

- Neue Tabelle `firm_links(id, a, b, note, created)` (a < b, keine Doppelten, Löschen eines Projekts löscht seine Links).
- `GET /api/firms`: alle Firmen mit Stufe, Abteilungen (Teams wie im Weltall), Agentenzahl, laufenden Aufgaben, Partnern.
- `POST /api/firms/links` (`a`, `b`, `note`) und `DELETE /api/firms/links/<id>`, mit Audit-Eintrag.
- Oberfläche: eigenes SVG `#hubsvg` im selben Zoom/Verschieben wie die anderen Grafiken, Ansicht `VIEW='hub'`, Welt
  `HUB.world` (stadt|weltall|molekuel) und `HUB.style` (klassisch|modern) in localStorage. Bewegung nur, wenn
  „Bewegung“ an ist und nicht auf dem Handy (wie bisher). Handy: Liste der Firmen als Karten.
- Jeder neue Knopf bekommt `title` bzw. einen Eintrag in `TIPS`, die Anleitung (`HELP`) ein Kapitel „Alle Firmen“.

## Schritte (je ein PR, Tests grün, Squash-Merge)

1. Dieser Plan.
2. Daten: `firm_links`, `/api/firms`, Partnerschaften setzen/lösen, Tests.
3. Stadt: Übersicht mit Gebäuden und Straßen, Schalter klassisch/modern, Innenansicht mit Etagen je Abteilung, Hilfetexte.
4. Weltall: Firmen als Sonnensysteme, unsichtbare Verbindungen, Raumschiffe bei Zusammenarbeit, Klick öffnet die Firma.
5. Molekül: Firmen als Atome, Bindungen bei Zusammenarbeit, Feinschliff und README.
