"""YouTube-Kanal mitverwalten: Upload-Pakete vorbereiten, Terminplan rechnen, Studio-CSV auswerten, nach Freigabe hochladen.

Grundsaetze (Wunsch ABI 2026-11-05, Rahmen aus dem Projekt):
- Vorbereitung (Titel, Beschreibung, Keywords, Hashtags, Terminliste) sind reine Dateien im Projektordner, die der Besitzer prueft.
- Hochladen nur ueber die offizielle YouTube Data API v3 und nur nach ausdruecklicher Bestaetigung JE VIDEO
  (`confirm` muss die Paket-ID sein; app.py legt dafuer immer eine Freigabe an). Kein Browser-Skript, keine Anmeldung per Automatik.
- Ein Upload ist immer `private`; mit Termin setzt YouTube das Video zum Termin selbst auf oeffentlich (`publishAt`).
- Anmeldung macht der Besitzer selbst (OAuth, eigenes Google-Cloud-Projekt). Tokens nur in tokens/youtube-<sprache>.json.
- Auswertung nur aus CSV-Exporten, die der Besitzer aus YouTube Studio herunterlaedt (keine automatische Anmeldung).
- Fremde Videos werden nie heruntergeladen oder neu hochgeladen.

Datei-Schluessel der Kanal-Datei sind Deutsch (wie film.json), alle Ausgaben Englisch.
"""
import base64
import csv
import hashlib
import http.server
import io
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover
    ZoneInfo, ZoneInfoNotFoundError = None, Exception

BASE = Path(__file__).resolve().parent
TIMEOUT = 60
CHUNK = 8 * 1024 * 1024

GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_DEVICE = "https://oauth2.googleapis.com/device/code"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
YT_API = "https://www.googleapis.com/youtube/v3"
YT_UPLOAD = "https://www.googleapis.com/upload/youtube/v3"
# Kleinster Scope fuer Uploads. Der Geraete-Code-Weg erlaubt laut Google nur 'youtube'/'youtube.readonly',
# darum dort der breitere Scope 'youtube' (siehe docs/youtube.md).
SCOPE_UPLOAD = "https://www.googleapis.com/auth/youtube.upload"
SCOPE_DEVICE = "https://www.googleapis.com/auth/youtube"

SPEC_FILE = "youtube/kanal.json"
PKG_DIR = "youtube/packages"
REPORT_DIR = "youtube/reports"

# YouTube-Grenzen (developers.google.com/youtube/v3/docs/videos, support.google.com/youtube/answer/6390658)
TITLE_MAX = 100          # Zeichen, ohne < >
DESC_MAX_BYTES = 5000    # Bytes, ohne < >
TAGS_MAX = 500           # Zeichen inkl. Kommas, Tags mit Leerzeichen zaehlen mit Anfuehrungszeichen
HASHTAGS_IGNORED = 60    # mehr als 60 -> YouTube ignoriert alle
HASHTAGS_ADVISED = 15    # eigene Empfehlung, nicht von YouTube
SHORT_MIN, SHORT_MAX = 45, 60   # Serienformat (Annahme aus dem Serien-Thread)
WEEK_MAX_ADVISED = 3     # anfangs 2-3 Folgen pro Woche
CATEGORY_COMEDY = "23"

LANGS = {
    "de": {"name": "Deutsch", "tz": "Europe/Berlin", "time": "18:00"},
    "en": {"name": "English", "tz": "America/New_York", "time": "17:00"},
    "tr": {"name": "Türkçe", "tz": "Europe/Istanbul", "time": "20:00"},
}
DAYS = {"mo": 0, "mon": 0, "di": 1, "tue": 1, "mi": 2, "wed": 2, "do": 3, "thu": 3, "fr": 4, "fri": 4,
        "sa": 5, "sat": 5, "so": 6, "sun": 6, "pzt": 0, "sal": 1, "çar": 2, "per": 3, "cum": 4, "cmt": 5, "paz": 6}

_lock = threading.Lock()


class YTError(Exception):
    pass


def env(k, d=""):
    return os.environ.get(k, d).strip()


# ------------------------------------------------------------------ Hilfen
def _inside(root, rel):
    root = Path(root).resolve()
    rel = str(rel or "").replace("\\", "/").strip().lstrip("/")
    p = (root / rel).resolve()
    p.relative_to(root)
    if not rel or any(x.startswith(".") for x in p.relative_to(root).parts):
        raise YTError(f"Path '{rel}' is not allowed.")
    return p


def _text(v, lang):
    """Feld je Sprache: {"de": "...", "en": "..."} oder fuer alle gleich als Text."""
    if isinstance(v, dict):
        return str(v.get(lang) or "").strip()
    return str(v or "").strip()


def _list(v, lang):
    if isinstance(v, dict):
        v = v.get(lang) or []
    if isinstance(v, str):
        v = [x for x in re.split(r"[,\n]", v)]
    return [str(x).strip() for x in (v or []) if str(x).strip()]


def _tz(name):
    if ZoneInfo is None:
        raise YTError("zoneinfo is missing (Python 3.9 or newer needed).")
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        raise YTError(f"Unknown time zone '{name}'. On Windows install the package tzdata (pip install tzdata).")


def tags_length(tags):
    """Laenge wie YouTube sie zaehlt: Kommas zwischen den Tags, Tags mit Leerzeichen in Anfuehrungszeichen."""
    return sum(len(t) + (2 if " " in t else 0) for t in tags) + max(0, len(tags) - 1)


def clean_hashtag(h):
    h = str(h or "").strip()
    if not h:
        return ""
    return h if h.startswith("#") else "#" + h


def ep_id(nr, lang):
    return f"ep{int(nr):02d}-{lang}"


# ------------------------------------------------------------------ Kanal-Datei
def template(serie="My series"):
    """Beispiel-Kanaldatei (der Besitzer bzw. die Agenten fuellen sie)."""
    return {
        "serie": serie,
        "sprachen": ["de", "en", "tr"],
        "kanaele": {k: {"name": f"{serie} ({v['name']})", "zeitzone": v["tz"], "uhrzeit": v["time"],
                        "hashtags": ["#Shorts"], "fuss": ""} for k, v in LANGS.items()},
        "rhythmus": {"start": (date.today() + timedelta(days=7)).isoformat(), "tage": ["di", "sa"]},
        "kategorie": CATEGORY_COMEDY,
        "fuer_kinder": False,
        "ki_inhalt": False,
        "folgen": [{"nr": 1,
                    "datei": {"de": "output/ep01-de.mp4", "en": "output/ep01-en.mp4", "tr": "output/ep01-tr.mp4"},
                    "titel": {"de": "", "en": "", "tr": ""},
                    "beschreibung": {"de": "", "en": "", "tr": ""},
                    "keywords": {"de": [], "en": [], "tr": []},
                    "hashtags": {"de": [], "en": [], "tr": []}}],
    }


def load_spec(root, rel=SPEC_FILE):
    f = _inside(root, rel)
    if not f.is_file():
        raise YTError(f"'{rel}' does not exist. Create it first (op 'template').")
    try:
        d = json.loads(f.read_text(encoding="utf-8-sig"))
    except ValueError as e:
        raise YTError(f"'{rel}' is not valid JSON: {e}")
    if not isinstance(d, dict) or not isinstance(d.get("folgen"), list):
        raise YTError(f"'{rel}' needs a list 'folgen'.")
    return d


def langs_of(spec):
    out = [str(x).lower() for x in (spec.get("sprachen") or list(LANGS)) if str(x).strip()]
    return out or ["de"]


def channel(spec, lang):
    c = dict(LANGS.get(lang, {"name": lang, "tz": "UTC", "time": "18:00"}))
    own = (spec.get("kanaele") or {}).get(lang) or {}
    return {"name": own.get("name") or f"{spec.get('serie', 'Channel')} ({c['name']})",
            "tz": own.get("zeitzone") or c["tz"], "time": own.get("uhrzeit") or c["time"],
            "hashtags": [clean_hashtag(h) for h in _list(own.get("hashtags"), lang) if clean_hashtag(h)],
            "footer": str(own.get("fuss") or "").strip()}


# ------------------------------------------------------------------ Terminplan
def _weekdays(rh):
    days = rh.get("tage") or ["di", "sa"]
    out = []
    for d in days:
        if isinstance(d, int) and 0 <= d <= 6:
            out.append(d)
        elif str(d).strip().lower()[:3] in DAYS or str(d).strip().lower()[:2] in DAYS:
            k = str(d).strip().lower()
            out.append(DAYS.get(k[:3], DAYS.get(k[:2])))
        else:
            raise YTError(f"Unknown weekday '{d}' in rhythmus.tage (use mo di mi do fr sa so or mon..sun).")
    return sorted(set(out))


def schedule_dates(rh, count):
    """Termine fuer count Folgen: ab start an den Wochentagen aus rhythmus.tage (anfangs 2-3 pro Woche)."""
    rh = rh or {}
    days = _weekdays(rh)
    try:
        d = date.fromisoformat(str(rh.get("start") or (date.today() + timedelta(days=7)).isoformat()))
    except ValueError:
        raise YTError("rhythmus.start must be a date like 2026-11-17.")
    out = []
    while len(out) < count:
        if d.weekday() in days:
            out.append(d)
        d += timedelta(days=1)
    return out


def publish_at(day, hhmm, tzname):
    """Lokaler Termin -> UTC fuer status.publishAt."""
    try:
        h, m = [int(x) for x in str(hhmm).split(":")[:2]]
    except ValueError:
        raise YTError(f"Time '{hhmm}' must look like 18:00.")
    local = datetime(day.year, day.month, day.day, h, m, tzinfo=_tz(tzname))
    return local, local.astimezone(timezone.utc)


# ------------------------------------------------------------------ Video pruefen
def probe(path):
    """Dauer und Groesse per ffprobe (None, wenn ffprobe fehlt)."""
    exe = shutil.which("ffprobe")
    if not exe:
        return None
    try:
        r = subprocess.run([exe, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
                            "-of", "json", str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        d = json.loads(r.stdout or "{}")
        st = (d.get("streams") or [{}])[0]
        return {"duration": float((d.get("format") or {}).get("duration") or 0), "width": int(st.get("width") or 0),
                "height": int(st.get("height") or 0)}
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def build_description(ep, lang, ch):
    text = _text(ep.get("beschreibung"), lang)
    tags = []
    for h in ch["hashtags"] + [clean_hashtag(x) for x in _list(ep.get("hashtags"), lang)]:
        if h and h.lower() not in [t.lower() for t in tags]:
            tags.append(h)
    parts = [p for p in (text, ch["footer"], " ".join(tags)) if p]
    return "\n\n".join(parts), tags


def check_episode(root, spec, ep, lang, with_video=True):
    """Prueft eine Folge in einer Sprache. Gibt (meta, errors, warnings) zurueck."""
    errs, warns = [], []
    ch = channel(spec, lang)
    nr = ep.get("nr")
    if not isinstance(nr, int) or nr < 1:
        errs.append("'nr' must be a whole number from 1")
        nr = 0
    title = _text(ep.get("titel"), lang)
    desc, hashtags = build_description(ep, lang, ch)
    tags = _list(ep.get("keywords"), lang)
    if not title:
        errs.append("title is missing")
    if len(title) > TITLE_MAX:
        errs.append(f"title has {len(title)} characters, YouTube allows {TITLE_MAX}")
    if len(title) > 60:
        warns.append(f"title has {len(title)} characters; on phones about 40-60 are visible")
    for name, v in (("title", title), ("description", desc)):
        if "<" in v or ">" in v:
            errs.append(f"{name} contains < or >, YouTube does not allow that")
    if len(desc.encode("utf-8")) > DESC_MAX_BYTES:
        errs.append(f"description has {len(desc.encode('utf-8'))} bytes, YouTube allows {DESC_MAX_BYTES}")
    if not _text(ep.get("beschreibung"), lang):
        warns.append("description text is empty (only footer/hashtags)")
    if tags_length(tags) > TAGS_MAX:
        errs.append(f"keywords are {tags_length(tags)} characters long, YouTube allows {TAGS_MAX}")
    if not tags:
        warns.append("no keywords")
    bad = [h for h in hashtags if " " in h or len(h) < 2]
    if bad:
        errs.append("hashtags must not contain spaces: " + ", ".join(bad))
    if len(hashtags) > HASHTAGS_IGNORED:
        errs.append(f"{len(hashtags)} hashtags: above {HASHTAGS_IGNORED} YouTube ignores all of them")
    elif len(hashtags) > HASHTAGS_ADVISED:
        warns.append(f"{len(hashtags)} hashtags; 3-5 good ones work better than many")
    video = _text(ep.get("datei"), lang)
    vpath, info = None, None
    if not video:
        errs.append("video file (datei) is missing")
    else:
        try:
            vpath = _inside(root, video)
        except (YTError, ValueError):
            errs.append(f"video path '{video}' is not allowed")
        if vpath is not None and not vpath.is_file():
            (errs if with_video else warns).append(f"video '{video}' does not exist yet")
        elif vpath is not None:
            info = probe(vpath)
            if info is None:
                warns.append("ffprobe missing: length and format not checked")
            else:
                if not SHORT_MIN - 1 <= info["duration"] <= SHORT_MAX + 1:
                    warns.append(f"video is {info['duration']:.0f} s long, the series format is {SHORT_MIN}-{SHORT_MAX} s")
                if info["width"] and info["height"] and info["height"] <= info["width"]:
                    warns.append(f"video is {info['width']}x{info['height']}, Shorts need portrait 9:16")
    thumb = _text(ep.get("thumbnail"), lang)
    if thumb:
        try:
            tp = _inside(root, thumb)
            if not tp.is_file():
                warns.append(f"thumbnail '{thumb}' does not exist")
            elif tp.suffix.lower() not in (".png", ".jpg", ".jpeg"):
                errs.append("thumbnail must be PNG or JPEG")
        except (YTError, ValueError):
            errs.append(f"thumbnail path '{thumb}' is not allowed")
    body = {
        "snippet": {"title": title, "description": desc, "tags": tags, "categoryId": str(spec.get("kategorie") or CATEGORY_COMEDY),
                    "defaultLanguage": lang, "defaultAudioLanguage": lang},
        "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": bool(spec.get("fuer_kinder", False)),
                   "containsSyntheticMedia": bool(spec.get("ki_inhalt", False)), "embeddable": True},
    }
    meta = {"id": ep_id(nr or 0, lang), "episode": nr, "lang": lang, "channel": ch["name"], "video": video,
            "thumbnail": thumb, "title": title, "hashtags": hashtags, "body": body, "video_info": info}
    return meta, errs, warns


# ------------------------------------------------------------------ Pakete schreiben
def prepare(root, rel=SPEC_FILE, write=True, with_video=False):
    """Baut aus der Kanaldatei je Folge und Sprache ein Upload-Paket, dazu youtube/schedule.csv und youtube/REVIEW.md.
    with_video=True verlangt, dass die Videos schon existieren. Gibt eine Zusammenfassung zurueck."""
    root = Path(root)
    spec = load_spec(root, rel)
    langs = langs_of(spec)
    eps = sorted([e for e in spec["folgen"] if isinstance(e, dict)], key=lambda e: e.get("nr") if isinstance(e.get("nr"), int) else 9999)
    general = []
    nrs = [e.get("nr") for e in eps]
    if len(nrs) != len(set(map(str, nrs))):
        general.append(("error", "episode numbers (nr) are not unique"))
    rh = spec.get("rhythmus") or {}
    try:
        days = _weekdays(rh)
        if len(days) > WEEK_MAX_ADVISED:
            general.append(("warning", f"{len(days)} episodes per week planned; the plan is 2-3 per week at the start"))
        dates = schedule_dates(rh, len(eps))
    except YTError as e:
        general.append(("error", str(e)))
        dates = [None] * len(eps)
    if spec.get("fuer_kinder"):
        general.append(("warning", "fuer_kinder is true: comments and personalised ads are off; the series is meant for adults"))
    rows, items = [], []
    for ep, day in zip(eps, dates):
        for lang in langs:
            meta, errs, warns = check_episode(root, spec, ep, lang, with_video)
            ch = channel(spec, lang)
            local = utc = None
            if day is not None:
                try:
                    local, utc = publish_at(day, ch["time"], ch["tz"])
                except YTError as e:
                    errs.append(str(e))
            if utc is not None:
                if utc <= datetime.now(timezone.utc) + timedelta(hours=1):
                    warns.append("publish time is in the past or within the next hour")
                meta["body"]["status"]["publishAt"] = utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            meta["publish_local"] = local.strftime("%Y-%m-%d %H:%M") if local else ""
            meta["timezone"] = ch["tz"]
            meta["errors"], meta["warnings"] = errs, warns
            items.append(meta)
            rows.append({"date_local": local.strftime("%Y-%m-%d") if local else "", "time_local": local.strftime("%H:%M") if local else "",
                         "weekday": local.strftime("%a") if local else "",
                         "timezone": ch["tz"], "publish_utc": meta["body"]["status"].get("publishAt", ""), "lang": lang,
                         "channel": ch["name"], "episode": meta["episode"], "title": meta["title"], "video": meta["video"],
                         "package": f"{PKG_DIR}/{meta['id']}", "check": "ERROR" if errs else ("warning" if warns else "ok")})
    if write:
        _write_outputs(root, spec, items, rows, general)
    n_err = sum(1 for m in items if m["errors"]) + sum(1 for k, _ in general if k == "error")
    n_warn = sum(1 for m in items if m["warnings"]) + sum(1 for k, _ in general if k == "warning")
    return {"packages": len(items), "errors": n_err, "warnings": n_warn, "general": general, "items": items, "rows": rows}


def _write_outputs(root, spec, items, rows, general):
    pk = root / PKG_DIR
    pk.mkdir(parents=True, exist_ok=True)
    for m in items:
        d = pk / m["id"]
        d.mkdir(exist_ok=True)
        old = {}
        if (d / "package.json").is_file():
            try:
                old = json.loads((d / "package.json").read_text(encoding="utf-8"))
            except ValueError:
                old = {}
        keep = {k: old[k] for k in ("uploaded",) if k in old}  # schon hochgeladen bleibt vermerkt
        data = {k: v for k, v in m.items() if k != "video_info"} | keep
        (d / "package.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        (d / "title.txt").write_text(m["title"] + "\n", encoding="utf-8")
        (d / "description.txt").write_text(m["body"]["snippet"]["description"] + "\n", encoding="utf-8")
        (d / "keywords.txt").write_text(", ".join(m["body"]["snippet"]["tags"]) + "\n", encoding="utf-8")
    cols = ["date_local", "time_local", "weekday", "timezone", "publish_utc", "lang", "channel", "episode", "title", "video", "package", "check"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, delimiter=";")
    w.writeheader()
    w.writerows(rows)
    (root / "youtube" / "schedule.csv").write_text("﻿" + buf.getvalue(), encoding="utf-8")  # BOM: Excel erkennt UTF-8
    (root / "youtube" / "REVIEW.md").write_text(review_text(spec, items, rows, general), encoding="utf-8")


def review_text(spec, items, rows, general):
    out = [f"# {spec.get('serie', 'Series')} – upload review", "",
           f"Created {datetime.now().strftime('%Y-%m-%d %H:%M')}. Nothing has been uploaded. Every upload needs your approval per video.", ""]
    if general:
        out += ["## General", ""] + [f"- **{k}:** {t}" for k, t in general] + [""]
    out += ["## Schedule", "", "| Date | Time | Lang | Ep. | Title | Check |", "|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['date_local']} | {r['time_local']} ({r['timezone']}) | {r['lang']} | {r['episode']} | "
                   f"{r['title'].replace('|', '/')} | {r['check']} |")
    out += ["", "## Packages", ""]
    for m in items:
        s = m["body"]["snippet"]
        out += [f"### {m['id']} · {m['channel']}", "", f"- **Title ({len(m['title'])}/100):** {m['title']}",
                f"- **Publish:** {m['publish_local']} {m['timezone']} (upload stays private until then)",
                f"- **Video:** `{m['video']}`" + (f" · thumbnail `{m['thumbnail']}`" if m["thumbnail"] else ""),
                f"- **Keywords ({tags_length(s['tags'])}/500):** {', '.join(s['tags'])}",
                f"- **Made for kids:** {'yes' if m['body']['status']['selfDeclaredMadeForKids'] else 'no'} · "
                f"**AI/altered content flag:** {'yes' if m['body']['status']['containsSyntheticMedia'] else 'no'}", "",
                "```text", s["description"], "```", ""]
        out += [f"- ❌ {e}" for e in m["errors"]] + [f"- ⚠️ {w}" for w in m["warnings"]] + ([""] if m["errors"] or m["warnings"] else [])
    out += ["## Before you approve an upload", "",
            "- Title, description and keywords read well in this language (no word-for-word translation).",
            "- The video is the final cut, 9:16, 45-60 s, subtitles burned in.",
            "- No names, logos or sounds from other series or films.",
            "- In YouTube Studio: audience 'not made for kids', and the altered/synthetic content question answered correctly.", ""]
    return "\n".join(out)


# ------------------------------------------------------------------ Auswertung (CSV aus YouTube Studio)
# Spaltennamen je Sprache des Studio-Exports. Nicht alle Varianten sind belegt; erkannt wird per Stichwort.
COLS = {
    "content": ["content", "inhalt", "içerik", "video"],
    "title": ["video title", "videotitel", "video başlığı", "titel", "title", "başlık"],
    "published": ["publish time", "veröffentlich", "yayınlanma", "yayın zamanı"],
    "views": ["views", "aufrufe", "görüntüleme"],
    "watch_hours": ["watch time (hours)", "wiedergabezeit (stunden)", "izlenme süresi (saat)"],
    "avg_duration": ["average view duration", "durchschnittliche wiedergabedauer", "ortalama izleme süresi"],
    "avg_percent": ["average percentage viewed", "durchschnittlich angesehen", "ortalama izlenme yüzdesi", "izlenen ortalama yüzde"],
    "stayed": ["stayed to watch", "angesehen statt weggewischt", "weitergesehen", "izlemeye devam"],
    "subscribers": ["subscribers", "abonnenten", "abone"],
    "impressions": ["impressions", "impressionen", "gösterim"],
    "ctr": ["click-through rate", "klickrate", "tıklama oranı"],
    "likes": ["likes", "mag ich", "beğeni"],
    "duration": ["duration", "dauer", "süre"],
}
TOTAL_ROWS = {"total", "gesamt", "summe", "toplam", "insgesamt"}


def _match_cols(header):
    found = {}
    low = [h.strip().lower() for h in header]
    order = ["watch_hours", "avg_duration", "avg_percent", "stayed", "ctr", "impressions", "subscribers", "views", "likes",
             "published", "title", "content", "duration"]
    for key in order:
        for i, h in enumerate(low):
            if i in found.values():
                continue
            if any(k in h for k in COLS[key]):
                if key == "impressions" and any(k in h for k in COLS["ctr"]):
                    continue
                if key == "duration" and any(k in h for k in COLS["avg_duration"]):
                    continue
                found[key] = i
                break
    return found


def _num(s):
    s = str(s or "").strip().replace(" ", "").replace(" ", "").replace("%", "")
    if not s or s in ("-", "—"):
        return None
    if re.fullmatch(r"\d+:\d{2}(:\d{2})?", s):  # Dauer h:mm:ss oder m:ss -> Sekunden
        p = [int(x) for x in s.split(":")]
        return float(p[0] * 3600 + p[1] * 60 + p[2]) if len(p) == 3 else float(p[0] * 60 + p[1])
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".") if re.search(r",\d{1,2}$", s) else s.replace(",", "")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def read_studio_csv(path):
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise YTError("Cannot read the CSV file (unknown encoding).")
    try:
        dialect = csv.Sniffer().sniff(text[:4000], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(io.StringIO(text), dialect))
    rows = [r for r in rows if any(c.strip() for c in r)]
    if len(rows) < 2:
        raise YTError("The CSV file has no data rows.")
    cols = _match_cols(rows[0])
    if "views" not in cols:
        raise YTError("No 'Views' column found. Export 'Table data' from YouTube Studio → Analytics → Advanced mode.")
    out = []
    for r in rows[1:]:
        cell = lambda k: r[cols[k]] if k in cols and cols[k] < len(r) else ""
        name = (cell("content") or "").strip().lower()
        if name in TOTAL_ROWS:
            continue
        v = {k: _num(cell(k)) for k in ("views", "watch_hours", "avg_duration", "avg_percent", "stayed", "subscribers",
                                       "impressions", "ctr", "likes", "duration")}
        v["title"] = (cell("title") or cell("content") or "?").strip()
        v["published"] = cell("published").strip()
        out.append(v)
    return out, sorted(cols)


def analyze(root, rels, write=True):
    """Wertet einen oder mehrere Studio-Exporte aus (z. B. je Kanal einen). Schreibt youtube/reports/analysis-<datum>.md."""
    root = Path(root)
    if isinstance(rels, str):
        rels = [rels]
    sections, summary = [], []
    for rel in rels:
        f = _inside(root, rel)
        if not f.is_file():
            raise YTError(f"'{rel}' does not exist.")
        vids, cols = read_studio_csv(f)
        vids.sort(key=lambda x: x["views"] or 0, reverse=True)
        views = sum(x["views"] or 0 for x in vids)
        ap = [x["avg_percent"] for x in vids if x["avg_percent"] is not None]
        st = [x["stayed"] for x in vids if x["stayed"] is not None]
        subs = sum(x["subscribers"] or 0 for x in vids)
        s = [f"## {rel}", "", f"{len(vids)} videos · {views:,.0f} views · {subs:+,.0f} subscribers" +
             (f" · average viewed {sum(ap) / len(ap):.0f} %" if ap else "") + (f" · stayed to watch {sum(st) / len(st):.0f} %" if st else ""),
             "", f"Columns found: {', '.join(cols)}", "",
             "| # | Title | Views | Avg. viewed % | Stayed % | Avg. duration | Subs |", "|---|---|---|---|---|---|---|"]
        for i, x in enumerate(vids, 1):
            dur = f"{int(x['avg_duration'] // 60)}:{int(x['avg_duration'] % 60):02d}" if x["avg_duration"] is not None else "–"
            pct = "–" if x["avg_percent"] is None else f"{x['avg_percent']:.0f}"
            stay = "–" if x["stayed"] is None else f"{x['stayed']:.0f}"
            s.append(f"| {i} | {x['title'][:60].replace('|', '/')} | {x['views'] or 0:,.0f} | {pct} | {stay} | {dur} | "
                     f"{x['subscribers'] or 0:+,.0f} |")
        s += ["", "**Notes (rules of thumb, not YouTube facts):**", ""] + [f"- {n}" for n in hints(vids)] + [""]
        sections.append("\n".join(s))
        summary.append({"file": rel, "videos": len(vids), "views": views, "subscribers": subs,
                        "avg_percent": round(sum(ap) / len(ap), 1) if ap else None, "top": [x["title"] for x in vids[:3]]})
    text = "\n".join([f"# YouTube analysis {date.today().isoformat()}", "",
                      "Source: CSV exports from YouTube Studio that the owner downloaded. Nothing was fetched from YouTube.", ""] + sections)
    path = ""
    if write:
        d = root / REPORT_DIR
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"analysis-{date.today().isoformat()}.md"
        p.write_text(text, encoding="utf-8")
        path = p.relative_to(root).as_posix()
    return {"report": path, "summary": summary, "text": text}


def hints(vids):
    out = []
    if len(vids) < 5:
        out.append("Fewer than 5 videos: too early for conclusions, keep the rhythm and compare again later.")
    ap = [x for x in vids if x["avg_percent"] is not None]
    if ap:
        avg = sum(x["avg_percent"] for x in ap) / len(ap)
        low = [x["title"][:40] for x in ap if x["avg_percent"] < avg * 0.8]
        high = [x["title"][:40] for x in ap if x["avg_percent"] > avg * 1.2]
        if high:
            out.append("Watched clearly longer than average: " + "; ".join(high[:3]) + ". Check what their first 2 seconds do differently.")
        if low:
            out.append("Watched clearly shorter: " + "; ".join(low[:3]) + ". Check the hook (first sentence, first picture).")
    st = [x for x in vids if x["stayed"] is not None]
    if st and sum(x["stayed"] for x in st) / len(st) < 60:
        out.append("Many viewers swipe away: start with the joke or the problem, not with the set-up.")
    if vids and sum(1 for x in vids if (x["subscribers"] or 0) > 0) <= len(vids) // 3:
        out.append("Few videos bring subscribers: a fixed running gag and the same characters help people recognise the series.")
    return out or ["No conspicuous values."]


# ------------------------------------------------------------------ Anmeldung (OAuth, macht der Besitzer selbst)
def tokens_dir():
    return Path(env("PCL_TOKENS_DIR") or str(BASE / "tokens"))


def _tok_file(lang):
    if not re.fullmatch(r"[a-z]{2,3}", lang or ""):
        raise YTError(f"Unknown channel language '{lang}'.")
    return tokens_dir() / f"youtube-{lang}.json"


def load_token(lang):
    try:
        return json.loads(_tok_file(lang).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_token(lang, data):
    d = tokens_dir()
    d.mkdir(parents=True, exist_ok=True)
    f = _tok_file(lang)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, f)


def logout(lang):
    try:
        _tok_file(lang).unlink()
    except FileNotFoundError:
        pass


def configured():
    return bool(env("YOUTUBE_CLIENT_ID") and env("YOUTUBE_CLIENT_SECRET"))


def logged_in():
    """Sprachen, fuer die ein Kanal angemeldet ist."""
    return sorted(k for k in LANGS if load_token(k).get("refresh_token")) if configured() else []


def _check(r, what):
    if r.status_code >= 400:
        try:
            d = r.json()
            msg = (d.get("error") or {}).get("message") if isinstance(d.get("error"), dict) else d.get("error_description") or d.get("error")
        except ValueError:
            msg = r.text[:200]
        raise YTError(f"{what}: HTTP {r.status_code} {msg or ''}".strip())
    return r


def access_token(lang):
    t = load_token(lang)
    if not t.get("refresh_token"):
        raise YTError(f"Channel '{lang}' is not signed in. On the computer run: python youtube_channel.py login {lang}")
    if t.get("access_token") and t.get("expires", 0) > time.time() + 60:
        return t["access_token"]
    r = requests.post(GOOGLE_TOKEN, data={"client_id": env("YOUTUBE_CLIENT_ID"), "client_secret": env("YOUTUBE_CLIENT_SECRET"),
                                          "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}, timeout=TIMEOUT)
    if r.status_code == 400:
        raise YTError(f"Sign-in for channel '{lang}' has expired (Google project in 'Testing' = 7 days). "
                      f"Run again: python youtube_channel.py login {lang}")
    d = _check(r, "Google sign-in").json()
    t.update(access_token=d["access_token"], expires=time.time() + int(d.get("expires_in", 3600)))
    save_token(lang, t)
    return t["access_token"]


def login_loopback(lang, open_browser=True, port=0):
    """Anmeldung im eigenen Browser auf DIESEM Rechner (Scope youtube.upload). Der Besitzer meldet sich selbst an
    und waehlt den Kanal; das Programm wartet nur auf die Rueckleitung an 127.0.0.1."""
    if not configured():
        raise YTError("YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET are missing in .env (see docs/youtube.md).")
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state = secrets.token_urlsafe(16)
    got = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state", [""])[0] == state:
                got.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<p>Hyperstead: you can close this window now.</p>".encode())

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", port), H)
    redirect = f"http://127.0.0.1:{srv.server_port}"
    url = GOOGLE_AUTH + "?" + urllib.parse.urlencode({
        "client_id": env("YOUTUBE_CLIENT_ID"), "redirect_uri": redirect, "response_type": "code", "scope": SCOPE_UPLOAD,
        "access_type": "offline", "prompt": "consent select_account", "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256"})
    print(f"\nChannel {lang}: open this address in the browser on THIS computer, sign in and choose the {LANGS.get(lang, {}).get('name', lang)} channel:\n\n{url}\n")
    if open_browser:
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass
    srv.timeout = 5
    end = time.time() + 600
    while not got and time.time() < end:
        srv.handle_request()
    srv.server_close()
    if not got.get("code"):
        raise YTError("No sign-in within 10 minutes" + (f" ({got.get('error')})" if got.get("error") else "") + ".")
    r = requests.post(GOOGLE_TOKEN, data={"client_id": env("YOUTUBE_CLIENT_ID"), "client_secret": env("YOUTUBE_CLIENT_SECRET"),
                                          "code": got["code"], "code_verifier": verifier, "grant_type": "authorization_code",
                                          "redirect_uri": redirect}, timeout=TIMEOUT)
    return _store_login(lang, _check(r, "Google sign-in").json(), SCOPE_UPLOAD)


def login_device(lang, out=print):
    """Anmeldung per Geraete-Code (fuer den Pi ohne Bildschirm). Google erlaubt hier nur den breiteren Scope 'youtube'."""
    if not configured():
        raise YTError("YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET are missing in .env (see docs/youtube.md).")
    r = _check(requests.post(GOOGLE_DEVICE, data={"client_id": env("YOUTUBE_CLIENT_ID"), "scope": SCOPE_DEVICE}, timeout=TIMEOUT),
               "Google device code").json()
    out(f"\nChannel {lang}: open {r.get('verification_url') or r.get('verification_uri')} on your phone or PC, "
        f"enter the code  {r['user_code']}  and choose the {LANGS.get(lang, {}).get('name', lang)} channel.\n")
    wait, end = int(r.get("interval", 5)), time.time() + int(r.get("expires_in", 900))
    while time.time() < end:
        time.sleep(wait)
        p = requests.post(GOOGLE_TOKEN, data={"client_id": env("YOUTUBE_CLIENT_ID"), "client_secret": env("YOUTUBE_CLIENT_SECRET"),
                                              "device_code": r["device_code"],
                                              "grant_type": "urn:ietf:params:oauth:grant-type:device_code"}, timeout=TIMEOUT)
        d = p.json() if p.content else {}
        if p.status_code == 200:
            return _store_login(lang, d, SCOPE_DEVICE)
        if d.get("error") == "slow_down":
            wait += 5
        elif d.get("error") != "authorization_pending":
            raise YTError(f"Sign-in failed: {d.get('error') or p.status_code}")
    raise YTError("The code has expired. Start again.")


def _store_login(lang, d, scope):
    if not d.get("refresh_token"):
        raise YTError("Google did not return a refresh token. Remove the app's access in your Google account and sign in again.")
    save_token(lang, {"refresh_token": d["refresh_token"], "access_token": d.get("access_token", ""),
                      "expires": time.time() + int(d.get("expires_in", 3600)), "scope": scope, "since": int(time.time())})
    try:
        ch = whoami(lang)
    except YTError:
        ch = {}
    t = load_token(lang)
    t["channel"] = ch
    save_token(lang, t)
    return ch


def whoami(lang):
    """Kanal hinter dem Token (nur mit Scope 'youtube' lesbar; mit youtube.upload ggf. leer)."""
    r = requests.get(f"{YT_API}/channels", params={"part": "snippet", "mine": "true"},
                     headers={"Authorization": "Bearer " + access_token(lang)}, timeout=TIMEOUT)
    if r.status_code == 403:
        return {}
    items = _check(r, "YouTube channel").json().get("items") or []
    return {"id": items[0]["id"], "title": items[0]["snippet"]["title"]} if items else {}


# ------------------------------------------------------------------ Hochladen (nur nach Bestaetigung je Video)
def package(root, pkg):
    """Liest ein Paket (Pfad youtube/packages/<id> oder nur die id)."""
    root = Path(root)
    pkg = str(pkg or "").strip().rstrip("/")
    if "/" not in pkg:
        pkg = f"{PKG_DIR}/{pkg}"
    d = _inside(root, pkg)
    if not d.relative_to(root.resolve()).as_posix().startswith(PKG_DIR + "/"):
        raise YTError(f"Packages live in {PKG_DIR}/.")
    f = d / "package.json"
    if not f.is_file():
        raise YTError(f"Package '{pkg}' does not exist. Prepare it first (op 'prepare').")
    m = json.loads(f.read_text(encoding="utf-8"))
    return d, m


def upload_check(root, pkg, need_login=True):
    """Prueft vor der Freigabe: Paket ohne Fehler, Video da, noch nicht hochgeladen, Kanal angemeldet."""
    d, m = package(root, pkg)
    if m.get("uploaded"):
        raise YTError(f"{m['id']} was already uploaded: https://youtu.be/{m['uploaded'].get('video_id')}")
    if m.get("errors"):
        raise YTError(f"{m['id']} has errors: " + "; ".join(m["errors"]) + ". Fix the channel file and prepare again.")
    v = _inside(root, m.get("video"))
    if not v.is_file():
        raise YTError(f"Video '{m.get('video')}' does not exist.")
    if need_login and m["lang"] not in logged_in():
        raise YTError(f"Channel '{m['lang']}' is not signed in (python youtube_channel.py login {m['lang']}).")
    return d, m, v


def upload(root, pkg, confirm):
    """Laedt EIN Paket hoch. confirm muss genau die Paket-ID sein (Bestaetigung des Besitzers).
    Immer privat; mit publishAt veroeffentlicht YouTube zum Termin. Gibt (video_id, link) zurueck."""
    with _lock:  # ein Upload gleichzeitig
        d, m, v = upload_check(root, pkg)
        if str(confirm or "").strip() != m["id"]:
            raise YTError(f"Upload of {m['id']} needs the owner's confirmation.")
        body = json.loads(json.dumps(m["body"]))
        body["status"]["privacyStatus"] = "private"  # nie direkt oeffentlich
        pa = body["status"].get("publishAt")
        if pa and datetime.strptime(pa, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
            body["status"].pop("publishAt")  # Termin vorbei: bleibt privat, Besitzer veroeffentlicht selbst
        tok = access_token(m["lang"])
        size = v.stat().st_size
        r = _check(requests.post(f"{YT_UPLOAD}/videos", params={"uploadType": "resumable", "part": "snippet,status"},
                                 headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json; charset=UTF-8",
                                          "X-Upload-Content-Length": str(size), "X-Upload-Content-Type": "video/*"},
                                 data=json.dumps(body), timeout=TIMEOUT), "YouTube upload start")
        url = r.headers.get("Location")
        if not url:
            raise YTError("YouTube did not return an upload address.")
        res = _resumable(url, v, size, tok)
        vid = res.get("id")
        if not vid:
            raise YTError("YouTube did not return a video id.")
        note = ""
        if m.get("thumbnail"):
            try:
                tp = _inside(root, m["thumbnail"])
                with open(tp, "rb") as fh:
                    _check(requests.post(f"{YT_UPLOAD}/thumbnails/set", params={"videoId": vid},
                                         headers={"Authorization": "Bearer " + tok,
                                                  "Content-Type": "image/png" if tp.suffix.lower() == ".png" else "image/jpeg"},
                                         data=fh, timeout=TIMEOUT), "Thumbnail")
            except (YTError, OSError, ValueError) as e:
                note = f" Thumbnail not set ({e}); set it in YouTube Studio."
        m["uploaded"] = {"video_id": vid, "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "publishAt": body["status"].get("publishAt", "")}
        (d / "package.json").write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
        when = f"goes public on {m.get('publish_local')} {m.get('timezone')}" if body["status"].get("publishAt") else "stays private until you publish it"
        return vid, f"https://youtu.be/{vid}", f"▶️ {m['id']} uploaded (private, {when}): https://studio.youtube.com/video/{vid}/edit{note}"


def _resumable(url, path, size, tok):
    """Fortsetzbarer Upload in Stuecken; bei Abbruch wird der Stand abgefragt (308 + Range)."""
    pos, tries = 0, 0
    with open(path, "rb") as fh:
        while True:
            fh.seek(pos)
            chunk = fh.read(CHUNK)
            end = pos + len(chunk) - 1
            try:
                r = requests.put(url, data=chunk, timeout=(30, 600), headers={
                    "Authorization": "Bearer " + tok, "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {pos}-{end}/{size}" if size else "bytes */0"})
            except requests.RequestException:
                r = None
            if r is not None and r.status_code in (200, 201):
                return r.json()
            if r is not None and r.status_code == 308:
                rng = r.headers.get("Range", "")
                pos = int(rng.split("-")[-1]) + 1 if rng else 0
                tries = 0
                continue
            if r is not None and r.status_code == 404:
                raise YTError("The upload session expired. Approve the upload again.")
            if r is not None and r.status_code < 500 and r.status_code != 429:
                _check(r, "YouTube upload")
            tries += 1
            if tries > 5:
                raise YTError("YouTube upload failed several times. Try again later.")
            time.sleep(min(60, 2 ** tries))
            s = requests.put(url, headers={"Authorization": "Bearer " + tok, "Content-Range": f"bytes */{size}",
                                           "Content-Length": "0"}, timeout=60)
            if s.status_code in (200, 201):
                return s.json()
            rng = s.headers.get("Range", "") if s.status_code == 308 else ""
            pos = int(rng.split("-")[-1]) + 1 if rng else 0


# ------------------------------------------------------------------ Werkzeug-Text fuer Agenten
def doc(signed_in):
    up = (f" Signed-in channels: {', '.join(signed_in)}." if signed_in else
          " No channel is signed in yet, so 'upload' is not possible; tell the owner (guide docs/youtube.md).")
    return ('  {"tool": "youtube", "op": "template|check|prepare|analyze|upload", ...}  YouTube channel work (files only, the owner reviews):\n'
            f'    op "template" {{"serie": "name"}}: writes an example {SPEC_FILE} if it does not exist. Fill it: per episode nr, datei (video per '
            'language), titel, beschreibung, keywords, hashtags (each as {"de": ..., "en": ..., "tr": ...}); rhythmus.start + rhythmus.tage '
            '(2-3 days per week at the start); kanaele per language (name, zeitzone, uhrzeit, hashtags, fuss).\n'
            f'    op "check": checks {SPEC_FILE} against YouTube limits without writing.\n'
            f'    op "prepare": writes one package per episode and language to {PKG_DIR}/<id>/, youtube/schedule.csv and youtube/REVIEW.md.\n'
            '    op "analyze" {"path": "input/Table data.csv"} (or "paths": [...]): evaluates CSV exports from YouTube Studio that the owner '
            f'uploaded; report in {REPORT_DIR}/. Never claim numbers that are not in the CSV.\n'
            '    op "upload" {"package": "ep01-de"}: asks the owner to approve uploading ONE prepared package (always private, scheduled). '
            'Only when the assignment asks for it.' + up + "\n"
            "    Never download or re-upload other people's videos. Write titles/descriptions in the channel's language, adapt jokes instead of "
            "translating word for word, no names from other series.")


def run(root, call):
    """Alle Ops ausser 'upload' (das braucht die Freigabe in app.py). Gibt (text, erzeugte_datei|None) zurueck."""
    op = str(call.get("op") or "").strip().lower()
    root = Path(root)
    try:
        if op == "template":
            f = root / SPEC_FILE
            if f.exists():
                return f"NOTE: {SPEC_FILE} already exists, not overwritten. Edit it with write_file.", None
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(template(str(call.get("serie") or "My series")), ensure_ascii=False, indent=2), encoding="utf-8")
            return f"Written: {SPEC_FILE}. Fill in the episodes, then run op 'prepare'.", SPEC_FILE
        if op in ("check", "prepare"):
            res = prepare(root, str(call.get("spec") or SPEC_FILE), write=(op == "prepare"))
            lines = [f"{res['packages']} packages, {res['errors']} with errors, {res['warnings']} with warnings."]
            lines += [f"- {k}: {t}" for k, t in res["general"]]
            for m in res["items"]:
                for e in m["errors"]:
                    lines.append(f"- {m['id']} ERROR: {e}")
                for w in m["warnings"][:3]:
                    lines.append(f"- {m['id']} warning: {w}")
            if op == "prepare":
                lines.append(f"Written: {PKG_DIR}/, youtube/schedule.csv, youtube/REVIEW.md (nothing uploaded).")
            return "\n".join(lines[:60]), ("youtube/REVIEW.md" if op == "prepare" else None)
        if op == "analyze":
            paths = call.get("paths") or [call.get("path")]
            res = analyze(root, [p for p in paths if p])
            return res["text"][:4000], res["report"]
        return f"ERROR: unknown op '{op}' (template, check, prepare, analyze, upload).", None
    except (YTError, ValueError, OSError) as e:
        return f"ERROR: {e}", None


# ------------------------------------------------------------------ Kommandozeile (Anmeldung und Pruefung durch den Besitzer)
def _load_env():
    f = BASE / ".env"
    if f.is_file():
        for line in f.read_text(encoding="utf-8-sig").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main(argv):
    _load_env()
    usage = ("usage:\n  python youtube_channel.py login <de|en|tr> [--device]\n  python youtube_channel.py logout <lang>\n"
             "  python youtube_channel.py status\n  python youtube_channel.py prepare <project folder>\n"
             "  python youtube_channel.py analyze <project folder> <csv in project>\n"
             "  python youtube_channel.py upload <project folder> <package id>   (asks you to type the id)")
    if not argv:
        print(usage)
        return 2
    cmd = argv[0]
    try:
        if cmd == "login" and len(argv) >= 2:
            lang = argv[1].lower()
            ch = login_device(lang) if "--device" in argv else login_loopback(lang)
            print(f"Signed in: channel {lang}" + (f" = {ch.get('title')}" if ch.get("title") else "") + f". Token: {_tok_file(lang)}")
        elif cmd == "logout" and len(argv) >= 2:
            logout(argv[1].lower())
            print("Signed out.")
        elif cmd == "status":
            print("Client in .env: " + ("yes" if configured() else "no (YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET)"))
            for k in LANGS:
                t = load_token(k)
                age = (time.time() - t.get("since", time.time())) / 86400
                print(f"  {k}: " + (f"signed in {age:.0f} days ago" + (f" ({t['channel'].get('title')})" if t.get("channel") else "")
                                    if t.get("refresh_token") else "not signed in"))
        elif cmd == "prepare" and len(argv) >= 2:
            print(run(argv[1], {"op": "prepare"})[0])
        elif cmd == "analyze" and len(argv) >= 3:
            print(run(argv[1], {"op": "analyze", "paths": argv[2:]})[0])
        elif cmd == "upload" and len(argv) >= 3:
            d, m, v = upload_check(argv[1], argv[2])
            print(f"\n{m['id']} · {m['channel']}\nTitle: {m['title']}\nVideo: {m['video']} ({v.stat().st_size / 1048576:.1f} MB)\n"
                  f"Publish: {m.get('publish_local') or 'stays private'} {m.get('timezone', '')}\n")
            ok = input(f"Type {m['id']} to upload this video: ").strip()
            print(upload(argv[1], argv[2], ok)[2])
        else:
            print(usage)
            return 2
    except YTError as e:
        print("ERROR:", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
