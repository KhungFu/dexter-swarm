"""Hyperstead: Welten und Wachstum.

Eine Welt ist nur ein Paket aus Begriffen, Symbolen, Farben und Stufennamen fuer die Oberflaeche.
Die KI-Agenten sehen nie Spielbegriffe, ihre Prompts bleiben neutral (Auftrag, Bericht, Team).
Punkte werden aus dem Audit-Log berechnet (append-only), daher bekommen alte Projekte ihre Punkte
automatisch nachgeruestet und nichts muss mitgezaehlt werden.
"""

DEFAULT_WORLD = "kosmos"

# Punkte je Ereignis
POINTS = {"done_first": 10, "done_revised": 5, "inbox_closed": 20, "task_failed": -3, "inbox_rework": -5}

# Stufen: ab Punkten, Teamgroesse und Tiefe, die die Fuehrung SELBST anwerben darf (None = keine Grenze)
STAGE_POINTS = [0, 100, 300, 700, 1500]
STAGE_TEAM = [8, 12, 18, 25, None]
STAGE_DEPTH = [2, 3, 4, 5, None]

# Raenge der Agenten nach eigenen abgenommenen Lieferungen
RANK_AT = [0, 5, 20, 60]

# Seit 2026-11-04 gibt es die Welten "Kosmos" und "Atom" (Wunsch ABI): Sonne = oberste Leitung, Planeten = Abteilungen
# bzw. Vorarbeiter, Monde = Mitarbeiter. Fruehere Welten (guild, tycoon, gizmo) werden per world_ok auf Kosmos umgestellt.
WORLDS = {
    "kosmos": {
        "name": "Kosmos", "tagline": "Vom Asteroiden zur Galaxie.",
        "stages": [["☄️", "Asteroid"], ["🪐", "Planet"], ["☀️", "Sonnensystem"], ["✨", "Sternhaufen"], ["🌌", "Galaxie"]],
        "ranks": [["☄️", "Komet"], ["🌙", "Mond"], ["🪐", "Planet"], ["⭐", "Stern"]],
        "words": {"owner": "Kommandant:in", "top": "Sonne", "lead": "Planet", "member": "Mond",
                  "team": "Planet", "teams": "Planeten", "task": "Mission", "tasks": "Missionen",
                  "done": "erfüllt", "project": "Universum", "world": "Sternkarte", "points": "Sternenstaub"},
        "planets": ["Nova", "Orion", "Vega", "Lyra", "Atlas", "Kepler", "Rigel", "Sirius"],
        "colors": {"accent": "#f59e0b", "accent2": "#6366f1", "ground": "#0b1026", "ground_dark": "#070b1a"},
        "explain": "Sonne = oberste Leitung, Planeten = Abteilungen, Monde = Mitarbeiter.",
    },
    # Wunsch ABI 2026-11-04: Atom als zweite Welt. Kern = oberste Leitung, jede Abteilung eine Elektronenschale,
    # Mitarbeiter = Elektronen. Gleiche Punkte und Stufengrenzen wie Kosmos, nur andere Namen.
    "atom": {
        "name": "Atom", "tagline": "Vom Quark zur lebenden Zelle.",
        "stages": [["✴️", "Quark"], ["⚛️", "Atom"], ["🧪", "Molekül"], ["💎", "Kristall"], ["🧬", "Zelle"]],
        "ranks": [["·", "Neutrino"], ["⚡", "Elektron"], ["🔴", "Proton"], ["💠", "Nukleon"]],
        "words": {"owner": "Forscher:in", "top": "Kern", "lead": "Schale", "member": "Elektron",
                  "team": "Schale", "teams": "Schalen", "task": "Experiment", "tasks": "Experimente",
                  "done": "gelungen", "project": "Element", "world": "Atommodell", "points": "Energie"},
        "planets": ["Alpha", "Beta", "Gamma", "Delta", "Sigma", "Omega", "Lambda", "Theta"],
        "colors": {"accent": "#22d3ee", "accent2": "#a855f7", "ground": "#061a24", "ground_dark": "#03101a"},
        "explain": "Kern = oberste Leitung, jede Abteilung = eine Elektronenschale, Mitarbeiter = Elektronen.",
    },
}


def world_ok(w):
    return w if w in WORLDS else DEFAULT_WORLD


def stage_of(points):
    s = 0
    for i, at in enumerate(STAGE_POINTS):
        if points >= at:
            s = i
    return s


def rank_of(done):
    r = 0
    for i, at in enumerate(RANK_AT):
        if done >= at:
            r = i
    return r


def points_from_events(done_rounds, closed, failed, rework):
    """done_rounds: Liste der rounds-Werte je erledigter Lieferung. Nie unter 0."""
    p = sum(POINTS["done_first"] if not r else POINTS["done_revised"] for r in done_rounds)
    p += closed * POINTS["inbox_closed"] + failed * POINTS["task_failed"] + rework * POINTS["inbox_rework"]
    return max(0, p)


def stage_info(points, world=DEFAULT_WORLD, max_depth=8):
    w = WORLDS[world_ok(world)]
    s = stage_of(points)
    nxt = STAGE_POINTS[s + 1] if s + 1 < len(STAGE_POINTS) else None
    low = STAGE_POINTS[s]
    return {
        "stage": s, "stage_count": len(STAGE_POINTS), "icon": w["stages"][s][0], "name": w["stages"][s][1],
        "points": points, "from": low, "next": nxt,
        "next_name": w["stages"][s + 1][1] if nxt is not None else None,
        "next_icon": w["stages"][s + 1][0] if nxt is not None else None,
        "progress": 1.0 if nxt is None else round((points - low) / float(nxt - low), 3),
        "team_limit": STAGE_TEAM[s], "depth_limit": STAGE_DEPTH[s] if STAGE_DEPTH[s] is not None else max_depth,
    }


def rank_info(done, world=DEFAULT_WORLD):
    w = WORLDS[world_ok(world)]
    r = rank_of(done)
    nxt = RANK_AT[r + 1] if r + 1 < len(RANK_AT) else None
    return {"rank": r, "icon": w["ranks"][r][0], "name": w["ranks"][r][1], "done": done, "next": nxt}
