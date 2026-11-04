"""Uebersicht aller Firmen (Stadt/Weltall/Molekuel) und Partnerschaften zwischen Firmen."""
import os
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
    """Moderne Ebene: Zusammenarbeit/Suche mit Hilfetexten, Anleitungskapitel, Zeichnung je Welt."""
    import os
    import re
    html = open(os.path.join(os.path.dirname(__file__), "..", "static", "index.html"), encoding="utf-8").read()
    bar = html[html.index('id="hubbar"'):html.index('id="hubcard"')]
    for b in ('id="hubLink"', 'id="hubOut"', 'id="hubSearch"'):
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
    hub = html[html.index("function hubDepsList("):html.index("/* ---------- Atom: Molekül")]
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
    """Wunsch ABI 2026-11-04 (Bilder): großer Knopf „＋ Neues Projekt“, kein 🏙 links, Grafik-Menü in Klassik und Modern."""
    import re
    html = open(os.path.join(os.path.dirname(__file__), "..", "static", "index.html"), encoding="utf-8").read()
    side = html[html.index('<div class="side-h"><span>Projekte'):html.index('id="projlist"')]
    assert 'id="btnNewProj"' in side and "＋ Neues Projekt</button>" in side and 'id="btnHub"' not in html
    assert all("title=" in t for t in re.findall(r"<button\b[^>]*>", side))
    dlg = html[html.index("async function newProjectDialog("):html.index("toast('Firma gegründet.')")]
    assert "'/projects','POST'" in dlg and "/templates" in dlg and "/projects/from_template" in dlg
    menu = html[html.index('id="gViewMenu"'):html.index('id="gTheme"')]
    k, m = menu.index(">Klassik<"), menu.index(">Modern<")
    for org in ("baum", "gliederung", "kreis"):
        assert k < menu.index(f'data-org="{org}"') < m
    for v in ('data-hubworld="stadt"', 'data-hubworld="kosmos"', 'data-hubworld="molekuel"'):
        assert menu.index(v) > m
    # Weltall und Molekuel je Projekt sind weg (Wunsch ABI), alte gespeicherte Ansichten fallen auf das Organigramm zurueck
    assert 'data-view="world"' not in menu and 'data-view="atom"' not in menu
    assert "if(!['org','plan','hub'].includes(v)) v='org';" in html
    # moderne Ansicht: die normale obere Leiste bleibt, eigener Welt-Umschalter ist weg
    assert 'id="hubClassic"' not in html and '#app.view-hub #growth' not in html


def test_welten_grafik_nach_referenzbild():
    """Stadt mit Baustil je Firma und Straßen nur durch Gassen, Gebäude innen mit der Leitung ganz oben, Abteilungssymbole."""
    import os
    html = open(os.path.join(os.path.dirname(__file__), "..", "static", "index.html"), encoding="utf-8").read()
    for fn in ("function hubStyle(", "function isoBox(", "function hubRoadPath(", "function hubDepIcon(", "function hubOrgChart(", "function hubSunSvg("):
        assert fn in html
    inner = html[html.index("function hubInsideCity("):html.index("function hubInsideCosmos(")]
    # eine Etage je Hierarchie-Ebene, Ebene 0 (Leitung) ganz oben, ein Raum je Person
    assert "hubLevels(f)" in inner and "top=-H+l*RH" in inner and "'Chefetage'" in inner and 'class="pers room' in inner
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


def test_hierarchie_ebenen_im_gebaeude(tmp_path):
    """Ebenen beliebig tief: hubLevels rechnet Ebene und Abteilung je Agent (per Node nachgerechnet, falls vorhanden)."""
    import os
    import shutil
    import subprocess
    html = open(os.path.join(os.path.dirname(__file__), "..", "static", "index.html"), encoding="utf-8").read()
    if not shutil.which("node"):
        return
    def fn(name):
        i = html.index("function " + name + "(")
        j = html.index("\nfunction ", i + 10)
        return html[i:j]
    js = fn("hubTeams") + "\n" + fn("hubLevels") + """
const f={agents:[{id:1,parent_id:null},{id:2,parent_id:1},{id:3,parent_id:1},{id:4,parent_id:2},{id:5,parent_id:4},{id:6,parent_id:5},{id:7,parent_id:3}]};
const L=hubLevels(f); console.log(JSON.stringify([L.max,L.lvl[6],L.dep[6],L.dep[7],L.lvl[1],L.dep[1]]));"""
    p = tmp_path / "t.js"
    p.write_text(js, encoding="utf-8")
    out = subprocess.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8").stdout.strip()
    assert out == "[4,4,0,1,0,-1]"


def test_stadt_lichter_und_atom_molekuel():
    """Wunsch ABI 2026-11-04: Lichter nur bei arbeitenden Firmen, Atom als Molekül-Netzwerk mit Organigramm-Stäben."""
    html = open(os.path.join(os.path.dirname(__file__), "..", "static", "index.html"), encoding="utf-8").read()
    bld = html[html.index("function hubBuilding("):html.index("function hubCity(")]
    assert "busy?" in bld and ":.07" in bld
    box = html[html.index("function isoBox("):html.index("function hubBuilding(")]
    assert 'style="fill:' in box  # CSS .win überdeckt sonst das fill-Attribut
    atom = html[html.index("const ATOM"):html.index("/* ---------- Start")]
    assert "function molLayout(" in atom and "function molStyle(" in atom and 'class="abond"' in atom
    assert "aorbit\" rx" not in atom.split("function atomSky(")[0]  # keine Elektronenbahnen mehr
    assert "requestAnimationFrame" not in atom


def test_firmenlogo_hochladen_zeigen_entfernen(client):
    """Wunsch ABI 2026-11-04: Firmen bekommen ein eigenes Logo (nur PNG/JPEG/WebP, kein SVG), sichtbar in Stadt und Kosmos."""
    import io
    pid = make_project("Logo GmbH")
    png = b"\x89PNG\r\n\x1a\n" + b"\0" * 64
    assert client.get(f"/api/projects/{pid}/logo").status_code == 404
    f = next(x for x in client.get("/api/firms").json["firms"] if x["id"] == pid)
    assert f["logo"] == 0
    r = client.post(f"/api/projects/{pid}/logo", data={"file": (io.BytesIO(png), "logo.svg")}, content_type="multipart/form-data")
    assert r.status_code == 200 and r.json["logo"] > 0  # Art kommt aus den Bytes, nicht aus dem Namen
    assert (A.proj_dir(pid) / ".logo.png").is_file()  # versteckt: Agenten, Webseite und ZIP sehen es nicht
    g = client.get(f"/api/projects/{pid}/logo")
    assert g.status_code == 200 and g.mimetype == "image/png" and "sandbox" in g.headers["Content-Security-Policy"]
    assert next(x for x in client.get("/api/firms").json["firms"] if x["id"] == pid)["logo"] > 0
    # SVG/HTML und zu grosse Dateien werden abgelehnt
    bad = client.post(f"/api/projects/{pid}/logo", data={"file": (io.BytesIO(b"<svg onload=alert(1)>"), "x.png")}, content_type="multipart/form-data")
    assert bad.status_code == 400
    big = client.post(f"/api/projects/{pid}/logo", data={"file": (io.BytesIO(png + b"\0" * A.LOGO_MAX), "x.png")}, content_type="multipart/form-data")
    assert big.status_code == 400
    # Wechsel auf JPEG ersetzt das PNG
    jpg = b"\xff\xd8\xff\xe0" + b"\0" * 32
    client.post(f"/api/projects/{pid}/logo", data={"file": (io.BytesIO(jpg), "a.jpg")}, content_type="multipart/form-data")
    assert client.get(f"/api/projects/{pid}/logo").mimetype == "image/jpeg" and not (A.proj_dir(pid) / ".logo.png").exists()
    assert client.delete(f"/api/projects/{pid}/logo").json["ok"]
    assert client.get(f"/api/projects/{pid}/logo").status_code == 404
    html = open(os.path.join(os.path.dirname(__file__), "..", "static", "index.html"), encoding="utf-8").read()
    assert html.count("hubLogo(f,") >= 4 and 'id="hubLogoUp"' in html


def test_logo_bytes_erkennung():
    assert A.logo_kind(b"RIFF\0\0\0\0WEBPVP8 ") == "webp"
    assert A.logo_kind(b"GIF89a") is None and A.logo_kind(b"") is None


def test_molekuel_welt_jede_firma_anders():
    """Wunsch ABI 2026-11-04: jede Firma ein eigenes Molekül (Saat = Projekt-ID), Partner per Bindung vernetzt."""
    html = open(os.path.join(os.path.dirname(__file__), "..", "static", "index.html"), encoding="utf-8").read()
    assert "molekuel:()=>hubMolecules()" in html and 'data-hubworld="molekuel"' in html
    mol = html[html.index("function hubMolecules("):html.index("function hubPlace(")]
    assert "molStyle(f.id" in mol and "hubMolBonds(pos)" in mol and "HUB.d.links" in mol and "function hubInsideMol(" in mol
    assert "requestAnimationFrame" not in mol  # Moleküle stehen still, nur Funken laufen über die Haupt-Animation
    style = html[html.index("function molStyle("):html.index("function molLayout(")]
    for k in ("spread", "bond", "squash", "turn", "mid", "small"):
        assert k + ":" in style
    assert "molStyle(S.pid" in html  # Atom-Ansicht nutzt dasselbe Molekül der Firma


def test_agenten_leiste_in_jeder_grafik():
    """Die Leiste „Agent hinzufügen“ bleibt in Organigramm, Bauplan und moderner Ansicht sichtbar (Wunsch ABI)."""
    import os
    import re
    html = open(os.path.join(os.path.dirname(__file__), "..", "static", "index.html"), encoding="utf-8").read()
    css = html[:html.index("</style>")]
    assert not re.search(r"#app\.view-\w+ #palette[,{]", css)
    assert "if(VIEW!=='plan'){ addAgent(k); return; }" in html and "if(x==null)" in html


def test_hub_drehen_und_neigen():
    """Stadt/Kosmos/Molekül lassen sich drehen und neigen, Beschriftungen drehen zurück (Wunsch ABI)."""
    import os
    import re
    html = open(os.path.join(os.path.dirname(__file__), "..", "static", "index.html"), encoding="utf-8").read()
    for b in ("hRotL", "hRotR", "hTiltUp", "hTiltDn", "hCam0"):
        tag = re.search(r'<button[^>]*id="%s"[^>]*>' % b, html)
        assert tag and "title=" in tag.group(0)
    assert "function hubTurn(" in html and "function hubCamApply(" in html and "rotateX(" in html
    assert "#hubsvg text{transform-box:view-box;transform:rotate(calc(var(--hrot) * -1deg))}" in html
    assert "drag.type==='turn'" in html and "hs-hubcam" in html
    # Texte im Hub haben kein eigenes transform-Attribut (sonst ueberschreibt die CSS-Rueckdrehung es)
    hub = html[html.index("const HUB = {"):html.index("const ATOM")]
    assert not re.search(r"<text[^>]*transform=", hub)
