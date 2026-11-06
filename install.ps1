# Hyperstead unter Windows einrichten: venv + Abhaengigkeiten + .env mit zufaelligem Passwort,
# danach Pruefung aller Voraussetzungen mit Rueckfrage vor jeder Installation (voraussetzungen.py)
# Aufruf in PowerShell im Hyperstead-Ordner:  powershell -ExecutionPolicy Bypass -File install.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$py = Get-Command py -ErrorAction SilentlyContinue
$pyArgs = @("-3")
if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue; $pyArgs = @() }
if (-not $py) {
  Write-Host "Python fehlt: https://www.python.org/downloads/ installieren (Haken bei 'Add python.exe to PATH')."
  exit 1
}
if (-not (Test-Path "venv")) { & $py.Source @pyArgs -m venv venv }
$vpy = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
& $vpy -m pip install -q --upgrade pip
& $vpy -m pip install -q -r requirements.txt
if ($LASTEXITCODE -eq 0) {
  # Stempel: hyperstead-start.bat erkennt daran, ob requirements.txt sich seit der letzten Installation geaendert hat
  $hash = (Get-FileHash "requirements.txt" -Algorithm SHA256).Hash.ToLower()
  [IO.File]::WriteAllText((Join-Path $PSScriptRoot "venv\.requirements.sha256"), $hash)
  Write-Host "Abhaengigkeiten installiert."
} else {
  Write-Host "WARNUNG: pip install -r requirements.txt ging nicht (Internet?). Die Pruefung unten bietet es erneut an."
}

if (-not (Test-Path ".env")) {
  $bytes = New-Object byte[] 18
  [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
  $pw = [Convert]::ToBase64String($bytes).Replace("+", "x").Replace("/", "y").Replace("=", "")
  $lines = Get-Content ".env.example" -Encoding UTF8 | ForEach-Object { if ($_ -match '^APP_TOKEN=') { "APP_TOKEN=$pw" } else { $_ } }
  [IO.File]::WriteAllLines((Join-Path $PSScriptRoot ".env"), [string[]]$lines, (New-Object Text.UTF8Encoding $false))
  Write-Host ""
  Write-Host " .env angelegt. Dein Login-Passwort (jetzt notieren): $pw"
  Write-Host " API-Keys eintragen:  notepad .env"
} else {
  Write-Host ".env existiert bereits - unveraendert gelassen."
}
# Alle weiteren Voraussetzungen pruefen (Video, Stimme, Browser, OCR, Filmstudio, Bildrechner, Rust, Compiler).
# Es wird NICHTS ohne Rueckfrage installiert: vor jedem Teil j/n (a = alle weiteren ja, x = alle weiteren nein).
# Nur anzeigen:  venv\Scripts\python.exe voraussetzungen.py --liste
Write-Host ""
& $vpy (Join-Path $PSScriptRoot "voraussetzungen.py")

Write-Host ""
Write-Host "Starten:  deploy\windows\hyperstead-start.bat   (oder: venv\Scripts\python.exe app.py)"
Write-Host "Pruefen:  python selftest.py"
