"""Ollama auf dem Pi: lange, langsame Antworten duerfen nicht abbrechen (Streaming, OLLAMA_TIMEOUT = Wartezeit ohne neue Daten)."""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

import app as A
from conftest import make_agent, make_project

CALLS = []


class FakeOllama(BaseHTTPRequestHandler):
    mode = "slow"      # slow | silent | memory | missing
    pause = 0.3        # Sekunden zwischen zwei Woertern
    first = 0.0        # Wartezeit vor dem ersten Wort (Modell laden, Prompt lesen)

    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        CALLS.append(body)
        m = FakeOllama.mode
        if m in ("memory", "missing"):
            msg = ("model requires more system memory (2.3 GiB) than is available (1.6 GiB)" if m == "memory"
                   else f'model "{body["model"]}" not found, try pulling it first')
            out = json.dumps({"error": {"message": msg}}).encode()
            self.send_response(500 if m == "memory" else 404)
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()

        def chunk(s):
            b = s.encode()
            self.wfile.write(f"{len(b):x}\r\n".encode() + b + b"\r\n")
            self.wfile.flush()

        if m == "silent":
            time.sleep(3)
        time.sleep(FakeOllama.first)
        for w in ["Hallo ", "aus ", "dem ", "Pi ", "ü"]:
            chunk("data: " + json.dumps({"choices": [{"delta": {"content": w}, "finish_reason": None}]}) + "\n\n")
            time.sleep(FakeOllama.pause)
        chunk("data: " + json.dumps({"choices": [{"delta": {}, "finish_reason": "stop"}]}) + "\n\n")
        chunk("data: " + json.dumps({"choices": [], "usage": {"total_tokens": 42}}) + "\n\n")
        chunk("data: [DONE]\n\n")
        self.wfile.write(b"0\r\n\r\n")


@pytest.fixture
def ollama(monkeypatch):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setitem(A.PROVIDERS["ollama"], "url", f"http://127.0.0.1:{srv.server_address[1]}/v1/chat/completions")
    FakeOllama.mode, FakeOllama.pause, FakeOllama.first = "slow", 0.3, 0.0
    CALLS.clear()
    yield srv
    srv.shutdown()


def agent(name="Pi"):
    return {"id": 0, "name": name, "provider": "ollama", "model": "qwen2.5:1.5b"}


def test_langsame_antwort_laeuft_laenger_als_zeitlimit(ollama, monkeypatch):
    # 5 Woerter x 0,3 s = 1,5 s Gesamtzeit, Zeitlimit ohne neue Daten nur 1 s: darf NICHT abbrechen
    monkeypatch.setenv("OLLAMA_TIMEOUT", "1")
    text, tok = A.call_llm(agent(), [{"role": "user", "content": "hi"}])
    assert text == "Hallo aus dem Pi ü" and tok == 42
    assert CALLS[0]["stream"] is True and CALLS[0]["model"] == "qwen2.5:1.5b"


def test_stille_bricht_ab_ohne_wiederholung(ollama, monkeypatch):
    FakeOllama.mode = "silent"
    monkeypatch.setenv("OLLAMA_TIMEOUT", "1")
    monkeypatch.setattr(A, "LLM_RETRIES", 3)
    with pytest.raises(RuntimeError, match="OLLAMA_TIMEOUT"):
        A.call_llm(agent(), [{"role": "user", "content": "hi"}])
    assert len(CALLS) == 1  # auf dem Pi keine zweite, ebenso lange Anfrage


def test_gesamtzeit_grenze(ollama, monkeypatch):
    monkeypatch.setenv("OLLAMA_MAX_TIME", "1")
    with pytest.raises(RuntimeError, match="OLLAMA_MAX_TIME"):
        A.call_llm(agent(), [{"role": "user", "content": "hi"}])


def test_standardwerte_grosszuegig(monkeypatch):
    monkeypatch.delenv("OLLAMA_TIMEOUT", raising=False)
    monkeypatch.delenv("OLLAMA_MAX_TIME", raising=False)
    assert A.ollama_limits() == (1800, 7200)
    monkeypatch.setenv("OLLAMA_MAX_TIME", "0")
    assert A.ollama_limits()[1] == 0


def test_zu_wenig_ram_klare_meldung(ollama):
    FakeOllama.mode = "memory"
    with pytest.raises(RuntimeError, match="kleineres"):
        A.call_llm(agent(), [{"role": "user", "content": "hi"}])


def test_modell_fehlt(ollama):
    FakeOllama.mode = "missing"
    with pytest.raises(RuntimeError, match="MODELL_WEG.*ollama pull"):
        A.call_llm(agent(), [{"role": "user", "content": "hi"}])


def test_dashboard_sieht_laufende_anfrage(ollama, client):
    FakeOllama.first = 1.0
    pid = make_project()
    aid = make_agent(pid, "Lokal", provider="ollama")
    t = threading.Thread(target=A.call_llm, args=({"id": aid, "name": "Lokal", "provider": "ollama", "model": "m"},
                                                 [{"role": "user", "content": "hi"}]))
    t.start()
    time.sleep(0.5)
    live = client.get(f"/api/projects/{pid}/graph").get_json()["live"]
    assert len(live) == 1 and live[0]["agent"] == "Lokal" and live[0]["provider"] == "ollama"
    t.join()
    assert client.get(f"/api/projects/{pid}/graph").get_json()["live"] == []


def test_chat_laeuft_im_hintergrund(ollama, client):
    pid = make_project()
    aid = make_agent(pid, "Lokal", provider="ollama")
    r = client.post(f"/api/agents/{aid}/chat", json={"message": "Erzähl was"}).get_json()
    assert r["job"]
    # zweite Nachricht, solange die erste laeuft: abgelehnt
    assert client.post(f"/api/agents/{aid}/chat", json={"message": "noch was"}).status_code == 409
    run = client.get(f"/api/agents/{aid}/chat/job").get_json()
    assert run and not run["done"] and run["message"] == "Erzähl was"
    for _ in range(50):
        j = client.get(f"/api/agents/{aid}/chat/job?id={r['job']}").get_json()
        if j["done"]:
            break
        time.sleep(0.1)
    assert j["reply"] == "Hallo aus dem Pi ü" and not j["error"]
    hist = client.get(f"/api/agents/{aid}/chat").get_json()
    assert [h["role"] for h in hist] == ["user", "assistant"]
    assert client.get(f"/api/agents/{aid}/chat/job").get_json() is None


def test_chat_mock_bleibt_sofort(client):
    pid = make_project()
    aid = make_agent(pid, "M")
    r = client.post(f"/api/agents/{aid}/chat", json={"message": "hallo"}).get_json()
    assert r["reply"].startswith("[Mock M]")
