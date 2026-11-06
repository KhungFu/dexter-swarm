@echo off
rem Hyperstead unter Windows starten (vorher einmal install.ps1 ausfuehren)
rem Vor dem Start: Voraussetzungen pruefen. Fehlt etwas, kommt EINE Frage (20 s Zeit, ohne Antwort startet Hyperstead
rem einfach, damit der Autostart nie haengen bleibt). Installiert wird nur nach "j".
cd /d "%~dp0..\.."
if not exist venv\Scripts\python.exe (
  echo Hyperstead ist noch nicht installiert ^(Ordner venv fehlt^).
  echo In PowerShell in diesem Ordner ausfuehren:  powershell -ExecutionPolicy Bypass -File install.ps1
  pause
  exit /b 1
)
venv\Scripts\python.exe voraussetzungen.py --start
venv\Scripts\python.exe app.py
pause
