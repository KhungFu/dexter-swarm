#!/usr/bin/env python3
"""Windows: Voraussetzungen pruefen und fehlende Teile NUR NACH RUECKFRAGE nachinstallieren.

    venv\\Scripts\\python.exe voraussetzungen.py            # pruefen, Liste zeigen, vor jeder Installation fragen (install.ps1)
    venv\\Scripts\\python.exe voraussetzungen.py --start    # beim Start (hyperstead-start.bat): eine Frage mit 20 s Zeit,
                                                         #   ohne Antwort startet Hyperstead einfach (Autostart haengt nie)
    venv\\Scripts\\python.exe voraussetzungen.py --liste    # nur zeigen, nichts fragen, nichts installieren

Antworten (eine Taste): j = installieren, n = nicht, a = alle weiteren ja, x = alle weiteren nein.
Mit n abgelehnte Teile merkt sich .voraussetzungen-nein: der Start fragt danach nicht mehr, install.ps1 fragt wieder.
Installiert wird mit winget (Programme), pip (Python-Pakete im venv) oder per Download nach tools/ (Poppler, OCR-Sprachen).
Nichts wird ohne j installiert. Auf Linux/Pi gibt es dafuer ./install.sh.
"""
import argparse
import hashlib
import importlib.util
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import win_pfade  # noqa: E402

WIN = os.name == "nt"
NEIN_DATEI = HERE / ".voraussetzungen-nein"
STEMPEL = HERE / "venv" / ".requirements.sha256"
BILDRECHNER = Path(os.environ.get("PCL_BILDRECHNER_DIR", r"C:\bildrechner"))
START_WARTEN = 20   # Sekunden fuer die Frage beim Start, danach "n"
WINGET_OK = (0, -1978335189, -1978335135)  # 0x8A15002B "kein Update", 0x8A150061 "schon installiert"


# ----------------------------------------------------------------------------- .env
def env_lesen(f=None):
    """KEY=wert aus .env wie app.load_env (Anfuehrungszeichen, Kommentar hinter dem Wert)."""
    f = f or HERE / ".env"
    out = {}
    if not Path(f).exists():
        return out
    for line in Path(f).read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip()
        if v[:1] in ('"', "'"):
            end = v.find(v[0], 1)
            v = v[1:end] if end > 0 else v[1:]
        else:
            v = re.split(r"\s+#", v, maxsplit=1)[0].strip()
        out[k.strip()] = v
    return out


def env_setzen(key, val, f=None):
    """Setzt KEY=val in .env (ersetzt eine aktive Zeile, sonst anhaengen). Kommentare bleiben."""
    f = Path(f or HERE / ".env")
    lines = f.read_text(encoding="utf-8-sig").splitlines() if f.exists() else []
    done = False
    for i, line in enumerate(lines):
        if re.match(rf"^\s*{re.escape(key)}\s*=", line):
            lines[i] = f"{key}={val}"
            done = True
    if not done:
        lines += ["", "# gesetzt von voraussetzungen.py", f"{key}={val}"]
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ[key] = val


def cfg(key, default=""):
    return os.environ.get(key) or default


# ----------------------------------------------------------------------------- Hilfen
def wo(name):
    return shutil.which(name)


def run(cmd, **kw):
    """Befehl sichtbar ausfuehren (Ausgabe direkt im Fenster). Gibt den Exit-Code zurueck."""
    print("   > " + " ".join(f'"{c}"' if " " in str(c) else str(c) for c in cmd), flush=True)
    try:
        return subprocess.run([str(c) for c in cmd], stdin=subprocess.DEVNULL, **kw).returncode
    except OSError as e:
        print(f"   konnte nicht gestartet werden: {e}")
        return 1


def winget(pid, *extra):
    if not wo("winget"):
        raise RuntimeError("winget fehlt. 'App-Installer' aus dem Microsoft Store installieren, dann erneut.")
    rc = run(["winget", "install", "-e", "--id", pid, "--accept-package-agreements", "--accept-source-agreements", *extra])
    if rc not in WINGET_OK:
        raise RuntimeError(f"winget meldet Fehler {rc}")


def pip(*pakete):
    if run([sys.executable, "-m", "pip", "install", "--upgrade", *pakete]) != 0:
        raise RuntimeError("pip install ging nicht (Internet?)")
    importlib.invalidate_caches()


def laden(url, ziel):
    import requests
    ziel = Path(ziel)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    teil = ziel.with_name(ziel.name + ".part")
    print(f"   lade {url}", flush=True)
    with requests.get(url, stream=True, timeout=60, headers={"User-Agent": "Hyperstead-Installer"}) as r:
        r.raise_for_status()
        with open(teil, "wb") as fh:
            for chunk in r.iter_content(1 << 16):
                fh.write(chunk)
    teil.replace(ziel)
    return ziel


def req_hash():
    return hashlib.sha256((HERE / "requirements.txt").read_bytes()).hexdigest().lower()


# ----------------------------------------------------------------------------- Pruefungen
def pakete_da():
    return STEMPEL.exists() and STEMPEL.read_text(encoding="utf-8-sig").strip().lower() == req_hash()


def pakete_install():
    if run([sys.executable, "-m", "pip", "install", "-r", HERE / "requirements.txt"]) != 0:
        raise RuntimeError("pip install -r requirements.txt ging nicht")
    STEMPEL.write_text(req_hash(), encoding="utf-8")


def piper_da():
    scripts = Path(sys.executable).parent
    exe = wo("piper") or any((scripts / n).exists() for n in ("piper.exe", "piper"))
    return bool(exe) and any((HERE / "models" / "piper").glob("*.onnx"))


def piper_install():
    pip("piper-tts")
    (HERE / "models" / "piper").mkdir(parents=True, exist_ok=True)
    if not any((HERE / "models" / "piper").glob("*.onnx")):
        if run([sys.executable, "-m", "piper.download_voices", "de_DE-thorsten-medium", "--download-dir", HERE / "models" / "piper"]) != 0:
            raise RuntimeError("Stimme konnte nicht geladen werden (Internet?)")


def browser_da():
    p = cfg("PCL_BROWSER_PATH")
    if p and Path(p).is_file():
        return True
    if not importlib.util.find_spec("playwright"):
        return False
    code = ("import os,sys\nfrom playwright.sync_api import sync_playwright\n"
            "with sync_playwright() as p: sys.exit(0 if os.path.exists(p.chromium.executable_path) else 1)")
    try:
        return subprocess.run([sys.executable, "-c", code], capture_output=True, timeout=60).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def browser_install():
    pip("playwright")
    if run([sys.executable, "-m", "playwright", "install", "chromium"]) != 0:
        raise RuntimeError("Chromium konnte nicht geladen werden")


def tess_langs():
    exe = wo("tesseract")
    if not exe:
        return set()
    try:
        out = subprocess.run([exe, "--list-langs"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20).stdout
    except (OSError, subprocess.TimeoutExpired):
        return set()
    return set(out.split()[1:]) if out else set()


def ocr_sprachen_install():
    # Eigener Ordner tools/tessdata (ohne Administrator), win_pfade setzt dann TESSDATA_PREFIX darauf
    d = HERE / "tools" / "tessdata"
    for lang in ("eng", "osd", "tur", "deu"):  # deu zuletzt: erst dann gilt der Ordner als fertig
        if not (d / f"{lang}.traineddata").exists():
            laden(f"https://github.com/tesseract-ocr/tessdata_fast/raw/main/{lang}.traineddata", d / f"{lang}.traineddata")


def poppler_install():
    import requests
    r = requests.get("https://api.github.com/repos/oschwartz10612/poppler-windows/releases/latest", timeout=30,
                     headers={"User-Agent": "Hyperstead-Installer"})
    r.raise_for_status()
    url = next((a["browser_download_url"] for a in r.json().get("assets", []) if a.get("name", "").endswith(".zip")), None)
    if not url:
        raise RuntimeError("keine ZIP-Datei im neuesten Poppler-Release gefunden")
    ziel = HERE / "tools" / "poppler"
    z = laden(url, HERE / "tools" / "poppler.zip")
    shutil.rmtree(ziel, ignore_errors=True)
    with zipfile.ZipFile(z) as zf:
        zf.extractall(ziel)
    z.unlink(missing_ok=True)


def blender_da():
    import film_studio
    return bool(film_studio.blender_exe())


def bildrechner_relevant():
    return cfg("IMAGE_PROVIDER").lower() == "sdcpp"


def bildrechner_install():
    if run(["powershell", "-ExecutionPolicy", "Bypass", "-File", HERE / "deploy" / "windows" / "bildrechner-einrichten.ps1"]) != 0:
        raise RuntimeError("Einrichtung abgebrochen (Meldung oben)")


def _sdcpp_lokal():
    u = urlparse(cfg("SDCPP_URL", "http://127.0.0.1:1234"))
    return u.hostname in ("127.0.0.1", "localhost", "::1"), u.port or 1234


def bildrechner_laeuft():
    port = _sdcpp_lokal()[1]
    try:
        with socket.create_connection(("127.0.0.1", port), 1.5):
            return True
    except OSError:
        return False


def bildrechner_starten():
    bat = BILDRECHNER / "bildrechner-start.bat"
    # eigenes Fenster (minimiert), Hyperstead startet gleich weiter; der Bildrechner braucht 1-2 Minuten
    subprocess.Popen(["cmd", "/c", "start", "Bildrechner", "/min", str(bat)], cwd=str(BILDRECHNER))


def cargo_da():
    home = Path(os.environ.get("CARGO_HOME") or Path.home() / ".cargo") / "bin"
    return bool(wo("cargo") or (home / "cargo.exe").exists() or (home / "cargo").exists())


def rust_install():
    winget("Rustlang.Rustup")
    win_pfade.erweitern()
    rustup = wo("rustup")
    if rustup and not wo("rustc"):
        run([rustup, "toolchain", "install", "stable", "--profile", "minimal"])
        run([rustup, "default", "stable"])


def vswhere():
    p = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
    return p if p.exists() else None


def buildtools_da():
    vw = vswhere()
    if not vw:
        return False
    try:
        out = subprocess.run([str(vw), "-products", "*", "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                              "-property", "installationPath"], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.TimeoutExpired):
        return False
    return bool(out.strip())


def bash_da():
    p = wo("bash")
    return bool(p) and "system32" not in p.lower()  # C:\Windows\System32\bash.exe ist WSL, nicht Git-Bash


def tsc_install():
    npm = wo("npm")
    if not npm:
        raise RuntimeError("npm fehlt (erst Node.js installieren)")
    if run([npm, "install", "-g", "typescript"]) != 0:
        raise RuntimeError("npm install -g typescript ging nicht")


class Teil:
    """Eine Voraussetzung. da() = vorhanden, install() = nachinstallieren (nur nach j)."""

    def __init__(self, id, name, wozu, groesse, befehl, da, install, relevant=None, braucht=None, nur_start=False, merken=True):
        self.id, self.name, self.wozu, self.groesse, self.befehl = id, name, wozu, groesse, befehl
        self.da, self.install = da, install
        self.relevant = relevant or (lambda: True)
        self.braucht, self.nur_start, self.merken = braucht, nur_start, merken


def wg(pid):
    return lambda: winget(pid)


def teile():
    W = "winget install -e --id "
    return [
        Teil("pakete", "Python-Pakete (requirements.txt)", "Hyperstead selbst, nach einem Update geaendert", "klein",
             r"venv\Scripts\pip install -r requirements.txt", pakete_da, pakete_install),
        Teil("ffmpeg", "ffmpeg + ffprobe", "Video schneiden, Filmstudio, Sprachausgabe, YouTube", "ca. 100 MB",
             W + "Gyan.FFmpeg", lambda: bool(wo("ffmpeg") and wo("ffprobe")), wg("Gyan.FFmpeg")),
        Teil("piper", "Piper (gute deutsche Offline-Stimme)", "Sprachausgabe, Filmstudio-Stimmen", "ca. 120 MB",
             r"venv\Scripts\pip install piper-tts + Stimme de_DE-thorsten-medium nach models\piper", piper_da, piper_install),
        Teil("edge", "edge-tts (Online-Stimmen fuer Tuerkisch, Englisch ...)", "Sprachausgabe in anderen Sprachen als Deutsch",
             "klein", r"venv\Scripts\pip install edge-tts", lambda: bool(importlib.util.find_spec("edge_tts")), lambda: pip("edge-tts")),
        Teil("browser", "Echter Browser (Playwright + Chromium)", "Werkzeug browse_page (Seiten mit JavaScript)", "ca. 400 MB",
             r"venv\Scripts\pip install playwright, dann venv\Scripts\python -m playwright install chromium", browser_da, browser_install),
        Teil("tesseract", "Tesseract (OCR)", "gescannte PDFs und Bilder lesen", "ca. 80 MB",
             W + "UB-Mannheim.TesseractOCR", lambda: bool(wo("tesseract")), wg("UB-Mannheim.TesseractOCR")),
        Teil("ocr-sprachen", "OCR-Sprachen Deutsch + Tuerkisch", "Umlaute und tuerkische Buchstaben richtig erkennen", "ca. 15 MB",
             r"Download nach tools\tessdata (tessdata_fast)", lambda: {"deu", "tur"} <= tess_langs(), ocr_sprachen_install, braucht="tesseract"),
        Teil("poppler", "Poppler (pdftoppm)", "gescannte PDFs Seite fuer Seite lesen", "ca. 40 MB",
             r"Download (github.com/oschwartz10612/poppler-windows) nach tools\poppler", lambda: bool(wo("pdftoppm")), poppler_install),
        Teil("blender", "Blender", "Filmstudio (Werkzeug film)", "ca. 400 MB Download",
             W + "BlenderFoundation.Blender", blender_da, wg("BlenderFoundation.Blender")),
        Teil("bildrechner", "Bildrechner (sd-server + FLUX-Modelle)", "eigene Bilder ohne Cloud (IMAGE_PROVIDER=sdcpp)", "ca. 4 GB",
             r"powershell -ExecutionPolicy Bypass -File deploy\windows\bildrechner-einrichten.ps1",
             lambda: (BILDRECHNER / "sd-server.exe").exists(), bildrechner_install, relevant=bildrechner_relevant),
        Teil("bildrechner-start", "Bildrechner starten", "laeuft nicht, Bilder (sdcpp) gehen sonst nicht", "nur starten",
             str(BILDRECHNER / "bildrechner-start.bat"), bildrechner_laeuft, bildrechner_starten,
             relevant=lambda: bildrechner_relevant() and _sdcpp_lokal()[0] and (BILDRECHNER / "bildrechner-start.bat").exists(),
             nur_start=True, merken=False),
        Teil("rust", "Rust (rustup, cargo, rustc)", "Rust-Code pruefen und Rust-Programme bauen", "ca. 300 MB",
             W + "Rustlang.Rustup", cargo_da, rust_install),
        Teil("buildtools", "Visual Studio Build Tools (C++)", "Linker, ohne den Rust keine .exe bauen kann", "ca. 6 GB",
             W + 'Microsoft.VisualStudio.2022.BuildTools --override "--quiet --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"',
             buildtools_da, lambda: winget("Microsoft.VisualStudio.2022.BuildTools", "--override",
                                          "--quiet --wait --norestart --nocache --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"),
             braucht="rust"),
        Teil("cargo-unsafe", "Rust-Programme bauen erlauben (PCL_CARGO_UNSAFE=1)",
             "Werkzeug rust_project. ACHTUNG: Code der Agenten laeuft unter Windows OHNE Abschottung mit deinen Rechten",
             "nur Einstellung in .env", "PCL_CARGO_UNSAFE=1 in .env", lambda: cfg("PCL_CARGO_UNSAFE") == "1",
             lambda: env_setzen("PCL_CARGO_UNSAFE", "1"), braucht="rust"),
        Teil("node", "Node.js", "JavaScript pruefen, Remotion/Werkstatt, Claude-CLI", "ca. 30 MB", W + "OpenJS.NodeJS.LTS",
             lambda: bool(wo("node")), wg("OpenJS.NodeJS.LTS")),
        Teil("typescript", "TypeScript (tsc)", "TypeScript pruefen", "ca. 25 MB", "npm install -g typescript",
             lambda: bool(wo("tsc")), tsc_install, braucht="node"),
        Teil("java", "Java JDK 21 (javac)", "Java pruefen", "ca. 190 MB", W + "EclipseAdoptium.Temurin.21.JDK",
             lambda: bool(wo("javac")), wg("EclipseAdoptium.Temurin.21.JDK")),
        Teil("go", "Go (gofmt)", "Go pruefen", "ca. 70 MB", W + "GoLang.Go", lambda: bool(wo("gofmt")), wg("GoLang.Go")),
        Teil("gcc", "GCC (gcc, g++)", "C und C++ pruefen", "ca. 250 MB", W + "BrechtSanders.WinLibs.POSIX.UCRT",
             lambda: bool(wo("gcc") and wo("g++")), wg("BrechtSanders.WinLibs.POSIX.UCRT")),
        Teil("bash", "Git mit Git-Bash", "Shell-Skripte pruefen, dazu git fuer Updates", "ca. 60 MB", W + "Git.Git", bash_da, wg("Git.Git")),
        Teil("ruby", "Ruby", "Ruby pruefen", "ca. 130 MB", W + "RubyInstallerTeam.Ruby.3.3", lambda: bool(wo("ruby")),
             wg("RubyInstallerTeam.Ruby.3.3")),
        Teil("php", "PHP", "PHP pruefen", "ca. 30 MB", W + "PHP.PHP.8.3", lambda: bool(wo("php")), wg("PHP.PHP.8.3")),
        Teil("lua", "Lua (luac)", "Lua pruefen", "ca. 5 MB", W + "DEVCOM.Lua", lambda: bool(wo("luac")), wg("DEVCOM.Lua")),
    ]


# ----------------------------------------------------------------------------- Fragen
def frage(text, erlaubt, standard, warten=None, eingabe=None):
    """Eine Taste. Ohne Antwort in `warten` Sekunden oder ohne Tastatur (Autostart, Umleitung) gilt `standard`."""
    zeige = "/".join(c.upper() if c == standard else c for c in erlaubt)
    print(f"{text} [{zeige}] ", end="", flush=True)
    if eingabe is not None:  # Tests
        ch = next(eingabe, standard)
        print(ch)
        return ch
    if not sys.stdin or not sys.stdin.isatty():
        print(f"{standard} (keine Eingabe moeglich)")
        return standard
    ende = time.time() + warten if warten else None
    if WIN:
        import msvcrt
        while True:
            if msvcrt.kbhit():
                ch = msvcrt.getwch().lower()
                if ch in ("\r", "\n"):
                    ch = standard
                if ch in erlaubt:
                    print(ch)
                    return ch
            elif ende and time.time() > ende:
                print(f"{standard} (keine Antwort in {warten} s)")
                return standard
            time.sleep(0.05)
    import select
    while True:
        rest = None if ende is None else max(0.0, ende - time.time())
        r, _, _ = select.select([sys.stdin], [], [], rest)
        if not r:
            print(f"{standard} (keine Antwort in {warten} s)")
            return standard
        ch = (sys.stdin.readline().strip().lower() or standard)[:1]
        if ch in erlaubt:
            return ch


def nein_lesen():
    try:
        return {z.strip() for z in NEIN_DATEI.read_text(encoding="utf-8").split() if z.strip()}
    except OSError:
        return set()


def nein_schreiben(ids):
    NEIN_DATEI.write_text("\n".join(sorted(ids)) + ("\n" if ids else ""), encoding="utf-8")


def ist_da(t):
    try:
        return bool(t.da())
    except Exception:  # noqa: BLE001 - eine kaputte Pruefung zaehlt als "fehlt", bricht aber nichts ab
        return False


def ist_relevant(t):
    try:
        return bool(t.relevant())
    except Exception:  # noqa: BLE001
        return False


def fehlende(liste, start):
    return [t for t in liste if (start or not t.nur_start) and ist_relevant(t) and not ist_da(t)]


def zeigen(fehl, nein):
    print(f"\nFehlende Teile ({len(fehl)}):")
    for t in fehl:
        merk = "  (frueher abgelehnt)" if t.id in nein else ""
        print(f"  FEHLT  {t.name}  [{t.groesse}]{merk}")
        print(f"         wozu:   {t.wozu}")
        print(f"         Befehl: {t.befehl}")


def ablauf(modus="install", liste=None, eingabe=None):
    """modus: install (alle fragen), start (eine Frage mit Zeitlimit, Abgelehntes nicht erneut), liste (nur zeigen).
    Gibt ein dict mit installiert/fehlgeschlagen/abgelehnt/uebersprungen zurueck."""
    liste = teile() if liste is None else liste
    start = modus == "start"
    erg = {"installiert": [], "fehlgeschlagen": [], "abgelehnt": [], "uebersprungen": []}
    fehl = fehlende(liste, start)
    nein = nein_lesen()
    if not fehl:
        print("Voraussetzungen: alles da.")
        return erg
    zeigen(fehl, nein)
    if modus == "liste":
        return erg
    angebot = [t for t in fehl if not (start and t.merken and t.id in nein)]
    if start:
        alt = [t.name for t in fehl if t not in angebot]
        if alt:
            print(f"\nNicht gefragt (frueher abgelehnt): {', '.join(alt)}. Erneut fragen: install.ps1")
        if not angebot:
            return erg
        print()
        a = frage(f"{len(angebot)} Teil(e) jetzt installieren? j = einzeln fragen, n = diesmal nicht, x = beim Start nie mehr fragen",
                  "jnx", "n", START_WARTEN, eingabe)
        if a != "j":
            if a == "x":
                nein_schreiben(nein | {t.id for t in angebot if t.merken})
            print("Hyperstead startet ohne die fehlenden Teile.")
            erg["abgelehnt"] = [t.id for t in angebot]
            return erg
    alle = None
    print()
    for t in angebot:
        if t.braucht and any(b.id == t.braucht for b in liste) and not ist_da(next(b for b in liste if b.id == t.braucht)):
            print(f"-- {t.name}: uebersprungen, weil '{t.braucht}' fehlt.")
            erg["uebersprungen"].append(t.id)
            continue
        if ist_da(t):  # z. B. durch ein anderes Paket mitgekommen
            continue
        a = alle or frage(f"{t.name} installieren? ({t.groesse})  j/n, a = alle weiteren ja, x = alle weiteren nein",
                          "jnax", "n", 120 if start else None, eingabe)
        if a in ("a", "x"):
            alle = "j" if a == "a" else "n"
            a = alle
        if a != "j":
            erg["abgelehnt"].append(t.id)
            if t.merken:
                nein.add(t.id)
            continue
        print(f"== {t.name}: wird installiert ...", flush=True)
        try:
            t.install()
            win_pfade.erweitern()
            if ist_da(t):
                print(f"   fertig: {t.name}")
                erg["installiert"].append(t.id)
                nein.discard(t.id)
            else:
                print(f"   installiert, wird aber noch nicht gefunden. Rechner neu starten oder neues Fenster oeffnen; sonst: {t.befehl}")
                erg["fehlgeschlagen"].append(t.id)
        except Exception as e:  # noqa: BLE001
            print(f"   FEHLER: {e}. Von Hand: {t.befehl}")
            erg["fehlgeschlagen"].append(t.id)
    nein_schreiben(nein)
    print(f"\nInstalliert: {len(erg['installiert'])}, fehlgeschlagen: {len(erg['fehlgeschlagen'])}, "
          f"abgelehnt: {len(erg['abgelehnt'])}, uebersprungen: {len(erg['uebersprungen'])}")
    if erg["installiert"] or erg["fehlgeschlagen"]:
        print("Pruefen:  python selftest.py")
    return erg


def in_venv():
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Voraussetzungen pruefen und nach Rueckfrage nachinstallieren (Windows)")
    ap.add_argument("--start", action="store_true", help="Modus fuer hyperstead-start.bat (eine Frage, 20 s Zeit)")
    ap.add_argument("--liste", action="store_true", help="nur zeigen, nichts installieren")
    a = ap.parse_args(argv)
    if not WIN:
        print("voraussetzungen.py ist fuer Windows. Auf dem Pi/Linux: ./install.sh (bzw. ./install.sh --update)")
        return 0
    vpy = HERE / "venv" / "Scripts" / "python.exe"
    if not in_venv() and vpy.exists() and not os.environ.get("HYPERSTEAD_VORAUS_REEXEC"):
        return subprocess.call([str(vpy), __file__, *(argv if argv is not None else sys.argv[1:])],
                               env=dict(os.environ, HYPERSTEAD_VORAUS_REEXEC="1"))
    os.system("")  # Farben/Steuerzeichen in cmd.exe
    for k, v in env_lesen().items():
        os.environ.setdefault(k, v)
    win_pfade.erweitern()
    print("Hyperstead: Voraussetzungen pruefen ...")
    try:
        ablauf("liste" if a.liste else "start" if a.start else "install")
    except KeyboardInterrupt:
        print("\nabgebrochen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
