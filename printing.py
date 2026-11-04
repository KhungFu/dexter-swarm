"""Drucken der Abendberichte auf einem freigegebenen Netzwerkdrucker.

Linux (Pi): CUPS mit `lpstat` (Drucker auflisten) und `lp` (drucken).
Windows (Laptop): PowerShell `Get-Printer` und `Out-Printer` (auch freigegebene Drucker wie \\\\server\\drucker,
sobald sie in Windows verbunden sind).
Dazu gibt es immer den Testdrucker TEST_PRINTER: er schreibt den Ausdruck als Textdatei nach <workspace>/.druck/,
damit sich alles ohne echten Drucker ausprobieren laesst.
"""
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

TEST_PRINTER = "Testdrucker (Datei)"
TIMEOUT = 30


def is_windows():
    return os.name == "nt"


def _run(cmd, env=None, input_text=None):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, env=env, input=input_text,
                          encoding="utf-8", errors="replace")


def system_status():
    """(bereit, Hinweis) - ob das Betriebssystem ueberhaupt drucken kann."""
    if is_windows():
        return (bool(shutil.which("powershell")), "Windows: Drucker unter Einstellungen > Drucker & Scanner verbinden.")
    if shutil.which("lp") and shutil.which("lpstat"):
        return True, "CUPS ist installiert."
    return False, "CUPS fehlt. Auf dem Pi: sudo apt install cups-client (oder ./install.sh --print)."


def list_printers():
    """(Liste der Druckernamen, Fehlertext oder ''). Der Testdrucker steht immer am Ende."""
    names, err = [], ""
    ok, hint = system_status()
    if not ok:
        return [TEST_PRINTER], hint
    try:
        if is_windows():
            r = _run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                      "Get-Printer | Select-Object -ExpandProperty Name"])
            names = [x.strip() for x in r.stdout.splitlines() if x.strip()]
        else:
            r = _run(["lpstat", "-e"])
            names = [x.strip() for x in r.stdout.splitlines() if x.strip()]
            if not names:
                r = _run(["lpstat", "-a"])
                names = [x.split()[0] for x in r.stdout.splitlines() if x.strip()]
        if r.returncode and not names:
            err = (r.stderr or r.stdout or "").strip()[:300] or "Drucker konnten nicht gelesen werden."
    except (OSError, subprocess.SubprocessError) as e:
        err = f"Drucker konnten nicht gelesen werden: {e}"
    if not names and not err:
        err = "Kein Drucker eingerichtet." + ("" if is_windows() else " Netzwerkdrucker in CUPS hinzufuegen (siehe docs/drucken.md).")
    return names + [TEST_PRINTER], err


def valid_name(name):
    """Druckername nur aus der Liste, ohne Steuerzeichen (er geht an lp bzw. PowerShell)."""
    return bool(name) and len(name) <= 200 and not re.search(r"[\x00-\x1f]", name)


def print_text(printer, title, text, out_dir):
    """Druckt Text. Gibt (ok, Meldung) zurueck. out_dir: Ablage fuer den Testdrucker."""
    if not valid_name(printer):
        return False, "Ungültiger Druckername."
    if printer == TEST_PRINTER:
        d = Path(out_dir)
        d.mkdir(parents=True, exist_ok=True)
        f = d / time.strftime("druck-%Y%m%d-%H%M%S.txt")
        n = 1
        while f.exists():
            n += 1
            f = d / time.strftime(f"druck-%Y%m%d-%H%M%S-{n}.txt")
        f.write_text(text, encoding="utf-8")
        return True, f"Testdrucker: gespeichert als {f.name}"
    ok, hint = system_status()
    if not ok:
        return False, hint
    tmp = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
    try:
        tmp.write(text)
        tmp.close()
        if is_windows():
            env = dict(os.environ, PCL_PRN=printer, PCL_PRN_FILE=tmp.name)  # Werte per Umgebung, nie in den Befehl
            r = _run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                      "Get-Content -Raw -Encoding UTF8 -LiteralPath $env:PCL_PRN_FILE | Out-Printer -Name $env:PCL_PRN"], env=env)
        else:
            r = _run(["lp", "-d", printer, "-t", (title or "Abendbericht")[:100], "--", tmp.name])
        if r.returncode:
            return False, "Drucker meldet einen Fehler: " + ((r.stderr or r.stdout or "").strip()[:300] or f"Code {r.returncode}")
        job = (r.stdout or "").strip()
        return True, "An den Drucker gesendet." + (f" ({job[:120]})" if job else "")
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"Drucken fehlgeschlagen: {e}"
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
