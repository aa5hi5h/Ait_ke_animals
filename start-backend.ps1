<#
.SYNOPSIS
  Starts the Samanvay FastAPI backend (document analysis + Google sign in).

.DESCRIPTION
  Reads the repository-root .env file, exports GOOGLE_CLIENT_ID and
  YONKO_SESSION_SECRET, puts Tesseract on PATH, then runs uvicorn from
  the backend/ directory.

  The session secret is generated once and appended to .env, so reviewer
  sessions survive restarts.

.EXAMPLE
  .\start-backend.ps1
  .\start-backend.ps1 -Reload
  .\start-backend.ps1 -Port 8000 -Bind 127.0.0.1
#>
[CmdletBinding()]
param(
    [string]$Bind = '127.0.0.1',
    [int]$Port = 8000,
    [switch]$Reload
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
if (-not $root) { $root = (Get-Location).Path }

function Read-EnvFile([string]$Path) {
    $map = @{}
    if (-not (Test-Path $Path)) { return $map }
    foreach ($line in (Get-Content $Path)) {
        $text = "$line".Trim()
        if ($text -eq '' -or $text.StartsWith('#')) { continue }
        $i = $text.IndexOf('=')
        if ($i -lt 1) { continue }
        $key = $text.Substring(0, $i).Trim()
        $value = $text.Substring($i + 1).Trim().Trim('"').Trim("'")
        $map[$key] = $value
    }
    return $map
}

$envPath = Join-Path $root '.env'
$vars = Read-EnvFile $envPath

# --- Python interpreter -------------------------------------------------
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    Write-Host 'No .venv found - creating it and installing backend requirements...' -ForegroundColor Yellow
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        throw 'uv is required to create the virtualenv. Install it from https://docs.astral.sh/uv/'
    }
    & uv venv (Join-Path $root '.venv')
    & uv pip install -r (Join-Path $root 'backend\requirements.txt') --python $python
    if (-not (Test-Path $python)) { throw 'Failed to create .venv - see the output above.' }
}

# --- Session secret: generated once, persisted in .env ------------------
$secret = ''
if ($vars.ContainsKey('YONKO_SESSION_SECRET')) { $secret = $vars['YONKO_SESSION_SECRET'] }
if ([string]::IsNullOrWhiteSpace($secret)) {
    $secret = ("& '$python' -c `"import secrets; print(secrets.token_urlsafe(48))`"")
    $secret = Invoke-Expression $secret
    $secret = "$secret".Trim()
    if ([string]::IsNullOrWhiteSpace($secret)) { throw 'Could not generate YONKO_SESSION_SECRET.' }
    $entry = "YONKO_SESSION_SECRET=$secret"
    if (Test-Path $envPath) { Add-Content -Path $envPath -Value $entry }
    else { Set-Content -Path $envPath -Value $entry }
    Write-Host 'Generated YONKO_SESSION_SECRET and appended it to .env' -ForegroundColor Green
}
$env:YONKO_SESSION_SECRET = $secret

# --- Google OAuth client id --------------------------------------------
$clientId = ''
if (-not [string]::IsNullOrWhiteSpace($env:GOOGLE_CLIENT_ID)) { $clientId = $env:GOOGLE_CLIENT_ID }
elseif ($vars.ContainsKey('VITE_GOOGLE_CLIENT_ID')) { $clientId = $vars['VITE_GOOGLE_CLIENT_ID'] }
if ([string]::IsNullOrWhiteSpace($clientId)) {
    Write-Warning 'GOOGLE_CLIENT_ID is not set. Email sign in works, but Google sign in returns 401 "not configured". Add VITE_GOOGLE_CLIENT_ID to .env.'
}
else { $env:GOOGLE_CLIENT_ID = $clientId }

# --- Tesseract OCR ------------------------------------------------------
$tessDir = $null
$tessCmd = Get-Command tesseract -ErrorAction SilentlyContinue
if ($tessCmd) { $tessDir = Split-Path -Parent $tessCmd.Source }
else {
    $candidates = @(
        (Join-Path $env:ProgramFiles 'Tesseract-OCR'),
        (Join-Path ${env:ProgramFiles(x86)} 'Tesseract-OCR'),
        (Join-Path $env:LOCALAPPDATA 'Tesseract-OCR')
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path (Join-Path $candidate 'tesseract.exe'))) { $tessDir = $candidate; break }
    }
}
if ($tessDir) { $env:PATH = "$tessDir;$env:PATH" }
else {
    Write-Warning 'Tesseract not found - /analyze will return no OCR results. Install with: winget install UB-Mannheim.TesseractOCR'
}

# --- Refuse to double-start --------------------------------------------
$busy = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($busy) {
    Write-Warning "Port $Port is already in use (PID $($busy[0].OwningProcess)). Stop that process first."
    exit 1
}

# --- Launch -------------------------------------------------------------
$uvArgs = @('-m', 'uvicorn', 'app.main:app', '--host', $Bind, '--port', "$Port")
if ($Reload) { $uvArgs += '--reload' }

Push-Location (Join-Path $root 'backend')
try {
    Write-Host ''
    Write-Host "Starting backend on http://$($Bind):$($Port)" -ForegroundColor Cyan
    Write-Host "  python     : $python"
    Write-Host "  tesseract  : $(if ($tessDir) { $tessDir } else { 'MISSING' })"
    Write-Host "  google auth: $(if ($clientId) { 'configured' } else { 'not configured' })"
    Write-Host "  frontend   : run 'npm run dev' separately (http://localhost:5173)" -ForegroundColor DarkGray
    Write-Host "  stop       : Ctrl+C" -ForegroundColor DarkGray
    Write-Host ''
    & $python @uvArgs
}
finally {
    Pop-Location
}
