"""video_generate, video_ai, sound_generate und Cloud-Stimmen gegen simulierte Anbieter-APIs (kein echter Key, kein Internet)."""
import base64
import json

import pytest

import agent_tools as T
import video_providers as VP

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64


class Resp:
    def __init__(self, body=None, status=200, content=None, headers=None):
        self.status_code, self._body = status, body
        self.text = json.dumps(body) if body is not None else ""
        self.content = content if content is not None else b""
        self.headers = headers or {}

    def json(self):
        if self._body is None:
            raise ValueError
        return self._body

    def iter_content(self, n):
        yield self.content

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Fake:
    """Antworten je (Methode, URL-Teil); Listen werden der Reihe nach abgegeben, der letzte Eintrag bleibt."""

    def __init__(self, monkeypatch, routes):
        self.routes, self.calls = routes, []
        for m in ("post", "get", "put"):
            monkeypatch.setattr(T.requests, m, self._handler(m.upper()))
        monkeypatch.setattr(VP.time, "sleep", lambda s: None)
        monkeypatch.setattr(T, "check_public", lambda host: None)

    def _handler(self, method):
        def h(url, **kw):
            self.calls.append((method, url, kw))
            for (m, part), resp in self.routes.items():
                if m == method and part in url:
                    if isinstance(resp, list):
                        return resp.pop(0) if len(resp) > 1 else resp[0]
                    return resp
            raise AssertionError(f"unerwarteter Aufruf {method} {url}")
        return h

    def find(self, method, part):
        return [c for c in self.calls if c[0] == method and part in c[1]]


@pytest.fixture
def proj(tmp_path, monkeypatch):
    for k in list(T.os.environ):
        if k.startswith(("VIDEO_", "KLING_", "AUDIO_", "FAL_", "TTS_")) or k.endswith("_VIDEO_MODEL") or k.endswith("_I2V_MODEL"):
            monkeypatch.delenv(k, raising=False)
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets/figur.png").write_bytes(PNG)
    return tmp_path


def use(monkeypatch, prov, **env):
    monkeypatch.setenv("VIDEO_PROVIDER", prov)
    for k, v in env.items():
        monkeypatch.setenv(k, v)


def test_aus_ohne_video_provider(proj):
    assert not T.video_enabled()
    assert "video_generate" not in T.available({"media": True})
    out, made = T.run_tool({"tool": "video_generate", "prompt": "x"}, proj, {"media": True})
    assert out.startswith("ERROR") and made is None


def test_mehrere_anbieter_und_auswahl(proj, monkeypatch):
    use(monkeypatch, "kling, runway,unbekannt", KLING_ACCESS_KEY="ak", KLING_SECRET_KEY="sk", RUNWAYML_API_SECRET="rw")
    assert VP.providers() == ["kling", "runway"]
    assert "video_generate" in T.available({"media": True})
    with pytest.raises(T.ToolError, match="not switched on"):
        VP.generate(proj, {"prompt": "x", "provider": "luma"})
    with pytest.raises(T.ToolError, match="continue_id"):
        VP.generate(proj, {"prompt": "x", "continue_id": "abc"})


def test_fehlender_key(proj, monkeypatch):
    use(monkeypatch, "minimax")
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    with pytest.raises(T.ToolError, match="MINIMAX_API_KEY is missing"):
        VP.generate(proj, {"prompt": "x"})


def test_modellwahl(monkeypatch):
    use(monkeypatch, "wan,fal", VIDEO_MODEL="wan2.5-t2v-preview")
    assert VP.model_of("wan", False, "wan") == "wan2.5-t2v-preview"
    assert VP.model_of("wan", True, "wan") == "wan2.2-i2v-plus"  # mit Startbild immer das Bild-zu-Video-Modell
    monkeypatch.setenv("WAN_I2V_MODEL", "wan2.5-i2v-preview")
    assert VP.model_of("wan", True, "wan") == "wan2.5-i2v-preview"
    assert VP.model_of("fal", True, "wan") == "fal-ai/wan/v2.2-a14b/image-to-video"  # VIDEO_MODEL gilt nur fuer den ersten
    monkeypatch.setenv("FAL_VIDEO_MODEL", "fal-ai/kling-video/v2.1/standard/text-to-video")
    assert VP.model_of("fal", False, "wan") == "fal-ai/kling-video/v2.1/standard/text-to-video"


def test_kling_jwt():
    tok = VP.kling_token("ak", "sk", now=1000)
    head, payload, sig = tok.split(".")
    pad = lambda s: s + "=" * (-len(s) % 4)  # noqa: E731
    assert json.loads(base64.urlsafe_b64decode(pad(payload))) == {"iss": "ak", "exp": 2800, "nbf": 995}
    assert json.loads(base64.urlsafe_b64decode(pad(head)))["alg"] == "HS256"


def test_kling_bild_zu_video(proj, monkeypatch):
    use(monkeypatch, "kling", KLING_ACCESS_KEY="ak", KLING_SECRET_KEY="sk")
    f = Fake(monkeypatch, {
        ("POST", "/v1/videos/image2video"): Resp({"code": 0, "data": {"task_id": "t1"}}),
        ("GET", "/v1/videos/image2video/t1"): [Resp({"code": 0, "data": {"task_status": "processing"}}),
                                                Resp({"code": 0, "data": {"task_status": "succeed",
                                                                          "task_result": {"videos": [{"url": "https://cdn.kling/x.mp4"}]}}})],
        ("GET", "cdn.kling"): Resp(content=MP4),
    })
    out = VP.generate(proj, {"prompt": "Figur winkt", "image": "assets/figur.png", "seconds": 10, "name": "Gruss"})
    assert "output/gruss.mp4" in out and (proj / "output/gruss.mp4").read_bytes() == MP4
    body = f.find("POST", "image2video")[0][2]["json"]
    assert body["image"] == base64.b64encode(PNG).decode() and body["duration"] == "10" and body["model_name"] == "kling-v2-5-turbo"
    assert f.find("POST", "image2video")[0][2]["headers"]["Authorization"].startswith("Bearer ey")
    assert f.find("GET", "cdn.kling")[0][2]["headers"] == {}  # Zugangsdaten nie an fremde Download-Hosts


def test_kling_fehler(proj, monkeypatch):
    use(monkeypatch, "kling", KLING_ACCESS_KEY="ak", KLING_SECRET_KEY="sk")
    Fake(monkeypatch, {
        ("POST", "/v1/videos/text2video"): Resp({"code": 0, "data": {"task_id": "t1"}}),
        ("GET", "/v1/videos/text2video/t1"): Resp({"code": 0, "data": {"task_status": "failed", "task_status_msg": "Risiko"}}),
    })
    with pytest.raises(T.ToolError, match="Risiko"):
        VP.generate(proj, {"prompt": "x"})


def test_minimax(proj, monkeypatch):
    use(monkeypatch, "minimax", MINIMAX_API_KEY="mm")
    f = Fake(monkeypatch, {
        ("POST", "/v1/video_generation"): Resp({"task_id": "9", "base_resp": {"status_code": 0, "status_msg": "success"}}),
        ("GET", "/v1/query/video_generation"): [Resp({"status": "Processing"}), Resp({"status": "Success", "file_id": "f7"})],
        ("GET", "/v1/files/retrieve"): Resp({"file": {"download_url": "https://files.minimax/v.mp4"}}),
        ("GET", "files.minimax"): Resp(content=MP4),
    })
    out = VP.generate(proj, {"prompt": "Meer", "image": "assets/figur.png", "seconds": 6})
    assert "minimax (MiniMax-Hailuo-2.3)" in out
    body = f.find("POST", "video_generation")[0][2]["json"]
    assert body["first_frame_image"].startswith("data:image/png;base64,") and body["duration"] == 6
    assert f.find("GET", "files/retrieve")[0][2]["params"] == {"file_id": "f7"}


def test_minimax_kontofehler(proj, monkeypatch):
    use(monkeypatch, "minimax", MINIMAX_API_KEY="mm")
    Fake(monkeypatch, {("POST", "/v1/video_generation"): Resp({"base_resp": {"status_code": 1008, "status_msg": "insufficient balance"}})})
    with pytest.raises(T.ToolError, match="insufficient balance"):
        VP.generate(proj, {"prompt": "x"})


def test_wan_text_hochkant(proj, monkeypatch):
    use(monkeypatch, "wan", DASHSCOPE_API_KEY="ds")
    f = Fake(monkeypatch, {
        ("POST", "video-synthesis"): Resp({"output": {"task_id": "w1", "task_status": "PENDING"}}),
        ("GET", "/api/v1/tasks/w1"): Resp({"output": {"task_status": "SUCCEEDED", "video_url": "https://oss.ali/w.mp4"}}),
        ("GET", "oss.ali"): Resp(content=MP4),
    })
    VP.generate(proj, {"prompt": "Stadt bei Nacht", "aspect": "9:16"})
    c = f.find("POST", "video-synthesis")[0][2]
    assert c["headers"]["X-DashScope-Async"] == "enable"
    assert c["json"]["model"] == "wan2.2-t2v-plus" and c["json"]["parameters"]["size"] == "1080*1920"


def test_wan_bild_nimmt_i2v_modell(proj, monkeypatch):
    use(monkeypatch, "wan", DASHSCOPE_API_KEY="ds")
    f = Fake(monkeypatch, {
        ("POST", "video-synthesis"): Resp({"output": {"task_id": "w1", "task_status": "PENDING"}}),
        ("GET", "/api/v1/tasks/w1"): Resp({"output": {"task_status": "FAILED", "message": "DataInspectionFailed"}}),
    })
    with pytest.raises(T.ToolError, match="DataInspectionFailed"):
        VP.generate(proj, {"prompt": "x", "image": "assets/figur.png"})
    j = f.find("POST", "video-synthesis")[0][2]["json"]
    assert j["model"] == "wan2.2-i2v-plus" and j["input"]["img_url"].startswith("data:image/png")


def test_higgsfield_mit_upload(proj, monkeypatch):
    use(monkeypatch, "higgsfield", HIGGSFIELD_API_KEY_ID="id", HIGGSFIELD_API_KEY_SECRET="geheim")
    f = Fake(monkeypatch, {
        ("POST", "/files/generate-upload-url"): Resp({"upload_url": "https://s3.hf/up?sig=1", "public_url": "https://cdn.hf/in.png",
                                                      "upload_headers": {"Content-Type": "image/png", "x-amz-tagging": "a=b"}}),
        ("PUT", "s3.hf"): Resp({}),
        ("POST", "/minimax/h3/image-to-video"): Resp({"status": "queued", "request_id": "r1",
                                                       "status_url": "https://api.higgsfield.ai/requests/r1/status"}),
        ("GET", "/requests/r1/status"): [Resp({"status": "in_progress"}), Resp({"status": "completed", "video": {"url": "https://cdn.hf/o.mp4"}})],
        ("GET", "cdn.hf/o.mp4"): Resp(content=MP4),
    })
    VP.generate(proj, {"prompt": "Figur rennt", "image": "assets/figur.png", "seconds": 8, "aspect": "16:9"})
    sub = f.find("POST", "image-to-video")[0][2]
    assert sub["headers"]["Authorization"] == "Key id:geheim" and sub["headers"]["Idempotency-Key"]
    assert sub["json"] == {"prompt": "Figur rennt", "duration": 8, "aspect_ratio": "16:9", "image_url": "https://cdn.hf/in.png"}
    put = f.find("PUT", "s3.hf")[0][2]
    assert "Authorization" not in put["headers"] and put["data"] == PNG


def test_higgsfield_nsfw(proj, monkeypatch):
    use(monkeypatch, "higgsfield", HIGGSFIELD_API_KEY="id:geheim")
    Fake(monkeypatch, {
        ("POST", "/minimax/h3/text-to-video"): Resp({"status": "queued", "request_id": "r1"}),
        ("GET", "/requests/r1/status"): Resp({"status": "nsfw"}),
    })
    with pytest.raises(T.ToolError, match="content check"):
        VP.generate(proj, {"prompt": "x"})


def test_higgsfield_ohne_secret(proj, monkeypatch):
    use(monkeypatch, "higgsfield", HIGGSFIELD_API_KEY="nur-id")
    with pytest.raises(T.ToolError, match="HIGGSFIELD_API_KEY_SECRET"):
        VP.generate(proj, {"prompt": "x"})


def test_openai_sora_mit_startbild(proj, monkeypatch):
    use(monkeypatch, "openai", OPENAI_API_KEY="sk")
    from PIL import Image
    Image.new("RGB", (300, 300), "red").save(proj / "assets/rot.png")
    f = Fake(monkeypatch, {
        ("POST", "/v1/videos"): Resp({"id": "video_1", "status": "queued"}),
        ("GET", "/v1/videos/video_1/content"): Resp(content=MP4),
        ("GET", "/v1/videos/video_1"): [Resp({"id": "video_1", "status": "in_progress"}), Resp({"id": "video_1", "status": "completed"})],
    })
    out = VP.generate(proj, {"prompt": "x", "image": "assets/rot.png", "aspect": "9:16", "seconds": 7})
    assert "continue_id: video_1" in out
    c = f.find("POST", "/v1/videos")[0][2]
    assert c["data"]["size"] == "720x1280" and c["data"]["seconds"] == "8"
    ref = Image.open(T.io.BytesIO(c["files"]["input_reference"][1]))
    assert ref.size == (720, 1280)  # Startbild auf Videogroesse gebracht
    assert f.find("GET", "/content")[0][2]["headers"]["Authorization"] == "Bearer sk"


def test_openrouter(proj, monkeypatch):
    use(monkeypatch, "openrouter", OPENROUTER_API_KEY="or", OPENROUTER_VIDEO_MODEL="minimax/hailuo-3")
    f = Fake(monkeypatch, {
        ("POST", "/api/v1/videos"): Resp({"id": "j1", "status": "pending", "polling_url": "https://openrouter.ai/api/v1/videos/j1"}),
        ("GET", "/content"): Resp(content=MP4),
        ("GET", "/api/v1/videos/j1"): Resp({"id": "j1", "status": "completed", "unsigned_urls": ["https://openrouter.ai/api/v1/videos/j1/content?index=0"]}),
    })
    VP.generate(proj, {"prompt": "x", "image": "assets/figur.png", "seconds": 6, "resolution": "1080p"})
    body = f.find("POST", "/api/v1/videos")[0][2]["json"]
    assert body["model"] == "minimax/hailuo-3" and body["duration"] == 6 and body["frame_images"][0]["frame_type"] == "first_frame"


def test_runway_luma_seedance(proj, monkeypatch):
    use(monkeypatch, "runway,luma,seedance", RUNWAYML_API_SECRET="rw", LUMAAI_API_KEY="lu", ARK_API_KEY="ark")
    f = Fake(monkeypatch, {
        ("POST", "/v1/image_to_video"): Resp({"id": "r1"}),
        ("GET", "/v1/tasks/r1"): Resp({"status": "SUCCEEDED", "output": ["https://dnznrvs05pmza.cloudfront.net/r.mp4"]}),
        ("POST", "/generations/tasks"): Resp({"id": "s1"}),
        ("GET", "/generations/tasks/s1"): Resp({"status": "succeeded", "content": {"video_url": "https://tos.byte/s.mp4"}}),
        ("POST", "/dream-machine/v1/generations"): Resp({"id": "l1", "state": "queued"}),
        ("GET", "/dream-machine/v1/generations/l1"): Resp({"state": "completed", "assets": {"video": "https://storage.luma/l.mp4"}}),
        ("GET", ".mp4"): Resp(content=MP4),
    })
    VP.generate(proj, {"prompt": "x", "image": "assets/figur.png"})
    assert f.find("POST", "image_to_video")[0][2]["json"]["promptImage"].startswith("data:image/png")
    assert f.find("POST", "image_to_video")[0][2]["headers"]["X-Runway-Version"] == "2024-11-06"
    VP.generate(proj, {"prompt": "Wald", "provider": "seedance", "aspect": "9:16", "seconds": 5})
    assert f.find("POST", "/generations/tasks")[0][2]["json"]["content"][0]["text"] == "Wald --ratio 9:16 --duration 5"
    with pytest.raises(T.ToolError, match="https address"):
        VP.generate(proj, {"prompt": "x", "provider": "luma", "image": "assets/figur.png"})
    VP.generate(proj, {"prompt": "x", "provider": "luma", "image": "https://example.com/a.png"})
    assert f.find("POST", "dream-machine")[-1][2]["json"]["keyframes"]["frame0"]["url"] == "https://example.com/a.png"
    assert len(list((proj / "output").glob("*.mp4"))) == 3


def test_fal_und_replicate(proj, monkeypatch):
    use(monkeypatch, "fal,replicate", FAL_KEY="fk", REPLICATE_API_TOKEN="rp", FAL_VIDEO_PARAMS='{"num_frames": 81}')
    f = Fake(monkeypatch, {
        ("POST", "queue.fal.run"): Resp({"request_id": "q1", "status": "IN_QUEUE", "status_url": "https://queue.fal.run/x/requests/q1/status",
                                         "response_url": "https://queue.fal.run/x/requests/q1"}),
        ("GET", "/requests/q1/status"): Resp({"status": "COMPLETED"}),
        ("GET", "/requests/q1"): Resp({"video": {"url": "https://v3.fal.media/f.mp4"}}),
        ("POST", "api.replicate.com/v1/models/"): Resp({"id": "p1", "status": "starting", "urls": {"get": "https://api.replicate.com/v1/predictions/p1"}}),
        ("GET", "/v1/predictions/p1"): Resp({"status": "succeeded", "output": "https://replicate.delivery/p.mp4"}),
        ("GET", ".mp4"): Resp(content=MP4),
    })
    VP.generate(proj, {"prompt": "x", "image": "assets/figur.png"})
    sub = f.find("POST", "queue.fal.run")[0]
    assert sub[1].endswith("fal-ai/wan/v2.2-a14b/image-to-video") and sub[2]["headers"]["Authorization"] == "Key fk"
    assert sub[2]["json"]["num_frames"] == 81 and sub[2]["json"]["image_url"].startswith("data:")
    VP.generate(proj, {"prompt": "x", "provider": "replicate"})
    assert "wan-video/wan-2.2-t2v-fast" in f.find("POST", "replicate")[0][1]


def test_download_nur_https(proj, monkeypatch):
    use(monkeypatch, "runway", RUNWAYML_API_SECRET="rw")
    Fake(monkeypatch, {
        ("POST", "/v1/text_to_video"): Resp({"id": "r1"}),
        ("GET", "/v1/tasks/r1"): Resp({"status": "SUCCEEDED", "output": ["http://intern/x.mp4"]}),
    })
    with pytest.raises(T.ToolError):
        VP.generate(proj, {"prompt": "x"})


def test_video_ai(proj, monkeypatch):
    (proj / "output").mkdir()
    (proj / "output/szene.mp4").write_bytes(MP4)
    (proj / "output/stimme.mp3").write_bytes(b"ID3" + b"\x00" * 20)
    assert "video_ai" not in T.available({"media": True})
    monkeypatch.setenv("VIDEO_AI", "fal")
    monkeypatch.setenv("FAL_KEY", "fk")
    assert "video_ai" in T.available({"media": True})
    f = Fake(monkeypatch, {
        ("POST", "queue.fal.run"): Resp({"request_id": "q1", "status": "COMPLETED"}),
        ("GET", "/requests/q1"): Resp({"video": {"url": "https://v3.fal.media/l.mp4"}}),
        ("GET", "v3.fal.media"): Resp(content=MP4),
    })
    out, made = T.run_tool({"tool": "video_ai", "op": "lipsync", "input": "output/szene.mp4", "audio": "output/stimme.mp3"}, proj, {"media": True})
    assert made == "output/lipsync.mp4", out
    body = f.find("POST", "sync-lipsync")[0][2]["json"]
    assert body["video_url"].startswith("data:video/mp4") and body["audio_url"].startswith("data:audio/mpeg")
    out, _ = T.run_tool({"tool": "video_ai", "op": "upscale", "input": "output/stimme.mp3"}, proj, {"media": True})
    assert "suitable format" in out


def test_sound_generate_elevenlabs(proj, monkeypatch):
    monkeypatch.setenv("AUDIO_PROVIDER", "elevenlabs")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "xi")
    f = Fake(monkeypatch, {("POST", "/v1/music"): Resp(content=b"ID3music"), ("POST", "/v1/sound-generation"): Resp(content=b"ID3sfx")})
    out, made = T.run_tool({"tool": "sound_generate", "prompt": "Regen", "seconds": 99, "name": "regen"}, proj, {"media": True})
    assert made == "output/audio/regen.mp3" and f.find("POST", "sound-generation")[0][2]["json"]["duration_seconds"] == 30
    T.run_tool({"tool": "sound_generate", "prompt": "Klavier", "kind": "music", "seconds": 20}, proj, {"media": True})
    assert f.find("POST", "/v1/music")[0][2]["json"]["music_length_ms"] == 20000
    assert (proj / "output/audio/music.mp3").read_bytes() == b"ID3music"


def test_speak_cloud_stimmen(proj, monkeypatch):
    monkeypatch.setenv("TTS_ENGINE", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk")
    monkeypatch.setattr(T, "_probe", lambda p: {"duration": 1.5})
    f = Fake(monkeypatch, {("POST", "/audio/speech"): Resp(content=b"ID3")})
    out = T.speak(proj, "Hallo", voice="nova", rate=1.2)
    assert "output/audio/sprecher.mp3" in out
    assert f.find("POST", "speech")[0][2]["json"]["voice"] == "nova"
    monkeypatch.setenv("TTS_ENGINE", "elevenlabs")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "xi")
    f.routes[("POST", "/text-to-speech/")] = Resp(content=b"ID3")
    T.speak(proj, "Hallo", voice="21m00Tcm4TlvDq8ikWAM")
    assert f.find("POST", "text-to-speech/21m00Tcm4TlvDq8ikWAM")


def test_gemini_omni_wie_bisher(proj, monkeypatch):
    use(monkeypatch, "gemini", GEMINI_API_KEY="g1,g2")
    f = Fake(monkeypatch, {("POST", "/v1beta/interactions"): Resp({"id": "i1", "status": "completed", "steps": [
        {"type": "model_output", "content": [{"type": "video", "data": base64.b64encode(MP4).decode()}]}]})})
    out = T.video_generate(proj, {"prompt": "x", "aspect": "9:16", "name": "omni"})
    assert "output/omni.mp4" in out and "continue_id: i1" in out and (proj / "output/omni.mp4").read_bytes() == MP4
    assert f.calls[0][2]["headers"]["x-goog-api-key"] == "g1"
