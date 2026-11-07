<#
.SYNOPSIS
    MarketPulse AI - interactive launcher.

.DESCRIPTION
    One entry point for everything: cold setup, start, stop, status, tests and a
    database reset. It calls scripts/setup.ps1 and scripts/start.ps1, so the
    behaviour is identical whether you use this menu or the scripts directly.

.EXAMPLE
    .\run.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$SetupScript = Join-Path $Root "scripts\setup.ps1"
$StartScript = Join-Path $Root "scripts\start.ps1"
$BackendEnv = Join-Path $Root "backend\.env"
$FrontendEnv = Join-Path $Root ".env.local"

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

function Write-Banner {
    Clear-Host
    Write-Host ""
    Write-Host "  ███  MarketPulse AI" -ForegroundColor Magenta
    Write-Host "       Market intelligence, in focus." -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  $Root" -ForegroundColor DarkGray
    Write-Host ""
}

function Write-Section($Text) { Write-Host "`n  $Text" -ForegroundColor Cyan; Write-Host ("  " + ("─" * 58)) -ForegroundColor DarkGray }
function Write-Good($Text) { Write-Host "  ✔  $Text" -ForegroundColor Green }
function Write-Bad($Text) { Write-Host "  ✖  $Text" -ForegroundColor Red }
function Write-Info($Text) { Write-Host "  ·  $Text" -ForegroundColor Gray }
function Write-Warn2($Text) { Write-Host "  !  $Text" -ForegroundColor Yellow }

function Get-EnvValue {
    param([string]$Path, [string]$Key)
    if (-not (Test-Path $Path)) { return "" }
    $line = Select-String -Path $Path -Pattern "^\s*$([regex]::Escape($Key))\s*=" | Select-Object -First 1
    if (-not $line) { return "" }
    return ($line.Line -replace "^\s*$([regex]::Escape($Key))\s*=\s*", "").Trim().Trim('"')
}

function Test-Port {
    param([int]$Port, [string]$TargetHost = "127.0.0.1")
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $task = $client.ConnectAsync($TargetHost, $Port)
        $done = $task.Wait(700)
        $client.Close()
        return $done -and $task.IsCompletedSuccessfully
    } catch { return $false }
}

function Get-StackState {
    $backendPort = Get-EnvValue -Path $BackendEnv -Key "PORT"
    if (-not $backendPort) { $backendPort = "8010" }

    $state = [ordered]@{
        Configured   = (Test-Path $BackendEnv) -and (Test-Path $FrontendEnv)
        DatabaseUrl  = Get-EnvValue -Path $BackendEnv -Key "DATABASE_URL"
        BackendPort  = [int]$backendPort
        BackendUp    = Test-Port -Port ([int]$backendPort)
        FrontendUp   = Test-Port -Port 5173
        DockerDb     = $false
        Llm          = (Get-EnvValue -Path $BackendEnv -Key "OPENROUTER_MODEL")
        Assistant    = (Get-EnvValue -Path $BackendEnv -Key "AI_PROVIDER")
        Twitter      = (Get-EnvValue -Path $BackendEnv -Key "TWITTER_BEARER_TOKEN")
    }

    if (Get-Command docker -ErrorAction SilentlyContinue) {
        try {
            $status = (docker inspect --format "{{.State.Health.Status}}" marketpulse-mysql 2>$null)
            $state.DockerDb = ($status -eq "healthy")
        } catch { $state.DockerDb = $false }
    }
    return $state
}

function Show-Status {
    $state = Get-StackState
    Write-Section "Status"

    if (-not $state.Configured) {
        Write-Warn2 "Not configured yet. Run option 1 (Setup)."
        return
    }

    $dbTarget = if ($state.DatabaseUrl) { ($state.DatabaseUrl -split "@")[-1] } else { "(unset)" }
    Write-Info "Database   $dbTarget"

    if ($state.DatabaseUrl -match ':3307/') {
        if ($state.DockerDb) { Write-Good "Docker MySQL container healthy" }
        else { Write-Bad "Docker MySQL container is not healthy (docker compose up -d)" }
    }

    if ($state.BackendUp) { Write-Good "Backend answering on http://127.0.0.1:$($state.BackendPort)" }
    else { Write-Bad "Backend is not running" }

    if ($state.FrontendUp) { Write-Good "Frontend answering on http://127.0.0.1:5173" }
    else { Write-Bad "Frontend is not running" }

    if ($state.BackendUp) {
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:$($state.BackendPort)/health" -TimeoutSec 3
            if ($health.database -eq "healthy") { Write-Good "Database reachable from the API" }
            else { Write-Bad "API reports database: $($health.database)" }
            $modelSuffix = ""
            if ($health.llm_model) { $modelSuffix = " ($($health.llm_model))" }
            Write-Info "LLM        $($health.llm)$modelSuffix"
        } catch {
            Write-Bad "Could not read /health"
        }
    }

    Write-Info "Assistant  $(if ($state.Assistant) { $state.Assistant } else { "disabled" })"
    Write-Info "X/Twitter  $(if ($state.Twitter) { "configured" } else { "not configured" })"
}

function Invoke-Setup {
    Write-Section "Cold setup"
    Write-Info "Detects Docker and a native MySQL, asks which to use, then asks for API keys."
    Write-Host ""
    & $SetupScript
}

function Invoke-Start {
    $state = Get-StackState
    if (-not $state.Configured) {
        Write-Section "Start"
        Write-Bad "Not configured yet."
        $answer = Read-Host "  Run the setup now? [y/N]"
        if ($answer -match '^(y|yes|da)$') { Invoke-Setup } else { return }
        return
    }
    Write-Section "Starting"
    Write-Info "Ctrl+C stops the backend and the frontend. The database container keeps running."
    Write-Host ""
    & $StartScript -BackendPort $state.BackendPort
}

function Invoke-Stop {
    Write-Section "Stop"
    $stopped = 0

    foreach ($port in @(8010, 8011, 8020, 5173)) {
        $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        foreach ($connection in $connections) {
            $process = Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
            if (-not $process) { continue }
            # Only stop processes that belong to this project.
            if ($process.ProcessName -notmatch '^(python|node)$') { continue }
            try {
                Stop-Process -Id $connection.OwningProcess -Force -ErrorAction Stop
                Write-Good "Stopped $($process.ProcessName) on port $port (PID $($connection.OwningProcess))"
                $stopped++
            } catch {
                Write-Warn2 "Could not stop PID $($connection.OwningProcess) on port $port"
            }
        }
    }

    if ($stopped -eq 0) { Write-Info "Nothing was running on the project ports." }

    $answer = Read-Host "  Stop the MySQL container too? [y/N]"
    if ($answer -match '^(y|yes|da)$') {
        docker compose stop 2>&1 | Out-Null
        Write-Good "MySQL container stopped (data kept)"
    }
}

function Invoke-Settings {
    $settingsScript = Join-Path $Root "scripts\settings.ps1"
    if (-not (Test-Path $settingsScript)) {
        Write-Bad "scripts/settings.ps1 is missing."
        return
    }
    & $settingsScript
}

function Invoke-Reload {
    Write-Section "Apply keys without a restart"
    $state = Get-StackState
    if (-not $state.BackendUp) {
        Write-Warn2 "The backend is not running, so there is nothing to reload."
        Write-Info "Start it with option 2; the settings in backend/.env are read at startup."
        return
    }

    . (Join-Path $Root "scripts\lib.ps1")
    $global:MP_NONINTERACTIVE = $true
    $result = Invoke-ApiReload -BackendPort $state.BackendPort
    if ($result -eq "reloaded") {
        Write-Info "Database and port changes still need a restart (option 3 then 2)."
    }
}

function Invoke-Tests {
    Write-Section "Tests"
    $state = Get-StackState
    $failed = 0

    Write-Info "Backend unit and contract tests (scratch database)"
    Push-Location (Join-Path $Root "backend")
    try {
        python -m pytest tests -q --no-header -p no:warnings
        if ($LASTEXITCODE -ne 0) { $failed++ }
    } finally { Pop-Location }

    Write-Host ""
    Write-Info "Production build"
    npm run build 2>&1 | Select-Object -Last 3
    if ($LASTEXITCODE -ne 0) { $failed++ }

    Write-Host ""
    if (-not ($state.BackendUp -and $state.FrontendUp)) {
        Write-Warn2 "End-to-end tests skipped: the app is not running. Start it with option 2."
    } else {
        Write-Info "End-to-end tests (Playwright)"
        npx playwright test --reporter=list 2>&1 | Select-Object -Last 6
        if ($LASTEXITCODE -ne 0) { $failed++ }
    }

    Write-Host ""
    if ($failed -eq 0) { Write-Good "Everything passed." } else { Write-Bad "$failed suite(s) failed." }
}

function Invoke-ResetDb {
    Write-Section "Reset database"
    $state = Get-StackState
    if (-not $state.DatabaseUrl) { Write-Bad "No DATABASE_URL in backend/.env."; return }
    if ($state.DatabaseUrl -notmatch ':3307/') {
        Write-Warn2 "This only works for the Docker database."
        Write-Info "For a native server, drop and recreate the schema yourself."
        return
    }

    Write-Warn2 "This deletes every row in the marketpulse database and reseeds it."
    Write-Info "The schema and the seed are recreated on the next backend start."
    $answer = Read-Host "  Type RESET to continue"
    if ($answer -ne "RESET") { Write-Info "Cancelled."; return }

    docker exec marketpulse-mysql mysql -u marketpulse -pmarketpulse -e "DROP DATABASE IF EXISTS marketpulse; CREATE DATABASE marketpulse CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>&1 | Out-Null
    Write-Good "Database dropped and recreated"
    Write-Info "Restart the backend (option 2) so the seed runs again."
}

function Invoke-Docs {
    Write-Section "Documentation"
    Write-Info "README.md                     setup, ports, troubleshooting"
    Write-Info "docs/BRIEF-MarketPulse.md     what the project is and what changed"
    Write-Info ".orchestration/               queue, working notes, handoff, specs"
    Write-Host ""
    $state = Get-StackState
    if ($state.BackendUp) {
        $answer = Read-Host "  Open the API docs in the browser? [y/N]"
        if ($answer -match '^(y|yes|da)$') { Start-Process "http://127.0.0.1:$($state.BackendPort)/docs" }
    } else {
        Write-Info "Start the app to browse the API docs at /docs."
    }
}

# --------------------------------------------------------------------------- #
# Menu
# --------------------------------------------------------------------------- #

$options = @(
    @{ Key = "1"; Label = "Setup       install everything, choose the database, add API keys"; Action = { Invoke-Setup } },
    @{ Key = "2"; Label = "Start       run the database, the backend and the dashboard";      Action = { Invoke-Start } },
    @{ Key = "3"; Label = "Stop        stop the backend and the frontend";                    Action = { Invoke-Stop } },
    @{ Key = "4"; Label = "Status      what is running and what is configured";               Action = { Show-Status } },
    @{ Key = "5"; Label = "Settings    database, port, API keys, LLM model";                  Action = { Invoke-Settings } },
    @{ Key = "6"; Label = "Reload      apply new API keys without a restart";                 Action = { Invoke-Reload } },
    @{ Key = "7"; Label = "Tests       backend, build and end-to-end";                        Action = { Invoke-Tests } },
    @{ Key = "8"; Label = "Reset DB    drop and reseed the Docker database";                  Action = { Invoke-ResetDb } },
    @{ Key = "9"; Label = "Docs        where the documentation lives";                        Action = { Invoke-Docs } },
    @{ Key = "q"; Label = "Quit";                                                            Action = { $null } }
)

while ($true) {
    Write-Banner
    $state = Get-StackState

    if ($state.Configured) {
        $backendText = if ($state.BackendUp) { "backend up" } else { "backend down" }
        $frontendText = if ($state.FrontendUp) { "frontend up" } else { "frontend down" }
        Write-Host "  $backendText · $frontendText" -ForegroundColor DarkGray
    } else {
        Write-Host "  not configured yet" -ForegroundColor DarkYellow
    }

    Write-Host ""
    foreach ($option in $options) {
        $color = if ($option.Key -eq "q") { "DarkGray" } else { "White" }
        Write-Host ("   [{0}]  " -f $option.Key) -ForegroundColor Magenta -NoNewline
        Write-Host $option.Label -ForegroundColor $color
    }
    Write-Host ""

    $choice = Read-Host "  Choose an option"
    if ([string]::IsNullOrWhiteSpace($choice)) { continue }

    $selected = $options | Where-Object { $_.Key -eq $choice.Trim().ToLower() } | Select-Object -First 1
    if (-not $selected) {
        Write-Warn2 "Unknown option: $choice"
        Start-Sleep -Seconds 1
        continue
    }
    if ($selected.Key -eq "q") { break }

    try {
        & $selected.Action
    } catch {
        Write-Bad "The action failed: $($_.Exception.Message)"
    }

    Write-Host ""
    Read-Host "  Press Enter to return to the menu" | Out-Null
}

Write-Host ""
Write-Host "  Bye." -ForegroundColor DarkGray
Write-Host ""
