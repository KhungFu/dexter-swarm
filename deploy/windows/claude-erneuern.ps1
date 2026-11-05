# Claude-CLI (dein Abo) fuer Hyperstead pruefen, aktualisieren und bei Bedarf neu anmelden (Windows 10/11).
#
# Aufruf in PowerShell im Hyperstead-Ordner, als der Windows-Benutzer, unter dem Hyperstead laeuft:
#   powershell -ExecutionPolicy Bypass -File deploy\windows\claude-erneuern.ps1            pruefen, aktualisieren, bei Bedarf neu anmelden
#   powershell -ExecutionPolicy Bypass -File deploy\windows\claude-erneuern.ps1 -Pruefen   nur pruefen, Exitcode 0 = ok, 1 = Anmeldung noetig, 2 = claude fehlt
#   powershell -ExecutionPolicy Bypass -File deploy\windows\claude-erneuern.ps1 -Neu       sofort ein neues Langzeit-Token holen
#
# Das Langzeit-Token aus "claude setup-token" gilt ein Jahr. Es landet in tokens\claude-oauth-token.txt (nur fuer dich lesbar).
# Hyperstead liest die Datei bei jedem Aufruf, ein Neustart ist nicht noetig.
param(
  [switch]$Pruefen,
  [switch]$Neu
)
$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Basis = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$TokDir = if ($env:PCL_TOKENS_DIR) { $env:PCL_TOKENS_DIR } else { Join-Path $Basis "tokens" }
$TokFile = Join-Path $TokDir "claude-oauth-token.txt"
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"

function Schritt($t) { if (-not $Pruefen) { Write-Host ""; Write-Host "== $t" -ForegroundColor Cyan } }
function Ok($t) { if (-not $Pruefen) { Write-Host "   ok: $t" -ForegroundColor Green } }
function Warnung($t) { Write-Host "   $t" -ForegroundColor Yellow }

function Teste {
  # Wie Hyperstead: ohne API-Keys in der Umgebung (sonst rechnet claude ueber den Key statt ueber das Abo ab)
  $alt = @{ K = $env:ANTHROPIC_API_KEY; A = $env:ANTHROPIC_AUTH_TOKEN; T = $env:CLAUDE_CODE_OAUTH_TOKEN }
  Remove-Item Env:ANTHROPIC_API_KEY, Env:ANTHROPIC_AUTH_TOKEN -ErrorAction SilentlyContinue
  if ((Test-Path $TokFile) -and (Get-Item $TokFile).Length -gt 0) {
    $env:CLAUDE_CODE_OAUTH_TOKEN = (Get-Content -Raw $TokFile).Trim()
  }
  $hier = Get-Location
  Set-Location $env:TEMP
  try {
    $script:Antwort = ("Antworte nur mit dem Wort OK" | & claude -p --strict-mcp-config --no-session-persistence --model haiku 2>&1 | Out-String)
    $rc = $LASTEXITCODE
  } finally {
    Set-Location $hier
    $env:ANTHROPIC_API_KEY = $alt.K; $env:ANTHROPIC_AUTH_TOKEN = $alt.A; $env:CLAUDE_CODE_OAUTH_TOKEN = $alt.T
  }
  return ($rc -eq 0 -and $script:Antwort -match "(?i)ok")
}

function TokenAlter {
  if (Test-Path $TokFile) {
    $tage = [int]((Get-Date) - (Get-Item $TokFile).LastWriteTime).TotalDays
    Ok "Langzeit-Token ist $tage Tage alt (gilt 365 Tage, Hyperstead warnt per Telegram 30 Tage vorher)"
  }
}

# 1. Ist claude installiert?
Schritt "1/4 Claude-CLI suchen"
$cl = Get-Command claude -ErrorAction SilentlyContinue
if (-not $cl) {
  if ($Pruefen) { exit 2 }
  Warnung "claude ist nicht installiert."
  $a = Read-Host "   Jetzt mit dem offiziellen Installer installieren (irm https://claude.ai/install.ps1 | iex)? [j/N]"
  if ($a -notmatch "^[jJyY]") { Write-Host "Abgebrochen."; exit 2 }
  Invoke-RestMethod https://claude.ai/install.ps1 | Invoke-Expression
  $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
  $cl = Get-Command claude -ErrorAction SilentlyContinue
  if (-not $cl) { Write-Host "claude nach der Installation nicht gefunden. Neues PowerShell-Fenster oeffnen und erneut starten." -ForegroundColor Red; exit 2 }
}
Ok "$($cl.Source), Version $((& claude --version 2>$null | Select-Object -First 1))"

# 2. Aktualisieren (alte Versionen kennen manche Schalter nicht)
if (-not $Pruefen) {
  Schritt "2/4 Aktualisieren"
  & claude update 2>&1 | Select-Object -Last 3 | ForEach-Object { Write-Host "   $_" }
  if ($LASTEXITCODE -eq 0) { Ok "Version jetzt $((& claude --version 2>$null | Select-Object -First 1))" }
  else { Warnung "Update ging nicht. Bei einer npm-Installation: npm install -g @anthropic-ai/claude-code@latest  (oder: claude install)" }
}

# 3. Funktioniert claude -p?
Schritt "3/4 claude -p testen (wie Hyperstead)"
if (-not $Neu -and (Teste)) {
  Ok "claude -p antwortet"
  TokenAlter
  if (-not $Pruefen) { Write-Host ""; Write-Host "Alles in Ordnung. Nichts zu tun." -ForegroundColor Green }
  exit 0
}
if ($Pruefen) { Write-Host "claude -p geht nicht: $($script:Antwort.Trim())"; exit 1 }
if (-not $Neu) { Warnung "claude -p geht nicht. Meldung:"; Write-Host "     $($script:Antwort.Trim())" }

# 4. Neu anmelden: Langzeit-Token holen (das kann nur der Mensch, im Browser)
Schritt "4/4 Neu anmelden (Langzeit-Token, 1 Jahr)"
Write-Host '   Gleich startet "claude setup-token". Es oeffnet den Browser (oder zeigt einen Link).'
Write-Host '   - Mit deinem Claude-Konto (Pro/Max) anmelden und "Autorisieren" klicken.'
Write-Host '   - Falls ein Code angezeigt wird: hier einfuegen und Enter druecken.'
Write-Host '   - Am Ende zeigt claude ein Token, das mit sk-ant-oat01- beginnt. Dieses Token kopieren.'
Write-Host '   Das Token NIEMANDEM schicken und nirgends hochladen, auch nicht in einen Chat.' -ForegroundColor Yellow
Read-Host "   Weiter mit Enter ..." | Out-Null
& claude setup-token
Write-Host ""
$sicher = Read-Host "   Token einfuegen (die Eingabe bleibt unsichtbar) und Enter" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sicher)
try { $tok = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
$tok = ($tok -replace "\s", "")
if (-not $tok.StartsWith("sk-ant-")) {
  Write-Host "   Das sieht nicht wie ein Claude-Token aus (beginnt nicht mit sk-ant-). Nichts gespeichert." -ForegroundColor Red
  exit 1
}
New-Item -ItemType Directory -Force -Path $TokDir | Out-Null
[IO.File]::WriteAllText($TokFile, $tok)
Remove-Variable tok
# Nur der eigene Benutzer darf die Datei lesen
& icacls $TokFile /inheritance:r /grant:r "$($env:USERNAME):F" | Out-Null
Ok "gespeichert in $TokFile (nur fuer dich lesbar)"

if (Teste) {
  Ok "claude -p antwortet mit dem neuen Token"
  Write-Host ""; Write-Host "Fertig. Hyperstead nutzt das Token ab dem naechsten Aufruf, ohne Neustart." -ForegroundColor Green
  exit 0
}
Warnung "Auch mit dem neuen Token kommt keine Antwort:"
Write-Host "     $($script:Antwort.Trim())"
Warnung "Pruefe Internet und Abo (claude.ai -> Einstellungen) und starte das Skript erneut."
exit 1
