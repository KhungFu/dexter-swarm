"""Dateien in die Cloud des Besitzers hochladen: GitHub, Google Drive, OneDrive.

Zugangsdaten: Client-IDs und GitHub-Token in .env (zur Laufzeit gelesen). Google und Microsoft melden sich per
Geraete-Code an (Code am Handy eingeben, klappt ohne HTTPS); das Erneuerungs-Token liegt in tokens/<dienst>.json
neben .env (PCL_TOKENS_DIR), nie in der Datenbank oder im Projektordner.
Das Modul kennt keine Agenten und keine Rechte: Wer hochladen darf, prueft app.py.
"""
import json
import os
import threading
import time
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent
TIMEOUT = 60
GITHUB_CONTENTS_MAX = 50 * 1024 * 1024    # groessere Dateien gehen als Release-Anhang (bis 2 GB)
GITHUB_RELEASE_MAX = 2000 * 1024 * 1024
DRIVE_CHUNK = 8 * 1024 * 1024             # Vielfaches von 256 KB
ONEDRIVE_SIMPLE_MAX = 4 * 1024 * 1024     # bis hier ein einfacher PUT
ONEDRIVE_CHUNK = 320 * 1024 * 20          # Vielfaches von 320 KB

GOOGLE_DEVICE = "https://oauth2.googleapis.com/device/code"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_SCOPE = "https://www.googleapis.com/auth/drive.file"
DRIVE_API = "https://www.googleapis.com/drive/v3"
DRIVE_UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
MS_LOGIN = "https://login.microsoftonline.com"
MS_SCOPE = "Files.ReadWrite offline_access"
GRAPH = "https://graph.microsoft.com/v1.0"
GITHUB_API = "https://api.github.com"
GITHUB_UPLOADS = "https://uploads.github.com"

LABELS = {"github": "GitHub", "gdrive": "Google Drive", "onedrive": "OneDrive"}
_lock = threading.Lock()


class CloudError(Exception):
    pass


def env(k, d=""):
    return os.environ.get(k, d).strip()


# ------------------------------------------------------------------ Tokens auf der Platte
def tokens_dir():
    return Path(env("PCL_TOKENS_DIR") or str(BASE / "tokens"))


def _tok_file(svc):
    return tokens_dir() / f"{svc}.json"


def load_token(svc):
    try:
        return json.loads(_tok_file(svc).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_token(svc, data):
    d = tokens_dir()
    d.mkdir(parents=True, exist_ok=True)
    f = _tok_file(svc)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, f)


def logout(svc):
    try:
        _tok_file(svc).unlink()
    except FileNotFoundError:
        pass


# ------------------------------------------------------------------ Status
def status(svc):
    """(eingerichtet, angemeldet, Hinweis)."""
    if svc == "github":
        if not env("GITHUB_UPLOAD_TOKEN"):
            return False, False, "GITHUB_UPLOAD_TOKEN missing in .env"
        if "/" not in env("GITHUB_UPLOAD_REPO"):
            return False, False, "GITHUB_UPLOAD_REPO missing in .env (format: owner/repo)"
        return True, True, env("GITHUB_UPLOAD_REPO")
    if svc == "gdrive":
        if not (env("GDRIVE_CLIENT_ID") and env("GDRIVE_CLIENT_SECRET")):
            return False, False, "GDRIVE_CLIENT_ID and GDRIVE_CLIENT_SECRET missing in .env"
        return True, bool(load_token(svc).get("refresh_token")), ""
    if svc == "onedrive":
        if not env("ONEDRIVE_CLIENT_ID"):
            return False, False, "ONEDRIVE_CLIENT_ID missing in .env"
        return True, bool(load_token(svc).get("refresh_token")), ""
    return False, False, "unbekannter Dienst"


def ready(svc):
    ok, logged, _ = status(svc)
    return ok and logged


def clean_folder(folder):
    """Ordnerpfad ohne .., Laufwerksbuchstaben und Steuerzeichen; '' = oberste Ebene."""
    parts = []
    for p in str(folder or "").replace("\\", "/").split("/"):
        p = "".join(ch for ch in p if ch >= " " and ch not in ':*?"<>|').strip().strip(".")
        if p:
            parts.append(p[:100])
    return "/".join(parts[:12])


def join_folder(base, sub):
    return "/".join(x for x in (clean_folder(base), clean_folder(sub)) if x)


def _check(r, what):
    if r.status_code >= 400:
        try:
            d = r.json()
            e = d.get("error") if isinstance(d, dict) else None
            msg = e.get("message", "") if isinstance(e, dict) else (d.get("error_description") or d.get("message") or e or "")
        except (ValueError, AttributeError):
            msg = ""
        raise CloudError(f"{what}: HTTP {r.status_code}{' – ' + str(msg)[:300] if msg else ''}")
    return r


# ------------------------------------------------------------------ Anmeldung per Geraete-Code
def _device_urls(svc):
    if svc == "gdrive":
        return GOOGLE_DEVICE, GOOGLE_TOKEN, GOOGLE_SCOPE, env("GDRIVE_CLIENT_ID"), env("GDRIVE_CLIENT_SECRET")
    tenant = env("ONEDRIVE_TENANT") or "consumers"
    return (f"{MS_LOGIN}/{tenant}/oauth2/v2.0/devicecode", f"{MS_LOGIN}/{tenant}/oauth2/v2.0/token", MS_SCOPE,
            env("ONEDRIVE_CLIENT_ID"), "")


def device_start(svc):
    """Startet die Anmeldung. Gibt dict mit user_code, url, device_code, interval, expires zurueck."""
    if svc not in ("gdrive", "onedrive"):
        raise CloudError("Sign-in by code exists only for Google Drive and OneDrive.")
    ok, _, hint = status(svc)
    if not ok:
        raise CloudError(hint)
    dev, _, scope, cid, _ = _device_urls(svc)
    r = _check(requests.post(dev, data={"client_id": cid, "scope": scope}, timeout=TIMEOUT), "Anmeldung starten")
    d = r.json()
    return {"user_code": d["user_code"], "url": d.get("verification_url") or d.get("verification_uri"),
            "device_code": d["device_code"], "interval": int(d.get("interval") or 5),
            "expires": time.time() + int(d.get("expires_in") or 900)}


def device_poll(svc, dc):
    """Einmal nachfragen. 'pending' / 'slow_down' / 'ok' (Token gespeichert); Fehler als CloudError."""
    _, tok, _, cid, secret = _device_urls(svc)
    data = {"client_id": cid, "device_code": dc["device_code"], "grant_type": "urn:ietf:params:oauth:grant-type:device_code"}
    if secret:
        data["client_secret"] = secret
    r = requests.post(tok, data=data, timeout=TIMEOUT)
    try:
        d = r.json()
    except ValueError:
        d = {}
    err = d.get("error")
    if err == "authorization_pending":
        return "pending"
    if err == "slow_down":
        return "slow_down"
    if err in ("access_denied", "authorization_declined"):
        raise CloudError("Anmeldung abgelehnt.")
    if err in ("expired_token", "code_expired"):
        raise CloudError("The code has expired. Please sign in again.")
    if err or not d.get("refresh_token"):
        raise CloudError(f"Anmeldung fehlgeschlagen: {d.get('error_description') or err or 'no refresh token (offline_access?)'}")
    save_token(svc, {"refresh_token": d["refresh_token"], "access_token": d.get("access_token", ""),
                     "expires": time.time() + int(d.get("expires_in") or 3000) - 60, "created": time.time()})
    return "ok"


def access_token(svc):
    with _lock:
        t = load_token(svc)
        if not t.get("refresh_token"):
            raise CloudError(f"{LABELS[svc]}: not signed in yet (in the ☁️ Cloud window click “Sign in”).")
        if t.get("access_token") and t.get("expires", 0) > time.time():
            return t["access_token"]
        _, tok, scope, cid, secret = _device_urls(svc)
        data = {"client_id": cid, "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}
        if secret:
            data["client_secret"] = secret
        if svc == "onedrive":
            data["scope"] = scope
        r = requests.post(tok, data=data, timeout=TIMEOUT)
        if r.status_code >= 400:
            raise CloudError(f"{LABELS[svc]}: sign-in expired or revoked (HTTP {r.status_code}). Please sign in again in the ☁️ Cloud window.")
        d = r.json()
        t["access_token"] = d["access_token"]
        t["expires"] = time.time() + int(d.get("expires_in") or 3000) - 60
        if d.get("refresh_token"):  # Microsoft tauscht das Erneuerungs-Token bei jeder Nutzung aus
            t["refresh_token"] = d["refresh_token"]
        save_token(svc, t)
        return t["access_token"]


# ------------------------------------------------------------------ GitHub
def _gh_headers(extra=None):
    return {"Authorization": f"Bearer {env('GITHUB_UPLOAD_TOKEN')}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "Hyperstead", **(extra or {})}


def _gh_path(p):
    return "/".join(requests.utils.quote(x, safe="") for x in p.split("/"))


def github_upload(path, folder, name):
    import base64
    repo = env("GITHUB_UPLOAD_REPO")
    size = path.stat().st_size
    if size > GITHUB_RELEASE_MAX:
        raise CloudError("GitHub: file is larger than 2 GB.")
    if size > GITHUB_CONTENTS_MAX:
        return _github_release(repo, path, name, size)
    target = join_folder(folder, name)
    url = f"{GITHUB_API}/repos/{repo}/contents/{_gh_path(target)}"
    branch = env("GITHUB_UPLOAD_BRANCH")
    old = requests.get(url, headers=_gh_headers(), params={"ref": branch} if branch else None, timeout=TIMEOUT)
    body = {"message": f"Hyperstead: {target}", "content": base64.b64encode(path.read_bytes()).decode()}
    if branch:
        body["branch"] = branch
    if old.status_code == 200 and isinstance(old.json(), dict) and old.json().get("sha"):
        body["sha"] = old.json()["sha"]  # gibt es schon: neue Version (die alte bleibt in der Historie)
    elif old.status_code not in (200, 404):
        _check(old, "GitHub")
    r = _check(requests.put(url, headers=_gh_headers(), json=body, timeout=max(TIMEOUT, size // 200_000)), "GitHub")
    return ((r.json().get("content") or {}).get("html_url") or f"https://github.com/{repo}/blob/{branch or 'HEAD'}/{target}")


def _github_release(repo, path, name, size):
    tag = env("GITHUB_UPLOAD_RELEASE") or "paperclip-ablage"
    r = requests.get(f"{GITHUB_API}/repos/{repo}/releases/tags/{tag}", headers=_gh_headers(), timeout=TIMEOUT)
    if r.status_code == 404:
        r = _check(requests.post(f"{GITHUB_API}/repos/{repo}/releases", headers=_gh_headers(),
                                 json={"tag_name": tag, "name": "Hyperstead-Ablage",
                                       "body": "Large files from Hyperstead (over 50 MB)."}, timeout=TIMEOUT), "GitHub-Release")
    rel = _check(r, "GitHub-Release").json()
    for a in rel.get("assets") or []:
        if a.get("name") == name:  # gleicher Name: alte Datei ersetzen
            _check(requests.delete(f"{GITHUB_API}/repos/{repo}/releases/assets/{a['id']}", headers=_gh_headers(), timeout=TIMEOUT),
                   "GitHub-Release")
    with open(path, "rb") as f:
        r = _check(requests.post(f"{GITHUB_UPLOADS}/repos/{repo}/releases/{rel['id']}/assets", params={"name": name},
                                 headers=_gh_headers({"Content-Type": "application/octet-stream", "Content-Length": str(size)}),
                                 data=f, timeout=(30, 3600)), "GitHub-Upload")
    return r.json().get("browser_download_url") or rel.get("html_url", "")


# ------------------------------------------------------------------ Google Drive
def _drive_folder(tok, folder):
    parent = env("GDRIVE_FOLDER_ID") or "root"
    h = {"Authorization": f"Bearer {tok}"}
    for part in [p for p in folder.split("/") if p]:
        esc = part.replace("\\", "\\\\").replace("'", "\\'")
        r = _check(requests.get(f"{DRIVE_API}/files", headers=h, timeout=TIMEOUT, params={
            "q": f"name='{esc}' and mimeType='application/vnd.google-apps.folder' and '{parent}' in parents and trashed=false",
            "fields": "files(id)", "pageSize": 1}), "Google Drive")
        found = r.json().get("files") or []
        if found:
            parent = found[0]["id"]
        else:
            r = _check(requests.post(f"{DRIVE_API}/files", headers=h, params={"fields": "id"}, timeout=TIMEOUT, json={
                "name": part, "mimeType": "application/vnd.google-apps.folder", "parents": [parent]}), "Google Drive (folder)")
            parent = r.json()["id"]
    return parent


def gdrive_upload(path, folder, name):
    tok = access_token("gdrive")
    parent = _drive_folder(tok, folder)
    size = path.stat().st_size
    r = _check(requests.post(DRIVE_UPLOAD, params={"uploadType": "resumable", "fields": "id,webViewLink"}, timeout=TIMEOUT,
                             headers={"Authorization": f"Bearer {tok}", "X-Upload-Content-Length": str(size),
                                      "Content-Type": "application/json; charset=UTF-8"},
                             json={"name": name, "parents": [parent]}), "Google Drive")
    loc = r.headers.get("Location") or r.headers.get("location")
    if not loc:
        raise CloudError("Google Drive: no upload address received.")
    d = _chunked_put(loc, path, size, DRIVE_CHUNK, {"Authorization": f"Bearer {tok}"}, "Google Drive")
    return d.get("webViewLink") or f"https://drive.google.com/file/d/{d.get('id', '')}/view"


# ------------------------------------------------------------------ OneDrive
def onedrive_upload(path, folder, name):
    tok = access_token("onedrive")
    h = {"Authorization": f"Bearer {tok}"}
    target = _gh_path(join_folder(folder, name))
    size = path.stat().st_size
    if size <= ONEDRIVE_SIMPLE_MAX:
        r = _check(requests.put(f"{GRAPH}/me/drive/root:/{target}:/content", headers=h, data=path.read_bytes(), timeout=TIMEOUT),
                   "OneDrive")
        return r.json().get("webUrl", "")
    r = _check(requests.post(f"{GRAPH}/me/drive/root:/{target}:/createUploadSession", headers=h, timeout=TIMEOUT,
                             json={"item": {"@microsoft.graph.conflictBehavior": "replace"}}), "OneDrive")
    d = _chunked_put(r.json()["uploadUrl"], path, size, ONEDRIVE_CHUNK, {}, "OneDrive")  # Upload-Adresse traegt die Berechtigung
    return d.get("webUrl", "")


def _chunked_put(url, path, size, chunk, headers, what):
    """Datei in Teilen hochladen (Google und Microsoft verstehen beide Content-Range). Gibt die JSON-Antwort des letzten Teils zurueck."""
    if size == 0:
        return _check(requests.put(url, headers={**headers, "Content-Length": "0"}, data=b"", timeout=TIMEOUT), what).json()
    with open(path, "rb") as f:
        pos = 0
        while pos < size:
            data = f.read(chunk)
            end = pos + len(data) - 1
            r = requests.put(url, data=data, timeout=(30, 600),
                             headers={**headers, "Content-Length": str(len(data)), "Content-Range": f"bytes {pos}-{end}/{size}"})
            if r.status_code in (200, 201):
                return r.json()
            if r.status_code not in (202, 308):
                _check(r, what)
                raise CloudError(f"{what}: unerwartete Antwort HTTP {r.status_code}")
            pos = end + 1
    raise CloudError(f"{what}: upload not completed.")


UPLOADERS = {"github": github_upload, "gdrive": gdrive_upload, "onedrive": onedrive_upload}


def upload(svc, path, folder="", name=""):
    """Laedt die Datei hoch und gibt den Link zurueck. Fehler als CloudError mit verstaendlicher Meldung."""
    if svc not in UPLOADERS:
        raise CloudError(f"Unbekannter Dienst '{svc}'. Moeglich: {', '.join(UPLOADERS)}")
    ok, logged, hint = status(svc)
    if not ok:
        raise CloudError(f"{LABELS[svc]} is not set up: {hint}")
    if not logged:
        raise CloudError(f"{LABELS[svc]}: not signed in yet (in the ☁️ Cloud window click “Sign in”).")
    path = Path(path)
    if not path.is_file():
        raise CloudError(f"File not found: {path.name}")
    name = clean_folder(name or path.name).replace("/", "_") or "file"
    try:
        return UPLOADERS[svc](path, clean_folder(folder), name)
    except requests.RequestException as e:
        raise CloudError(f"{LABELS[svc]} not reachable ({type(e).__name__}).")
