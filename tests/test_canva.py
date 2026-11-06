"""Bilder ueber Canva (Konnektor der Claude-CLI): canva_upload, IMAGE_PROVIDER=canva, kein Ersatzbild ohne Referenz."""
import pytest

import agent_tools as T
import ai_links as L

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


class Resp:
    def __init__(self, status=200, text='{"media_id": "MABC123"}'):
        self.status_code, self.text = status, text


@pytest.fixture
def canva(monkeypatch, tmp_path):
    monkeypatch.setenv("PCL_CLAUDE_CONNECTORS", "Canva")
    monkeypatch.delenv("PCL_CANVA_UPLOAD_HOSTS", raising=False)
    monkeypatch.setattr(T, "check_public", lambda host: None)
    calls = []

    def post(url, **kw):
        calls.append((url, kw))
        return Resp()
    monkeypatch.setattr(T.requests, "post", post)
    (tmp_path / "input").mkdir()
    (tmp_path / "input/ref.png").write_bytes(PNG)
    return calls


def test_upload_schickt_rohe_bytes(canva, tmp_path):
    out = T.canva_upload(tmp_path, "input/ref.png", "https://upload.canva.com/abc?sig=1")
    assert "MABC123" in out and "input/ref.png" in out
    url, kw = canva[0]
    assert kw["data"] == PNG and kw["headers"]["Content-Type"] == "application/octet-stream"
    assert kw["allow_redirects"] is False


@pytest.mark.parametrize("url", ["http://upload.canva.com/x", "https://evil.example.com/x", "https://canva.com.evil.net/x"])
def test_upload_nur_zu_canva(canva, tmp_path, url):
    with pytest.raises(T.ToolError):
        T.canva_upload(tmp_path, "input/ref.png", url)
    assert canva == []


def test_upload_weitere_hosts_per_env(canva, tmp_path, monkeypatch):
    monkeypatch.setenv("PCL_CANVA_UPLOAD_HOSTS", "canva-uploads.example.net")
    T.canva_upload(tmp_path, "input/ref.png", "https://x.canva-uploads.example.net/u")
    assert len(canva) == 1


def test_upload_ausserhalb_und_ohne_bild(canva, tmp_path):
    (tmp_path / "input/text.txt").write_text("hallo")
    for p in ("../geheim.png", "input/fehlt.png", "input/text.txt"):
        with pytest.raises(T.ToolError):
            T.canva_upload(tmp_path, p, "https://upload.canva.com/x")


def test_upload_fehler_von_canva(canva, tmp_path, monkeypatch):
    monkeypatch.setattr(T.requests, "post", lambda url, **kw: Resp(410, "expired"))
    with pytest.raises(T.ToolError, match="HTTP 410"):
        T.canva_upload(tmp_path, "input/ref.png", "https://upload.canva.com/x")


def test_werkzeug_nur_mit_konnektor(monkeypatch):
    monkeypatch.delenv("PCL_CLAUDE_CONNECTORS", raising=False)
    assert "canva_upload" not in T.available({"images": True})
    monkeypatch.setenv("PCL_CLAUDE_CONNECTORS", "Gmail, canva")
    assert "canva_upload" in T.available({"images": True})
    assert "canva_upload" not in T.available({"web": True})


def test_image_provider_canva_erklaert_den_weg(canva, tmp_path, monkeypatch):
    monkeypatch.setenv("IMAGE_PROVIDER", "canva")
    with pytest.raises(T.ToolError, match="create-upload-url.*canva_upload.*imageReferences"):
        T.image_generate(tmp_path, {"prompt": "Captain auf der Bruecke", "refs": ["input/ref.png"]})
    monkeypatch.delenv("PCL_CLAUDE_CONNECTORS")
    with pytest.raises(T.ToolError, match="not connected"):
        T.image_generate(tmp_path, {"prompt": "x"})


def test_kein_ersatzbild_ohne_referenz_wenn_canva_da(canva, tmp_path, monkeypatch):
    monkeypatch.setenv("IMAGE_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.setenv("IMAGE_FALLBACK", "pollinations")
    monkeypatch.delenv("POLLINATIONS_API_KEY", raising=False)

    def kaputt(*a, **k):
        raise T.ToolError("HTTP 402 Payment Required")
    monkeypatch.setattr(T, "_gen_openrouter", kaputt)
    monkeypatch.setattr(T, "_gen_pollinations", lambda *a, **k: pytest.fail("Ersatzbild ohne Referenz"))
    with pytest.raises(T.ToolError, match="HTTP 402.*canva_upload"):
        T.image_generate(tmp_path, {"prompt": "Captain", "refs": ["input/ref.png"]})


def test_image_save_mit_zielpfad(tmp_path, monkeypatch):
    monkeypatch.setattr(T, "safe_get", lambda url, mx: (None, PNG, False))
    out = T.image_save(tmp_path, "https://media.canva.com/bild.png", path="karten/bilder/k01.png")
    assert "karten/bilder/k01.png" in out and (tmp_path / "karten/bilder/k01.png").read_bytes() == PNG


def test_prompt_nennt_canva_weg(monkeypatch, tmp_path):
    monkeypatch.setenv("PCL_TOKENS_DIR", str(tmp_path))
    monkeypatch.delenv("PCL_CLAUDE_MCP", raising=False)
    monkeypatch.setenv("PCL_CLAUDE_CONNECTORS", "Canva")
    assert "IMAGES THROUGH CANVA" in L.prompt_block("claude_cli")
    monkeypatch.setenv("PCL_CLAUDE_CONNECTORS", "Gmail")
    assert "IMAGES THROUGH CANVA" not in L.prompt_block("claude_cli")


def test_eigener_canva_server_zaehlt_als_konnektor(monkeypatch, tmp_path):
    """Laedt der Abo-Konnektor nicht (Langzeit-Token), darf ein eigener Server 'canva' einspringen."""
    monkeypatch.setenv("PCL_TOKENS_DIR", str(tmp_path))
    monkeypatch.delenv("PCL_CLAUDE_MCP", raising=False)
    monkeypatch.setenv("PCL_CLAUDE_CONNECTORS", "Canva")
    monkeypatch.setattr(L, "LEARNED", {})
    monkeypatch.setattr(L, "STATE", {})
    out = L.claude_args(["claude", "-p", "--strict-mcp-config"])
    assert "mcp__canva" in out[out.index("--allowedTools") + 1].split(",")
    bad = L.record("claude_cli", {"canva": "connected"}, L.claude_config())
    assert bad == [] and L.LEARNED["Canva"] == "canva"
