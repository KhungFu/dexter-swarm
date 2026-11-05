"""
Filmstudio: aus einem Drehbuch (film/film.json) wird ein Animationsfilm mit Figuren, Stimmen, Kamera und Schnitt.

Ablauf (Werkzeug `film`, Recht `media`):
  save      -> Drehbuch speichern (film/film.json)
  check     -> Drehbuch pruefen, ohne etwas zu rendern
  voices    -> jede Dialogzeile mit der Stimme ihrer Figur vertonen (film/ton/), Ergebnis wird zwischengespeichert
  preview   -> ein Standbild einer Szene in Blender (film/vorschau/<szene>.png)
  render    -> Szene(n) in Blender rendern, Bilder + Ton -> film/clips/<szene>.mp4 (nur geaenderte Szenen)
  assemble  -> alle Clips zum fertigen Film output/<name>.mp4 (+ Untertitel output/<name>.srt)

Sicherheit: Agenten liefern nur DATEN (JSON). Blender fuehrt ausschliesslich das feste Skript blender/pcl_film.py aus,
mit --factory-startup und --disable-autoexec (Skripte in .blend-Dateien laufen nicht). Alle Pfade bleiben im Projektordner.
Die ganze Zeitlogik (Bewegung, Kamera, Lippensync) wird hier in Python berechnet; Blender baut nur die Szene und
stellt je Bild die fertigen Werte ein. So ist die Logik ohne Blender testbar und laeuft mit Blender 3.6 bis 5.x.
"""
import array
import glob
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import agent_tools as T
from agent_tools import ToolError

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "blender" / "pcl_film.py"
PLAN = "film/film.json"
SCRIPT_VERSION = "1"  # bei Aenderungen am Blender-Skript erhoehen, dann rendert render alle Szenen neu

FIGUR_ARTEN = ("hund", "katze", "hase", "baer", "maus", "mensch")
REQUISITEN = ("baum", "busch", "haus", "stein", "ball", "wolke", "blume", "kiste", "bild")
AKTIONEN = ("gehen", "springen", "winken", "drehen", "nicken", "erscheinen", "verschwinden")
EINSTELLUNGEN = {"total": (11.0, 2.6, 1.3), "halbtotal": (6.5, 1.9, 1.15), "nah": (3.6, 1.55, 1.3)}  # Abstand, Kamerahoehe, Blickhoehe
BEWEGUNGEN = ("keine", "zoom_rein", "zoom_raus", "schwenk_links", "schwenk_rechts", "folgen")
RICHTUNG = {"vorne": 0.0, "kamera": 0.0, "rechts": 60.0, "links": -60.0, "hinten": 180.0}  # Dreiviertelansicht: Gesicht bleibt sichtbar
LICHT = ("tag", "abend", "nacht")
ENGINES = ("eevee", "workbench", "cycles")
MAX_SZENEN = 60
MAX_DAUER = 120.0
WALK_SPEED = 1.6  # Meter pro Sekunde


def _env(k, d=""):
    return os.environ.get(k, d).strip()


# ----------------------------------------------------------------------------- Blender finden
def blender_exe():
    """BLENDER_PATH, sonst blender im PATH, sonst die Standardordner unter Windows (neueste Version zuerst)."""
    p = _env("BLENDER_PATH").strip("\"'")
    if p:
        return p if Path(p).is_file() else None
    p = shutil.which("blender")
    if p:
        return p
    pats = [os.path.join(os.environ.get(v, ""), "Blender Foundation", "Blender*", "blender.exe")
            for v in ("ProgramFiles", "ProgramW6432", "LOCALAPPDATA") if os.environ.get(v)]
    pats += [os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Steam", "steamapps", "common", "Blender", "blender.exe"),
             "/Applications/Blender.app/Contents/MacOS/Blender", "/snap/bin/blender"]
    found = sorted({f for pat in pats for f in glob.glob(pat)}, key=_version_key, reverse=True)
    return found[0] if found else None


def _version_key(path):
    m = re.search(r"Blender\s*(\d+)\.(\d+)", path)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def blender_hint():
    return ("Blender was not found. Set BLENDER_PATH in the .env, e.g. "
            "BLENDER_PATH=C:\\Program Files\\Blender Foundation\\Blender 4.2\\blender.exe (Raspberry Pi: sudo apt install blender).")


# ----------------------------------------------------------------------------- Hilfen
def _f(v, default, lo, hi, what):
    if v in (None, ""):
        return default
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ToolError(f"{what}: '{v}' is not a number")
    if not math.isfinite(x):
        raise ToolError(f"{what}: invalid number")
    return max(lo, min(hi, x))


def _pos(v, default, what):
    if v in (None, ""):
        return list(default)
    if not isinstance(v, (list, tuple)) or len(v) not in (2, 3):
        raise ToolError(f"{what}: pos must be [x, tiefe] (x, depth), e.g. [-2, 0]")
    return [_f(v[0], 0, -30, 30, what), _f(v[1], 0, -5, 40, what)] + ([_f(v[2], 0, -5, 30, what)] if len(v) == 3 else [])


def _color(v, default):
    """'#rrggbb' -> lineares RGB (Blender rechnet linear)."""
    s = str(v or default).strip().lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}|[0-9a-fA-F]{3}", s):
        s = default.lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    out = []
    for i in (0, 2, 4):
        c = int(s[i:i + 2], 16) / 255
        out.append(round(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4, 4))
    return out


def _sid(v):
    s = re.sub(r"[^a-z0-9_-]+", "-", str(v or "").lower()).strip("-")[:40]
    if not s:
        raise ToolError("every scene needs an id (e.g. \"s01\")")
    return s


def _file(root, rel, what, exts=None):
    try:
        f = T._inside(root, rel)
    except ValueError:
        raise ToolError(f"{what}: path is outside the project folder")
    if not f.is_file():
        raise ToolError(f"{what}: file '{rel}' does not exist")
    if any(part.startswith(".") for part in Path(str(rel)).parts):
        raise ToolError(f"{what}: hidden paths are not allowed")
    if exts and f.suffix.lower() not in exts:
        raise ToolError(f"{what}: allowed are {', '.join(exts)}")
    return f


IMG_EXT = (".png", ".jpg", ".jpeg", ".webp")
AUDIO_EXT = (".mp3", ".wav", ".ogg", ".m4a", ".flac")


def _hash(*parts):
    h = hashlib.sha1()
    for p in parts:
        h.update(json.dumps(p, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8"))
    return h.hexdigest()[:16]


def _mtime(f):
    try:
        return int(Path(f).stat().st_mtime)
    except OSError:
        return 0


# ----------------------------------------------------------------------------- Drehbuch laden und pruefen
def plan_path(root, call):
    name = str(call.get("datei") or PLAN)
    if not name.startswith("film/") or not name.endswith(".json") or ".." in name:
        raise ToolError("datei (file) must be in film/ and end in .json (default film/film.json)")
    return T._inside(root, name)


def load_plan(root, call):
    p = plan_path(root, call)
    if not p.is_file():
        raise ToolError(f"{_rel(root, p)} is missing. First save a script with op=save (or write_file).")
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except ValueError as e:
        raise ToolError(f"{_rel(root, p)} is not valid JSON: {e}")
    return normalize(root, data)


def _rel(root, p):
    return Path(p).resolve().relative_to(Path(root).resolve()).as_posix()


def normalize(root, data):
    """Prueft das Drehbuch und fuellt Standardwerte. Wirft ToolError mit ALLEN gefundenen Fehlern."""
    if not isinstance(data, dict):
        raise ToolError("The script must be a JSON object ({\"titel\": ..., \"figuren\": {...}, \"szenen\": [...]})")
    errs = []

    def guard(fn, *a):
        try:
            return fn(*a)
        except ToolError as e:
            errs.append(str(e))
            return None

    plan = {"titel": str(data.get("titel") or "Film")[:120]}
    m = re.fullmatch(r"\s*(\d{2,4})\s*[xX×]\s*(\d{2,4})\s*", str(data.get("aufloesung") or _env("FILM_RES", "640x360")))
    w, h = (int(m.group(1)), int(m.group(2))) if m else (640, 360)
    plan["breite"], plan["hoehe"] = max(160, min(w, 1920)) // 2 * 2, max(90, min(h, 1080)) // 2 * 2
    plan["fps"] = int(guard(_f, data.get("fps"), float(_env("FILM_FPS", "12") or 12), 6, 30, "fps") or 12)
    eng = str(data.get("renderer") or _env("BLENDER_ENGINE", "eevee")).lower()
    plan["renderer"] = eng if eng in ENGINES else "eevee"
    plan["samples"] = int(guard(_f, data.get("samples"), float(_env("BLENDER_SAMPLES", "16") or 16), 1, 256, "samples") or 16)
    plan["umriss"] = data.get("umriss", True) is not False
    plan["musik"] = None
    if data.get("musik"):
        f = guard(_file, root, data.get("musik"), "musik", AUDIO_EXT)
        plan["musik"] = str(f) if f else None
    plan["musik_lautstaerke"] = guard(_f, data.get("musik_lautstaerke"), 0.25, 0, 2, "musik_lautstaerke") or 0.25
    plan["titelkarte"] = guard(_f, data.get("titelkarte"), 0, 0, 10, "titelkarte") or 0

    figs = data.get("figuren") or {}
    if isinstance(figs, list):  # auch [{"name": ...}, ...] annehmen
        figs = {str(x.get("name")): x for x in figs if isinstance(x, dict) and x.get("name")}
    if not isinstance(figs, dict):
        errs.append("figuren must be an object: {\"Bello\": {\"art\": \"hund\", ...}}")
        figs = {}
    plan["figuren"] = {}
    for name, fd in list(figs.items())[:20]:
        fd = fd if isinstance(fd, dict) else {}
        art = str(fd.get("art") or "mensch").lower()
        fig = {"name": str(name)[:40], "groesse": guard(_f, fd.get("groesse"), 1.0, 0.2, 5, f"Figure {name}: groesse") or 1.0}
        if art in FIGUR_ARTEN:
            fig.update(typ="figur", art=art, farbe=_color(fd.get("farbe"), "#c8843c" if art != "mensch" else "#3b6fd1"),
                       farbe2=_color(fd.get("farbe2"), "#f6e7d0" if art != "mensch" else "#f1c27d"),
                       haar=_color(fd.get("haar"), "#4a2c17"))
        elif art == "bild":
            f = guard(_file, root, fd.get("bild"), f"Figure {name}: bild", IMG_EXT)
            fig.update(typ="bild", bild=str(f) if f else "", freistellen=fd.get("freistellen", True) is not False,
                       blick=str(fd.get("blickrichtung") or "vorne").lower())
            fig["groesse"] = guard(_f, fd.get("groesse"), 1.8, 0.2, 8, f"Figure {name}: groesse") or 1.8
        elif art == "blend":
            f = guard(_file, root, fd.get("datei"), f"Figure {name}: datei", (".blend",))
            fig.update(typ="blend", datei=str(f) if f else "", objekt=str(fd.get("objekt") or "")[:80],
                       aktion=str(fd.get("aktion") or "")[:80])
        else:
            errs.append(f"Figure {name}: art '{art}' unknown. Allowed: {', '.join(FIGUR_ARTEN)}, bild, blend")
            continue
        st = fd.get("stimme") if isinstance(fd.get("stimme"), dict) else {}
        fig["stimme"] = {"lang": str(st.get("lang") or "de")[:5], "voice": str(st.get("voice") or "")[:60],
                         "pitch": st.get("pitch", st.get("tonhoehe")), "rate": st.get("rate", st.get("tempo")),
                         "engine": _engine(st, f"Figure {name}", errs)}
        plan["figuren"][fig["name"]] = fig

    scenes = data.get("szenen")
    if not isinstance(scenes, list) or not scenes:
        errs.append("szenen missing: list of scenes [{\"id\": \"s01\", ...}]")
        scenes = []
    if len(scenes) > MAX_SZENEN:
        errs.append(f"at most {MAX_SZENEN} scenes per script (for more: second file film/teil2.json)")
    plan["szenen"], seen = [], set()
    for i, sc in enumerate(scenes[:MAX_SZENEN]):
        if not isinstance(sc, dict):
            errs.append(f"Scene {i + 1}: must be an object")
            continue
        sid = guard(_sid, sc.get("id") or f"s{i + 1:02d}")
        if not sid:
            continue
        if sid in seen:
            errs.append(f"Scene {sid}: duplicate id")
        seen.add(sid)
        plan["szenen"].append(_norm_scene(root, sc, sid, plan, errs, guard))
    if errs:
        raise ToolError("Script has errors:\n- " + "\n- ".join(errs[:30]))
    return plan


def _norm_scene(root, sc, sid, plan, errs, guard):
    s = {"id": sid, "titel": str(sc.get("titel") or "")[:120]}
    ort = sc.get("ort") if isinstance(sc.get("ort"), dict) else {}
    licht = str(ort.get("licht") or "tag").lower()
    bg = None
    if ort.get("hintergrund"):
        f = guard(_file, root, ort.get("hintergrund"), f"Scene {sid}: hintergrund", IMG_EXT)
        bg = str(f) if f else None
    boden = ort.get("boden", None)
    s["ort"] = {"himmel": _color(ort.get("himmel"), {"tag": "#9fd7ff", "abend": "#f4a582", "nacht": "#1b2a4a"}.get(licht, "#9fd7ff")),
                "boden": None if boden is False or (boden is None and bg) else _color(boden, "#7cc96b"),
                "hintergrund": bg, "licht": licht if licht in LICHT else "tag"}
    s["dauer_min"] = guard(_f, sc.get("dauer"), 3.0, 0.5, MAX_DAUER, f"Scene {sid}: dauer") or 3.0
    s["musik"] = None
    if sc.get("musik"):
        f = guard(_file, root, sc.get("musik"), f"Scene {sid}: musik", AUDIO_EXT)
        s["musik"] = str(f) if f else None
    s["musik_lautstaerke"] = guard(_f, sc.get("musik_lautstaerke"), 0.3, 0, 2, f"Scene {sid}: musik_lautstaerke") or 0.3

    ents = []
    figs = sc.get("figuren") or {}
    if isinstance(figs, list):  # ["Bello", "Mimi"] oder [{"name": ..., "pos": ...}]
        figs = {(x if isinstance(x, str) else str(x.get("name"))): ({} if isinstance(x, str) else x) for x in figs}
    if not isinstance(figs, dict):
        errs.append(f"Scene {sid}: figuren must be an object: {{\"Bello\": {{\"pos\": [-2, 0]}}}}")
        figs = {}
    n = max(1, len(figs))
    for k, (name, fd) in enumerate(figs.items()):
        if name not in plan["figuren"]:
            errs.append(f"Scene {sid}: figure '{name}' is not defined above under figuren")
            continue
        fd = fd if isinstance(fd, dict) else {}
        default = [round((k - (n - 1) / 2) * 2.5, 2), 0]
        blick = str(fd.get("blick") or "vorne").lower()
        ents.append({"id": name, "fig": name, "pos": guard(_pos, fd.get("pos"), default, f"Scene {sid}/{name}") or default,
                     "blick": RICHTUNG.get(blick, 0.0), "sichtbar": fd.get("sichtbar", True) is not False})
    for k, rq in enumerate((sc.get("requisiten") or [])[:40]):
        if not isinstance(rq, dict):
            continue
        typ = str(rq.get("typ") or "").lower()
        if typ not in REQUISITEN:
            errs.append(f"Scene {sid}: prop '{typ}' unknown. Allowed: {', '.join(REQUISITEN)}")
            continue
        e = {"id": str(rq.get("id") or f"{typ}{k + 1}")[:40], "prop": typ, "farbe": _color(rq.get("farbe"), _PROP_COLORS.get(typ, "#999999")),
             "groesse": guard(_f, rq.get("groesse"), 1.0, 0.1, 10, f"Scene {sid}/{typ}: groesse") or 1.0,
             "pos": guard(_pos, rq.get("pos"), [0, 3], f"Scene {sid}/{typ}") or [0, 3], "blick": 0.0, "sichtbar": True}
        if typ == "bild":
            f = guard(_file, root, rq.get("bild"), f"Scene {sid}/bild", IMG_EXT)
            e["bild"] = str(f) if f else ""
        ents.append(e)
    ids = [e["id"] for e in ents]
    if len(ids) != len(set(ids)):
        errs.append(f"Scene {sid}: prop ids and figure names must be unique")
    s["entities"] = ents

    s["aktionen"] = []
    for a in (sc.get("aktionen") or [])[:200]:
        if not isinstance(a, dict):
            continue
        who, what = str(a.get("figur") or a.get("id") or ""), str(a.get("tun") or "").lower()
        if who not in ids:
            errs.append(f"Scene {sid}: action for '{who}', but that does not exist in this scene ({', '.join(ids) or 'empty'})")
            continue
        if what not in AKTIONEN:
            errs.append(f"Scene {sid}: tun '{what}' unknown. Allowed: {', '.join(AKTIONEN)}")
            continue
        act = {"wer": who, "tun": what, "zeit": guard(_f, a.get("zeit"), 0.0, 0, MAX_DAUER, f"Scene {sid}: zeit") or 0.0}
        if a.get("dauer") not in (None, ""):
            act["dauer"] = guard(_f, a.get("dauer"), 1.0, 0.1, 60, f"Scene {sid}: dauer") or 1.0
        if what == "gehen":
            if a.get("nach") is None:
                errs.append(f"Scene {sid}: gehen (walk) needs \"nach\": [x, tiefe]")
                continue
            act["nach"] = guard(_pos, a.get("nach"), [0, 0], f"Scene {sid}: nach") or [0, 0]
        if what == "drehen":
            act["richtung"] = RICHTUNG.get(str(a.get("richtung") or "vorne").lower(), 0.0)
        if what == "springen":
            act["hoehe"] = guard(_f, a.get("hoehe"), 0.8, 0.1, 5, f"Scene {sid}: hoehe") or 0.8
        s["aktionen"].append(act)

    s["dialog"] = []
    for d in (sc.get("dialog") or [])[:60]:
        if not isinstance(d, dict) or not str(d.get("text") or "").strip():
            continue
        who = str(d.get("figur") or "")
        if who and who not in plan["figuren"]:
            errs.append(f"Scene {sid}: dialogue by '{who}', the figure is not defined (leave empty = narrator)")
            continue
        s["dialog"].append({"figur": who, "text": str(d.get("text")).strip()[:600],
                            "pause": guard(_f, d.get("pause"), 0.35, 0, 10, f"Scene {sid}: pause") or 0.35,
                            "zeit": None if d.get("zeit") in (None, "") else guard(_f, d.get("zeit"), 0, 0, MAX_DAUER, f"Scene {sid}: zeit")})
    erz = sc.get("erzaehler_stimme") if isinstance(sc.get("erzaehler_stimme"), dict) else {}
    s["erzaehler"] = {"lang": str(erz.get("lang") or "de")[:5], "voice": str(erz.get("voice") or "")[:60],
                      "pitch": erz.get("pitch"), "rate": erz.get("rate"), "engine": _engine(erz, f"Scene {sid}: erzaehler_stimme", errs)}

    k = sc.get("kamera") if isinstance(sc.get("kamera"), dict) else {}
    ein, bew = str(k.get("einstellung") or "total").lower(), str(k.get("bewegung") or "keine").lower()
    if ein not in EINSTELLUNGEN:
        errs.append(f"Scene {sid}: kamera.einstellung '{ein}' unknown ({', '.join(EINSTELLUNGEN)})")
        ein = "total"
    if bew not in BEWEGUNGEN:
        errs.append(f"Scene {sid}: kamera.bewegung '{bew}' unknown ({', '.join(BEWEGUNGEN)})")
        bew = "keine"
    ziel = str(k.get("ziel") or "")
    if ziel and ziel not in ids:
        errs.append(f"Scene {sid}: kamera.ziel '{ziel}' is not in the scene")
        ziel = ""
    s["kamera"] = {"einstellung": ein, "bewegung": bew, "ziel": ziel}
    return s


_PROP_COLORS = {"baum": "#3f9b3f", "busch": "#4caf50", "haus": "#f2d38b", "stein": "#9e9e9e", "ball": "#e53935",
                "wolke": "#ffffff", "blume": "#ff6fa8", "kiste": "#a0703c", "bild": "#ffffff"}


# ----------------------------------------------------------------------------- Ton
def _engine(st, where, errs):
    """Stimmen-Engine je Figur/Erzaehler (z. B. elevenlabs fuer die Hauptfigur), leer = TTS_ENGINE aus .env."""
    e = str(st.get("engine") or "").strip()
    if not e:
        return ""
    try:
        return T.tts_engine(e)
    except ToolError as ex:
        errs.append(f"{where}: {ex}")
        return ""


def _voice_of(plan, scene, who):
    return plan["figuren"][who]["stimme"] if who else scene["erzaehler"]


def voices(root, plan, scene_ids=None):
    """Vertont alle Dialogzeilen (nur neue/geaenderte). Gibt {szene_id: [zeile...]} mit Datei + Dauer zurueck."""
    tondir = root / "film" / "ton"
    tondir.mkdir(parents=True, exist_ok=True)
    idx_f = tondir / "index.json"
    try:
        idx = json.loads(idx_f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        idx = {}
    out, made = {}, 0
    for sc in plan["szenen"]:
        if scene_ids and sc["id"] not in scene_ids:
            continue
        lines = []
        for n, d in enumerate(sc["dialog"], 1):
            v = _voice_of(plan, sc, d["figur"])
            eng = T.tts_engine(v.get("engine"))
            key, h = f"{sc['id']}_{n:02d}", _hash(d["text"], v, eng)
            f = tondir / f"{key}.mp3"
            if not (f.is_file() and idx.get(key, {}).get("hash") == h):
                res = T.speak(root, d["text"], v["lang"], "", v["voice"], v["pitch"], v["rate"], target=f, engine=eng)
                idx[key] = {"hash": h, "dauer": round(T._probe(f)["duration"], 3)}
                if res.startswith("NOTE"):  # Ersatzstimme: Hash ungueltig, damit sie beim naechsten Mal nachvertont wird
                    idx[key].update(hash="ersatz", ersatz=res.split(", local voice instead")[0][6:])
                made += 1
            lines.append(dict(d, datei=str(f), dauer=idx[key]["dauer"], ersatz=idx[key].get("ersatz", "")))
        out[sc["id"]] = lines
    idx_f.write_text(json.dumps(idx, indent=1), encoding="utf-8")
    return out, made


def timing(scene, lines):
    """Startzeiten der Dialogzeilen und Gesamtdauer der Szene."""
    t, timed = 0.5, []
    for ln in lines:
        start = ln["zeit"] if ln.get("zeit") is not None else t
        timed.append(dict(ln, start=round(start, 3), ende=round(start + ln["dauer"], 3)))
        t = start + ln["dauer"] + ln["pause"]
    acts_end = max([a["zeit"] + _act_dur(a, None) for a in scene["aktionen"]] or [0])
    dur = max(scene["dauer_min"], (timed[-1]["ende"] + 0.6) if timed else 0, acts_end + 0.3)
    return timed, round(min(dur, MAX_DAUER), 3)


def envelope(root, audio, fps):
    """Lautstaerke je Filmbild (0..1) fuer den Mund. Nur ffmpeg, kein numpy."""
    tmp = Path(tempfile.mkdtemp(prefix=".tmp-", dir=root))
    try:
        raw = tmp / "a.raw"
        T._ff(["-i", audio, "-f", "s16le", "-ac", "1", "-ar", "8000", raw], root)
        a = array.array("h")
        a.frombytes(raw.read_bytes()[: (raw.stat().st_size // 2) * 2])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if sys.byteorder == "big":
        a.byteswap()
    step = max(1, int(8000 / fps))
    vals = [math.sqrt(sum(x * x for x in a[i:i + step]) / max(1, len(a[i:i + step]))) for i in range(0, len(a), step)]
    top = sorted(vals)[int(len(vals) * 0.95)] if vals else 0
    if top <= 0:
        return [0.0] * len(vals)
    return [round(min(1.0, max(0.0, (v / top - 0.12) / 0.88)), 3) for v in vals]


def scene_audio(root, scene, timed, dur, dst):
    """Alle Zeilen an ihrer Startzeit + Szenenmusik -> eine WAV-Datei mit genau der Szenenlaenge."""
    args, parts, n = ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=stereo"], [], 1
    for ln in timed:
        args += ["-i", ln["datei"]]
        ms = int(ln["start"] * 1000)
        parts.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[a{n}]")
        n += 1
    if scene.get("musik"):
        args += ["-stream_loop", "-1", "-i", scene["musik"]]
        parts.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,volume={scene['musik_lautstaerke']}[a{n}]")
        n += 1
    labels = "[0:a]" + "".join(f"[a{i}]" for i in range(1, n))
    fc = ";".join(parts + [f"{labels}amix=inputs={n}:duration=first:dropout_transition=0:normalize=0[out]"]) if n > 1 else "[0:a]anull[out]"
    T._ff(args + ["-filter_complex", fc, "-map", "[out]", "-t", f"{dur:.3f}", "-c:a", "pcm_s16le", dst], root)


# ----------------------------------------------------------------------------- Zeitlogik je Bild
def _act_dur(a, fig):
    if "dauer" in a:
        return a["dauer"]
    if a["tun"] == "gehen":
        return 1.0  # echte Dauer haengt vom Startpunkt ab, siehe _walks
    return {"springen": 0.6, "winken": 1.5, "drehen": 0.3, "nicken": 0.8, "erscheinen": 0.4, "verschwinden": 0.4}[a["tun"]]


def _smooth(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def _lerp_angle(a, b, u):
    d = (b - a + 180) % 360 - 180
    return a + d * u


def _walks(ent, acts):
    """Gehwege nacheinander: (start, ende, von, nach, richtung)."""
    pos, out = list(ent["pos"][:2]), []
    for a in sorted((a for a in acts if a["tun"] == "gehen"), key=lambda a: a["zeit"]):
        to = a["nach"][:2]
        dist = math.hypot(to[0] - pos[0], to[1] - pos[1])
        d = a.get("dauer") or max(0.4, dist / WALK_SPEED)
        ang = math.degrees(math.atan2(to[0] - pos[0], -(to[1] - pos[1]))) if dist > 1e-6 else None
        out.append((a["zeit"], a["zeit"] + d, list(pos), list(to), ang))
        pos = list(to)
    return out


def entity_frames(ent, acts, fig, timed, envs, fps, frames):
    """Je Bild: [x, y, z, drehung, skal, skal_z, arm_schwung, winken, nicken, mund, augen, kippen, spiegeln]."""
    acts = sorted((a for a in acts if a["wer"] == ent["id"]), key=lambda a: a["zeit"])
    walks = _walks(ent, acts)
    is_fig = "fig" in ent
    flat = bool(fig and fig.get("typ") == "bild")
    turns = [(a["zeit"], a["richtung"]) for a in acts if a["tun"] == "drehen"]
    seed = (sum(map(ord, ent["id"])) % 97) / 97.0
    talk = [(ln, envs[i]) for i, ln in enumerate(timed) if ent.get("fig") and ln["figur"] == ent["fig"]]
    img_dir = RICHTUNG.get((fig or {}).get("blick", "vorne"), 0.0) if flat else 0.0
    rows = []
    for f in range(frames):
        t = f / fps
        # Position
        x, y = ent["pos"][:2]
        z = ent["pos"][2] if len(ent["pos"]) == 3 else 0.0
        walking, wdir, wphase, wstart = False, None, 0.0, 0.0
        for (s, e, p0, p1, ang) in walks:
            if t >= e:
                x, y = p1
            elif t >= s:
                u = (t - s) / (e - s)
                x, y = p0[0] + (p1[0] - p0[0]) * _smooth(u), p0[1] + (p1[1] - p0[1]) * _smooth(u)
                walking, wdir, wphase, wstart = True, ang, (t - s) * 2.2, s
                break
            else:
                break
        # Richtung
        face = ent["blick"]
        for (s, r) in turns:
            if t >= s:
                face = _lerp_angle(face, r, _smooth((t - s) / 0.3))
        last_walk = max((w for w in walks if w[1] <= t and w[4] is not None), key=lambda w: w[1], default=None)
        if walking and wdir is not None:
            target = max(-70.0, min(70.0, wdir)) if abs(wdir) <= 110 else (180.0 if not flat else wdir)
            rot = _lerp_angle(face, target, _smooth((t - wstart) / 0.15))
        elif last_walk is not None and t - last_walk[1] < 0.35:
            wd = last_walk[4]
            prev = max(-70.0, min(70.0, wd)) if abs(wd) <= 110 else 180.0
            rot = _lerp_angle(prev, face, _smooth((t - last_walk[1]) / 0.35))
        else:
            rot = face
        swing = math.sin(wphase * math.pi * 2) * 28 if (walking and is_fig) else 0.0
        if walking and is_fig:
            z += 0.07 * abs(math.sin(wphase * math.pi * 2))
        scale, sz, wave, nod, tilt = 1.0, 1.0, 0.0, 0.0, 0.0
        for a in acts:
            s, d = a["zeit"], _act_dur(a, fig)
            if not (s <= t):
                continue
            u = (t - s) / d
            if a["tun"] == "springen" and u <= 1:
                z += a["hoehe"] * 4 * u * (1 - u)
                sz *= 1 + 0.08 * math.sin(u * math.pi * 2)
            elif a["tun"] == "winken" and u <= 1:
                env = _smooth(min(u, 1 - u) * 6)
                wave = env * (140 + 25 * math.sin(u * d * math.pi * 6))
                tilt = env * 8 * math.sin(u * d * math.pi * 6) if flat else 0.0
            elif a["tun"] == "nicken" and u <= 1:
                nod = 18 * math.sin(u * math.pi * 4) * (1 - u)
            elif a["tun"] == "erscheinen":
                scale = _smooth(u)
            elif a["tun"] == "verschwinden":
                scale = 1 - _smooth(u)
        if not ent["sichtbar"] and not any(a["tun"] == "erscheinen" and a["zeit"] <= t for a in acts):
            scale = 0.0
        if any(a["tun"] == "erscheinen" for a in acts) and not any(a["tun"] == "erscheinen" and a["zeit"] <= t for a in acts):
            scale = 0.0
        # Sprechen
        mouth = 0.0
        for ln, env in talk:
            if ln["start"] <= t < ln["ende"]:
                i = int((t - ln["start"]) * fps)
                mouth = env[i] if i < len(env) else 0.0
        nod += 5 * mouth
        if flat:
            sz *= 1 + 0.035 * mouth
        # Atmen und Blinzeln
        if is_fig:
            sz *= 1 + 0.015 * math.sin(2 * math.pi * (t / 2.6 + seed))
        blink = ((t + seed * 3.7) % 3.7) < (1.6 / fps)
        eyes = 0.1 if blink else 1.0
        flip = 1.0
        if flat:  # Bildfiguren drehen sich nicht, sie werden gespiegelt
            look = wdir if walking and wdir is not None else rot
            if img_dir and look and (look > 0) != (img_dir > 0) and abs(look) < 135:
                flip = -1.0
            rot = 0.0
        rows.append([round(x, 3), round(y, 3), round(z, 3), round(rot, 2), round(scale, 3), round(sz, 4), round(swing, 2),
                     round(wave, 2), round(nod, 2), mouth, eyes, round(tilt, 2), flip])
    return rows


def camera_frames(scene, ents_rows, fps, frames):
    """Je Bild: [x, y, z, ziel_x, ziel_y, ziel_z, brennweite]."""
    k = scene["kamera"]
    d, h, look = EINSTELLUNGEN[k["einstellung"]]
    ids = [e["id"] for e in scene["entities"]]
    figs = [i for i, e in enumerate(scene["entities"]) if "fig" in e] or list(range(len(ids)))
    tgt = ids.index(k["ziel"]) if k["ziel"] else None
    rows, smooth_x = [], None
    for f in range(frames):
        u = f / max(1, frames - 1)
        if tgt is not None:
            tx, ty = ents_rows[tgt][f][0], ents_rows[tgt][f][1]
        elif figs and ents_rows:
            tx = sum(ents_rows[i][0 if k["bewegung"] == "folgen" else f][0] for i in figs) / len(figs)
            ty = sum(ents_rows[i][0][1] for i in figs) / len(figs)
        else:
            tx, ty = 0.0, 0.0
        if k["bewegung"] != "folgen" and tgt is not None:
            tx, ty = ents_rows[tgt][0][0], ents_rows[tgt][0][1]  # Ziel am Anfang, Kamera bleibt ruhig
        smooth_x = tx if smooth_x is None else smooth_x + (tx - smooth_x) * 0.25
        cx = smooth_x if k["bewegung"] == "folgen" else tx
        dd = d
        if k["bewegung"] == "zoom_rein":
            dd = d * (1.35 - 0.55 * _smooth(u))
        elif k["bewegung"] == "zoom_raus":
            dd = d * (0.8 + 0.55 * _smooth(u))
        elif k["bewegung"] == "schwenk_links":
            cx = tx + 2.5 - 5 * _smooth(u)
        elif k["bewegung"] == "schwenk_rechts":
            cx = tx - 2.5 + 5 * _smooth(u)
        rows.append([round(cx, 3), round(ty - dd, 3), round(h * dd / d if k["bewegung"].startswith("zoom") else h, 3),
                     round(cx, 3), round(ty, 3), look, 35.0])
    return rows


# ----------------------------------------------------------------------------- Bildfiguren freistellen
def cutout(root, src):
    """Einfarbigen Hintergrund (Farbe der Bildecken) transparent machen, Ergebnis in film/.cache/. Bilder mit Alpha bleiben."""
    from PIL import Image, ImageDraw
    cache = root / "film" / ".cache"
    cache.mkdir(parents=True, exist_ok=True)
    dst = cache / f"{Path(src).stem}-{_hash(str(src), _mtime(src))}.png"
    if dst.exists():
        return str(dst)
    im = Image.open(src).convert("RGBA")
    if im.getextrema()[3][0] < 250:  # hat schon Transparenz
        im.save(dst)
        return str(dst)
    im.thumbnail((1024, 1024))
    w, h = im.size
    for corner in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        if im.getpixel(corner)[3]:
            ImageDraw.floodfill(im, corner, (0, 0, 0, 0), thresh=40)
    im.save(dst)
    return str(dst)


# ----------------------------------------------------------------------------- Blender aufrufen
def build_job(root, plan, scene, timed, dur, envs, out_dir, still=None):
    fps = plan["fps"]
    frames = max(1, int(round(dur * fps)))
    ents, rows = [], []
    for e in scene["entities"]:
        fig = plan["figuren"].get(e.get("fig")) if "fig" in e else None
        spec = dict(e)
        if fig:
            spec["figur"] = dict(fig)
            if fig["typ"] == "bild" and fig["bild"]:
                spec["figur"]["bild"] = cutout(root, fig["bild"]) if fig["freistellen"] else fig["bild"]
        r = entity_frames(e, scene["aktionen"], fig, timed, envs, fps, frames)
        rows.append(r)
        ents.append(spec)
    cam = camera_frames(scene, rows, fps, frames)
    if still is not None:
        f = max(0, min(frames - 1, int(still * fps)))
        rows, cam, frames, first = [[r[f]] for r in rows], [cam[f]], 1, f
    else:
        first = 0
    for spec, r in zip(ents, rows):
        spec["frames"] = r
    return {"version": SCRIPT_VERSION, "breite": plan["breite"], "hoehe": plan["hoehe"], "fps": fps, "frames": frames, "erstes": first,
            "renderer": plan["renderer"], "samples": plan["samples"], "umriss": plan["umriss"], "ort": scene["ort"],
            "entities": ents, "kamera": cam, "ausgabe": str(out_dir), "einzelbild": still is not None,
            "threads": int(_env("BLENDER_THREADS", "0") or 0)}


def run_blender(root, job, timeout=None):
    exe = blender_exe()
    if not exe:
        raise ToolError(blender_hint())
    timeout = timeout or int(_env("PCL_BLENDER_TIMEOUT", "3600"))
    tmp = Path(tempfile.mkdtemp(prefix=".tmp-", dir=root))
    try:
        jf = tmp / "job.json"
        jf.write_text(json.dumps(job), encoding="utf-8")
        cmd = [exe, "-b", "--factory-startup", "--disable-autoexec", "-noaudio", "--python-exit-code", "3",
               "--python", str(SCRIPT), "--", str(jf)]
        env = {k: v for k, v in os.environ.items() if not re.search(r"KEY|TOKEN|SECRET|PASSWORD", k, re.I)}  # Blender braucht keine Schluessel
        with T._heavy_lock:  # nie zwei Blender oder Blender + Bildrechner gleichzeitig (8 GB RAM)
            try:
                r = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, encoding="utf-8", errors="replace",
                                   timeout=timeout, env=env)
            except subprocess.TimeoutExpired:
                raise ToolError(f"Blender time limit ({timeout} s). Finished frames are kept: calling render again continues. "
                                "Faster: smaller aufloesung, fps 12, renderer workbench.")
        log = (r.stdout or "") + (r.stderr or "")
        if r.returncode != 0 or "PCL_FERTIG" not in log:
            errs = [ln for ln in log.splitlines() if "PCL_FEHLER" in ln or "Error" in ln or "Traceback" in ln]
            raise ToolError("Blender error: " + ("\n".join(errs[-6:]) or log[-600:]))
        return log
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ----------------------------------------------------------------------------- Operationen
def _scene_ids(plan, call):
    want = call.get("szene") or call.get("szenen")
    all_ids = [s["id"] for s in plan["szenen"]]
    if want in (None, "", "alle", "all"):
        return all_ids
    want = [want] if isinstance(want, str) else list(want)
    bad = [w for w in want if w not in all_ids]
    if bad:
        raise ToolError(f"Scene(s) {', '.join(map(str, bad))} do not exist. Available: {', '.join(all_ids)}")
    return want


def _prep(root, plan, sc, lines):
    timed, dur = timing(sc, lines)
    envs = [envelope(root, ln["datei"], plan["fps"]) for ln in timed]
    return timed, dur, envs


def op_check(root, plan):
    lines, _ = {}, None
    out = [f"Script ok: '{plan['titel']}', {len(plan['figuren'])} figures, {len(plan['szenen'])} scenes, "
           f"{plan['breite']}x{plan['hoehe']} @ {plan['fps']} fps, renderer {plan['renderer']}."]
    total = 0.0
    for sc in plan["szenen"]:
        est = sum(len(d["text"]) / 14.0 + d["pause"] for d in sc["dialog"])
        dur = max(sc["dauer_min"], est + 0.8)
        total += dur
        out.append(f"- {sc['id']}: {len(sc['entities'])} objects, {len(sc['aktionen'])} actions, {len(sc['dialog'])} dialogue lines, approx. {dur:.0f} s")
    exe = blender_exe()
    out.append(f"Estimated length: {total:.0f} s. Blender: {exe or 'NOT found (' + blender_hint() + ')'}")
    return "\n".join(out)


def op_voices(root, plan, call):
    ids = _scene_ids(plan, call)
    got, made = voices(root, plan, ids)
    rows = [f"- {sid}: {len(ls)} lines, {sum(x['dauer'] for x in ls):.1f} s speech" for sid, ls in got.items()]
    ersatz = [x["ersatz"] for ls in got.values() for x in ls if x.get("ersatz")]
    hint = (f"\nNOTE: {len(ersatz)} lines with a local substitute voice, because: " + "; ".join(sorted(set(ersatz)))
            + ". The next op=voices tries again.") if ersatz else ""
    return f"Voices done ({made} newly voiced, rest from the cache) in film/ton/:\n" + "\n".join(rows) + hint


def op_preview(root, plan, call):
    sid = _scene_ids(plan, {"szene": call.get("szene") or plan["szenen"][0]["id"]})[0]
    sc = next(s for s in plan["szenen"] if s["id"] == sid)
    lines = voices(root, plan, [sid])[0][sid]
    timed, dur, envs = _prep(root, plan, sc, lines)
    at = _f(call.get("zeit"), dur / 2, 0, dur, "zeit")
    outdir = root / "film" / "vorschau"
    outdir.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=".tmp-", dir=root))
    try:
        run_blender(root, build_job(root, plan, sc, timed, dur, envs, tmp, still=at), timeout=int(_env("PCL_BLENDER_PREVIEW_TIMEOUT", "900")))
        pngs = sorted(tmp.glob("*.png"))
        if not pngs:
            raise ToolError("Blender wrote no image")
        dst = outdir / f"{sid}.png"
        shutil.move(str(pngs[0]), dst)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return f"Preview: film/vorschau/{sid}.png (scene {sid} at {at:.1f} s of {dur:.1f} s). Look at it and check it with view_image."


def _clip_index(root):
    f = root / "film" / "clips" / "index.json"
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _scene_hash(plan, sc, timed):
    figs = {e["fig"]: plan["figuren"][e["fig"]] for e in sc["entities"] if "fig" in e}
    files = [figs[k].get("bild") or figs[k].get("datei") for k in figs] + [sc["ort"]["hintergrund"], sc.get("musik")] + \
            [e.get("bild") for e in sc["entities"]] + [ln["datei"] for ln in timed]
    keys = {k: plan[k] for k in ("breite", "hoehe", "fps", "renderer", "samples", "umriss")}
    return _hash(SCRIPT_VERSION, keys, sc, figs, [(f, _mtime(f)) for f in files if f])


def render_scene(root, plan, sc, lines, force=False):
    timed, dur, envs = _prep(root, plan, sc, lines)
    clips = root / "film" / "clips"
    clips.mkdir(parents=True, exist_ok=True)
    idx = _clip_index(root)
    h = _scene_hash(plan, sc, timed)
    clip = clips / f"{sc['id']}.mp4"
    if not force and clip.is_file() and idx.get(sc["id"], {}).get("hash") == h:
        return f"{sc['id']}: unchanged, clip film/clips/{sc['id']}.mp4 kept", False
    frames_dir = root / "film" / ".frames" / sc["id"]
    stamp = frames_dir / "hash.txt"
    if frames_dir.exists() and (not stamp.is_file() or stamp.read_text() != h):
        shutil.rmtree(frames_dir, ignore_errors=True)  # alte Bilder einer geaenderten Szene nicht weiterverwenden
    frames_dir.mkdir(parents=True, exist_ok=True)
    stamp.write_text(h)
    t0 = time.time()
    run_blender(root, build_job(root, plan, sc, timed, dur, envs, frames_dir))
    secs = time.time() - t0
    tmp = Path(tempfile.mkdtemp(prefix=".tmp-", dir=root))
    try:
        wav = tmp / "ton.wav"
        scene_audio(root, sc, timed, dur, wav)
        T._ff(["-framerate", plan["fps"], "-i", frames_dir / "%05d.png", "-i", wav, "-map", "0:v", "-map", "1:a",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", plan["fps"],
               "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", "-t", f"{dur:.3f}", "-movflags", "+faststart", clip], root)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(frames_dir, ignore_errors=True)
    idx = _clip_index(root)
    idx[sc["id"]] = {"hash": h, "dauer": dur, "dialog": [{"figur": t["figur"], "text": t["text"], "start": t["start"], "ende": t["ende"]}
                                                          for t in timed], "rendersekunden": round(secs)}
    (clips / "index.json").write_text(json.dumps(idx, indent=1, ensure_ascii=False), encoding="utf-8")
    n = int(round(dur * plan["fps"]))
    return f"{sc['id']}: rendered -> film/clips/{sc['id']}.mp4 ({dur:.1f} s, {n} frames in {secs:.0f} s)", True


def op_render(root, plan, call):
    ids = _scene_ids(plan, call)
    got, _ = voices(root, plan, ids)
    budget = int(_env("PCL_FILM_BUDGET", "2700"))
    t0, out, left = time.time(), [], []
    for sid in ids:
        if out and time.time() - t0 > budget:
            left.append(sid)
            continue
        sc = next(s for s in plan["szenen"] if s["id"] == sid)
        msg, _ = render_scene(root, plan, sc, got[sid], force=bool(call.get("neu")))
        out.append(msg)
    if left:
        out.append(f"Time budget ({budget} s) reached. Still open: {', '.join(left)}. Call render again, finished scenes are skipped.")
    else:
        out.append("All requested scenes done. Next step: op=assemble.")
    return "\n".join(out)


def _srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def op_assemble(root, plan, call):
    idx = _clip_index(root)
    clips_dir = root / "film" / "clips"
    missing = [s["id"] for s in plan["szenen"] if not (clips_dir / f"{s['id']}.mp4").is_file()]
    if missing:
        raise ToolError(f"Clips missing for: {', '.join(missing)}. Run op=render first.")
    tmp = Path(tempfile.mkdtemp(prefix=".tmp-", dir=root))
    try:
        segs, srt, t, n = [], [], 0.0, 1
        if plan["titelkarte"]:
            card = tmp / "titel.mp4"
            font = T._find_font(bold=True)
            txt = tmp / "titel.txt"
            txt.write_text(plan["titel"], encoding="utf-8")
            draw = (f"drawtext=textfile=titel.txt:fontcolor=white:fontsize={plan['hoehe'] // 9}:x=(w-text_w)/2:y=(h-text_h)/2"
                    + (":fontfile=font.ttf" if font else ""))
            if font:
                shutil.copy(font, tmp / "font.ttf")
            d = plan["titelkarte"]
            subprocess_args = ["-f", "lavfi", "-i", f"color=c=0x1b2a4a:s={plan['breite']}x{plan['hoehe']}:r={plan['fps']}:d={d}",
                               "-f", "lavfi", "-t", str(d), "-i", "anullsrc=r=48000:cl=stereo", "-vf", draw,
                               "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                               "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", "-t", str(d), card.name]
            T._ff(subprocess_args, tmp)
            segs.append(card)
            t += d
        for sc in plan["szenen"]:
            segs.append(clips_dir / f"{sc['id']}.mp4")
            info = idx.get(sc["id"]) or {}
            for ln in info.get("dialog", []):
                srt.append(f"{n}\n{_srt_time(t + ln['start'])} --> {_srt_time(t + ln['ende'])}\n"
                           + (f"{ln['figur']}: " if ln["figur"] and call.get("namen") else "") + ln["text"] + "\n")
                n += 1
            t += info.get("dauer") or T._probe(segs[-1])["duration"]
        joined = tmp / "film.mp4"
        T._concat(segs, joined, root, tmp)
        cur = joined
        if plan["musik"]:
            mixed = tmp / "musik.mp4"
            T._ff(["-i", cur, "-stream_loop", "-1", "-i", plan["musik"], "-filter_complex",
                   f"[1:a]volume={plan['musik_lautstaerke']}[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
                   "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", mixed], root)
            cur = mixed
        (tmp / "u.srt").write_text("\n".join(srt), encoding="utf-8")
        if call.get("untertitel") and srt:
            burned = tmp / "ut.mp4"
            T._ff(["-i", cur.name, "-vf", "subtitles=u.srt", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                   "-pix_fmt", "yuv420p", "-c:a", "copy", burned.name], tmp)
            cur = burned
        out = T._out_path(root, call, T._safe_name(plan["titel"], "film"), "mp4")
        shutil.move(str(cur), out)
        if srt:
            shutil.copy(tmp / "u.srt", out.with_suffix(".srt"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    p = T._probe(out)
    return (f"Film done: {_rel(root, out)} ({T._describe_probe(p)})" + (f", subtitles {_rel(root, out.with_suffix('.srt'))}" if srt else "")
            + ". Check: video_edit op=frame for stills, media_info for duration.")


def op_save(root, call):
    data = call.get("film") or call.get("drehbuch")
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except ValueError as e:
            raise ToolError(f"film is not valid JSON: {e}")
    if not isinstance(data, dict):
        raise ToolError("film missing: pass the complete script as a JSON object")
    plan = normalize(root, data)  # erst pruefen, dann speichern
    p = plan_path(root, call)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    return f"Saved: {_rel(root, p)}. " + op_check(root, plan)


def film(root, call):
    op = str(call.get("op") or "check").strip().lower()
    root = Path(root)
    if op == "save":
        return op_save(root, call)
    plan = load_plan(root, call)
    if op == "check":
        return op_check(root, plan)
    if op == "voices":
        return op_voices(root, plan, call)
    if op == "preview":
        return op_preview(root, plan, call)
    if op == "render":
        return op_render(root, plan, call)
    if op == "assemble":
        return op_assemble(root, plan, call)
    raise ToolError("op unknown. Allowed: save, check, voices, preview, render, assemble")
