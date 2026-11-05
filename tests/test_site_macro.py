"""Browser-Makros des Besitzers (site_macro): Freischaltung, Aufruf ohne Schlüssel, Ergebnis nach output/."""
import importlib.util
import os
import sys
import types

import pytest
import agent_tools as T

MAKRO = '''
import os, pathlib
out = pathlib.Path(os.environ["PCL_OUTPUT"])
assert "FAL_KEY" not in os.environ and "GEMINI_API_KEY" not in os.environ, "Schluessel duerfen nicht ans Makro"
(out / "video.mp4").write_bytes(b"\\x00\\x00\\x00\\x18ftypmp42" + os.environ["PCL_PROMPT"].encode())
print("fertig", os.environ["PCL_STORAGE"].endswith("demo.json"))
'''


@pytest.fixture
def makros(monkeypatch, tmp_path):
    d = tmp_path / "macros"
    d.mkdir()
    (d / "demo.py").write_text(MAKRO, encoding="utf-8")
    (d / "kaputt.py").write_text("import os, pathlib; (pathlib.Path(os.environ['PCL_OUTPUT']) / 'fehler-bildschirm.png').write_bytes(b'png')\n"
                                 "raise SystemExit('Knopf nicht gefunden')", encoding="utf-8")
    (d / "leer.py").write_text("print('nichts')", encoding="utf-8")
    (d / "vorlage_x.py").write_text("", encoding="utf-8")
    monkeypatch.setenv("PCL_MACRO_DIR", str(d))
    monkeypatch.setenv("PCL_MACROS", "1")
    monkeypatch.setenv("FAL_KEY", "geheim")
    real = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec", lambda n, *a: types.SimpleNamespace() if n == "playwright" else real(n, *a))
    return d


def test_standard_aus(monkeypatch, makros):
    monkeypatch.setenv("PCL_MACROS", "0")
    assert T.macro_sites() == []
    assert "site_macro" not in T.available({"media": True})


def test_sichtbar_ohne_vorlagen(makros):
    assert T.macro_sites() == ["demo", "kaputt", "leer"]
    assert "site_macro" in T.available({"media": True})
    assert "site_macro" not in T.available({"media": False})


def test_lauf_legt_video_in_output(makros, tmp_path):
    root = tmp_path / "proj"
    out, made = T.run_tool({"tool": "site_macro", "site": "demo", "prompt": "Ein Fuchs", "name": "folge1"}, root, {"media": True})
    assert made == "output/folge1.mp4", out
    assert (root / made).read_bytes().endswith(b"Ein Fuchs")
    assert "fertig True" in out
    assert not [p for p in (root / "output").iterdir() if p.name.startswith(".tmp-macro-")]


def test_fehler_und_unbekannte_seite(makros, tmp_path):
    root = tmp_path / "proj"
    out, _ = T.run_tool({"tool": "site_macro", "site": "kaputt", "prompt": "x"}, root, {"media": True})
    assert out.startswith("ERROR") and "Knopf nicht gefunden" in out
    assert "output/kaputt-error.png" in out and (root / "output/kaputt-error.png").exists()
    out, _ = T.run_tool({"tool": "site_macro", "site": "leer", "prompt": "x"}, root, {"media": True})
    assert "saved no file" in out
    out, _ = T.run_tool({"tool": "site_macro", "site": "../demo", "prompt": "x"}, root, {"media": True})
    assert "Unknown site" in out and "demo" in out
    out, _ = T.run_tool({"tool": "site_macro", "site": "demo", "prompt": ""}, root, {"media": True})
    assert "prompt missing" in out


def test_vorlagen_sind_gueltiges_python():
    here = os.path.join(os.path.dirname(__file__), "..", "macros")
    for n in ("vorlage_magiclight.py", "vorlage_flow.py"):
        compile(open(os.path.join(here, n), encoding="utf-8").read(), n, "exec")
