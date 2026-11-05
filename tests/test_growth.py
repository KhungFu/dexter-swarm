"""Hyperstead: Welten, Punkte, Stufen, Raenge und Anwerbe-Grenzen."""
import app as A
import growth as G
from conftest import drain, make_agent, make_project, make_task


def _done(pid, aid, rounds=0, n=1):
    for _ in range(n):
        tid = make_task(pid, aid, status="done")
        A.ex("UPDATE tasks SET rounds=? WHERE id=?", (rounds, tid))
        A.log("task_done", "x", pid, aid, tid)


def test_stufen_und_raenge_rein():
    assert G.stage_of(0) == 0 and G.stage_of(99) == 0 and G.stage_of(100) == 1 and G.stage_of(5000) == 4
    assert G.rank_of(4) == 0 and G.rank_of(5) == 1 and G.rank_of(60) == 3
    assert G.points_from_events([0, 0, 2], 1, 1, 1) == 10 + 10 + 5 + 20 - 3 - 5
    assert G.points_from_events([], 0, 5, 0) == 0  # nie negativ
    i = G.stage_info(150, "kosmos")
    assert i["name"] == "Planet" and i["next"] == 300 and 0 < i["progress"] < 1
    assert G.stage_info(9999, "kosmos")["next"] is None and G.stage_info(9999)["name"] == "Galaxy"
    assert G.world_ok("quatsch") == G.DEFAULT_WORLD == "kosmos"
    assert list(G.WORLDS) == ["kosmos", "atom"]  # Kosmos und Atom (Wunsch ABI 2026-11-04)
    for w in G.WORLDS.values():  # jede Welt hat alle Stufen und Raenge
        assert len(w["stages"]) == len(G.STAGE_POINTS) and len(w["ranks"]) == len(G.RANK_AT)


def test_punkte_aus_dem_audit_log(client):
    pid = make_project()
    ceo = make_agent(pid, "CEO")
    _done(pid, ceo, n=9)          # 90
    _done(pid, ceo, rounds=1)     # +5
    A.log("inbox_closed", "x", pid, ceo)   # +20
    A.log("inbox_rework", "x", pid, ceo)   # -5
    A.log("task_failed", "x", pid, ceo)    # -3
    g = client.get(f"/api/projects/{pid}/growth").json
    assert g["points"] == 107 and g["stage"] == 1 and g["world"] == "kosmos" and g["name"] == "Planet"
    assert g["ranks"][str(ceo)]["rank"] == 1 and g["ranks"][str(ceo)]["done"] == 10


def test_welt_wechseln(client):
    pid = make_project()
    r = client.put(f"/api/projects/{pid}/world", json={"world": "kosmos"})
    assert r.json["world"] == "kosmos" and r.json["name"] == "Asteroid"
    assert client.put(f"/api/projects/{pid}/world", json={"world": "guild"}).status_code == 400
    assert client.put(f"/api/projects/{pid}/world", json={"world": "mars"}).status_code == 400
    assert client.put(f"/api/projects/{pid}/world", json={"limits": False}).json["limits"] is False
    assert client.get("/api/worlds").json["worlds"]["kosmos"]["stages"][4][1] == "Galaxy"
    r = client.put(f"/api/projects/{pid}/world", json={"world": "atom"})
    assert r.json["world"] == "atom" and r.json["name"] == "Quark"
    assert client.get(f"/api/projects/{pid}/growth").json["world"] == "atom"


def test_alte_welten_werden_kosmos():
    """Projekte mit frueherer Welt (Gilde, Tycoon, Gizmo-Stadt) zeigen automatisch Kosmos."""
    pid = make_project()
    for old in ("guild", "tycoon", "gizmo"):
        A.set_setting(f"world:{pid}", old)
        assert A.project_growth(pid)["world"] == "kosmos"


def test_aufstieg_wird_einmal_gemeldet(monkeypatch):
    sent = []
    monkeypatch.setattr(A, "tg_notify", lambda text, *a, **k: sent.append(text))
    pid = make_project()
    ceo = make_agent(pid, "CEO")
    _done(pid, ceo, n=3)           # erster Aufruf merkt nur den Stand
    assert not sent
    _done(pid, ceo, n=7)           # 100 Punkte -> Stufe 2
    assert len(sent) == 1 and "Planet" in sent[0]
    _done(pid, ceo, n=1)
    assert len(sent) == 1
    assert A.q1("SELECT COUNT(*) c FROM audit WHERE event='stage_up'")["c"] == 1


def test_neue_stufe_ohne_meldung_beim_nachruesten(monkeypatch):
    """Ein altes Projekt mit vielen Erfolgen startet still auf der passenden Stufe."""
    sent = []
    monkeypatch.setattr(A, "tg_notify", lambda text, *a, **k: sent.append(text))
    pid = make_project()
    ceo = make_agent(pid, "CEO")
    for i in range(40):  # Verlauf ohne growth_check (wie vor dem Update)
        tid = make_task(pid, ceo, status="done")
        A.ex("INSERT INTO audit(ts,project_id,agent_id,task_id,event,detail) VALUES(0,?,?,?,'task_done','')", (pid, ceo, tid))
    assert A.growth_check(pid) is None and not sent
    assert A.project_growth(pid)["stage"] == 2


def test_anwerben_haengt_von_der_stufe_ab():
    pid = make_project()
    ceo = A.q1("SELECT * FROM agents WHERE id=?", (make_agent(pid, "CEO", recruit=True),))
    notes = []
    people = [{"name": f"P{i}"} for i in range(12)]
    A.recruit_team(ceo, {"id": pid, "name": "x"}, people, notes)
    assert A.q1("SELECT COUNT(*) c FROM agents WHERE project_id=?", (pid,))["c"] == G.STAGE_TEAM[0]
    assert any("nicht eingestellt" in n for n in notes)


def test_anwerben_tiefe_begrenzt():
    pid = make_project()
    ceo = A.q1("SELECT * FROM agents WHERE id=?", (make_agent(pid, "CEO", recruit=True),))
    chain = [{"name": "A"}, {"name": "B", "reports_to": "A"}, {"name": "C", "reports_to": "B"}]
    notes = []
    A.recruit_team(ceo, {"id": pid, "name": "x"}, chain, notes)
    c = A.q1("SELECT * FROM agents WHERE name='C'")
    assert A.agent_depth(c["id"]) <= G.STAGE_DEPTH[0]
    assert c["parent_id"] == ceo["id"]


def test_grenzen_abschaltbar(client):
    pid = make_project()
    client.put(f"/api/projects/{pid}/world", json={"limits": False})
    ceo = A.q1("SELECT * FROM agents WHERE id=?", (make_agent(pid, "CEO", recruit=True),))
    A.recruit_team(ceo, {"id": pid, "name": "x"}, [{"name": f"P{i}"} for i in range(12)], [])
    assert A.q1("SELECT COUNT(*) c FROM agents WHERE project_id=?", (pid,))["c"] == 13


def test_echter_lauf_gibt_punkte():
    pid = make_project()
    ceo = make_agent(pid, "CEO")
    make_task(pid, ceo)
    drain()
    assert A.project_points(pid) >= 10


def test_prompts_ohne_spielbegriffe():
    """Die Welt ist nur Oberflaeche: die Agenten-Prompts nennen keine Spielbegriffe."""
    pid = make_project()
    ceo = A.q1("SELECT * FROM agents WHERE id=?", (make_agent(pid, "CEO", delegate=True),))
    make_agent(pid, "M", parent=ceo["id"])
    text = str(A.build_system(ceo, q_proj(pid), "plan"))
    for w in ("Sonne", "Planet", "Mond", "Mission", "Sternenstaub", "Galaxie", "Stardust", "Galaxy", "Quark", "Elektron", "Electron", "Molekül", "Molecule", "Nukleon", "Nucleon"):
        assert w not in text
    A.set_setting(f"world:{pid}", "atom")
    text = str(A.build_system(ceo, q_proj(pid), "plan"))
    for w in ("Quark", "Elektron", "Electron", "Molekül", "Molecule", "Experiment", "Nukleon", "Nucleon"):
        assert w not in text


def q_proj(pid):
    return A.q1("SELECT * FROM projects WHERE id=?", (pid,))


def test_betriebszentrale(client):
    """Betriebszentrale zeigt nur vorhandene Daten: laufend, Fehler, Freigaben, Zeitplaene, Kosten."""
    pid = make_project()
    ceo = make_agent(pid, "CEO")
    make_task(pid, ceo, status="running")
    bad = make_task(pid, ceo, status="failed")
    A.ex("UPDATE tasks SET result='Zeitlimit', updated=? WHERE id=?", (A.time.time(), bad))
    A.ex("INSERT INTO approvals(project_id,task_id,agent_id,kind,payload,created) VALUES(?,?,?,'publish','',?)",
         (pid, bad, ceo, A.time.time()))
    A.ex("INSERT INTO schedules(project_id,agent_id,title,at,created) VALUES(?,?,'Morgenrunde','09:00',0)", (pid, ceo))
    A.ex("INSERT INTO llm_calls(ts,project_id,agent_id,provider,model,tokens,cost) VALUES(?,?,?,'openai','x',100,0.5)",
         (A.time.time(), pid, ceo))
    A.log("task_failed", "kaputt", pid, ceo, bad)
    r = client.get(f"/api/projects/{pid}/ops").json
    assert [t["status"] for t in r["active"]] == ["running"]
    assert r["failed"][0]["error"] == "Zeitlimit" and r["approvals"][0]["kind"] == "publish"
    assert r["schedules"][0]["title"] == "Morgenrunde"
    assert r["cost_today"]["cost"] == 0.5 and r["cost_week"]["calls"] == 1
    assert r["errors"][0]["event"] == "task_failed" and r["open"] is True
    g = client.get(f"/api/projects/{pid}/growth").json
    assert g["cost_today"] == 0.5 and g["calls_today"] == 1
    assert client.get("/api/projects/99999/ops").status_code == 404
