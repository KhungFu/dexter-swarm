"""Claude-CLI (Abo): Langzeit-Token aus 'claude setup-token' nur an 'claude' weitergeben, Anmeldefehler klar melden und per Telegram warnen."""
import os
import time

import pytest

from conftest import A, make_agent, make_project  # noqa: F401


class R:
    def __init__(self, rc=0, out="ok", err=""):
        self.returncode, self.stdout, self.stderr = rc, out, err


@pytest.fixture
def cli(monkeypatch, tmp_path):
    monkeypatch.setenv("PCL_TOKENS_DIR", str(tmp_path))
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.setattr(A, "ALLOW_CLI", True)
    monkeypatch.setattr(A.shutil, "which", lambda b: "/usr/bin/" + b)
    monkeypatch.setitem(A._claude_alarm, "auth", 0.0)
    monkeypatch.setitem(A._claude_alarm, "age", 0.0)
    sent, runs = [], []
    monkeypatch.setattr(A, "tg_notify", lambda text, *a, **k: sent.append(text))
    state = {"r": R()}

    def fake_run(argv, **kw):
        runs.append((argv, kw))
        return state["r"]
    monkeypatch.setattr(A.subprocess, "run", fake_run)
    return {"dir": tmp_path, "sent": sent, "runs": runs, "state": state}


def agent(provider="claude_cli"):
    pid = make_project()
    aid = make_agent(pid, "A", provider=provider)
    return A.q1("SELECT * FROM agents WHERE id=?", (aid,))


def test_token_file_goes_only_to_claude(cli, monkeypatch):
    (cli["dir"] / "claude-oauth-token.txt").write_text("sk-ant-oat01-abc\n")
    monkeypatch.setenv("SOME_API_KEY", "geheim")
    A._call_llm(agent(), [{"role": "user", "content": "hi"}])
    env = cli["runs"][-1][1]["env"]
    assert env["CLAUDE_CODE_OAUTH_TOKEN"] == "sk-ant-oat01-abc" and "SOME_API_KEY" not in env
    A._call_llm(agent("codex_cli"), [{"role": "user", "content": "hi"}])
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in cli["runs"][-1][1]["env"]


def test_env_token_fallback_and_none(cli, monkeypatch):
    A._call_llm(agent(), [{"role": "user", "content": "hi"}])
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in cli["runs"][-1][1]["env"]  # ohne Token: claude nutzt seine eigene Anmeldung
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-env")
    A._call_llm(agent(), [{"role": "user", "content": "hi"}])
    assert cli["runs"][-1][1]["env"]["CLAUDE_CODE_OAUTH_TOKEN"] == "sk-ant-oat01-env"


def test_auth_error_hint_and_alarm_once(cli):
    cli["state"]["r"] = R(1, "", "Invalid API key · Please run /login")
    for _ in range(2):
        with pytest.raises(RuntimeError) as e:
            A._call_llm(agent(), [{"role": "user", "content": "hi"}])
        assert "claude-erneuern" in str(e.value)
    assert len(cli["sent"]) == 1 and "claude-erneuern" in cli["sent"][0]


def test_other_errors_unchanged(cli):
    cli["state"]["r"] = R(1, "", "Overloaded")
    with pytest.raises(RuntimeError) as e:
        A._call_llm(agent(), [{"role": "user", "content": "hi"}])
    assert "claude-erneuern" not in str(e.value) and not cli["sent"]


def test_age_warning(cli):
    f = cli["dir"] / "claude-oauth-token.txt"
    f.write_text("sk-ant-oat01-abc")
    A._call_llm(agent(), [{"role": "user", "content": "hi"}])
    assert not cli["sent"] and A.claude_token_days_left() >= 364
    old = time.time() - 350 * 86400
    os.utime(f, (old, old))
    A._call_llm(agent(), [{"role": "user", "content": "hi"}])
    A._call_llm(agent(), [{"role": "user", "content": "hi"}])
    assert len(cli["sent"]) == 1 and "expires in about" in cli["sent"][0]
