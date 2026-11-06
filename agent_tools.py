"""
Werkzeuge der Agenten: Websuche, Webseiten lesen, Bilder suchen/laden/erzeugen, Projektdateien lesen.

Eigenstaendiges Modul (keine Imports aus app.py). Alle Funktionen werfen nie nach aussen:
run_tool() liefert immer Text, Fehler beginnen mit "ERROR:", damit das Modell sie lesen und reagieren kann.
Konfiguration nur ueber Umgebungsvariablen (zur Laufzeit gelesen), siehe .env.example.

Sicherheit:
- fetch_url/image_save duerfen nur oeffentliche Adressen laden (keine localhost-, LAN-, Tailscale-, Metadaten-IPs),
  Weiterleitungen werden Schritt fuer Schritt neu geprueft. (Restrisiko: DNS-Rebinding zwischen Pruefung und Abruf.)
- Alles Geladene ist UNVERTRAUENSWUERDIGE Daten. Die Rechte der Agenten bleiben serverseitig in app.py geprueft.
- Dateien nur innerhalb des Projektordners workspace/<projekt-id>/.
"""
import base64
import html as htmllib
import io
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse

import requests

UA = "Mozilla/5.0 (compatible; Hyperstead/1.0; self-hosted agent team)"
MAX_PAGE_BYTES = 2_000_000
MAX_IMAGE_BYTES = 8_000_000
PAGE_CHARS = 7000        # Text pro Seite, der ans Modell geht
READ_CHARS = 12000       # Text pro gelesener Projektdatei
MAX_PDF_BYTES = 30_000_000


class ToolError(Exception):
    pass


def _env(k, d=""):
    return os.environ.get(k, d).strip()


def _model_env(k, default):
    """Modellname aus .env: leer = Standard; Anfuehrungszeichen, Leerzeichen und fuehrendes models/ weg."""
    m = _env(k).strip("\"' \r")
    m = m[len("models/"):] if m.startswith("models/") else m
    return m or default


def enabled():
    """Globaler Schalter (PCL_ALLOW_WEB=0 sperrt alle Internet-Werkzeuge)."""
    return _env("PCL_ALLOW_WEB", "1") != "0"


# --------------------------------------------------------------------- Beschreibung fuers Modell (Englisch, Wunsch ABI 2026-11-05)
TOOLS = {
    "web_search": ("web", '{"tool": "web_search", "query": "search term"}  Web search: current information, laws, prices, competition, sources. '
                          'Find PDFs/documents: search term + " filetype:pdf"'),
    "fetch_url": ("web", '{"tool": "fetch_url", "url": "https://..."}  Read a web page or PDF (text content)'),
    "browse_page": ("web", '{"tool": "browse_page", "url": "https://...", "screenshot": true}  Open a page in a REAL browser (JavaScript runs): '
                           'for pages where fetch_url is empty/incomplete (web apps, shops, maps). screenshot true = you see the page as an image; '
                           'optional wait (seconds, max. 10), save "name" = store the screenshot in assets/screenshots/. Slower than fetch_url'),
    "download_file": ("web", '{"tool": "download_file", "url": "https://.../x.pdf", "name": "shortname"}  Save a file (PDF, EPUB, Office, audio, video, ZIP) '
                             'in downloads/. Respect copyright/licence, only for permitted use'),
    "image_search": ("images", '{"tool": "image_search", "query": "mountain lake sunrise"}  Search freely usable photos (licence/author are included)'),
    "image_save": ("images", '{"tool": "image_save", "url": "https://...jpg", "name": "hero"}  Save an image in the project\'s assets/; '
                             'optional "path": "karten/bilder/k01.png" = fixed target in assets/, output/ or karten/'),
    "canva_upload": ("images", '{"tool": "canva_upload", "path": "input/reference.jpg", "upload_url": "https://..."}  Upload an image from the '
                               'project folder to Canva (only if your AI has the Canva connection). First get a fresh upload_url with Canva '
                               'create-upload-url, then call this; the answer contains the Canva media ID for generate-image imageReferences'),
    "image_generate": ("images", """{"tool": "image_generate", "prompt": "detailed image description incl. style", "name": "logo"}  Create an image with AI (PNG), default: new in assets/.
     Optional: "refs": ["input/template.png", "karten/characters.png"] = up to 4 reference images from the project folder, so that characters and style
     stay the same across many images (for series ALWAYS pass the same reference images); "format": "square" | "portrait" | "landscape";
     "path": "karten/bilder/k01.png" = fixed target path in assets/, output/ or karten/ (an existing file is replaced);
     "quality": "low" | "medium" | "high" (OpenAI only, high costs more). Then check with view_image."""),
    "video_generate": ("media", """{"tool": "video_generate", "prompt": "scene: place, characters, action, camera, light, sound", "name": "scene1"}  Create a short video clip with AI (approx. 4-15 s, costs per clip/second), result in output/.
     optional: provider (one of the enabled video providers, default = first), aspect 16:9|9:16|1:1, resolution 720p|1080p, seconds (length),
     image (start image in the project, e.g. assets/character.png, or https address), continue_id (ID from an earlier result: continue the clip, gemini/openai only).
     Longer films: create several clips and join them with video_edit op=concat. Describe the same characters the same way in every prompt"""),
    "video_ai": ("media", """{"tool": "video_ai", "op": "upscale", "input": "output/scene1.mp4"}  AI post-processing of a video (fal.ai, costs), result in output/:
     op=upscale: input, scale 2-4 (higher resolution, sharper) | op=lipsync: input (video with a face), audio (speech, e.g. from speak) = lips matching the speech |
     op=sound: input, prompt (which sounds) = matching sound/noises for a silent video. Videos max. 50 MB"""),
    "sound_generate": ("media", '{"tool": "sound_generate", "prompt": "rain on a tin roof, distant thunder", "kind": "sfx", "seconds": 8, "name": "rain"}  '
                                'Create a sound effect (kind sfx) or music (kind music, e.g. "calm piano music, sad") with AI, result in output/audio/. '
                                'Into the video with video_edit add_audio mode mix'),
    "site_macro": ("media", """{"tool": "site_macro", "site": "magiclight", "prompt": "story / scene description", "name": "episode1"}  Create a video on a website with the
     owner's account (e.g. MagicLight for long story videos with consistent characters, Google Flow). A browser robot
     operates the site, this can take many minutes. Result in output/. Available site names are in the error message if you pick a wrong one"""),
    "list_files": ("read_files", '{"tool": "list_files", "path": ""}  List files in the project folder (input/ = uploaded by the owner, '
                                 'assets/ = images, downloads/ = downloaded files, output/ = finished media/documents)'),
    "read_file": ("read_files", '{"tool": "read_file", "path": "file.pdf", "offset": 0}  Read a file: text, Markdown, HTML, PDF, DOCX, EPUB. '
                                'Read long files in parts (offset = character position, stated at the end of the output)'),
    "view_image": ("read_files", '{"tool": "view_image", "path": "input/photo.jpg"}  LOOK AT an image (maps, layouts, photos, screenshots). '
                                 'Also pages of scanned PDFs: {"tool": "view_image", "path": "input/scan.pdf", "page": 1} (up to 4 pages from page). '
                                 'The image is only attached to the next round: write down right away what you see'),
    "copy_files": ("write_files", '{"tool": "copy_files", "from": "site", "to": "www", "move": false}  Copy a file or a whole folder within the project folder '
                                  '(move true = move). Example: take over a finished site from site/ to www/. Existing files are overwritten'),
    "write_file": ("write_files", '{"tool": "write_file", "path": "book/chapter-01.md", "content": "..."}  Create/overwrite a text file in the project folder '
                                  '(Markdown, HTML, CSS, TXT, CSV, JSON, SVG ...; not input/, max. 500 KB). Available immediately, e.g. then make_document with sources'),
    "write_code": ("code", '{"tool": "write_code", "path": "src/main.py", "content": "..."}  Create/overwrite a source code file in the project folder '
                           '(any language: .py .rs .java .js .ts .go .c .cpp .sh .rb .php .lua .kt .cs .html .css ...). Then check with check_code'),
    "check_code": ("code", '{"tool": "check_code", "path": "src/main.py"}  Check syntax or compile WITHOUT running the program; '
                           'returns errors with line numbers. On errors fix them and check again'),
    "run_code": ("run_code", '{"tool": "run_code", "path": "src/analysis.py"}  RUN a script (Python, JavaScript, Bash, Ruby, PHP, Lua) '
                             'in an isolated environment: NO internet, time/RAM limit, project files read-only under /projekt (e.g. /projekt/input/data.csv). '
                             'What the script writes into its current directory ends up in output/run/<time>/ afterwards. '
                             'Instead of path also "code": "print(1+1)", "lang": "python". Optional args [..], stdin. Standard library/system packages only'),
    "rust_project": ("run_code", '{"tool": "rust_project", "op": "test", "dir": "rust/calculator"}  BUILD A FINISHED RUST PROGRAM: dir = folder with '
                                 'Cargo.toml (create it first with write_code: Cargo.toml, src/main.rs, tests as #[test] under #[cfg(test)]). '
                                 'Loads dependencies from crates.io, builds and tests isolated (no internet while building/testing). '
                                 'op=test (cargo test) | build | run (args [..], stdin) | package = tests + release build + output/<name>.zip '
                                 'with source code, program, test report and README.txt. Flow: write -> test -> fix errors -> '
                                 'test again -> package. A package is only created when all tests pass. Optional name (file name of the package)'),
    "media_info": ("media", '{"tool": "media_info", "path": "input/video.mp4"}  Duration, resolution, codecs of a video/audio/image file'),
    "video_edit": ("media", """{"tool": "video_edit", "op": "...", ...}  Edit video/audio (ffmpeg). Paths relative to the project folder, the result goes to output/.
     op=trim: input, start, end (seconds or MM:SS)
     op=concat: inputs [..] (brought to the same size/frame rate), optional width, height, fps
     op=slideshow: images [..], seconds (per image, default 4), kenburns true/false (zoom/pan), audio (optional music/narrator), width, height
     op=text_overlay: input, text, start, end, position top|center|bottom, size, color
     op=burn_subtitles: input, srt (subtitle file)
     op=overlay_image: input, image (logo/watermark), position tl|tr|bl|br|center, width
     op=add_audio: input (Video), audio, mode replace|mix, volume (0.0-2.0)
     op=extract_audio: input, format mp3|wav
     op=speed: input, factor (0.25-4)
     op=convert: input, format mp4|webm|gif|mp3|wav, optional width, height, fps
     op=frame: input, at (second) -> PNG still image
     optional for all: name (file name of the result without extension)"""),
    "speak": ("media", '{"tool": "speak", "text": "narrator text", "lang": "en", "name": "narrator1"}  Text to a spoken audio file (output/audio/). lang: de, en, tr ... '
                       'Optional own voice: voice (espeak variant m1-m7/f1-f5, Piper model x.onnx, Edge voice, ElevenLabs voice ID or OpenAI voice '
                       'like nova/onyx, depending on TTS_ENGINE), pitch 0-99 (50 normal), rate 0.5-2. '
                       'engine (optional, only for this call): auto | piper | espeak | edge | elevenlabs | openai'),
    "film": ("media", """{"tool": "film", "op": "...", ...}  ANIMATED FILM (Blender, characters with voices, lip sync, camera). Script = film/film.json (keys are German, use them exactly):
     {"titel": "Bello and the ball", "aufloesung": "640x360", "fps": 12,
      "figuren": {"Bello": {"art": "hund", "farbe": "#c8843c", "farbe2": "#f6e7d0", "stimme": {"lang": "en", "voice": "m3", "pitch": 40}},
                  "Mimi": {"art": "bild", "bild": "assets/mimi.png", "groesse": 1.6, "blickrichtung": "rechts"}},
      "szenen": [{"id": "s01", "ort": {"himmel": "#9fd7ff", "boden": "#7cc96b", "licht": "tag"},
                  "requisiten": [{"typ": "baum", "pos": [-4, 3]}, {"id": "ball", "typ": "ball", "pos": [1, 0]}],
                  "figuren": {"Bello": {"pos": [-3, 0]}, "Mimi": {"pos": [2.5, 0], "blick": "links"}},
                  "aktionen": [{"zeit": 0.5, "figur": "Bello", "tun": "gehen", "nach": [0, 0]}, {"zeit": 3, "figur": "Mimi", "tun": "winken"}],
                  "dialog": [{"figur": "Bello", "text": "Hello Mimi!"}, {"figur": "Mimi", "text": "Hello Bello!"}],
                  "kamera": {"einstellung": "total", "bewegung": "keine"}, "dauer": 5}]}
     art (kind): hund=dog katze=cat hase=rabbit baer=bear maus=mouse mensch=human (built in, haar = hair colour) | bild (character image from image_generate, background is removed) | blend (datei, objekt, aktion).
     pos [x, tiefe]: x -6..6 left/right, tiefe (depth) 0 front to 8 back. blick/richtung (look/direction): vorne=front links=left rechts=right hinten=back.
     tun (do): gehen=walk (nach=to, dauer=duration), springen=jump (hoehe=height), winken=wave, drehen=turn (richtung), nicken=nod, erscheinen=appear, verschwinden=disappear. Props can also be moved by id.
     requisiten (props) typ: baum=tree busch=bush haus=house stein=stone ball wolke=cloud blume=flower kiste=box bild=picture. ort (place): himmel=sky, boden=ground (false = none), hintergrund=background (image), licht=light tag|abend|nacht (day|evening|night).
     kamera: einstellung (shot) total|halbtotal|nah (wide|medium|close), ziel (target character), bewegung (movement) keine|zoom_rein|zoom_raus|schwenk_links|schwenk_rechts|folgen (none|zoom in|zoom out|pan left|pan right|follow).
     stimme/erzaehler_stimme (voice/narrator voice): lang, voice, pitch, rate, optional engine (e.g. elevenlabs only for the characters that should sound especially good).
     dialog without figur = narrator (erzaehler_stimme). Optional: musik, musik_lautstaerke (volume), titelkarte (title card, seconds), renderer eevee|workbench|cycles.
     Flow: op=save with "film": {...} (checks + saves) -> op=check -> op=voices -> op=preview, szene "s01" (still image, then view_image)
     -> op=render (szene "s01" or all; only changed scenes, can take long) -> op=assemble, name "film", untertitel (subtitles) true -> output/<name>.mp4"""),
    "make_document": ("media", """{"tool": "make_document", "format": "pdf", "title": "Book title", "author": "Name", "sources": ["chapter1.md", "chapter2.md"], "name": "book"}
     Creates a finished document in output/ from Markdown files. format: pdf | docx | epub | html. Optional: content (Markdown directly instead of sources),
     cover (image path, epub only), page A4|A5 (pdf). Markdown: # Chapter, ## Section, ### Subsection, - lists, 1. numbered, > quote, **bold**, *italic*, ![Text](assets/image.png)
     Free layout (rebuild a template: colours, columns, boxes, tabs): {"tool": "make_document", "html": "<!doctype html><html><head><style>
     @page { size: A4; margin: 0 } ...</style></head><body>...</body></html>", "name": "Game_A"} -> PDF in output/ (the HTML is saved as
     work/<name>.html and can later be rendered again as "html": "work/game_a.html"). Images in the HTML with paths
     relative to work/ (e.g. ../input/map.png), internet addresses are not loaded."""),
}


def available(perms):
    """Namen der Werkzeuge, die dieser Agent nutzen darf."""
    if not enabled():
        return []
    return [n for n, (right, _) in TOOLS.items()
            if (perms.get(right) or (n == "make_document" and perms.get("write_files"))  # Dokumente bauen gehoert zum Dateien schreiben
                or (n == "image_generate" and perms.get("media")))  # Bilder erzeugen gehoert auch zu den Medien
            and (n != "video_generate" or video_enabled())
            and (n != "video_ai" or _vp_on("video_ai_enabled"))
            and (n != "sound_generate" or _vp_on("audio_provider"))
            and (n != "site_macro" or bool(macro_sites()))
            and (n != "browse_page" or browser_enabled())
            and (n != "run_code" or run_enabled())
            and (n != "rust_project" or cargo_enabled())
            and (n != "canva_upload" or canva_enabled())]


def describe(names):
    out = []
    for n in names:
        out.append("  " + TOOLS[n][1])
        if n in ("speak", "film") and _env("ELEVENLABS_API_KEY"):
            out.append(TTS_PREMIUM_HINT)
    return "\n".join(out)


TTS_PREMIUM_HINT = ("     ELEVENLABS IS SET UP: if a voice really has to sound good (audiobook, advertising, film characters, narrator), "
                    "set \"engine\": \"elevenlabs\" (for film in stimme or erzaehler_stimme). Costs per character, for tests and drafts "
                    "keep the local voice. Matching voice IDs: {\"tool\": \"speak\", \"list_voices\": true}, then enter one as voice. "
                    "Without voice ElevenLabs uses the default voice. If ElevenLabs fails, the local voice is used automatically.")


# ------------------------------------------------------------------------- Sicherer Abruf
def check_public(host):
    """Wirft ToolError, wenn der Host nicht auf eine oeffentliche Adresse zeigt."""
    if not host:
        raise ToolError("Invalid address")
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        raise ToolError(f"Host '{host}' not found")
    for i in infos:
        ip = ipaddress.ip_address(i[4][0].split("%")[0])
        if getattr(ip, "ipv4_mapped", None):
            ip = ip.ipv4_mapped
        if not ip.is_global:
            raise ToolError("Access to local/private addresses is blocked")


def safe_get(url, max_bytes, hops=5):
    """GET mit Pruefung jeder Weiterleitung. Gibt (response, bytes, abgeschnitten) zurueck."""
    for _ in range(hops):
        u = urlparse(url)
        if u.scheme not in ("http", "https"):
            raise ToolError("Only http(s) addresses are allowed")
        check_public(u.hostname)
        r = requests.get(url, headers={"User-Agent": UA, "Accept": "*/*"}, timeout=(6, 20),
                         stream=True, allow_redirects=False)
        if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("Location"):
            url = urljoin(url, r.headers["Location"])
            r.close()
            continue
        buf, cut = bytearray(), False
        if "pdf" in r.headers.get("Content-Type", "").lower():
            max_bytes = max(max_bytes, MAX_PDF_BYTES)
        for chunk in r.iter_content(65536):
            buf += chunk
            if len(buf) > max_bytes:
                cut = True
                break
        r.close()
        if r.status_code >= 400:
            raise ToolError(f"HTTP {r.status_code} from {urlparse(url).netloc}")
        return r, bytes(buf[:max_bytes]), cut
    raise ToolError("Too many redirects")


class _Text(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "head", "template"}
    BREAK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "table", "ul", "ol"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip, self.title, self._in_title = [], 0, "", False

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        if tag in self.SKIP:
            self.skip += 1
        if tag in self.BREAK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        if tag in self.BREAK:
            self.out.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self.skip:
            self.out.append(data)


def html_to_text(html):
    p = _Text()
    try:
        p.feed(html)
    except Exception:
        pass
    text = re.sub(r"[ \t\r\f\v]+", " ", "".join(p.out))
    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
    return p.title.strip(), text


def _clip(text, n):
    return text if len(text) <= n else text[:n] + f"\n[... shortened, {len(text) - n} characters left out]"


# ------------------------------------------------------------------------------ Werkzeuge
def web_search(query, n=6):
    query = str(query or "").strip()[:300]
    if not query:
        raise ToolError("query missing")
    n = min(max(int(n or 6), 1), 10)
    rows = []  # (titel, url, text)
    if _env("SEARXNG_URL"):
        r = requests.get(_env("SEARXNG_URL").rstrip("/") + "/search", params={"q": query, "format": "json"},
                         headers={"User-Agent": UA}, timeout=15)
        rows = [(x.get("title", ""), x.get("url", ""), x.get("content", "")) for x in r.json().get("results", [])]
    elif _env("TAVILY_API_KEY"):
        r = requests.post("https://api.tavily.com/search", json={"query": query, "max_results": n},
                          headers={"Authorization": "Bearer " + _env("TAVILY_API_KEY")}, timeout=20)
        rows = [(x.get("title", ""), x.get("url", ""), x.get("content", "")) for x in r.json().get("results", [])]
    elif _env("BRAVE_API_KEY"):
        r = requests.get("https://api.search.brave.com/res/v1/web/search", params={"q": query, "count": n},
                         headers={"X-Subscription-Token": _env("BRAVE_API_KEY"), "Accept": "application/json"}, timeout=15)
        rows = [(x.get("title", ""), x.get("url", ""), re.sub(r"<[^>]+>", "", x.get("description", "")))
                for x in r.json().get("web", {}).get("results", [])]
    else:  # ohne Key: DuckDuckGo-HTML (kann sich aendern oder Anfragen begrenzen)
        r = requests.post("https://html.duckduckgo.com/html/", data={"q": query}, headers={"User-Agent": UA}, timeout=15)
        for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>(.*?)(?=<a[^>]+class="result__a"|$)',
                             r.text, re.S):
            href = m.group(1)
            if "uddg=" in href:
                href = unquote(parse_qs(urlparse(href if href.startswith("http") else "https:" + href).query).get("uddg", [href])[0])
            sn = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', m.group(3), re.S)
            clean = lambda s: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()
            rows.append((clean(m.group(2)), href, clean(sn.group(1)) if sn else ""))
    rows = [r for r in rows if r[1]][:n]
    if not rows:
        return "No results (or the search is not reachable right now). Phrase the search differently."
    return "\n".join(f"{i}. {t}\n   {u}\n   {_clip(s, 300)}" for i, (t, u, s) in enumerate(rows, 1))


def fetch_url(url):
    r, data, cut = safe_get(str(url or "").strip(), MAX_PAGE_BYTES)
    ctype = r.headers.get("Content-Type", "").lower()
    if "pdf" in ctype or data[:4] == b"%PDF":
        txt = pdf_text(data)
        if not txt.strip():
            return f"Source: {url}\nPDF without readable text (scan?). Save it with download_file."
        return (f"Source: {url} (PDF, {len(data) // 1024} KB)\n\n" + _clip(txt, PAGE_CHARS) +
                "\n\nFor the whole document: download_file, then read_file with offset.")
    if any(x in ctype for x in ("image/", "video/", "audio/", "zip", "octet-stream")):
        raise ToolError(f"No text content ({ctype.split(';')[0]}). Use image_save for images.")
    text = data.decode(r.encoding or "utf-8", errors="replace")
    if "html" in ctype or text.lstrip()[:1] == "<":
        title, body = html_to_text(text)
    else:
        title, body = "", text
    head = f"Source: {url}" + (f"\nTitle: {title}" if title else "") + ("\n(The page was very large, only the beginning was read)" if cut else "")
    return head + "\n\n" + _clip(body, PAGE_CHARS)


# ------------------------------------------------------------- Echter Browser (Recht "web")
BROWSER_TIMEOUT = int(_env("PCL_BROWSER_TIMEOUT", "30"))
_browser_lock = __import__("threading").Lock()  # Chromium braucht viel RAM: auf dem Pi immer nur eine Instanz


def browser_enabled():
    """browse_page gibt es nur, wenn Playwright installiert ist (install.sh --browser) und PCL_BROWSER nicht 0 ist."""
    if _env("PCL_BROWSER", "1") == "0":
        return False
    import importlib.util
    return importlib.util.find_spec("playwright") is not None


def _browser_exe():
    """Eigener Pfad (PCL_BROWSER_PATH) oder None = Chromium von Playwright."""
    p = _env("PCL_BROWSER_PATH")
    return p if p and Path(p).exists() else None


def browse_page(root, url, screenshot=False, wait=0, save=None):
    """Oeffnet eine Seite in Chromium (JavaScript an), gibt (Text, [Bild]) zurueck.
    Jede Anfrage der Seite (auch Skripte, Frames, XHR, WebSocket) muss auf eine oeffentliche Adresse gehen."""
    url = str(url or "").strip()
    u = urlparse(url)
    if u.scheme not in ("http", "https"):
        raise ToolError("Only http(s) addresses are allowed")
    check_public(u.hostname)
    from playwright.sync_api import Error as PwError, sync_playwright
    ok_hosts, blocked = {}, set()

    def public(link):
        p = urlparse(link)
        if p.scheme in ("data", "blob", "about"):
            return True
        if p.scheme not in ("http", "https", "ws", "wss"):
            return False
        h = p.hostname or ""
        if h not in ok_hosts:
            try:
                check_public(h)
                ok_hosts[h] = True
            except ToolError:
                ok_hosts[h] = False
        if not ok_hosts[h]:
            blocked.add(h)
        return ok_hosts[h]

    def route(r):
        if r.request.resource_type in ("media", "font") or not public(r.request.url):
            return r.abort()
        return r.continue_()

    def ws_route(ws):
        if public(ws.url):
            ws.connect_to_server()
        else:
            ws.close()

    wait = min(max(float(wait or 0), 0), 10)
    if not _browser_lock.acquire(timeout=BROWSER_TIMEOUT * 2):
        raise ToolError("The browser is busy right now, try again in a moment")
    try:
        with sync_playwright() as pw:
            # WebRTC darf nicht am Proxy/Routing vorbei ins LAN, Downloads gibt es nicht
            b = pw.chromium.launch(executable_path=_browser_exe(),
                                   args=["--force-webrtc-ip-handling-policy=disable_non_proxied_udp", "--disable-dev-shm-usage"])
            try:
                ctx = b.new_context(user_agent=UA.replace("compatible;", "X11; Linux aarch64; compatible;"),
                                    viewport={"width": 1280, "height": 900}, accept_downloads=False,
                                    service_workers="block", java_script_enabled=True, locale="de-DE")
                ctx.route("**/*", route)
                if hasattr(ctx, "route_web_socket"):
                    ctx.route_web_socket("**/*", ws_route)
                ctx.set_default_timeout(BROWSER_TIMEOUT * 1000)
                page = ctx.new_page()
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=BROWSER_TIMEOUT * 1000)
                    try:
                        page.wait_for_load_state("networkidle", timeout=min(8000, BROWSER_TIMEOUT * 1000))
                    except PwError:
                        pass  # Seiten mit Dauer-Verbindungen werden nie "idle"
                    if wait:
                        page.wait_for_timeout(wait * 1000)
                except PwError as e:
                    raise ToolError("The page could not be loaded: " + str(e).splitlines()[0][:200])
                final = page.url
                if not public(final):
                    raise ToolError("The page redirects to a local/private address")
                title = page.title()
                body = page.inner_text("body") if page.query_selector("body") else ""
                links = page.eval_on_selector_all(
                    "a[href]", "els => els.slice(0, 400).map(a => [a.innerText.trim().slice(0, 80), a.href])")
                shot = page.screenshot(type="jpeg", quality=70) if screenshot or save else None
            finally:
                b.close()
    finally:
        _browser_lock.release()
    body = re.sub(r"\n\s*\n+", "\n\n", body or "").strip()
    seen_l, rows = set(), []
    for t, h in links:
        if t and h.startswith("http") and h not in seen_l:
            seen_l.add(h)
            rows.append(f"- {t} -> {h}")
        if len(rows) >= 25:
            break
    out = f"Source: {final} (opened in the browser, JavaScript on)" + (f"\nTitle: {title}" if title else "")
    if blocked:
        out += "\n(Blocked because local/private: " + ", ".join(sorted(blocked))[:200] + ")"
    out += "\n\n" + (_clip(body, PAGE_CHARS) or "(no visible text)")
    if rows:
        out += "\n\nLinks:\n" + "\n".join(rows)
    imgs = []
    if shot:
        imgs = [("image/jpeg", base64.b64encode(shot).decode())]
        if save:
            name = re.sub(r"[^\w-]+", "-", str(save)).strip("-")[:60] or "seite"
            d = Path(root) / "assets" / "screenshots"
            d.mkdir(parents=True, exist_ok=True)
            (d / f"{name}.jpg").write_bytes(shot)
            out += f"\n\nScreenshot saved: assets/screenshots/{name}.jpg"
    return out, imgs


def image_search(query, n=6):
    query = str(query or "").strip()[:200]
    if not query:
        raise ToolError("query missing")
    n = min(max(int(n or 6), 1), 10)
    items = []
    if _env("PEXELS_API_KEY"):
        r = requests.get("https://api.pexels.com/v1/search", params={"query": query, "per_page": n},
                         headers={"Authorization": _env("PEXELS_API_KEY")}, timeout=15)
        for x in r.json().get("photos", []):
            items.append((x["src"].get("large2x") or x["src"]["large"], x.get("alt") or query,
                          x.get("photographer", "?"), "Pexels-Lizenz (frei nutzbar)", x.get("url", "")))
    else:  # Openverse: Millionen frei lizenzierte Bilder, kein Key noetig
        r = requests.get("https://api.openverse.org/v1/images/",
                         params={"q": query, "page_size": n, "license_type": "commercial"},
                         headers={"User-Agent": UA}, timeout=20)
        for x in r.json().get("results", []):
            lic = f"CC {x.get('license', '?').upper()} {x.get('license_version', '')}".strip()
            items.append((x.get("url", ""), x.get("title") or query, x.get("creator") or "unbekannt", lic,
                          x.get("foreign_landing_url", "")))
    items = [i for i in items if i[0]]
    if not items:
        return "No images found. Try English or more general search terms."
    return "\n".join(f"{i}. {t}\n   Image URL: {u}\n   Author: {c} | Licence: {lic} | Page: {page}"
                     for i, (u, t, c, lic, page) in enumerate(items, 1)) + \
        "\nNote: for CC licences name the author in the imprint/image credits. Then save with image_save."


_IMG_TYPES = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif", "image/webp": "webp", "image/svg+xml": "svg"}


def _sniff(data):
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data.lstrip()[:5] in (b"<?xml", b"<svg ") or b"<svg" in data[:600]:
        return "svg"
    return None


# ------------------------------------------------------------------------- Video per KI (Google; weitere Anbieter in video_providers.py)
MAX_VIDEO_BYTES = 300_000_000
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _vp():
    import video_providers  # erst hier: video_providers importiert dieses Modul
    return video_providers


def _vp_on(flag):
    """Schalter aus video_providers; fehlt die Datei, sind die Video-/Tonwerkzeuge einfach unsichtbar."""
    try:
        return bool(getattr(_vp(), flag)())
    except ImportError:
        return False


def video_enabled():
    """Standard aus: erst mit VIDEO_PROVIDER=<anbieter>[,<anbieter>...] (kostet pro Clip)."""
    return _vp_on("providers")


def _gemini_key():
    key = _env("GEMINI_API_KEY").split(",")[0].strip()
    if not key:
        raise ToolError("VIDEO_PROVIDER=gemini, but GEMINI_API_KEY is missing")
    return key


def _gjson(r):
    try:
        d = r.json()
    except ValueError:
        d = {}
    if r.status_code >= 400:
        msg = (d.get("error") or {}).get("message") if isinstance(d.get("error"), dict) else None
        raise ToolError(f"Video API answers with HTTP {r.status_code}: " + _clip(msg or r.text, 300))
    return d


def _video_image(root, rel):
    f = _inside_existing(root, rel)
    data = f.read_bytes()
    mime = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}.get(_sniff(data))
    if not mime:
        raise ToolError(f"'{rel}' is not an image (PNG, JPEG, WEBP)")
    return mime, base64.b64encode(data).decode()


def _download_video(url, key, dst):
    with requests.get(url, headers={"x-goog-api-key": key}, stream=True, timeout=300, allow_redirects=True) as r:
        if r.status_code >= 400:
            raise ToolError(f"Video-Download fehlgeschlagen (HTTP {r.status_code})")
        size = 0
        with open(dst, "wb") as fh:
            for chunk in r.iter_content(1 << 16):
                size += len(chunk)
                if size > MAX_VIDEO_BYTES:
                    raise ToolError("Video is too large")
                fh.write(chunk)


def _omni_video(key, model, call, root, deadline):
    rf = {"type": "video"}
    if call.get("aspect") in ("16:9", "9:16"):
        rf["aspect_ratio"] = call["aspect"]
    if call.get("resolution") in ("360p", "720p", "1080p", "4k"):
        rf["resolution"] = call["resolution"]
    prompt = str(call.get("prompt") or "").strip()[:2000]
    body = {"model": model, "response_format": rf, "input": prompt}
    if call.get("image"):
        mime, b64 = _video_image(root, call["image"])
        body["input"] = [{"type": "image", "mime_type": mime, "data": b64}, {"type": "text", "text": prompt}]
    if call.get("continue_id"):
        body["previous_interaction_id"] = str(call["continue_id"])[:200]
    d = _gjson(requests.post(GEMINI_BASE + "/interactions", headers={"x-goog-api-key": key}, json=body, timeout=900))
    while d.get("status") not in (None, "completed") and time.time() < deadline:
        if d.get("status") in ("failed", "cancelled", "incomplete"):
            raise ToolError("Video was not created: " + _clip(json.dumps(d.get("error") or d.get("status")), 300))
        time.sleep(10)
        d = _gjson(requests.get(f"{GEMINI_BASE}/interactions/{d.get('id')}", headers={"x-goog-api-key": key}, timeout=300))
    for step in d.get("steps") or []:
        if step.get("type") != "model_output":
            continue
        for c in step.get("content") or []:
            if c.get("type") == "video" and c.get("data"):
                return base64.b64decode(c["data"]), None, d.get("id")
            if c.get("type") == "video" and c.get("uri"):
                return None, c["uri"], d.get("id")
    raise ToolError("No video in the answer (prompt possibly rejected by the safety filter): " + _clip(json.dumps(d)[:600], 300))


def _veo_video(key, model, call, root, deadline):
    inst = {"prompt": str(call.get("prompt") or "").strip()[:2000]}
    if call.get("image"):
        mime, b64 = _video_image(root, call["image"])
        inst["image"] = {"bytesBase64Encoded": b64, "mimeType": mime}
    params = {}
    if call.get("aspect") in ("16:9", "9:16"):
        params["aspectRatio"] = call["aspect"]
    if call.get("resolution") in ("720p", "1080p"):
        params["resolution"] = call["resolution"]
    op = _gjson(requests.post(f"{GEMINI_BASE}/models/{model}:predictLongRunning", headers={"x-goog-api-key": key},
                              json={"instances": [inst], "parameters": params}, timeout=120))
    while not op.get("done"):
        if time.time() > deadline:
            raise ToolError("Time limit for the video creation reached (PCL_VIDEO_TIMEOUT)")
        time.sleep(10)
        op = _gjson(requests.get(f"{GEMINI_BASE}/{op['name']}", headers={"x-goog-api-key": key}, timeout=60))
    if op.get("error"):
        raise ToolError("Video was not created: " + _clip(json.dumps(op["error"]), 300))
    samples = ((op.get("response") or {}).get("generateVideoResponse") or {}).get("generatedSamples") or []
    uri = ((samples[0] if samples else {}).get("video") or {}).get("uri")
    if not uri:
        raise ToolError("No video in the answer (prompt possibly rejected by the safety filter)")
    return None, uri, None


def video_generate(root, call):
    return _vp().generate(root, call)


# ------------------------------------------------- Browser-Makros des Besitzers (MagicLight, Flow ...)
# Der Besitzer legt in macros/<site>.py ein Playwright-Skript ab (aufgenommen mit "playwright codegen", siehe macros/README.md).
# Agenten waehlen nur den Namen und den Text; das Skript selbst kommt nie von einem Agenten.
# Es bekommt PCL_PROMPT, PCL_OUTPUT (leerer Ordner fuer das Ergebnis) und PCL_STORAGE (gespeicherte Anmeldung, macros/<site>.json).


def macro_dir():
    return Path(_env("PCL_MACRO_DIR") or Path(__file__).resolve().parent / "macros")


def macro_sites():
    """Standard aus: erst mit PCL_MACROS=1, Playwright und mindestens einem Skript in macros/ (Vorlagen zaehlen nicht)."""
    if _env("PCL_MACROS", "0") != "1":
        return []
    import importlib.util
    if importlib.util.find_spec("playwright") is None:
        return []
    d = macro_dir()
    if not d.is_dir():
        return []
    return sorted(f.stem for f in d.glob("*.py") if re.fullmatch(r"[a-z0-9_-]+", f.stem) and not f.stem.startswith("vorlage"))


_macro_lock = __import__("threading").Lock()  # Chromium braucht viel RAM: immer nur ein Makro gleichzeitig


def site_macro(root, call):
    sites = macro_sites()
    site = str(call.get("site") or "").strip().lower()
    if site not in sites:
        raise ToolError(f"Unknown site '{site}'. Available: {', '.join(sites) or 'none'}")
    prompt = str(call.get("prompt") or "").strip()[:8000]
    if not prompt:
        raise ToolError("prompt missing")
    d = macro_dir()
    timeout = int(_env("PCL_MACRO_TIMEOUT", "3600") or 3600)
    if not _macro_lock.acquire(timeout=60):
        raise ToolError("Another macro is running right now, try again later")
    try:
        out_dir = root / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".tmp-macro-", dir=out_dir) as tmp:
            # Minimale Umgebung: keine Schluessel aus .env an das Skript
            env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG", "DISPLAY", "PLAYWRIGHT_BROWSERS_PATH",
                                                      "SYSTEMROOT", "TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA", "APPDATA")
                   if k in os.environ}
            env.update(PCL_PROMPT=prompt, PCL_OUTPUT=tmp, PCL_STORAGE=str(d / f"{site}.json"),
                       PCL_BROWSER_PATH=_env("PCL_BROWSER_PATH"), PYTHONIOENCODING="utf-8")
            try:
                r = subprocess.run([sys.executable, str(d / f"{site}.py")], cwd=tmp, env=env, capture_output=True,
                                   text=True, encoding="utf-8", errors="replace", timeout=timeout)
            except subprocess.TimeoutExpired:
                raise ToolError(f"Macro '{site}' exceeded the time limit (PCL_MACRO_TIMEOUT={timeout} s)")
            log = _clip((r.stdout or "") + (r.stderr or ""), 600).strip()
            if r.returncode != 0:
                shot = next((f for f in Path(tmp).glob("*.png") if f.is_file() and not f.is_symlink()), None)
                hint = ""
                if shot:  # Bildschirmfoto der Vorlage bleibt fuer den Besitzer erhalten
                    dst = _out_path(root, {"name": f"{site}-error"}, site, "png")
                    shutil.move(str(shot), dst)
                    hint = f" Screenshot: {_rel(root, dst)}."
                raise ToolError(f"Macro '{site}' failed (code {r.returncode}). The site may have changed or "
                                f"the sign-in has expired.{hint} Output: {log or '(empty)'}")
            files = sorted((f for f in Path(tmp).rglob("*") if f.is_file() and not f.is_symlink()), key=lambda f: f.stat().st_size, reverse=True)
            if not files:
                raise ToolError(f"Macro '{site}' ran through but saved no file. Output: {log or '(empty)'}")
            made = []
            for i, f in enumerate(files[:5]):
                if f.stat().st_size > MAX_VIDEO_BYTES:
                    continue
                ext = re.sub(r"[^a-z0-9]", "", f.suffix.lower())[:5] or "mp4"
                dst = _out_path(root, {"name": call.get("name") if i == 0 else f"{call.get('name') or site}-{i + 1}"}, site, ext)
                shutil.move(str(f), dst)
                made.append(_rel(root, dst))
            if not made:
                raise ToolError("The saved file is too large")
    finally:
        _macro_lock.release()
    return f"Result of {site}: {' | '.join(made)} " + (f"(note from the macro: {log[-300:]})" if log else "")


def _safe_name(name, default):
    n = re.sub(r"[^a-z0-9_-]+", "-", str(name or "").lower()).strip("-")[:50]
    return n or default


def _store_image(root, data, name, default):
    ext = _sniff(data)
    if not ext:
        raise ToolError("This is not a valid image file (PNG, JPG, GIF, WEBP or SVG).")
    assets = root / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    base, i = _safe_name(name, default), 0
    while True:
        target = assets / (f"{base}{'' if not i else '-' + str(i)}.{ext}")
        if not target.exists():
            break
        i += 1
    target.write_bytes(data)
    return f"assets/{target.name}", len(data)


def image_save(root, url, name="", path=""):
    r, data, cut = safe_get(str(url or "").strip(), MAX_IMAGE_BYTES)
    if cut:
        raise ToolError(f"Image is larger than {MAX_IMAGE_BYTES // 1_000_000} MB")
    target = _img_target(Path(root), {"path": path}, _sniff(data) or "png") if str(path or "").strip() else None
    if target:
        if _sniff(data) not in ("png", "jpg", "webp"):
            raise ToolError("The address does not deliver a PNG, JPG or WEBP image")
        target.write_bytes(data)
        rel, size = _rel(Path(root), target), len(data)
    else:
        rel, size = _store_image(root, data, name, "bild")
    return f"Saved: {rel} ({size // 1024} KB). Embed it in HTML like this: <img src=\"{rel}\" alt=\"...\">"


IMAGE_DIRS = ("assets", "output", "karten")  # erlaubte Zielordner fuer image_generate
MAX_REF_IMAGES = 4
# Format -> (OpenAI-Groesse, Gemini-Seitenverhaeltnis, Pollinations-Breite/Hoehe)
_IMG_FORMATS = {"quadrat": ("1024x1024", "1:1", (1024, 1024)), "hoch": ("1024x1536", "2:3", (1024, 1536)),
                "quer": ("1536x1024", "3:2", (1536, 1024))}
_IMG_ALIASES = {"1:1": "quadrat", "square": "quadrat", "1024x1024": "quadrat", "2:3": "hoch", "portrait": "hoch",
                "hochformat": "hoch", "1024x1536": "hoch", "3:2": "quer", "landscape": "quer", "querformat": "quer",
                "1536x1024": "quer"}


def _img_format(call):
    f = str(call.get("format") or call.get("size") or "").strip().lower()
    if not f:
        return _IMG_FORMATS["quer" if _env("IMAGE_PROVIDER", "pollinations").lower() == "pollinations" else "quadrat"]
    f = _IMG_ALIASES.get(f, f)
    if f not in _IMG_FORMATS:
        raise ToolError("format must be square, portrait or landscape")
    return _IMG_FORMATS[f]


def _ref_images(root, refs):
    """Referenzbilder aus dem Projektordner: [(dateiname, bytes, mime)]."""
    if isinstance(refs, str):
        refs = [refs]
    refs = [str(r).strip() for r in (refs or []) if str(r or "").strip()]
    if len(refs) > MAX_REF_IMAGES:
        raise ToolError(f"At most {MAX_REF_IMAGES} reference images")
    out = []
    for rel in refs:
        f = _img_path(root, rel)
        if not f:
            raise ToolError(f"Reference image not found: {rel}")
        data = f.read_bytes()
        if len(data) > MAX_IMAGE_BYTES:
            raise ToolError(f"Reference image too large (max. {MAX_IMAGE_BYTES // 1_000_000} MB): {rel}")
        ext = _sniff(data)
        if ext not in ("png", "jpg", "webp"):
            raise ToolError(f"Reference image must be PNG, JPG or WEBP: {rel}")
        out.append((f"ref{len(out) + 1}.{ext}", data, {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}[ext]))
    return out


def _img_target(root, call, ext):
    """Zielpfad: "path" (assets/, output/ oder karten/, wird ueberschrieben) oder assets/<name>.<ext> (neu)."""
    path = str(call.get("path") or "").strip()
    if not path:
        return None
    try:
        t = _inside(root, path)
    except ValueError:
        raise ToolError("Path is outside the project folder")
    parts = t.relative_to(Path(root).resolve()).parts
    if len(parts) < 2 or parts[0] not in IMAGE_DIRS or any(p.startswith(".") for p in parts):
        raise ToolError("path must be in " + ", ".join(d + "/" for d in IMAGE_DIRS) + ", e.g. karten/bilder/k01.png")
    t = t.with_name(_safe_name(t.stem, "bild") + "." + ext)
    t.parent.mkdir(parents=True, exist_ok=True)
    return t


GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"  # breit verfuegbar, Abschaltung fruehestens 2027-03-15; neuer: gemini-nano-banana-2.1


def _gen_gemini(prompt, refs, fmt, call):
    key = _env("GEMINI_API_KEY").split(",")[0].strip()
    if not key:
        raise ToolError("IMAGE_PROVIDER=gemini, but GEMINI_API_KEY is missing")
    model = _model_env("IMAGE_MODEL", GEMINI_IMAGE_MODEL)
    parts = [{"text": prompt}] + [{"inline_data": {"mime_type": mime, "data": base64.b64encode(d).decode()}} for _, d, mime in refs]
    img_cfg = {"aspectRatio": fmt[1]}
    size = _env("IMAGE_SIZE").upper()  # 1K | 2K | 4K, leer = Standard des Modells
    if size:
        img_cfg["imageSize"] = size
    r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                      headers={"x-goog-api-key": key}, timeout=180,
                      json={"contents": [{"parts": parts}],
                            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"], "imageConfig": img_cfg}})
    try:
        cands = r.json().get("candidates") or [{}]
    except ValueError:
        cands = [{}]
    for part in (cands[0].get("content") or {}).get("parts", []):
        blob = part.get("inlineData") or part.get("inline_data")
        if blob:
            return base64.b64decode(blob["data"])
    hint = " (image models usually need a Google account with billing)" if r.status_code == 429 else ""
    raise ToolError(f"Gemini ({model}) returned no image (HTTP {r.status_code}){hint}: " + _clip(r.text, 300))


def _gen_openai(prompt, refs, fmt, call):
    key = _env("OPENAI_API_KEY").split(",")[0].strip()
    if not key:
        raise ToolError("IMAGE_PROVIDER=openai, but OPENAI_API_KEY is missing")
    base = _env("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    fields = {"model": _model_env("IMAGE_MODEL", "gpt-image-1"), "prompt": prompt, "size": fmt[0]}
    quality = str(call.get("quality") or _env("IMAGE_QUALITY")).strip().lower()
    if quality:
        if quality not in ("low", "medium", "high", "auto"):
            raise ToolError("quality must be low, medium, high or auto")
        fields["quality"] = quality
    head = {"Authorization": "Bearer " + key}
    if refs:  # Bearbeiten-Endpunkt: Referenzbilder halten Figuren und Stil gleich
        r = requests.post(base + "/images/edits", headers=head, timeout=300, data=fields,
                          files=[("image[]", (n, d, mime)) for n, d, mime in refs])
    else:
        r = requests.post(base + "/images/generations", headers=head, timeout=300, json=fields)
    try:
        body = r.json()
    except ValueError:
        body = {}
    if r.status_code >= 400 or body.get("error"):
        msg = (body.get("error") or {}).get("message") if isinstance(body.get("error"), dict) else None
        raise ToolError(f"OpenAI image API ({fields['model']}): HTTP {r.status_code} " + _clip(msg or r.text, 300))
    d = (body.get("data") or [{}])[0]
    if d.get("b64_json"):
        return base64.b64decode(d["b64_json"])
    if d.get("url"):
        return safe_get(d["url"], MAX_IMAGE_BYTES)[1]
    raise ToolError("Image provider returned no image: " + _clip(r.text, 300))


OPENROUTER_IMAGE_MODEL = "google/gemini-2.5-flash-image"


def _gen_openrouter(prompt, refs, fmt, call):
    """OpenRouter Image API (/api/v1/images): ein Key, viele Bildmodelle, Referenzbilder als data-URL."""
    key = _env("OPENROUTER_API_KEY").split(",")[0].strip()
    if not key:
        raise ToolError("IMAGE_PROVIDER=openrouter, but OPENROUTER_API_KEY is missing")
    model = _model_env("IMAGE_MODEL", OPENROUTER_IMAGE_MODEL)
    body = {"model": model, "prompt": prompt, "aspect_ratio": fmt[1], "output_format": "png"}
    size = _env("IMAGE_SIZE").upper()
    if size:
        body["resolution"] = size
    if refs:
        body["input_references"] = [{"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64.b64encode(d).decode()}"}}
                                    for _, d, mime in refs]
    r = requests.post("https://openrouter.ai/api/v1/images", headers={"Authorization": "Bearer " + key}, timeout=300, json=body)
    try:
        data = r.json()
    except ValueError:
        data = {}
    if r.status_code >= 400 or data.get("error"):
        err = data.get("error")
        msg = err.get("message") if isinstance(err, dict) else None
        hint = " (check your OpenRouter credit)" if r.status_code == 402 else ""
        raise ToolError(f"OpenRouter ({model}): HTTP {r.status_code}{hint} " + _clip(msg or r.text, 300))
    d = (data.get("data") or [{}])[0]
    if d.get("b64_json"):
        return base64.b64decode(d["b64_json"])
    if d.get("url"):
        return safe_get(d["url"], MAX_IMAGE_BYTES)[1]
    raise ToolError(f"OpenRouter ({model}) returned no image: " + _clip(r.text, 300))


POLLINATIONS_MODEL = "black-forest-labs/flux.2-klein-4b"  # mit Key: guenstig, nimmt bis zu 4 Referenzbilder


def _gen_pollinations(prompt, refs, fmt, call):
    """Ohne POLLINATIONS_API_KEY: alter Gratis-Endpunkt (nicht mehr dokumentiert, ohne Referenzbilder).
    Mit Key (enter.pollinations.ai, Pollen-Guthaben): gen.pollinations.ai, Modell waehlbar, Referenzbilder als data-URL."""
    key = _env("POLLINATIONS_API_KEY").split(",")[0].strip()
    w, h = fmt[2]
    if not key:
        if refs:
            raise ToolError("Reference images only work with IMAGE_PROVIDER=openai, gemini, openrouter, sdcpp, cloudflare, nvidia "
                            "or with POLLINATIONS_API_KEY (set it in .env)")
        params = {"width": w, "height": h, "nologo": "true", "seed": int(time.time()) % 100000}
        model = _model_env("POLLINATIONS_MODEL", "")
        if model:
            params["model"] = model
        r = requests.get("https://image.pollinations.ai/prompt/" + quote(prompt[:800]),
                         params=params, headers={"User-Agent": UA}, timeout=120)
        if r.status_code >= 400:
            raise ToolError(f"Image generator answers with HTTP {r.status_code}"
                            + (" (model needs POLLINATIONS_API_KEY)" if model and r.status_code in (401, 402, 403) else ""))
        return r.content
    model = _model_env("POLLINATIONS_MODEL", POLLINATIONS_MODEL)
    body = {"model": model, "prompt": prompt, "size": f"{w}x{h}", "response_format": "b64_json"}
    if refs:  # als Liste, ein einzelner data-URL-String wird am Komma zerlegt
        body["image"] = [f"data:{mime};base64,{base64.b64encode(d).decode()}" for _, d, mime in refs]
    r = requests.post("https://gen.pollinations.ai/v1/images/generations", timeout=300, json=body,
                      headers={"Authorization": "Bearer " + key, "User-Agent": UA})
    try:
        data = r.json()
    except ValueError:
        data = {}
    if r.status_code >= 400 or data.get("error"):
        err = data.get("error")
        msg = err.get("message") if isinstance(err, dict) else err
        hint = {401: " (POLLINATIONS_API_KEY check the key)", 402: " (pollen credit used up, enter.pollinations.ai)"}.get(r.status_code, "")
        raise ToolError(f"Pollinations ({model}): HTTP {r.status_code}{hint} " + _clip(str(msg or r.text), 300))
    d = (data.get("data") or [{}])[0]
    if d.get("b64_json"):
        return base64.b64decode(d["b64_json"])
    if d.get("url"):
        return safe_get(d["url"], MAX_IMAGE_BYTES)[1]
    raise ToolError(f"Pollinations ({model}) returned no image: " + _clip(r.text, 300))


_heavy_lock = __import__("threading").Lock()  # Bildrechner und Blender (film_studio) nie gleichzeitig: 8 GB RAM


def _sdcpp_size(fmt):
    """Laengste Seite = SDCPP_SIZE (Std. 1024), beide Seiten auf Vielfache von 16 (CPU-Rechner: kleiner = schneller)."""
    try:
        side = max(256, min(2048, int(_env("SDCPP_SIZE", "1024"))))
    except ValueError:
        side = 1024
    return _scaled(fmt, side)


def _gen_sdcpp(prompt, refs, fmt, call):
    """Eigener Bildrechner mit stable-diffusion.cpp (sd-server, z. B. FLUX.2 klein 4B auf einem Laptop im Heimnetz).
    Referenzbilder gehen als extra_images mit. Langsam (Minuten je Bild), deshalb langes Zeitlimit und immer nur ein Bild."""
    url = _env("SDCPP_URL").strip().rstrip("/")
    if not url:
        raise ToolError("IMAGE_PROVIDER=sdcpp, but SDCPP_URL is missing (e.g. http://192.168.1.50:1234)")
    w, h = _sdcpp_size(fmt)
    try:
        steps, cfg = int(_env("SDCPP_STEPS", "4")), float(_env("SDCPP_CFG", "1.0"))
        timeout = int(_env("SDCPP_TIMEOUT", "1800"))
    except ValueError:
        raise ToolError("SDCPP_STEPS, SDCPP_CFG and SDCPP_TIMEOUT must be numbers")
    body = {"prompt": prompt, "width": w, "height": h, "steps": steps, "cfg_scale": cfg,
            "seed": int(time.time() * 1000) % 2_000_000_000}  # fester Wert: seed -1 liefert bei manchen Builds nichts
    if refs:
        body["extra_images"] = [f"data:{mime};base64,{base64.b64encode(d).decode()}" for _, d, mime in refs]
    with _heavy_lock:
        r = requests.post(url + "/sdapi/v1/txt2img", json=body, timeout=(10, timeout))
    try:
        data = r.json()
    except ValueError:
        data = {}
    if r.status_code >= 400:
        raise ToolError(f"Image computer ({url}): HTTP {r.status_code} " + _clip(str(data.get("error") or r.text), 300))
    imgs = data.get("images") or []
    if not imgs:
        raise ToolError("Image computer returned no image: " + _clip(r.text, 300))
    b64 = str(imgs[0])
    return base64.b64decode(b64.split(",", 1)[1] if b64.startswith("data:") else b64)


def _scaled(fmt, side=1024, step=16):
    """Format auf laengste Seite `side` bringen, beide Seiten Vielfache von `step`."""
    w, h = fmt[2]
    k = side / max(w, h)
    return max(step, int(w * k) // step * step), max(step, int(h * k) // step * step)


def _b64_image(data):
    """Bild aus typischen JSON-Antworten (artifacts/result/data/image) holen."""
    if isinstance(data, dict):
        for k in ("artifacts", "data", "images"):
            v = data.get(k)
            if isinstance(v, list) and v:
                got = _b64_image(v[0])
                if got:
                    return got
        if isinstance(data.get("result"), dict):
            return _b64_image(data["result"])
        for k in ("base64", "b64_json", "image"):
            v = data.get(k)
            if isinstance(v, str) and len(v) > 64:
                return base64.b64decode(v.split(",", 1)[1] if v.startswith("data:") else v)
    if isinstance(data, str) and len(data) > 64:
        return base64.b64decode(data.split(",", 1)[1] if data.startswith("data:") else data)
    return None


def _small_ref(d, mime, side=512):
    """Referenzbild fuer Anbieter mit Groessengrenze verkleinern (Cloudflare FLUX.2: unter 512 px)."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(d))
        if max(im.size) < side:
            return d, mime
        im.thumbnail((side - 1, side - 1))
        out = io.BytesIO()
        im.convert("RGB").save(out, "PNG")
        return out.getvalue(), "image/png"
    except Exception:
        return d, mime


def _api_error(name, model, r, hint=""):
    try:
        body = r.json()
        msg = body.get("detail") or body.get("error") or body.get("errors") or body
    except ValueError:
        msg = r.text
    raise ToolError(f"{name} ({model}): HTTP {r.status_code}{hint} " + _clip(str(msg), 300))


NVIDIA_IMAGE_MODEL = "black-forest-labs/flux.1-schnell"


def _gen_nvidia(prompt, refs, fmt, call):
    """NVIDIA NIM (build.nvidia.com): POST ai.api.nvidia.com/v1/genai/<modell>. Referenzbild nur bei Bearbeitungsmodellen
    (z. B. black-forest-labs/flux.1-kontext-dev), dort genau eins."""
    key = _env("NVIDIA_API_KEY").split(",")[0].strip()
    if not key:
        raise ToolError("IMAGE_PROVIDER=nvidia, but NVIDIA_API_KEY is missing")
    model = _model_env("IMAGE_MODEL", NVIDIA_IMAGE_MODEL)
    body = {"prompt": prompt[:10000], "seed": int(time.time() * 1000) % 2_000_000_000}
    if "schnell" in model:
        body["steps"] = 4  # schnell kann nur 1024x1024
    else:
        body["width"], body["height"] = _scaled(fmt, 1024, 64)
    if refs:
        if len(refs) > 1:
            raise ToolError("NVIDIA image models take at most 1 reference image")
        _, d, mime = refs[0]
        body["image"] = f"data:{mime};base64,{base64.b64encode(d).decode()}"
    r = requests.post(f"https://ai.api.nvidia.com/v1/genai/{model}", timeout=300, json=body,
                      headers={"Authorization": "Bearer " + key, "Accept": "application/json"})
    if r.status_code >= 400:
        _api_error("NVIDIA", model, r, " (model cannot take reference images?)" if refs and r.status_code == 422 else "")
    img = _b64_image(r.json())
    if not img:
        raise ToolError(f"NVIDIA ({model}) returned no image: " + _clip(r.text, 300))
    return img


CLOUDFLARE_IMAGE_MODEL = "@cf/black-forest-labs/flux-2-klein-4b"


def _gen_cloudflare(prompt, refs, fmt, call):
    """Cloudflare Workers AI: FLUX.2-Modelle per Multipart (Referenzbilder input_image_0..3, unter 512 px),
    aeltere Modelle (z. B. flux-1-schnell) per JSON ohne Referenzen."""
    acc, key = _env("CF_ACCOUNT_ID").strip(), _env("CF_API_TOKEN").split(",")[0].strip()
    if not acc or not key:
        raise ToolError("IMAGE_PROVIDER=cloudflare, but CF_ACCOUNT_ID or CF_API_TOKEN is missing")
    model = _model_env("IMAGE_MODEL", CLOUDFLARE_IMAGE_MODEL)
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{model}"
    w, h = _scaled(fmt, 1024)
    headers = {"Authorization": "Bearer " + key}
    if "flux-2" in model:
        form = {"prompt": (None, prompt), "width": (None, str(w)), "height": (None, str(h))}
        for i, (name, d, mime) in enumerate(refs):
            d, mime = _small_ref(d, mime)
            form[f"input_image_{i}"] = (name, d, mime)
        r = requests.post(url, headers=headers, files=form, timeout=300)
    else:
        if refs:
            raise ToolError(f"{model} cannot take reference images, choose a FLUX.2 model for that (IMAGE_MODEL)")
        r = requests.post(url, headers=headers, json={"prompt": prompt, "width": w, "height": h}, timeout=300)
    if r.status_code >= 400:
        _api_error("Cloudflare", model, r)
    if r.headers.get("content-type", "").startswith("image/"):
        return r.content
    img = _b64_image(r.json())
    if not img:
        raise ToolError(f"Cloudflare ({model}) returned no image: " + _clip(r.text, 300))
    return img


HF_IMAGE_MODEL = "black-forest-labs/FLUX.1-schnell"


def _gen_hf(prompt, refs, fmt, call):
    """Hugging Face Inference (router.huggingface.co/<anbieter>/models/<modell>), Antwort = Bilddatei. Ohne Referenzbilder."""
    key = _env("HF_TOKEN").split(",")[0].strip()
    if not key:
        raise ToolError("IMAGE_PROVIDER=hf, but HF_TOKEN is missing")
    if refs:
        raise ToolError("Hugging Face (text to image) cannot take reference images here")
    model = _model_env("IMAGE_MODEL", HF_IMAGE_MODEL)
    sub = _env("HF_IMAGE_PROVIDER", "hf-inference").strip().strip("/") or "hf-inference"
    w, h = _scaled(fmt, 1024)
    r = requests.post(f"https://router.huggingface.co/{sub}/models/{model}", timeout=300,
                      headers={"Authorization": "Bearer " + key, "Accept": "image/png"},
                      json={"inputs": prompt, "parameters": {"width": w, "height": h}})
    if r.status_code >= 400:
        _api_error("Hugging Face", model, r, " (Guthaben aufgebraucht)" if r.status_code == 402 else "")
    if r.headers.get("content-type", "").startswith("image/"):
        return r.content
    try:
        img = _b64_image(r.json())
    except ValueError:
        img = None
    if not img:
        raise ToolError(f"Hugging Face ({model}) returned no image: " + _clip(r.text, 300))
    return img


# ------------------------------------------------------------------ Canva ueber die Claude-CLI (Konnektor aus dem claude.ai-Abo)
# Der Server selbst kommt nicht an Canva. Das kann nur ein Agent mit dem Anbieter claude_cli und PCL_CLAUDE_CONNECTORS=Canva.
# Hier gibt es nur zwei Hilfen: canva_upload (Referenzbild in den Upload-Link von Canva schicken) und klare Hinweise.
CANVA_UPLOAD_HOSTS = ("canva.com", "canva-api.com", "canva.cn")
CANVA_MAX_UPLOAD = 25_000_000

CANVA_HOWTO = ("Create the image through Canva with your AI's own Canva connection, ALWAYS with the reference image(s): "
               "1) Canva create-upload-url, 2) canva_upload {\"path\": \"<reference image in the project>\", \"upload_url\": \"<url>\"} -> media ID, "
               "3) Canva generate-image with the prompt and imageReferences [{\"type\": \"MEDIA\", \"id\": \"<media ID>\"}], "
               "4) poll get-generate-image-job until SUCCESS, 5) image_save {\"url\": \"<image URL>\", \"path\": \"<target>\"}, 6) view_image. "
               "Never create characters or landscapes without the reference image.")


def canva_enabled():
    import ai_links
    return any(c.strip().lower() == "canva" for c in ai_links.connector_names())


def _canva_host_ok(host):
    host = (host or "").lower().rstrip(".")
    extra = [h.strip().lower() for h in _env("PCL_CANVA_UPLOAD_HOSTS").split(",") if h.strip()]
    return any(host == h or host.endswith("." + h) for h in list(CANVA_UPLOAD_HOSTS) + extra)


def canva_upload(root, path, upload_url):
    """Schickt ein Bild aus dem Projektordner roh (application/octet-stream) an einen Upload-Link von Canva."""
    if not canva_enabled():
        raise ToolError("Canva is not connected (owner: PCL_CLAUDE_CONNECTORS=Canva in .env, see docs/ki-verbindungen.md)")
    f = _img_path(Path(root), str(path or "").strip())
    if not f:
        raise ToolError(f"Image not found in the project folder: {path}")
    data = f.read_bytes()
    if len(data) > CANVA_MAX_UPLOAD:
        raise ToolError(f"Image too large for the upload (max. {CANVA_MAX_UPLOAD // 1_000_000} MB)")
    if _sniff(data) not in ("png", "jpg", "webp"):
        raise ToolError("Only PNG, JPG or WEBP images can be uploaded")
    url = str(upload_url or "").strip()
    u = urlparse(url)
    if u.scheme != "https" or not _canva_host_ok(u.hostname):
        raise ToolError(f"upload_url must be an https address of Canva (got host '{u.hostname or ''}'). "
                        "Take it unchanged from Canva create-upload-url. Owner can allow more hosts with PCL_CANVA_UPLOAD_HOSTS.")
    check_public(u.hostname)
    r = requests.post(url, data=data, headers={"Content-Type": "application/octet-stream", "User-Agent": UA},
                      timeout=(10, 120), allow_redirects=False)
    if r.status_code >= 400:
        raise ToolError(f"Canva upload failed: HTTP {r.status_code} {_clip(r.text, 300)}. The link is single-use: "
                        "get a new one with create-upload-url and try once more.")
    return (f"Uploaded {_rel(Path(root), f)} to Canva ({len(data) // 1024} KB). Canva answered: {_clip(r.text, 1500)}\n"
            "Use the media ID from this answer in generate-image imageReferences.")


def image_generate(root, call):
    prompt = str(call.get("prompt") or "").strip()[:4000]
    if not prompt:
        raise ToolError("prompt missing")
    style = _env("IMAGE_STYLE").strip()  # fester Zeichenstil fuer jedes Bild, z. B. Buntstift auf Pastell
    if style:
        prompt = f"Stil: {style}\n\n{prompt}"  # vorne, der Gratis-Endpunkt kuerzt lange Prompts
    root = Path(root)
    fmt = _img_format(call)
    refs = _ref_images(root, call.get("refs") or call.get("reference_images"))
    _img_target(root, call, "png")  # Pfad vor dem (kostenpflichtigen) Aufruf pruefen
    prov = _env("IMAGE_PROVIDER", "pollinations").lower()
    if prov == "canva":
        if not canva_enabled():
            raise ToolError("IMAGE_PROVIDER=canva, but Canva is not connected (owner: PCL_CLAUDE_CONNECTORS=Canva in .env, "
                            "see docs/ki-verbindungen.md)")
        raise ToolError("IMAGE_PROVIDER=canva: image_generate does not create images itself. " + CANVA_HOWTO)
    gen = {"gemini": _gen_gemini, "openai": _gen_openai, "openrouter": _gen_openrouter,
           "sdcpp": _gen_sdcpp, "nvidia": _gen_nvidia, "cloudflare": _gen_cloudflare, "hf": _gen_hf,
           "huggingface": _gen_hf}.get(prov, _gen_pollinations)
    fallback = ""
    try:
        data = gen(prompt, refs, fmt, call)
    except (ToolError, requests.RequestException) as e:
        # IMAGE_FALLBACK=pollinations: kostenloser Ersatz, aber OHNE Referenzbilder (Figuren/Stil koennen abweichen)
        canva = (f" Alternative: {CANVA_HOWTO}" if canva_enabled() else "")
        if gen is _gen_pollinations or _env("IMAGE_FALLBACK").lower() != "pollinations":
            if canva:
                raise ToolError(f"{_clip(str(e), 300)}.{canva}")
            raise
        if refs and canva and not _env("POLLINATIONS_API_KEY").strip():
            # Ersatzbild ohne Referenzbild wuerde Figuren/Stil verfehlen: lieber Canva mit Referenzbild
            raise ToolError(f"{_clip(str(e), 300)}. Free fallback skipped because it cannot use reference images.{canva}")
        keep = refs if _env("POLLINATIONS_API_KEY").strip() else []  # mit Key gehen Referenzbilder auch dort
        data = _gen_pollinations(prompt, keep, fmt, call)
        code = re.search(r"HTTP \d{3}", str(e))
        how = ("created with pollen credit and reference images" if keep else
               "created for free and WITHOUT reference images" + (", characters and style may differ" if refs else ""))
        fallback = (f"NOTE: switched to Pollinations, free generation not possible with {prov} "
                    f"({code.group(0) if code else type(e).__name__}). {how}. Error: {_clip(str(e), 160)} ")
        refs = keep
    if len(data) > MAX_IMAGE_BYTES * 3:
        raise ToolError("Created image is too large")
    ext = _sniff(data)
    if ext not in ("png", "jpg", "webp"):
        raise ToolError("Image provider returned no valid image file")
    target = _img_target(root, call, ext)
    if target:
        target.write_bytes(data)
        rel, size = _rel(root, target), len(data)
    else:
        rel, size = _store_image(root, data, call.get("name"), "generated")
    via = f" with {len(refs)} reference image(s)" if refs else ""
    return f"{fallback}Image created{via} and saved: {rel} ({size // 1024} KB). Look at it with view_image. Embed it in HTML like this: <img src=\"{rel}\" alt=\"...\">"


def _inside(root, rel):
    target = (root / str(rel or "")).resolve()
    target.relative_to(root.resolve())  # wirft ValueError ausserhalb
    return target


COPY_MAX_FILES = 500
COPY_MAX_BYTES = 100 * 1024 * 1024


def copy_files(root, src, dst, move=False):
    """Kopiert/verschiebt Datei oder Ordner innerhalb des Projektordners (kein Ausbruch, keine Symlinks, Limits)."""
    import shutil
    root = Path(root).resolve()
    try:
        a, b = _inside(root, src), _inside(root, dst)
    except ValueError:
        raise ToolError("Path is outside the project folder")
    if not str(src or "").strip() or not str(dst or "").strip():
        raise ToolError("'from' and 'to' are required")
    if a == root or b == root:
        raise ToolError("The project folder itself cannot be copied/overwritten")
    if not a.exists():
        raise ToolError(f"Source not found: {src}")
    if a == b or b.is_relative_to(a):
        raise ToolError("Target must not be the same as the source or inside it")
    top = lambda p: p.relative_to(root).parts[0]
    if top(b).startswith(".") or top(a).startswith("."):
        raise ToolError("Hidden folders are not allowed")
    if top(b) == "input":
        raise ToolError("input/ belongs to the owner, nothing is written there")
    files = [a] if a.is_file() else [f for f in sorted(a.rglob("*")) if f.is_file() and not f.is_symlink()
                                       and not any(x.startswith(".") for x in f.relative_to(a).parts)]
    if len(files) > COPY_MAX_FILES or sum(f.stat().st_size for f in files) > COPY_MAX_BYTES:
        raise ToolError(f"Too large (max. {COPY_MAX_FILES} files / {COPY_MAX_BYTES // 1048576} MB)")
    if not files:
        raise ToolError("Nothing to copy (empty)")
    n = 0
    for f in files:
        t = b if a.is_file() and not (b.exists() and b.is_dir()) else (b / f.name if a.is_file() else b / f.relative_to(a))
        t.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, t)
        n += 1
        if move:
            f.unlink()
    if move and a.is_dir():
        shutil.rmtree(a, ignore_errors=True)
    return f"{n} file(s) {'moved' if move else 'copied'}: {src} -> {dst}"


# ------------------------------------------------------------------ Programmieren (Recht "code")
CODE_MAX_BYTES = 500_000
CODE_TIMEOUT = int(_env("PCL_CODE_TIMEOUT", "120"))


def write_code(root, path, content):
    """Schreibt eine Quelltext-Datei in den Projektordner (nicht input/, keine Dotordner)."""
    root = Path(root).resolve()
    if not str(path or "").strip():
        raise ToolError("'path' is required")
    try:
        f = _inside(root, path)
    except ValueError:
        raise ToolError("Path is outside the project folder")
    parts = f.relative_to(root).parts
    if f == root or any(x.startswith(".") for x in parts):
        raise ToolError("Hidden files/folders are not allowed")
    if parts[0] == "input":
        raise ToolError("input/ belongs to the owner, nothing is written there")
    data = str(content or "").encode("utf-8")
    if len(data) > CODE_MAX_BYTES:
        raise ToolError(f"Too large (max. {CODE_MAX_BYTES // 1000} KB per file, split the code into several files)")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(data)
    rel = f.relative_to(root).as_posix()
    lines = data.count(b"\n") + 1
    return f"Saved: {rel} ({len(data)} bytes, {lines} lines)"


# Endung -> (Sprache, Pruefbefehl). {f} = Datei, {o} = leerer Temp-Ordner. Nur Werkzeuge, die den Code NICHT ausfuehren
# (kein perl -c / ghc: BEGIN-Bloecke bzw. Template Haskell wuerden laufen).
CODE_CHECKERS = {
    ".js": ("JavaScript", ["node", "--check", "{f}"]), ".mjs": ("JavaScript", ["node", "--check", "{f}"]),
    ".cjs": ("JavaScript", ["node", "--check", "{f}"]),
    ".ts": ("TypeScript", ["tsc", "--noEmit", "--skipLibCheck", "{f}"]),
    ".rs": ("Rust", ["rustc", "--edition", "2021", "--emit=metadata", "--out-dir", "{o}", "{f}"]),
    ".java": ("Java", ["javac", "-proc:none", "-d", "{o}", "{f}"]),
    ".go": ("Go", ["gofmt", "-e", "-l", "{f}"]),
    ".c": ("C", ["gcc", "-fsyntax-only", "-Wall", "{f}"]), ".h": ("C", ["gcc", "-fsyntax-only", "{f}"]),
    ".cpp": ("C++", ["g++", "-fsyntax-only", "-Wall", "{f}"]), ".cc": ("C++", ["g++", "-fsyntax-only", "-Wall", "{f}"]),
    ".hpp": ("C++", ["g++", "-fsyntax-only", "{f}"]),
    ".sh": ("Shell", ["bash", "-n", "{f}"]), ".bash": ("Shell", ["bash", "-n", "{f}"]),
    ".rb": ("Ruby", ["ruby", "-c", "{f}"]), ".php": ("PHP", ["php", "-l", "{f}"]),
    ".lua": ("Lua", ["luac", "-p", "{f}"]),
    ".kt": ("Kotlin", ["kotlinc", "{f}", "-d", "{o}"]),
    ".cs": ("C#", ["mcs", "-target:library", "-out:{o}/x.dll", "{f}"]),
    ".swift": ("Swift", ["swiftc", "-parse", "{f}"]),
}


def check_code(root, path):
    """Prueft Syntax/Kompilierbarkeit ohne Ausfuehrung. Python/JSON intern, sonst mit installiertem Compiler."""
    f = _inside_existing(Path(root).resolve(), path)
    ext = f.suffix.lower()
    if ext in (".py", ".pyw"):
        src = f.read_text(encoding="utf-8", errors="replace")
        try:
            compile(src, str(path), "exec", dont_inherit=True)  # kompiliert nur, fuehrt nichts aus
        except SyntaxError as e:
            return f"Python: ERROR in line {e.lineno}, column {e.offset}: {e.msg}\n  {(e.text or '').rstrip()}"
        return f"Python: {path} is syntactically correct."
    if ext == ".json":
        try:
            json.loads(f.read_text(encoding="utf-8"))
        except ValueError as e:
            return f"JSON: ERROR: {e}"
        return f"JSON: {path} is valid."
    spec = CODE_CHECKERS.get(ext)
    if not spec:
        return (f"There is no automatic check for '{ext or 'no extension'}'. Check the code carefully yourself. "
                f"Checkable: .py .json " + " ".join(sorted(CODE_CHECKERS)))
    lang, cmd = spec
    if not shutil.which(cmd[0]):
        return (f"{lang}: check tool '{cmd[0]}' is not installed on the server. The code was saved but not checked "
                f"(the owner can install it).")
    # Minimale Umgebung: Compiler sehen keine API-Keys aus .env
    env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG", "JAVA_HOME", "GOROOT", "RUSTUP_HOME", "CARGO_HOME") if k in os.environ}
    with tempfile.TemporaryDirectory(prefix="pcl-code-") as o:
        args = [a.replace("{f}", str(f)).replace("{o}", o) for a in cmd]
        try:
            r = subprocess.run(args, cwd=o, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=CODE_TIMEOUT)
        except subprocess.TimeoutExpired:
            return f"{lang}: check stopped after {CODE_TIMEOUT} s (too slow/too large)."
    out = (r.stdout + r.stderr).replace(str(f.parent) + os.sep, "").strip()
    if ext == ".go" and r.returncode == 0:
        return f"Go: {path} is syntactically correct."
    if r.returncode == 0:
        return f"{lang}: {path} OK." + (f"\nHinweise:\n{out[:3000]}" if out else "")
    return f"{lang}: ERROR (code {r.returncode}):\n{out[:4000] or '(no output)'}"


# ------------------------------------------------- Code ausfuehren (Recht "run_code", isoliert)
RUN_TIMEOUT = int(_env("PCL_RUN_TIMEOUT", "60"))
RUN_MEM_MB = int(_env("PCL_RUN_MEM_MB", "1024"))
RUN_OUT_MAX_FILES = 50
RUN_OUT_MAX_BYTES = 50 * 1024 * 1024
# Endung -> (Sprache, Befehl). Laeuft mit den Programmen des Systems (/usr), ohne venv und ohne Keys.
RUNNERS = {
    ".py": ("Python", ["python3", "-I", "{f}"]), ".js": ("JavaScript", ["node", "{f}"]), ".mjs": ("JavaScript", ["node", "{f}"]),
    ".sh": ("Shell", ["bash", "{f}"]), ".rb": ("Ruby", ["ruby", "{f}"]), ".php": ("PHP", ["php", "{f}"]),
    ".lua": ("Lua", ["lua", "{f}"]),
}
_LANG_EXT = {"python": ".py", "py": ".py", "javascript": ".js", "js": ".js", "node": ".js", "bash": ".sh", "sh": ".sh",
             "shell": ".sh", "ruby": ".rb", "php": ".php", "lua": ".lua"}


def cargo_enabled():
    """rust_project: cargo vorhanden und abschottbar (bubblewrap) oder PCL_CARGO_UNSAFE=1 (z. B. Windows)."""
    import rust_builder
    return rust_builder.cargo_enabled()


def run_enabled():
    """run_code braucht bubblewrap (bwrap) fuer die Isolierung; PCL_ALLOW_RUN=0 sperrt es global."""
    return _env("PCL_ALLOW_RUN", "1") != "0" and bool(shutil.which("bwrap"))


def _sandbox_cmd(proj, work):
    """bwrap-Aufruf: nur /usr + noetige /etc-Teile lesbar, Projekt schreibgeschuetzt unter /projekt, /arbeit beschreibbar,
    kein Netz (eigener Netz-Namensraum), eigene PIDs, nichts vom Server (.env, Datenbank, Home) sichtbar."""
    cmd = ["bwrap", "--ro-bind", "/usr", "/usr"]
    for d in ("bin", "lib", "lib64", "lib32", "sbin"):
        p = Path("/" + d)
        if p.is_symlink():
            cmd += ["--symlink", os.readlink(p), "/" + d]
        elif p.is_dir():
            cmd += ["--ro-bind", str(p), "/" + d]
    for e in ("alternatives", "ssl", "ld.so.cache", "ld.so.conf", "ld.so.conf.d", "localtime", "mime.types", "nsswitch.conf"):
        cmd += ["--ro-bind-try", "/etc/" + e, "/etc/" + e]
    cmd += ["--ro-bind", str(proj), "/projekt", "--bind", str(work), "/arbeit", "--chdir", "/arbeit",
            "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
            "--unshare-all", "--die-with-parent", "--new-session", "--hostname", "sandbox",
            "--clearenv", "--setenv", "PATH", "/usr/local/bin:/usr/bin:/bin", "--setenv", "HOME", "/arbeit",
            "--setenv", "LANG", "C.UTF-8", "--setenv", "PYTHONDONTWRITEBYTECODE", "1", "--setenv", "MPLBACKEND", "Agg", "--"]
    return cmd


def _limits():
    import resource
    mem = RUN_MEM_MB * 1024 * 1024
    for lim, val in ((resource.RLIMIT_AS, mem), (resource.RLIMIT_CPU, RUN_TIMEOUT + 5),
                     (resource.RLIMIT_FSIZE, RUN_OUT_MAX_BYTES), (resource.RLIMIT_CORE, 0)):
        try:
            resource.setrlimit(lim, (val, val))
        except (ValueError, OSError):
            pass


def run_code(root, path=None, code=None, lang=None, args=None, stdin=None):
    """Fuehrt ein Skript isoliert aus: kein Netz, kein Zugriff ausser dem Projekt (nur lesen), Zeit-/RAM-Grenzen.
    Neue Dateien aus dem Arbeitsordner landen in output/run/<zeit>/."""
    if not run_enabled():
        raise ToolError("Running code is not set up on this server (bubblewrap missing or PCL_ALLOW_RUN=0)")
    root = Path(root).resolve()
    if code:
        ext = _LANG_EXT.get(str(lang or "python").lower().strip())
        if not ext:
            raise ToolError("lang: python, javascript, bash, ruby, php or lua")
        data = str(code).encode("utf-8")
        if len(data) > CODE_MAX_BYTES:
            raise ToolError("Code too large")
        rel = None
    else:
        f = _inside_existing(root, path)
        if any(x.startswith(".") for x in f.relative_to(root).parts):
            raise ToolError("Hidden files are not allowed")
        ext, rel = f.suffix.lower(), f.relative_to(root).as_posix()
    spec = RUNNERS.get(ext)
    if not spec:
        return f"Running works for: {' '.join(sorted(RUNNERS))}. Check other languages only with check_code."
    lng, prog = spec
    if not shutil.which(prog[0], path="/usr/local/bin:/usr/bin:/bin"):  # die Sandbox sieht nur /usr
        return f"{lng}: '{prog[0]}' is not installed on the server (in /usr/bin)."
    argv = [str(x)[:500] for x in (args if isinstance(args, list) else [])][:20]
    with tempfile.TemporaryDirectory(prefix="pcl-run-") as work:
        w = Path(work)
        if rel is None:
            (w / ("main" + ext)).write_bytes(data)
            target = "/arbeit/main" + ext
        else:
            target = "/projekt/" + rel
        cmd = _sandbox_cmd(root, w) + [a.replace("{f}", target) for a in prog] + argv
        t0 = time.time()
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             preexec_fn=_limits, start_new_session=True)
        try:
            outb, _ = p.communicate(input=str(stdin or "").encode()[:1_000_000], timeout=RUN_TIMEOUT)
            timeout = False
        except subprocess.TimeoutExpired:
            import signal
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except OSError:
                pass
            outb, _ = p.communicate()
            timeout = True
        secs = time.time() - t0
        text = (outb or b"").decode("utf-8", "replace").replace("/arbeit/", "").replace("/projekt/", "")
        # Ergebnisdateien uebernehmen (keine Symlinks/Dotdateien, Limits)
        kept, size = [], 0
        stamp = time.strftime("%Y%m%d-%H%M%S")
        for f in sorted(w.rglob("*")):
            r = f.relative_to(w)
            if f.is_symlink() or not f.is_file() or any(x.startswith(".") for x in r.parts) or r.as_posix() == "main" + ext:
                continue
            size += f.stat().st_size
            if len(kept) >= RUN_OUT_MAX_FILES or size > RUN_OUT_MAX_BYTES:
                break
            dst = root / "output" / "run" / stamp / r
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, dst)
            kept.append(f"output/run/{stamp}/{r.as_posix()}")
    head = f"{lng}: " + (f"STOPPED after {RUN_TIMEOUT} s (time limit)" if timeout else f"exit code {p.returncode}") + f", {secs:.1f} s"
    if p.returncode in (-9, 137) and not timeout:
        head += " (probably RAM limit reached)"
    out = head + "\n--- Output ---\n" + (_clip(text.strip(), 6000) or "(no output)")
    if kept:
        out += "\n--- New files ---\n" + "\n".join(kept)
    return out


def list_files(root, path=""):
    try:
        d = _inside(root, path)
    except ValueError:
        raise ToolError("Path is outside the project folder")
    if not d.exists():
        return "(Folder is empty or does not exist yet)"
    rows = []
    for f in sorted(d.rglob("*"))[:600]:
        if f.is_file() and not any(part.startswith(".") for part in f.relative_to(root.resolve()).parts):
            rows.append(f"{f.relative_to(root.resolve())}  ({f.stat().st_size // 1024 or 1} KB)")
    return "\n".join(rows) or "(no files)"


def read_file(root, path, offset=0):
    try:
        f = _inside(root, path)
    except ValueError:
        raise ToolError("Path is outside the project folder")
    if not f.is_file():
        raise ToolError(f"File '{path}' does not exist (list_files shows the content)")
    ext = f.suffix.lower()
    if ext in (".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp") and shutil.which("tesseract") and _env("PCL_OCR_IMAGES", "1") != "0":
        try:
            t = ocr_image(f)
        except Exception as e:
            raise ToolError(f"OCR failed ({type(e).__name__})")
        return (f"{path}: ONLY the text from the image (OCR, errors possible). You see the image content (map, layout, photo) with "
                f"view_image:\n{t[:READ_CHARS]}" if t
                else f"{path}: image without recognisable text ({f.stat().st_size // 1024} KB). You see the content with view_image.")
    if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        return f"{path}: image ({f.stat().st_size // 1024} KB). Look at it with view_image, read_file does not read images."
    if ext in (".mp4", ".webm", ".mov", ".mp3", ".wav", ".ogg", ".zip"):
        return f"{path}: media file ({f.stat().st_size // 1024} KB). For videos/audio: media_info."
    cap = int(_env("PCL_MAX_READ_MB", "200")) * 1_000_000 if ext == ".pdf" else 30_000_000  # Scans sind oft sehr gross
    raw = f.read_bytes()[:cap]
    try:
        text = _doc_text(path, raw)
    except Exception as e:
        raise ToolError(f"Document not readable ({type(e).__name__})")
    if text is None:
        if b"\x00" in raw[:2000]:
            return f"{path}: binary file ({f.stat().st_size // 1024} KB), cannot be read as text."
        text = raw[:2_000_000].decode("utf-8", errors="replace")
    try:
        offset = max(0, int(offset or 0))
    except (TypeError, ValueError):
        offset = 0
    chunk = text[offset:offset + READ_CHARS]
    more = f"\n[Continued: read_file with offset={offset + READ_CHARS}; total length {len(text)} characters]" if len(text) > offset + READ_CHARS else ""
    return f"File {path} (from character {offset}):\n" + chunk + more


# ------------------------------------------------------------------ Dokumente lesen (PDF, DOCX, EPUB)
def pdf_text(data):
    """Text aus PDF-Bytes. pypdf, sonst pdftotext."""
    try:
        from pypdf import PdfReader
        rd = PdfReader(io.BytesIO(data))
        parts = []
        for i, pg in enumerate(rd.pages, 1):
            t = (pg.extract_text() or "").strip()
            if t:
                parts.append(f"[Page {i}]\n{t}")
        txt = "\n\n".join(parts)
        if txt.strip():
            return txt
    except ImportError:
        pass
    except Exception:
        pass
    if shutil.which("pdftotext"):
        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            f.write(data)
            f.flush()
            r = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
            if r.stdout.strip():
                return r.stdout
    return ""


def _tess_lang():
    """OCR-Sprachen: PCL_OCR_LANG (z.B. deu+eng), sonst alles Vorhandene aus deu/eng/tur."""
    want = _env("PCL_OCR_LANG")
    try:
        have = set(subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20).stdout.split()[1:])
    except Exception:
        have = set()
    langs = [l for l in (want.split("+") if want else ["deu", "eng", "tur"]) if l in have]
    return "+".join(langs) or ("eng" if "eng" in have else "")


def ocr_image(path):
    """Text aus einem Bild (tesseract). Leerer String, wenn nichts erkannt wurde."""
    if not shutil.which("tesseract"):
        raise ToolError("OCR not installed (Raspberry Pi: sudo apt install tesseract-ocr tesseract-ocr-deu)")
    lang = _tess_lang()
    cmd = ["tesseract", str(path), "-"] + (["-l", lang] if lang else [])
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    return r.stdout.strip()


def ocr_pdf(data, max_pages=None):
    """Gescannte PDF seitenweise per pdftoppm + tesseract lesen (langsam auf dem Pi, daher Seitenlimit PCL_OCR_MAX_PAGES)."""
    if not shutil.which("tesseract"):
        return ""
    max_pages = max_pages or int(_env("PCL_OCR_MAX_PAGES", "25"))
    parts, total = [], 0
    with tempfile.TemporaryDirectory(prefix="pcl-ocr-") as td:
        pdf = Path(td) / "in.pdf"
        pdf.write_bytes(data)
        if shutil.which("pdftoppm"):
            subprocess.run(["pdftoppm", "-r", "200", "-gray", "-l", str(max_pages), "-png", str(pdf), str(Path(td) / "p")],
                           capture_output=True, timeout=600)
        else:  # ohne poppler: die eingebetteten Scanbilder der Seiten nehmen
            try:
                from pypdf import PdfReader
                for i, pg in enumerate(list(PdfReader(str(pdf)).pages)[:max_pages], 1):
                    imgs = list(pg.images)
                    if imgs:
                        (Path(td) / f"p-{i:04d}.png").write_bytes(max(imgs, key=lambda x: len(x.data)).data)
            except Exception:
                pass
        pages = sorted(Path(td).glob("p-*.png"))
        total = len(pages)
        for i, img in enumerate(pages, 1):
            try:
                t = ocr_image(img)
            except Exception:
                t = ""
            if t:
                parts.append(f"[Page {i}]\n{t}")
    if not parts:
        return ""
    note = f"[OCR text of a scan, errors possible; the first {total} pages read]\n\n"
    return note + "\n\n".join(parts)


IMG_MAX_PX = 1568  # groesser bringt den Modellen nichts, kostet nur Tokens


def _pil_b64(im):
    """PIL-Bild verkleinern und als (media_type, base64) liefern."""
    im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
    im.thumbnail((IMG_MAX_PX, IMG_MAX_PX))
    buf = io.BytesIO()
    if im.mode == "RGBA":
        im.save(buf, "PNG", optimize=True)
        return "image/png", base64.b64encode(buf.getvalue()).decode()
    im.save(buf, "JPEG", quality=88)
    return "image/jpeg", base64.b64encode(buf.getvalue()).decode()


IMG_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp",
             ".bmp": None, ".tif": None, ".tiff": None}  # None = wird umgewandelt


def image_b64(path):
    """(media_type, base64) einer Bilddatei fuer Modelle mit Bildverstaendnis, oder None."""
    f = Path(path)
    ext = f.suffix.lower()
    if ext not in IMG_TYPES or not f.is_file():
        return None
    try:
        from PIL import Image
        with Image.open(f) as im:
            if IMG_TYPES[ext] and max(im.size) <= IMG_MAX_PX and f.stat().st_size <= 3_500_000:
                return IMG_TYPES[ext], base64.b64encode(f.read_bytes()).decode()
            return _pil_b64(im)
    except Exception:
        if IMG_TYPES[ext] and f.stat().st_size <= 3_500_000:
            return IMG_TYPES[ext], base64.b64encode(f.read_bytes()).decode()
        return None


def pdf_page_images(path, first=1, count=4):
    """Seiten einer (gescannten) PDF als Bilder: per pdftoppm, sonst die eingebetteten Scanbilder (pypdf, ohne poppler)."""
    first, count = max(1, int(first or 1)), max(1, min(int(count or 4), 4))
    out = []
    if shutil.which("pdftoppm"):
        with tempfile.TemporaryDirectory(prefix="pcl-pdfimg-") as td:
            subprocess.run(["pdftoppm", "-r", "110", "-f", str(first), "-l", str(first + count - 1), "-jpeg", str(path),
                            str(Path(td) / "p")], capture_output=True, timeout=300)
            for img in sorted(Path(td).glob("p-*.jpg")):
                b = image_b64(img)
                if b:
                    out.append(b)
        if out:
            return out
    try:
        from PIL import Image
        from pypdf import PdfReader
        rd = PdfReader(str(path))
        for pg in list(rd.pages)[first - 1:first - 1 + count]:
            imgs = list(pg.images)
            if not imgs:
                continue
            big = max(imgs, key=lambda x: len(x.data))
            with Image.open(io.BytesIO(big.data)) as im:
                out.append(_pil_b64(im))
    except Exception:
        pass
    return out


def pdf_overview(path, max_pages=16, cols=4):
    """Alle Seiten (bis max_pages) verkleinert auf einem Uebersichtsbild, fuer die Selbstkontrolle. (Bild, Seitenzahl) oder (None, 0)."""
    if not shutil.which("pdftoppm"):
        return None, 0
    try:
        from PIL import Image
        with tempfile.TemporaryDirectory(prefix="pcl-pdfov-") as td:
            subprocess.run(["pdftoppm", "-r", "45", "-l", str(max_pages), "-jpeg", str(path), str(Path(td) / "p")],
                           capture_output=True, timeout=300)
            pages = sorted(Path(td).glob("p-*.jpg"), key=lambda x: int(x.stem.rsplit("-", 1)[1]))
            if not pages:
                return None, 0
            ims = [Image.open(x).convert("RGB") for x in pages]
            w, h = max(i.width for i in ims), max(i.height for i in ims)
            c = min(cols, len(ims))
            sheet = Image.new("RGB", (c * (w + 8) + 8, ((len(ims) + c - 1) // c) * (h + 8) + 8), "#888888")
            for n, im in enumerate(ims):
                sheet.paste(im, (8 + (n % c) * (w + 8), 8 + (n // c) * (h + 8)))
            return _pil_b64(sheet), len(ims)
    except Exception:
        return None, 0


def view_image(root, path, page=None):
    """Fuer das Werkzeug view_image: (Text, [Bilder])."""
    try:
        f = _inside(root, path)
    except ValueError:
        raise ToolError("Path is outside the project folder")
    if not f.is_file():
        raise ToolError(f"File '{path}' does not exist (list_files shows the content)")
    if f.suffix.lower() == ".pdf":
        first = max(1, int(page or 1)) if str(page or "1").isdigit() else 1
        imgs = pdf_page_images(f, first, 4)
        if not imgs:
            raise ToolError("No page images could be taken from this PDF")
        return f"{path}: pages {first}-{first + len(imgs) - 1} attached as images.", imgs
    img = image_b64(f)
    if not img:
        raise ToolError("Not a supported image format (png, jpg, gif, webp, bmp, tif)")
    return f"{path}: image attached ({f.stat().st_size // 1024} KB).", [img]


def docx_text(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab/>", "\t", xml)
    return htmllib.unescape(re.sub(r"<[^>]+>", "", xml)).strip()


def epub_text(data):
    out = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = sorted(n for n in z.namelist() if n.lower().endswith((".xhtml", ".html", ".htm")))
        for n in names:
            title, body = html_to_text(z.read(n).decode("utf-8", "replace"))
            if body.strip():
                out.append(body)
    return "\n\n".join(out)


def _doc_text(path, data):
    ext = Path(str(path)).suffix.lower()
    if ext == ".pdf" or data[:4] == b"%PDF":
        t = pdf_text(data)
        if not t.strip():
            t = ocr_pdf(data)
        return t or ("(The PDF contains no readable text, probably a scan, and OCR is not installed: sudo apt install tesseract-ocr "
                     "tesseract-ocr-deu tesseract-ocr-tur poppler-utils. Look at pages: view_image with path and page)")
    if ext == ".docx":
        return docx_text(data)
    if ext == ".epub":
        return epub_text(data)
    if ext in (".html", ".htm"):
        return html_to_text(data.decode("utf-8", "replace"))[1]
    return None


# --------------------------------------------------------------------------- Dateien laden
_DL_EXT = {"application/pdf": "pdf", "application/epub+zip": "epub", "text/plain": "txt", "text/csv": "csv",
           "application/json": "json", "application/zip": "zip", "video/mp4": "mp4", "video/webm": "webm",
           "video/quicktime": "mov", "audio/mpeg": "mp3", "audio/wav": "wav", "audio/x-wav": "wav", "audio/ogg": "ogg",
           "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
           "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx"}
_DL_OK_EXT = {"pdf", "epub", "txt", "csv", "json", "zip", "mp4", "webm", "mov", "mp3", "wav", "ogg", "docx", "xlsx", "pptx",
              "md", "png", "jpg", "jpeg", "gif", "webp", "svg"}


def download_file(root, url, name=""):
    maxb = int(_env("PCL_MAX_DOWNLOAD_MB", "60")) * 1_000_000
    url = str(url or "").strip()
    r, data, cut = safe_get(url, maxb)
    if cut:
        raise ToolError(f"File is larger than {maxb // 1_000_000} MB")
    ctype = r.headers.get("Content-Type", "").split(";")[0].strip().lower()
    ext = _DL_EXT.get(ctype) or Path(urlparse(url).path).suffix.lower().lstrip(".")
    if data[:4] == b"%PDF":
        ext = "pdf"
    if ext not in _DL_OK_EXT:
        raise ToolError(f"File type not allowed ({ctype or ext or 'unknown'}). Allowed: PDF, EPUB, Office, text, audio, video, ZIP, images.")
    if ext == "pdf" and data[:4] != b"%PDF":
        raise ToolError("The address does not deliver a real PDF (probably a web page). Look at it with fetch_url and search for the direct link.")
    d = root / "downloads"
    d.mkdir(parents=True, exist_ok=True)
    base = _safe_name(name or Path(urlparse(url).path).stem, "datei")
    i = 0
    while (d / f"{base}{'' if not i else '-' + str(i)}.{ext}").exists():
        i += 1
    target = d / f"{base}{'' if not i else '-' + str(i)}.{ext}"
    target.write_bytes(data)
    extra = ""
    if ext == "pdf":
        extra = f" Page text readable: {'yes' if pdf_text(data).strip() else 'no (scan)'}. To read: read_file."
    return f"Saved: downloads/{target.name} ({len(data) // 1024} KB).{extra}"


# ------------------------------------------------------------------------------ ffmpeg
def _bin(name):
    p = shutil.which(name)
    if not p:
        raise ToolError(f"'{name}' is not installed on the server (Raspberry Pi: sudo apt install {name if name != 'ffprobe' else 'ffmpeg'})")
    return p


def _ff(args, root, timeout=None):
    timeout = timeout or int(_env("PCL_FFMPEG_TIMEOUT", "3600"))
    try:
        r = subprocess.run([_bin("ffmpeg"), "-nostdin", "-y", "-hide_banner", "-loglevel", "error"] + [str(a) for a in args],
                           cwd=str(root), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        raise ToolError(f"ffmpeg time limit ({timeout} s). Use shorter clips or a lower resolution.")
    if r.returncode != 0:
        raise ToolError("ffmpeg error: " + (r.stderr or "")[-600:])


def _probe(path):
    try:
        r = subprocess.run([_bin("ffprobe"), "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        d = json.loads(r.stdout or "{}")
    except (subprocess.TimeoutExpired, ValueError):
        raise ToolError("File could not be analysed")
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), None)
    a = next((s for s in d.get("streams", []) if s.get("codec_type") == "audio"), None)
    dur = float((d.get("format") or {}).get("duration") or (v or a or {}).get("duration") or 0)
    return {"duration": dur, "video": v, "audio": a, "size": int((d.get("format") or {}).get("size") or 0)}


def _describe_probe(p):
    bits = []
    if p["video"]:
        v = p["video"]
        bits.append(f"Video {v.get('width')}x{v.get('height')} {v.get('codec_name')}")
    if p["audio"]:
        bits.append(f"Audio {p['audio'].get('codec_name')}")
    return f"{p['duration']:.1f} s, " + ", ".join(bits) + f", {p['size'] // 1024} KB"


def media_info(root, path):
    f = _inside_existing(root, path)
    return f"{path}: " + _describe_probe(_probe(f))


def _inside_existing(root, rel):
    try:
        f = _inside(root, rel)
    except ValueError:
        raise ToolError("Path is outside the project folder")
    if not f.is_file():
        raise ToolError(f"File '{rel}' does not exist (list_files shows the content)")
    return f


def _secs(v, default=None):
    if v in (None, ""):
        return default
    if isinstance(v, (int, float)):
        return float(v)
    parts = str(v).strip().replace(",", ".").split(":")
    try:
        n = [float(x) for x in parts]
    except ValueError:
        raise ToolError(f"Time '{v}' not readable (seconds or MM:SS)")
    t = 0.0
    for x in n:
        t = t * 60 + x
    return t


def _find_font(bold=False):
    names = (["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "arialbd.ttf"] if bold
             else ["DejaVuSans.ttf", "LiberationSans-Regular.ttf", "arial.ttf"])
    for d in ("/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/liberation", "/usr/share/fonts/TTF", "/usr/share/fonts",
              os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")):
        for n in names:
            if os.path.exists(os.path.join(d, n)):
                return os.path.join(d, n)
    return None


def _out_path(root, call, default, ext):
    out = root / "output"
    out.mkdir(parents=True, exist_ok=True)
    base = _safe_name(call.get("name"), default)
    p, i = out / f"{base}.{ext}", 1
    while p.exists():
        p = out / f"{base}-{i}.{ext}"
        i += 1
    return p


def _rel(root, p):
    return Path(p).resolve().relative_to(root.resolve()).as_posix()


def _dims(call, default_w=1280, default_h=720):
    try:
        w, h = int(call.get("width") or default_w), int(call.get("height") or default_h)
        fps = int(call.get("fps") or 30)
    except (TypeError, ValueError):
        raise ToolError("width/height/fps must be numbers")
    w, h, fps = max(64, min(w, 3840)) // 2 * 2, max(64, min(h, 2160)) // 2 * 2, max(1, min(fps, 60))
    return w, h, fps


def _norm_segment(src, dst, root, w, h, fps):
    p = _probe(src)
    if not p["video"]:
        raise ToolError(f"{_rel(root, src)} contains no video")
    vf = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,"
          f"setsar=1,fps={fps},format=yuv420p")
    args = ["-i", src]
    if not p["audio"]:
        args += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest"]
    args += ["-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-ar", "48000", "-ac", "2", dst]
    _ff(args, root)


def _concat(segments, dst, root, tmp):
    lst = Path(tmp) / "list.txt"
    lst.write_text("".join(f"file '{Path(s).resolve().as_posix()}'\n" for s in segments), encoding="utf-8")
    _ff(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", dst], root)


def video_edit(root, call):
    op = str(call.get("op") or "").strip().lower()
    tmp = Path(tempfile.mkdtemp(prefix=".tmp-", dir=root))
    try:
        return _video_edit(root, call, op, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _video_edit(root, call, op, tmp):
    def src(key="input"):
        return _inside_existing(root, call.get(key))

    if op == "trim":
        f = src()
        start, end = _secs(call.get("start"), 0.0), _secs(call.get("end"))
        if end is not None and end <= start:
            raise ToolError("end must be after start")
        out = _out_path(root, call, "ausschnitt", "mp4")
        args = ["-ss", start, "-i", f] + (["-t", end - start] if end is not None else [])
        _ff(args + ["-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-c:a", "aac", "-movflags", "+faststart", out], root)

    elif op == "concat":
        ins = call.get("inputs")
        if not isinstance(ins, list) or len(ins) < 2:
            raise ToolError("inputs: list with at least 2 videos")
        w, h, fps = _dims(call)
        segs = []
        for i, name in enumerate(ins[:40]):
            seg = tmp / f"seg{i}.mp4"
            _norm_segment(_inside_existing(root, name), seg, root, w, h, fps)
            segs.append(seg)
        out = _out_path(root, call, "zusammenschnitt", "mp4")
        _concat(segs, out, root, tmp)

    elif op == "slideshow":
        imgs = call.get("images")
        if not isinstance(imgs, list) or not imgs:
            raise ToolError("images: list of image paths")
        w, h, fps = _dims(call)
        sec = max(1.0, min(_secs(call.get("seconds"), 4.0), 30.0))
        kb = str(call.get("kenburns", "true")).lower() not in ("false", "0", "no")
        frames = int(sec * fps)
        segs = []
        for i, name in enumerate(imgs[:80]):
            f = _inside_existing(root, name)
            seg = tmp / f"s{i}.mp4"
            fade = f"fade=t=in:st=0:d=0.5,fade=t=out:st={sec - 0.5}:d=0.5,format=yuv420p"
            if kb:
                zexpr = "min(zoom+0.0007,1.2)" if i % 2 == 0 else "if(eq(on,0),1.2,max(zoom-0.0007,1.0))"
                vf = (f"scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase,crop={w * 2}:{h * 2},"
                      f"zoompan=z='{zexpr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={w}x{h}:fps={fps},{fade}")
                _ff(["-i", f, "-vf", vf, "-frames:v", frames, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", seg], root)
            else:
                vf = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,{fade}"
                _ff(["-loop", "1", "-t", sec, "-i", f, "-vf", vf, "-r", fps, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", seg], root)
            segs.append(seg)
        silent = tmp / "all.mp4"
        _concat(segs, silent, root, tmp)
        out = _out_path(root, call, "diashow", "mp4")
        if call.get("audio"):
            a = _inside_existing(root, call.get("audio"))
            _ff(["-i", silent, "-i", a, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-shortest",
                 "-movflags", "+faststart", out], root)
        else:
            shutil.move(str(silent), str(out))

    elif op == "text_overlay":
        f = src()
        text = str(call.get("text") or "").strip()
        if not text:
            raise ToolError("text missing")
        font = _find_font(bold=True)
        if not font:
            raise ToolError("No font found (sudo apt install fonts-dejavu-core)")
        tf = tmp / "t.txt"
        tf.write_text(text[:300], encoding="utf-8")
        size = max(12, min(int(call.get("size") or 48), 200))
        color = str(call.get("color") or "white")
        if not re.fullmatch(r"[A-Za-z0-9#]{3,20}", color):
            raise ToolError("color invalid")
        pos = {"top": "y=h*0.08", "center": "y=(h-text_h)/2"}.get(str(call.get("position") or "bottom"), "y=h*0.80")
        st, en = _secs(call.get("start"), 0.0), _secs(call.get("end"))
        en_part = f":enable='between(t,{st},{en})'" if en is not None else (f":enable='gte(t,{st})'" if st else "")
        rel_tf = tf.relative_to(root.resolve()).as_posix()
        vf = (f"drawtext=fontfile={font}:textfile={rel_tf}:fontsize={size}:fontcolor={color}:x=(w-text_w)/2:{pos}"
              f":box=1:boxcolor=black@0.45:boxborderw=14{en_part}")
        out = _out_path(root, call, "with-text", "mp4")
        _ff(["-i", f, "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-c:a", "copy", "-movflags", "+faststart", out], root)

    elif op == "burn_subtitles":
        f, srt = src(), src("srt")
        local = tmp / "sub.srt"
        shutil.copy(srt, local)
        out = _out_path(root, call, "with-subtitles", "mp4")
        rel_sub = local.relative_to(root.resolve()).as_posix()
        _ff(["-i", f, "-vf", f"subtitles={rel_sub}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-c:a", "copy", out], root)

    elif op == "overlay_image":
        f, img = src(), src("image")
        wpx = max(16, min(int(call.get("width") or 160), 1000))
        xy = {"tl": "x=20:y=20", "tr": "x=W-w-20:y=20", "bl": "x=20:y=H-h-20", "center": "x=(W-w)/2:y=(H-h)/2"}.get(
            str(call.get("position") or "br"), "x=W-w-20:y=H-h-20")
        out = _out_path(root, call, "with-logo", "mp4")
        _ff(["-i", f, "-i", img, "-filter_complex", f"[1:v]scale={wpx}:-1[lg];[0:v][lg]overlay={xy}", "-c:v", "libx264",
             "-preset", "veryfast", "-crf", "22", "-c:a", "copy", out], root)

    elif op == "add_audio":
        f, a = src(), src("audio")
        vol = max(0.0, min(float(call.get("volume") or 1.0), 2.0))
        has_a = bool(_probe(f)["audio"])
        out = _out_path(root, call, "with-sound", "mp4")
        if str(call.get("mode") or "replace") == "mix" and has_a:
            _ff(["-i", f, "-i", a, "-filter_complex", f"[1:a]volume={vol}[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=2[aout]",
                 "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-movflags", "+faststart", out], root)
        else:
            _ff(["-i", f, "-i", a, "-filter_complex", f"[1:a]volume={vol}[m]", "-map", "0:v", "-map", "[m]", "-c:v", "copy",
                 "-c:a", "aac", "-shortest", "-movflags", "+faststart", out], root)

    elif op == "extract_audio":
        f = src()
        fmt = "wav" if str(call.get("format")) == "wav" else "mp3"
        out = _out_path(root, call, "audio", fmt)
        _ff(["-i", f, "-vn"] + (["-c:a", "libmp3lame", "-q:a", "2"] if fmt == "mp3" else []) + [out], root)

    elif op == "speed":
        f = src()
        fac = max(0.25, min(float(call.get("factor") or 1.0), 4.0))
        has_a = bool(_probe(f)["audio"])
        chain, x = [], fac
        while x > 2.0:
            chain.append("atempo=2.0")
            x /= 2
        while x < 0.5:
            chain.append("atempo=0.5")
            x *= 2
        chain.append(f"atempo={x:.4f}")
        out = _out_path(root, call, f"tempo-{fac:g}x", "mp4")
        args = ["-i", f, "-vf", f"setpts=PTS/{fac}"] + (["-af", ",".join(chain)] if has_a else ["-an"])
        _ff(args + ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-movflags", "+faststart", out], root)

    elif op == "convert":
        f = src()
        fmt = str(call.get("format") or "mp4").lower()
        if fmt not in ("mp4", "webm", "gif", "mp3", "wav"):
            raise ToolError("format: mp4, webm, gif, mp3 or wav")
        out = _out_path(root, call, "converted", fmt)
        sc = ""
        if call.get("width") or call.get("height"):
            w, h, _ = _dims(call)
            sc = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,"
        fps = int(call.get("fps") or (12 if fmt == "gif" else 30))
        if fmt == "gif":
            vf = f"{sc}fps={min(fps, 20)},scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
            _ff(["-i", f, "-vf", vf, "-t", 30, out], root)
        elif fmt in ("mp3", "wav"):
            _ff(["-i", f, "-vn", out], root)
        elif fmt == "webm":
            _ff(["-i", f, "-vf", f"{sc}fps={fps}".rstrip(","), "-c:v", "libvpx-vp9", "-b:v", "1M", "-deadline", "realtime", "-cpu-used", "5",
                 "-c:a", "libopus", out], root)
        else:
            _ff(["-i", f, "-vf", f"{sc}fps={fps},format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac",
                 "-movflags", "+faststart", out], root)

    elif op == "frame":
        f = src()
        out = _out_path(root, call, "still", "png")
        _ff(["-ss", _secs(call.get("at"), 0.0), "-i", f, "-frames:v", 1, out], root)

    else:
        raise ToolError("op unknown. Allowed: trim, concat, slideshow, text_overlay, burn_subtitles, overlay_image, add_audio, extract_audio, speed, convert, frame")

    if not out.exists() or out.stat().st_size == 0:
        raise ToolError("Result was not created")
    info = ""
    if out.suffix in (".mp4", ".webm", ".mp3", ".wav"):
        try:
            info = " " + _describe_probe(_probe(out))
        except ToolError:
            pass
    return f"Done: {_rel(root, out)}{info}"


# ------------------------------------------------------------------------- Sprache (TTS)
_VOICES_EDGE = {"de": "de-DE-KatjaNeural", "en": "en-US-AriaNeural", "tr": "tr-TR-EmelNeural", "fr": "fr-FR-DeniseNeural",
                "es": "es-ES-ElviraNeural", "it": "it-IT-ElsaNeural"}


def _piper():
    """(Kommando, Modell) fuer Piper. Sucht im venv und in models/piper/, damit PATH und .env nicht stimmen muessen."""
    here = Path(__file__).resolve().parent
    exe = shutil.which("piper") or next((str(x) for x in (Path(sys.executable).parent / "piper", here / "venv" / "bin" / "piper") if x.exists()), "")
    model = _env("PIPER_MODEL")
    if not model:
        cands = sorted((here / "models" / "piper").glob("*.onnx")) if (here / "models" / "piper").is_dir() else []
        model = str(cands[0]) if cands else ""
    return (exe, model) if exe and model and Path(model).exists() else (None, None)


def _num(v, lo, hi):
    """Zahl aus Agenten-Eingabe, begrenzt auf [lo, hi]; None, wenn nicht lesbar."""
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return None


TTS_ENGINES = ("auto", "piper", "espeak", "edge", "elevenlabs", "openai")
_CLOUD_TTS = {"elevenlabs": "ElevenLabs", "openai": "OpenAI voice"}


def tts_engine(engine=None):
    """Wirksame Stimmen-Engine: Wahl im Aufruf (engine) vor TTS_ENGINE aus .env. 'beste'/'premium' = elevenlabs."""
    e = re.sub(r"[^a-z]", "", str(engine or "").lower())
    if e in ("beste", "premium", "hoch", "gut", "eleven"):
        e = "elevenlabs"
    e = e or _env("TTS_ENGINE", "auto").lower()
    if e not in TTS_ENGINES:
        raise ToolError(f"engine '{e}' unknown. Allowed: {', '.join(TTS_ENGINES)}")
    return e


def speak(root, text, lang="de", name="", voice=None, pitch=None, rate=None, target=None, engine=None):
    """voice/pitch/rate geben jeder Filmfigur eine eigene Stimme: espeak-ng Variante (z. B. m3, f2) bzw. Piper-Modell
    (Dateiname in models/piper/) bzw. Edge-Stimme; pitch 0-99 (50 = normal), rate 0.5-2.0. target = fester Zielpfad (film/ton/).
    engine waehlt fuer diesen Aufruf (z. B. elevenlabs nur dort, wo die Stimme wirklich gut sein muss). Scheitert eine
    Cloud-Stimme (Key fehlt, Guthaben leer, Netz), springt die lokale Stimme ein, ausser TTS_FALLBACK=0."""
    text = str(text or "").strip()[:6000]
    if not text:
        raise ToolError("text missing")
    lang = re.sub(r"[^a-z-]", "", str(lang or "de").lower())[:5] or "de"
    voice = re.sub(r"[^A-Za-z0-9_.+-]", "", str(voice or ""))[:60]
    pitch, rate = _num(pitch, 0, 99), _num(rate, 0.5, 2.0)
    if target is None:
        outdir = root / "output" / "audio"
        outdir.mkdir(parents=True, exist_ok=True)
        base, i = _safe_name(name, "sprecher"), 0
        while (outdir / f"{base}{'' if not i else '-' + str(i)}.mp3").exists():
            i += 1
        target = outdir / f"{base}{'' if not i else '-' + str(i)}.mp3"
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.unlink(missing_ok=True)
    engine, note = tts_engine(engine), ""
    if engine in _CLOUD_TTS:  # Cloud-Stimmen (kosten pro Zeichen) zuerst, bei Fehler lokale Stimme
        try:
            _vp().cloud_tts(engine, text, voice, rate, target)
            p = _probe(target)
            return (f"Speech created with {_CLOUD_TTS[engine]}: {_rel(root, target)} ({p['duration']:.1f} s). "
                    "For videos: video_edit add_audio or slideshow with audio.")
        except (ToolError, OSError) as e:  # requests-Fehler sind OSError
            target.unlink(missing_ok=True)
            if _env("TTS_FALLBACK", "1") == "0":
                raise ToolError(str(e)) if not isinstance(e, ToolError) else e
            note = f"NOTE: {_CLOUD_TTS[engine]} not used ({_clip(str(e), 200)}), local voice instead. "
            engine = "auto"
            if len(voice) >= 16 or voice in ("alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer", "verse"):
                voice = ""  # Cloud-Stimmen-ID passt nicht zu espeak/Piper
    tmp = Path(tempfile.mkdtemp(prefix=".tmp-", dir=root))
    try:
        txt = tmp / "t.txt"
        txt.write_text(text, encoding="utf-8")
        done = False
        pexe, pmodel = _piper()
        if pexe and voice.endswith(".onnx") and (Path(pmodel).parent / voice).is_file():  # eigene Piper-Stimme je Figur
            pmodel = str(Path(pmodel).parent / voice)
        # Piper-Stimmen sind einsprachig (Dateiname z.B. de_DE-thorsten-medium.onnx): automatisch nur fuer passende Sprache
        pl = Path(pmodel).name.split("_")[0].lower() if pmodel else ""
        if pexe and (engine == "piper" or (engine == "auto" and pl == lang.split("-")[0])):
            wav = tmp / "o.wav"
            r = subprocess.run([pexe, "--model", pmodel, "--output_file", str(wav)]
                               + (["--length_scale", f"{1 / rate:.2f}"] if rate else []), input=text, text=True, encoding="utf-8", errors="replace",
                               capture_output=True, timeout=600)
            if r.returncode == 0 and wav.exists():
                _ff(["-i", wav, "-c:a", "libmp3lame", "-q:a", "3", target], root)
                done = True
        if not done and engine in ("auto", "espeak") and shutil.which("espeak-ng"):
            wav = tmp / "o.wav"
            ev = lang.split("-")[0] + ("+" + voice if voice and not voice.endswith(".onnx") and "-" not in voice else "")
            r = subprocess.run(["espeak-ng", "-v", ev, "-s", str(int(150 * (rate or 1))), "-p", str(int(50 if pitch is None else pitch)),
                                "-f", str(txt), "-w", str(wav)],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
            if r.returncode == 0 and wav.exists():
                _ff(["-i", wav, "-c:a", "libmp3lame", "-q:a", "3", target], root)
                done = True
        if not done and engine == "edge":
            ev = voice if "Neural" in voice else (_env("EDGE_VOICE") or _VOICES_EDGE.get(lang.split("-")[0], "en-US-AriaNeural"))
            import importlib.util
            py = sys.executable if importlib.util.find_spec("edge_tts") else (shutil.which("python3") or sys.executable)
            extra = ([f"--pitch={int((pitch - 50) * 2):+d}Hz"] if pitch is not None else []) + ([f"--rate={int((rate - 1) * 100):+d}%"] if rate else [])
            r = subprocess.run([py, "-m", "edge_tts", "--voice", ev, "--file", str(txt), "--write-media", str(target)] + extra,
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
            done = r.returncode == 0 and target.exists()
        if not done:
            raise ToolError(note + "No speech output available. On the Pi: sudo apt install espeak-ng (simple voice), or "
                            "PIPER_MODEL (Piper, good offline voice) or TTS_ENGINE=edge with pip install edge-tts (online voices, unofficial service).")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    p = _probe(target)
    return note + f"Speech created: {_rel(root, target)} ({p['duration']:.1f} s). For videos: video_edit add_audio or slideshow with audio."


# ----------------------------------------------------------------------------- Dokumente bauen
def _parse_md(text):
    blocks, para = [], []

    def flush():
        if para:
            blocks.append(("p", " ".join(para)))
            para.clear()
    for line in text.replace("\r", "").split("\n"):
        st = line.strip()
        if not st:
            flush()
            continue
        m = re.match(r"^(#{1,3})\s+(.*)$", st)
        im = re.fullmatch(r"!\[(.*?)\]\((.+?)\)", st)
        if m:
            flush()
            blocks.append(("h", len(m.group(1)), m.group(2)))
        elif im:
            flush()
            blocks.append(("img", im.group(1), im.group(2)))
        elif re.match(r"^[-*+]\s+", st):
            flush()
            blocks.append(("li", re.sub(r"^[-*+]\s+", "", st)))
        elif re.match(r"^\d+[.)]\s+", st):
            flush()
            blocks.append(("ol", re.sub(r"^\d+[.)]\s+", "", st)))
        elif st.startswith(">"):
            flush()
            blocks.append(("q", st.lstrip("> ").strip()))
        elif re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", st):
            flush()
            blocks.append(("hr",))
        else:
            para.append(st)
    flush()
    return blocks


def _inline_html(t, code_tag="code"):
    t = htmllib.escape(t, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", t)
    t = re.sub(r"`(.+?)`", rf"<{code_tag}>\1</{code_tag}>", t)
    return re.sub(r"\[(.+?)\]\((https?://[^)\s]+)\)", r"\1", t)  # Links: nur Text (PDF/EPUB bleiben schlicht)


def _runs(t):
    """Inline-Markdown -> [(text, bold, italic)] fuer DOCX."""
    out, pos = [], 0
    for m in re.finditer(r"\*\*(.+?)\*\*|(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", t):
        if m.start() > pos:
            out.append((t[pos:m.start()], False, False))
        out.append((m.group(1) or m.group(2), bool(m.group(1)), bool(m.group(2))))
        pos = m.end()
    if pos < len(t):
        out.append((t[pos:], False, False))
    return out


def _md_sources(root, call):
    if call.get("content"):
        return str(call["content"])[:2_000_000]
    srcs = call.get("sources")
    if isinstance(srcs, str):
        srcs = [srcs]
    if not isinstance(srcs, list) or not srcs:
        raise ToolError("sources (list of Markdown files) or content missing")
    return "\n\n".join(_inside_existing(root, s).read_text(encoding="utf-8", errors="replace") for s in srcs[:100])


def _html_pdf(root, call):
    """HTML + CSS -> PDF per WeasyPrint. Nachladen nur aus dem Projektordner (keine Netz-, keine fremden Dateien)."""
    if not isinstance(call.get("html"), str) or not call["html"].strip():
        raise ToolError("html: path to the HTML file or the HTML text itself")
    if "<" in call["html"]:  # HTML direkt im Aufruf -> work/<name>.html, dann rendern
        if len(call["html"].encode()) > 2_000_000:
            raise ToolError("html is too large (max. 2 MB)")
        work = Path(root) / "work"
        work.mkdir(parents=True, exist_ok=True)
        src = work / (_safe_name(call.get("name"), "dokument") + ".html")
        src.write_text(call["html"], encoding="utf-8")
        call = dict(call, html=_rel(root, src))
    try:
        f = _inside(root, call.get("html"))
    except ValueError:
        raise ToolError("html: path is outside the project folder")
    if not f.is_file() or f.suffix.lower() not in (".html", ".htm"):
        raise ToolError(f"html: '{call.get('html')}' is not an HTML file in the project (create it first with write_file)")
    try:
        import weasyprint
    except Exception:
        raise ToolError("WeasyPrint is missing on the server (./install.sh --system). Alternative: make_document with Markdown (sources/content)")
    top = Path(root).resolve()

    def allowed(url):
        if url.startswith("data:"):
            return True
        if url.startswith("file://"):
            from urllib.parse import unquote, urlparse
            p = Path(unquote(urlparse(url).path)).resolve()
            return (p == top or top in p.parents) and p.is_file() and not any(x.startswith(".") for x in p.relative_to(top).parts)
        return False

    if hasattr(weasyprint, "URLFetcher"):  # WeasyPrint ab 66
        class Fetcher(weasyprint.URLFetcher):
            def fetch(self, url, headers=None):
                if not allowed(url):
                    raise ValueError("only files from the project folder allowed")
                return super().fetch(url, headers)
        fetch = Fetcher(allowed_protocols=("file", "data"), allow_redirects=False)
    else:
        def fetch(url, *a, **kw):
            if not allowed(url):
                raise ValueError("only files from the project folder allowed")
            return weasyprint.default_url_fetcher(url, *a, **kw)

    out = _out_path(root, call, _safe_name(f.stem, "dokument"), "pdf")
    weasyprint.HTML(filename=str(f), encoding="utf-8", base_url=str(f.parent), url_fetcher=fetch).write_pdf(str(out))
    return out


def make_document(root, call):
    if call.get("html"):
        out = _html_pdf(root, call)
        try:
            from pypdf import PdfReader
            n = f", {len(PdfReader(str(out)).pages)} pages"
        except Exception:
            n = ""
        return f"Document created: {_rel(root, out)} ({out.stat().st_size // 1024} KB{n}) from HTML."
    fmt = str(call.get("format") or "pdf").lower()
    if fmt not in ("pdf", "docx", "epub", "html"):
        raise ToolError("format: pdf, docx, epub or html")
    title = str(call.get("title") or "Dokument")[:200]
    author = str(call.get("author") or "")[:100]
    blocks = _parse_md(_md_sources(root, call))
    if not blocks:
        raise ToolError("The content is empty")
    out = _out_path(root, call, _safe_name(title, "dokument"), fmt)
    warn = ""
    if fmt == "pdf":
        warn = _build_pdf(out, title, author, blocks, root, str(call.get("page") or "A4").upper())
    elif fmt == "docx":
        _build_docx(out, title, author, blocks, root)
    elif fmt == "epub":
        _build_epub(out, title, author, blocks, root, call.get("cover"))
    else:
        out.write_text(_build_html(title, author, blocks, root, out), encoding="utf-8")
    extra = ""
    if fmt == "pdf":
        try:
            from pypdf import PdfReader
            extra = f", {len(PdfReader(str(out)).pages)} pages"
        except Exception:
            pass
    return f"Document created: {_rel(root, out)} ({out.stat().st_size // 1024} KB{extra}).{warn}"


def _img_path(root, rel):
    try:
        f = _inside(root, rel)
        return f if f.is_file() else None
    except ValueError:
        return None


_WIN_FONTS = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts") + os.sep
_FONT_SETS = [
    ("DejaVuSerif", "/usr/share/fonts/truetype/dejavu/", ("DejaVuSerif.ttf", "DejaVuSerif-Bold.ttf", "DejaVuSerif-Italic.ttf", "DejaVuSerif-BoldItalic.ttf")),
    ("DejaVuSans", "/usr/share/fonts/truetype/dejavu/", ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans-Oblique.ttf", "DejaVuSans-BoldOblique.ttf")),
    ("LiberationSerif", "/usr/share/fonts/truetype/liberation/", ("LiberationSerif-Regular.ttf", "LiberationSerif-Bold.ttf", "LiberationSerif-Italic.ttf", "LiberationSerif-BoldItalic.ttf")),
    # Windows: Systemschriften mit Umlauten und Tuerkisch
    ("Georgia", _WIN_FONTS, ("georgia.ttf", "georgiab.ttf", "georgiai.ttf", "georgiaz.ttf")),
    ("Arial", _WIN_FONTS, ("arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf")),
]


def _pdf_font():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    for fam, d, files in _FONT_SETS:
        if all(os.path.exists(d + f) for f in files):
            if fam not in pdfmetrics.getRegisteredFontNames():
                for suffix, f in zip(("", "-B", "-I", "-BI"), files):
                    pdfmetrics.registerFont(TTFont(fam + suffix, d + f))
                pdfmetrics.registerFontFamily(fam, normal=fam, bold=fam + "-B", italic=fam + "-I", boldItalic=fam + "-BI")
            return fam
    return "Helvetica"


def _build_pdf(out, title, author, blocks, root, page):
    try:
        from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
        from reportlab.lib.pagesizes import A4, A5
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer
    except ImportError:
        raise ToolError("PDF creation needs reportlab (pip install reportlab in the venv)")
    fam = _pdf_font()
    size = A5 if page == "A5" else A4
    fs = 10.5 if page == "A5" else 11
    st = {
        "p": ParagraphStyle("p", fontName=fam, fontSize=fs, leading=fs * 1.45, alignment=TA_JUSTIFY, spaceAfter=fs * 0.7),
        "h1": ParagraphStyle("h1", fontName=fam + ("-B" if fam != "Helvetica" else "-Bold"), fontSize=fs * 1.9, leading=fs * 2.3, spaceAfter=fs * 1.2, spaceBefore=fs),
        "h2": ParagraphStyle("h2", fontName=fam + ("-B" if fam != "Helvetica" else "-Bold"), fontSize=fs * 1.35, leading=fs * 1.8, spaceAfter=fs * 0.6, spaceBefore=fs * 1.1),
        "h3": ParagraphStyle("h3", fontName=fam + ("-B" if fam != "Helvetica" else "-Bold"), fontSize=fs * 1.1, leading=fs * 1.5, spaceAfter=fs * 0.4, spaceBefore=fs * 0.8),
        "q": ParagraphStyle("q", fontName=fam + ("-I" if fam != "Helvetica" else "-Oblique"), fontSize=fs, leading=fs * 1.45, leftIndent=14 * mm / 2, spaceAfter=fs * 0.7),
        "li": ParagraphStyle("li", fontName=fam, fontSize=fs, leading=fs * 1.4, leftIndent=12, bulletIndent=2, spaceAfter=fs * 0.3),
        "title": ParagraphStyle("t", fontName=fam + ("-B" if fam != "Helvetica" else "-Bold"), fontSize=fs * 2.6, leading=fs * 3.1, alignment=TA_CENTER),
        "author": ParagraphStyle("a", fontName=fam, fontSize=fs * 1.3, alignment=TA_CENTER, spaceBefore=fs * 2),
    }

    def footer(canv, doc):
        canv.setFont(fam, 8)
        canv.drawCentredString(size[0] / 2, 10 * mm, str(doc.page))
    doc = SimpleDocTemplate(str(out), pagesize=size, title=title, author=author, leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=20 * mm, bottomMargin=20 * mm)
    fw, fh = size[0] - 40 * mm, size[1] - 40 * mm
    story = [Spacer(1, fh * 0.3), Paragraph(htmllib.escape(title), st["title"])]
    if author:
        story.append(Paragraph(htmllib.escape(author), st["author"]))
    story.append(PageBreak())
    first_h1, n_ol = True, 0
    for b in blocks:
        kind = b[0]
        if kind != "ol":
            n_ol = 0
        if kind == "h":
            if b[1] == 1 and not first_h1:
                story.append(PageBreak())
            first_h1 = first_h1 and b[1] != 1
            story.append(Paragraph(_inline_html(b[2], "font"), st[f"h{b[1]}"]))
        elif kind == "p":
            story.append(Paragraph(_inline_html(b[1], "font"), st["p"]))
        elif kind == "li":
            story.append(Paragraph(_inline_html(b[1], "font"), st["li"], bulletText="•"))
        elif kind == "ol":
            n_ol += 1
            story.append(Paragraph(_inline_html(b[1], "font"), st["li"], bulletText=f"{n_ol}."))
        elif kind == "q":
            story.append(Paragraph(_inline_html(b[1], "font"), st["q"]))
        elif kind == "hr":
            story.append(Spacer(1, fs))
        elif kind == "img":
            f = _img_path(root, b[2])
            try:
                if not f:
                    raise ValueError
                img = Image(str(f))
                r = min(fw / img.imageWidth, fh * 0.7 / img.imageHeight, 1.0)
                img.drawWidth, img.drawHeight = img.imageWidth * r, img.imageHeight * r
                story += [img, Spacer(1, fs * 0.6)]
                if b[1]:
                    story.append(Paragraph("<i>" + htmllib.escape(b[1]) + "</i>", st["q"]))
            except Exception:
                story.append(Paragraph(f"[Image cannot be shown: {htmllib.escape(b[2])}]", st["p"]))
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    if fam == "Helvetica":
        return " WARNING: no Unicode font found, special characters (e.g. Turkish) may be missing (server: sudo apt install fonts-dejavu-core)."
    return ""


def _build_docx(out, title, author, blocks, root):
    try:
        from docx import Document
        from docx.shared import Inches
    except ImportError:
        raise ToolError("DOCX creation needs python-docx (pip install python-docx in the venv)")
    d = Document()
    d.core_properties.title, d.core_properties.author = title, author
    d.add_heading(title, 0)
    if author:
        d.add_paragraph(author)
    for b in blocks:
        kind = b[0]
        if kind == "h":
            d.add_heading(b[2], min(b[1], 3))
        elif kind in ("p", "q", "li", "ol"):
            style = {"li": "List Bullet", "ol": "List Number", "q": "Intense Quote"}.get(kind)
            p = d.add_paragraph(style=style)
            for txt, bold, ital in _runs(b[1]):
                r = p.add_run(txt)
                r.bold, r.italic = bold or None, ital or None
        elif kind == "img":
            f = _img_path(root, b[2])
            try:
                d.add_picture(str(f), width=Inches(5.5))
            except Exception:
                d.add_paragraph(f"[Image cannot be shown: {b[2]}]")
    d.save(str(out))


_CSS = ("body{font-family:Georgia,'DejaVu Serif',serif;max-width:42em;margin:2em auto;padding:0 1em;line-height:1.6;color:#222}"
        "h1,h2,h3{font-family:system-ui,sans-serif;line-height:1.25}img{max-width:100%;height:auto}blockquote{border-left:3px solid #bbb;margin-left:0;padding-left:1em;color:#555}")


def _blocks_html(blocks, root, img_prefix=lambda rel: rel, collect=None):
    out, lst = [], None

    def close():
        nonlocal lst
        if lst:
            out.append(f"</{lst}>")
            lst = None
    for b in blocks:
        k = b[0]
        if k not in ("li", "ol"):
            close()
        if k == "h":
            out.append(f"<h{b[1]}>{_inline_html(b[2])}</h{b[1]}>")
        elif k == "p":
            out.append(f"<p>{_inline_html(b[1])}</p>")
        elif k in ("li", "ol"):
            tag = "ul" if k == "li" else "ol"
            if lst != tag:
                close()
                out.append(f"<{tag}>")
                lst = tag
            out.append(f"<li>{_inline_html(b[1])}</li>")
        elif k == "q":
            out.append(f"<blockquote>{_inline_html(b[1])}</blockquote>")
        elif k == "hr":
            out.append("<hr/>")
        elif k == "img":
            f = _img_path(root, b[2])
            if f:
                if collect is not None:
                    collect.append(f)
                out.append(f'<p><img src="{htmllib.escape(img_prefix(b[2]))}" alt="{htmllib.escape(b[1])}"/></p>')
    close()
    return "\n".join(out)


def _build_html(title, author, blocks, root, out):
    prefix = os.path.relpath(root.resolve(), out.parent.resolve()).replace("\\", "/")
    body = _blocks_html(blocks, root, img_prefix=lambda rel: f"{prefix}/{rel}")
    return (f'<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{htmllib.escape(title)}</title><style>{_CSS}</style></head><body><h1>{htmllib.escape(title)}</h1>"
            f"<p><em>{htmllib.escape(author)}</em></p>{body}</body></html>")


def _build_epub(out, title, author, blocks, root, cover):
    chapters, cur = [], []
    for b in blocks:
        if b[0] == "h" and b[1] == 1 and cur:
            chapters.append(cur)
            cur = []
        cur.append(b)
    if cur:
        chapters.append(cur)
    uid = "urn:uuid:" + __import__("uuid").uuid4().hex
    images = {}
    items, spine, nav = [], [], []
    xhtml = ('<?xml version="1.0" encoding="utf-8"?><!DOCTYPE html><html xmlns="http://www.w3.org/1999/xhtml" lang="de"><head>'
             '<meta charset="utf-8"/><title>{t}</title><style>{css}</style></head><body>{b}</body></html>')
    with zipfile.ZipFile(out, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip")  # muss zuerst und unkomprimiert sein
        z.writestr("META-INF/container.xml", '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                   '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>',
                   compress_type=zipfile.ZIP_DEFLATED)
        for i, ch in enumerate(chapters, 1):
            found = []
            body = _blocks_html(ch, root, img_prefix=lambda rel: "images/" + _safe_name(Path(rel).stem, "bild") + Path(rel).suffix.lower(), collect=found)
            for f in found:
                nm = _safe_name(f.stem, "bild") + f.suffix.lower()
                if nm not in images:
                    images[nm] = f
            head = next((b[2] for b in ch if b[0] == "h"), f"Kapitel {i}")
            fn = f"ch{i}.xhtml"
            z.writestr("OEBPS/" + fn, xhtml.format(t=htmllib.escape(head), css=_CSS, b=body), compress_type=zipfile.ZIP_DEFLATED)
            items.append(f'<item id="ch{i}" href="{fn}" media-type="application/xhtml+xml"/>')
            spine.append(f'<itemref idref="ch{i}"/>')
            nav.append(f'<li><a href="{fn}">{htmllib.escape(head)}</a></li>')
        mt = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".svg": "image/svg+xml", ".webp": "image/webp"}
        meta_cover = ""
        for j, (nm, f) in enumerate(images.items(), 1):
            z.writestr("OEBPS/images/" + nm, f.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
            items.append(f'<item id="img{j}" href="images/{nm}" media-type="{mt.get(Path(nm).suffix, "image/png")}"/>')
        cf = _img_path(root, cover) if cover else None
        if cf and cf.suffix.lower() in mt:
            z.writestr("OEBPS/cover" + cf.suffix.lower(), cf.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
            items.append(f'<item id="cover-image" href="cover{cf.suffix.lower()}" media-type="{mt[cf.suffix.lower()]}" properties="cover-image"/>')
            meta_cover = '<meta name="cover" content="cover-image"/>'
        z.writestr("OEBPS/nav.xhtml", xhtml.format(t="Inhalt", css=_CSS, b=f'<nav xmlns:epub="http://www.idpf.org/2007/ops" epub:type="toc"><h1>Inhalt</h1><ol>{"".join(nav)}</ol></nav>'),
                   compress_type=zipfile.ZIP_DEFLATED)
        items.append('<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>')
        opf = ('<?xml version="1.0" encoding="utf-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bid">'
               f'<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="bid">{uid}</dc:identifier><dc:title>{htmllib.escape(title)}</dc:title>'
               f'<dc:creator>{htmllib.escape(author or "unbekannt")}</dc:creator><dc:language>de</dc:language>'
               f'<meta property="dcterms:modified">{time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}</meta>{meta_cover}</metadata>'
               f'<manifest>{"".join(items)}</manifest><spine>{"".join(spine)}</spine></package>')
        z.writestr("OEBPS/content.opf", opf, compress_type=zipfile.ZIP_DEFLATED)


# ----------------------------------------------------------------------------- Dispatcher
def run_tool(call, root, perms):
    """call: dict {"tool": ..., ...}. Gibt (text, erzeugte_datei_oder_None) zurueck. Wirft nie."""
    name = str((call or {}).get("tool", ""))
    spec = TOOLS.get(name)
    if not spec:
        return f"ERROR: unknown tool '{name}'. Allowed: {', '.join(available(perms)) or 'none'}.", None
    if name not in available(perms):
        return f"ERROR: tool '{name}' is not allowed for you.", None
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    try:
        if name == "web_search":
            out = web_search(call.get("query"), call.get("count"))
        elif name == "fetch_url":
            out = fetch_url(call.get("url"))
        elif name == "image_search":
            out = image_search(call.get("query"), call.get("count"))
        elif name == "image_save":
            out = image_save(root, call.get("url"), call.get("name"), call.get("path"))
        elif name == "canva_upload":
            out = canva_upload(root, call.get("path"), call.get("upload_url") or call.get("url"))
        elif name == "image_generate":
            out = image_generate(root, call)
        elif name == "video_generate":
            out = video_generate(root, call)
        elif name == "video_ai":
            out = _vp().video_ai(root, call)
        elif name == "sound_generate":
            out = _vp().sound_generate(root, call)
        elif name == "site_macro":
            out = site_macro(root, call)
        elif name == "list_files":
            out = list_files(root, call.get("path"))
        elif name == "view_image":  # die Bilder selbst haengt app.run_with_tools an
            out = view_image(root, call.get("path"), call.get("page"))[0]
        elif name == "download_file":
            out = download_file(root, call.get("url"), call.get("name"))
        elif name == "copy_files":
            out = copy_files(root, call.get("from"), call.get("to"), bool(call.get("move")))
        elif name == "write_file":
            out = write_code(root, call.get("path"), call.get("content"))
        elif name == "write_code":
            out = write_code(root, call.get("path"), call.get("content"))
        elif name == "check_code":
            out = check_code(root, call.get("path"))
        elif name == "browse_page":  # Screenshot haengt app.run_with_tools an
            out = browse_page(root, call.get("url"), call.get("screenshot"), call.get("wait"), call.get("save"))[0]
        elif name == "run_code":
            out = run_code(root, call.get("path"), call.get("code"), call.get("lang"), call.get("args"), call.get("stdin"))
        elif name == "rust_project":
            import rust_builder  # erst hier: rust_builder importiert dieses Modul
            out = rust_builder.rust_project(root, call)
        elif name == "media_info":
            out = media_info(root, call.get("path"))
        elif name == "video_edit":
            out = video_edit(root, call)
        elif name == "speak":
            if call.get("list_voices"):
                out = _vp().elevenlabs_voices(call.get("lang"))
            else:
                out = speak(root, call.get("text"), call.get("lang"), call.get("name"), call.get("voice"), call.get("pitch"),
                            call.get("rate"), engine=call.get("engine"))
        elif name == "make_document":
            out = make_document(root, call)
        elif name == "film":
            import film_studio  # erst hier: film_studio importiert dieses Modul
            out = film_studio.film(root, call)
        else:
            out = read_file(root, call.get("path"), call.get("offset"))
        made = None
        m = re.search(r"((?:assets|downloads|output|karten|film)/[\w./-]+?)(?:\s|\(|$|\.\s|,)", out) if name in (
            "image_save", "image_generate", "video_generate", "site_macro", "video_ai", "sound_generate", "download_file", "video_edit", "speak", "make_document", "run_code", "browse_page",
            "film", "rust_project") else None
        if m:
            made = m.group(1)
        return out, made
    except ToolError as e:
        return f"ERROR: {e}", None
    except requests.RequestException as e:
        return f"ERROR: network ({type(e).__name__}). Try again later or search differently.", None
    except Exception as e:  # Modell soll weiterarbeiten koennen
        return f"ERROR: {type(e).__name__}: {e}", None
