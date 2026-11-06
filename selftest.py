#!/usr/bin/env python3
"""Hyperstead Selbsttest: prueft auf dem echten Rechner (Pi), ob alles funktioniert, was die Agenten brauchen.

    python selftest.py            # alles pruefen (Windows; auf dem Pi: python3 selftest.py)
    python selftest.py web        # nur Gruppe: web | browser | run | llm | links | telegram | media | ocr | code | film

Wird das Skript mit dem normalen System-Python gestartet, wechselt es selbst ins Hyperstead-venv
(venv\\Scripts\\python.exe bzw. ./venv/bin/python). Fehlt das venv, sagt es, wie man es anlegt.

Jede Zeile: OK / MISSING (optional) / ERROR, bei Problemen mit konkretem Hinweis. Es werden keine Keys ausgegeben.
Die LLM-Tests senden je Anbieter eine winzige Anfrage (kostet praktisch nichts). Bilder werden nur im Temp-Ordner erzeugt.
"""
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def venv_python(root=HERE, windows=os.name == "nt"):
    """Pfad zum Python im Hyperstead-venv (oder None, wenn es keins gibt)."""
    p = root / "venv" / ("Scripts/python.exe" if windows else "bin/python")
    return p if p.exists() else None


def in_venv():
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def missing_venv_hint(windows=os.name == "nt", missing="requests"):
    head = f"Python package '{missing}' is missing (no Hyperstead venv yet, or it is out of date).\n"
    if windows:
        return (head +
                "  Run in PowerShell in the Hyperstead folder:\n"
                "    powershell -ExecutionPolicy Bypass -File install.ps1\n"
                "  Then again:  python selftest.py")
    return (head +
            "  Run in the Hyperstead folder:  ./install.sh  (or ./install.sh --update)\n"
            "  Then again:  python3 selftest.py")


def ensure_venv(argv=None, run=None):
    """Startet den Selbsttest mit dem venv-Python neu, wenn er mit dem System-Python gestartet wurde.

    Gibt None zurueck, wenn hier weitergemacht werden soll, sonst den Exit-Code des neuen Laufs.
    """
    if in_venv() or os.environ.get("HYPERSTEAD_SELFTEST_REEXEC"):
        return None
    vpy = venv_python()
    if vpy is None:
        return None
    import subprocess
    env = dict(os.environ, HYPERSTEAD_SELFTEST_REEXEC="1")
    print(f"(using Hyperstead venv: {vpy})")
    sys.stdout.flush()
    return (run or subprocess.call)([str(vpy), str(HERE / "selftest.py"), *(sys.argv[1:] if argv is None else argv)], env=env)


if __name__ == "__main__":
    _rc = ensure_venv()
    if _rc is not None:
        sys.exit(_rc)

try:
    import requests  # noqa: E402

    import agent_tools as T  # noqa: E402
    import app as A  # noqa: E402  (laedt .env)
except ModuleNotFoundError as _e:
    if __name__ == "__main__":
        print(missing_venv_hint(missing=_e.name))
        sys.exit(2)
    raise

RES = {"ok": 0, "warn": 0, "fail": 0}


def line(state, name, detail=""):
    sym = {"ok": "\033[32mOK     \033[0m", "warn": "\033[33mMISSING\033[0m", "fail": "\033[31mERROR  \033[0m"}[state]
    RES[state] += 1
    print(f"  {sym} {name:<34} {detail}")


def check(name, fn, optional=False, hint=""):
    t0 = time.time()
    try:
        out = fn()
    except Exception as e:  # noqa: BLE001
        msg = str(e)[:220].replace("\n", " ")
        line("warn" if optional else "fail", name, msg + (f"  -> {hint}" if hint else ""))
        return None
    line("ok", name, f"{(out or '')}  ({time.time() - t0:.1f} s)".strip())
    return out


WIN = os.name == "nt"
if WIN:
    os.system("")  # schaltet Farbcodes in cmd.exe ein (sonst erscheint "←[32m")
# Installationshinweis je System: (Linux/Pi, Windows)
WIN_HINTS = {
    "ffmpeg": "winget install Gyan.FFmpeg (then open a new window)",
    "tesseract-ocr tesseract-ocr-deu": "winget install UB-Mannheim.TesseractOCR (tick German during installation), add the folder to PATH",
    "poppler-utils": "Poppler for Windows (github.com/oschwartz10612/poppler-windows), add the folder Library\\bin to PATH",
}


def fix(linux, windows):
    return windows if WIN else linux


def need(prog, apt):
    if not shutil.which(prog):
        raise RuntimeError(f"'{prog}' not installed: " + fix(f"sudo apt install {apt}", WIN_HINTS.get(apt, f"install {prog} and add it to PATH")))
    return shutil.which(prog)


def group_web():
    print("\nInternet tools")
    check("Web search", lambda: (lambda r: r.splitlines()[0][:80] if r.startswith("1.") else (_ for _ in ()).throw(RuntimeError(r)))(
        T.web_search("Raspberry Pi 4 Datenblatt", 3)),
        hint="DuckDuckGo (without key) is sometimes rate-limited: set SEARXNG_URL, TAVILY_API_KEY or BRAVE_API_KEY in .env")
    check("Read page", lambda: T.fetch_url("https://example.com")[:60].replace("\n", " "))
    check("Image search", lambda: (lambda r: r.splitlines()[0][:80] if r.strip() and "No images" not in r[:12] else (_ for _ in ()).throw(RuntimeError(r[:100])))(
        T.image_search("mountain lake", 3)))
    with tempfile.TemporaryDirectory(prefix="pcl-selftest-") as td:
        root = Path(td)
        prov = T._env("IMAGE_PROVIDER", "pollinations").lower()  # noqa: SLF001
        if prov in ("gemini", "openai", "openrouter"):
            def imodel():
                if prov == "openrouter":
                    model = T._model_env("IMAGE_MODEL", T.OPENROUTER_IMAGE_MODEL)  # noqa: SLF001
                    r = requests.get("https://openrouter.ai/api/v1/images/models", timeout=20,
                                     headers={"Authorization": "Bearer " + T._env("OPENROUTER_API_KEY").split(",")[0].strip()})  # noqa: SLF001
                    if r.status_code < 400:
                        ids = {m.get("id") for m in (r.json().get("data") or [])}
                        if model not in ids:
                            raise RuntimeError(f"Model '{model}' not in the OpenRouter image model list. E.g.: "
                                               + ", ".join(sorted(i for i in ids if i)[:8]))
                elif prov == "gemini":
                    model = T._model_env("IMAGE_MODEL", T.GEMINI_IMAGE_MODEL)  # noqa: SLF001
                    r = requests.get(f"{T.GEMINI_BASE}/models/{model}", timeout=20,
                                     headers={"x-goog-api-key": T._env("GEMINI_API_KEY").split(",")[0].strip()})  # noqa: SLF001
                else:
                    model = T._model_env("IMAGE_MODEL", "gpt-image-1")  # noqa: SLF001
                    base = T._env("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")  # noqa: SLF001
                    r = requests.get(f"{base}/models/{model}", timeout=20,
                                     headers={"Authorization": "Bearer " + T._env("OPENAI_API_KEY").split(",")[0].strip()})  # noqa: SLF001
                if r.status_code >= 400:
                    raise RuntimeError(f"Model '{model}' not available (HTTP {r.status_code}): {r.text[:150]}")
                return f"{model} available"
            check(f"Image model ({prov})", imodel, hint="leave IMAGE_MODEL in .env empty (default) or enter a name from the model list, without models/ and quotes")
        if prov == "sdcpp":
            check("Image computer reachable", lambda: f"HTTP {requests.get(T._env('SDCPP_URL').rstrip('/') + '/', timeout=10).status_code}",  # noqa: SLF001
                  hint="Laptop on? sd-server started? SDCPP_URL in .env = http://<laptop IP>:1234, allow the Windows firewall for the private network")
        check(f"Create image ({prov})", lambda: T.image_generate(root, {"prompt": "a red apple, simple illustration", "name": "test",
                                                                          "quality": "low" if prov == "openai" else ""})[:80],
              hint="image computer started?" if prov == "sdcpp" else "choose another IMAGE_PROVIDER with a key if this one is not reachable")
        ref = next(iter(sorted((root / "assets").glob("test.*"))), None) if (root / "assets").exists() else None
        pkey = prov == "pollinations" and T._env("POLLINATIONS_API_KEY").strip()  # noqa: SLF001
        if (prov in ("openai", "gemini", "openrouter", "sdcpp", "cloudflare") or pkey) and ref:
            check("Image with reference image", lambda: T.image_generate(root, {
                "prompt": "the same apple, now cut in half, same drawing style", "refs": [f"assets/{ref.name}"],
                "path": "karten/test-ref.png", "quality": "low" if prov == "openai" else ""})[:80],
                  hint="reference images need an image model with an edit function (gpt-image-1, gemini-2.5-flash-image, "
                       "with Pollinations e.g. black-forest-labs/flux.2-klein-4b)")
    if T.video_enabled():
        import video_providers as VP
        for prov in VP.providers():
            def vkeys(prov=prov):
                VP.keys_of(prov)
                return f"key present, model {VP.model_of(prov, False, VP.providers()[0])} (no clip created, that costs money)"
            check(f"Video provider {prov}", vkeys, optional=True, hint="enter the key in .env, see docs/videodienste.md")

        def vmodel():
            key, model = T._gemini_key(), VP.model_of("gemini", False, VP.providers()[0])  # noqa: SLF001
            r = requests.get(f"{T.GEMINI_BASE}/models/{model}", headers={"x-goog-api-key": key}, timeout=20)
            if r.status_code >= 400:
                raise RuntimeError(f"Model '{model}' not available (HTTP {r.status_code})")
            return f"{model} available"
        if "gemini" in VP.providers():
            check("Video model (Gemini)", vmodel, optional=True, hint="GEMINI_API_KEY with billing? check VIDEO_MODEL")
    else:
        line("warn", "Video generation", "off (optional: VIDEO_PROVIDER=kling, wan, higgsfield ... in .env, see docs/videodienste.md)")
    import video_providers as VPX
    if VPX.video_ai_enabled():
        check("video_ai (fal.ai)", lambda: "key present" if T._env("FAL_KEY") else (_ for _ in ()).throw(RuntimeError("FAL_KEY missing")),  # noqa: SLF001
              optional=True, hint="enter FAL_KEY in .env (fal.ai)")
    if VPX.audio_provider():
        need_key = "ELEVENLABS_API_KEY" if VPX.audio_provider() == "elevenlabs" else "FAL_KEY"
        check(f"sound_generate ({VPX.audio_provider()})",
              lambda: "key present" if T._env(need_key) else (_ for _ in ()).throw(RuntimeError(f"{need_key} missing")),  # noqa: SLF001
              optional=True, hint=f"enter {need_key} in .env")
    check("SSRF protection blocks local addresses", lambda: "ok" if _blocked() else (_ for _ in ()).throw(RuntimeError("not blocked!")))


def _blocked():
    try:
        T.fetch_url("http://127.0.0.1:8787/")
    except T.ToolError:
        return True
    return False


def group_llm():
    print("\nAI providers (one mini request each)")
    any_real = False
    for pid, cfg in A.PROVIDERS.items():
        if pid in ("mock", "cli"):
            continue
        if not A.provider_configured(pid):
            if cfg.get("kind") == "cli":
                why = "PCL_ALLOW_CLI=1 missing in .env" if not A.ALLOW_CLI else f"'{cfg['bin']}' not installed (see README: CLI providers)"
            else:
                why = "no key" if pid != "ollama" else f"not reachable ({cfg['url']}) - is 'ollama serve' running?"
            line("warn", cfg["label"], why)
            continue
        any_real = True

        def run(pid=pid):
            txt, tok = A.call_llm({"provider": pid, "model": "", "name": "Selbsttest", "id": 0, "perms": "{}"},
                                  [{"role": "user", "content": "Answer only with the word: ready"}])
            return f"answer: {txt.strip()[:40]!r}"
        check(f"{cfg['label']} ({cfg['model'] or 'default'})", run,
              hint="CLI program signed in? Test once by hand: echo hello | " + (cfg.get("cmd") or "") if cfg.get("kind") == "cli" else "")
        if pid == "ollama":
            def olist():
                r = A.list_models("ollama", force=True)
                if r.get("error"):
                    raise RuntimeError(r["error"])
                return f"{len(r['models'])} models: " + ", ".join(r["models"][:4])
            check("Ollama: model list", olist, hint="load a model: ollama pull qwen2.5:3b")
    if not any_real:
        line("fail", "no real AI provider", "set at least one key in .env or start Ollama")


def group_telegram():
    print("\nTelegram")
    if not A.TG_TOKEN:
        line("warn", "Bot token", "TELEGRAM_BOT_TOKEN not set (optional)")
        return

    def me():
        r = requests.get(f"{A.TG_API}/bot{A.TG_TOKEN}/getMe", timeout=15).json()
        if not r.get("ok"):
            raise RuntimeError("token invalid (check @BotFather)")
        return "Bot @" + r["result"].get("username", "?")
    check("Bot reachable", me)
    if not A.TG_CHATS:
        line("warn", "Chat ID", "TELEGRAM_CHAT_ID missing: write /start to the bot, it tells you the ID")
        return
    cid = sorted(A.TG_CHATS)[0]

    def send():
        r = requests.post(f"{A.TG_API}/bot{A.TG_TOKEN}/sendMessage", json={"chat_id": cid, "text": "Hyperstead Selbsttest: Telegram funktioniert."}, timeout=15).json()
        if not r.get("ok"):
            raise RuntimeError(r.get("description", "Senden fehlgeschlagen"))
        return "test message sent"
    check("Message to your chat ID", send)


def group_media():
    print("\nVideo, speech, documents")
    check("ffmpeg", lambda: need("ffmpeg", "ffmpeg") and "ok", optional=WIN)
    check("ffprobe", lambda: need("ffprobe", "ffmpeg") and "ok", optional=WIN)
    with tempfile.TemporaryDirectory(prefix="pcl-selftest-") as td:
        root = Path(td)

        def tts():
            out = T.speak(root, "Hello, this is a test of the speech output.", "en", "t")
            eng = "Piper" if T._piper()[0] else "espeak-ng"  # noqa: SLF001
            return f"{eng}: {out[:60]}"
        check("Speech output", tts, optional=WIN, hint=fix("sudo apt install espeak-ng; better: ./install.sh (sets up Piper)",
                                             "venv\\Scripts\\pip install edge-tts and TTS_ENGINE=edge in .env (online voice)"))
        check("Piper (good voice)", lambda: (lambda x: "model " + Path(x[1]).name if x[0] else (_ for _ in ()).throw(RuntimeError("not set up")))(T._piper()),  # noqa: SLF001
              optional=True, hint=fix("./install.sh (sets up Piper)", "optional, on Windows by hand (see docs/windows.md)"))

        def doc():
            r = T.make_document(root, {"title": "Test", "format": "pdf", "content": "# Chapter\n\nUmlauts: äöüß. Turkish: ğışçö."})
            if "WARNING" in r:
                raise RuntimeError(r[r.index("WARNING"):][:160])
            return r[:70]
        check("Create PDF (umlauts, Turkish)", doc, hint=fix("sudo apt install fonts-dejavu-core", "font Arial/Georgia missing in C:\\Windows\\Fonts?"))


def group_ocr():
    print("\nOCR (scanned PDFs and images)")
    check("tesseract", lambda: need("tesseract", "tesseract-ocr tesseract-ocr-deu") and "languages: " + (T._tess_lang() or "none"),  # noqa: SLF001
          optional=WIN)
    check("pdftoppm", lambda: need("pdftoppm", "poppler-utils") and "ok", optional=WIN)
    if shutil.which("tesseract") and "deu" not in T._tess_lang():  # noqa: SLF001
        line("warn", "German for OCR", fix("sudo apt install tesseract-ocr-deu", "reinstall Tesseract and tick German")
             + " (otherwise umlauts are recognised worse)")


CODE_SAMPLES = {  # Datei -> fehlerfreies Mini-Programm (wird nur geprueft, nicht ausgefuehrt)
    "t.py": "print('ok')\n", "t.js": "console.log('ok');\n", "t.ts": "const x: number = 1;\n",
    "Main.java": "public class Main { public static void main(String[] a) { System.out.println(1); } }\n",
    "t.rs": "fn main() { println!(\"ok\"); }\n", "t.go": "package main\n\nfunc main() {}\n",
    "t.c": "int main(void) { return 0; }\n", "t.cpp": "int main() { return 0; }\n", "t.sh": "echo ok\n",
    "t.rb": "puts 1\n", "t.php": "<?php echo 1;\n", "t.lua": "print(1)\n",
}


def group_code():
    print("\nProgramming (permission 'Programming': check/compile code)")
    with tempfile.TemporaryDirectory(prefix="pcl-selftest-") as td:
        for fn, src in CODE_SAMPLES.items():
            (Path(td) / fn).write_text(src, encoding="utf-8")
            def run(fn=fn):
                r = T.check_code(td, fn)
                if "not installed" in r:
                    raise RuntimeError(r.split(".")[0] + fix("  -> ./install.sh --code", "  -> optional, install the compiler and add it to PATH"))
                if "ERROR" in r:
                    raise RuntimeError(r[:200])
                return "ok"
            ext = Path(fn).suffix.lower()
            lang = "Python" if ext == ".py" else T.CODE_CHECKERS[ext][0]
            check(f"{lang} ({fn})", run, optional=True)


def group_browser():
    print("\nReal browser (browse_page)")
    if not T.browser_enabled():
        line("warn", "Browser", "off (optional: " + fix("./install.sh (sets up the browser)", "venv\\Scripts\\pip install playwright; venv\\Scripts\\python -m playwright install chromium") + ")")
        return
    with tempfile.TemporaryDirectory(prefix="pcl-selftest-") as td:
        check("Open page in the browser", lambda: (lambda r: f"{len(r[1])} Screenshot, " + r[0].splitlines()[1][:50])(
            T.browse_page(td, "https://example.com", screenshot=True)),
            hint="Chromium missing? ./venv/bin/python -m playwright install chromium (or PCL_BROWSER_PATH)")

    def blocked():
        try:
            T.browse_page(td, "http://127.0.0.1:8787/")
        except T.ToolError:
            return "ok"
        raise RuntimeError("not blocked!")
    check("Browser blocks local addresses", blocked)
    _macros()


def _macros():
    if T._env("PCL_MACROS", "0") != "1":  # noqa: SLF001
        line("warn", "Browser macros (MagicLight, Flow)", "off (optional: PCL_MACROS=1, see macros/README.md)")
        return
    sites = T.macro_sites()
    if not sites:
        line("warn", "Browser macros (MagicLight, Flow)", "no macro in macros/ (copy the template, see macros/README.md)")
        return
    for s in sites:
        login = (T.macro_dir() / f"{s}.json").exists()
        line("ok" if login else "warn", f"Macro {s}", "sign-in saved (not started, that costs credits)" if login
             else f"sign-in missing: playwright codegen --save-storage macros/{s}.json ...")


def group_run():
    print("\nRun code (permission 'Run code', sandboxed)")
    if not T.run_enabled():
        line("warn", "Run code", fix("off (bubblewrap missing: ./install.sh --run, or PCL_ALLOW_RUN=0)",
                                            "not available on Windows (needs Linux), PCL_ALLOW_RUN=0 hides it"))
        return
    with tempfile.TemporaryDirectory(prefix="pcl-selftest-") as td:
        def py():
            r = T.run_code(td, code="print(6*7)", lang="python")
            if "Exit-Code 0" not in r or "42" not in r:
                raise RuntimeError(r[:200] + "  -> Unprivilegierte User-Namespaces aktiv? (sysctl kernel.unprivileged_userns_clone=1)")
            return "ok"
        check("Python in the sandbox", py)

        def nonet():
            r = T.run_code(td, code="import socket\ntry:\n socket.create_connection(('1.1.1.1',53),3); print('NET')\n"
                                    "except OSError: print('closed')", lang="python")
            if "closed" not in r:
                raise RuntimeError("Sandbox has internet! " + r[:120])
            return "no internet in the sandbox"
        check("Sandbox without network", nonet)


def group_rust():
    print("\nBuild Rust programs (tool rust_project, permission 'Run code')")
    import rust_builder as R
    if not R.cargo_path():
        line("warn", "cargo", fix("not found: curl https://sh.rustup.rs -sSf | sh (then restart Hyperstead)",
                                  "not found: winget install Rustlang.Rustup (with Visual Studio Build Tools C++), then restart"))
        return
    line("ok", "cargo", R.cargo_path())
    mode = R.sandbox_mode()
    if not mode:
        line("warn", "Build Rust", fix("off (bubblewrap missing: ./install.sh --run, or PCL_CARGO=0/PCL_ALLOW_RUN=0)",
                                       "off: on Windows without sandbox only with PCL_CARGO_UNSAFE=1 in .env"))
        return
    line("ok" if mode == "bwrap" else "warn", "Isolation", "bubblewrap" if mode == "bwrap" else "NONE (PCL_CARGO_UNSAFE=1)")
    with tempfile.TemporaryDirectory(prefix="pcl-selftest-") as td:
        d = Path(td) / "rust" / "probe"
        (d / "src").mkdir(parents=True)
        (d / "Cargo.toml").write_text('[package]\nname = "probe"\nversion = "0.1.0"\nedition = "2021"\n', encoding="utf-8")
        (d / "src" / "main.rs").write_text('fn main() { println!("ok"); }\n#[cfg(test)]\nmod t { #[test] fn a() { assert_eq!(1 + 1, 2); } }\n',
                                           encoding="utf-8")

        def pkg():
            r = R.rust_project(td, {"op": "package", "dir": "rust/probe"})
            if "PACKAGE DONE" not in r:
                raise RuntimeError(r[-300:] + fix("", "  -> Visual Studio Build Tools (C++) installed?"))
            return "built, tested, output/probe.zip"
        check("Build + test sample program", pkg)


def group_film():
    print("\nFilm studio (Blender, tool film)")
    import film_studio as F
    exe = F.blender_exe()
    if not exe:
        line("warn", "Blender", fix("not found: sudo apt install blender or BLENDER_PATH in .env",
                                    "not found: BLENDER_PATH=C:\\Program Files\\Blender Foundation\\Blender 4.2\\blender.exe in .env"))
        return
    line("ok", "Blender", exe)
    with tempfile.TemporaryDirectory(prefix="pcl-selftest-") as td:
        root = Path(td)
        plan = {"titel": "Selbsttest", "aufloesung": "320x180", "fps": 6,
                "figuren": {"Bello": {"art": "hund"}, "Mimi": {"art": "katze", "farbe": "#888888"}},
                "szenen": [{"id": "s01", "figuren": {"Bello": {"pos": [-1.5, 0]}, "Mimi": {"pos": [1.5, 0]}},
                            "requisiten": [{"typ": "baum", "pos": [-4, 3]}], "dialog": [{"figur": "Bello", "text": "Hello Mimi!"}],
                            "aktionen": [{"zeit": 0.3, "figur": "Mimi", "tun": "springen"}], "dauer": 1.5}]}
        F.film(root, {"op": "save", "film": plan})
        if check("Preview image (1 frame)", lambda: F.film(root, {"op": "preview"})[:60],
                 hint="old graphics driver? Try BLENDER_ENGINE=cycles in .env (slower, without graphics card)") is None:
            return
        check("Render scene (1.5 s)", lambda: F.film(root, {"op": "render"}).splitlines()[0][:80],
              hint="ffmpeg and speech output needed (group media)")


def group_links():
    print("\nOwn AI connections (MCP of Claude/Codex CLI, docs/ki-verbindungen.md)")
    import ai_links as L
    cfg = L.claude_config()
    if cfg["error"]:
        line("fail", "tokens/claude-mcp.json", cfg["error"])
    if not L.active(cfg) and not L.codex_servers():
        line("warn", "no connections set up", "optional: PCL_CLAUDE_CONNECTORS=Canva in .env or tokens/claude-mcp.json")
        return
    if L.active(cfg):
        if not A.ALLOW_CLI or not shutil.which("claude"):
            line("fail", "Claude CLI", "PCL_ALLOW_CLI=1 and an installed 'claude' are needed")
        else:
            try:
                A.ai_links_check()
            except Exception as e:  # noqa: BLE001
                line("fail", "Claude CLI test call", str(e)[:200])
        for r in L.overview("claude_cli")["links"]:
            ok = r["status"] == "connected"
            hint = "" if ok else ("  -> claude.ai connectors need 'claude /login' with your subscription (see docs)"
                                  if "connector" in r["name"] else "  -> check command/url in tokens/claude-mcp.json")
            line("ok" if ok else "fail", r["name"][:34], L.STATUS_TEXT.get(r["status"], r["status"]) + hint)
    for n in L.codex_servers():
        line("ok", f"Codex: {n}"[:34], "configured in ~/.codex/config.toml (status not checked)")


GROUPS = {"web": group_web, "browser": group_browser, "run": group_run, "llm": group_llm, "links": group_links, "telegram": group_telegram, "media": group_media, "ocr": group_ocr, "code": group_code, "rust": group_rust, "film": group_film}

if __name__ == "__main__":
    wanted = [a for a in sys.argv[1:] if a in GROUPS] or list(GROUPS)
    print("Hyperstead self-test")
    for g in wanted:
        GROUPS[g]()
    print(f"\nResult: {RES['ok']} OK, {RES['warn']} missing/optional, {RES['fail']} errors")
    sys.exit(1 if RES["fail"] else 0)
