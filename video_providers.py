"""KI-Videoanbieter fuer das Werkzeug video_generate und die Zusatzwerkzeuge video_ai / sound_generate.

Jeder Anbieter ist eine Funktion gen(keys, model, call, root, deadline) -> (bytes|None, url|None, download_headers|None, fortsetzen_id|None).
Alle laufen nach demselben Muster: Auftrag abschicken, alle POLL Sekunden nachfragen, fertige Datei herunterladen.
Nur gegen simulierte Antworten getestet (tests/test_video_providers.py), echte Keys zuerst mit selftest.py pruefen.
"""
import base64
import hashlib
import hmac
import io
import json
import re
import time
from urllib.parse import urljoin, urlparse

import requests

import agent_tools as T
from agent_tools import ToolError

POLL = 10

# Anbieter -> (Pflicht-Variablen in .env, Standardmodell Text-zu-Video, Standardmodell Bild-zu-Video oder None = gleiches Modell)
VIDEO = {
    "gemini": (("GEMINI_API_KEY",), "gemini-omni-1.1-flash", None),
    "openai": (("OPENAI_API_KEY",), "sora-2", None),
    "openrouter": (("OPENROUTER_API_KEY",), "google/veo-3.1", None),
    "runway": (("RUNWAYML_API_SECRET",), "gen4.5", None),
    "luma": (("LUMAAI_API_KEY",), "ray-2", None),
    "kling": (("KLING_ACCESS_KEY", "KLING_SECRET_KEY"), "kling-v2-5-turbo", None),
    "minimax": (("MINIMAX_API_KEY",), "MiniMax-Hailuo-2.3", None),
    "wan": (("DASHSCOPE_API_KEY",), "wan2.2-t2v-plus", "wan2.2-i2v-plus"),
    "seedance": (("ARK_API_KEY",), "seedance-1-0-pro-250528", None),
    "higgsfield": (("HIGGSFIELD_API_KEY",), "minimax/h3/text-to-video", "minimax/h3/image-to-video"),
    "fal": (("FAL_KEY",), "minimax/h3-max/text-to-video", "fal-ai/wan/v2.2-a14b/image-to-video"),  # H3 Max: 0,03 $/s (fal.ai/pricing)
    "replicate": (("REPLICATE_API_TOKEN",), "wan-video/wan-2.2-t2v-fast", "wan-video/wan-2.2-i2v-fast"),
}


def providers():
    """Eingeschaltete Videoanbieter in der Reihenfolge aus VIDEO_PROVIDER (der erste ist Standard)."""
    out = []
    for p in re.split(r"[\s,;]+", T._env("VIDEO_PROVIDER").lower()):
        if p in VIDEO and p not in out:
            out.append(p)
    return out


def keys_of(prov):
    if prov == "higgsfield":  # Higgsfield: Key-ID und Secret, wahlweise als HIGGSFIELD_API_KEY=id:secret
        kid, sec = T._env("HIGGSFIELD_API_KEY_ID"), T._env("HIGGSFIELD_API_KEY_SECRET")
        k = f"{kid}:{sec}" if kid and sec else T._env("HIGGSFIELD_API_KEY")
        if ":" not in k:
            raise ToolError("VIDEO_PROVIDER=higgsfield, but HIGGSFIELD_API_KEY_ID and HIGGSFIELD_API_KEY_SECRET are missing")
        return (k,)
    vals = []
    for k in VIDEO[prov][0]:
        v = T._env(k).split(",")[0].strip()
        if not v:
            raise ToolError(f"VIDEO_PROVIDER={prov}, but {k} is missing in .env")
        vals.append(v)
    return tuple(vals)


def model_of(prov, image, default_prov):
    """<ANBIETER>_VIDEO_MODEL, fuer den Standardanbieter auch das alte VIDEO_MODEL; Bild-zu-Video eigene Variable, wo es eigene Modelle gibt."""
    p = prov.upper()
    t2v, i2v = VIDEO[prov][1], VIDEO[prov][2]
    base = T._model_env(f"{p}_VIDEO_MODEL", T._model_env("VIDEO_MODEL", t2v) if prov == default_prov else t2v)
    if "/" in t2v and "/" not in base:  # Endpunkt-Anbieter (fal, openrouter ...): ein Gemini-Name wie veo-3.1 gilt hier nicht
        base = t2v
    if image and i2v:  # eigene Bild-zu-Video-Endpunkte: ein Text-Modell kann kein Startbild
        return T._model_env(f"{p}_I2V_MODEL", i2v)
    return base


# --------------------------------------------------------------------------- Hilfen
def _json(r, who):
    try:
        d = r.json()
    except ValueError:
        d = {}
    if r.status_code >= 400:
        raise ToolError(f"{who} answers with HTTP {r.status_code}: " + T._clip(_errmsg(d) or r.text, 300))
    return d if isinstance(d, dict) else {"data": d}


def _errmsg(d):
    if not isinstance(d, dict):
        return ""
    for k in ("error", "detail", "message", "failure", "failure_reason", "task_status_msg"):
        v = d.get(k)
        if isinstance(v, dict):
            v = v.get("message") or v.get("msg") or json.dumps(v)
        if isinstance(v, list):
            v = json.dumps(v)
        if v:
            return str(v)
    br = d.get("base_resp") or {}
    return br.get("status_msg", "") if br.get("status_code") else ""


def _wait(deadline):
    if time.time() > deadline:
        raise ToolError("Time limit for video generation reached (PCL_VIDEO_TIMEOUT)")
    time.sleep(POLL)


def _seconds(call, lo=1, hi=60):
    try:
        s = int(float(call.get("seconds") or 0))
    except (TypeError, ValueError):
        raise ToolError("seconds must be a number")
    return max(lo, min(s, hi)) if s else None


def _aspect(call):
    a = str(call.get("aspect") or "").strip()
    if a and a not in ("16:9", "9:16", "1:1"):
        raise ToolError("aspect must be 16:9, 9:16 or 1:1")
    return a or None


def _prompt(call, n=2000):
    return str(call.get("prompt") or "").strip()[:n]


def image_input(root, ref):
    """Startbild: Datei im Projekt -> (mime, rohdaten, data-URL); oeffentliche https-Adresse -> (None, None, url)."""
    ref = str(ref or "").strip()
    if not ref:
        return None
    if ref.startswith("https://"):
        T.check_public(urlparse(ref).hostname)
        return None, None, ref
    f = T._inside_existing(root, ref)
    data = f.read_bytes()
    mime = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}.get(T._sniff(data))
    if not mime:
        raise ToolError(f"'{ref}' is not an image (PNG, JPEG, WEBP)")
    return mime, data, f"data:{mime};base64," + base64.b64encode(data).decode()


def media_input(root, rel, kinds=("video", "audio"), max_mb=50):
    """Video/Audio aus dem Projekt als data-URL (fal nimmt data-URLs als Datei an)."""
    f = T._inside_existing(root, rel)
    size = f.stat().st_size
    if size > max_mb * 1_000_000:
        raise ToolError(f"'{rel}' is larger than {max_mb} MB, shorten or shrink it with video_edit first")
    ext = f.suffix.lower().lstrip(".")
    mime = {"mp4": "video/mp4", "mov": "video/quicktime", "webm": "video/webm", "mp3": "audio/mpeg", "wav": "audio/wav",
            "m4a": "audio/mp4", "ogg": "audio/ogg"}.get(ext)
    if not mime or mime.split("/")[0] not in kinds:
        raise ToolError(f"'{rel}' has no suitable format ({', '.join(kinds)})")
    return f"data:{mime};base64," + base64.b64encode(f.read_bytes()).decode()


def save_url(url, dst, headers=None, limit=None):
    """Ergebnis herunterladen: nur https und oeffentliche Hosts, jede Weiterleitung gepruefte, Zugangsdaten nur an den ersten Host."""
    limit = limit or T.MAX_VIDEO_BYTES
    host0 = urlparse(url).hostname
    for _ in range(6):
        u = urlparse(url)
        if u.scheme != "https":
            raise ToolError("Provider returned no https address for the result")
        T.check_public(u.hostname)
        h = dict(headers or {}) if u.hostname == host0 else {}
        with requests.get(url, headers=h, stream=True, timeout=300, allow_redirects=False) as r:
            if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("Location"):
                url = urljoin(url, r.headers["Location"])
                continue
            if r.status_code >= 400:
                raise ToolError(f"Downloading the result failed (HTTP {r.status_code})")
            size = 0
            with open(dst, "wb") as fh:
                for chunk in r.iter_content(1 << 16):
                    size += len(chunk)
                    if size > limit:
                        raise ToolError("Result is too large")
                    fh.write(chunk)
            return
    raise ToolError("Too many redirects during download")


def find_url(d, prefer=("video", "videos", "output", "audio", "audio_file", "file")):
    """Erste Ergebnis-URL aus typischen Antworten ({video: {url}}, {videos: [{url}]}, {output: "https://..."})."""
    if isinstance(d, str):
        return d if d.startswith("https://") else None
    if isinstance(d, list):
        for x in d:
            u = find_url(x, prefer)
            if u:
                return u
        return None
    if isinstance(d, dict):
        for k in prefer + ("url",):
            if k in d:
                u = find_url(d[k], prefer)
                if u:
                    return u
    return None


def _extra(prov):
    """<ANBIETER>_VIDEO_PARAMS bzw. VIDEO_PARAMS = JSON mit Zusatzfeldern (Modelle bei fal/replicate/openrouter/higgsfield haben eigene Parameter)."""
    name = f"{prov.upper()}_VIDEO_PARAMS" if T._env(f"{prov.upper()}_VIDEO_PARAMS") else "VIDEO_PARAMS"
    raw = T._env(name)
    if not raw:
        return {}
    try:
        d = json.loads(raw)
    except ValueError:
        raise ToolError(f"{name} in .env is not valid JSON")
    return d if isinstance(d, dict) else {}


# --------------------------------------------------------------------------- Anbieter
def gen_gemini(keys, model, call, root, deadline):
    gen = T._veo_video if model.startswith("veo") else T._omni_video
    data, uri, iid = gen(keys[0], model, call, root, deadline)
    return data, uri, {"x-goog-api-key": keys[0]}, iid


def _fit_image(data, size):
    """Sora verlangt ein Startbild in genau der Videogroesse: mittig zuschneiden und skalieren."""
    from PIL import Image, ImageOps
    w, h = (int(x) for x in size.split("x"))
    im = ImageOps.fit(Image.open(io.BytesIO(data)).convert("RGB"), (w, h))
    out = io.BytesIO()
    im.save(out, "PNG")
    return out.getvalue()


def gen_openai(keys, model, call, root, deadline):
    base = T._env("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    h = {"Authorization": "Bearer " + keys[0]}
    hoch = _aspect(call) == "9:16"
    big = call.get("resolution") == "1080p" and "pro" in model
    size = ("1024x1792" if hoch else "1792x1024") if big else ("720x1280" if hoch else "1280x720")
    s = _seconds(call)
    if call.get("continue_id"):  # Remix eines frueheren Sora-Videos
        vid = re.sub(r"[^\w-]", "", str(call["continue_id"]))[:100]
        d = _json(requests.post(f"{base}/videos/{vid}/remix", headers=h, json={"prompt": _prompt(call)}, timeout=120), "OpenAI Sora")
    else:
        fields = {"model": model, "prompt": _prompt(call), "size": size}
        if s:
            fields["seconds"] = str(min((4, 8, 12), key=lambda x: abs(x - s)))
        files = None
        img = image_input(root, call.get("image"))
        if img:
            if not img[1]:
                raise ToolError("Sora takes start images only from the project folder (e.g. assets/figure.png)")
            files = {"input_reference": ("start.png", _fit_image(img[1], size), "image/png")}
        d = _json(requests.post(f"{base}/videos", headers=h, data=fields, files=files, timeout=120), "OpenAI Sora")
    vid = d.get("id")
    while d.get("status") not in ("completed", "failed"):
        _wait(deadline)
        d = _json(requests.get(f"{base}/videos/{vid}", headers=h, timeout=60), "OpenAI Sora")
    if d["status"] == "failed":
        raise ToolError("Sora did not create a video: " + T._clip(_errmsg(d) or "unknown error", 300))
    return None, f"{base}/videos/{vid}/content", h, vid


def gen_openrouter(keys, model, call, root, deadline):
    base = T._env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
    h = {"Authorization": "Bearer " + keys[0]}
    body = {"model": model, "prompt": _prompt(call)}
    if _aspect(call):
        body["aspect_ratio"] = _aspect(call)
    if call.get("resolution") in ("480p", "720p", "1080p"):
        body["resolution"] = call["resolution"]
    if _seconds(call):
        body["duration"] = _seconds(call)
    img = image_input(root, call.get("image"))
    if img:
        body["frame_images"] = [{"type": "image_url", "image_url": {"url": img[2]}, "frame_type": "first_frame"}]
    body.update(_extra("openrouter"))
    d = _json(requests.post(base + "/videos", headers=h, json=body, timeout=120), "OpenRouter-Video")
    poll = d.get("polling_url") or f"{base}/videos/{d.get('id')}"
    while d.get("status") not in ("completed", "failed", "cancelled", "expired"):
        _wait(deadline)
        d = _json(requests.get(poll, headers=h, timeout=60), "OpenRouter-Video")
    if d["status"] != "completed":
        raise ToolError(f"OpenRouter ({model}): Video {d['status']}: " + T._clip(_errmsg(d), 300))
    urls = d.get("unsigned_urls") or []
    return None, urls[0] if urls else f"{base}/videos/{d.get('id')}/content?index=0", h, None


def gen_runway(keys, model, call, root, deadline):
    base = T._env("RUNWAY_BASE_URL", "https://api.dev.runwayml.com").rstrip("/")
    h = {"Authorization": "Bearer " + keys[0], "X-Runway-Version": T._env("RUNWAY_API_VERSION", "2024-11-06")}
    a = _aspect(call)
    body = {"model": model, "promptText": _prompt(call, 1000),
            "ratio": {"9:16": "720:1280", "1:1": "960:960"}.get(a, "1280:720"), "duration": _seconds(call, 2, 10) or 5}
    img = image_input(root, call.get("image"))
    if img:
        body["promptImage"] = img[2]
    d = _json(requests.post(f"{base}/v1/{'image_to_video' if img else 'text_to_video'}", headers=h, json=body, timeout=120), "Runway")
    tid = d.get("id")
    while d.get("status") not in ("SUCCEEDED", "FAILED", "CANCELLED"):
        _wait(deadline)
        d = _json(requests.get(f"{base}/v1/tasks/{tid}", headers=h, timeout=60), "Runway")
    if d["status"] != "SUCCEEDED":
        raise ToolError("Runway did not create a video: " + T._clip(_errmsg(d) or d["status"], 300))
    return None, find_url(d.get("output")), None, None


def gen_luma(keys, model, call, root, deadline):
    base = T._env("LUMA_BASE_URL", "https://api.lumalabs.ai/dream-machine/v1").rstrip("/")
    h = {"Authorization": "Bearer " + keys[0]}
    body = {"prompt": _prompt(call), "model": model, "aspect_ratio": _aspect(call) or "16:9"}
    if call.get("resolution") in ("540p", "720p", "1080p", "4k"):
        body["resolution"] = call["resolution"]
    if _seconds(call):
        body["duration"] = "9s" if _seconds(call) > 6 else "5s"
    img = image_input(root, call.get("image"))
    if img:
        if img[1]:
            raise ToolError("Luma takes start images only as a public https address, not from the project folder")
        body["keyframes"] = {"frame0": {"type": "image", "url": img[2]}}
    d = _json(requests.post(base + "/generations", headers=h, json=body, timeout=120), "Luma")
    gid = d.get("id")
    while d.get("state") not in ("completed", "failed"):
        _wait(deadline)
        d = _json(requests.get(f"{base}/generations/{gid}", headers=h, timeout=60), "Luma")
    if d["state"] == "failed":
        raise ToolError("Luma did not create a video: " + T._clip(_errmsg(d) or "unknown error", 300))
    return None, ((d.get("assets") or {}).get("video")), None, None


def kling_token(ak, sk, now=None):
    """Kling verlangt ein kurzlebiges JWT (HS256) aus Access Key und Secret Key."""
    now = int(now or time.time())

    def b64(o):
        return base64.urlsafe_b64encode(json.dumps(o, separators=(",", ":")).encode()).rstrip(b"=")
    msg = b64({"alg": "HS256", "typ": "JWT"}) + b"." + b64({"iss": ak, "exp": now + 1800, "nbf": now - 5})
    sig = base64.urlsafe_b64encode(hmac.new(sk.encode(), msg, hashlib.sha256).digest()).rstrip(b"=")
    return (msg + b"." + sig).decode()


def gen_kling(keys, model, call, root, deadline):
    base = T._env("KLING_BASE_URL", "https://api-singapore.klingai.com").rstrip("/")
    h = {"Authorization": "Bearer " + kling_token(*keys)}
    img = image_input(root, call.get("image"))
    kind = "image2video" if img else "text2video"
    body = {"model_name": model, "prompt": _prompt(call, 2500), "mode": T._env("KLING_MODE", "std"),
            "duration": "10" if (_seconds(call) or 5) > 7 else "5"}
    if img:
        body["image"] = img[2] if not img[1] else base64.b64encode(img[1]).decode()  # Kling: Base64 ohne data:-Vorspann
    else:
        body["aspect_ratio"] = _aspect(call) or "16:9"
    d = _json(requests.post(f"{base}/v1/videos/{kind}", headers=h, json=body, timeout=120), "Kling")
    if d.get("code") not in (0, None):
        raise ToolError("Kling: " + T._clip(d.get("message") or json.dumps(d), 300))
    tid = (d.get("data") or {}).get("task_id")
    st = "submitted"
    while st not in ("succeed", "failed"):
        _wait(deadline)
        h = {"Authorization": "Bearer " + kling_token(*keys)}
        d = _json(requests.get(f"{base}/v1/videos/{kind}/{tid}", headers=h, timeout=60), "Kling")
        data = d.get("data") or {}
        st = data.get("task_status")
    if st == "failed":
        raise ToolError("Kling did not create a video: " + T._clip(data.get("task_status_msg") or "unknown error", 300))
    return None, find_url((data.get("task_result") or {}).get("videos")), None, None


def gen_minimax(keys, model, call, root, deadline):
    base = T._env("MINIMAX_BASE_URL", "https://api.minimax.io").rstrip("/")
    h = {"Authorization": "Bearer " + keys[0]}
    body = {"model": model, "prompt": _prompt(call)}
    if _seconds(call):
        body["duration"] = 10 if _seconds(call) > 7 else 6
    if call.get("resolution") in ("768p", "1080p", "720p"):
        body["resolution"] = call["resolution"].upper()
    img = image_input(root, call.get("image"))
    if img:
        body["first_frame_image"] = img[2]
    d = _json(requests.post(base + "/v1/video_generation", headers=h, json=body, timeout=120), "MiniMax")
    if (d.get("base_resp") or {}).get("status_code"):
        raise ToolError("MiniMax: " + T._clip(_errmsg(d), 300))
    tid, st = d.get("task_id"), ""
    while st not in ("success", "fail"):
        _wait(deadline)
        d = _json(requests.get(base + "/v1/query/video_generation", params={"task_id": tid}, headers=h, timeout=60), "MiniMax")
        st = str(d.get("status") or "").lower()
    if st == "fail":
        raise ToolError("MiniMax did not create a video: " + T._clip(_errmsg(d) or "unknown error", 300))
    f = _json(requests.get(base + "/v1/files/retrieve", params={"file_id": d.get("file_id")}, headers=h, timeout=60), "MiniMax")
    return None, (f.get("file") or {}).get("download_url"), None, None


def gen_wan(keys, model, call, root, deadline):
    base = T._env("DASHSCOPE_BASE_URL", "https://dashscope-intl.aliyuncs.com").rstrip("/")
    h = {"Authorization": "Bearer " + keys[0], "X-DashScope-Async": "enable"}
    img = image_input(root, call.get("image"))
    inp, par = {"prompt": _prompt(call, 800)}, {"prompt_extend": True}
    hd = call.get("resolution") != "720p"
    if img:
        inp["img_url"] = img[2]
        par["resolution"] = "1080P" if hd else "720P"
    else:
        w, hh = (1920, 1080) if hd else (1280, 720)
        a = _aspect(call)
        par["size"] = f"{hh}*{w}" if a == "9:16" else (f"{hh}*{hh}" if a == "1:1" else f"{w}*{hh}")
    if _seconds(call):
        par["duration"] = _seconds(call, 2, 15)
    d = _json(requests.post(base + "/api/v1/services/aigc/video-generation/video-synthesis", headers=h,
                            json={"model": model, "input": inp, "parameters": par}, timeout=120), "Wan (DashScope)")
    out = d.get("output") or {}
    tid, st = out.get("task_id"), out.get("task_status")
    while st not in ("SUCCEEDED", "FAILED", "CANCELED", "UNKNOWN"):
        _wait(deadline)
        out = _json(requests.get(f"{base}/api/v1/tasks/{tid}", headers={"Authorization": h["Authorization"]}, timeout=60),
                    "Wan (DashScope)").get("output") or {}
        st = out.get("task_status")
    if st != "SUCCEEDED":
        raise ToolError("Wan did not create a video: " + T._clip(out.get("message") or st, 300))
    return None, out.get("video_url"), None, None


def gen_seedance(keys, model, call, root, deadline):
    base = T._env("ARK_BASE_URL", "https://ark.ap-southeast.bytepluses.com/api/v3").rstrip("/")
    h = {"Authorization": "Bearer " + keys[0]}
    img = image_input(root, call.get("image"))
    flags = f" --ratio {'adaptive' if img else (_aspect(call) or '16:9')} --duration {_seconds(call, 3, 12) or 5}"
    if call.get("resolution") in ("480p", "720p", "1080p"):
        flags += f" --resolution {call['resolution']}"
    content = [{"type": "text", "text": _prompt(call) + flags}]
    if img:
        content.append({"type": "image_url", "image_url": {"url": img[2]}})
    d = _json(requests.post(base + "/contents/generations/tasks", headers=h, json={"model": model, "content": content}, timeout=120),
              "Seedance (BytePlus)")
    tid = d.get("id")
    while d.get("status") not in ("succeeded", "failed", "cancelled"):
        _wait(deadline)
        d = _json(requests.get(f"{base}/contents/generations/tasks/{tid}", headers=h, timeout=60), "Seedance (BytePlus)")
    if d["status"] != "succeeded":
        raise ToolError("Seedance did not create a video: " + T._clip(_errmsg(d) or d["status"], 300))
    return None, (d.get("content") or {}).get("video_url"), None, None


def higgsfield_upload(key, mime, data):
    """Higgsfield nimmt nur oeffentliche Adressen: Datei in den Higgsfield-Speicher laden (vorsignierte Adresse, ohne Zugangsdaten)."""
    d = _json(requests.post("https://api.higgsfield.ai/files/generate-upload-url", headers={"Authorization": "Key " + key},
                            json={"content_type": mime}, timeout=60), "Higgsfield")
    r = requests.put(d["upload_url"], data=data, headers=d.get("upload_headers") or {"Content-Type": mime}, timeout=300)
    if r.status_code >= 400:
        raise ToolError(f"Higgsfield-Upload fehlgeschlagen (HTTP {r.status_code})")
    return d["public_url"]


def gen_higgsfield(keys, model, call, root, deadline):
    base = T._env("HIGGSFIELD_BASE_URL", "https://api.higgsfield.ai").rstrip("/")
    h = {"Authorization": "Key " + keys[0]}
    body = {"prompt": _prompt(call, 7000)}
    if _seconds(call):
        body["duration"] = _seconds(call, 2, 30)
    if _aspect(call):
        body["aspect_ratio"] = _aspect(call)
    img = image_input(root, call.get("image"))
    if img:
        body["image_url"] = higgsfield_upload(keys[0], img[0], img[1]) if img[1] else img[2]
    body.update(_extra("higgsfield"))
    h2 = dict(h, **{"Idempotency-Key": hashlib.sha256(json.dumps(body, sort_keys=True).encode() + str(time.time()).encode()).hexdigest()[:32]})
    d = _json(requests.post(f"{base}/{model.strip('/')}", headers=h2, json=body, timeout=120), "Higgsfield")
    poll = d.get("status_url") or f"{base}/requests/{d.get('request_id')}/status"
    while d.get("status") not in ("completed", "failed", "nsfw", "canceled"):
        _wait(deadline)
        d = _json(requests.get(poll, headers=h, timeout=60), "Higgsfield")
    if d["status"] == "nsfw":
        raise ToolError("Higgsfield rejected the job because of the content check (nsfw)")
    if d["status"] != "completed":
        raise ToolError(f"Higgsfield: Video {d['status']}: " + T._clip(_errmsg(d), 300))
    return None, find_url(d), None, None


def fal_run(key, model, body, deadline, who="fal.ai"):
    """fal.ai-Warteschlange: abschicken, Status abfragen, Ergebnis-JSON holen."""
    h = {"Authorization": "Key " + key}
    d = _json(requests.post("https://queue.fal.run/" + model.strip("/"), headers=h, json=body, timeout=300), who)
    status_url = d.get("status_url") or f"https://queue.fal.run/{model}/requests/{d.get('request_id')}/status"
    resp_url = d.get("response_url") or f"https://queue.fal.run/{model}/requests/{d.get('request_id')}"
    while d.get("status") != "COMPLETED":
        _wait(deadline)
        d = _json(requests.get(status_url, headers=h, timeout=60), who)
        if d.get("error"):
            break
    res = _json(requests.get(resp_url, headers=h, timeout=120), who)
    if not find_url(res):
        raise ToolError(f"{who} ({model}) returned no result: " + T._clip(_errmsg(res) or _errmsg(d) or json.dumps(res)[:300], 300))
    return res


def gen_fal(keys, model, call, root, deadline):
    body = {"prompt": _prompt(call)}
    if _aspect(call):
        body["aspect_ratio"] = _aspect(call)
    if call.get("resolution") in ("480p", "580p", "720p", "1080p"):
        body["resolution"] = call["resolution"]
    img = image_input(root, call.get("image"))
    if img:
        body["image_url"] = img[2]
    body.update(_extra("fal"))
    return None, find_url(fal_run(keys[0], model, body, deadline)), None, None


def gen_replicate(keys, model, call, root, deadline):
    h = {"Authorization": "Bearer " + keys[0], "Prefer": "wait=60"}
    inp = {"prompt": _prompt(call)}
    if _aspect(call):
        inp["aspect_ratio"] = _aspect(call)
    img = image_input(root, call.get("image"))
    if img:
        inp[T._env("REPLICATE_IMAGE_FIELD", "image")] = img[2]
    inp.update(_extra("replicate"))
    if ":" in model:  # owner/name:version
        r = requests.post("https://api.replicate.com/v1/predictions", headers=h, json={"version": model.split(":", 1)[1], "input": inp}, timeout=120)
    else:
        r = requests.post(f"https://api.replicate.com/v1/models/{model}/predictions", headers=h, json={"input": inp}, timeout=120)
    d = _json(r, "Replicate")
    while d.get("status") not in ("succeeded", "failed", "canceled"):
        _wait(deadline)
        d = _json(requests.get((d.get("urls") or {}).get("get") or f"https://api.replicate.com/v1/predictions/{d.get('id')}",
                               headers={"Authorization": h["Authorization"]}, timeout=60), "Replicate")
    if d["status"] != "succeeded":
        raise ToolError("Replicate did not create a video: " + T._clip(_errmsg(d) or d["status"], 300))
    return None, find_url(d.get("output")), None, None


GEN = {"gemini": gen_gemini, "openai": gen_openai, "openrouter": gen_openrouter, "runway": gen_runway, "luma": gen_luma,
       "kling": gen_kling, "minimax": gen_minimax, "wan": gen_wan, "seedance": gen_seedance, "higgsfield": gen_higgsfield,
       "fal": gen_fal, "replicate": gen_replicate}


def generate(root, call):
    provs = providers()
    if not provs:
        raise ToolError("Video generation is off (set VIDEO_PROVIDER in .env, e.g. VIDEO_PROVIDER=kling)")
    if not _prompt(call):
        raise ToolError("prompt missing")
    prov = str(call.get("provider") or provs[0]).strip().lower()
    if prov not in provs:
        raise ToolError(f"Provider '{prov}' is not switched on. Possible: {', '.join(provs)}")
    if call.get("continue_id") and prov not in ("gemini", "openai"):
        raise ToolError("continue_id only works with gemini (Omni) or openai (Sora remix)")
    keys = keys_of(prov)
    model = model_of(prov, bool(call.get("image")), provs[0])
    deadline = time.time() + int(T._env("PCL_VIDEO_TIMEOUT", "900") or 900)
    data, url, headers, iid = GEN[prov](keys, model, call, root, deadline)
    dst = T._out_path(root, call, "video", "mp4")
    if data is not None:
        if len(data) > T.MAX_VIDEO_BYTES:
            raise ToolError("Video is too large")
        dst.write_bytes(data)
    elif url:
        if prov == "gemini":
            T._download_video(url, keys[0], dst)
        else:
            save_url(url, dst, headers)
    else:
        raise ToolError(f"{prov} ({model}) reported success, but without a video address")
    rel = T._rel(root, dst)
    try:
        p = T._probe(dst)
        info = " " + T._describe_probe(p) + "." if p["video"] else ""
    except Exception:  # ffprobe fehlt: Video ist trotzdem da
        info = ""
    return (f"Video created with {prov} ({model}): {rel} ({dst.stat().st_size // 1024} KB).{info}"
            + (f" Continue with continue_id: {iid}" if iid else ""))


# --------------------------------------------------------------------------- video_ai: Hochskalieren, Lippensync, Ton zum Video (fal.ai)
AI_OPS = {
    "upscale": ("FAL_UPSCALE_MODEL", "fal-ai/video-upscaler"),
    "lipsync": ("FAL_LIPSYNC_MODEL", "fal-ai/sync-lipsync/v2"),
    "sound": ("FAL_SOUND_MODEL", "fal-ai/mmaudio-v2"),
}


def video_ai_enabled():
    return T._env("VIDEO_AI").lower() == "fal"


def video_ai(root, call):
    if not video_ai_enabled():
        raise ToolError("video_ai is off (set VIDEO_AI=fal and FAL_KEY in .env)")
    key = T._env("FAL_KEY").split(",")[0].strip()
    if not key:
        raise ToolError("VIDEO_AI=fal, but FAL_KEY is missing")
    op = str(call.get("op") or "").strip().lower()
    if op not in AI_OPS:
        raise ToolError("op must be upscale, lipsync or sound")
    if not call.get("input"):
        raise ToolError("input missing (video in the project folder, e.g. output/scene1.mp4)")
    model = T._model_env(*AI_OPS[op])
    body = {"video_url": media_input(root, call["input"], ("video",))}
    if op == "upscale":
        try:
            body["scale"] = max(1, min(int(call.get("scale") or 2), 4))
        except (TypeError, ValueError):
            raise ToolError("scale must be 2, 3 or 4")
    elif op == "lipsync":
        if not call.get("audio"):
            raise ToolError("audio missing (voice recording, e.g. from speak)")
        body["audio_url"] = media_input(root, call["audio"], ("audio",))
    elif op == "sound":
        body["prompt"] = str(call.get("prompt") or "").strip()[:1000]
    deadline = time.time() + int(T._env("PCL_VIDEO_TIMEOUT", "900") or 900)
    url = find_url(fal_run(key, model, body, deadline))
    dst = T._out_path(root, {"name": call.get("name") or f"{op}"}, op, "mp4")
    save_url(url, dst)
    return f"video_ai {op} done ({model}): {T._rel(root, dst)} ({dst.stat().st_size // 1024} KB)"


# --------------------------------------------------------------------------- sound_generate: Geraeusche und Musik
def audio_provider():
    p = T._env("AUDIO_PROVIDER").lower()
    return p if p in ("elevenlabs", "fal") else ""


def sound_generate(root, call):
    prov = audio_provider()
    if not prov:
        raise ToolError("sound_generate is off (set AUDIO_PROVIDER=elevenlabs or fal in .env)")
    prompt = str(call.get("prompt") or "").strip()[:2000]
    if not prompt:
        raise ToolError("prompt missing (e.g. 'rain on a tin roof, distant thunder')")
    kind = str(call.get("kind") or "sfx").lower()
    if kind not in ("sfx", "music"):
        raise ToolError("kind must be sfx (sound effect) or music")
    try:
        secs = float(call.get("seconds") or (30 if kind == "music" else 5))
    except (TypeError, ValueError):
        raise ToolError("seconds must be a number")
    outdir = root / "output" / "audio"
    outdir.mkdir(parents=True, exist_ok=True)
    base, i = T._safe_name(call.get("name"), kind), 0
    while (outdir / f"{base}{'' if not i else '-' + str(i)}.mp3").exists() or (outdir / f"{base}{'' if not i else '-' + str(i)}.wav").exists():
        i += 1
    stem = f"{base}{'' if not i else '-' + str(i)}"
    if prov == "elevenlabs":
        key = T._env("ELEVENLABS_API_KEY")
        if not key:
            raise ToolError("AUDIO_PROVIDER=elevenlabs, but ELEVENLABS_API_KEY is missing")
        h = {"xi-api-key": key}
        if kind == "music":
            r = requests.post("https://api.elevenlabs.io/v1/music", headers=h, params={"output_format": "mp3_44100_128"},
                              json={"prompt": prompt, "music_length_ms": int(max(3, min(secs, 300)) * 1000)}, timeout=600)
        else:
            r = requests.post("https://api.elevenlabs.io/v1/sound-generation", headers=h, params={"output_format": "mp3_44100_128"},
                              json={"text": prompt, "duration_seconds": max(0.5, min(secs, 30))}, timeout=300)
        if r.status_code >= 400:
            raise ToolError(f"ElevenLabs answers with HTTP {r.status_code}: " + T._clip(r.text, 300))
        dst = outdir / f"{stem}.mp3"
        dst.write_bytes(r.content)
    else:
        key = T._env("FAL_KEY").split(",")[0].strip()
        if not key:
            raise ToolError("AUDIO_PROVIDER=fal, but FAL_KEY is missing")
        model = T._model_env("FAL_AUDIO_MODEL", "fal-ai/stable-audio")
        res = fal_run(key, model, {"prompt": prompt, "seconds_total": int(max(1, min(secs, 47)))},
                      time.time() + int(T._env("PCL_VIDEO_TIMEOUT", "900") or 900))
        url = find_url(res, ("audio_file", "audio", "output"))
        ext = "mp3" if urlparse(url).path.lower().endswith(".mp3") else "wav"
        dst = outdir / f"{stem}.{ext}"
        save_url(url, dst, limit=100_000_000)
    return f"Sound created with {prov}: {T._rel(root, dst)} ({dst.stat().st_size // 1024} KB). Into the video: video_edit add_audio mode mix."


# --------------------------------------------------------------------------- Cloud-Stimmen fuer speak (TTS_ENGINE=elevenlabs | openai)
def cloud_tts(engine, text, voice, rate, target):
    if engine == "elevenlabs":
        key = T._env("ELEVENLABS_API_KEY")
        if not key:
            raise ToolError("TTS_ENGINE=elevenlabs, but ELEVENLABS_API_KEY is missing")
        vid = voice if voice and not voice.endswith(".onnx") and len(voice) >= 16 else T._env("ELEVENLABS_VOICE", "JBFqnCBsd6RMkjVDRZzb")
        body = {"text": text, "model_id": T._model_env("ELEVENLABS_TTS_MODEL", "eleven_multilingual_v2")}
        if rate:
            body["voice_settings"] = {"speed": max(0.7, min(rate, 1.2))}
        r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}", headers={"xi-api-key": key},
                          params={"output_format": "mp3_44100_128"}, json=body, timeout=300)
        who = "ElevenLabs"
    else:
        key = T._env("OPENAI_API_KEY").split(",")[0].strip()
        if not key:
            raise ToolError("TTS_ENGINE=openai, but OPENAI_API_KEY is missing")
        base = T._env("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        ov = voice if voice in ("alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer", "verse") \
            else T._env("OPENAI_TTS_VOICE", "alloy")
        body = {"model": T._model_env("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"), "voice": ov, "input": text, "response_format": "mp3"}
        if rate:
            body["speed"] = max(0.25, min(rate, 4.0))
        r = requests.post(base + "/audio/speech", headers={"Authorization": "Bearer " + key}, json=body, timeout=300)
        who = "OpenAI voice"
    if r.status_code >= 400:
        raise ToolError(f"{who} answers with HTTP {r.status_code}: " + T._clip(r.text, 300))
    target.write_bytes(r.content)


def elevenlabs_voices(lang=None):
    """Stimmen des ElevenLabs-Kontos (inkl. Standardstimmen) als kurze Liste fuer die Agenten."""
    key = T._env("ELEVENLABS_API_KEY")
    if not key:
        raise ToolError("ElevenLabs is not set up (ELEVENLABS_API_KEY missing in .env). Without a key there are only the local voices.")
    r = requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": key}, timeout=60)
    if r.status_code >= 400:
        raise ToolError(f"ElevenLabs answers with HTTP {r.status_code}: " + T._clip(r.text, 300))
    rows = []
    for v in (r.json() or {}).get("voices") or []:
        lab = v.get("labels") or {}
        info = ", ".join(str(lab[k]) for k in ("gender", "age", "accent", "description", "use_case", "language") if lab.get(k))
        rows.append(f"- {v.get('name', '?')}: {v.get('voice_id', '')}" + (f" ({info})" if info else ""))
    if not rows:
        return "No voices found in the ElevenLabs account."
    return ("ElevenLabs voices (voice = ID, with eleven_multilingual_v2 all of them also speak German/Turkish etc.):\n"
            + "\n".join(rows[:80]) + ("\n..." if len(rows) > 80 else ""))
