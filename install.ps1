# Hyperstead unter Windows einrichten: venv + Abhaengigkeiten + .env mit zufaelligem Passwort
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
Write-Host "Abhaengigkeiten installiert."

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
Write-Host ""
Write-Host "Starten:  deploy\windows\hyperstead-start.bat   (oder: venv\Scripts\python.exe app.py)"
Write-Host "Pruefen:  python selftest.py"
