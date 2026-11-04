"""Oberflaeche: jeder Knopf hat eine Erklaerung, die Anleitung ist eingebaut (kein Download)."""
import os
import re

HTML = open(os.path.join(os.path.dirname(__file__), "..", "static", "index.html"), encoding="utf-8").read()


def _tip_keys():
    block = HTML[HTML.index("const TIPS={"):]
    block = block[:block.index("\n};")]
    return set(re.findall(r"^\s*'([#.\[][^']+)'\s*:", block, re.M))


def test_jeder_knopf_hat_eine_erklaerung():
    keys = _tip_keys()
    ohne = []
    for tag in re.findall(r"<button\b[^>]*>", HTML):
        if "title=" in tag or "aria-label=" in tag or "copyText(" in tag:
            continue
        m = re.search(r'\bid="([^"$]+)"', tag)
        if m and "#" + m.group(1) in keys:
            continue
        datas = re.findall(r"\b(data-[a-z]+)=", tag)
        if any("[" + d + "]" in keys for d in datas):
            continue
        ohne.append(tag[:100])
    assert not ohne, "Knoepfe ohne Erklaerung (title oder Eintrag in TIPS):\n" + "\n".join(ohne)


def test_tips_haben_text():
    for k in _tip_keys():
        assert k.startswith(("#", "[", ".")), k


def test_anleitung_im_dashboard():
    assert 'id="btnHelp"' in HTML and "function showHelp" in HTML
    kap = re.findall(r"\{id:'([a-z]+)',t:'", HTML)
    for k in ("start", "welt", "agenten", "auftraege", "zeitplan", "betrieb", "dateien", "telegram", "probleme"):
        assert k in kap
    # jedes Ziel der Fenster-Zuordnung ist ein echtes Kapitel
    for ziel in re.findall(r"\['[^']+','([a-z]+)'\]", HTML[HTML.index("const HELP_MAP"):HTML.index("function helpFor")]):
        assert ziel in kap


def test_drei_organigramme():
    """Ansicht Organigramm mit drei Arten, jede Art mit Erklaerung im Knopf und in der Anleitung."""
    html = HTML
    assert 'data-view="org"' in html
    for art, fn in (("baum", "orgBaum"), ("gliederung", "orgGliederung"), ("kreis", "orgKreis")):
        assert f'data-org="{art}"' in html and f"function {fn}(" in html
    assert "🏢 Organigramm:</b>" in html


def test_postkorb_und_seitenmenue():
    """Post auswaehlen/loeschen/leeren mit Rueckfrage, Seitenleiste in aufklappbaren Kategorien."""
    for i in ("in_all", "in_del", "in_clear"):
        assert f'id="{i}"' in HTML
    assert "/inbox/clear" in HTML and "confirm(" in HTML[HTML.index("in_clear"):]
    assert HTML.count('class="side-grp"') >= 4
    menu = HTML[HTML.index('id="sidemenu"'):HTML.index('<div class="side-h"><span>Projekte')]
    for b in ("btnInbox", "btnApprovals", "btnOps", "btnGoals", "btnSched", "btnGroupAI", "btnModels", "btnKnow",
              "btnFiles", "btnCloud", "btnConn", "btnUsage", "btnAudit", "btnHelp", "btnLogout"):
        assert f'id="{b}"' in menu


def test_grafik_auswahl_atom_und_farben():
    html = HTML
    # aufklappbare Auswahl mit allen sechs Grafiken
    assert 'id="gViewMenu"' in html and 'aria-haspopup="true"' in html
    for v in ('data-view="world"', 'data-view="atom"', 'data-view="plan"'):
        assert v in html
    assert "function drawAtom(" in html and "Atom" in html
    # Organigramm-Karten verschiebbar
    assert "type:'org'" in html and 'id="orgReset"' in html
    # dunkles Design: Variablen duerfen nicht auf sich selbst zeigen (sonst sind die Bauplan-Linien unsichtbar)
    for name in ("chip", "dotgrid", "edge", "hover", "toastbg"):
        assert not re.search(r"--%s:var\(--%s\)" % (name, name), html)


def test_atom_steht_still_und_logo():
    """Atom ohne Animation (Wunsch ABI), Logo als Symbol eingebunden und ohne Anmeldung abrufbar."""
    atom = HTML[HTML.index("const ATOM"):HTML.index("/* ---------- Start")]
    assert "requestAnimationFrame" not in atom and "opulse" not in atom
    assert "atomTick" not in HTML and "startAtom" not in HTML
    root = os.path.join(os.path.dirname(__file__), "..")
    for n in (32, 180, 192, 512, 1024):
        assert os.path.isfile(os.path.join(root, "static", "logo", f"hyperstead-{n}.png"))
    assert 'rel="icon"' in HTML and "/static/logo/hyperstead-192.png" in HTML
    app = open(os.path.join(root, "app.py"), encoding="utf-8").read()
    assert '"/static/logo/"' in app


def test_planeten_drehen_sich_um_die_eigene_achse():
    assert "function spinWrap(" in HTML and 'class="spin"' in HTML
    place = HTML[HTML.index("function placeMovers("):HTML.index("function orbitTick(")]
    assert "m.spin" in place
