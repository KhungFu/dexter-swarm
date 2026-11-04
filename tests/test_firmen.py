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
    assert 'id="btnHub"' in html and 'data-view="hub"' in html
    assert "stadt:()=>hubCity()" in html and "kosmos:()=>hubCosmos()" in html
    assert "{id:'firmen'" in html and "'/firms'" in html
