"""Windows-Voraussetzungen: Pruefen, Liste, Rueckfrage vor jeder Installation, Merken abgelehnter Teile, PATH-Ergaenzung."""
from pathlib import Path

import pytest

import voraussetzungen as V
import win_pfade

ROOT = Path(__file__).resolve().parent.parent
ERWEITERN = win_pfade.erweitern  # vor dem Ersetzen in der Fixture merken


class Fake:
    def __init__(self):
        self.da = {}
        self.installiert = []

    def teil(self, id, da=False, braucht=None, merken=True, nur_start=False, relevant=True, kaputt=False):
        self.da[id] = da

        def install():
            if kaputt:
                raise RuntimeError("kaputt")
            self.installiert.append(id)
            self.da[id] = True
        return V.Teil(id, id.upper(), "wozu", "1 MB", f"befehl {id}", lambda: self.da[id], install,
                      relevant=lambda: relevant, braucht=braucht, merken=merken, nur_start=nur_start)


@pytest.fixture(autouse=True)
def nein_datei(tmp_path, monkeypatch):
    monkeypatch.setattr(V, "NEIN_DATEI", tmp_path / "nein")
    monkeypatch.setattr(V.win_pfade, "erweitern", lambda *a, **k: [])
    return tmp_path / "nein"


def test_alles_da(capsys):
    f = Fake()
    erg = V.ablauf("install", [f.teil("a", da=True)], iter([]))
    assert "alles da" in capsys.readouterr().out and not any(erg.values())


def test_liste_installiert_nichts(capsys):
    f = Fake()
    V.ablauf("liste", [f.teil("a"), f.teil("b")], iter(["j", "j"]))
    out = capsys.readouterr().out
    assert "FEHLT  A" in out and "befehl b" in out and f.installiert == []


def test_install_fragt_jeden_teil(nein_datei):
    f = Fake()
    erg = V.ablauf("install", [f.teil("a"), f.teil("b"), f.teil("c")], iter(["j", "n", "j"]))
    assert f.installiert == ["a", "c"] and erg["abgelehnt"] == ["b"]
    assert nein_datei.read_text().split() == ["b"]


def test_ohne_antwort_nichts_installieren():
    f = Fake()
    V.ablauf("install", [f.teil("a")], iter([]))  # Standard ist n
    assert f.installiert == []


def test_alle_ja_und_alle_nein():
    f = Fake()
    V.ablauf("install", [f.teil("a"), f.teil("b"), f.teil("c")], iter(["a"]))
    assert f.installiert == ["a", "b", "c"]
    g = Fake()
    erg = V.ablauf("install", [g.teil("a"), g.teil("b")], iter(["x"]))
    assert g.installiert == [] and erg["abgelehnt"] == ["a", "b"]


def test_start_ohne_antwort_startet_einfach(nein_datei):
    f = Fake()
    erg = V.ablauf("start", [f.teil("a"), f.teil("b")], iter([]))
    assert f.installiert == [] and not nein_datei.exists() and erg["abgelehnt"] == ["a", "b"]


def test_start_x_merkt_und_fragt_nicht_mehr(nein_datei, capsys):
    f = Fake()
    V.ablauf("start", [f.teil("a"), f.teil("b", merken=False, nur_start=True)], iter(["x"]))
    assert nein_datei.read_text().split() == ["a"]
    capsys.readouterr()
    V.ablauf("start", [f.teil("a")], iter(["j", "j"]))
    out = capsys.readouterr().out
    assert f.installiert == [] and "frueher abgelehnt" in out
    # install.ps1 fragt Abgelehntes wieder und vergisst die Ablehnung nach der Installation
    V.ablauf("install", [f.teil("a")], iter(["j"]))
    assert f.installiert == ["a"] and nein_datei.read_text().split() == []


def test_start_j_fragt_einzeln():
    f = Fake()
    V.ablauf("start", [f.teil("a"), f.teil("b")], iter(["j", "n", "j"]))
    assert f.installiert == ["b"]


def test_nur_start_teile_nicht_in_install():
    f = Fake()
    V.ablauf("install", [f.teil("s", nur_start=True)], iter(["j"]))
    assert f.installiert == []


def test_abhaengigkeit_und_fehler():
    f = Fake()
    erg = V.ablauf("install", [f.teil("node"), f.teil("tsc", braucht="node")], iter(["n"]))
    assert erg["uebersprungen"] == ["tsc"]
    g = Fake()
    erg = V.ablauf("install", [g.teil("node"), g.teil("tsc", braucht="node")], iter(["j", "j"]))
    assert g.installiert == ["node", "tsc"]
    h = Fake()
    erg = V.ablauf("install", [h.teil("k", kaputt=True), h.teil("b")], iter(["j", "j"]))
    assert erg["fehlgeschlagen"] == ["k"] and h.installiert == ["b"]


def test_nicht_relevant_wird_nicht_gezeigt(capsys):
    f = Fake()
    V.ablauf("liste", [f.teil("bild", relevant=False)], iter([]))
    assert "alles da" in capsys.readouterr().out


def test_echte_liste_vollstaendig():
    ids = [t.id for t in V.teile()]
    for i in ("pakete", "ffmpeg", "piper", "edge", "browser", "tesseract", "ocr-sprachen", "poppler", "blender",
              "bildrechner", "bildrechner-start", "rust", "buildtools", "cargo-unsafe", "node", "typescript", "java",
              "go", "gcc", "bash", "ruby", "php", "lua"):
        assert i in ids
    for t in V.teile():
        if t.braucht:
            assert ids.index(t.braucht) < ids.index(t.id), t.id  # Abhaengigkeit kommt vorher
        assert t.befehl and t.groesse and t.wozu


def test_env_setzen(tmp_path, monkeypatch):
    f = tmp_path / ".env"
    f.write_text("﻿A=1\n# PCL_CARGO_UNSAFE=0\nB=2\n", encoding="utf-8")
    V.env_setzen("PCL_CARGO_UNSAFE", "1", f)
    assert V.env_lesen(f)["PCL_CARGO_UNSAFE"] == "1" and "# PCL_CARGO_UNSAFE=0" in f.read_text()
    V.env_setzen("B", "3", f)
    assert V.env_lesen(f)["B"] == "3" and f.read_text().count("B=") == 1
    monkeypatch.delenv("PCL_CARGO_UNSAFE")


def test_pakete_stempel(tmp_path, monkeypatch):
    monkeypatch.setattr(V, "STEMPEL", tmp_path / "s")
    assert not V.pakete_da()
    (tmp_path / "s").write_text(V.req_hash().upper())  # PowerShell schreibt evtl. gross
    assert V.pakete_da()


def test_main_auf_linux_tut_nichts(capsys, monkeypatch):
    monkeypatch.setattr(V, "WIN", False)
    assert V.main([]) == 0 and "install.sh" in capsys.readouterr().out


def test_win_pfade(tmp_path):
    pf = tmp_path / "pf"
    (pf / "Tesseract-OCR").mkdir(parents=True)
    (pf / "Git" / "bin").mkdir(parents=True)
    links = tmp_path / "local" / "Microsoft" / "WinGet" / "Links"
    links.mkdir(parents=True)
    pkg = tmp_path / "local" / "Microsoft" / "WinGet" / "Packages" / "Gyan.FFmpeg_x" / "ffmpeg-7" / "bin"
    pkg.mkdir(parents=True)
    (pkg / "ffmpeg.exe").write_text("")
    (tmp_path / "tools" / "tessdata").mkdir(parents=True)
    (tmp_path / "tools" / "tessdata" / "deu.traineddata").write_text("")
    env = {"PATH": str(pf / "Git" / "bin"), "ProgramFiles": str(pf), "LOCALAPPDATA": str(tmp_path / "local")}
    neu = ERWEITERN(env, windows=True, here=tmp_path, registry=False)
    assert str(pf / "Tesseract-OCR") in neu and str(links) in neu and str(pkg) in neu
    assert str(pf / "Git" / "bin") not in neu  # war schon da
    assert env["TESSDATA_PREFIX"] == str(tmp_path / "tools" / "tessdata")
    assert ERWEITERN({"PATH": "x"}, windows=False) == []


def test_skripte_rufen_pruefung_auf():
    ps = (ROOT / "install.ps1").read_text(encoding="utf-8")
    assert "voraussetzungen.py" in ps and ".requirements.sha256" in ps
    assert all(ord(c) < 128 for c in ps)  # Windows PowerShell 5.1 liest .ps1 ohne BOM als ANSI
    bat = (ROOT / "deploy" / "windows" / "hyperstead-start.bat").read_bytes()
    assert b"voraussetzungen.py --start" in bat and b"\r\n" in bat
    assert bat.index(b"voraussetzungen.py --start") < bat.index(b"app.py")
