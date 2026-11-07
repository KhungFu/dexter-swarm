"""Drucken der Abendberichte auf einem freigegebenen Netzwerkdrucker.

Linux (Pi): CUPS mit `lpstat` (Drucker auflisten) und `lp` (drucken).
Windows (Laptop): PowerShell `Get-Printer` und `Out-Printer` (auch freigegebene Drucker wie \\\\server\\drucker,
sobald sie in Windows verbunden sind).
Pi-Drucker vom Laptop aus: Ist `cups_server` gesetzt (Einstellung oder PCL_CUPS_SERVER, z. B. "dexter.local"), fragt
Hyperstead das CUPS des Pi direkt per IPP ab und druckt dorthin ("Name @ dexter.local"). Windows braucht dafuer keinen Treiber,
CUPS auf dem Pi wandelt den Text um.
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


def _run(cmd, env=None, input_text=None):
    if not is_windows() and cmd and cmd[0] in ("lp", "lpstat", "lpoptions", "lpadmin", "lpinfo"):
        # CUPS antwortet sonst in der Sprache des Pi ("Drucker Buero ist deaktiviert"), die Pruefung sucht englische Woerter
        env = dict(env or os.environ, LC_ALL="C", LANG="C", LANGUAGE="C")
    return subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, env=env, input=input_text,
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


# PowerShell gibt sonst in der OEM-Codeseite aus: Druckernamen mit Umlauten kaemen verstuemmelt an und waeren nicht druckbar.
_PS_UTF8 = "[Console]::OutputEncoding = [Text.Encoding]::UTF8; $ErrorActionPreference = 'Stop'; "
_PS_LIST = (_PS_UTF8 + "try { Get-Printer | ForEach-Object { $_.Name } } catch { "
            "$e = $_.Exception.Message; try { Get-CimInstance Win32_Printer | ForEach-Object { $_.Name } } "
            "catch { [Console]::Error.WriteLine('Get-Printer: ' + $e + ' / Win32_Printer: ' + $_.Exception.Message); exit 2 } }")
# Virtuelle Drucker, die jedes Windows hat: stehen nur sie in der Liste, ist kein echter Drucker verbunden.
VIRTUAL_WIN = ("microsoft print to pdf", "microsoft xps document writer", "onenote", "fax", "send to onenote",
               "an onenote senden", "pdf24", "adobe pdf")


def system_status():
    """(bereit, Hinweis) - ob das Betriebssystem ueberhaupt drucken kann."""
    if is_windows():
        return (bool(powershell()), "PowerShell not found on this Windows. Printing needs Windows PowerShell "
                                    "(C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe).")
    if shutil.which("lp") and shutil.which("lpstat"):
        return True, "CUPS is installed."
    return False, "CUPS missing. On the Pi: sudo apt install cups-client (or ./install.sh --print)."


def _cups_queues():
    """Richtig eingerichtete CUPS-Warteschlangen (lpstat -a). Nur die kann CUPS sicher bedienen."""
    r = _run(["lpstat", "-a"])
    return [x.split()[0] for x in r.stdout.splitlines() if x.strip()], r


def network_only(printer):
    """True, wenn CUPS den Drucker nur im Netzwerk gesehen hat (lpstat -e), er aber nicht als Drucker eingerichtet ist."""
    if is_windows() or printer == TEST_PRINTER or remote_split(printer)[1]:
        return False
    try:
        queues, _ = _cups_queues()
        if printer in queues:
            return False
        return printer in [x.strip() for x in _run(["lpstat", "-e"]).stdout.splitlines()]
    except (OSError, subprocess.SubprocessError):
        return False


def list_details(server=""):
    """(Liste von {name, kind}, Fehlertext). kind: queue | network (nur gefunden) | windows | remote | test."""
    items, errs = [], []
    ok, hint = system_status()
    if not ok:
        errs.append(hint)
    else:
        try:
            if is_windows():
                r = _run([powershell(), "-NoProfile", "-NonInteractive", "-Command", _PS_LIST])
                names = [x.strip() for x in r.stdout.splitlines() if x.strip()]
                items += [{"name": n, "kind": "windows"} for n in names]
                if r.returncode and not names:
                    errs.append("Windows could not list the printers: " + ((r.stderr or r.stdout or "").strip()[:300]
                                or f"code {r.returncode}") + " Is the service 'Print Spooler' running (services.msc)?")
                elif not names:
                    errs.append("Windows has no printer installed.")
                elif all(any(v in n.lower() for v in VIRTUAL_WIN) for n in names):
                    errs.append("Windows only has virtual printers (PDF, OneNote …), no real printer is connected.")
                if errs and not server:
                    errs.append("Printers the Pi finds are NOT automatically in Windows. Enter the Pi's address below "
                                "(e.g. dexter.local) to print on the Pi's printers, or add the printer in Windows under "
                                "Settings › Printers & scanners.")
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
    if server:
        names, err = remote_printers(server)
        items += [{"name": f"{n} @ {server}", "kind": "remote"} for n in names]
        if err:
            errs.append(err)
    items.append({"name": TEST_PRINTER, "kind": "test"})
    return items, " ".join(e.strip() for e in errs if e.strip())


def list_printers(server=""):
    """(Liste der Druckernamen, Fehlertext oder ''). Der Testdrucker steht immer am Ende."""
    items, err = list_details(server)
    return [i["name"] for i in items], err


def valid_name(name):
    """Druckername nur aus der Liste, ohne Steuerzeichen (er geht an lp bzw. PowerShell)."""
    return bool(name) and len(name) <= 200 and not re.search(r"[\x00-\x1f]", name)


def print_text(printer, title, text, out_dir, server=""):
    """Druckt Text. Gibt (ok, Meldung) zurueck. out_dir: Ablage fuer den Testdrucker. server: CUPS des Pi (siehe oben)."""
    if not valid_name(printer):
        return False, "Invalid printer name."
    name, host = remote_split(printer, server)
    if host:
        return remote_print(host, name, title, text)
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
            r = _run([powershell(), "-NoProfile", "-NonInteractive", "-Command",
                      _PS_UTF8 + "Get-Content -Raw -Encoding UTF8 -LiteralPath $env:PCL_PRN_FILE | Out-Printer -Name $env:PCL_PRN"], env=env)
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
    return _run([powershell(), "-NoProfile", "-NonInteractive", "-Command", _PS_UTF8 + script], env=env)


def status(printer, server=""):
    """Zustand eines Druckers als Dict: lines (Rohinfo fuer die Anzeige), problems (verstaendliche Ursachen), jobs (offene Auftraege)."""
    out = {"printer": printer, "lines": [], "problems": [], "jobs": [], "setup": False}
    name, host = remote_split(printer, server)
    if host:
        return remote_status(host, name, out)
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
                if network_only(printer):
                    uri = discovered_uri(printer)
                    out["setup"] = True
                    out["lines"].append("Found on the network: " + (uri or "(address unknown)"))
                    out["problems"].append(
                        "CUPS has only SEEN this printer on the network, it is not set up as a printer. That is why the "
                        "test page does not come out. Click 🔧 Set up printer (or on the Pi: sudo lpadmin -p '"
                        f"{printer}' -E -v '{uri or 'ipp://PRINTER-IP/ipp/print'}' -m everywhere -o printer-is-shared=true).")
                else:
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


def after_print_problems(printer, job_text="", server=""):
    """Kurz nach dem Senden: (probleme, hinweise). Probleme = Drucker gestoppt/offline/ohne Treiber, Hinweise = Auftrag wartet noch."""
    if WAIT_AFTER <= 0:
        return [], []
    time.sleep(WAIT_AFTER)
    st = status(printer, server)
    probs, warn = list(st["problems"]), []
    if remote_split(printer, server)[1]:
        if st["jobs"] and not probs:
            warn.append(f"{len(st['jobs'])} job(s) still waiting on the Pi. Is the printer on and reachable from the Pi? See 🩺 Check printer.")
    elif not is_windows():
        m = re.search(r"request id is (\S+)", job_text or "")
        if m and any(x.split()[0] == m.group(1) for x in st["jobs"] if x.split()):
            if not probs:
                warn.append(f"Job {m.group(1)} is still waiting in the queue after {int(WAIT_AFTER)} s. "
                             "Is the printer on and reachable from the Pi (ping its IP)? See 🩺 Check printer.")
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
        return False, "Only on the Pi (CUPS). On Windows add the printer under Settings › Printers & scanners."
    if not valid_name(printer) or not re.fullmatch(r"[A-Za-z0-9_.\-]{1,127}", printer):
        return False, "This printer name cannot be used as a CUPS name."
    if not shutil.which("lpadmin"):
        return False, "lpadmin missing. On the Pi: ./install.sh --print"
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
            hint = " Hyperstead's user may not change printers. Run it once yourself on the Pi:"
        else:
            hint = " If the printer does not support driverless printing, pick a model driver (docs/drucken.md). Command:"
        return False, f"Could not set up the printer: {err}.{hint} sudo " + " ".join(
            f"'{c}'" if (" " in c or c == printer) else c for c in cmd)
    return True, f"'{printer}' is now set up in CUPS ({uri}). Print the test page again."


# ---------------------------------------------------------------- CUPS des Pi per IPP (fuer den Laptop)
IPP_TIMEOUT = float(os.environ.get("PCL_IPP_TIMEOUT", "5"))
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # Pi steht im Heimnetz, nie ueber einen Proxy
_REQ_ID = [0]


def valid_server(server):
    return bool(server) and len(server) <= 120 and bool(re.fullmatch(r"[A-Za-z0-9._\-]+(:\d{1,5})?|\[[0-9A-Fa-f:]+\](:\d{1,5})?", server))


def remote_split(printer, server=""):
    """'Buero @ dexter.local' -> ('Buero', 'dexter.local'), sonst (printer, ''). Nur fuer den eingestellten Server."""
    if not server or not printer or " @ " not in printer:
        return printer, ""
    name, host = printer.rsplit(" @ ", 1)
    return (name, host) if host == server and valid_server(host) else (printer, "")


def _base(server):
    return "http://" + (server if re.search(r":\d+$", server) and not server.endswith("]") else server + ":631")


def _attr(tag, name, value):
    v = struct.pack(">i", value) if isinstance(value, int) else value.encode("utf-8")
    n = name.encode("utf-8")
    return struct.pack(">BH", tag, len(n)) + n + struct.pack(">H", len(v)) + v


def _ipp(server, path, op, attrs, data=b""):
    """Eine IPP-Anfrage an CUPS. Gibt (status, gruppen) zurueck; gruppen = Liste (tag, {name: [werte]})."""
    _REQ_ID[0] += 1
    body = struct.pack(">BBHi", 2, 0, op, _REQ_ID[0]) + b"\x01"
    body += _attr(0x47, "attributes-charset", "utf-8") + _attr(0x48, "attributes-natural-language", "en")
    body += _attr(0x45, "printer-uri", "ipp://" + _base(server)[7:] + path)
    for tag, name, value in attrs:
        vals = value if isinstance(value, (list, tuple)) else [value]
        for i, v in enumerate(vals):
            body += _attr(tag, name if i == 0 else "", v)
    body += b"\x03" + data
    req = urllib.request.Request(_base(server) + path, data=body, method="POST",
                                 headers={"Content-Type": "application/ipp"})
    with _OPENER.open(req, timeout=IPP_TIMEOUT) as r:
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


def _ipp_error(server, e):
    msg = str(getattr(e, "reason", "") or e)
    if isinstance(e, urllib.error.HTTPError) and e.code in (401, 403):
        return (f"The Pi ({server}) refuses access from this computer. On the Pi run once: "
                "sudo cupsctl --remote-any --share-printers")
    return (f"Cannot reach CUPS on {server}:631 ({msg}). Is the Pi on, is the address right (try its IP), and did you run "
            "on the Pi: sudo cupsctl --remote-any --share-printers ?")


def remote_printers(server):
    """Drucker des Pi (CUPS-Get-Printers). (namen, fehler)."""
    if not valid_server(server):
        return [], "Invalid Pi address. Example: dexter.local or 192.168.1.20"
    try:
        st, groups = _ipp(server, "/", 0x4002, [(0x44, "requested-attributes", ["printer-name", "printer-is-shared"])])
    except (OSError, ValueError, urllib.error.URLError) as e:
        return [], _ipp_error(server, e)
    if st >= 0x0400 and st != 0x0406:  # 0x0406 = keine Drucker
        return [], f"CUPS on {server} answers with error 0x{st:04x}."
    names = [g["printer-name"][0] for t, g in groups if t == 0x04 and g.get("printer-name")]
    if not names:
        return [], (f"CUPS on {server} has no printer set up yet. Set it up on the Pi first "
                    "(🖨 Printer › 🔧 Set up printer there, or docs/drucken.md).")
    return names, ""


def remote_print(server, name, title, text):
    path = "/printers/" + urllib.request.quote(name, safe="")
    try:
        st, groups = _ipp(server, path, 0x0002, [
            (0x42, "requesting-user-name", "hyperstead"),
            (0x42, "job-name", (title or "Evening report")[:100]),
            (0x49, "document-format", "text/plain"),
        ], data=text.encode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError) as e:
        return False, _ipp_error(server, e)
    if st >= 0x0400:
        msg = " ".join(str(v) for t, g in groups for v in g.get("status-message", []))
        hint = " The printer is not shared on the Pi: there run sudo lpadmin -p '" + name + "' -o printer-is-shared=true" \
            if "not shared" in msg.lower() else ""
        return False, f"The Pi refused the job (0x{st:04x} {msg}).{hint}"
    job = next((g["job-id"][0] for t, g in groups if g.get("job-id")), None)
    msg = f"Sent to {name} on the Pi ({server})." + (f" Job {job}." if job else "")
    probs, warn = after_print_problems(f"{name} @ {server}", "", server)
    if probs:
        return False, "The Pi accepted the job but it is not printing: " + " ".join(probs)
    return True, msg + ("" if not warn else " Note: " + " ".join(warn))


def remote_status(server, name, out):
    path = "/printers/" + urllib.request.quote(name, safe="")
    try:
        st, groups = _ipp(server, path, 0x000B, [(0x44, "requested-attributes", [
            "printer-state", "printer-state-message", "printer-state-reasons", "printer-is-accepting-jobs",
            "queued-job-count", "printer-make-and-model", "device-uri", "printer-is-shared"])])
    except (OSError, ValueError, urllib.error.URLError) as e:
        out["problems"].append(_ipp_error(server, e))
        return out
    if st >= 0x0400:
        out["problems"].append(f"The Pi does not know the printer '{name}' (0x{st:04x}). ↻ Search again.")
        return out
    a = {}
    for t, g in groups:
        if t == 0x04:
            a.update(g)
    state = (a.get("printer-state") or [0])[0]
    reasons = [r for r in a.get("printer-state-reasons", []) if r != "none"]
    out["lines"] += [f"Pi: {server}", f"State: {({3: 'idle', 4: 'printing', 5: 'stopped'}).get(state, state)}"]
    if a.get("printer-state-message", [""])[0]:
        out["lines"].append("Message: " + a["printer-state-message"][0])
    if reasons:
        out["lines"].append("Reasons: " + ", ".join(reasons))
    if a.get("printer-make-and-model"):
        out["lines"].append("Driver on the Pi: " + a["printer-make-and-model"][0])
    if state == 5:
        out["problems"].append(f"CUPS on the Pi has STOPPED this printer. On the Pi: sudo cupsenable '{name}' "
                               "(first make sure the printer is on and reachable).")
    if a.get("printer-is-accepting-jobs") == [False]:
        out["problems"].append(f"The printer on the Pi does not accept jobs. On the Pi: sudo cupsaccept '{name}'")
    if "raw" in (a.get("printer-make-and-model") or [""])[0].lower():
        out["problems"].append("The printer on the Pi is set up WITHOUT a driver (raw), text is silently dropped. "
                               "Set it up again with -m everywhere (docs/drucken.md).")
    n = (a.get("queued-job-count") or [0])[0]
    if n:
        out["jobs"] = [f"{n} job(s) waiting on the Pi"]
    return out
