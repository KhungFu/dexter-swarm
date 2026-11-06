"""Uebergabe-Stand je Auftrag (Wunsch ABI 2026-11-06).

Jeder oberste Auftrag bekommt im Projektordner eine Datei handover/assignment-<id>.md. Der Server schreibt dort hinein:
Auftrag, Arbeitsort (Projektordner, Repos, vorhandene STAND.md/HANDOVER.md), und je Lauf die Zwischenschritte
(wer, welches Modell, welche Werkzeuge, Ergebnis, naechster Schritt, Fehler). Faellt ein Modell aus (Kontingent,
Absturz, Neustart) oder wechselt der Besitzer das Modell, bekommt das naechste Modell diese Datei in den Auftrag und
macht dort weiter. Reine Dateifunktionen, keine Datenbank.
"""
import os
import re
import threading
import time
from pathlib import Path

DIR = "handover"
MAX_BYTES = int(os.environ.get("PCL_HANDOVER_KB", "64")) * 1024     # danach werden die aeltesten Eintraege gekuerzt
PROMPT_CHARS = int(os.environ.get("PCL_HANDOVER_PROMPT", "6000"))   # so viel vom Ende der Datei geht in den Auftrag
ENTRY_CHARS = 1500
LOG_HEAD = "## Log"
DOC_NAMES = {"stand.md", "handover.md"}
_lock = threading.Lock()


def enabled():
    return os.environ.get("PCL_HANDOVER", "1") != "0"


def path(root, top_id):
    return Path(root) / DIR / f"assignment-{int(top_id)}.md"


def _clip(text, n):
    text = str(text or "").strip()
    return text if len(text) <= n else text[:n] + f" [... {len(text) - n} characters shortened]"


def _remote(git_dir):
    """URL von origin aus .git/config, ohne Zugangsdaten."""
    try:
        cfg = (git_dir / "config").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    m = re.search(r'\[remote "origin"\][^\[]*?url\s*=\s*(\S+)', cfg)
    return re.sub(r"//[^/@\s]+@", "//", m.group(1)) if m else ""


def workplace(root, max_dirs=3000):
    """Wo die Firma arbeitet: Git-Repos (bis Tiefe 2) und Uebergabe-Dateien (STAND.md/HANDOVER.md, bis Tiefe 4) im Projektordner."""
    root = Path(root)
    repos, docs, seen = [], [], 0
    if not root.is_dir():
        return repos, docs
    for cur, dirs, files in os.walk(root):
        seen += 1
        rel = Path(cur).relative_to(root)
        depth = len(rel.parts)
        if ".git" in dirs and 0 < depth <= 2:
            repos.append((rel.as_posix(), _remote(Path(cur) / ".git")))
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in ("target", "node_modules", "input", DIR)
                         and depth < 4)
        for f in sorted(files):
            if f.lower() in DOC_NAMES and len(docs) < 10:
                docs.append((rel / f).as_posix())
        if seen >= max_dirs:
            break
    return repos[:10], docs


def workplace_text(root, folder=""):
    repos, docs = workplace(root)
    lines = [f"- Project folder: {folder or Path(root).name} (all paths are relative to it)"]
    if repos:
        lines.append("- Repositories in the project folder: " + "; ".join(f"{r} ({u})" if u else r for r, u in repos))
    if docs:
        lines.append("- Handover files from earlier work, READ THEM FIRST with read_file: " + ", ".join(docs))
    if (Path(root) / "wissen").is_dir():
        lines.append("- Company knowledge: wissen/")
    return "\n".join(lines)


def _ensure(root, top, folder=""):
    f = path(root, top["id"])
    if f.is_file():
        return f
    f.parent.mkdir(parents=True, exist_ok=True)
    head = (f"# HANDOVER: assignment #{top['id']} - {_clip(top.get('title'), 200)}\n\n"
            "Saved by Hyperstead after every step. Every AI model that works on this assignment (any provider) reads this file "
            "first and continues from the last entry. Do not start over and do not redo finished steps.\n\n"
            f"Assignment:\n{_clip(top.get('description'), 3000) or '(no description)'}\n\n"
            f"Where to work (at the start):\n{workplace_text(root, folder)}\n\n{LOG_HEAD}\n")
    f.write_text(head, encoding="utf-8")
    return f


def _trim(f):
    data = f.read_text(encoding="utf-8", errors="replace")
    if len(data.encode("utf-8")) <= MAX_BYTES:
        return
    i = data.find(LOG_HEAD)
    head = data[:i + len(LOG_HEAD)] if i >= 0 else ""
    body = data[len(head):]
    keep = MAX_BYTES - len(head.encode("utf-8")) - 200
    tail = body.encode("utf-8")[-max(keep, 1000):].decode("utf-8", "ignore")
    j = tail.find("\n### ")
    tail = tail[j:] if j >= 0 else tail
    f.write_text(head + "\n\n(older entries removed, file limit PCL_HANDOVER_KB)\n" + tail, encoding="utf-8")


def note(root, top, tid, who, kind, text="", folder=""):
    """Haengt einen Eintrag an. who = 'Name (Rolle) - anbieter/modell'. Fehler beim Schreiben brechen die Arbeit nie ab."""
    if not enabled() or not top:
        return
    try:
        with _lock:
            f = _ensure(root, top, folder)
            entry = f"\n### {time.strftime('%Y-%m-%d %H:%M')} | task #{int(tid)} | {who} | {kind}\n"
            if str(text or "").strip():
                entry += _clip(text, ENTRY_CHARS) + "\n"
            with open(f, "a", encoding="utf-8") as fh:
                fh.write(entry)
            _trim(f)
    except OSError as e:
        print("Handover not written:", e)


def has_entries(root, top_id, tid=None):
    f = path(root, top_id)
    if not f.is_file():
        return False
    data = f.read_text(encoding="utf-8", errors="replace")
    return (f"| task #{int(tid)} |" in data) if tid else ("\n### " in data)


def prompt_block(root, top_id, folder=""):
    """Block fuer den Auftrag: Arbeitsort (aktuell) + Ende der Uebergabe-Datei."""
    f = path(root, top_id)
    if not f.is_file():
        return ""
    data = f.read_text(encoding="utf-8", errors="replace")
    i = data.find(LOG_HEAD)
    log = data[i + len(LOG_HEAD):].strip() if i >= 0 else data
    if len(log) > PROMPT_CHARS:
        log = "[... earlier entries: read_file " + f"{DIR}/{f.name}]\n" + log[-PROMPT_CHARS:]
    return ("HANDOVER STATE of this assignment (saved by the server in "
            f"{DIR}/{f.name}). Earlier runs, possibly with another AI model, already worked on it. Continue exactly from the "
            "last entry: do not start over, do not redo finished steps, use the files that already exist.\n"
            f"Where to work:\n{workplace_text(root, folder)}\n\nLog (newest at the end):\n{log}")
