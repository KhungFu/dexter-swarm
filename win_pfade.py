"""Windows: Programme finden, die nachinstalliert wurden, ohne dass PATH stimmt und ohne neues Fenster.

winget, Tesseract, Git, Rust, Node, Ruby usw. legen ihre Programme in eigene Ordner. Manche tragen sich gar nicht in PATH
ein (Tesseract von UB Mannheim, Git-Bash), andere erst fuer NEUE Fenster. Hyperstead sucht ueberall mit shutil.which,
deshalb ergaenzt dieses Modul beim Start einmal den PATH des laufenden Prozesses:

1. PATH frisch aus der Registry (System + Benutzer), damit gerade Installiertes ohne neues Fenster gefunden wird.
2. Bekannte Installationsordner (Liste unten), nur wenn sie existieren.
3. Hyperstead-eigene Ordner tools/ (Poppler) und tools/tessdata (OCR-Sprachen, setzt TESSDATA_PREFIX).

Auf Linux/Pi tut es nichts. Wird von agent_tools.py beim Import aufgerufen (also auch von app.py und selftest.py).
"""
import glob
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Programme, die in einem winget-Paketordner (portable ZIP) liegen koennen und dann gesucht werden
WINGET_SUCHE = ("ffmpeg.exe", "gcc.exe", "php.exe", "luac.exe", "luac5.4.exe", "pdftoppm.exe")


def _registry_path():
    """PATH aus der Registry (System, dann Benutzer), Variablen wie %USERPROFILE% aufgeloest."""
    try:
        import winreg
    except ImportError:
        return []
    out = []
    for hive, key in ((winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
                      (winreg.HKEY_CURRENT_USER, "Environment")):
        try:
            with winreg.OpenKey(hive, key) as k:
                val = winreg.QueryValueEx(k, "Path")[0]
        except OSError:
            continue
        out += [os.path.expandvars(p) for p in str(val).split(";") if p.strip()]
    return out


def bekannte_ordner(env=None, here=HERE):
    """Kandidaten-Ordner (nicht geprueft, ob sie existieren). Reihenfolge = Vorrang."""
    env = os.environ if env is None else env
    pf = env.get("ProgramFiles", r"C:\Program Files")
    pf86 = env.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local = env.get("LOCALAPPDATA", "")
    roam = env.get("APPDATA", "")
    home = env.get("USERPROFILE", "")
    j = os.path.join
    dirs = [str(Path(sys.executable).parent)]  # venv\Scripts (piper.exe, playwright.exe)
    if local:
        dirs.append(j(local, "Microsoft", "WinGet", "Links"))
    dirs += [j(pf, "Tesseract-OCR"), j(pf86, "Tesseract-OCR")]
    if local:
        dirs.append(j(local, "Programs", "Tesseract-OCR"))
    dirs += [j(pf, "Git", "bin"), j(pf, "nodejs"), j(pf, "Go", "bin")]
    if roam:
        dirs.append(j(roam, "npm"))  # npm install -g (tsc)
    cargo = env.get("CARGO_HOME") or (j(home, ".cargo") if home else "")
    if cargo:
        dirs.append(j(cargo, "bin"))
    if home:
        dirs.append(j(home, "go", "bin"))
    pats = [j(pf, "Eclipse Adoptium", "jdk-*", "bin"), j(pf, "Microsoft", "jdk-*", "bin"), j(pf, "Java", "jdk*", "bin"),
            r"C:\Ruby*\bin", j(pf, "Ruby*", "bin"), j(pf86, "Lua", "*"), j(pf, "Lua", "*"), j(pf86, "Lua"), j(pf, "Lua"),
            j(pf, "PHP*"), j(str(here), "tools", "poppler", "*", "Library", "bin"), j(str(here), "tools", "poppler", "Library", "bin")]
    for pat in pats:
        dirs += sorted(glob.glob(pat), reverse=True)  # neueste Version zuerst
    if local:
        pk = j(local, "Microsoft", "WinGet", "Packages")
        for name in WINGET_SUCHE:
            for depth in range(1, 5):
                dirs += sorted({str(Path(f).parent) for f in glob.glob(j(pk, *(["*"] * depth), name))}, reverse=True)
    return dirs


def erweitern(env=None, windows=os.name == "nt", here=HERE, registry=True):
    """Ergaenzt env['PATH'] (Standard: os.environ). Gibt die neu angehaengten Ordner zurueck."""
    if not windows:
        return []
    env = os.environ if env is None else env
    teile = [p for p in env.get("PATH", "").split(os.pathsep) if p]
    seen = {os.path.normcase(p.rstrip("\\/")) for p in teile}
    neu = []
    for d in (_registry_path() if registry else []) + bekannte_ordner(env, here):
        key = os.path.normcase(d.rstrip("\\/"))
        if key in seen or not os.path.isdir(d):
            continue
        seen.add(key)
        neu.append(d)
    if neu:
        env["PATH"] = os.pathsep.join(teile + neu)
    tess = Path(here) / "tools" / "tessdata"
    if not env.get("TESSDATA_PREFIX") and (tess / "deu.traineddata").is_file():
        env["TESSDATA_PREFIX"] = str(tess)
    return neu
