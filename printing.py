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

TEST_PRINTER = "Test printer (file)"
TIMEOUT = 30


def is_windows():
    return os.name == "nt"


def _run(cmd, env=None, input_text=None):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, env=env, input=input_text,
                          encoding="utf-8", errors="replace")


def system_status():
    """(bereit, Hinweis) - ob das Betriebssystem ueberhaupt drucken kann."""
    if is_windows():
        return (bool(shutil.which("powershell")), "Windows: connect printers under Settings > Printers & scanners.")
    if shutil.which("lp") and shutil.which("lpstat"):
        return True, "CUPS is installed."
    return False, "CUPS missing. On the Pi: sudo apt install cups-client (or ./install.sh --print)."


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
            err = (r.stderr or r.stdout or "").strip()[:300] or "Could not read the printers."
    except (OSError, subprocess.SubprocessError) as e:
        err = f"Could not read the printers: {e}"
    if not names and not err:
        err = "No printer set up." + ("" if is_windows() else " Add a network printer in CUPS (see docs/drucken.md).")
    return names + [TEST_PRINTER], err


def valid_name(name):
    """Druckername nur aus der Liste, ohne Steuerzeichen (er geht an lp bzw. PowerShell)."""
    return bool(name) and len(name) <= 200 and not re.search(r"[\x00-\x1f]", name)


def print_text(printer, title, text, out_dir):
    """Druckt Text. Gibt (ok, Meldung) zurueck. out_dir: Ablage fuer den Testdrucker."""
    if not valid_name(printer):
        return False, "Invalid printer name."
    if printer == TEST_PRINTER:
        d = Path(out_dir)
        d.mkdir(parents=True, exist_ok=True)
        f = d / time.strftime("print-%Y%m%d-%H%M%S.txt")
        n = 1
        while f.exists():
            n += 1
            f = d / time.strftime(f"print-%Y%m%d-%H%M%S-{n}.txt")
        f.write_text(text, encoding="utf-8")
        return True, f"Test printer: saved as {f.name}"
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
            r = _run(["lp", "-d", printer, "-t", (title or "Evening report")[:100], "--", tmp.name])
        if r.returncode:
            return False, "Printer reports an error: " + ((r.stderr or r.stdout or "").strip()[:300] or f"Code {r.returncode}")
        job = (r.stdout or "").strip()
        msg = "Sent to the printer." + (f" ({job[:120]})" if job else "")
        problems, warnings = after_print_problems(printer, job)
        if problems:  # Auftrag angenommen, aber er kommt nicht durch: ehrlich melden statt "gesendet"
            return False, "The job was accepted but is not printing: " + " ".join(problems)
        return True, msg + ("" if not warnings else " Note: " + " ".join(warnings))
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"Printing failed: {e}"
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


# ---------------------------------------------------------------- Pruefen, warum nichts herauskommt
WAIT_AFTER = float(os.environ.get("PCL_PRINT_CHECK_WAIT", "6"))   # Sekunden, bevor der Auftrag geprueft wird
_PS_STATUS = ("$p = Get-Printer -Name $env:PCL_PRN -ErrorAction Stop; "
              "'STATUS=' + $p.PrinterStatus; 'TYPE=' + $p.Type; 'PORT=' + $p.PortName; 'DRIVER=' + $p.DriverName; "
              "'SHARED=' + $p.Shared; 'COMPUTER=' + $p.ComputerName; "
              "Get-PrintJob -PrinterName $env:PCL_PRN -ErrorAction SilentlyContinue | "
              "ForEach-Object { 'JOB=' + $_.Id + '|' + $_.JobStatus + '|' + $_.DocumentName + '|' + $_.SubmittedTime }")
BAD_WIN = ("error", "offline", "paused", "paperjam", "paperout", "manualfeed", "paperproblem", "notavailable",
           "userintervention", "outofmemory", "dooropen", "tonerlow", "nottoner", "pendingdeletion")


def _ps(printer, script):
    env = dict(os.environ, PCL_PRN=printer)
    return _run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], env=env)


def status(printer):
    """Zustand eines Druckers als Dict: lines (Rohinfo fuer die Anzeige), problems (verstaendliche Ursachen), jobs (offene Auftraege)."""
    out = {"printer": printer, "lines": [], "problems": [], "jobs": []}
    if printer == TEST_PRINTER:
        out["lines"].append("Test printer: writes a text file, never reaches paper.")
        out["problems"].append("This is the test printer (file). Choose your real printer from the list.")
        return out
    ok, hint = system_status()
    if not ok:
        out["problems"].append(hint)
        return out
    try:
        if is_windows():
            r = _ps(printer, _PS_STATUS)
            if r.returncode:
                out["problems"].append("Windows does not know this printer: " + (r.stderr or "").strip()[:200])
                return out
            kv = {}
            for line in r.stdout.splitlines():
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k == "JOB":
                    out["jobs"].append(v.strip())
                else:
                    kv[k] = v.strip()
                out["lines"].append(line.strip())
            st = kv.get("STATUS", "").lower()
            if any(b in st for b in BAD_WIN):
                out["problems"].append(f"Windows reports the printer as '{kv.get('STATUS')}'. Switch it on, check paper/toner, "
                                       "and in Settings > Printers & scanners > Open print queue untick 'Pause printing' / 'Use printer offline'.")
            for j in out["jobs"]:
                js = j.split("|")[1].lower() if "|" in j else ""
                if any(b in js for b in ("error", "blocked", "paused", "offline", "deleting", "userintervention")):
                    out["problems"].append(f"A print job is stuck ({j.split('|')[1]}). Open the print queue in Windows, delete stuck jobs, then try again.")
                    break
            if kv.get("TYPE", "").lower() == "connection" and kv.get("COMPUTER"):
                out["lines"].append(f"Shared printer on {kv['COMPUTER']}: that computer must be on and share the printer.")
        else:
            r = _run(["lpstat", "-l", "-p", printer])
            txt = (r.stdout or "") + (r.stderr or "")
            out["lines"] += [x.rstrip() for x in txt.splitlines() if x.strip()][:12]
            low = txt.lower()
            if r.returncode or "invalid destination" in low:
                out["problems"].append("CUPS does not know this printer. Run lpstat -e and add it again (docs/drucken.md).")
                return out
            if "disabled" in low:
                out["problems"].append("CUPS has STOPPED this printer (usually after an error it could not reach the printer). "
                                       f"Fix the cause, then: sudo cupsenable '{printer}'. Reason above / in /var/log/cups/error_log.")
            v = _run(["lpstat", "-v", printer])
            uri = (v.stdout or "").strip()
            if uri:
                out["lines"].append(uri)
            o = _run(["lpoptions", "-p", printer])
            opts = o.stdout or ""
            m = re.search(r"printer-make-and-model='?([^']*)'?", opts)
            model = (m.group(1) if m else "").strip()
            if model:
                out["lines"].append("Driver: " + model)
            if "raw" in model.lower():
                out["problems"].append("The printer is set up WITHOUT a driver (raw). CUPS then sends plain text that most printers "
                                       "silently ignore. Set it up again with a driver: for a network printer "
                                       f"sudo lpadmin -p '{printer}' -E -v ipp://PRINTER-IP/ipp/print -m everywhere ; "
                                       "for a printer shared by Windows pick the model driver (lpinfo -m | grep -i YOURMODEL).")
            j = _run(["lpstat", "-o", printer])
            out["jobs"] = [x.strip() for x in (j.stdout or "").splitlines() if x.strip()][:10]
    except (OSError, subprocess.SubprocessError) as e:
        out["problems"].append(f"Could not check the printer: {e}")
    return out


def after_print_problems(printer, job_text=""):
    """Kurz nach dem Senden: (probleme, hinweise). Probleme = Drucker gestoppt/offline/ohne Treiber, Hinweise = Auftrag wartet noch."""
    if WAIT_AFTER <= 0:
        return [], []
    time.sleep(WAIT_AFTER)
    st = status(printer)
    probs, warn = list(st["problems"]), []
    if not is_windows():
        m = re.search(r"request id is (\S+)", job_text or "")
        if m and any(x.split()[0] == m.group(1) for x in st["jobs"] if x.split()):
            if not probs:
                warn.append(f"Job {m.group(1)} is still waiting in the queue after {int(WAIT_AFTER)} s. "
                             "Is the printer on and reachable from the Pi (ping its IP)? See 🩺 Check printer.")
    elif st["jobs"] and not probs:
        warn.append(f"{len(st['jobs'])} job(s) still waiting in the Windows print queue. Is the printer on and online? See 🩺 Check printer.")
    return probs, warn
