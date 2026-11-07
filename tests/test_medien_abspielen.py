"""Video und Ton aus dem Projektordner im Browser abspielen und einzeln herunterladen (Dateiansicht ▶ / ⬇)."""
import app as A
from conftest import make_project


def _put(pid, rel, data=b"\x00\x00\x00\x18ftypmp42"):
    f = A.proj_dir(pid) / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(data)


def test_video_und_ton_ohne_sandbox(client):
    pid = make_project()
    _put(pid, "output/folge1.mp4")
    _put(pid, "film/clips/s1.wav", b"RIFF0000WAVE")
    tok = A.file_token(pid)
    for rel, typ in (("output/folge1.mp4", "video/mp4"), ("film/clips/s1.wav", "audio/wav")):
        r = client.get(f"/files/{pid}/{tok}/{rel}")
        assert r.status_code == 200
        assert r.mimetype == typ
        csp = r.headers["Content-Security-Policy"]
        assert "sandbox" not in csp  # Chrome sperrt Medien in der Sandbox (Herkunft null)
        assert "default-src 'none'" in csp and "media-src 'self'" in csp
        assert r.headers["X-Content-Type-Options"] == "nosniff"
        assert "attachment" not in r.headers.get("Content-Disposition", "")


def test_spulen_per_range(client):
    pid = make_project()
    _put(pid, "output/f.mp4", bytes(range(200)))
    r = client.get(f"/files/{pid}/{A.file_token(pid)}/output/f.mp4", headers={"Range": "bytes=10-19"})
    assert r.status_code == 206 and r.data == bytes(range(10, 20))


def test_download_link(client):
    pid = make_project()
    _put(pid, "output/f.mp4")
    r = client.get(f"/files/{pid}/{A.file_token(pid)}/output/f.mp4?download=1")
    assert r.status_code == 200 and "attachment" in r.headers["Content-Disposition"]


def test_html_bleibt_in_sandbox(client):
    pid = make_project()
    _put(pid, "www/index.html", b"<script>alert(1)</script>")
    r = client.get(f"/files/{pid}/{A.file_token(pid)}/www/index.html")
    assert r.headers["Content-Security-Policy"].startswith("sandbox")


def test_falsches_token(client):
    pid = make_project()
    _put(pid, "output/f.mp4")
    assert client.get(f"/files/{pid}/falsch/output/f.mp4").status_code == 404


def test_oberflaeche_hat_abspieler():
    html = (A.BASE / "static" / "index.html").read_text(encoding="utf-8")
    assert "Finished videos" in html and "data-play" in html and "download=1" in html
