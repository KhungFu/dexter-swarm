"""Uebersicht aller Firmen (Stadt/Weltall/Molekuel) und Partnerschaften zwischen Firmen."""
import app as A
from conftest import make_agent, make_project, make_task


def test_firmen_uebersicht(client):
    p1, p2 = make_project("Baeckerei"), make_project("Druckerei")
    chef = make_agent(p1, "Chef")
    make_agent(p1, "Ofen", parent=chef)
    make_task(p1, chef, status="running")
    d = client.get("/api/firms").json
    f = {x["id"]: x for x in d["firms"]}
    assert set(f) >= {p1, p2}
    assert f[p1]["name"] == "Baeckerei" and f[p1]["stage_name"]
    assert f[p1]["busy"] == 1 and f[p2]["busy"] == 0
    assert [a["name"] for a in f[p1]["agents"]] == ["Chef", "Ofen"]
    assert f[p1]["agents"][1]["parent_id"] == chef and f[p1]["agents"][0]["busy"] == 1
    assert f[p1]["stage"] == 0 and f[p1]["icon"] and f[p1]["partners"] == []
    # keine Geheimnisse/Einstellungen der Agenten in der Uebersicht
    assert "perms" not in f[p1]["agents"][0] and "provider" not in f[p1]["agents"][0]


def test_partnerschaft_setzen_und_loesen(client):
    p1, p2 = make_project("A"), make_project("B")
    r = client.post("/api/firms/links", json={"a": p2, "b": p1, "note": "Lieferung"})
    assert r.status_code == 200
    lid = r.json["id"]
    # doppelt (auch umgekehrt) legt nichts Neues an
    assert client.post("/api/firms/links", json={"a": p1, "b": p2}).json == {"id": lid, "exists": True}
    d = client.get("/api/firms").json
    f = {x["id"]: x for x in d["firms"]}
    assert f[p1]["partners"] == [p2] and f[p2]["partners"] == [p1]
    assert d["links"][0]["a"] == min(p1, p2) and d["links"][0]["note"] == "Lieferung"
    assert A.q1("SELECT 1 FROM audit WHERE event='firm_link'")
    assert client.delete(f"/api/firms/links/{lid}").status_code == 200
    assert client.get("/api/firms").json["links"] == []
    assert client.delete(f"/api/firms/links/{lid}").status_code == 404


def test_partnerschaft_pruefungen(client):
    p1 = make_project("A")
    assert client.post("/api/firms/links", json={"a": p1, "b": p1}).status_code == 400
    assert client.post("/api/firms/links", json={"a": p1, "b": 9999}).status_code == 404
    assert client.post("/api/firms/links", json={"a": "x", "b": p1}).status_code == 400


def test_projekt_loeschen_entfernt_partnerschaft(client):
    p1, p2 = make_project("A"), make_project("B")
    client.post("/api/firms/links", json={"a": p1, "b": p2})
    client.delete(f"/api/projects/{p1}")
    assert client.get("/api/firms").json["links"] == []


def test_oberflaeche_stadt_und_kosmos():
    """Moderne Ebene: Umschalter Klassisch/Stadt/Kosmos mit Hilfetexten, Anleitungskapitel, Zeichnung je Welt."""
    import os
    import re
    html = open(os.path.join(os.path.dirname(__file__), "..", "static", "index.html"), encoding="utf-8").read()
    bar = html[html.index('id="hubbar"'):html.index('id="hubcard"')]
    for b in ('id="hubClassic"', 'data-hubworld="stadt"', 'data-hubworld="kosmos"'):
        assert b in bar
    assert all("title=" in t for t in re.findall(r"<button\b[^>]*>", bar))
    assert 'data-view="hub"' in html
    assert "stadt:()=>hubCity()" in html and "kosmos:()=>hubCosmos()" in html
    assert "{id:'firmen'" in html and "'/firms'" in html


def test_oberflaeche_hineinzoomen_und_suche():
    """Phase 2: Firma betreten (Etagen bzw. Planeten), Abteilungsliste, Suche, alles mit Hilfetext."""
    import os
    import re
    html = open(os.path.join(os.path.dirname(__file__), "..", "static", "index.html"), encoding="utf-8").read()
    for fn in ("function hubInsideCity(", "function hubInsideCosmos(", "function hubEnter(", "function hubDep(", "function hubLeave("):
        assert fn in html
    assert 'id="hubOut"' in html and 'id="hubSearch"' in html and 'aria-label="Firma oder Agent suchen"' in html
    assert 'id="hubdeps"' in html
    hub = html[html.index("function hubDepsList("):html.index("/* ---------- Atom: Kern")]
    assert all("title=" in t for t in re.findall(r"<button\b[^>]*>", hub))
    assert "Abteilung öffnen" in html and "Hineingehen" in html


def test_oberflaeche_zusammenarbeit():
    """Phase 3: Strassen/Raumschiffe nur aus Partnerschaften, Dialog mit Hilfetexten."""
    import os
    import re
    html = open(os.path.join(os.path.dirname(__file__), "..", "static", "index.html"), encoding="utf-8").read()
    for fn in ("function hubCityRoads(", "function hubCosmosRoutes(", "function showFirmLinks(", "function hubTraffic("):
        assert fn in html
    roads = html[html.index("function hubCityRoads("):html.index("function hubCosmosRoutes(")]
    assert "HUB.d.links.forEach" in roads  # Strassen entstehen nur aus Partnerschaften
    dlg = html[html.index("async function showFirmLinks("):html.index("$('#hubLink').onclick")]
    assert all("title=" in t for t in re.findall(r"<button\b[^>]*>", dlg))
    assert "'/firms/links'" in dlg and 'id="hubLink"' in html and "['Zusammenarbeit','firmen']" in html


def test_projekte_menue_neu_und_ansichten():
    """Projekte: anlegen (leer oder Vorlage) in einem Fenster, Ansicht Klassisch/Stadt/Kosmos als Oberpunkt."""
    import os
    import re
    html = open(os.path.join(os.path.dirname(__file__), "..", "static", "index.html"), encoding="utf-8").read()
    side = html[html.index('<div class="side-h"><span>Projekte'):html.index('id="projlist"')]
    for b in ('id="btnNewProj"', 'data-pview="classic"', 'data-pview="stadt"', 'data-pview="kosmos"'):
        assert b in side
    assert "＋ Neues Projekt" in side and 'id="btnHub"' not in html and 'id="btnTplProj"' not in html
    assert all("title=" in t for t in re.findall(r"<button\b[^>]*>", side))
    dlg = html[html.index("async function newProjectDialog("):html.index("toast('Firma gegründet.')")]
    assert "'/projects','POST'" in dlg and "/templates" in dlg and "/projects/from_template" in dlg
    menu = html[html.index('id="gViewMenu"'):html.index('id="gTheme"')]
    assert menu.index("Alle Projekte") < menu.index('data-hubworld="stadt"') < menu.index("Dieses Projekt") < menu.index('data-view="world"')


def test_welten_grafik_nach_referenzbild():
    """Stadt mit Baustil je Firma und Straßen nur durch Gassen, Gebäude innen mit der Leitung ganz oben, Abteilungssymbole."""
    import os
    html = open(os.path.join(os.path.dirname(__file__), "..", "static", "index.html"), encoding="utf-8").read()
    for fn in ("function hubStyle(", "function isoBox(", "function hubRoadPath(", "function hubDepIcon(", "function hubOrgChart(", "function hubSunSvg("):
        assert fn in html
    inner = html[html.index("function hubInsideCity("):html.index("function hubInsideCosmos(")]
    # Leitung ist die erste Etage und wird oben (y=-H) begonnen
    assert "floors=[{dep:-1, name:'Leitung'" in inner and "let y=-H;" in inner and "'Chefetage'" in inner
    assert "hubOrgChart(T," in inner
    # Raumschiff-Spur nur bei aktiver Zusammenarbeit
    routes = html[html.index("function hubCosmosRoutes("):html.index("function hubAlong(")]
    assert "if(T.live) veh.unshift(`<path class=\"sroute\"" in routes


def test_welten_bewegung_und_lesbare_namen():
    """Wunsch ABI: alles dreht sich (auch am Handy und innen), Namen lesbar, keine Firmensymbole, Sonne wächst."""
    import os
    html = open(os.path.join(os.path.dirname(__file__), "..", "static", "index.html"), encoding="utf-8").read()
    moving = html[html.index("function hubMoving("):html.index("function hubTick(")]
    assert "innerWidth" not in moving
    assert "HUB.mv.push({rx:r, ry, a0:a" in html[html.index("function hubInsideCosmos("):]
    assert "var(--lz,1)" in html and "setProperty('--lz'" in html
    assert 'class="badge"' not in html[html.index("function hubBuilding("):html.index("function hubCity(")]
    assert "function hubSunR(" in html
