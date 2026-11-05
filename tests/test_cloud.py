"""Cloud-Upload (GitHub, Google Drive, OneDrive, Telegram) gegen simulierte APIs, ohne Internet und ohne echte Zugangsdaten."""
import time

import pytest

import cloud_upload as C
from conftest import A, make_agent, make_project, make_task


class Resp:
    def __init__(self, body=None, status=200, headers=None):
        self.status_code, self._body, self.headers = status, body, headers or {}

    def json(self):
        if self._body is None:
            raise ValueError
        return self._body


class Fake:
    """Antworten je (Methode, URL-Teil); Listen werden der Reihe nach abgegeben, der letzte Eintrag bleibt."""

    def __init__(self, monkeypatch, routes):
        self.routes, self.calls = routes, []
        for m in ("post", "get", "put", "delete"):
            monkeypatch.setattr(C.requests, m, self._handler(m.upper()))

    def _handler(self, method):
        def h(url, **kw):
            if "data" in kw and hasattr(kw["data"], "read"):
                kw = {**kw, "data": kw["data"].read()}
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
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("PCL_TOKENS_DIR", str(tmp_path / "tokens"))
    for k in ("GITHUB_UPLOAD_TOKEN", "GITHUB_UPLOAD_REPO", "GITHUB_UPLOAD_BRANCH", "GDRIVE_CLIENT_ID", "GDRIVE_CLIENT_SECRET",
              "GDRIVE_FOLDER_ID", "ONEDRIVE_CLIENT_ID", "ONEDRIVE_TENANT"):
        monkeypatch.delenv(k, raising=False)
    return monkeypatch


def test_clean_folder():
    assert C.clean_folder("../a/./b\\c:/ ..") == "a/b/c"
    assert C.join_folder("Hyperstead/Film", "/Szene 1/") == "Hyperstead/Film/Szene 1"
    assert C.join_folder("", "") == ""


def test_status_without_keys(env):
    assert C.status("github")[0] is False
    assert C.status("gdrive") == (False, False, "GDRIVE_CLIENT_ID and GDRIVE_CLIENT_SECRET missing in .env")
    with pytest.raises(C.CloudError, match="not set up"):
        C.upload("onedrive", __file__)


def test_github_small_file_overwrites_with_sha(env, tmp_path):
    env.setenv("GITHUB_UPLOAD_TOKEN", "ghp_x")
    env.setenv("GITHUB_UPLOAD_REPO", "abi/ablage")
    f = tmp_path / "bericht.pdf"
    f.write_bytes(b"%PDF-1.4 test")
    fake = Fake(env, {("GET", "/contents/"): Resp({"sha": "abc"}),
                      ("PUT", "/contents/"): Resp({"content": {"html_url": "https://github.com/abi/ablage/blob/main/f/bericht.pdf"}})})
    link = C.upload("github", f, "f")
    assert link.endswith("/f/bericht.pdf")
    url, kw = fake.find("PUT", "/contents/")[0][1:]
    assert url.endswith("/repos/abi/ablage/contents/f/bericht.pdf")
    assert kw["json"]["sha"] == "abc" and kw["headers"]["Authorization"] == "Bearer ghp_x"


def test_github_big_file_goes_to_release(env, tmp_path):
    env.setenv("GITHUB_UPLOAD_TOKEN", "ghp_x")
    env.setenv("GITHUB_UPLOAD_REPO", "abi/ablage")
    env.setattr(C, "GITHUB_CONTENTS_MAX", 10)
    f = tmp_path / "film.mp4"
    f.write_bytes(b"x" * 100)
    fake = Fake(env, {("GET", "/releases/tags/"): Resp(status=404),
                      ("POST", "api.github.com/repos/abi/ablage/releases"): Resp({"id": 7, "assets": []}),
                      ("POST", "uploads.github.com"): Resp({"browser_download_url": "https://github.com/dl/film.mp4"})})
    assert C.upload("github", f) == "https://github.com/dl/film.mp4"
    up = fake.find("POST", "uploads.github.com")[0]
    assert "/releases/7/assets" in up[1] and up[2]["params"] == {"name": "film.mp4"} and up[2]["data"] == b"x" * 100


def test_gdrive_login_and_chunked_upload(env, tmp_path):
    env.setenv("GDRIVE_CLIENT_ID", "cid")
    env.setenv("GDRIVE_CLIENT_SECRET", "sec")
    env.setattr(C, "DRIVE_CHUNK", 4)
    fake = Fake(env, {
        ("POST", "/device/code"): Resp({"user_code": "ABCD-EFGH", "verification_url": "https://www.google.com/device",
                                        "device_code": "dc", "interval": 5, "expires_in": 900}),
        ("POST", "oauth2.googleapis.com/token"): [Resp({"error": "authorization_pending"}, 428),
                                                  Resp({"access_token": "at", "refresh_token": "rt", "expires_in": 3600})],
        ("POST", "/upload/drive/v3/files"): Resp({}, headers={"Location": "https://upload.example/session"}),  # vor /drive/v3/files
        ("GET", "/drive/v3/files"): [Resp({"files": [{"id": "F1"}]}), Resp({"files": []})],
        ("POST", "/drive/v3/files"): Resp({"id": "F2"}),
        ("PUT", "upload.example/session"): [Resp(status=308), Resp(status=308), Resp({"id": "X", "webViewLink": "https://drive/x"})],
    })
    dc = C.device_start("gdrive")
    assert dc["user_code"] == "ABCD-EFGH" and dc["url"].endswith("/device")
    assert C.device_poll("gdrive", dc) == "pending"
    assert C.device_poll("gdrive", dc) == "ok"
    assert C.load_token("gdrive")["refresh_token"] == "rt" and C.ready("gdrive")
    f = tmp_path / "a.txt"
    f.write_bytes(b"0123456789")  # 3 Teile zu 4 Byte
    assert C.upload("gdrive", f, "Hyperstead/Neu") == "https://drive/x"
    assert fake.find("POST", "googleapis.com/drive/v3/files")[0][2]["json"]["parents"] == ["F1"]  # erster Ordner gefunden, zweiter angelegt
    meta = fake.find("POST", "/upload/drive/v3/files")[0][2]["json"]
    assert meta == {"name": "a.txt", "parents": ["F2"]}
    ranges = [c[2]["headers"]["Content-Range"] for c in fake.find("PUT", "upload.example")]
    assert ranges == ["bytes 0-3/10", "bytes 4-7/10", "bytes 8-9/10"]


def test_onedrive_refresh_rotates_token_and_uploads(env, tmp_path):
    env.setenv("ONEDRIVE_CLIENT_ID", "cid")
    C.save_token("onedrive", {"refresh_token": "alt", "access_token": "", "expires": 0})
    env.setattr(C, "ONEDRIVE_SIMPLE_MAX", 2)
    env.setattr(C, "ONEDRIVE_CHUNK", 5)
    fake = Fake(env, {
        ("POST", "/consumers/oauth2/v2.0/token"): Resp({"access_token": "at", "refresh_token": "neu", "expires_in": 3600}),
        ("POST", "/createUploadSession"): Resp({"uploadUrl": "https://up.example/s"}),
        ("PUT", "up.example/s"): [Resp({}, 202), Resp({"webUrl": "https://onedrive/x"}, 201)],
    })
    f = tmp_path / "film.mp4"
    f.write_bytes(b"0123456789")
    assert C.upload("onedrive", f, "Videos/Neu") == "https://onedrive/x"
    assert C.load_token("onedrive")["refresh_token"] == "neu"
    assert "/root:/Videos/Neu/film.mp4:/createUploadSession" in fake.find("POST", "createUploadSession")[0][1]
    assert all("Authorization" not in c[2]["headers"] for c in fake.find("PUT", "up.example"))


def test_onedrive_expired_login_message(env, tmp_path):
    env.setenv("ONEDRIVE_CLIENT_ID", "cid")
    C.save_token("onedrive", {"refresh_token": "alt", "expires": 0})
    Fake(env, {("POST", "/token"): Resp({"error": "invalid_grant"}, 400)})
    f = tmp_path / "a.txt"
    f.write_text("x")
    with pytest.raises(C.CloudError, match="sign in again"):
        C.upload("onedrive", f)


# ------------------------------------------------------------------ App: Werkzeug, Freigabe, Web, Telegram
def _wait_job(client, jid):
    for _ in range(100):
        j = client.get(f"/api/cloud/jobs/{jid}").get_json()
        if j["state"] != "running":
            return j
        time.sleep(0.02)
    raise AssertionError("Upload haengt")


def test_agent_upload_needs_approval_then_link_in_task(env, client, monkeypatch):
    env.setenv("GITHUB_UPLOAD_TOKEN", "ghp_x")
    env.setenv("GITHUB_UPLOAD_REPO", "abi/ablage")
    pid = make_project("Filmfirma")
    aid = make_agent(pid, "Cutter", upload=True)
    tid = make_task(pid, aid, status="running")
    out = A.proj_dir(pid) / "output"
    out.mkdir(parents=True, exist_ok=True)
    (out / "film.mp4").write_bytes(b"film")
    perms = dict(A.DEFAULT_PERMS, upload=True)
    assert "cloud_upload" in A.cloud_doc(pid, perms) and A.cloud_doc(pid, A.DEFAULT_PERMS) == ""
    assert A.request_upload({"to": "github", "path": "../.env"}, pid, aid, tid).startswith("ERROR")
    assert A.request_upload({"to": "gdrive", "path": "output/film.mp4"}, pid, aid, tid).startswith("ERROR: target")
    msg = A.request_upload({"to": "github", "path": "output/film.mp4", "folder": "Szene 1"}, pid, aid, tid)
    assert "approval" in msg
    assert "already waiting" in A.request_upload({"to": "github", "path": "output/film.mp4", "folder": "Szene 1"}, pid, aid, tid)
    ap = A.q1("SELECT * FROM approvals WHERE task_id=?", (tid,))
    assert ap["kind"] == "upload" and "Filmfirma/Szene 1" in ap["payload"]
    A.set_task(tid, "waiting_approval", "Film fertig.")
    seen = {}
    monkeypatch.setattr(A.cloud, "upload", lambda svc, f, folder: seen.update(svc=svc, folder=folder) or "https://github.com/x/film.mp4")
    r = client.post(f"/api/approvals/{ap['id']}", json={"decision": "approve"})
    assert r.status_code == 200
    for _ in range(100):
        t = A.q1("SELECT * FROM tasks WHERE id=?", (tid,))
        if t["status"] == "done":
            break
        time.sleep(0.02)
    assert t["status"] == "done" and "https://github.com/x/film.mp4" in t["result"]
    assert seen == {"svc": "github", "folder": "Filmfirma/Szene 1"}


def test_web_upload_settings_and_job(env, client, monkeypatch):
    env.setenv("GITHUB_UPLOAD_TOKEN", "ghp_x")
    env.setenv("GITHUB_UPLOAD_REPO", "abi/ablage")
    pid = make_project("Buch")
    (A.proj_dir(pid) / "output").mkdir(parents=True, exist_ok=True)
    (A.proj_dir(pid) / "output" / "buch.pdf").write_bytes(b"%PDF")
    r = client.get(f"/api/projects/{pid}/cloud").get_json()
    assert r["services"]["github"]["configured"] and not r["services"]["gdrive"]["configured"]
    assert r["folders"]["gdrive"] == "Hyperstead/Buch"
    client.put(f"/api/projects/{pid}/cloud", json={"folders": {"gdrive": "Meine Ablage/../Buch"}})
    assert A.cloud_folders(pid)["gdrive"] == "Meine Ablage/Buch"
    assert client.post(f"/api/projects/{pid}/cloud/upload", json={"to": "gdrive", "path": "output/buch.pdf"}).status_code == 400
    assert client.post(f"/api/projects/{pid}/cloud/upload", json={"to": "github", "path": ".env"}).status_code == 400
    seen = {}
    monkeypatch.setattr(A.cloud, "upload", lambda svc, f, folder: seen.update(folder=folder) or "https://github.com/x/buch.pdf")
    jid = client.post(f"/api/projects/{pid}/cloud/upload", json={"to": "github", "path": "output/buch.pdf", "folder": "Druck"}).get_json()["job"]
    j = _wait_job(client, jid)
    assert j["state"] == "done" and "https://github.com/x/buch.pdf" in j["message"] and seen["folder"] == "Druck"


def test_telegram_datei_command(env, monkeypatch):
    pid = make_project("Handy")
    d = A.proj_dir(pid)
    (d / "output").mkdir(parents=True, exist_ok=True)
    (d / "output" / "plan.pdf").write_bytes(b"%PDF")
    (d / "output" / "bild.png").write_bytes(b"png")
    (d / "input").mkdir(exist_ok=True)
    (d / "input" / "geheim.pdf").write_bytes(b"x")
    A.set_setting("tg_project", pid)
    sent, msgs = [], []
    monkeypatch.setattr(A, "tg_send_now", lambda chat, text, task_id=None, buttons=None, force_reply=False: msgs.append((text, buttons)))
    monkeypatch.setattr(A, "tg_send_file", lambda chat, path, caption="": sent.append(path.name))
    monkeypatch.setattr(A, "tg", lambda *a, **k: {})
    A.tg_files("42")
    text, buttons = msgs[-1]
    labels = [b[0]["text"] for b in buttons]
    assert len(labels) == 2 and not any("geheim" in x for x in labels)
    A.tg_files("42", "plan")  # ein Treffer -> sofort
    idx = [i for i, (_, p) in enumerate(A._tg_filelist["42"]) if p.endswith("bild.png")][0]
    monkeypatch.setattr(A, "TG_CHATS", {"42"})
    A.tg_callback({"id": "c", "data": f"sf:{idx}", "message": {"chat": {"id": 42}, "message_id": 1}})
    for _ in range(100):
        if len(sent) == 2:
            break
        time.sleep(0.02)
    assert sorted(sent) == ["bild.png", "plan.pdf"]


def test_ceo_chat_knows_cloud_setup(env):
    env.setenv("GITHUB_UPLOAD_TOKEN", "ghp_x")
    env.setenv("GITHUB_UPLOAD_REPO", "abi/ablage")
    pid = make_project("Ablage")
    ceo = make_agent(pid, "CEO")
    kid = make_agent(pid, "Helfer", parent=ceo)
    p = A.q1("SELECT * FROM projects WHERE id=?", (pid,))
    txt = A.chat_system(A.q1("SELECT * FROM agents WHERE id=?", (ceo,)), p)
    assert "CLOUD UPLOAD" in txt and "GitHub: ready" in txt and "GDRIVE_CLIENT_ID" in txt and "NEVER" in txt
    assert "ghp_x" not in txt
    assert "CLOUD UPLOAD" not in A.chat_system(A.q1("SELECT * FROM agents WHERE id=?", (kid,)), p)
