"""Echter Browser (browse_page) und abgeschottetes Ausfuehren (run_code)."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

import agent_tools as T
import app as A
from conftest import drain, make_agent, make_project, make_task, task

needs_run = pytest.mark.skipif(not T.run_enabled(), reason="bubblewrap fehlt")


def scripted(monkeypatch, replies, seen=None):
    """Mock-Modell mit festen Antworten; merkt sich die Nachrichten jeder Runde."""
    it = iter(replies)

    def fake(agent, messages):
        if seen is not None:
            seen.append([m["content"] for m in messages])
        return json.dumps(next(it)), 10
    monkeypatch.setattr(A, "mock_llm", fake)


# ------------------------------------------------------------------ run_code
@needs_run
def test_run_code_isoliert(tmp_path):
    (tmp_path / "input").mkdir()
    (tmp_path / "input" / "d.csv").write_text("a,b\n1,2\n")
    src = ("import os, socket\n"
           "print(open('/projekt/input/d.csv').read().strip())\n"
           "print('ENV', sorted(os.environ))\n"
           "try:\n socket.create_connection(('1.1.1.1', 53), 3); print('NETZ')\nexcept OSError: print('KEIN-NETZ')\n"
           "try:\n open('/projekt/x', 'w'); print('SCHREIBT')\nexcept OSError: print('NUR-LESEN')\n"
           "print('HOME-SICHTBAR' if os.path.exists('/home') else 'KEIN-HOME')\n"
           "open('ergebnis.txt', 'w').write('42')\n")
    out = T.run_code(tmp_path, code=src, lang="python")
    assert "Exit-Code 0" in out and "a,b" in out
    assert "KEIN-NETZ" in out and "NUR-LESEN" in out and "KEIN-HOME" in out
    assert "API" not in out.split("ENV", 1)[1].splitlines()[0]  # keine Keys aus .env
    files = list((tmp_path / "output" / "run").rglob("ergebnis.txt"))
    assert files and files[0].read_text() == "42"
    assert not (tmp_path / "x").exists()


@needs_run
def test_run_code_zeitlimit(tmp_path, monkeypatch):
    monkeypatch.setattr(T, "RUN_TIMEOUT", 2)
    out = T.run_code(tmp_path, code="while True: pass", lang="python")
    assert "ABGEBROCHEN" in out


@needs_run
def test_run_code_pfade(tmp_path):
    (tmp_path / "s.py").write_text("import sys; print('ARGS', sys.argv[1:])")
    assert "ARGS ['x']" in T.run_code(tmp_path, path="s.py", args=["x"])
    with pytest.raises(T.ToolError):
        T.run_code(tmp_path, path="../etc/passwd")
    with pytest.raises(T.ToolError):
        T.run_code(tmp_path, code="x", lang="cobol")


def test_run_code_nur_mit_recht():
    assert "run_code" not in T.available(dict(A.DEFAULT_PERMS))
    assert A.DEFAULT_PERMS["run_code"] is False
    out, _ = T.run_tool({"tool": "run_code", "code": "print(1)"}, "/tmp", dict(A.DEFAULT_PERMS))
    assert "not allowed" in out


def test_run_code_global_gesperrt(monkeypatch):
    monkeypatch.setenv("PCL_ALLOW_RUN", "0")
    assert "run_code" not in T.available(dict(A.DEFAULT_PERMS, run_code=True))


@needs_run
def test_agent_fuehrt_code_aus(monkeypatch):
    pid = make_project()
    a = make_agent(pid, "Analyst", run_code=True)
    seen = []
    scripted(monkeypatch, [{"tools": [{"tool": "run_code", "code": "print(sum(range(10)))", "lang": "python"}]},
                           {"result": "Summe ist 45"}], seen)
    tid = make_task(pid, a)
    drain()
    assert task(tid)["status"] == "done"
    assert "45" in seen[-1][-1] and "Exit-Code 0" in seen[-1][-1]
    system = A.build_system(A.q1("SELECT * FROM agents WHERE id=?", (a,)), A.q1("SELECT * FROM projects WHERE id=?", (pid,)), "work")
    assert "run_code" in system


# ------------------------------------------------------------------ browse_page
class Site:
    """Testseite, deren Text erst per JavaScript entsteht und die heimlich 'localhost' abfragen will."""

    def __init__(self):
        outer = self
        self.secret_hits = 0

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                port = self.server.server_address[1]
                if self.path == "/":
                    b = (f"<html><head><title>JS-Test</title></head><body><div id=x>roh</div><a href='/b'>Weiter</a><script>"
                         f"document.getElementById('x').textContent='VON-JS-GERENDERT';"
                         f"fetch('http://localhost:{port}/geheim').then(r=>r.text()).then(t=>document.body.append(t))"
                         f".catch(()=>document.body.append('fetch-blockiert'));</script></body></html>").encode()
                else:
                    outer.secret_hits += 1
                    b = b"GEHEIM"
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b)
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}/"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()


@pytest.fixture
def site(monkeypatch):
    if not T.browser_enabled():
        pytest.skip("Playwright fehlt")
    s = Site()

    def only_ip(host):  # 127.0.0.1 gilt im Test als "oeffentlich", localhost nicht
        if host != "127.0.0.1":
            raise T.ToolError("privat")
    monkeypatch.setattr(T, "check_public", only_ip)
    yield s
    s.srv.shutdown()


def test_browser_rendert_js_und_blockt_lan(site, tmp_path):
    try:
        out, imgs = T.browse_page(tmp_path, site.url, screenshot=True, save="start")
    except T.ToolError as e:
        if "Executable" in str(e) or "executable" in str(e):
            pytest.skip("Chromium fehlt")
        raise
    assert "VON-JS-GERENDERT" in out and "Titel: JS-Test" in out
    assert "fetch-blockiert" in out and "GEHEIM" not in out and site.secret_hits == 0
    assert "Blockiert" in out and "localhost" in out
    assert imgs and imgs[0][0] == "image/jpeg"
    assert (tmp_path / "assets" / "screenshots" / "start.jpg").stat().st_size > 1000


def test_browser_lokale_startadresse(tmp_path):
    with pytest.raises(T.ToolError):
        T.browse_page(tmp_path, "http://127.0.0.1:8787/")
    with pytest.raises(T.ToolError):
        T.browse_page(tmp_path, "file:///etc/passwd")


def test_agent_sieht_screenshot(site, monkeypatch):
    pid = make_project()
    a = make_agent(pid, "Rechercheur")
    imgs_per_round = []
    orig = A.call_llm_img

    def spy(agent, messages, images):
        imgs_per_round.append(len(images))
        return orig(agent, messages, images)
    monkeypatch.setattr(A, "call_llm_img", spy)
    seen = []
    scripted(monkeypatch, [{"tools": [{"tool": "browse_page", "url": site.url, "screenshot": True}]},
                           {"result": "Seite gelesen"}], seen)
    tid = make_task(pid, a)
    drain()
    assert task(tid)["status"] == "done"
    assert "VON-JS-GERENDERT" in seen[-1][-1] and "Bild Nr. 1" in seen[-1][-1]
    assert imgs_per_round[-1] == 1
