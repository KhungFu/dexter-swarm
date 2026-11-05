"""Vorlage: Video bei Google Flow erzeugen. Kopieren nach macros/flow.py und die Stellen mit ANPASSEN pruefen.

Die genauen Knoepfe kennt nur deine Aufnahme: Starte einmal
    ./venv/bin/playwright codegen --save-storage macros/flow.json https://flow.google.com/
melde dich an, klicke einen Auftrag einmal von Hand durch und uebernimm die Zeilen aus dem Aufnahmefenster
in den Block "Klickweg" unten. Die Anmeldung landet in macros/flow.json (enthaelt Cookies, nie weitergeben).

PaperclipLite startet das Skript mit:
    PCL_PROMPT   Text des Agenten (Szenenbeschreibung)
    PCL_OUTPUT   leerer Ordner, hier muss das fertige Video landen
    PCL_STORAGE  Pfad zu macros/flow.json
Ein Fehler (Exception) = Werkzeug meldet FEHLER, mit der letzten Ausgabe dieses Skripts.
"""
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

PROMPT = os.environ["PCL_PROMPT"]
OUT = Path(os.environ["PCL_OUTPUT"])
STORAGE = os.environ["PCL_STORAGE"]
WARTEN_MIN = 15  # ANPASSEN: so lange darf Google Flow rechnen (Flow-Clips sind meist nach wenigen Minuten fertig)

if not Path(STORAGE).exists():
    raise SystemExit("No saved sign-in: run playwright codegen --save-storage ... first (see above)")

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, executable_path=os.environ.get("PCL_BROWSER_PATH") or None)
    ctx = browser.new_context(storage_state=STORAGE, accept_downloads=True, viewport={"width": 1440, "height": 900}, locale="de-DE")
    page = ctx.new_page()
    page.set_default_timeout(60_000)
    try:
        # ---------------- Klickweg (ANPASSEN: aus deiner codegen-Aufnahme) ----------------
        page.goto("https://flow.google.com/")
        page.get_by_role("button", name="Create").first.click()            # ANPASSEN: Knopf fuer ein neues Video
        page.locator("textarea").first.fill(PROMPT)                         # ANPASSEN: Eingabefeld fuer den Prompt
        page.get_by_role("button", name="Generate").first.click()          # ANPASSEN: Start-Knopf
        # Warten, bis das Video fertig ist und ein Download-Knopf erscheint
        dl_button = page.get_by_role("button", name="Download").first       # ANPASSEN
        dl_button.wait_for(state="visible", timeout=WARTEN_MIN * 60_000)
        with page.expect_download(timeout=10 * 60_000) as info:
            dl_button.click()
        # ------------------------------------------------------------------------------------
        d = info.value
        d.save_as(OUT / (d.suggested_filename or "flow.mp4"))
        ctx.storage_state(path=STORAGE)  # verlaengerte Anmeldung merken
        print("done:", d.suggested_filename)
    except Exception:
        page.screenshot(path=str(OUT / "error-screen.png"))  # landet in output/, zeigt wo es haengt
        raise
    finally:
        browser.close()
