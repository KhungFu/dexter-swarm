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
