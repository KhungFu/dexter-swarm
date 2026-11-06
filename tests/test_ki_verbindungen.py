"""Eigene Verbindungen (MCP) der Herkunfts-KI: Konfiguration aus tokens/, Status aus der init-Zeile, ehrliche Meldung an den CEO."""
import json

import pytest

import ai_links as L
from conftest import A, make_agent, make_project

BASE_ARGV = ["claude", "-p", "--tools", "", "--strict-mcp-config", "--no-session-persistence"]


class R:
    def __init__(self, rc=0, out="ok", err=""):
        self.returncode, self.stdout, self.stderr = rc, out, err


def stream(servers, answer="fertig"):
    init = {"type": "system", "subtype": "init", "tools": [], "mcp_servers": [{"name": n, "status": s} for n, s in servers.items()]}
    return json.dumps(init) + "\n" + json.dumps({"type": "result", "is_error": False, "result": answer}) + "\n"


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("PCL_TOKENS_DIR", str(tmp_path))
    monkeypatch.delenv("PCL_CLAUDE_MCP", raising=False)
    monkeypatch.delenv("PCL_CLAUDE_CONNECTORS", raising=False)
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex"))
    monkeypatch.setattr(A, "ALLOW_CLI", True)
    monkeypatch.setattr(A.shutil, "which", lambda b: "/usr/bin/" + b)
    monkeypatch.setattr(L, "STATE", {})
    monkeypatch.setattr(L, "LEARNED", {})
    monkeypatch.setattr(A, "_links_alarm", {})
    sent, runs = [], []
    monkeypatch.setattr(A, "tg_notify", lambda text, *a, **k: sent.append(text))
    state = {"r": R()}

    def fake_run(argv, **kw):
        runs.append((argv, kw))
        return state["r"]
    monkeypatch.setattr(A.subprocess, "run", fake_run)
    return {"dir": tmp_path, "sent": sent, "runs": runs, "state": state}


def mcp_file(d, servers):
    (d / "claude-mcp.json").write_text(json.dumps({"mcpServers": servers}))


def agent(provider="claude_cli", parent=None):
    pid = make_project()
    aid = make_agent(pid, "CEO", provider=provider, parent=parent)
    return A.q1("SELECT * FROM agents WHERE id=?", (aid,))


def test_without_config_nothing_changes(env):
    assert L.claude_args(BASE_ARGV) == BASE_ARGV
    A._call_llm(agent(), [{"role": "user", "content": "hi"}])
    argv = env["runs"][-1][0]
    assert "--strict-mcp-config" in argv and "--mcp-config" not in argv and "stream-json" not in argv


def test_mcp_file_and_connectors_build_args(env, monkeypatch):
    mcp_file(env["dir"], {"echo": {"command": "python3"}, "web site": {"type": "http", "url": "https://x.example/mcp"}})
    out = L.claude_args(BASE_ARGV)
    assert out[out.index("--mcp-config") + 1] == str(env["dir"] / "claude-mcp.json")
    assert out[out.index("--allowedTools") + 1] == "mcp__echo,mcp__web_site"
    assert "--strict-mcp-config" in out  # ohne Konnektoren bleiben fremde MCP-Server aus
    monkeypatch.setenv("PCL_CLAUDE_CONNECTORS", "Canva, Google Drive")
    out = L.claude_args(["claude", "-p", "--allowedTools", "Read,Glob", "--strict-mcp-config"])
    assert "--strict-mcp-config" not in out
    assert out[out.index("--allowedTools") + 1] == "Read,Glob,mcp__echo,mcp__web_site,mcp__claude_ai_Canva,mcp__claude_ai_Google_Drive,mcp__canva,mcp__google_drive"
    assert out.count("--allowedTools") == 1


def test_invalid_file_is_reported_not_swallowed(env):
    (env["dir"] / "claude-mcp.json").write_text("{kaputt")
    cfg = L.claude_config()
    assert cfg["error"] and not L.active(cfg)
    A._call_llm(agent(), [{"role": "user", "content": "hi"}])
    assert any("claude-mcp.json" in s for s in env["sent"])
    assert A.q1("SELECT 1 FROM audit WHERE event='ai_link_failed'")
    assert "CONFIGURATION ERROR" in L.prompt_block("claude_cli", top=True)
    (env["dir"] / "claude-mcp.json").write_text(json.dumps({"mcpServers": {"x": {"args": []}}}))
    assert "without 'command' or 'url'" in L.claude_config()["error"]


def test_status_from_init_line_and_alarm(env, monkeypatch):
    mcp_file(env["dir"], {"echo": {"command": "python3"}, "drive": {"command": "npx"}})
    monkeypatch.setenv("PCL_CLAUDE_CONNECTORS", "Canva")
    env["state"]["r"] = R(0, stream({"echo": "connected", "drive": "failed", "claude.ai Canva": "needs-auth"}, "Antwort"))
    out, _ = A._call_llm(agent(), [{"role": "user", "content": "hi"}])
    assert out == "Antwort"
    argv = env["runs"][-1][0]
    assert "stream-json" in argv and "--mcp-config" in argv
    st = {r["name"]: r["status"] for r in L.overview("claude_cli")["links"]}
    assert st == {"echo": "connected", "drive": "failed", "Canva (claude.ai connector)": "needs-auth"}
    assert len(env["sent"]) == 2 and any("drive" in s for s in env["sent"]) and any("Canva" in s for s in env["sent"])
    A._call_llm(agent(), [{"role": "user", "content": "hi"}])
    assert len(env["sent"]) == 2  # nicht bei jedem Aufruf erneut
    block = L.prompt_block("claude_cli")
    assert "echo: connected" in block and "FAILED" in block and "NEEDS SIGN-IN" in block


def test_connector_missing_and_learned_name(env, monkeypatch):
    monkeypatch.setenv("PCL_CLAUDE_CONNECTORS", "Canva")
    env["state"]["r"] = R(0, stream({}))
    A._call_llm(agent(), [{"role": "user", "content": "hi"}])
    assert L.overview("claude_cli")["links"][0]["status"] == "missing"
    env["state"]["r"] = R(0, stream({"claude_ai_Canva": "connected"}))
    A._call_llm(agent(), [{"role": "user", "content": "hi"}])
    assert L.overview("claude_cli")["links"][0]["status"] == "connected"
    assert "mcp__claude_ai_Canva" in ",".join(L.claude_args(BASE_ARGV))


def test_images_and_links_in_one_stream(env, monkeypatch):
    mcp_file(env["dir"], {"echo": {"command": "python3"}})
    env["state"]["r"] = R(0, stream({"echo": "connected"}, "sehe Bild"))
    out, _ = A._call_llm(agent(), [{"role": "user", "content": "was siehst du?"}], images=[("image/png", "AAAA")])
    assert out == "sehe Bild"
    msg = json.loads(env["runs"][-1][1]["input"])
    assert [c["type"] for c in msg["message"]["content"]] == ["text", "image"]


def test_werkstatt_keeps_its_tools_and_adds_mcp(env, monkeypatch):
    mcp_file(env["dir"], {"echo": {"command": "python3"}})
    argv = ["claude", "-p", "--tools", "Read,Glob,Grep", "--allowedTools", "Read,Glob,Grep", "--strict-mcp-config"]
    out = L.claude_args(argv)
    assert out[out.index("--allowedTools") + 1] == "Read,Glob,Grep,mcp__echo"
    assert out[out.index("--tools") + 1] == "Read,Glob,Grep"


def test_prompt_blocks(env, monkeypatch):
    assert L.prompt_block("openai", top=True) == ""
    assert L.prompt_block("claude_cli", top=False) == ""  # Mitarbeiter ohne Verbindungen: kein Text
    assert "docs/ki-verbindungen.md" in L.prompt_block("claude_cli", top=True)
    (env["dir"] / "codex").mkdir()
    (env["dir"] / "codex" / "config.toml").write_text('model = "x"\n[mcp_servers.figma]\ncommand = "npx"\n[mcp_servers."my docs"]\nurl = "u"\n')
    assert L.codex_servers() == ["figma", "my docs"]
    assert "figma: configured in Codex" in L.prompt_block("codex_cli")
    monkeypatch.setenv("PCL_CLAUDE_CONNECTORS", "Canva")
    a = agent()
    proj = A.q1("SELECT * FROM projects WHERE id=?", (a["project_id"],))
    chat = A.chat_system(a, proj)
    assert "Canva (claude.ai connector): not checked yet" in chat and "Apart from the own connections" in chat
    assert "OWN CONNECTIONS OF YOUR AI" in A.build_system(a, proj, "work")


def test_api_lists_links(env, client, monkeypatch):
    monkeypatch.setenv("PCL_CLAUDE_CONNECTORS", "Canva")
    data = client.get("/api/ai_links").get_json()
    assert data[0]["links"][0] == {"name": "Canva (claude.ai connector)", "status": "unchecked", "checked": None}
    env["state"]["r"] = R(0, stream({"claude.ai Canva": "connected"}, "ready"))
    data = client.post("/api/ai_links/check").get_json()
    assert data[0]["links"][0]["status"] == "connected"
    assert "haiku" in env["runs"][-1][0]


def test_chat_attaches_newest_image_when_owner_mentions_it(client, tmp_path):
    pid = make_project()
    aid = make_agent(pid, "CEO")
    inp = A.proj_dir(pid) / "input"
    inp.mkdir(parents=True, exist_ok=True)
    png = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                        "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082")
    (inp / "notizen.txt").write_text("hallo")
    (inp / "strichmaennchen.png").write_bytes(png)
    r = client.post(f"/api/agents/{aid}/chat", json={"message": "Das Referenzbild habe ich beigefügt."}).get_json()
    assert r["files"] == ["input/strichmaennchen.png"]
    r = client.post(f"/api/agents/{aid}/chat", json={"message": "Die Ausbildung der Figuren ist wichtig."}).get_json()
    assert r["files"] == []
