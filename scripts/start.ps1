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

.PARAMETER Detach
    Start the backend and the frontend and return immediately instead of
    waiting. Used by the setup and settings scripts when they restart the app.

.EXAMPLE
    .\scripts\start.ps1

.EXAMPLE
    .\scripts\start.ps1 -Detach
#>
[CmdletBinding()]
param(
    [int]$BackendPort = 8010,
    [int]$FrontendPort = 5173,
    [switch]$SkipDatabase,
    [switch]$Detach
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

. (Join-Path $PSScriptRoot "lib.ps1")
$global:MP_NONINTERACTIVE = $true

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
# A port held by our own backend or frontend is not an error: report it and stop
# instead of starting a second copy. A foreign process is a hard stop.
$alreadyRunning = 0
foreach ($port in @($BackendPort, $FrontendPort)) {
    $listener = Get-ProjectListener -Port $port
    if (-not $listener) { continue }

    if ($listener.IsOurs) {
        Write-Warn "$($listener.Name) is already listening on port $port (PID $($listener.Pid))."
        $alreadyRunning++
    } else {
        Write-Fail "Port $port is held by '$($listener.Name)' (PID $($listener.Pid)), which is not part of this project."
        Write-Host "    Stop it, or pass -BackendPort / -FrontendPort with a free port." -ForegroundColor Yellow
        exit 1
    }
}

if ($alreadyRunning -eq 2) {
    Write-Ok "The app is already running: http://127.0.0.1:$FrontendPort"
    Write-Host "    To restart it, use option 3 (Stop) then option 2 (Start), or the settings manager." -ForegroundColor Yellow
    exit 0
}
if ($alreadyRunning -eq 1) {
    Write-Warn "One component is already running; starting only the missing one."
}

# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------
$backendOut = Join-Path $env:TEMP "marketpulse-backend.log"
$backendErr = Join-Path $env:TEMP "marketpulse-backend.err.log"
$backend = $null

if (Get-ProjectListener -Port $BackendPort) {
    Write-Step "Backend already running on $BackendPort"
    Write-Ok "Leaving it alone"
} else {
    Write-Step "Starting the backend on $BackendPort"
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
}

# ---------------------------------------------------------------------------
# AI assistant service (backend/server.py)
#
# It is a separate app on its own port. Without it the "Ask AI" panel and the
# per-chart "Analyse" buttons are dead, so the launcher starts it whenever
# VITE_AI_API_URL is configured.
# ---------------------------------------------------------------------------
$assistant = $null
$assistantUrl = ""
$frontendEnv = Join-Path $Root ".env.local"
if (Test-Path $frontendEnv) {
    $line = Select-String -Path $frontendEnv -Pattern '^\s*VITE_AI_API_URL\s*=' | Select-Object -First 1
    if ($line) {
        $assistantUrl = ($line.Line -replace '^\s*VITE_AI_API_URL\s*=\s*', "").Trim().Trim('"')
    }
}

if ($assistantUrl) {
    $assistantPort = 0
    if ($assistantUrl -match ':(\d+)') { $assistantPort = [int]$Matches[1] }

    if ($assistantPort -gt 0) {
        if (Get-ProjectListener -Port $assistantPort) {
            Write-Step "AI assistant already running on $assistantPort"
            Write-Ok "Leaving it alone"
        } else {
            Write-Step "Starting the AI assistant on $assistantPort"
            $assistantOut = Join-Path $env:TEMP "marketpulse-assistant.log"
            $assistantErr = Join-Path $env:TEMP "marketpulse-assistant.err.log"
            $assistant = Start-Process -FilePath "python" `
                -ArgumentList "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", "$assistantPort" `
                -WorkingDirectory (Join-Path $Root "backend") `
                -RedirectStandardOutput $assistantOut -RedirectStandardError $assistantErr `
                -PassThru -WindowStyle Hidden

            $assistantReady = $false
            for ($i = 0; $i -lt 30; $i++) {
                try {
                    $assistantHealth = Invoke-RestMethod -Uri "http://127.0.0.1:$assistantPort/health" -TimeoutSec 2
                    $assistantReady = $true
                    break
                } catch { Start-Sleep -Seconds 2 }
            }
            if ($assistantReady) {
                Write-Ok "Assistant healthy: provider=$($assistantHealth.provider), key=$($assistantHealth.key_configured)"
            } else {
                Write-Warn "The assistant did not start. The dashboard works; the Ask AI panel will not."
                Get-Content $assistantErr -Tail 10 -ErrorAction SilentlyContinue
            }
        }
    }
} else {
    Write-Note "VITE_AI_API_URL is empty; the assistant is disabled."
}

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------
$viteOut = Join-Path $env:TEMP "marketpulse-frontend.log"
$viteErr = Join-Path $env:TEMP "marketpulse-frontend.err.log"
$frontend = $null

if (Get-ProjectListener -Port $FrontendPort) {
    Write-Step "Frontend already running on $FrontendPort"
    Write-Ok "Leaving it alone"
} else {
    Write-Step "Starting the frontend on $FrontendPort"
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
        if ($backend) { Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue }
        Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue
        exit 1
    }
    Write-Ok "Frontend serving"
}

Write-Host @"

MarketPulse AI is running.

  Dashboard : http://127.0.0.1:$FrontendPort
  API       : http://127.0.0.1:$BackendPort
  API docs  : http://127.0.0.1:$BackendPort/docs

  Logs      : $backendOut
              $viteOut

"@ -ForegroundColor Green

# -Detach: the caller (setup or settings) keeps the processes running and
# returns to its own flow.
#
# [Environment]::Exit rather than `exit`: the processes started with
# Start-Process hold inherited console handles, and a plain `exit` leaves this
# host waiting on them, which makes a scripted caller appear to hang.
if ($Detach) {
    Write-Host "Started in the background. Stop it with .\run.ps1 (option 3)." -ForegroundColor Yellow
    [Environment]::Exit(0)
}

$watched = @()
if ($backend) { $watched += $backend.Id }
if ($frontend) { $watched += $frontend.Id }
if ($assistant) { $watched += $assistant.Id }

if ($watched.Count -eq 0) {
    Write-Host "Both components were already running; nothing to wait for." -ForegroundColor Yellow
    exit 0
}

Write-Host "Press Ctrl+C to stop the processes this script started." -ForegroundColor Gray
Write-Host "The MySQL container keeps running (stop it with: docker compose stop)." -ForegroundColor Gray

try {
    Wait-Process -Id $watched -ErrorAction Stop
} finally {
    Write-Host "`nStopping the processes this script started..." -ForegroundColor Yellow
    foreach ($id in $watched) {
        Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Stopped. The database container is left running." -ForegroundColor Yellow
}
