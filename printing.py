"""Drucken der Abendberichte auf einem freigegebenen Netzwerkdrucker.

Linux (Pi): CUPS mit `lpstat` (Drucker auflisten) und `lp` (drucken).
Windows (Laptop): PowerShell `Get-Printer` und `Out-Printer` (auch freigegebene Drucker wie \\\\server\\drucker,
sobald sie in Windows verbunden sind).
Entfernte Drucker (Einstellung `remote_printers`, eine Adresse je Zeile, dazu PCL_REMOTE_PRINTERS / altes PCL_CUPS_SERVER):
- IP oder Name eines Druckers bzw. ipp://-Adresse: Druck direkt per IPP (PDF, sonst JPEG je Seite, sonst Text).
- IP oder Name eines Rechners mit CUPS (z. B. der Pi): seine Drucker erscheinen als "Name @ adresse".
- E-Mail-Adresse (Epson Connect, HP ePrint, Canon …): Ausdruck als PDF-Anhang per SMTP (SMTP_* in der .env).
Windows: Druck per .NET PrintDocument (Out-Printer scheitert ohne Konsole mit "Das Handle ist ungueltig").
Dazu gibt es immer den Testdrucker TEST_PRINTER: er schreibt den Ausdruck als Textdatei nach <workspace>/.druck/,
damit sich alles ohne echten Drucker ausprobieren laesst.
"""
import os
import re
import shutil
import struct
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

TEST_PRINTER = "Test printer (file)"
TIMEOUT = 30


def is_windows():
    return os.name == "nt"


def _run(cmd, env=None, input_text=None, timeout=None):
    if not is_windows() and cmd and cmd[0] in ("lp", "lpstat", "lpoptions", "lpadmin", "lpinfo"):
        # CUPS antwortet sonst in der Sprache des Pi ("Drucker Buero ist deaktiviert"), die Pruefung sucht englische Woerter
        env = dict(env or os.environ, LC_ALL="C", LANG="C", LANGUAGE="C")
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout or TIMEOUT, env=env, input=input_text,
                          encoding="utf-8", errors="replace")


def powershell():
    """Pfad zu PowerShell. Fehlt sie im PATH (z. B. Start aus einer Verknuepfung oder venv), liegt sie trotzdem in System32."""
    for n in ("powershell", "pwsh"):
        p = shutil.which(n)
        if p:
            return p
    root = os.environ.get("SystemRoot") or os.environ.get("windir") or r"C:\Windows"
    p = os.path.join(root, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
    return p if os.path.isfile(p) else ""


def notepad():
    root = os.environ.get("SystemRoot") or os.environ.get("windir") or r"C:\Windows"
    p = os.path.join(root, "System32", "notepad.exe")
    return p if os.path.isfile(p) else "notepad.exe"


# PowerShell gibt sonst in der OEM-Codeseite aus: Druckernamen mit Umlauten kaemen verstuemmelt an und waeren nicht druckbar.
_PS_UTF8 = "[Console]::OutputEncoding = [Text.Encoding]::UTF8; $ErrorActionPreference = 'Stop'; "
_PS_LIST = (_PS_UTF8 + "try { Get-Printer | ForEach-Object { $_.Name } } catch { "
            "$e = $_.Exception.Message; try { Get-CimInstance Win32_Printer | ForEach-Object { $_.Name } } "
            "catch { [Console]::Error.WriteLine('Get-Printer: ' + $e + ' / Win32_Printer: ' + $_.Exception.Message); exit 2 } }")
# Drucken per .NET PrintDocument: braucht keine Konsole (Out-Printer meldet ohne Konsole "Das Handle ist ungueltig"),
# bricht lange Zeilen um und blaettert Seiten. Werte nur per Umgebung.
_PS_PRINT = r"""
Add-Type -AssemblyName System.Drawing
$st = @{ i = 0; lines = ([IO.File]::ReadAllText($env:PCL_PRN_FILE, [Text.Encoding]::UTF8) -split "`r?`n") }
$font = New-Object System.Drawing.Font('Consolas', 10)
$doc = New-Object System.Drawing.Printing.PrintDocument
$doc.PrinterSettings.PrinterName = $env:PCL_PRN
if (-not $doc.PrinterSettings.IsValid) { throw ('Printer not found: ' + $env:PCL_PRN) }
$doc.DocumentName = $env:PCL_PRN_TITLE
$doc.add_PrintPage({ param($sender, $e)
  $r = $e.MarginBounds; $y = [single]$r.Top
  while ($st.i -lt $st.lines.Count) {
    $line = $st.lines[$st.i]; if ($line -eq '') { $line = ' ' }
    $h = $e.Graphics.MeasureString($line, $font, $r.Width).Height
    if (($y + $h) -gt $r.Bottom -and $y -gt $r.Top) { $e.HasMorePages = $true; return }
    $e.Graphics.DrawString($line, $font, [System.Drawing.Brushes]::Black,
      (New-Object System.Drawing.RectangleF([single]$r.Left, $y, [single]$r.Width, $h)))
    $y += $h; $st.i++
  }
  $e.HasMorePages = $false
})
$doc.Print()
$doc.Dispose()
'OK'
"""
# Virtuelle Drucker, die jedes Windows hat: stehen nur sie in der Liste, ist kein echter Drucker verbunden.
VIRTUAL_WIN = ("microsoft print to pdf", "microsoft xps document writer", "onenote", "fax", "send to onenote",
               "an onenote senden", "pdf24", "adobe pdf")


WIN_TIMEOUT = float(os.environ.get("PCL_PRINT_WIN_TIMEOUT", "120"))  # PowerShell startet auf langsamen Laptops oft >30 s


def win_enum_printers():
    """Drucker direkt aus der Windows-Druckwarteschlange (winspool.drv, EnumPrintersW), ohne PowerShell.
    Gibt (namen, standarddrucker, fehler) zurueck. Lokale UND verbundene Drucker (\\\\server\\drucker)."""
    import ctypes
    from ctypes import wintypes
    try:
        ws = ctypes.WinDLL("winspool.drv", use_last_error=True)
    except (OSError, AttributeError) as e:
        return [], "", f"winspool.drv not available: {e}"

    class PI4(ctypes.Structure):
        _fields_ = [("pPrinterName", wintypes.LPWSTR), ("pServerName", wintypes.LPWSTR), ("Attributes", wintypes.DWORD)]
    flags = 0x2 | 0x4  # PRINTER_ENUM_LOCAL | PRINTER_ENUM_CONNECTIONS
    need, ret = wintypes.DWORD(0), wintypes.DWORD(0)
    ws.EnumPrintersW(flags, None, 4, None, 0, ctypes.byref(need), ctypes.byref(ret))
    if not need.value:
        err = ctypes.get_last_error()
        return [], "", ("" if err in (0, 122) else f"EnumPrinters error {err} ({ctypes.FormatError(err).strip()})")
    buf = ctypes.create_string_buffer(need.value)
    if not ws.EnumPrintersW(flags, None, 4, buf, need, ctypes.byref(need), ctypes.byref(ret)):
        err = ctypes.get_last_error()
        return [], "", f"EnumPrinters error {err} ({ctypes.FormatError(err).strip()})"
    arr = ctypes.cast(buf, ctypes.POINTER(PI4))
    names = [arr[i].pPrinterName for i in range(ret.value) if arr[i].pPrinterName]
    default = ""
    try:
        n = wintypes.DWORD(0)
        ws.GetDefaultPrinterW(None, ctypes.byref(n))
        if n.value:
            b = ctypes.create_unicode_buffer(n.value)
            if ws.GetDefaultPrinterW(b, ctypes.byref(n)):
                default = b.value
    except (OSError, AttributeError):
        pass
    return names, default, ""


def system_status():
    """(bereit, Hinweis) - ob das Betriebssystem ueberhaupt drucken kann."""
    if is_windows():
        return True, "Windows printers (winspool)."
    if shutil.which("lp") and shutil.which("lpstat"):
        return True, "CUPS is installed."
    return False, "CUPS missing. On Linux: sudo apt install cups-client (or ./install.sh --print)."


def _cups_queues():
    """Richtig eingerichtete CUPS-Warteschlangen (lpstat -a). Nur die kann CUPS sicher bedienen."""
    r = _run(["lpstat", "-a"])
    return [x.split()[0] for x in r.stdout.splitlines() if x.strip()], r


def network_only(printer):
    """True, wenn CUPS den Drucker nur im Netzwerk gesehen hat (lpstat -e), er aber nicht als Drucker eingerichtet ist."""
    if is_windows() or printer == TEST_PRINTER or " @ " in printer:
        return False
    try:
        queues, _ = _cups_queues()
        if printer in queues:
            return False
        return printer in [x.strip() for x in _run(["lpstat", "-e"]).stdout.splitlines()]
    except (OSError, subprocess.SubprocessError):
        return False


def list_details(remotes=""):
    """(Liste von {name, kind}, Fehlertext). kind: queue | network (nur gefunden) | windows | remote | test."""
    items, errs = [], []
    ok, hint = system_status()
    if not ok:
        errs.append(hint)
    else:
        try:
            if is_windows():
                names, default, werr = win_enum_printers()
                if not names:  # Rueckfall PowerShell (Get-Printer, dann Win32_Printer)
                    r = _ps("", _PS_LIST) if powershell() else None
                    names = [x.strip() for x in (r.stdout if r else "").splitlines() if x.strip()]
                    if not names:
                        werr = " / ".join(x for x in (werr, ((r.stderr or r.stdout or "").strip()[:300] if r and r.returncode else "")) if x)
                if default in names:  # Standarddrucker von Windows zuerst
                    names = [default] + [n for n in names if n != default]
                items += [{"name": n, "kind": "windows", "default": n == default} for n in names]
                r = subprocess.CompletedProcess([], 1 if werr else 0, "", werr)
                if r.returncode and not names:
                    errs.append("Windows could not list the printers: " + ((r.stderr or r.stdout or "").strip()[:300]
                                or f"code {r.returncode}") + " Is the service 'Print Spooler' running (services.msc)?")
                elif not names:
                    errs.append("Windows has no printer installed.")
                elif all(any(v in n.lower() for v in VIRTUAL_WIN) for n in names):
                    errs.append("Windows only has virtual printers (PDF, OneNote …), no real printer is connected.")
                if errs and not parse_remotes(remotes):
                    errs.append("Add the printer in Windows under Settings › Printers & scanners, or enter it below as a "
                                "remote printer (IP address, network name or e-mail address of the printer).")
            else:
                queues, r = _cups_queues()
                found = [x.strip() for x in _run(["lpstat", "-e"]).stdout.splitlines() if x.strip()]
                items += [{"name": n, "kind": "queue"} for n in queues]
                items += [{"name": n, "kind": "network"} for n in found if n not in queues]
                if not items:
                    errs.append(((r.stderr or "").strip()[:200] + " ") if r.returncode else "")
                    errs[-1] += "No printer set up. Add a network printer in CUPS (see docs/drucken.md)."
        except (OSError, subprocess.SubprocessError) as e:
            errs.append(f"Could not read the printers: {e}")
    r_items, r_err = remote_items(remotes)
    items += r_items
    if r_err:
        errs.append(r_err)
    items.append({"name": TEST_PRINTER, "kind": "test"})
    return items, " ".join(e.strip() for e in errs if e.strip())


def list_printers(remotes=""):
    """(Liste der Druckernamen, Fehlertext oder ''). Der Testdrucker steht immer am Ende."""
    items, err = list_details(remotes)
    return [i["name"] for i in items], err


def valid_name(name):
    """Druckername nur aus der Liste, ohne Steuerzeichen (er geht an lp bzw. PowerShell)."""
    return bool(name) and len(name) <= 200 and not re.search(r"[\x00-\x1f]", name)


def print_text(printer, title, text, out_dir, remotes=""):
    """Druckt Text. Gibt (ok, Meldung) zurueck. out_dir: Ablage fuer den Testdrucker. remotes: entfernte Drucker (siehe oben)."""
    if not valid_name(printer):
        return False, "Invalid printer name."
    target = resolve(printer, remotes)
    if target:
        return remote_print(target, title, text, remotes)
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
            env = dict(os.environ, PCL_PRN=printer, PCL_PRN_FILE=tmp.name,  # Werte per Umgebung, nie in den Befehl
                       PCL_PRN_TITLE=(title or "Evening report")[:100])
            r = None
            if powershell():  # 1. Out-Printer (bewaehrt), 2. PrintDocument (geht auch ohne Konsole), 3. Notepad
                r = _run([powershell(), "-NoProfile", "-NonInteractive", "-Command", _PS_UTF8 +
                          "Get-Content -Raw -Encoding UTF8 -LiteralPath $env:PCL_PRN_FILE | Out-Printer -Name $env:PCL_PRN"],
                         env=env, timeout=WIN_TIMEOUT)
                if r.returncode:
                    r2 = _run([powershell(), "-NoProfile", "-NonInteractive", "-Command", _PS_UTF8 + _PS_PRINT],
                              env=env, timeout=WIN_TIMEOUT)
                    r = r2 if not r2.returncode else r
            if r is None or r.returncode:  # ohne PowerShell oder bei Fehler: Notepad druckt die Textdatei (/pt)
                first = r
                r = _run([notepad(), "/pt", tmp.name, printer], timeout=WIN_TIMEOUT)
                if r.returncode and first is not None:
                    r = first
        else:
            r = _run(["lp", "-d", printer, "-t", (title or "Evening report")[:100], "--", tmp.name])
        if r.returncode:
            err = (r.stderr or r.stdout or "").strip()[:300] or f"Code {r.returncode}"
            if not is_windows() and network_only(printer):
                return False, (f"'{printer}' was only found on the network, it is not set up as a printer in CUPS, "
                               "so CUPS cannot print on it (" + err + "). Click 🔧 Set up printer once, then print again.")
            return False, "Printer reports an error: " + err
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
    return _run([powershell(), "-NoProfile", "-NonInteractive", "-Command", _PS_UTF8 + script], env=env, timeout=WIN_TIMEOUT)


def status(printer, remotes=""):
    """Zustand eines Druckers als Dict: lines (Rohinfo fuer die Anzeige), problems (verstaendliche Ursachen), jobs (offene Auftraege)."""
    out = {"printer": printer, "lines": [], "problems": [], "jobs": [], "setup": False}
    target = resolve(printer, remotes)
    if target:
        return remote_status(target, out)
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
            if not powershell():
                names, _, _ = win_enum_printers()
                out["lines"].append("Detailed check needs Windows PowerShell (not found).")
                if printer not in names:
                    out["problems"].append("Windows does not know this printer (any more). ↻ Search again.")
                return out
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
                if network_only(printer):
                    uri = discovered_uri(printer)
                    out["setup"] = True
                    out["lines"].append("Found on the network: " + (uri or "(address unknown)"))
                    out["problems"].append(
                        "CUPS has only SEEN this printer on the network, it is not set up as a printer. That is why the "
                        "test page does not come out. Click 🔧 Set up printer (or in a terminal: sudo lpadmin -p '"
                        f"{printer}' -E -v '{uri or 'ipp://PRINTER-IP/ipp/print'}' -m everywhere -o printer-is-shared=true).")
                else:
                    out["problems"].append("CUPS does not know this printer. Run lpstat -e and add it again (docs/drucken.md).")
                return out
            if "disabled" in low and "cups-browsed" in low:
                host = printer.split("@", 1)[1] if "@" in printer else "PRINTER-IP"
                out["problems"].append(
                    "This printer was set up automatically by cups-browsed, which no longer supplies its address, so CUPS "
                    "stopped it (cupsenable alone does not help). Set it up once with a fixed address: "
                    f"sudo lpadmin -p MyPrinter -E -v ipp://{host}/ipp/print -m everywhere -o printer-is-shared=true "
                    f"(better the printer's IP: ping {host}), then choose “MyPrinter” here. "
                    f"Afterwards the old entry can go: sudo lpadmin -x '{printer}'")
            elif "disabled" in low and ("unable to locate" in low or "resolve" in low):
                out["problems"].append(
                    "The printer's network name (….local) could not be resolved, so CUPS stopped it. Set it up once with "
                    "the printer's IP address (router or printer display): sudo lpadmin -p Drucker -E -v "
                    "ipp://PRINTER-IP/ipp/print -m everywhere ; then choose “Drucker” here. If the name should work: "
                    "sudo apt install avahi-daemon libnss-mdns")
            if "disabled" in low and "filter failed" in low:
                out["problems"].append("A conversion filter failed. Set the printer up driverless again: "
                                       "sudo lpadmin -p NAME -E -v ipp://PRINTER-IP/ipp/print -m everywhere")
            if "disabled" in low and "cups-browsed" not in low:
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


def after_print_problems(printer, job_text="", remotes=""):
    """Kurz nach dem Senden: (probleme, hinweise). Probleme = Drucker gestoppt/offline/ohne Treiber, Hinweise = Auftrag wartet noch."""
    if WAIT_AFTER <= 0:
        return [], []
    time.sleep(WAIT_AFTER)
    st = status(printer, remotes)
    probs, warn = list(st["problems"]), []
    if resolve(printer, remotes):
        if st["jobs"] and not probs:
            warn.append(f"{st['jobs'][0]}. Is the printer on and has paper? See 🩺 Check printer.")
    elif not is_windows():
        m = re.search(r"request id is (\S+)", job_text or "")
        if m and any(x.split()[0] == m.group(1) for x in st["jobs"] if x.split()):
            if not probs:
                warn.append(f"Job {m.group(1)} is still waiting in the queue after {int(WAIT_AFTER)} s. "
                             "Is the printer on and reachable from this computer (ping its IP)? See 🩺 Check printer.")
    elif st["jobs"] and not probs:
        warn.append(f"{len(st['jobs'])} job(s) still waiting in the Windows print queue. Is the printer on and online? See 🩺 Check printer.")
    return probs, warn


# ---------------------------------------------------------------- Drucker auf dem Pi einrichten (aus "nur gefunden")
def discovered_uri(printer):
    """Adresse eines nur gefundenen Druckers: lpoptions kennt die device-uri, sonst lpinfo (dnssd/ipp) nach Namen."""
    try:
        o = _run(["lpoptions", "-p", printer]).stdout or ""
        m = re.search(r"device-uri=(\S+)", o)
        if m:
            return m.group(1).strip("'\"")
        key = re.sub(r"[^a-z0-9]", "", printer.lower())
        for line in _run(["lpinfo", "--include-schemes", "dnssd,ipp,ipps", "-v"]).stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                uri = parts[1]
                label = urllib.request.unquote(uri.split("://", 1)[-1].split("._", 1)[0].split("/", 1)[0])
                if key and re.sub(r"[^a-z0-9]", "", label.lower()) == key:
                    return uri
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def setup_printer(printer):
    """Richtet einen nur gefundenen Netzwerkdrucker als feste CUPS-Warteschlange ein (treiberlos, IPP Everywhere),
    freigegeben, damit auch der Laptop ueber den Pi drucken kann. (ok, Meldung)."""
    if is_windows():
        return False, "Only on Linux (CUPS). On Windows add the printer under Settings › Printers & scanners."
    if not valid_name(printer) or not re.fullmatch(r"[A-Za-z0-9_.\-]{1,127}", printer):
        return False, "This printer name cannot be used as a CUPS name."
    if not shutil.which("lpadmin"):
        return False, "lpadmin missing. Run: ./install.sh --print"
    uri = discovered_uri(printer)
    if not uri:
        return False, ("The printer's network address was not found. Look it up with: lpinfo --include-schemes dnssd,ipp -v "
                       f"and then: sudo lpadmin -p '{printer}' -E -v ADDRESS -m everywhere -o printer-is-shared=true")
    cmd = ["lpadmin", "-p", printer, "-E", "-v", uri, "-m", "everywhere", "-o", "printer-is-shared=true"]
    try:
        r = _run(cmd)
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"lpadmin failed: {e}"
    if r.returncode:
        err = (r.stderr or r.stdout or "").strip()[:300]
        hint = ""
        if "forbidden" in err.lower() or "not authorized" in err.lower() or "unauthorized" in err.lower():
            hint = " Hyperstead's user may not change printers. Run it once yourself in a terminal:"
        else:
            hint = " If the printer does not support driverless printing, pick a model driver (docs/drucken.md). Command:"
        return False, f"Could not set up the printer: {err}.{hint} sudo " + " ".join(
            f"'{c}'" if (" " in c or c == printer) else c for c in cmd)
    return True, f"'{printer}' is now set up in CUPS ({uri}). Print the test page again."


# ---------------------------------------------------------------- Entfernte Drucker: IPP direkt, CUPS-Rechner, E-Mail
IPP_TIMEOUT = float(os.environ.get("PCL_IPP_TIMEOUT", "5"))
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # Drucker stehen meist im Heimnetz: nie ueber einen Proxy
_REQ_ID = [0]
_DIRECT = {}  # Adresse -> gefundener IPP-Pfad eines Druckers (/ipp/print …)
MAX_REMOTES = 20
_HOST = r"(?:[A-Za-z0-9._\-]+|\[[0-9A-Fa-f:]+\])(?::\d{1,5})?"
_MAIL = r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"
DIRECT_PATHS = ("/ipp/print", "/ipp", "/ipp/printer", "/printers/ipp", "/")
REASONS = {"media-empty": "out of paper", "media-needed": "out of paper", "media-jam": "paper jam",
           "marker-supply-empty": "ink or toner empty", "toner-empty": "toner empty", "door-open": "a cover is open",
           "cover-open": "a cover is open", "offline": "offline", "paused": "paused", "input-tray-missing": "paper tray missing"}


def valid_server(server):
    return bool(server) and len(server) <= 120 and bool(re.fullmatch(_HOST, server))


def parse_remote(addr):
    """Eine Adresse -> {addr, kind: mail|host|url, base, path} oder None. host = Rechner mit CUPS ODER Drucker (wird geprueft)."""
    a = (addr or "").strip()
    if not a or len(a) > 300 or re.search(r"[\s\x00-\x1f]", a):
        return None
    if re.fullmatch(_MAIL, a):
        return {"addr": a, "kind": "mail"}
    scheme, path = "ipp", ""
    rest = a
    if "://" in a:
        scheme, rest = a.split("://", 1)
        scheme = scheme.lower()
        if scheme not in ("ipp", "ipps", "http", "https"):
            return None
        rest, sep, p = rest.partition("/")
        path = (sep + p) if sep else ""
        path = urllib.request.quote(urllib.request.unquote(path), safe="/-_.~")
    if not re.fullmatch(_HOST, rest):
        return None
    tls = scheme in ("ipps", "https")
    hostport = rest if re.search(r":\d+$", rest) and not rest.endswith("]") else rest + (":443" if scheme == "https" else ":631")
    return {"addr": a, "kind": "url" if path not in ("", "/") else "host", "base": ("https://" if tls else "http://") + hostport,
            "path": path if path not in ("", "/") else ""}


def parse_remotes(remotes):
    """Text (je Zeile/Komma eine Adresse) oder Liste -> gueltige Eintraege, ohne Doppelte."""
    if isinstance(remotes, str):
        remotes = re.split(r"[\n,;]+", remotes)
    out, seen = [], set()
    for x in remotes or []:
        e = parse_remote(x)
        if e and e["addr"].lower() not in seen:
            seen.add(e["addr"].lower())
            out.append(e)
    return out[:MAX_REMOTES]


def invalid_remotes(text):
    return [x.strip() for x in re.split(r"[\n,;]+", text or "") if x.strip() and not parse_remote(x)]


def resolve(printer, remotes=""):
    """Druckername -> Ziel {type: ipp|cups|mail, entry, queue} oder None (lokaler Drucker)."""
    if not printer or not remotes:
        return None
    entries = parse_remotes(remotes)
    for e in entries:
        if printer == e["addr"]:
            return {"type": "mail" if e["kind"] == "mail" else "ipp", "entry": e}
    if " @ " in printer:
        q, a = printer.rsplit(" @ ", 1)
        for e in entries:
            if e["addr"] == a and e["kind"] == "host":
                return {"type": "cups", "entry": e, "queue": q}
    return None


def remote_split(printer, server=""):
    """Alte Schnittstelle: 'Buero @ host' -> ('Buero', 'host')."""
    t = resolve(printer, server)
    return (t["queue"], t["entry"]["addr"]) if t and t["type"] == "cups" else (printer, "")


def _attr(tag, name, value):
    v = struct.pack(">i", value) if isinstance(value, int) else value.encode("utf-8")
    n = name.encode("utf-8")
    return struct.pack(">BH", tag, len(n)) + n + struct.pack(">H", len(v)) + v


def _ipp(base, path, op, attrs, data=b""):
    """Eine IPP-Anfrage. Gibt (status, gruppen) zurueck; gruppen = Liste (tag, {name: [werte]})."""
    _REQ_ID[0] += 1
    path = path or "/"
    body = struct.pack(">BBHi", 2, 0, op, _REQ_ID[0]) + b"\x01"
    body += _attr(0x47, "attributes-charset", "utf-8") + _attr(0x48, "attributes-natural-language", "en")
    body += _attr(0x45, "printer-uri", ("ipps://" if base.startswith("https") else "ipp://") + base.split("://", 1)[1] + path)
    for tag, name, value in attrs:
        vals = value if isinstance(value, (list, tuple)) else [value]
        for i, v in enumerate(vals):
            body += _attr(tag, name if i == 0 else "", v)
    body += b"\x03" + data
    req = urllib.request.Request(base + path, data=body, method="POST", headers={"Content-Type": "application/ipp"})
    with _OPENER.open(req, timeout=IPP_TIMEOUT if not data else max(IPP_TIMEOUT, 60)) as r:
        raw = r.read()
    return _parse(raw)


def _parse(raw):
    if len(raw) < 8:
        raise ValueError("short IPP answer")
    st = struct.unpack(">H", raw[2:4])[0]
    i, groups, last = 8, [], None
    while i < len(raw):
        tag = raw[i]
        i += 1
        if tag == 0x03:
            break
        if tag < 0x10:
            groups.append((tag, {}))
            continue
        nl = struct.unpack(">H", raw[i:i + 2])[0]
        name = raw[i + 2:i + 2 + nl].decode("utf-8", "replace")
        i += 2 + nl
        vl = struct.unpack(">H", raw[i:i + 2])[0]
        v = raw[i + 2:i + 2 + vl]
        i += 2 + vl
        val = struct.unpack(">i", v)[0] if tag in (0x21, 0x23) and vl == 4 else (
            bool(v[0]) if tag == 0x22 and vl == 1 else v.decode("utf-8", "replace"))
        if not groups:
            groups.append((0x01, {}))
        if name:
            last = name
        if last:
            groups[-1][1].setdefault(last, []).append(val)
    return st, groups


def _group(groups, tag=0x04):
    a = {}
    for t, g in groups:
        if t == tag:
            a.update(g)
    return a


def _ipp_error(addr, e):
    msg = str(getattr(e, "reason", "") or e)
    if isinstance(e, urllib.error.HTTPError) and e.code in (401, 403):
        return (f"{addr} refuses access from this computer (HTTP {e.code}). If it is a computer with CUPS, run there once: "
                "sudo cupsctl --remote-any --share-printers")
    if "certificate" in msg.lower():
        return f"{addr}: the printer's certificate is not trusted ({msg}). Use ipp:// instead of ipps://."
    return (f"Cannot reach {addr} ({msg}). Is the printer on and in the same network or reachable from the internet, "
            "and is the address right (try the IP)?")


_PRN_ATTRS = ["printer-name", "printer-state", "printer-state-message", "printer-state-reasons", "printer-is-accepting-jobs",
              "queued-job-count", "printer-make-and-model", "document-format-supported", "printer-info"]


def _printer_attrs(base, path):
    st, groups = _ipp(base, path, 0x000B, [(0x44, "requested-attributes", _PRN_ATTRS)])
    if st >= 0x0400:
        raise ValueError(f"IPP status 0x{st:04x}")
    return _group(groups)


def _direct_path(e):
    """IPP-Pfad eines Druckers suchen (gemerkt). Gibt (pfad, attribute) zurueck oder wirft den letzten Fehler."""
    if e["kind"] == "url":
        return e["path"], _printer_attrs(e["base"], e["path"])
    paths = ([_DIRECT[e["addr"]]] if e["addr"] in _DIRECT else []) + [p for p in DIRECT_PATHS if p != _DIRECT.get(e["addr"])]
    last = None
    for p in paths:
        try:
            a = _printer_attrs(e["base"], p)
            _DIRECT[e["addr"]] = p
            return p, a
        except urllib.error.HTTPError as err:
            last = err
            if err.code in (401, 403):
                raise
        except (OSError, ValueError, urllib.error.URLError) as err:
            last = err
            if not isinstance(err, (ValueError, urllib.error.HTTPError)):
                break  # nicht erreichbar: weitere Pfade bringen nichts
    raise last or ValueError("no IPP printer found")


def _remote_queues(e):
    """Drucker eines CUPS-Rechners (CUPS-Get-Printers). Leere Liste = kein CUPS-Rechner."""
    st, groups = _ipp(e["base"], "/", 0x4002, [(0x44, "requested-attributes", ["printer-name"])])
    if st >= 0x0400:
        return []
    return [g["printer-name"][0] for t, g in groups if t == 0x04 and g.get("printer-name")]


def remote_printers(server):
    """Alte Schnittstelle: Drucker eines CUPS-Rechners. (namen, fehler)."""
    e = parse_remote(server)
    if not e or e["kind"] != "host":
        return [], "Invalid address. Example: printer.local or 192.168.1.20"
    try:
        names = _remote_queues(e)
    except (OSError, ValueError, urllib.error.URLError) as err:
        return [], _ipp_error(server, err)
    return names, "" if names else f"{server} has no printer set up."


def remote_items(remotes):
    """Eintraege fuer die Druckerliste aus den entfernten Adressen. (items, fehler)."""
    items, errs = [], []
    for e in parse_remotes(remotes):
        a = e["addr"]
        if e["kind"] == "mail":
            items.append({"name": a, "kind": "mail", "label": f"{a} (e-mail printer)"})
            if not smtp_config()[0]:
                errs.append(f"{a}: printing by e-mail needs SMTP_HOST, SMTP_USER, SMTP_PASSWORD in the .env.")
            continue
        try:
            queues = _remote_queues(e) if e["kind"] == "host" else []
        except urllib.error.HTTPError as err:
            if err.code in (401, 403):
                errs.append(_ipp_error(a, err))
                items.append({"name": a, "kind": "remote", "label": f"{a} (remote printer)"})
                continue
            queues = []
        except (OSError, ValueError, urllib.error.URLError) as err:
            errs.append(_ipp_error(a, err))
            items.append({"name": a, "kind": "remote", "label": f"{a} (remote printer, not reachable)"})
            continue
        if queues:
            items += [{"name": f"{q} @ {a}", "kind": "remote", "label": f"{q} @ {a} (remote printer)"} for q in queues]
            continue
        try:
            _, attrs = _direct_path(e)
            model = (attrs.get("printer-make-and-model") or attrs.get("printer-info") or [""])[0]
            items.append({"name": a, "kind": "remote", "label": f"{a} ({model or 'remote printer'})"})
        except (OSError, ValueError, urllib.error.URLError) as err:
            errs.append(_ipp_error(a, err))
            items.append({"name": a, "kind": "remote", "label": f"{a} (remote printer, not reachable)"})
    return items, " ".join(errs)


# ---------------------------------------------------------------- Text als PDF / JPEG (fuer Drucker ohne Treiber und E-Mail)
_MONO = ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"]
_WIN = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
_MONO += [os.path.join(_WIN, f) for f in ("consola.ttf", "cour.ttf", "lucon.ttf")]


def _mono_font():
    return next((f for f in _MONO if os.path.isfile(f)), "")


def _wrap(text, width):
    out = []
    for line in text.replace("\t", "    ").splitlines() or [""]:
        while len(line) > width:
            cut = line.rfind(" ", 0, width)
            cut = cut if cut > width // 2 else width
            out.append(line[:cut])
            line = line[cut:].lstrip()
        out.append(line)
    return out


def text_pdf(title, text):
    """Text -> PDF (A4, Schrift mit Umlauten und Tuerkisch, wenn vorhanden)."""
    import io
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    font, size = "Courier", 10
    f = _mono_font()
    if f:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        if "PclMono" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("PclMono", f))
        font = "PclMono"
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(title or "Hyperstead")
    w, h = A4
    margin, lh = 50, size * 1.35
    y = h - margin
    for line in _wrap(text, 88):
        if y < margin:
            c.showPage()
            y = h - margin
        c.setFont(font, size)
        c.drawString(margin, y, line if font != "Courier" else line.encode("latin-1", "replace").decode("latin-1"))
        y -= lh
    c.save()
    return buf.getvalue()


def text_jpegs(text, dpi=150):
    """Text -> JPEG je A4-Seite (fuer Drucker, die kein PDF koennen)."""
    import io
    from PIL import Image, ImageDraw, ImageFont
    W, H = int(8.27 * dpi), int(11.69 * dpi)
    f = _mono_font()
    font = ImageFont.truetype(f, int(dpi * 10 / 72)) if f else ImageFont.load_default()
    lh, margin = int(dpi * 10 / 72 * 1.35), int(dpi * 0.7)
    lines, pages = _wrap(text, 88), []
    per = max(1, (H - 2 * margin) // lh)
    for i in range(0, len(lines), per):
        img = Image.new("RGB", (W, H), "white")
        d = ImageDraw.Draw(img)
        for n, line in enumerate(lines[i:i + per]):
            d.text((margin, margin + n * lh), line, fill="black", font=font)
        b = io.BytesIO()
        img.save(b, "JPEG", quality=85)
        pages.append(b.getvalue())
    return pages


# ---------------------------------------------------------------- Drucken auf entfernten Druckern
def _target_ipp(t):
    """(base, pfad, attribute) fuer IPP-Ziele."""
    e = t["entry"]
    if t["type"] == "cups":
        path = "/printers/" + urllib.request.quote(t["queue"], safe="")
        return e["base"], path, _printer_attrs(e["base"], path)
    path, attrs = _direct_path(e)
    return e["base"], path, attrs


def remote_print(t, title, text, remotes=""):
    if t["type"] == "mail":
        return mail_print(t["entry"]["addr"], title, text)
    label = t.get("queue", "") + (" @ " if t.get("queue") else "") + t["entry"]["addr"]
    try:
        base, path, attrs = _target_ipp(t)
    except (OSError, ValueError, urllib.error.URLError) as e:
        return False, _ipp_error(t["entry"]["addr"], e)
    fmts = [f.lower() for f in attrs.get("document-format-supported", [])]
    try:
        if not fmts or "application/pdf" in fmts:
            docs, fmt = [text_pdf(title, text)], "application/pdf"
        elif "image/jpeg" in fmts:
            docs, fmt = text_jpegs(text), "image/jpeg"
        elif "text/plain" in fmts:
            docs, fmt = [text.encode("utf-8")], "text/plain"
        else:
            return False, (f"{label} only accepts {', '.join(fmts[:6])}. Hyperstead can send PDF, JPEG or text. "
                           "Add this printer in Windows (with its driver) or print via a computer with CUPS.")
    except Exception as e:  # noqa: BLE001 - PDF/Bild-Erzeugung (reportlab/Pillow fehlt o. ae.)
        return False, f"Could not prepare the printout: {e}"
    jobs = []
    for i, doc in enumerate(docs):
        try:
            st, groups = _ipp(base, path, 0x0002, [
                (0x42, "requesting-user-name", "hyperstead"),
                (0x42, "job-name", ((title or "Evening report") + (f" ({i + 1}/{len(docs)})" if len(docs) > 1 else ""))[:100]),
                (0x49, "document-format", fmt),
            ], data=doc)
        except (OSError, ValueError, urllib.error.URLError) as e:
            return False, _ipp_error(t["entry"]["addr"], e)
        if st >= 0x0400:
            msg = " ".join(str(v) for _, g in groups for v in g.get("status-message", []))
            hint = (" The printer is not shared on that computer: there run sudo lpadmin -p '" + t["queue"] +
                    "' -o printer-is-shared=true") if "not shared" in msg.lower() and t.get("queue") else ""
            return False, f"{label} refused the job (0x{st:04x} {msg}).{hint}"
        jobs += [str(g["job-id"][0]) for _, g in groups if g.get("job-id")]
    msg = f"Sent to {label} ({fmt.split('/')[1].upper()})." + (f" Job {', '.join(jobs)}." if jobs else "")
    probs, warn = after_print_problems(label if t["type"] == "cups" else t["entry"]["addr"], "", remotes)
    if probs:
        return False, "The printer accepted the job but is not printing: " + " ".join(probs)
    return True, msg + ("" if not warn else " Note: " + " ".join(warn))


def remote_status(t, out):
    a = t["entry"]["addr"]
    if t["type"] == "mail":
        ok, why = smtp_config()
        out["lines"] += [f"E-mail printer: {a}", "Hyperstead sends the printout as a PDF attachment."]
        if ok:
            out["lines"].append(f"SMTP: {why}")
        else:
            out["problems"].append("Printing by e-mail needs SMTP_HOST, SMTP_USER and SMTP_PASSWORD (and SMTP_FROM) in the .env.")
        out["lines"].append("The sender address must be allowed in the printer's cloud service (e.g. Epson Connect: "
                            "Approved Senders List), otherwise the mail is ignored.")
        return out
    try:
        base, path, attrs = _target_ipp(t)
    except (OSError, ValueError, urllib.error.URLError) as e:
        out["problems"].append(_ipp_error(a, e))
        return out
    state = (attrs.get("printer-state") or [0])[0]
    reasons = [r for r in attrs.get("printer-state-reasons", []) if r != "none"]
    out["lines"] += [f"Address: {('ipps://' if base.startswith('https') else 'ipp://') + base.split('://', 1)[1] + path}",
                     f"State: {({3: 'idle', 4: 'printing', 5: 'stopped'}).get(state, state)}"]
    for k, label in (("printer-state-message", "Message"), ("printer-make-and-model", "Model / driver")):
        if (attrs.get(k) or [""])[0]:
            out["lines"].append(f"{label}: {attrs[k][0]}")
    if reasons:
        out["lines"].append("Reasons: " + ", ".join(reasons))
    if attrs.get("document-format-supported"):
        out["lines"].append("Formats: " + ", ".join(attrs["document-format-supported"][:8]))
    bad = [r for r in reasons if r.endswith("-error") or r in REASONS]
    if bad:
        out["problems"].append("The printer reports: " + ", ".join(REASONS.get(re.sub(r"-(error|warning|report)$", "", r), r)
                                                                    for r in bad) + ".")
    if state == 5:
        out["problems"].append("The printer is STOPPED." + (f" On the computer with CUPS run: sudo cupsenable '{t['queue']}'"
                                                             if t["type"] == "cups" else " Switch it off and on again."))
    if attrs.get("printer-is-accepting-jobs") == [False]:
        out["problems"].append("The printer does not accept jobs." + (f" There run: sudo cupsaccept '{t['queue']}'"
                                                                       if t["type"] == "cups" else ""))
    if "raw" in (attrs.get("printer-make-and-model") or [""])[0].lower():
        out["problems"].append("The printer is set up WITHOUT a driver (raw), text is silently dropped. "
                               "Set it up again with -m everywhere (docs/drucken.md).")
    n = (attrs.get("queued-job-count") or [0])[0]
    if n:
        out["jobs"] = [f"{n} job(s) waiting at the printer"]
    return out


# ---------------------------------------------------------------- Drucken per E-Mail (Epson Connect, HP ePrint …)
def smtp_config():
    """(bereit, beschreibung). Werte aus der Umgebung (.env): SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM."""
    host = os.environ.get("SMTP_HOST", "").strip()
    user = os.environ.get("SMTP_USER", "").strip()
    if not host or not (user or os.environ.get("SMTP_FROM")):
        return False, ""
    return True, f"{host}:{os.environ.get('SMTP_PORT', '587')} as {os.environ.get('SMTP_FROM') or user}"


def mail_print(to, title, text):
    import smtplib
    import ssl
    from email.message import EmailMessage
    ok, _ = smtp_config()
    if not ok:
        return False, "Printing by e-mail needs SMTP_HOST, SMTP_USER and SMTP_PASSWORD (and SMTP_FROM) in the .env."
    try:
        pdf = text_pdf(title, text)
    except Exception as e:  # noqa: BLE001
        return False, f"Could not prepare the PDF: {e}"
    host = os.environ["SMTP_HOST"].strip()
    port = int(os.environ.get("SMTP_PORT", "587") or 587)
    user, pw = os.environ.get("SMTP_USER", "").strip(), os.environ.get("SMTP_PASSWORD", "")
    msg = EmailMessage()
    msg["From"] = os.environ.get("SMTP_FROM", "").strip() or user
    msg["To"] = to
    msg["Subject"] = (title or "Hyperstead printout")[:120]
    msg.set_content("Printout from Hyperstead (PDF attached).")
    fname = re.sub(r"[^A-Za-z0-9_.-]+", "-", (title or "printout"))[:60].strip("-") or "printout"
    msg.add_attachment(pdf, maintype="application", subtype="pdf", filename=fname + ".pdf")
    try:
        ctx = ssl.create_default_context()
        if port == 465:
            s = smtplib.SMTP_SSL(host, port, timeout=30, context=ctx)
        else:
            s = smtplib.SMTP(host, port, timeout=30)
            if os.environ.get("SMTP_STARTTLS", "1") != "0":
                s.starttls(context=ctx)
        with s:
            if user:
                s.login(user, pw)
            s.send_message(msg)
    except (OSError, smtplib.SMTPException) as e:
        return False, f"E-mail to the printer failed: {e}"
    return True, (f"Sent as PDF by e-mail to {to}. The printer's cloud service prints it in a minute or two "
                  "(only if your sender address is allowed there).")
