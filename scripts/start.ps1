<#
.SYNOPSIS
    Start MarketPulse AI (database, backend, frontend) on Windows.

.DESCRIPTION
    Brings the database up if it runs in Docker, starts the FastAPI backend and
    the Vite dev server, and waits until both answer. Ctrl+C stops the two
    processes this script started; the database container keeps running.

.PARAMETER BackendPort
    Backend port. Default 8010 (8000 is used by another local service on some
    machines).

.PARAMETER FrontendPort
    Vite port. Default 5173.

.PARAMETER SkipDatabase
    Do not touch Docker; assume MySQL is already reachable.

.EXAMPLE
    .\scripts\start.ps1
#>
[CmdletBinding()]
param(
    [int]$BackendPort = 8010,
    [int]$FrontendPort = 5173,
    [switch]$SkipDatabase
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Write-Step($Message) { Write-Host "`n==> $Message" -ForegroundColor Cyan }
function Write-Ok($Message) { Write-Host "    OK  $Message" -ForegroundColor Green }
function Write-Fail($Message) { Write-Host "    X   $Message" -ForegroundColor Red }

if (-not (Test-Path (Join-Path $Root "backend\.env"))) {
    Write-Fail "backend/.env is missing. Run .\scripts\setup.ps1 first."
    exit 1
}

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
if (-not $SkipDatabase) {
    Write-Step "Ensuring the database is running"
    $composeFile = Join-Path $Root "docker-compose.yml"
    $usesDocker = $false
    if (Test-Path $composeFile) {
        $envLine = Select-String -Path (Join-Path $Root "backend\.env") -Pattern '^DATABASE_URL="?([^"\r\n]+)' | Select-Object -First 1
        if ($envLine -and $envLine.Matches[0].Groups[1].Value -match ':3307/') { $usesDocker = $true }
    }

    if ($usesDocker) {
        docker compose up -d | Out-Null
        for ($i = 0; $i -lt 60; $i++) {
            $status = (docker inspect --format "{{.State.Health.Status}}" marketpulse-mysql 2>$null)
            if ($status -eq "healthy") { break }
            Start-Sleep -Seconds 2
        }
        if ($status -ne "healthy") { Write-Fail "MySQL container is not healthy. Run: docker compose logs mysql"; exit 1 }
        Write-Ok "MySQL container healthy"
    } else {
        Write-Ok "Using the MySQL server configured in backend/.env"
    }
}

# ---------------------------------------------------------------------------
# Ports
# ---------------------------------------------------------------------------
foreach ($port in @($BackendPort, $FrontendPort)) {
    $inUse = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($inUse) {
        Write-Fail "Port $port is already in use (PID $($inUse[0].OwningProcess))."
        Write-Host "    Stop it, or pass -BackendPort / -FrontendPort with a free port." -ForegroundColor Yellow
        exit 1
    }
}

# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------
Write-Step "Starting the backend on $BackendPort"
$backendOut = Join-Path $env:TEMP "marketpulse-backend.log"
$backendErr = Join-Path $env:TEMP "marketpulse-backend.err.log"
$backend = Start-Process -FilePath "python" `
    -ArgumentList "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "$BackendPort" `
    -WorkingDirectory (Join-Path $Root "backend") `
    -RedirectStandardOutput $backendOut -RedirectStandardError $backendErr `
    -PassThru -WindowStyle Hidden

$ready = $false
for ($i = 0; $i -lt 45; $i++) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/health" -TimeoutSec 2
        $ready = $true
        break
    } catch { Start-Sleep -Seconds 2 }
}
if (-not $ready) {
    Write-Fail "The backend did not start. Last lines of $backendErr :"
    Get-Content $backendErr -Tail 20 -ErrorAction SilentlyContinue
    Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
    exit 1
}
Write-Ok "Backend healthy: database=$($health.database), llm=$($health.llm)"

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------
Write-Step "Starting the frontend on $FrontendPort"
$viteOut = Join-Path $env:TEMP "marketpulse-frontend.log"
$viteErr = Join-Path $env:TEMP "marketpulse-frontend.err.log"
$frontend = Start-Process -FilePath "npm.cmd" `
    -ArgumentList "run", "dev", "--", "--port", "$FrontendPort", "--host", "127.0.0.1" `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $viteOut -RedirectStandardError $viteErr `
    -PassThru -WindowStyle Hidden

$viteReady = $false
for ($i = 0; $i -lt 45; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:$FrontendPort/" -TimeoutSec 2 -UseBasicParsing
        if ($response.StatusCode -eq 200) { $viteReady = $true; break }
    } catch { Start-Sleep -Seconds 2 }
}
if (-not $viteReady) {
    Write-Fail "The frontend did not start. Last lines of $viteErr :"
    Get-Content $viteErr -Tail 20 -ErrorAction SilentlyContinue
    Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue
    exit 1
}
Write-Ok "Frontend serving"

Write-Host @"

MarketPulse AI is running.

  Dashboard : http://127.0.0.1:$FrontendPort
  API       : http://127.0.0.1:$BackendPort
  API docs  : http://127.0.0.1:$BackendPort/docs

  Logs      : $backendOut
              $viteOut

Press Ctrl+C to stop the backend and the frontend.
The MySQL container keeps running (stop it with: docker compose stop).

"@ -ForegroundColor Green

try {
    Wait-Process -Id $backend.Id, $frontend.Id -ErrorAction Stop
} finally {
    Write-Host "`nStopping the processes this script started..." -ForegroundColor Yellow
    Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue
    Write-Host "Stopped. The database container is left running." -ForegroundColor Yellow
}
