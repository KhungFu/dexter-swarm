"""Werkstatt: Agenten arbeiten mit echten Befehlen im Projektordner und ruesten Programme nach.

Stufen (je Agent):
  1 vorsichtig: jeder Befehl wird als Antrag gestellt
  2 normal:     Befehle im Projekt laufen sofort; Installationen, Loeschen, Pfade ausserhalb des Projekts -> Antrag
  3 frei:       alles laeuft sofort (nur mit PCL_WERKSTATT_FREI=1, sonst wie Stufe 2)

Antrag = Mitarbeiter -> CEO prueft -> Besitzer bestaetigt (Web oder Telegram) -> Server fuehrt den Befehl aus.
Die Einteilung unten ist eine Vorsortierung nach Mustern, KEINE Abschottung: Stufe 2 faengt die ueblichen
Installations- und Loeschbefehle ab, ein Agent mit boeser Absicht koennte sie umgehen. Deshalb ist die Werkstatt
standardmaessig aus und nur der Besitzer kann sie je Agent einschalten.
"""
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

IS_WIN = os.name == "nt"


def cmd_timeout():      # Befehl eines Agenten (.env wird erst nach dem Import gelesen, deshalb als Funktion)
    return int(os.environ.get("PCL_BEFEHL_TIMEOUT", "600"))


def install_timeout():  # freigegebene Nachruestung
    return int(os.environ.get("PCL_NACHRUEST_TIMEOUT", "1800"))

OUT_CHARS = 6000
_lock = threading.Lock()  # immer nur ein Werkstatt-Befehl gleichzeitig (kleiner Laptop/Pi)


def enabled():
    return os.environ.get("PCL_ALLOW_WERKSTATT", "0") == "1"


def free_allowed():
    return os.environ.get("PCL_WERKSTATT_FREI", "0") == "1"


def level(raw):
    """Stufe aus dem gespeicherten Wert; Stufe 3 nur, wenn der Besitzer sie in der .env erlaubt."""
    try:
        n = int(raw)
    except (TypeError, ValueError):
        n = 2
    n = min(3, max(1, n))
    return 2 if n == 3 and not free_allowed() else n


INSTALL = [
    r"\b(npm|pnpm|yarn|bun)\s+(i|install|add|ci|update|upgrade|up|link|dlx|x)\b",
    r"\b(npm|pnpm|yarn)\s+(-g|--global)\b", r"\bnpm\s+exec\b",
    r"\bpip3?\s+(install|download|uninstall)\b", r"-m\s+pip\s+(install|download|uninstall)\b", r"\bpipx\b",
    r"\buv\s+(pip|add|tool|sync|python\s+install)\b", r"\bconda\s+(install|create|update)\b", r"\bpoetry\s+(add|install)\b",
    r"\b(winget|choco|chocolatey|scoop|apt|apt-get|aptitude|dpkg|dnf|yum|zypper|pacman|brew|snap|flatpak|port|pkg|rpm|msiexec)\b",
    r"\bsudo\b", r"\bsu\s", r"\bdoas\b", r"\brunas\b", r"Start-Process[^\n]*-Verb\s+RunAs",
    r"\bcargo\s+(install|binstall)\b", r"\bgo\s+install\b", r"\bgem\s+install\b", r"\bcomposer\s+(require|global)\b",
    r"\b(Install-Module|Install-Package|Install-Script|Add-AppxPackage|Enable-WindowsOptionalFeature)\b",
    r"\b(rustup|nvm|volta|fnm)\b", r"\bnpx\s+(-y|--yes)\b",
    r"\b(curl|wget|iwr|irm|Invoke-WebRequest|Invoke-RestMethod)\b[^\n|]*\|\s*(sh|bash|zsh|python3?|iex|Invoke-Expression)\b",
    r"\b(iex|Invoke-Expression)\b",
    r"\bplaywright\s+install\b", r"\bremotion\s+browser\s+ensure\b",
]
DANGER = [
    r"(^|[\s;&|(])(rm|rmdir|rd|del|erase|shred|unlink)\s", r"\bRemove-Item\b", r"\b(ri|rmdir)\s+-",
    r"\bformat(\.com)?\s+[a-z]:", r"\b(mkfs|fdisk|diskpart|dd)\b", r"\b(shutdown|reboot|halt|poweroff|Stop-Computer|Restart-Computer)\b",
    r"\breg(\.exe)?\s+(add|delete|import)\b", r"\b(Set-ItemProperty|New-ItemProperty)\b[^\n]*HK(LM|CU)",
    r"\b(schtasks|crontab|systemctl|service|sc(\.exe)?\s+(create|config|delete)|launchctl)\b",
    r"\bgit\s+(push|remote\s+(add|set-url))\b", r"\bchmod\s+[0-7]*[67][0-7]*\s+/", r"\bchown\b",
    r"\b(setx|Set-ExecutionPolicy|netsh|New-NetFirewallRule|icacls|takeown)\b",
    r"\b(Stop-Process|taskkill|kill|pkill|killall)\b",
]
SECRET = [r"(^|[\\/\s\"'=])\.env\b", r"\btokens[\\/]", r"\bAPP_TOKEN\b", r"_API_KEY\b", r"\bpcl\.db\b", r"\.secret\b",
          r"\b(printenv|Get-ChildItem\s+env:|gci\s+env:|ls\s+env:)", r"(^|[\s;&|])(env|set)\s*($|[;&|])",
          r"\$env:\w*(KEY|TOKEN|SECRET|PASSWORD)", r"\.ssh\b", r"\.claude[\\/]", r"\.codex[\\/]", r"\bid_rsa\b"]
_ABS = re.compile(r"""(?:^|(?<=[\s"'=(:,;|&<>]))(~[\\/]|~(?=\s|$)|[A-Za-z]:[\\/]|\\\\|/(?!dev/null\b)[A-Za-z_.][\w.\-]+|%\w+%|\$HOME\b|\$\{HOME|\$env:(?!npm_)\w+)""")


def classify(cmd, root):
    """-> (art, grund): art 'frei' | 'antrag' | 'verboten'."""
    c = str(cmd or "")
    if not c.strip():
        return "verboten", "empty command"
    for p in SECRET:
        if re.search(p, c, re.I):
            return "verboten", "access data (.env, tokens, environment variables, credentials) is blocked for agents"
    for p in INSTALL:
        if re.search(p, c, re.I):
            return "antrag", "installation/new tool"
    for p in DANGER:
        if re.search(p, c, re.I):
            return "antrag", "deleting or changing the system"
    if re.search(r"(^|[\\/\s\"'=])\.\.([\\/]|$|\s)", c):
        return "antrag", "path outside the project folder (..)"
    rs = str(Path(root).resolve())
    for m in _ABS.finditer(c):
        rest = c[m.start():].split()[0].strip("\"'")
        if rest.lower().startswith(rs.lower()):
            continue
        return "antrag", "path outside the project folder"
    return "frei", ""


def clean_env(root=None):
    """Umgebung ohne Zugangsdaten; npx installiert nichts heimlich nach."""
    env = {k: v for k, v in os.environ.items()
           if not (re.search(r"(KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL)", k, re.I) or k in ("TELEGRAM_CHAT_ID",))}
    env["npm_config_yes"] = "false"
    env["PCL_WERKSTATT"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    if root:
        nb = Path(root) / "node_modules" / ".bin"
        env["PATH"] = str(nb) + os.pathsep + env.get("PATH", "")
    return env


def shell_argv(cmd, shell=None):
    sh = (shell or "").lower().strip()
    if not sh:
        sh = "powershell" if IS_WIN else "bash"
    if sh in ("powershell", "pwsh", "ps"):
        exe = shutil.which("pwsh") or shutil.which("powershell") or "powershell"
        return [exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", cmd]
    if sh == "cmd":
        return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c", cmd]
    exe = shutil.which("bash") or shutil.which("sh") or "/bin/sh"
    return [exe, "-c", cmd]


def run(cmd, root, shell=None, timeout=None):
    """Fuehrt einen Befehl im Projektordner aus. -> (exitcode, ausgabe)"""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    tmo = timeout or cmd_timeout()
    kw = {}
    if IS_WIN:
        kw["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        kw["start_new_session"] = True
    with _lock:
        t0 = time.time()
        try:
            p = subprocess.Popen(shell_argv(cmd, shell), cwd=str(root), env=clean_env(root), stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", **kw)
        except FileNotFoundError as e:
            return 127, f"Shell not found: {e}"
        try:
            out, _ = p.communicate(timeout=tmo)
        except subprocess.TimeoutExpired:
            _kill(p)
            out = (p.communicate()[0] or "") if p.stdout else ""
            return 124, clip(out) + f"\n(time limit {tmo} s reached - stopped)"
        return p.returncode, clip(out) + f"\n(done in {time.time() - t0:.0f} s)"


def _kill(p):
    try:
        if IS_WIN:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
        else:
            os.killpg(p.pid, 9)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass


def clip(s, n=OUT_CHARS):
    s = s or ""
    return s if len(s) <= n else s[:n // 3] + f"\n... ({len(s) - n} characters shortened) ...\n" + s[-(2 * n // 3):]


def note_installed(root, cmd, wozu, who, code):
    """Firmenwissen: was schon nachgeruestet ist, damit es niemand doppelt beantragt."""
    f = Path(root) / "wissen" / "werkzeuge.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    head = "" if f.exists() else ("# Installed tools\n\nApproved and installed by the owner. "
                                   "Check here before a new request.\n\n")
    line = (f"- {time.strftime('%Y-%m-%d')}: `{cmd}`" + (f" for {wozu}" if wozu else "") + f" (requested by {who}, "
            + ("ok" if code == 0 else f"error, exit {code}") + ")\n")
    with f.open("a", encoding="utf-8") as fh:
        fh.write(head + line)


def platform_hint():
    if IS_WIN:
        return ("Windows: commands run in PowerShell (or \"shell\": \"cmd\"). You install programs with winget "
                "(z. B. winget install --id OpenJS.NodeJS.LTS -e --scope user --accept-package-agreements --accept-source-agreements), "
                "packages with npm/pip.")
    return "Linux: commands run in bash. Programs via apt (needs sudo), packages with npm/pip (pip preferably in a venv in the project)."


def doc(lvl, native=""):
    lv = {1: "1 (careful): EVERY command is a request",
          2: "2 (normal): commands in the project folder run immediately; installations, deleting and paths outside the project are requests",
          3: "3 (free): everything runs immediately, the owner only gets a notice"}[lvl]
    return ("\nWORKSHOP (you work like on a real computer, level " + lv + "):\n"
            + (native + "\n" if native else "")
            + "- befehl: {\"tool\": \"befehl\", \"befehl\": \"npx remotion render src/index.ts Main output/film.mp4\", \"shell\": \"\"} "
              f"runs a command in the project folder (time limit {cmd_timeout()} s) and returns the output. {platform_hint()}\n"
            + "- nachruesten: {\"tool\": \"nachruesten\", \"befehl\": \"npm install remotion @remotion/cli\", \"wozu\": \"animate the intro\", "
              "\"groesse\": \"approx. 300 MB\"} requests a program or package you are missing (keys befehl = command, wozu = what for, groesse = size). "
              "The request goes to the CEO, the CEO presents it to the owner, after their yes the server installs exactly this command and you get the task back with the result. "
              "Only request what really makes the work better, look in wissen/werkzeuge.md first and check with befehl (e.g. node --version) "
              "whether it is already there. Submit a request only once, keep working on the rest and write in result what you are waiting for.\n"
            + "- Access data (.env, tokens, environment variables) is blocked. What you install applies to all projects on this computer.")


def ceo_prompt(req_name, req_role, cmd, wozu, groesse, project):
    return (f"An employee of your company '{project}' requests to install a program/package on the computer.\n"
            f"Employee: {req_name} ({req_role or 'no role'})\nCommand: {cmd}\nWhat for: {wozu or '(not given)'}\n"
            f"Size: {groesse or '(not given)'}\n\nCheck as the boss: does the company really need this for better work, is the command "
            "sensible and from a reputable source (official package sources npm/PyPI/winget/apt), does it already exist? You do NOT decide "
            "finally, the owner confirms afterwards. Only reject what is obviously unnecessary, duplicate or dangerous.\n"
            "Answer ONLY with JSON: {\"forward\": true or false, \"recommendation\": \"one or two sentences to the owner, in the owner's language\"}")
