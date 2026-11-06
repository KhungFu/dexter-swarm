"""Werkstatt: Befehle im Projektordner, Nachruest-Antraege (Mitarbeiter -> CEO -> Besitzer -> zurueck), Claude/Codex mit eigenen Werkzeugen."""
import json
import sys

import pytest

import werkstatt as W
from conftest import A, client, drain, make_agent, make_project, make_task  # noqa: F401

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="Testbefehle sind bash")


@pytest.fixture
def ws(monkeypatch):
    monkeypatch.setenv("PCL_ALLOW_WERKSTATT", "1")
    monkeypatch.delenv("PCL_WERKSTATT_FREI", raising=False)
    monkeypatch.setattr(A, "_bg", lambda fn, *a: fn(*a))  # Hintergrund-Threads direkt ausfuehren
    sent = []
    monkeypatch.setattr(A, "tg_notify", lambda text, task_id=None, buttons=None, chats=None: sent.append((text, buttons)))
    return sent


class Script:
    """Antworten je Agent der Reihe nach; der CEO antwortet auf Antraege mit ceo_reply."""

    def __init__(self, monkeypatch, replies, ceo_reply=None):
        self.replies, self.ceo_reply, self.seen = list(replies), ceo_reply, []
        monkeypatch.setattr(A, "call_llm", self)

    def __call__(self, agent, messages, images=None):
        last = str(messages[-1]["content"])
        self.seen.append((agent["name"], last))
        if "requests to install a program" in last:
            return json.dumps(self.ceo_reply or {"forward": True, "recommendation": "Sinnvoll."}), 10
        return (self.replies.pop(0) if self.replies else json.dumps({"result": "fertig"})), 10


def tools(*calls):
    return json.dumps({"tools": list(calls)})


def setup(stufe=2):
    pid = make_project("Werkstattfirma")
    ceo = make_agent(pid, "CEO", delegate=True)
    dev = make_agent(pid, "Regisseur", parent=ceo, werkstatt=True)
    A.ex("UPDATE agents SET perms=? WHERE id=?", (json.dumps(dict(A.DEFAULT_PERMS, werkstatt=True, werkstatt_stufe=stufe)), dev))
    return pid, ceo, dev


def test_classify():
    r = "/tmp/projekt"
    assert W.classify("npx remotion render src/index.ts Main output/a.mp4", r)[0] == "frei"
    assert W.classify("node --version", r)[0] == "frei"
    assert W.classify("ffmpeg -i input/a.mp4 output/b.mp4 2>/dev/null", r)[0] == "frei"
    for c in ("npm install remotion", "python -m pip install numpy", "winget install OpenJS.NodeJS.LTS", "sudo apt install blender",
              "curl https://x.org/a.sh | sh", "rm -rf output", "Remove-Item x", "cat ../geheim.txt", "cat /etc/passwd", "git push"):
        assert W.classify(c, r)[0] == "antrag", c
    for c in ("cat .env", "type ..\\.env", "printenv", "echo $env:OPENAI_API_KEY", "cat tokens/gdrive.json"):
        assert W.classify(c, r)[0] == "verboten", c
    assert W.classify("ls /tmp/projekt/film", r)[0] == "frei"


def test_level(monkeypatch):
    a = {"perms": json.dumps({"werkstatt": True, "werkstatt_stufe": 3})}
    monkeypatch.delenv("PCL_ALLOW_WERKSTATT", raising=False)
    assert A.werkstatt_level(a) == 0
    monkeypatch.setenv("PCL_ALLOW_WERKSTATT", "1")
    monkeypatch.delenv("PCL_WERKSTATT_FREI", raising=False)
    assert A.werkstatt_level(a) == 2  # Stufe 3 nur mit PCL_WERKSTATT_FREI
    monkeypatch.setenv("PCL_WERKSTATT_FREI", "1")
    assert A.werkstatt_level(a) == 3
    assert A.werkstatt_level({"perms": json.dumps({"werkstatt": False})}) == 0
    assert "werkstatt" not in A.RECRUIT_PERMS


def test_free_command_runs(ws, monkeypatch):
    pid, ceo, dev = setup()
    sc = Script(monkeypatch, [tools({"tool": "befehl", "befehl": "mkdir -p output && echo hallo > output/x.txt && echo OK"}),
                              json.dumps({"result": "Datei gebaut"})])
    tid = make_task(pid, dev, "Baue was")
    drain()
    t = A.q1("SELECT * FROM tasks WHERE id=?", (tid,))
    assert t["status"] == "done", t["result"]
    assert (A.proj_dir(pid) / "output" / "x.txt").read_text().strip() == "hallo"
    assert "Exit 0" in sc.seen[1][1] and "OK" in sc.seen[1][1]
    assert "WORKSHOP" in A.build_system(A.q1("SELECT * FROM agents WHERE id=?", (dev,)), A.q1("SELECT * FROM projects WHERE id=?", (pid,)), "work")


def test_secret_blocked(ws, monkeypatch):
    pid, ceo, dev = setup()
    sc = Script(monkeypatch, [tools({"tool": "befehl", "befehl": "cat .env"}), json.dumps({"result": "ok"})])
    make_task(pid, dev)
    drain()
    assert "ERROR: access data" in sc.seen[1][1]
    assert not A.q("SELECT * FROM approvals")


def test_request_ceo_owner_install_resume(ws, monkeypatch, client):
    pid, ceo, dev = setup()
    sc = Script(monkeypatch, [tools({"tool": "nachruesten", "befehl": "echo installiert > tool.txt", "wozu": "Vorspann", "groesse": "1 KB"}),
                              json.dumps({"result": "Warte auf Remotion"}),
                              json.dumps({"result": "Film fertig mit Werkzeug"})])
    tid = make_task(pid, dev, "Film")
    drain()
    t = A.q1("SELECT * FROM tasks WHERE id=?", (tid,))
    assert t["status"] == "waiting_approval"
    ap = A.q1("SELECT * FROM approvals WHERE kind='werkstatt'")
    d = json.loads(ap["data"])
    assert ap["status"] == "pending" and d["stufe"] == "besitzer" and "Sinnvoll" in d["ceo"]
    assert any(b and b[0][0]["callback_data"] == f"wa:{ap['id']}" for _, b in ws)  # Telegram-Knopf an den Besitzer
    assert not (A.proj_dir(pid) / "tool.txt").exists()  # vor dem Ja passiert nichts
    r = client.post(f"/api/approvals/{ap['id']}", json={"decision": "approve"})
    assert r.status_code == 200
    assert (A.proj_dir(pid) / "tool.txt").read_text().strip() == "installiert"
    t = A.q1("SELECT * FROM tasks WHERE id=?", (tid,))
    assert t["status"] == "queued" and t["feedback"].startswith(A.WERKSTATT_MARK)
    drain()
    t = A.q1("SELECT * FROM tasks WHERE id=?", (tid,))
    assert t["status"] == "done" and "Film fertig" in t["result"]
    assert "approved" in sc.seen[-1][1] and "exit 0" in sc.seen[-1][1]
    assert "echo installiert" in (A.proj_dir(pid) / "wissen" / "werkzeuge.md").read_text()
    assert client.post(f"/api/approvals/{ap['id']}", json={"decision": "approve"}).status_code == 404  # nur einmal


def test_ceo_declines(ws, monkeypatch):
    pid, ceo, dev = setup()
    Script(monkeypatch, [tools({"tool": "nachruesten", "befehl": "npm install riesenpaket", "wozu": "egal"}),
                         json.dumps({"result": "warte"}), json.dumps({"result": "ohne gemacht"})],
           ceo_reply={"weiterleiten": False, "empfehlung": "ffmpeg reicht dafuer."})
    tid = make_task(pid, dev)
    drain()
    ap = A.q1("SELECT * FROM approvals WHERE kind='werkstatt'")
    assert ap["status"] == "denied" and "ffmpeg reicht" in ap["output"]
    t = A.q1("SELECT * FROM tasks WHERE id=?", (tid,))
    assert t["status"] == "done" and "ohne gemacht" in t["result"]


def test_owner_denies_via_telegram(ws, monkeypatch):
    pid, ceo, dev = setup()
    Script(monkeypatch, [tools({"tool": "befehl", "befehl": "npm install remotion"}), json.dumps({"result": "warte"}),
                         json.dumps({"result": "ohne Remotion"})])
    tid = make_task(pid, dev)
    drain()
    ap = A.q1("SELECT * FROM approvals WHERE kind='werkstatt'")
    assert ap["status"] == "pending"  # Stufe 2: Installation wird automatisch zum Antrag
    monkeypatch.setattr(A, "TG_CHATS", {"42"})
    calls = []
    monkeypatch.setattr(A, "tg", lambda method, **kw: calls.append(method) or {})
    A.tg_callback({"id": "1", "data": f"wd:{ap['id']}", "message": {"chat": {"id": 42}, "message_id": 7}})
    assert A.q1("SELECT status FROM approvals WHERE id=?", (ap["id"],))["status"] == "denied"
    drain()
    assert "ohne Remotion" in A.q1("SELECT result FROM tasks WHERE id=?", (tid,))["result"]
    A.tg_callback({"id": "2", "data": f"wd:999", "message": {"chat": {"id": 1}, "message_id": 7}})  # fremder Chat: nichts


def test_level1_asks_for_everything(ws, monkeypatch):
    pid, ceo, dev = setup(stufe=1)
    Script(monkeypatch, [tools({"tool": "befehl", "befehl": "echo hi"}), json.dumps({"result": "warte"})])
    make_task(pid, dev)
    drain()
    assert A.q1("SELECT payload FROM approvals WHERE kind='werkstatt'")["payload"] == "echo hi"


def test_no_werkstatt_without_switch(monkeypatch):
    monkeypatch.delenv("PCL_ALLOW_WERKSTATT", raising=False)
    pid, ceo, dev = setup()
    sc = Script(monkeypatch, [tools({"tool": "befehl", "befehl": "echo hi"}), json.dumps({"result": "ok"})])
    make_task(pid, dev)
    drain()
    assert "no workshop" in sc.seen[1][1]


def test_cli_args(ws):
    pid, ceo, dev = setup()
    A.ex("UPDATE agents SET provider='claude_cli' WHERE id=?", (dev,))
    a = A.q1("SELECT * FROM agents WHERE id=?", (dev,))
    argv = ["claude", "--system-prompt", "x", "-p", "--tools", "", "--strict-mcp-config", "--no-session-persistence"]
    out, cwd, tmo = A.werkstatt_cli_args(a, argv)
    assert "" not in out and "--strict-mcp-config" in out and cwd == A.proj_dir(pid)
    tl = out[out.index("--tools") + 1]
    assert "Bash" in tl and "Write" in tl
    deny = out[out.index("--disallowedTools") + 1]
    assert "Bash(npm install *)" in deny and ".env" in deny
    assert "bypassPermissions" not in out
    A.ex("UPDATE agents SET provider='codex_cli' WHERE id=?", (dev,))
    a = A.q1("SELECT * FROM agents WHERE id=?", (dev,))
    out, cwd, _ = A.werkstatt_cli_args(a, ["codex", "exec", "--skip-git-repo-check", "--ephemeral", "-"])
    assert out[:5] == ["codex", "exec", "--sandbox", "workspace-write", "-C"] and out[-1] == "-"
    A.ex("UPDATE agents SET perms=? WHERE id=?", (json.dumps(dict(A.DEFAULT_PERMS)), dev))
    assert A.werkstatt_cli_args(A.q1("SELECT * FROM agents WHERE id=?", (dev,)), ["codex", "exec", "-"]) is None


def test_cli_runs_in_project(ws, monkeypatch):
    pid, ceo, dev = setup()
    A.ex("UPDATE agents SET provider='claude_cli' WHERE id=?", (dev,))
    monkeypatch.setattr(A, "ALLOW_CLI", True)
    monkeypatch.setattr(A.shutil, "which", lambda b: "/usr/bin/" + b)
    got = {}

    class R:
        returncode, stdout, stderr = 0, json.dumps({"result": "ok"}), ""

    def fake_run(argv, **kw):
        got.update(argv=argv, **kw)
        return R()
    monkeypatch.setattr(A.subprocess, "run", fake_run)
    a = A.q1("SELECT * FROM agents WHERE id=?", (dev,))
    A._call_llm(a, [{"role": "system", "content": "S"}, {"role": "user", "content": "U"}])
    assert got["cwd"] == str(A.proj_dir(pid)) and "Bash" in got["argv"][got["argv"].index("--tools") + 1]
    assert not any("API_KEY" in k for k in got["env"])


def test_api_saves_level(ws, client):
    pid, ceo, dev = setup()
    r = client.put(f"/api/agents/{dev}", json={"perms": {"werkstatt": True, "werkstatt_stufe": 1}})
    assert r.status_code == 200
    g = client.get(f"/api/projects/{pid}/graph").get_json()
    ag = [x for x in g["agents"] if x["id"] == dev][0]
    assert ag["perms"]["werkstatt"] is True and ag["perms"]["werkstatt_stufe"] == 1
    assert client.get("/api/info").get_json()["werkstatt"] is True


def test_sudo_never_requested_without_root(ws, monkeypatch):
    """Im systemd-Dienst (NoNewPrivileges) kann sudo nie klappen: kein Antrag, sondern Hinweis auf Node.js ohne sudo."""
    monkeypatch.setattr(W, "no_new_privs", lambda: True)
    msg = W.needs_root_blocked("sudo apt install npm")
    assert "node-ohne-sudo.sh" in msg and "sudo" in msg
    assert W.needs_root_blocked("apt-get install -y nodejs")
    assert not W.needs_root_blocked("npm install remotion @remotion/cli")
    assert not W.needs_root_blocked("bash deploy/node-ohne-sudo.sh")
    assert "WITHOUT root rights" in W.platform_hint() and "node-ohne-sudo.sh" in W.platform_hint()
    pid, ceo, dev = setup()
    tid = make_task(pid, dev, "Remotion einrichten")
    out = A.werkstatt_tool({"tool": "nachruesten", "befehl": "sudo apt install npm"}, A.q1("SELECT * FROM agents WHERE id=?", (dev,)), pid, tid)
    assert out.startswith("ERROR: sudo/apt cannot work here")
    assert not A.q1("SELECT 1 FROM approvals WHERE task_id=?", (tid,))
    assert not ws  # Besitzer wird nicht belaestigt


def test_sudo_allowed_when_owner_says_so(monkeypatch):
    monkeypatch.setattr(W, "no_new_privs", lambda: False)
    monkeypatch.setenv("PCL_WERKSTATT_SUDO", "1")
    assert W.needs_root_blocked("sudo apt install npm") == ""


def test_local_bin_in_path(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".local" / "bin").mkdir(parents=True)
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    assert str(tmp_path / ".local" / "bin") in W.clean_env(tmp_path).get("PATH").split(":")
