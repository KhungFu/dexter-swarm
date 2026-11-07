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
        monkeypatch.setattr(P, "win_enum_printers", lambda: ([], "", ""))
        monkeypatch.setattr(P.shutil, "which", lambda n: "/usr/bin/" + n)
        self.out, self.rc = out, rc

        def run(cmd, **kw):
            self.calls.append((cmd, kw))
            if cmd[0] == "lp":
                self.printed = open(cmd[-1], encoding="utf-8").read()
            if "powershell" in cmd[0] and "Out-Printer" in cmd[-1]:
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
    assert [c for c, _ in f.calls] == [["lpstat", "-a"], ["lpstat", "-e"]]
    assert all(kw["env"]["LC_ALL"] == "C" for _, kw in f.calls)  # CUPS-Ausgabe immer englisch (Pi auf Deutsch)


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


# ---------------------------------------------------------------- Pi: nur gefunden, nicht eingerichtet
class Found:
    """CUPS kennt 'Buero' als Warteschlange, 'HP_Laser_MFP' hat es nur im Netzwerk gesehen (lpstat -e)."""

    def __init__(self, monkeypatch, lp_rc=1, admin_rc=0):
        monkeypatch.setattr(P, "is_windows", lambda: False)
        monkeypatch.setattr(P.shutil, "which", lambda n: "/usr/bin/" + n)
        self.calls = []

        def run(cmd, **kw):
            self.calls.append(cmd)
            c, rc, out, err = " ".join(cmd), 0, "", ""
            if c == "lpstat -a":
                out = "Buero accepting requests since Thu"
            elif c == "lpstat -e":
                out = "Buero\nHP_Laser_MFP\n"
            elif c.startswith("lpstat -l -p HP_Laser_MFP"):
                rc, err = 1, 'lpstat: Invalid destination name in list "HP_Laser_MFP".'
            elif c.startswith("lpoptions -p HP_Laser_MFP"):
                out = "device-uri=dnssd://HP%20Laser%20MFP._ipp._tcp.local/?uuid=1 printer-info='HP Laser MFP'"
            elif cmd[0] == "lp":
                rc, err = lp_rc, "lp: The printer or class does not exist." if lp_rc else ""
            elif cmd[0] == "lpadmin":
                rc, err = admin_rc, "lpadmin: Forbidden" if admin_rc else ""
            return subprocess.CompletedProcess(cmd, rc, out, err)
        monkeypatch.setattr(P.subprocess, "run", run)


def test_nur_gefunden_wird_markiert(monkeypatch):
    Found(monkeypatch)
    items, err = P.list_details()
    assert {"name": "Buero", "kind": "queue"} in items and {"name": "HP_Laser_MFP", "kind": "network"} in items
    assert P.network_only("HP_Laser_MFP") and not P.network_only("Buero")


def test_nur_gefunden_druck_erklaert_ursache(monkeypatch, tmp_path):
    Found(monkeypatch)
    ok, msg = P.print_text("HP_Laser_MFP", "t", "x", tmp_path)
    assert not ok and "only found on the network" in msg and "Set up printer" in msg
    st = P.status("HP_Laser_MFP")
    assert st["setup"] and any("only SEEN" in p for p in st["problems"])
    assert any("dnssd://HP%20Laser%20MFP" in x for x in st["lines"])


def test_einrichten(client, monkeypatch):
    f = Found(monkeypatch)
    r = client.post("/api/printers/setup", json={"printer": "HP_Laser_MFP"})
    assert r.status_code == 200, r.get_data(as_text=True)
    adm = [c for c in f.calls if c[0] == "lpadmin"][0]
    assert adm[:3] == ["lpadmin", "-p", "HP_Laser_MFP"] and "everywhere" in adm and "printer-is-shared=true" in adm
    assert "dnssd://HP%20Laser%20MFP._ipp._tcp.local/?uuid=1" in adm
    # eingerichtete Warteschlange wird nicht noch einmal angelegt
    assert client.post("/api/printers/setup", json={"printer": "Buero"}).status_code == 400


def test_einrichten_ohne_recht_nennt_befehl(monkeypatch):
    Found(monkeypatch, admin_rc=1)
    ok, msg = P.setup_printer("HP_Laser_MFP")
    assert not ok and "sudo lpadmin" in msg and "Forbidden" in msg


# ---------------------------------------------------------------- Windows
def test_windows_powershell_fehlt_im_path(monkeypatch, tmp_path):
    monkeypatch.setattr(P.shutil, "which", lambda n: None)
    ps = tmp_path / "System32" / "WindowsPowerShell" / "v1.0"
    ps.mkdir(parents=True)
    (ps / "powershell.exe").write_text("")
    monkeypatch.setenv("SystemRoot", str(tmp_path))
    assert P.powershell() == str(ps / "powershell.exe")


def win(monkeypatch, out="", rc=0, err="", enum=([], "", "")):
    monkeypatch.setattr(P, "is_windows", lambda: True)
    monkeypatch.setattr(P, "win_enum_printers", lambda: enum)
    monkeypatch.setattr(P.shutil, "which", lambda n: "C:/ps.exe")
    calls = []

    def run(cmd, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, rc, out, err)
    monkeypatch.setattr(P.subprocess, "run", run)
    return calls


def test_windows_liste_utf8_und_rueckfall(monkeypatch):
    calls = win(monkeypatch, out="Büro Drucker\nMicrosoft Print to PDF\n")
    names, err = P.list_printers()
    assert names[:2] == ["Büro Drucker", "Microsoft Print to PDF"] and err == ""
    assert "UTF8" in calls[0][-1] and "Win32_Printer" in calls[0][-1]


def test_windows_nur_virtuelle_drucker(monkeypatch):
    win(monkeypatch, out="Microsoft Print to PDF\nOneNote (Desktop)\nFax\n")
    _, err = P.list_printers()
    assert "only has virtual printers" in err and "Pi's address" in err


def test_windows_fehler_wird_gezeigt(monkeypatch):
    win(monkeypatch, rc=2, err="Get-Printer: The spooler service is not reachable.")
    names, err = P.list_printers()
    assert names == [P.TEST_PRINTER] and "spooler service" in err and "Print Spooler" in err


# ---------------------------------------------------------------- Laptop druckt ueber das CUPS des Pi (IPP)
import struct
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


def _a(tag, name, v):
    v = struct.pack(">i", v) if isinstance(v, int) else v.encode()
    return struct.pack(">BH", tag, len(name)) + name.encode() + struct.pack(">H", len(v)) + v


@pytest.fixture
def pi():
    """Kleiner IPP-Server wie CUPS auf dem Pi: zwei Drucker, nimmt Auftraege an."""
    got = {"jobs": [], "stopped": False}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            op = struct.unpack(">H", body[2:4])[0]
            st, groups = P._parse(body)
            ops = groups[0][1]
            head = struct.pack(">BBHi", 2, 0, 0, 1) + b"\x01" + _a(0x47, "attributes-charset", "utf-8")
            if op == 0x4002:
                out = head
                for n in ("Buero", "Keller Laser"):
                    out += b"\x04" + _a(0x42, "printer-name", n)
            elif op == 0x0002:
                got["jobs"].append((self.path, ops, body))
                out = head + b"\x02" + _a(0x21, "job-id", 77)
            else:
                out = head + b"\x04" + _a(0x23, "printer-state", 5 if got["stopped"] else 3) + \
                    _a(0x41, "printer-make-and-model", "HP Laser MFP, driverless") + _a(0x21, "queued-job-count", 0)
            out += b"\x03"
            self.send_response(200)
            self.send_header("Content-Type", "application/ipp")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    got["server"] = f"127.0.0.1:{srv.server_port}"
    yield got
    srv.shutdown()


def test_pi_drucker_vom_laptop(client, monkeypatch, pi):
    win(monkeypatch, out="Microsoft Print to PDF\n")
    monkeypatch.setattr(P, "WAIT_AFTER", 1)
    monkeypatch.setattr(P.time, "sleep", lambda s: None)
    assert client.put("/api/printers", json={"cups_server": "http://" + pi["server"] + "/"}).status_code == 200
    r = client.get("/api/printers").get_json()
    name = "Keller Laser @ " + pi["server"]
    assert name in r["printers"] and r["cups_server"] == pi["server"]
    assert {"name": name, "kind": "remote"} in r["details"] and "virtual" in r["error"] and "Pi's address" not in r["error"]
    t = client.post("/api/printers/test", json={"printer": name})
    assert t.status_code == 200, t.get_data(as_text=True)
    assert "Job 77" in t.get_json()["message"]
    path, ops, body = pi["jobs"][-1]
    assert path == "/printers/Keller%20Laser" and ops["document-format"] == ["text/plain"]
    assert ops["printer-uri"] == ["ipp://" + pi["server"] + "/printers/Keller%20Laser"]
    assert "TEST PAGE" in body.decode("utf-8") and "ä ö ü" in body.decode("utf-8")
    st = client.get("/api/printers/status?printer=" + name).get_json()
    assert not st["problems"] and any("driverless" in x for x in st["lines"])
    pi["stopped"] = True
    st = P.status(name, pi["server"])
    assert any("STOPPED" in p for p in st["problems"])


def test_pi_nicht_erreichbar(monkeypatch):
    monkeypatch.setattr(P, "IPP_TIMEOUT", 1)
    names, err = P.remote_printers("127.0.0.1:9")
    assert names == [] and "Cannot reach CUPS" in err and "cupsctl" in err


def test_pi_adresse_pruefen(client):
    assert client.put("/api/printers", json={"cups_server": "dexter; rm -rf /"}).status_code == 400
    assert client.put("/api/printers", json={"cups_server": "dexter.local"}).get_json()["cups_server"] == "dexter.local"
    assert P.remote_split("Buero @ dexter.local", "dexter.local") == ("Buero", "dexter.local")
    assert P.remote_split("Buero @ anders", "dexter.local") == ("Buero @ anders", "")


def test_windows_eigene_drucker_ohne_powershell(monkeypatch):
    """Liste kommt direkt aus winspool (EnumPrinters), der Standarddrucker steht vorn, PowerShell wird nicht gebraucht."""
    calls = win(monkeypatch, enum=(["Microsoft Print to PDF", "HP LaserJet Büro", "\\\\SERVER\\Keller"], "HP LaserJet Büro", ""))
    items, err = P.list_details()
    assert [i["name"] for i in items] == ["HP LaserJet Büro", "Microsoft Print to PDF", "\\\\SERVER\\Keller", P.TEST_PRINTER]
    assert items[0]["default"] and err == "" and calls == []


def test_windows_druck_ohne_powershell_mit_notepad(monkeypatch, tmp_path):
    calls = win(monkeypatch)
    monkeypatch.setattr(P, "powershell", lambda: "")
    ok, msg = P.print_text("HP LaserJet", "t", "Hallo", tmp_path)
    assert ok, msg
    assert calls[0][0].lower().endswith("notepad.exe") and calls[0][1] == "/pt" and calls[0][-1] == "HP LaserJet"


def test_windows_api_waehlt_standarddrucker(client, monkeypatch):
    win(monkeypatch, enum=(["Microsoft Print to PDF", "Canon"], "Canon", ""))
    r = client.get("/api/printers").get_json()
    assert r["printers"][0] == "Canon" and r["details"][0]["default"] and r["error"] == ""
