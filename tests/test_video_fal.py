"""Videoerzeugung über fal.ai: Warteschlange, Schlüssel, Download ohne Schlüssel."""
import pytest
import agent_tools as T
import video_providers as VP


class R:
    def __init__(self, body, status=200):
        self.status_code, self._b, self.text = status, body, str(body)

    def json(self):
        return self._b


def test_fal_braucht_schluessel(monkeypatch, tmp_path):
    monkeypatch.setenv("VIDEO_PROVIDER", "fal")
    monkeypatch.delenv("FAL_KEY", raising=False)
    with pytest.raises(T.ToolError, match="FAL_KEY"):
        T.video_generate(tmp_path, {"prompt": "eine Katze"})


def test_fal_standardmodell_ist_der_guenstigste(monkeypatch):
    monkeypatch.delenv("VIDEO_MODEL", raising=False)
    assert VP.VIDEO["fal"][1] == "minimax/h3-max/text-to-video"
    monkeypatch.setenv("VIDEO_PROVIDER", "fal")
    monkeypatch.setenv("VIDEO_MODEL", "veo-3.1-fast-generate-001")  # Gemini-Name von frueher: gilt bei fal nicht
    assert VP.model_of("fal", False, "fal") == "minimax/h3-max/text-to-video"


def test_fal_ablauf_und_download_ohne_schluessel(monkeypatch, tmp_path):
    monkeypatch.setenv("VIDEO_PROVIDER", "fal")
    monkeypatch.setenv("FAL_KEY", "geheim")
    monkeypatch.setenv("VIDEO_MODEL", "fal-ai/kling-video/v2.5-turbo/pro/text-to-video")
    monkeypatch.setattr(T.time, "sleep", lambda s: None)
    monkeypatch.delenv("FAL_VIDEO_MODEL", raising=False)
    posted, gets, dl = [], [], {}

    def fake_post(url, headers=None, json=None, timeout=None):
        posted.append((url, headers, json))
        return R({"status_url": "https://queue.fal.run/fal-ai/kling-video/requests/1/status",
                  "response_url": "https://queue.fal.run/fal-ai/kling-video/requests/1"})

    states = iter([{"status": "IN_QUEUE"}, {"status": "COMPLETED"}])

    def fake_get(url, headers=None, timeout=None, **kw):
        gets.append((url, headers))
        if url.endswith("/status"):
            return R(next(states))
        return R({"video": {"url": "https://cdn.example/clip.mp4"}})

    def fake_download(url, dst, headers=None, limit=None):
        dl.update(url=url, key=headers)
        dst.write_bytes(b"\x00\x00\x00\x18ftypmp42")

    monkeypatch.setattr(T.requests, "post", fake_post)
    monkeypatch.setattr(T.requests, "get", fake_get)
    monkeypatch.setattr(VP, "save_url", fake_download)
    out = T.video_generate(tmp_path, {"prompt": "eine Katze", "aspect": "9:16"})

    url, headers, body = posted[0]
    assert url == "https://queue.fal.run/fal-ai/kling-video/v2.5-turbo/pro/text-to-video"
    assert headers == {"Authorization": "Key geheim"}
    assert body == {"prompt": "eine Katze", "aspect_ratio": "9:16"}
    assert all(h == {"Authorization": "Key geheim"} for _, h in gets)
    # Der fal-Schlüssel darf nicht an den Download-Server gehen
    assert dl == {"url": "https://cdn.example/clip.mp4", "key": None}
    assert "Video created" in out


def test_fal_bild_zu_video_nimmt_i2v_endpunkt(monkeypatch, tmp_path):
    monkeypatch.setenv("VIDEO_PROVIDER", "fal")
    monkeypatch.setenv("FAL_KEY", "geheim")
    monkeypatch.delenv("FAL_I2V_MODEL", raising=False)
    assert VP.model_of("fal", True, "fal") == "fal-ai/wan/v2.2-a14b/image-to-video"
