"""Filmstudio (film_studio.py + blender/pcl_film.py): Drehbuch, Zeitlogik, Ton, Rendern, Schnitt.

Ohne Blender laeuft alles ausser dem echten Rendern: dafuer gibt es eine Blender-Attrappe, die Bilder mit Pillow malt.
Mit echtem Blender: PCL_TEST_BLENDER=/pfad/zu/blender python -m pytest tests/test_film.py
"""
import json
import os
import shutil
import stat
import sys
from pathlib import Path

import pytest

import agent_tools as T
import film_studio as F
from agent_tools import ToolError

HAS_FF = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
HAS_TTS = bool(shutil.which("espeak-ng"))
ff = pytest.mark.skipif(not HAS_FF, reason="ffmpeg fehlt")
tts = pytest.mark.skipif(not (HAS_FF and HAS_TTS), reason="ffmpeg/espeak-ng fehlt")


def plan(**over):
    p = {"titel": "Test", "aufloesung": "160x90", "fps": 6,
         "figuren": {"Bello": {"art": "hund", "stimme": {"voice": "m3", "pitch": 30}}, "Mimi": {"art": "katze"}},
         "szenen": [{"id": "s01", "figuren": {"Bello": {"pos": [-2, 0]}, "Mimi": {"pos": [2, 0], "blick": "links"}},
                     "requisiten": [{"id": "ball", "typ": "ball", "pos": [0, 1]}],
                     "aktionen": [{"zeit": 0, "figur": "Bello", "tun": "gehen", "nach": [0, 0], "dauer": 1},
                                  {"zeit": 1.5, "figur": "Mimi", "tun": "springen"}],
                     "dialog": [{"figur": "Bello", "text": "Hallo!"}],
                     "kamera": {"einstellung": "total"}, "dauer": 2}]}
    p.update(over)
    return p


@pytest.fixture
def root(tmp_path):
    (tmp_path / "assets").mkdir()
    return tmp_path


# ----------------------------------------------------------------------------- Drehbuch
def test_normalize_defaults(root):
    p = F.normalize(root, plan())
    assert (p["breite"], p["hoehe"], p["fps"]) == (160, 90, 6)
    sc = p["szenen"][0]
    assert [e["id"] for e in sc["entities"]] == ["Bello", "Mimi", "ball"]
    assert sc["entities"][1]["blick"] == F.RICHTUNG["links"]
    assert p["figuren"]["Bello"]["stimme"]["voice"] == "m3"


def test_normalize_collects_all_errors(root):
    bad = plan(figuren={"Bello": {"art": "drache"}, "Mimi": {"art": "katze"}})
    bad["szenen"][0]["aktionen"].append({"zeit": 0, "figur": "Mimi", "tun": "fliegen"})
    bad["szenen"][0]["kamera"] = {"einstellung": "super"}
    with pytest.raises(ToolError) as e:
        F.normalize(root, bad)
    msg = str(e.value)
    assert "drache" in msg and "Bello" in msg and "fliegen" in msg and "super" in msg


def test_paths_stay_inside_project(root, tmp_path_factory):
    outside = tmp_path_factory.mktemp("x") / "a.png"
    outside.write_bytes(b"x")
    for p in ("../a.png", str(outside), ".geheim/a.png"):
        with pytest.raises(ToolError):
            F.normalize(root, plan(figuren={"X": {"art": "bild", "bild": p}}, szenen=[{"id": "a"}]))
    with pytest.raises(ToolError):
        F.normalize(root, plan(figuren={"X": {"art": "blend", "datei": "assets/fehlt.blend"}}, szenen=[{"id": "a"}]))
    with pytest.raises(ToolError, match="film/"):
        F.film(root, {"op": "save", "film": plan(), "datei": "../x.json"})


def test_save_checks_before_writing(root):
    with pytest.raises(ToolError):
        F.film(root, {"op": "save", "film": {"szenen": []}})
    assert not (root / "film" / "film.json").exists()
    out = F.film(root, {"op": "save", "film": json.dumps(plan())})
    assert "Saved: film/film.json" in out and "s01" in out
    assert "Script ok" in F.film(root, {"op": "check"})


# ----------------------------------------------------------------------------- Zeitlogik
def test_walk_jump_and_mouth():
    p = F.normalize(Path("."), plan())
    sc = p["szenen"][0]
    timed = [{"figur": "Bello", "text": "Hallo", "start": 1.0, "ende": 1.5}]
    env = [[1.0, 0.5, 0.0]]
    bello = F.entity_frames(sc["entities"][0], sc["aktionen"], p["figuren"]["Bello"], timed, env, 6, 18)
    assert bello[0][0] == -2 and bello[6][0] == 0  # nach 1 s angekommen
    assert 0 < bello[3][3] <= 70  # beim Gehen nach rechts in Dreiviertelansicht
    assert bello[6][9] == 1.0 and bello[7][9] == 0.5 and bello[12][9] == 0.0  # Mund folgt der Lautstaerke
    mimi = F.entity_frames(sc["entities"][1], sc["aktionen"], p["figuren"]["Mimi"], timed, env, 6, 18)
    assert max(r[2] for r in mimi) > 0.5 and mimi[0][2] == 0  # Sprung
    assert all(r[9] == 0 for r in mimi)  # Mimi spricht nicht


def test_flat_figures_flip_instead_of_turning(root):
    from PIL import Image
    Image.new("RGB", (40, 80), "white").save(root / "assets" / "f.png")
    p = F.normalize(root, plan(figuren={"F": {"art": "bild", "bild": "assets/f.png", "blickrichtung": "rechts"}},
                               szenen=[{"id": "a", "figuren": {"F": {"pos": [2, 0]}},
                                        "aktionen": [{"zeit": 0, "figur": "F", "tun": "gehen", "nach": [-2, 0], "dauer": 1}]}]))
    sc = p["szenen"][0]
    rows = F.entity_frames(sc["entities"][0], sc["aktionen"], p["figuren"]["F"], [], [], 6, 6)
    assert all(r[3] == 0 for r in rows)  # nie gedreht (sonst unsichtbar von der Seite)
    assert rows[2][12] == -1  # laeuft nach links, Bild schaut nach rechts -> gespiegelt


def test_appear_and_camera_moves():
    p = F.normalize(Path("."), plan())
    sc = p["szenen"][0]
    sc["aktionen"].append({"wer": "ball", "tun": "erscheinen", "zeit": 1.0})
    ball = F.entity_frames(sc["entities"][2], sc["aktionen"], None, [], [], 6, 12)
    assert ball[0][4] == 0 and ball[11][4] == 1
    sc["kamera"] = {"einstellung": "nah", "bewegung": "zoom_raus", "ziel": "Mimi"}
    rows = [F.entity_frames(e, sc["aktionen"], p["figuren"].get(e.get("fig")), [], [], 6, 12) for e in sc["entities"]]
    cam = F.camera_frames(sc, rows, 6, 12)
    assert cam[0][3] == 2 and abs(cam[-1][1]) > abs(cam[0][1])  # zielt auf Mimi, faehrt zurueck


def test_timing_uses_audio_lengths():
    sc = F.normalize(Path("."), plan())["szenen"][0]
    lines = [dict(figur="Bello", text="a", pause=0.5, zeit=None, dauer=2.0), dict(figur="Mimi", text="b", pause=0.3, zeit=None, dauer=1.0)]
    timed, dur = F.timing(sc, lines)
    assert [t["start"] for t in timed] == [0.5, 3.0] and dur == pytest.approx(4.6)


# ----------------------------------------------------------------------------- Werkzeug und Rechte
def test_tool_needs_media_right(root):
    assert "film" in T.available({"media": True}) and "film" not in T.available({"web": True})
    out, _ = T.run_tool({"tool": "film", "op": "check"}, root, {"media": True})
    assert out.startswith("ERROR") and "op=save" in out
    out, made = T.run_tool({"tool": "film", "op": "save", "film": plan()}, root, {"media": True})
    assert made == "film/film.json"


def test_blender_missing_is_explained(root, monkeypatch):
    monkeypatch.setenv("BLENDER_PATH", str(root / "gibtsnicht.exe"))
    assert F.blender_exe() is None
    F.film(root, {"op": "save", "film": plan(szenen=[{"id": "a", "figuren": {"Bello": {}}, "dauer": 1}])})
    out, _ = T.run_tool({"tool": "film", "op": "preview"}, root, {"media": True})
    assert "BLENDER_PATH" in out


def test_windows_default_folder(monkeypatch, tmp_path):
    for v in ("BLENDER_PATH", "ProgramW6432", "LOCALAPPDATA"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setattr(F.shutil, "which", lambda n: None)
    for ver in ("3.6", "4.2"):
        d = tmp_path / "Blender Foundation" / f"Blender {ver}"
        d.mkdir(parents=True)
        (d / "blender.exe").write_text("")
    monkeypatch.setenv("ProgramFiles", str(tmp_path))
    assert F.blender_exe().endswith(os.path.join("Blender 4.2", "blender.exe"))


# ----------------------------------------------------------------------------- Ton und Rendern
FAKE = '''import json, os, sys
from PIL import Image
if os.environ.get("FAKE_KEY"):
    print("PCL_FEHLER Schluessel sichtbar"); sys.exit(3)
job = json.load(open(sys.argv[sys.argv.index("--") + 1], encoding="utf-8"))
os.makedirs(job["ausgabe"], exist_ok=True)
for i in range(job["frames"]):
    Image.new("RGB", (job["breite"], job["hoehe"]), (i * 7 % 255, 120, 200)).save(os.path.join(job["ausgabe"], f"{i:05d}.png"))
print("PCL_FERTIG")
'''


@pytest.fixture
def fake_blender(tmp_path_factory, monkeypatch):
    if os.name == "nt":
        pytest.skip("Attrappe ist ein Shell-Skript")
    d = tmp_path_factory.mktemp("bl")
    (d / "fake.py").write_text(FAKE)
    exe = d / "blender"
    exe.write_text(f'#!/bin/sh\nfor a; do last="$a"; done\nexec "{sys.executable}" "{d / "fake.py"}" -- "$last"\n')
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("BLENDER_PATH", str(exe))
    monkeypatch.setenv("FAKE_KEY", "geheim")  # darf in Blender nicht ankommen
    return exe


@tts
def test_voices_are_cached(root):
    F.film(root, {"op": "save", "film": plan()})
    assert "1 neu" in F.film(root, {"op": "voices"})
    assert "0 neu" in F.film(root, {"op": "voices"})
    env = F.envelope(root, str(root / "film" / "ton" / "s01_01.mp3"), 6)
    assert env and max(env) == 1.0


@tts
def test_render_and_assemble_with_fake_blender(root, fake_blender):
    F.film(root, {"op": "save", "film": plan(titelkarte=1)})
    out = F.film(root, {"op": "render"})
    assert "film/clips/s01.mp4" in out
    assert "unchanged" in F.film(root, {"op": "render"})  # nichts geaendert -> nicht neu rendern
    assert not (root / "film" / ".frames" / "s01").exists()
    clip = T._probe(root / "film" / "clips" / "s01.mp4")
    assert clip["video"] and clip["audio"] and clip["duration"] >= 2
    out = F.film(root, {"op": "assemble", "name": "folge1", "untertitel": True})
    assert "output/folge1.mp4" in out
    film = T._probe(root / "output" / "folge1.mp4")
    assert film["duration"] == pytest.approx(clip["duration"] + 1, abs=0.4)
    assert "Hallo!" in (root / "output" / "folge1.srt").read_text(encoding="utf-8")


@ff
def test_assemble_reports_missing_clips(root):
    F.film(root, {"op": "save", "film": plan()})
    with pytest.raises(ToolError, match="s01"):
        F.film(root, {"op": "assemble"})


@tts
def test_preview_with_fake_blender(root, fake_blender):
    F.film(root, {"op": "save", "film": plan()})
    out, made = T.run_tool({"tool": "film", "op": "preview", "szene": "s01", "zeit": 1}, root, {"media": True})
    assert made == "film/vorschau/s01.png", out


@pytest.mark.skipif(not (os.environ.get("PCL_TEST_BLENDER") and HAS_TTS), reason="echtes Blender: PCL_TEST_BLENDER setzen")
def test_real_blender(root, monkeypatch):
    from PIL import Image
    monkeypatch.setenv("BLENDER_PATH", os.environ["PCL_TEST_BLENDER"])
    Image.new("RGB", (60, 120), "white").save(root / "assets" / "fig.png")
    p = plan(renderer="cycles", samples=2)
    p["figuren"]["Bild"] = {"art": "bild", "bild": "assets/fig.png"}
    p["szenen"][0]["figuren"]["Bild"] = {"pos": [0, 2]}
    p["szenen"][0]["ort"] = {"hintergrund": "assets/fig.png"}
    F.film(root, {"op": "save", "film": p})
    assert "s01.png" in F.film(root, {"op": "preview"})
    assert "gerendert" in F.film(root, {"op": "render"})
    assert T._probe(root / "film" / "clips" / "s01.mp4")["video"]
