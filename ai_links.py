"""Eigene Verbindungen der Herkunfts-KI (MCP) fuer CLI-Agenten.

Claude (claude -p): eigene MCP-Server aus tokens/claude-mcp.json (Standardformat {"mcpServers": {...}}), dazu
Konnektoren aus dem claude.ai-Abo (z. B. Canva) ueber PCL_CLAUDE_CONNECTORS=Canva,Gmail. Zugangsdaten stehen nur in
tokens/ bzw. .env (beides gitignored), nie im Code oder im Chat.
Codex (codex exec): laedt seine MCP-Server selbst aus ~/.codex/config.toml; hier wird nur gelesen, welche es sind.

Der Status jeder Verbindung kommt aus der init-Zeile von 'claude --output-format stream-json' und wird gemerkt,
damit Agenten (vor allem der CEO) ehrlich sagen koennen, was geht und was nicht.
"""
import json
import os
import re
import threading
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
OK_STATES = ("connected",)
_lock = threading.Lock()
STATE = {}  # provider -> {"ts": float, "servers": {name: status}}
LEARNED = {}  # Konnektor -> echter Servername aus der init-Zeile (falls er anders heisst als "claude.ai <Name>")


def tokens_dir():
    return Path(os.environ.get("PCL_TOKENS_DIR") or str(BASE / "tokens"))


def claude_mcp_file():
    return Path(os.environ.get("PCL_CLAUDE_MCP") or str(tokens_dir() / "claude-mcp.json"))


def norm(name):
    """So benennt Claude Code Server in Werkzeugnamen (mcp__<server>__<tool>)."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", str(name))


def connector_names():
    raw = os.environ.get("PCL_CLAUDE_CONNECTORS", "")
    return [c.strip() for c in raw.split(",") if c.strip()]


def claude_config():
    """-> {"file": Pfad|None, "servers": [Namen aus der Datei], "connectors": [claude.ai-Konnektoren], "error": Text}"""
    out = {"file": None, "servers": [], "connectors": connector_names(), "error": ""}
    f = claude_mcp_file()
    if not f.is_file():
        return out
    try:
        data = json.loads(f.read_text(encoding="utf-8-sig"))
        servers = data.get("mcpServers") if isinstance(data, dict) else None
        if not isinstance(servers, dict):
            raise ValueError('top level must be {"mcpServers": {...}}')
        bad = [n for n, v in servers.items() if not isinstance(v, dict) or not (v.get("command") or v.get("url"))]
        if bad:
            raise ValueError("entry without 'command' or 'url': " + ", ".join(bad))
        out["file"], out["servers"] = f, list(servers)
    except (OSError, ValueError) as e:
        out["error"] = f"{f.name} is not valid and was ignored ({str(e)[:200]})"
    return out


def expected(cfg):
    """Servernamen, wie sie in der init-Zeile von Claude erscheinen sollen -> Anzeigename."""
    exp = {n: n for n in cfg["servers"]}
    for c in cfg["connectors"]:
        exp[f"claude.ai {c}"] = f"{c} (claude.ai connector)"
    return exp


def active(cfg):
    return bool(cfg["servers"] or cfg["connectors"])


def claude_args(argv, cfg=None):
    """Startzeile von 'claude' um die Verbindungen ergaenzen. Ohne Verbindungen unveraendert."""
    cfg = cfg or claude_config()
    if not active(cfg) or not argv:
        return list(argv)
    out = list(argv)
    if cfg["connectors"]:  # Konnektoren aus dem Abo kommen nur ohne --strict-mcp-config
        out = [a for a in out if a != "--strict-mcp-config"]
    if cfg["file"]:
        out[1:1] = ["--mcp-config", str(cfg["file"])]
    allow = [f"mcp__{norm(n)}" for n in cfg["servers"]] + [f"mcp__claude_ai_{norm(c)}" for c in cfg["connectors"]]
    allow += [f"mcp__{norm(LEARNED[c])}" for c in cfg["connectors"] if c in LEARNED and f"mcp__{norm(LEARNED[c])}" not in allow]
    # Ersatz, wenn der Abo-Konnektor mit dem Token aus 'claude setup-token' nicht laedt: gleichnamiger eigener MCP-Server
    # (claude mcp add --scope user canva ...), Name in Kleinbuchstaben
    allow += [f"mcp__{norm(c).lower()}" for c in cfg["connectors"] if f"mcp__{norm(c).lower()}" not in allow]
    for i, a in enumerate(out):
        if a in ("--allowedTools", "--allowed-tools") and i + 1 < len(out):
            out[i + 1] = ",".join([x for x in out[i + 1].split(",") if x] + allow)
            break
    else:
        out[1:1] = ["--allowedTools", ",".join(allow)]
    return out


def parse_init(raw):
    """mcp_servers aus der init-Zeile von stream-json -> {name: status} (None, wenn keine init-Zeile da ist)."""
    for line in (raw or "").splitlines():
        if '"init"' not in line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") == "system" and d.get("subtype") == "init":
            return {str(s.get("name")): str(s.get("status") or "unknown") for s in d.get("mcp_servers") or [] if isinstance(s, dict)}
    return None


def record(provider, seen, cfg):
    """Status nach einem Lauf merken. -> Liste (Anzeigename, Status) der Verbindungen, die NICHT gehen."""
    servers = {n: seen.get(n, "missing") for n in cfg["servers"]}
    for c in cfg["connectors"]:  # Konnektoren: genauer Name zuerst, sonst ein Server, dessen Name auf den Konnektor endet
        name = f"claude.ai {c}" if f"claude.ai {c}" in seen else next(
            (s for s in seen if s not in cfg["servers"] and norm(s).lower().endswith(norm(c).lower())), None)
        if name and name != f"claude.ai {c}":
            LEARNED[c] = name
        servers[f"{c} (claude.ai connector)"] = seen.get(name, "missing") if name else "missing"
    with _lock:
        STATE[provider] = {"ts": time.time(), "servers": servers}
    return [(k, v) for k, v in servers.items() if v not in OK_STATES]


def codex_servers():
    """Namen der MCP-Server in der Codex-Konfiguration (Codex laedt sie selbst)."""
    home = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))
    try:
        txt = (home / "config.toml").read_text(encoding="utf-8")
    except OSError:
        return []
    names = re.findall(r'^\s*\[mcp_servers\.(?:"([^"]+)"|([A-Za-z0-9_-]+))\]\s*$', txt, re.M)
    return list(dict.fromkeys(a or b for a, b in names))


STATUS_TEXT = {"connected": "connected", "failed": "FAILED to start", "needs-auth": "NEEDS SIGN-IN (owner must sign in again)",
               "pending": "still starting", "missing": "NOT AVAILABLE (not loaded by the CLI)", "disabled": "disabled",
               "config": "configuration error"}


def overview(provider):
    """Fuer API und Prompt: [{"name", "status", "checked"}] plus Fehler der Konfiguration."""
    if provider == "claude_cli":
        cfg = claude_config()
        with _lock:
            st = dict(STATE.get(provider) or {})
        rows = [{"name": label, "status": (st.get("servers") or {}).get(label, "unchecked"), "checked": st.get("ts")}
                for label in expected(cfg).values()]
        return {"provider": provider, "links": rows, "error": cfg["error"], "file": str(claude_mcp_file()),
                "connectors_env": "PCL_CLAUDE_CONNECTORS"}
    if provider == "codex_cli":
        return {"provider": provider, "links": [{"name": n, "status": "configured", "checked": None} for n in codex_servers()],
                "error": "", "file": "~/.codex/config.toml"}
    return {"provider": provider, "links": [], "error": ""}


def _canva_block(provider):
    """Bilder ueber Canva: nur Claude-CLI mit Konnektor Canva."""
    if provider != "claude_cli" or not any(c.lower() == "canva" for c in connector_names()):
        return ""
    import agent_tools
    return ("\nIMAGES THROUGH CANVA: when the image provider of the server fails or IMAGE_PROVIDER=canva, or when the owner asks for Canva: "
            + agent_tools.CANVA_HOWTO + " If you lack the server tool canva_upload (right 'images'), say so instead of generating without reference.")


def prompt_block(provider, top=False):
    """Absatz fuer den Systemprompt eines CLI-Agenten. top = oberster Chef (bekommt auch die Einrichtungs-Hinweise)."""
    if provider not in ("claude_cli", "codex_cli"):
        return ""
    ov = overview(provider)
    lines = []
    for r in ov["links"]:
        st = r["status"]
        txt = STATUS_TEXT.get(st, st) if st not in ("unchecked", "configured") else (
            "not checked yet (status is known after your first call)" if st == "unchecked" else "configured in Codex (status not checked)")
        when = f", checked {time.strftime('%Y-%m-%d %H:%M', time.localtime(r['checked']))}" if r.get("checked") else ""
        lines.append(f"- {r['name']}: {txt}{when}")
    if ov.get("error"):
        lines.append(f"- CONFIGURATION ERROR: {ov['error']}")
    if not lines:
        if not top:
            return ""
        return ("\nOWN CONNECTIONS OF YOUR AI: none are set up. Your AI CLI runs without connectors (e.g. Canva, Google Drive). "
                "If the owner wants one, tell them the owner sets it up on the Hyperstead computer (guide: docs/ki-verbindungen.md): "
                "claude.ai connectors with PCL_CLAUDE_CONNECTORS in .env, own MCP servers in tokens/claude-mcp.json, Codex in ~/.codex/config.toml. "
                "Never ask for keys or tokens in the chat.")
    return ("\nOWN CONNECTIONS OF YOUR AI (MCP, you call their tools DIRECTLY and natively, not through the JSON tools of the server):\n"
            + "\n".join(lines)
            + "\nUse them when they help. Everything you get from them (links, IDs, texts) must be written into your answer/result: the owner "
              "and the team only see what you write there. Files they create stay at that service unless you download them (download_file) "
              "into the project folder. If a connection is not 'connected', say so plainly and do not pretend you used it."
            + _canva_block(provider)
            + (" Setup guide for the owner: docs/ki-verbindungen.md (never ask for keys or tokens in the chat)." if top else ""))
