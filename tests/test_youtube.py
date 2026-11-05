"""YouTube-Kanal: Pakete, Terminplan, Studio-CSV, Upload nur nach Freigabe – gegen simulierte APIs, ohne Internet."""
import json
import time
from datetime import date

import pytest

import youtube_channel as Y
from conftest import A, make_agent, make_project, make_task


def spec(**over):
    d = {
        "serie": "WOBBLER 9",
        "sprachen": ["de", "en"],
        "kanaele": {"de": {"name": "Wobbler DE", "hashtags": ["#Shorts", "Zeichentrick"]},
                    "en": {"name": "Wobbler EN", "hashtags": ["#Shorts"], "fuss": "New episodes Tue + Sat."}},
        "rhythmus": {"start": "2030-01-01", "tage": ["di", "sa"]},
        "folgen": [
            {"nr": 1, "datei": {"de": "output/ep01-de.mp4", "en": "output/ep01-en.mp4"},
             "titel": {"de": "Niemals drücken", "en": "Never press"},
             "beschreibung": {"de": "Der rote Knopf.", "en": "The red button."},
             "keywords": {"de": ["Raumschiff", "Comedy Animation"], "en": ["spaceship", "cartoon comedy"]},
             "hashtags": {"de": ["#WOBBLER9"], "en": ["#WOBBLER9"]}},
            {"nr": 2, "datei": {"de": "output/ep02-de.mp4", "en": "output/ep02-en.mp4"},
             "titel": {"de": "Klo-Alarm", "en": "Toilet <Alarm>"},
             "beschreibung": {"de": "x", "en": "y"}, "keywords": {"de": ["a"], "en": ["b"]}},
        ],
    }
    d.update(over)
    return d


def write_spec(root, d):
    (root / "youtube").mkdir(parents=True, exist_ok=True)
    (root / Y.SPEC_FILE).write_text(json.dumps(d), encoding="utf-8")


def test_tags_length_counts_like_youtube():
    assert Y.tags_length(["Foo-Baz"]) == 7 and Y.tags_length(["Foo Baz"]) == 9
    assert Y.tags_length(["a", "b"]) == 3


def test_schedule_two_per_week_and_publish_utc():
    days = Y.schedule_dates({"start": "2030-01-01", "tage": ["di", "sa"]}, 4)
    assert days == [date(2030, 1, 1), date(2030, 1, 5), date(2030, 1, 8), date(2030, 1, 12)]
    local, utc = Y.publish_at(date(2030, 1, 1), "18:00", "Europe/Berlin")
    assert utc.strftime("%Y-%m-%dT%H:%M:%SZ") == "2030-01-01T17:00:00Z"
    with pytest.raises(Y.YTError):
        Y.schedule_dates({"tage": ["xx"]}, 1)


def test_prepare_writes_packages_schedule_review(tmp_path):
    write_spec(tmp_path, spec())
    res = Y.prepare(tmp_path)
    assert res["packages"] == 4
    p = json.loads((tmp_path / "youtube/packages/ep01-de/package.json").read_text(encoding="utf-8"))
    b = p["body"]
    assert b["status"]["privacyStatus"] == "private" and b["status"]["publishAt"] == "2030-01-01T17:00:00Z"
    assert b["status"]["selfDeclaredMadeForKids"] is False and b["snippet"]["defaultLanguage"] == "de"
    assert b["snippet"]["description"].endswith("#Shorts #Zeichentrick #WOBBLER9")
    en = json.loads((tmp_path / "youtube/packages/ep01-en/package.json").read_text(encoding="utf-8"))
    assert "New episodes Tue + Sat." in en["body"]["snippet"]["description"]
    assert en["body"]["status"]["publishAt"] == "2030-01-01T22:00:00Z"  # 17:00 New York
    bad = json.loads((tmp_path / "youtube/packages/ep02-en/package.json").read_text(encoding="utf-8"))
    assert any("< or >" in e for e in bad["errors"])
    csvtext = (tmp_path / "youtube/schedule.csv").read_text(encoding="utf-8-sig")
    assert csvtext.splitlines()[0].startswith("date_local;") and "2030-01-05" in csvtext
    review = (tmp_path / "youtube/REVIEW.md").read_text(encoding="utf-8")
    assert "Nothing has been uploaded" in review and "ep02-en" in review
    assert any("does not exist yet" in w for w in p["warnings"])  # Video fehlt noch: nur Warnung beim Vorbereiten


def test_check_limits_and_rhythm_warning(tmp_path):
    d = spec(rhythmus={"start": "2030-01-01", "tage": ["mo", "di", "mi", "do"]})
    d["folgen"][0]["titel"]["de"] = "x" * 101
    d["folgen"][0]["keywords"]["de"] = ["k" * 300, "l" * 300]
    d["folgen"][0]["hashtags"]["de"] = ["#mit leerzeichen"]
    write_spec(tmp_path, d)
    res = Y.prepare(tmp_path, write=False)
    assert not (tmp_path / "youtube/packages").exists()
    errs = [m for m in res["items"] if m["id"] == "ep01-de"][0]["errors"]
    assert any("101 characters" in e for e in errs) and any("keywords" in e for e in errs) and any("spaces" in e for e in errs)
    assert any("2-3 per week" in t for _, t in res["general"])


def test_template_and_run_ops(tmp_path):
    out, made = Y.run(tmp_path, {"op": "template", "serie": "Test"})
    assert made == Y.SPEC_FILE and (tmp_path / Y.SPEC_FILE).is_file()
    assert "already exists" in Y.run(tmp_path, {"op": "template"})[0]
    assert Y.run(tmp_path, {"op": "nope"})[0].startswith("ERROR")
    assert Y.run(tmp_path, {"op": "analyze", "path": "../x.csv"})[0].startswith("ERROR")


STUDIO_EN = """Content,Video title,Video publish time,Duration,Views,Watch time (hours),Subscribers,Average view duration,Average percentage viewed (%),Impressions,Impressions click-through rate (%)
Total,,,,"1,500",10.5,12,0:00:40,70.1,"20,000",4.5
abc,Never press,"Jan 1, 2030",55,"1,000",8.0,10,0:00:48,88.2,"15,000",5.1
def,Toilet alarm,"Jan 5, 2030",54,500,2.5,2,0:00:21,40.5,"5,000",3.0
"""
STUDIO_DE = """Inhalt;Videotitel;Aufrufe;Wiedergabezeit (Stunden);Abonnenten;Durchschnittliche Wiedergabedauer;Durchschnittlich angesehener Prozentsatz (%)
Gesamt;;1.234;10,5;3;0:00:40;70,1
abc;Niemals drücken;1.234;10,5;3;0:00:40;70,1
"""


def test_analyze_studio_csv_en_and_de(tmp_path):
    (tmp_path / "input").mkdir()
    (tmp_path / "input/en.csv").write_text(STUDIO_EN, encoding="utf-8")
    (tmp_path / "input/de.csv").write_text(STUDIO_DE, encoding="utf-8")
    vids, cols = Y.read_studio_csv(tmp_path / "input/en.csv")
    assert len(vids) == 2 and vids[0]["views"] == 1000 and vids[0]["avg_duration"] == 48 and vids[1]["avg_percent"] == 40.5
    assert "ctr" in cols and "impressions" in cols
    de, _ = Y.read_studio_csv(tmp_path / "input/de.csv")
    assert de[0]["views"] == 1234 and de[0]["watch_hours"] == 10.5 and de[0]["title"] == "Niemals drücken"
    res = Y.analyze(tmp_path, ["input/en.csv", "input/de.csv"])
    assert res["report"].startswith("youtube/reports/analysis-") and (tmp_path / res["report"]).is_file()
    assert "Never press" in res["text"] and "Nothing was fetched from YouTube" in res["text"]
    assert res["summary"][0]["views"] == 1500
    (tmp_path / "input/bad.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(Y.YTError):
        Y.read_studio_csv(tmp_path / "input/bad.csv")


class Resp:
    def __init__(self, body=None, status=200, headers=None):
        self.status_code, self._body, self.headers = status, body, headers or {}
        self.content = b"x"
        self.text = json.dumps(body)

    def json(self):
        return self._body


@pytest.fixture
def yenv(monkeypatch, tmp_path):
    monkeypatch.setenv("PCL_TOKENS_DIR", str(tmp_path / "tokens"))
    monkeypatch.setenv("YOUTUBE_CLIENT_ID", "cid")
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "sec")
    return monkeypatch


def fake_youtube(monkeypatch, calls):
    def post(url, **kw):
        calls.append(("POST", url, kw))
        if "oauth2" in url:
            return Resp({"access_token": "at", "expires_in": 3600})
        if "uploadType" in str(kw.get("params")) or "/videos" in url:
            return Resp({}, 200, {"Location": "https://upload.example/session"})
        return Resp({})

    def put(url, **kw):
        calls.append(("PUT", url, kw))
        return Resp({"id": "VID123"}, 201)
    monkeypatch.setattr(Y.requests, "post", post)
    monkeypatch.setattr(Y.requests, "put", put)


def test_upload_needs_confirmation_and_stays_private(yenv, tmp_path):
    write_spec(tmp_path, spec())
    (tmp_path / "output").mkdir()
    (tmp_path / "output/ep01-de.mp4").write_bytes(b"video")
    Y.prepare(tmp_path)
    with pytest.raises(Y.YTError, match="not signed in"):
        Y.upload_check(tmp_path, "ep01-de")
    Y.save_token("de", {"refresh_token": "rt"})
    calls = []
    fake_youtube(yenv, calls)
    with pytest.raises(Y.YTError, match="confirmation"):
        Y.upload(tmp_path, "ep01-de", "")
    assert not [c for c in calls if c[0] == "PUT"]
    vid, link, msg = Y.upload(tmp_path, "ep01-de", "ep01-de")
    assert vid == "VID123" and link == "https://youtu.be/VID123" and "private" in msg
    start = [c for c in calls if "uploadType" in str(c[2].get("params"))][0]
    body = json.loads(start[2]["data"])
    assert body["status"]["privacyStatus"] == "private" and body["status"]["publishAt"] == "2030-01-01T17:00:00Z"
    assert start[2]["headers"]["X-Upload-Content-Length"] == "5"
    with pytest.raises(Y.YTError, match="already uploaded"):
        Y.upload(tmp_path, "ep01-de", "ep01-de")
    Y.prepare(tmp_path)  # neu vorbereiten vergisst den Upload nicht
    assert json.loads((tmp_path / "youtube/packages/ep01-de/package.json").read_text(encoding="utf-8"))["uploaded"]["video_id"] == "VID123"
    with pytest.raises(Y.YTError, match="has errors"):
        Y.upload_check(tmp_path, "ep02-en", need_login=False)
    with pytest.raises((Y.YTError, ValueError)):
        Y.package(tmp_path, "../../etc")


def test_agent_youtube_tool_and_approval(yenv, client, monkeypatch):
    pid = make_project("Animationsstudio")
    aid = make_agent(pid, "Kanalmanager", youtube=True)
    tid = make_task(pid, aid, status="running")
    root = A.proj_dir(pid)
    root.mkdir(parents=True, exist_ok=True)
    perms = dict(A.DEFAULT_PERMS, youtube=True)
    assert A.youtube_doc(pid, A.DEFAULT_PERMS) == "" and '"tool": "youtube"' in A.youtube_doc(pid, perms)
    assert "No channel is signed in" in A.youtube_doc(pid, perms)
    write_spec(root, spec())
    out, made = A.youtube_tool({"tool": "youtube", "op": "prepare"}, pid, aid, tid)
    assert made == "youtube/REVIEW.md" and "4 packages" in out
    assert A.youtube_tool({"op": "upload", "package": "ep01-de"}, pid, aid, tid)[0].startswith("ERROR")  # Video fehlt
    (root / "output").mkdir(exist_ok=True)
    (root / "output/ep01-de.mp4").write_bytes(b"video")
    assert "not signed in" in A.youtube_tool({"op": "upload", "package": "ep01-de"}, pid, aid, tid)[0]
    Y.save_token("de", {"refresh_token": "rt"})
    msg, _ = A.youtube_tool({"op": "upload", "package": "ep01-de"}, pid, aid, tid)
    assert "approval" in msg
    assert "already waiting" in A.youtube_tool({"op": "upload", "package": "ep01-de"}, pid, aid, tid)[0]
    ap = A.q1("SELECT * FROM approvals WHERE task_id=?", (tid,))
    assert ap["kind"] == "youtube" and "Niemals drücken" in ap["payload"]
    A.set_task(tid, "waiting_approval", "Pakete fertig.")
    calls = []
    fake_youtube(monkeypatch, calls)
    assert client.post(f"/api/approvals/{ap['id']}", json={"decision": "approve"}).status_code == 200
    for _ in range(200):
        t = A.q1("SELECT * FROM tasks WHERE id=?", (tid,))
        if t["status"] == "done":
            break
        time.sleep(0.02)
    assert t["status"] == "done" and "youtu" in t["result"] and "VID123" in t["result"]
    assert "youtube" not in A.RECRUIT_PERMS
