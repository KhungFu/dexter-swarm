"""image_generate gegen simulierte Bild-APIs (kein echter Key, kein Internet)."""
import base64
import json

import pytest

import agent_tools as T

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


class Resp:
    def __init__(self, body, status=200):
        self.status_code, self._body = status, body
        self.text = json.dumps(body)

    def json(self):
        return self._body


@pytest.fixture
def openai(monkeypatch):
    monkeypatch.setenv("IMAGE_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("IMAGE_QUALITY", raising=False)
    calls = []

    def post(url, **kw):
        calls.append((url, kw))
        return Resp({"data": [{"b64_json": base64.b64encode(PNG).decode()}]})
    monkeypatch.setattr(T.requests, "post", post)
    return calls


def test_openai_ohne_referenz(openai, tmp_path):
    out = T.image_generate(tmp_path, {"prompt": "Kind malt mit Buntstift", "name": "Karte 1", "format": "hoch"})
    assert "assets/karte-1.png" in out and (tmp_path / "assets/karte-1.png").read_bytes() == PNG
    url, kw = openai[0]
    assert url.endswith("/images/generations")
    assert kw["json"]["size"] == "1024x1536" and kw["headers"]["Authorization"] == "Bearer sk-test"


def test_openai_mit_referenzbildern_und_zielpfad(openai, tmp_path):
    (tmp_path / "input").mkdir()
    (tmp_path / "input/figuren.png").write_bytes(PNG)
    (tmp_path / "input/stil.jpg").write_bytes(JPG)
    out = T.image_generate(tmp_path, {"prompt": "K1 und K6 spielen", "refs": ["input/figuren.png", "input/stil.jpg"],
                                      "path": "karten/bilder/k01.png", "quality": "high"})
    assert "with 2 reference image" in out and (tmp_path / "karten/bilder/k01.png").exists()
    url, kw = openai[0]
    assert url.endswith("/images/edits")
    assert [f[0] for f in kw["files"]] == ["image[]", "image[]"]
    assert kw["files"][1][1][2] == "image/jpeg"
    assert kw["data"]["quality"] == "high" and kw["data"]["size"] == "1024x1024"
    # gleicher Pfad nochmal: wird ersetzt statt k01-1.png
    T.image_generate(tmp_path, {"prompt": "neu", "path": "karten/bilder/k01.png"})
    assert sorted(p.name for p in (tmp_path / "karten/bilder").iterdir()) == ["k01.png"]


@pytest.mark.parametrize("call, msg", [
    ({"prompt": "x", "path": "../weg.png"}, "outside"),
    ({"prompt": "x", "path": "input/x.png"}, "path must be in"),
    ({"prompt": "x", "path": "karten.png"}, "path must be in"),
    ({"prompt": "x", "refs": ["input/fehlt.png"]}, "not found"),
    ({"prompt": "x", "refs": ["../../etc/passwd"]}, "not found"),
    ({"prompt": "x", "refs": ["a.png"] * 5}, "Hoechstens"),
    ({"prompt": "x", "format": "rund"}, "format"),
    ({"prompt": "x", "quality": "ultra"}, "quality"),
    ({"prompt": ""}, "prompt missing"),
])
def test_ungueltige_eingaben_kosten_nichts(openai, tmp_path, call, msg):
    with pytest.raises(T.ToolError, match=msg):
        T.image_generate(tmp_path, call)
    assert not openai  # Fehler fallen VOR dem kostenpflichtigen Aufruf auf


def test_referenz_muss_bild_sein(openai, tmp_path):
    (tmp_path / "notiz.txt").write_text("kein Bild")
    with pytest.raises(T.ToolError, match="PNG, JPG or WEBP"):
        T.image_generate(tmp_path, {"prompt": "x", "refs": "notiz.txt"})


def test_openai_fehler_wird_gemeldet(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(T.requests, "post", lambda url, **kw: Resp({"error": {"message": "Incorrect API key"}}, 401))
    with pytest.raises(T.ToolError, match="HTTP 401 Incorrect API key"):
        T.image_generate(tmp_path, {"prompt": "x"})


def test_openai_ohne_key(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    with pytest.raises(T.ToolError, match="OPENAI_API_KEY is missing"):
        T.image_generate(tmp_path, {"prompt": "x"})


def test_gemini_mit_referenz(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "g-test")
    seen = {}

    def post(url, **kw):
        seen.update(url=url, **kw)
        return Resp({"candidates": [{"content": {"parts": [{"inlineData": {"data": base64.b64encode(PNG).decode()}}]}}]})
    monkeypatch.setattr(T.requests, "post", post)
    (tmp_path / "ref.png").write_bytes(PNG)
    out = T.image_generate(tmp_path, {"prompt": "x", "refs": ["ref.png"], "format": "quer", "path": "output/a.png"})
    assert "output/a.png" in out
    parts = seen["json"]["contents"][0]["parts"]
    assert parts[0] == {"text": "x"} and parts[1]["inline_data"]["mime_type"] == "image/png"
    assert "/models/gemini-2.5-flash-image:generateContent" in seen["url"]
    assert seen["json"]["generationConfig"]["imageConfig"] == {"aspectRatio": "3:2"}


def test_gemini_bildgroesse_und_abrechnungshinweis(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "g-test")
    monkeypatch.setenv("IMAGE_SIZE", "2k")
    seen = {}

    def post(url, **kw):
        seen.update(kw)
        return Resp({"error": {"code": 429, "message": "quota exceeded, limit: 0"}}, 429)
    monkeypatch.setattr(T.requests, "post", post)
    with pytest.raises(T.ToolError, match="HTTP 429.*billing"):
        T.image_generate(tmp_path, {"prompt": "x"})
    assert seen["json"]["generationConfig"]["imageConfig"]["imageSize"] == "2K"


def test_pollinations_lehnt_referenzen_ab(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "pollinations")
    (tmp_path / "ref.png").write_bytes(PNG)
    with pytest.raises(T.ToolError, match="only work with IMAGE_PROVIDER=openai, gemini, openrouter, sdcpp, cloudflare, nvidia"):
        T.image_generate(tmp_path, {"prompt": "x", "refs": ["ref.png"]})


def test_recht_bilder_oder_medien(openai, tmp_path):
    assert "image_generate" in T.available({"images": 1})
    assert "image_generate" in T.available({"media": 1})
    assert "image_generate" not in T.available({"web": 1})
    text, made = T.run_tool({"tool": "image_generate", "prompt": "x", "path": "karten/k02.png"}, tmp_path, {"media": 1})
    assert made == "karten/k02.png", text
    text, _ = T.run_tool({"tool": "image_generate", "prompt": "x"}, tmp_path, {"web": 1})
    assert "not allowed" in text


@pytest.mark.parametrize("value, expected", [
    ("", "gemini-2.5-flash-image"), ("  ", "gemini-2.5-flash-image"), ('"gemini-nano-banana-2.1"', "gemini-nano-banana-2.1"),
    ("models/gemini-3-pro-image", "gemini-3-pro-image"), ("gemini-2.5-flash-image\r", "gemini-2.5-flash-image"),
])
def test_gemini_modellname_gehaertet(monkeypatch, tmp_path, value, expected):
    monkeypatch.setenv("IMAGE_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "g-test")
    monkeypatch.setenv("IMAGE_MODEL", value)
    seen = {}

    def post(url, **kw):
        seen["url"] = url
        return Resp({"error": {"code": 400, "message": "bad"}}, 400)
    monkeypatch.setattr(T.requests, "post", post)
    with pytest.raises(T.ToolError, match=f"Gemini \\({expected}\\).*HTTP 400"):
        T.image_generate(tmp_path, {"prompt": "x"})
    assert seen["url"].endswith(f"/models/{expected}:generateContent")


def test_openrouter_mit_referenz(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")
    monkeypatch.delenv("IMAGE_MODEL", raising=False)
    monkeypatch.delenv("IMAGE_SIZE", raising=False)
    seen = {}

    def post(url, **kw):
        seen.update(url=url, **kw)
        return Resp({"data": [{"b64_json": base64.b64encode(PNG).decode(), "media_type": "image/png"}]})
    monkeypatch.setattr(T.requests, "post", post)
    (tmp_path / "ref.jpg").write_bytes(JPG)
    out = T.image_generate(tmp_path, {"prompt": "x", "refs": ["ref.jpg"], "format": "hoch", "path": "karten/k1.png"})
    assert "karten/k1.png" in out and (tmp_path / "karten/k1.png").read_bytes() == PNG
    assert seen["url"] == "https://openrouter.ai/api/v1/images"
    assert seen["headers"]["Authorization"] == "Bearer or-test"
    body = seen["json"]
    assert body["model"] == "google/gemini-2.5-flash-image" and body["aspect_ratio"] == "2:3"
    assert body["input_references"][0]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_openrouter_fehler_und_key(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    with pytest.raises(T.ToolError, match="OPENROUTER_API_KEY is missing"):
        T.image_generate(tmp_path, {"prompt": "x"})
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")
    monkeypatch.setattr(T.requests, "post", lambda url, **kw: Resp({"error": {"message": "Insufficient credits"}}, 402))
    with pytest.raises(T.ToolError, match="HTTP 402 .*credit.*Insufficient credits"):
        T.image_generate(tmp_path, {"prompt": "x"})


class Raw:
    status_code, content = 200, PNG


def test_rueckfall_auf_pollinations(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")
    monkeypatch.setattr(T.requests, "post", lambda url, **kw: Resp({"error": {"message": "Insufficient credits"}}, 402))
    got = []
    monkeypatch.setattr(T.requests, "get", lambda url, **kw: got.append(url) or Raw())
    (tmp_path / "ref.png").write_bytes(PNG)
    call = {"prompt": "x", "refs": ["ref.png"], "path": "karten/k1.png"}
    monkeypatch.delenv("IMAGE_FALLBACK", raising=False)
    with pytest.raises(T.ToolError, match="402"):  # Standard: kein Rueckfall
        T.image_generate(tmp_path, call)
    assert not got
    monkeypatch.setenv("IMAGE_FALLBACK", "pollinations")
    out = T.image_generate(tmp_path, call)
    assert "pollinations" in got[0] and (tmp_path / "karten/k1.png").exists()
    assert out.startswith("NOTE: switched to Pollinations") and "with openrouter" in out and "HTTP 402" in out[:150]
    assert "WITHOUT reference images" in out and "with 1 reference image" not in out
    text, made = T.run_tool({"tool": "image_generate", **call}, tmp_path, {"media": 1})
    assert made == "karten/k1.png", text


def test_pollinations_mit_key_modell_und_referenzen(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "pollinations")
    monkeypatch.setenv("POLLINATIONS_API_KEY", "sk_test")
    monkeypatch.setenv("IMAGE_STYLE", "Buntstift auf Pastell")
    monkeypatch.delenv("POLLINATIONS_MODEL", raising=False)
    seen = {}

    def post(url, **kw):
        seen.update(url=url, **kw)
        return Resp({"data": [{"b64_json": base64.b64encode(PNG).decode()}]})
    monkeypatch.setattr(T.requests, "post", post)
    (tmp_path / "ref.png").write_bytes(PNG)
    out = T.image_generate(tmp_path, {"prompt": "K1 winkt", "refs": ["ref.png"], "format": "hoch", "path": "karten/k1.png"})
    assert "with 1 reference image" in out and (tmp_path / "karten/k1.png").read_bytes() == PNG
    body = seen["json"]
    assert seen["url"] == "https://gen.pollinations.ai/v1/images/generations"
    assert seen["headers"]["Authorization"] == "Bearer sk_test"
    assert body["model"] == T.POLLINATIONS_MODEL and body["size"] == "1024x1536"
    assert isinstance(body["image"], list) and body["image"][0].startswith("data:image/png;base64,")
    assert body["prompt"].startswith("Stil: Buntstift auf Pastell") and "K1 winkt" in body["prompt"]


def test_pollinations_guthaben_leer(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "pollinations")
    monkeypatch.setenv("POLLINATIONS_API_KEY", "sk_test")
    monkeypatch.setenv("POLLINATIONS_MODEL", "google/gemini-2.5-flash-image")
    monkeypatch.setattr(T.requests, "post", lambda url, **kw: Resp({"error": {"message": "budget exhausted"}}, 402))
    with pytest.raises(T.ToolError, match="gemini-2.5-flash-image.*HTTP 402.*Pollen-Guthaben"):
        T.image_generate(tmp_path, {"prompt": "x"})


def test_pollinations_ohne_key_mit_modell(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "pollinations")
    monkeypatch.delenv("POLLINATIONS_API_KEY", raising=False)
    monkeypatch.setenv("POLLINATIONS_MODEL", "flux")
    seen = {}
    monkeypatch.setattr(T.requests, "get", lambda url, **kw: seen.update(url=url, **kw) or Raw())
    T.image_generate(tmp_path, {"prompt": "x"})
    assert seen["url"].startswith("https://image.pollinations.ai/prompt/") and seen["params"]["model"] == "flux"


def test_rueckfall_mit_pollinations_key_behaelt_referenzen(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")
    monkeypatch.setenv("IMAGE_FALLBACK", "pollinations")
    monkeypatch.setenv("POLLINATIONS_API_KEY", "sk_test")
    urls = []

    def post(url, **kw):
        urls.append(url)
        if "openrouter" in url:
            return Resp({"error": {"message": "Insufficient credits"}}, 402)
        assert len(kw["json"]["image"]) == 1
        return Resp({"data": [{"b64_json": base64.b64encode(PNG).decode()}]})
    monkeypatch.setattr(T.requests, "post", post)
    (tmp_path / "ref.png").write_bytes(PNG)
    out = T.image_generate(tmp_path, {"prompt": "x", "refs": ["ref.png"]})
    assert "gen.pollinations.ai" in urls[-1] and "with 1 reference image" in out and "pollen credit and reference images" in out


def test_sdcpp_laptop_mit_referenz(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "sdcpp")
    monkeypatch.setenv("SDCPP_URL", "http://192.168.1.50:1234/")
    monkeypatch.delenv("SDCPP_SIZE", raising=False)
    seen = {}

    def post(url, **kw):
        seen.update(url=url, **kw)
        return Resp({"images": [base64.b64encode(PNG).decode()]})
    monkeypatch.setattr(T.requests, "post", post)
    (tmp_path / "ref.png").write_bytes(PNG)
    out = T.image_generate(tmp_path, {"prompt": "K1 winkt", "refs": ["ref.png"], "format": "quer", "path": "karten/k1.png"})
    assert "with 1 reference image" in out and (tmp_path / "karten/k1.png").read_bytes() == PNG
    body = seen["json"]
    assert seen["url"] == "http://192.168.1.50:1234/sdapi/v1/txt2img"
    assert (body["width"], body["height"]) == (1024, 672) and body["steps"] == 4 and body["cfg_scale"] == 1.0
    assert body["extra_images"][0].startswith("data:image/png;base64,")
    assert seen["timeout"] == (10, 1800)


def test_sdcpp_groesse_fehler_und_url(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "sdcpp")
    monkeypatch.delenv("SDCPP_URL", raising=False)
    with pytest.raises(T.ToolError, match="SDCPP_URL is missing"):
        T.image_generate(tmp_path, {"prompt": "x"})
    monkeypatch.setenv("SDCPP_URL", "http://laptop:1234")
    monkeypatch.setenv("SDCPP_SIZE", "768")
    seen = {}
    monkeypatch.setattr(T.requests, "post", lambda url, **kw: seen.update(kw) or Resp({"error": "out of memory"}, 500))
    with pytest.raises(T.ToolError, match="HTTP 500 out of memory"):
        T.image_generate(tmp_path, {"prompt": "x", "format": "hoch"})
    assert (seen["json"]["width"], seen["json"]["height"]) == (512, 768)


def test_sdcpp_laptop_aus_rueckfall(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "sdcpp")
    monkeypatch.setenv("SDCPP_URL", "http://laptop:1234")
    monkeypatch.setenv("IMAGE_FALLBACK", "pollinations")
    monkeypatch.delenv("POLLINATIONS_API_KEY", raising=False)

    def post(url, **kw):
        raise T.requests.ConnectionError("connection refused")
    monkeypatch.setattr(T.requests, "post", post)
    monkeypatch.setattr(T.requests, "get", lambda url, **kw: Raw())
    out = T.image_generate(tmp_path, {"prompt": "x"})
    assert out.startswith("NOTE: switched to Pollinations") and "with sdcpp" in out


class Img:
    status_code, content, headers, text = 200, PNG, {"content-type": "image/png"}, ""


def test_nvidia_schnell_und_kontext(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "nvidia")
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")
    monkeypatch.delenv("IMAGE_MODEL", raising=False)
    seen = {}

    def post(url, **kw):
        seen.update(url=url, **kw)
        return Resp({"artifacts": [{"base64": base64.b64encode(PNG).decode(), "finishReason": "SUCCESS"}]})
    monkeypatch.setattr(T.requests, "post", post)
    T.image_generate(tmp_path, {"prompt": "x"})
    assert seen["url"] == "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-schnell"
    assert seen["json"]["steps"] == 4 and "width" not in seen["json"]
    monkeypatch.setenv("IMAGE_MODEL", "black-forest-labs/flux.1-kontext-dev")
    (tmp_path / "ref.png").write_bytes(PNG)
    out = T.image_generate(tmp_path, {"prompt": "x", "refs": ["ref.png"], "format": "quadrat"})
    assert "with 1 reference image" in out and seen["json"]["image"].startswith("data:image/png;base64,")
    assert (seen["json"]["width"], seen["json"]["height"]) == (1024, 1024)
    (tmp_path / "ref2.png").write_bytes(PNG)
    with pytest.raises(T.ToolError, match="hoechstens 1 Referenzbild"):
        T.image_generate(tmp_path, {"prompt": "x", "refs": ["ref.png", "ref2.png"]})


def test_cloudflare_flux2_multipart_mit_refs(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "cloudflare")
    monkeypatch.setenv("CF_ACCOUNT_ID", "acc1")
    monkeypatch.setenv("CF_API_TOKEN", "cf-test")
    monkeypatch.delenv("IMAGE_MODEL", raising=False)
    seen = {}

    class J(Resp):
        headers = {"content-type": "application/json"}

    def post(url, **kw):
        seen.update(url=url, **kw)
        return J({"result": {"image": base64.b64encode(PNG).decode()}, "success": True})
    monkeypatch.setattr(T.requests, "post", post)
    (tmp_path / "ref.png").write_bytes(PNG)
    out = T.image_generate(tmp_path, {"prompt": "K1", "refs": ["ref.png"], "format": "quer"})
    assert "with 1 reference image" in out
    assert seen["url"] == "https://api.cloudflare.com/client/v4/accounts/acc1/ai/run/@cf/black-forest-labs/flux-2-klein-4b"
    assert seen["files"]["prompt"] == (None, "K1") and "input_image_0" in seen["files"]
    assert seen["files"]["width"] == (None, "1024")
    monkeypatch.setenv("IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell")
    with pytest.raises(T.ToolError, match="cannot take reference images"):
        T.image_generate(tmp_path, {"prompt": "K1", "refs": ["ref.png"]})
    monkeypatch.delenv("CF_ACCOUNT_ID")
    with pytest.raises(T.ToolError, match="CF_ACCOUNT_ID"):
        T.image_generate(tmp_path, {"prompt": "K1"})


def test_hf_bild_und_fehler(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "hf")
    monkeypatch.setenv("HF_TOKEN", "hf_test")
    monkeypatch.delenv("IMAGE_MODEL", raising=False)
    monkeypatch.delenv("HF_IMAGE_PROVIDER", raising=False)
    seen = {}
    monkeypatch.setattr(T.requests, "post", lambda url, **kw: seen.update(url=url, **kw) or Img())
    T.image_generate(tmp_path, {"prompt": "x"})
    assert seen["url"] == "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
    assert seen["json"]["inputs"] == "x"
    monkeypatch.setattr(T.requests, "post", lambda url, **kw: Resp({"error": "credits exceeded"}, 402))
    with pytest.raises(T.ToolError, match="HTTP 402 \\(Guthaben aufgebraucht\\)"):
        T.image_generate(tmp_path, {"prompt": "x"})
