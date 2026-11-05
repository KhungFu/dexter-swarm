"""Drucken der Abendberichte: Testdrucker (Datei), gespielte CUPS-/Windows-Befehle, Recht des CEO, Bestaetigung."""
import subprocess

import pytest

import printing as P
from conftest import A, make_agent, make_project, make_task


def report_task(pid, aid, result="Alles fertig. Morgen: Angebote."):
    tid = make_task(pid, aid, "Kontrollgang", status="done")
    A.ex("UPDATE tasks SET description=?, result=?, inbox='new' WHERE id=?",
         (A.REPORT_HEAD + ", 04.11.2026 18:00, Projekt X)\n...", result, tid))
    return tid


@pytest.fixture(autouse=True)
def no_wait(monkeypatch):
    monkeypatch.setattr(P, "WAIT_AFTER", 0)  # Nachpruefung nur in den Tests, die sie wollen


@pytest.fixture
def firm():
    pid = make_project("Druckerei")
    ceo = make_agent(pid, "CEO", delegate=True)
    make_agent(pid, "Mitarbeiter", parent=ceo)
    make_agent(pid, "Einzelgaenger")  # zweiter oberster Agent ohne Team ist nicht der CEO
    return pid, ceo


class Fake:
    def __init__(self, monkeypatch, windows=False, out="", rc=0):
        self.calls = []
        monkeypatch.setattr(P, "is_windows", lambda: windows)
        monkeypatch.setattr(P.shutil, "which", lambda n: "/usr/bin/" + n)
        self.out, self.rc = out, rc

        def run(cmd, **kw):
            self.calls.append((cmd, kw))
            if cmd[0] == "lp":
                self.printed = open(cmd[-1], encoding="utf-8").read()
            if cmd[0] == "powershell" and "Out-Printer" in cmd[-1]:
                self.printed = open(kw["env"]["PCL_PRN_FILE"], encoding="utf-8").read()
            return subprocess.CompletedProcess(cmd, self.rc, self.out, "kaputt" if self.rc else "")
        monkeypatch.setattr(P.subprocess, "run", run)


def test_ceo_ist_chef_mit_team(firm):
    pid, ceo = firm
    assert A.ceo_of(pid)["id"] == ceo
    assert not A.print_allowed(pid)


def test_liste_cups(monkeypatch):
    f = Fake(monkeypatch, out="Buero_HP\nKeller\n")
    names, err = P.list_printers()
    assert names == ["Buero_HP", "Keller", P.TEST_PRINTER] and err == ""
    assert f.calls[0][0] == ["lpstat", "-e"]


def test_liste_ohne_cups(monkeypatch):
    monkeypatch.setattr(P, "is_windows", lambda: False)
    monkeypatch.setattr(P.shutil, "which", lambda n: None)
    names, err = P.list_printers()
    assert names == [P.TEST_PRINTER] and "CUPS missing" in err


def test_druck_nur_mit_bestaetigung_und_recht(client, firm, monkeypatch):
    pid, ceo = firm
    tid = report_task(pid, ceo)
    A.set_setting("printer", "Buero_HP")
    f = Fake(monkeypatch, out="request id is Buero_HP-7 (1 file(s))")
    r = client.post(f"/api/tasks/{tid}/print", json={})
    assert r.status_code == 400 and "confirmation" in r.get_data(as_text=True)
    r = client.post(f"/api/tasks/{tid}/print", json={"confirm": True})
    assert r.status_code == 400 and "blocked" in r.get_data(as_text=True)
    assert not f.calls
    # CEO erlaubt das Drucken
    assert client.put(f"/api/projects/{pid}/print", json={"allowed": True}).get_json()["allowed"]
    r = client.post(f"/api/tasks/{tid}/print", json={"confirm": True})
    assert r.status_code == 200, r.get_data(as_text=True)
    cmd = f.calls[-1][0]
    assert cmd[:3] == ["lp", "-d", "Buero_HP"] and "--" in cmd
    assert "EVENING REPORT" in f.printed and "Druckerei" in f.printed and "Morgen: Angebote" in f.printed
    assert A.q1("SELECT 1 x FROM audit WHERE event='print'")
    # wieder sperren
    client.put(f"/api/projects/{pid}/print", json={"allowed": False})
    assert client.post(f"/api/tasks/{tid}/print", json={"confirm": True}).status_code == 400


def test_nur_abendberichte(client, firm, monkeypatch):
    pid, ceo = firm
    client.put(f"/api/projects/{pid}/print", json={"allowed": True})
    A.set_setting("printer", P.TEST_PRINTER)
    tid = make_task(pid, ceo, "Normaler Auftrag", status="done")
    A.ex("UPDATE tasks SET result='x' WHERE id=?", (tid,))
    r = client.post(f"/api/tasks/{tid}/print", json={"confirm": True})
    assert r.status_code == 400 and "Only evening reports" in r.get_data(as_text=True)


def test_ohne_drucker(client, firm):
    pid, ceo = firm
    client.put(f"/api/projects/{pid}/print", json={"allowed": True})
    tid = report_task(pid, ceo)
    r = client.post(f"/api/tasks/{tid}/print", json={"confirm": True})
    assert r.status_code == 400 and "No printer" in r.get_data(as_text=True)


def test_testdrucker_schreibt_datei(client, firm):
    pid, ceo = firm
    client.put(f"/api/projects/{pid}/print", json={"allowed": True})
    assert client.put("/api/printers", json={"printer": P.TEST_PRINTER}).status_code == 200
    tid = report_task(pid, ceo)
    r = client.post(f"/api/tasks/{tid}/print", json={"confirm": True})
    assert r.status_code == 200 and "Test printer" in r.get_json()["message"]
    files = list((A.WORKSPACE / ".druck").glob("print-*.txt"))
    assert files and any("Morgen: Angebote" in f.read_text(encoding="utf-8") for f in files)


def test_windows_name_per_umgebung(monkeypatch, tmp_path):
    f = Fake(monkeypatch, windows=True)
    bad = 'HP"; Remove-Item C:\\ -Recurse; "'
    ok, msg = P.print_text(bad, "t", "Hallo Welt", tmp_path)
    assert ok, msg
    cmd, kw = f.calls[-1]
    assert bad not in " ".join(cmd) and kw["env"]["PCL_PRN"] == bad
    assert f.printed == "Hallo Welt"


def test_druckerfehler_wird_gemeldet(monkeypatch, tmp_path):
    Fake(monkeypatch, rc=1)
    ok, msg = P.print_text("Buero", "t", "x", tmp_path)
    assert not ok and "kaputt" in msg


def test_ungueltiger_name(client):
    assert client.put("/api/printers", json={"printer": "a\nb"}).status_code == 400


def test_post_und_aufgaben_markieren_abendberichte(client, firm):
    pid, ceo = firm
    tid = report_task(pid, ceo)
    other = make_task(pid, ceo, "Anderes", status="done")
    A.ex("UPDATE tasks SET inbox='new', result='y' WHERE id=?", (other,))
    inbox = {r["id"]: r for r in client.get("/api/inbox").get_json()}
    assert inbox[tid]["report"] and not inbox[other]["report"] and "description" not in inbox[tid]
    tasks = {r["id"]: r for r in client.get(f"/api/agents/{ceo}/tasks").get_json()}
    assert tasks[tid]["report"] and not tasks[other]["report"]


def test_druckerliste_api(client, firm, monkeypatch):
    pid, ceo = firm
    Fake(monkeypatch, out="Buero_HP\n")
    r = client.get(f"/api/printers?pid={pid}").get_json()
    assert r["printers"][0] == "Buero_HP" and r["ceo"]["id"] == ceo and r["allowed"] is False


def test_recht_im_agentendialog(client, firm):
    pid, ceo = firm
    client.put(f"/api/agents/{ceo}", json={"perms": {"print": True}})
    assert A.print_allowed(pid)


def test_testseite_auf_cups_drucker(client, monkeypatch):
    f = Fake(monkeypatch, out="Buero_Laser\n")
    r = client.post("/api/printers/test", json={"printer": "Buero_Laser"})
    assert r.status_code == 200
    lp = [c for c, _ in f.calls if c[0] == "lp"][0]
    assert lp[:3] == ["lp", "-d", "Buero_Laser"] and "TEST PAGE" in f.printed and "Buero_Laser" in f.printed
    assert not A.get_setting("printer", "")  # Testseite speichert den Drucker nicht


def test_testseite_nur_drucker_aus_der_liste(client, monkeypatch):
    f = Fake(monkeypatch, out="Buero_Laser\n")
    assert client.post("/api/printers/test", json={"printer": "Fremd"}).status_code == 400
    assert not [c for c, _ in f.calls if c[0] == "lp"]


def test_testseite_testdrucker(client):
    r = client.post("/api/printers/test", json={"printer": P.TEST_PRINTER})
    assert r.status_code == 200 and "Test printer" in r.get_json()["message"]


class Cups:
    """Gespieltes CUPS je Befehl: lp nimmt an, lpstat/lpoptions liefern den eingestellten Zustand."""

    def __init__(self, monkeypatch, state="printer Buero is idle.  enabled since Thu", model="IPP Everywhere", jobs=""):
        monkeypatch.setattr(P, "is_windows", lambda: False)
        monkeypatch.setattr(P.shutil, "which", lambda n: "/usr/bin/" + n)
        monkeypatch.setattr(P.time, "sleep", lambda s: None)
        self.state, self.model, self.jobs = state, model, jobs

        def run(cmd, **kw):
            c = " ".join(cmd)
            if cmd[0] == "lp":
                out = "request id is Buero-12 (1 file(s))"
            elif c.startswith("lpstat -l -p"):
                out = self.state
            elif c.startswith("lpstat -v"):
                out = "device for Buero: ipp://192.168.1.50/ipp/print"
            elif cmd[0] == "lpoptions":
                out = f"copies=1 printer-make-and-model='{self.model}' printer-state=3"
            elif c.startswith("lpstat -o"):
                out = self.jobs
            else:
                out = ""
            return subprocess.CompletedProcess(cmd, 0, out, "")
        monkeypatch.setattr(P.subprocess, "run", run)


def test_gestoppter_drucker_wird_gemeldet(monkeypatch, tmp_path):
    monkeypatch.setattr(P, "WAIT_AFTER", 1)
    Cups(monkeypatch, state="printer Buero disabled since Thu -\n\tUnable to connect to printer; will retry in 30 seconds.")
    ok, msg = P.print_text("Buero", "t", "x", tmp_path)
    assert not ok and "STOPPED" in msg and "cupsenable" in msg


def test_raw_ohne_treiber_wird_gemeldet(monkeypatch):
    Cups(monkeypatch, model="Local Raw Printer")
    st = P.status("Buero")
    assert any("WITHOUT a driver" in p for p in st["problems"])
    assert any("ipp://192.168.1.50" in x for x in st["lines"])


def test_wartender_auftrag_ist_hinweis(monkeypatch, tmp_path):
    monkeypatch.setattr(P, "WAIT_AFTER", 1)
    Cups(monkeypatch, jobs="Buero-12   abi   1024   Thu")
    ok, msg = P.print_text("Buero", "t", "x", tmp_path)
    assert ok and "still waiting" in msg


def test_alles_gut(monkeypatch, tmp_path):
    monkeypatch.setattr(P, "WAIT_AFTER", 1)
    Cups(monkeypatch)
    ok, msg = P.print_text("Buero", "t", "x", tmp_path)
    assert ok and "Note" not in msg


def test_windows_offline(monkeypatch):
    monkeypatch.setattr(P, "is_windows", lambda: True)
    monkeypatch.setattr(P.shutil, "which", lambda n: "C:/ps.exe")
    out = "STATUS=Offline\nTYPE=Connection\nCOMPUTER=SERVER\nJOB=3|Error, Printing|Testseite|05.11.2026\n"
    monkeypatch.setattr(P.subprocess, "run", lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, out, ""))
    st = P.status("\\\\SERVER\\HP")
    assert any("Offline" in p for p in st["problems"]) and any("stuck" in p for p in st["problems"])
    assert st["jobs"] and any("SERVER" in x for x in st["lines"])


def test_status_api(client, monkeypatch):
    Cups(monkeypatch, model="Local Raw Printer")
    A.set_setting("printer", "Buero")
    r = client.get("/api/printers/status").get_json()
    assert r["printer"] == "Buero" and r["problems"]
    assert client.get("/api/printers/status?printer=" + P.TEST_PRINTER).get_json()["problems"]
