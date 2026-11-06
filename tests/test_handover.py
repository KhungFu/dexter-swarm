"""Uebergabe-Stand (handover/) und automatisches Weitermachen nach Fehler, Neustart oder Modellwechsel (Wunsch ABI 2026-11-06)."""
import json
import time

import pytest

import handover as HO
from conftest import A, client, drain, make_agent, make_project, make_task, task  # noqa: F401


@pytest.fixture(autouse=True)
def quiet(monkeypatch):
    sent = []
    monkeypatch.setattr(A, "tg_notify", lambda text, *a, **k: sent.append(text))
    return sent


class Script:
    """Antworten der Reihe nach; ein Eintrag 'ERROR:...' wirft eine Ausnahme wie ein volles Kontingent."""

    def __init__(self, monkeypatch, replies):
        self.replies, self.seen = list(replies), []
        monkeypatch.setattr(A, "call_llm", self)

    def __call__(self, agent, messages, images=None):
        self.seen.append((agent["model"], str(messages[-1]["content"])))
        r = self.replies.pop(0) if self.replies else json.dumps({"result": "fertig"})
        if r.startswith("ERROR:"):
            raise RuntimeError(r[6:])
        return r, 10


def handover_text(pid, tid):
    return HO.path(A.proj_dir(pid), tid).read_text(encoding="utf-8")


def test_steps_and_next_step_are_saved(monkeypatch):
    pid = make_project("Nexora")
    dev = make_agent(pid, "Dev", write_files=True)
    tid = make_task(pid, dev, "Rust-Umbau")
    Script(monkeypatch, [json.dumps({"tools": [{"tool": "write_file", "path": "src/main.rs", "content": "fn main(){}"}]}),
                         json.dumps({"result": "main.rs angelegt", "next_step": "Tests schreiben"})])
    drain()
    assert task(tid)["status"] == "done"
    text = handover_text(pid, tid)
    assert "HANDOVER: assignment" in text and "Rust-Umbau" in text
    assert "start (work)" in text and "tool round 1" in text and "write_file src/main.rs" in text
    assert "NEXT STEP: Tests schreiben" in text and "mock/" in text


def test_error_waits_and_model_change_continues(monkeypatch, client):
    pid = make_project("Nexora")
    dev = make_agent(pid, "Dev", write_files=True)
    tid = make_task(pid, dev, "Rust-Umbau")
    s = Script(monkeypatch, [json.dumps({"tools": [{"tool": "write_file", "path": "a.txt", "content": "x"}]}),
                             "ERROR:HTTP 429 quota exceeded"])
    drain()
    t = task(tid)
    assert t["status"] == "queued" and t["retries"] == 1 and t["retry_at"] > time.time() + 60
    assert A.claim_next() is None  # wartet
    assert "quota exceeded" in handover_text(pid, tid) and "write_file a.txt" in handover_text(pid, tid)
    assert "STOPPED BY AN ERROR" in A.inspection_report(pid)
    # Besitzer stellt ein anderes Modell ein -> sofort weiter, neues Modell bekommt den Stand
    r = client.put(f"/api/agents/{dev}", json={"model": "anderes-modell"})
    assert r.status_code == 200
    assert task(tid)["retry_at"] == 0
    s.replies = [json.dumps({"result": "weiter und fertig"})]
    drain()
    assert task(tid)["status"] == "done"
    model, prompt = s.seen[-1]
    assert model == "anderes-modell"
    assert "HANDOVER STATE" in prompt and "write_file a.txt" in prompt and prompt.count(A.RESUME_MARK) >= 1
    assert "AI model changed" in handover_text(pid, tid)


def test_retries_run_out(monkeypatch):
    monkeypatch.setattr(A, "RETRY_MAX", 1)
    pid = make_project("Nexora")
    dev = make_agent(pid, "Dev")
    tid = make_task(pid, dev, "X")
    Script(monkeypatch, ["ERROR:kaputt", "ERROR:wieder kaputt"])
    drain()
    A.set_task(tid, retry_at=0)
    drain()
    t = task(tid)
    assert t["status"] == "failed" and t["result"].startswith("Error:")
    assert "no automatic retry left" in handover_text(pid, tid)


def test_failed_top_task_resumes_after_model_change(monkeypatch):
    monkeypatch.setattr(A, "AUTO_RESUME", True)
    pid = make_project("Nexora")
    dev = make_agent(pid, "Dev")
    tid = make_task(pid, dev, "X", status="failed")
    A.set_task(tid, result="Error: alt")
    assert A.model_changed([dev], "groq/neu") == 1
    assert task(tid)["status"] == "queued" and task(tid)["feedback"].startswith(A.RESUME_MARK)


def test_restart_continues_running_task():
    pid = make_project("Nexora")
    dev = make_agent(pid, "Dev")
    tid = make_task(pid, dev, "X", status="running")
    A.init_db()
    t = task(tid)
    assert t["status"] == "queued" and t["feedback"].startswith(A.RESUME_MARK)
    assert "server restart" in handover_text(pid, tid)


def test_subtask_writes_into_top_assignment(monkeypatch):
    pid = make_project("Nexora")
    ceo = make_agent(pid, "CEO", delegate=True)
    make_agent(pid, "Dev", parent=ceo)
    tid = make_task(pid, ceo, "Gesamt")
    Script(monkeypatch, [json.dumps({"result": "Plan", "delegate": [{"to": "Dev", "title": "Teil", "description": "mach"}]}),
                         json.dumps({"result": "Teil fertig", "next_step": "nichts"}),
                         json.dumps({"result": "alles fertig"})])
    drain()
    assert task(tid)["status"] == "done"
    text = handover_text(pid, tid)
    assert "Teil fertig" in text and "alles fertig" in text
    sub = A.q1("SELECT id FROM tasks WHERE parent_task_id=?", (tid,))["id"]
    assert not HO.path(A.proj_dir(pid), sub).exists()  # Mitarbeiter schreiben in die Datei des obersten Auftrags


def test_workplace_finds_repo_and_stand(tmp_path):
    repo = tmp_path / "swarm"
    (repo / ".git").mkdir(parents=True)
    (repo / ".git" / "config").write_text('[remote "origin"]\n\turl = https://user:geheim@github.com/KhungFu/swarm\n')
    (repo / "rust" / "dexter-core").mkdir(parents=True)
    (repo / "rust" / "dexter-core" / "STAND.md").write_text("x")
    text = HO.workplace_text(tmp_path, "nexora")
    assert "swarm (https://github.com/KhungFu/swarm)" in text and "geheim" not in text
    assert "swarm/rust/dexter-core/STAND.md" in text


def test_trim_keeps_header(tmp_path, monkeypatch):
    monkeypatch.setattr(HO, "MAX_BYTES", 4000)
    top = {"id": 7, "title": "T", "description": "D"}
    for i in range(80):
        HO.note(tmp_path, top, 7, "Dev", f"step {i}", "x" * 200)
    text = HO.path(tmp_path, 7).read_text(encoding="utf-8")
    assert text.startswith("# HANDOVER") and "step 79" in text and "step 0 " not in text and len(text) < 5000


def test_switch_off(monkeypatch):
    monkeypatch.setenv("PCL_HANDOVER", "0")
    pid = make_project("Ohne Uebergabe")
    dev = make_agent(pid, "Dev")
    make_task(pid, dev, "X")
    drain()
    assert not (A.proj_dir(pid) / "handover").exists()
