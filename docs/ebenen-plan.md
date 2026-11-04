# Plan: zwei Ebenen – klassisch und modern (Stadt, Kosmos)

Wunsch ABI (2026-11-04, mit Konzeptbild): Hyperstead bekommt zwei Ebenen der Darstellung. Beide zeigen **dieselben
echten Daten** (Firmen, Abteilungen, Agenten, Aufgaben, Zusammenarbeit), nur anders gezeichnet.

| Ebene | Was | Zweck |
|---|---|---|
| **Klassisch** | die bisherigen Ansichten einer Firma: Organigramm (Baum, Gliederung, Kreis), Bauplan, Weltall, Atom | sachlich verwalten und einstellen, bleibt unverändert |
| **Modern** | eine Welt mit **allen** Firmen: 🏙 Stadt oder 🌌 Kosmos | erleben, wie die Firmen aufgebaut sind und arbeiten |

Firma = Projekt in Hyperstead. Umschalter oben in der modernen Welt: **📐 Klassisch · 🏙 Stadt · 🌌 Kosmos**.
Eingang (seit 2026-11-04, Wunsch ABI): „Projekte“ ist der Oberpunkt. Links darunter die Ansichten 📐 Klassisch · 🏙 Stadt · 🌌 Kosmos und „＋ Neues Projekt“; die Grafik-Auswahl ist gegliedert in „Alle Projekte · modern“ und „Dieses Projekt · klassisch“.

## Stadt (wie SimCity, isometrisch)

- Jede Firma ist ein eigenes Gebäude auf eigenem Grundstück: Höhe nach Wachstumsstufe, Farbe je Firma,
  Fenster leuchten, wenn dort gearbeitet wird. Dunkler Grund, Leuchtkanten, weiche Schatten (Richtung Konzeptbild).
- **Straßen nur zwischen Firmen, die zusammenarbeiten.** Firmen ohne Verbindung werden nicht künstlich verbunden.
- Lieferwagen fahren über diese Straßen, mehr Verkehr bei mehr Aktivität.
- **Hineingehen:** Klick auf ein Gebäude zoomt hinein. Innen: ganz oben die Leitung (Chefetage), darunter eine Etage je Abteilung, rechts das Organigramm,
  Agenten an Tischen (leuchtender Bildschirm = arbeitet). Links eine Liste der Abteilungen zum Anklicken.

## Kosmos

- Jede Firma ist ein eigenes Sonnensystem: Sonne = Leitung, Planeten = Abteilungen, Monde = Agenten.
- **Am Anfang keine Linien.** Erst bei Zusammenarbeit fliegen kleine Raumschiffe zwischen den Sonnen,
  bei mehr Aktivität häufiger. Ruhende Partnerschaften bleiben unauffällig.
- **Hineinzoomen:** Klick auf ein Sonnensystem vergrößert es, die Abteilungen werden sichtbar (mit Liste wie im Bild).

## Gemeinsam für beide Welten

- Keine eigene Datenstruktur je Welt: alles kommt aus `GET /api/firms` (Projekte, Agenten mit Chef, laufende Arbeit,
  Stufe, Partnerschaften). Änderst du in der klassischen Ansicht ein Team, sieht die Stadt es beim nächsten Abruf.
- Klick auf einen Agenten öffnet seine echte Karte (Aufgaben, Status, Rechte) wie in der klassischen Ansicht.
  Was du dort änderst, gilt überall.
- Suche nach Firmen und Agenten, Infofenster beim Auswählen, Zoomen und Verschieben wie bisher.
- Neue Welten (Inseln, Fabrik, Ökosystem) sollen später nur eine weitere Zeichenfunktion sein (`HUB_WORLDS`).
- Bewegung nur mit eingeschaltetem „Bewegung“, auch auf dem Handy (sparsamer) und im geöffneten Sonnensystem. Jeder neue Knopf hat einen Hilfetext,
  die Anleitung ein Kapitel „Alle Firmen“.

## Was „Zusammenarbeit“ heißt

Bisher arbeiten Firmen in Hyperstead nicht über Projektgrenzen hinweg. Darum legt ABI Partnerschaften zuerst selbst
an (🤝 Zusammenarbeit, Tabelle `firm_links`). Die Stärke des Verkehrs kommt aus der echten Aktivität beider Firmen.
Arbeiten Agenten später wirklich firmenübergreifend, schreibt das in dieselbe Tabelle.

## Stand

Alle Schritte gebaut (2026-11-04): #8/#9 Plan und Daten, #13 Phase 1, #15 Phase 2, danach Phase 3. Auf Pi/Laptop noch ungetestet.

## Schritte (je ein PR, Tests grün, Squash-Merge)

1. Dieser Plan.
2. Daten: `firm_links`, `/api/firms`, Partnerschaften setzen und lösen, Tests.
3. Phase 1: Stadt und Kosmos als Übersicht, Umschalter Klassisch / Stadt / Kosmos, Hilfetexte.
4. Phase 2: Hineinzoomen, Abteilungen öffnen (Etagen bzw. Planeten, Liste), Infofenster, Suche.
5. Phase 3: Zusammenarbeit: Straßen, Lieferwagen und Raumschiffe nach echter Aktivität, README.
