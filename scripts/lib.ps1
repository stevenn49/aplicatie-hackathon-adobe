<#
.SYNOPSIS
    Shared helpers for the MarketPulse AI scripts.

.DESCRIPTION
    Dot-source this file:

        . "$PSScriptRoot\lib.ps1"

    It provides console output, prompts, .env read/write, port checks and the
    OpenRouter free-model discovery used by both setup.ps1 and settings.ps1.
#>

# --------------------------------------------------------------------------- #
# Console output
# --------------------------------------------------------------------------- #

function Write-Step($Message) { Write-Host "`n==> $Message" -ForegroundColor Cyan }
function Write-Ok($Message) { Write-Host "    OK   $Message" -ForegroundColor Green }
function Write-Warn($Message) { Write-Host "    !    $Message" -ForegroundColor Yellow }
function Write-Fail($Message) { Write-Host "    X    $Message" -ForegroundColor Red }
function Write-Note($Message) { Write-Host "         $Message" -ForegroundColor DarkGray }

# --------------------------------------------------------------------------- #
# Prompts
#
# Non-interactive mode is a GLOBAL flag, not a script-scoped one: the helpers
# live in a dot-sourced file and a $script: variable set by the caller was not
# always visible here, which made Read-Host block forever under a redirected
# stdin. `[Console]::IsInputRedirected` is the second guard.
# --------------------------------------------------------------------------- #

function Test-Interactive {
    if ($global:MP_NONINTERACTIVE) { return $false }
    try {
        if ([Console]::IsInputRedirected) { return $false }
    } catch { return $false }
    return $true
}

function Read-Choice {
    param(
        [string]$Prompt,
        [string[]]$Options,
        [string]$Default
    )
    if (-not (Test-Interactive)) { return $Default }
    $list = $Options -join " / "
    while ($true) {
        $answer = Read-Host "    $Prompt [$list] (default: $Default)"
        if ([string]::IsNullOrWhiteSpace($answer)) { return $Default }
        $match = $Options | Where-Object { $_ -eq $answer.Trim().ToLower() } | Select-Object -First 1
        if ($match) { return $match }
        Write-Warn "Choose one of: $list"
    }
}

function Read-Secret {
    param([string]$Prompt, [string]$Default = "")
    if (-not (Test-Interactive)) { return $Default }
    $hint = if ($Default) { " (Enter keeps the current value)" } else { " (Enter skips)" }
    $secure = Read-Host "    $Prompt$hint" -AsSecureString
    if ($null -eq $secure -or $secure.Length -eq 0) { return $Default }
    return [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    )
}

function Read-Text {
    param([string]$Prompt, [string]$Default = "")
    if (-not (Test-Interactive)) { return $Default }
    $answer = Read-Host "    $Prompt (default: $Default)"
    if ([string]::IsNullOrWhiteSpace($answer)) { return $Default }
    return $answer.Trim()
}

function Read-Number {
    param([string]$Prompt, [int]$Default, [int]$Min = 0, [int]$Max = 999)
    while ($true) {
        $answer = Read-Text -Prompt $Prompt -Default "$Default"
        if ($answer -match '^\d+$') {
            $value = [int]$answer
            if ($value -ge $Min -and $value -le $Max) { return $value }
        }
        Write-Warn "Enter a number between $Min and $Max."
    }
}

function Mask {
    param([string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { return "(empty)" }
    if ($Value.Length -le 8) { return "****" }
    return $Value.Substring(0, 6) + "…" + $Value.Substring($Value.Length - 4)
}

# --------------------------------------------------------------------------- #
# .env read/write
# --------------------------------------------------------------------------- #

function Get-EnvValue {
    param([string]$Path, [string]$Key)
    if (-not (Test-Path $Path)) { return "" }
    $line = Select-String -Path $Path -Pattern "^\s*$([regex]::Escape($Key))\s*=" | Select-Object -First 1
    if (-not $line) { return "" }
    return ($line.Line -replace "^\s*$([regex]::Escape($Key))\s*=\s*", "").Trim().Trim('"')
}

function Set-EnvValue {
    param([string]$Path, [string]$Key, [string]$Value)
    if (-not (Test-Path $Path)) { New-Item -ItemType File -Path $Path | Out-Null }
    $content = Get-Content $Path -Raw
    if ($null -eq $content) { $content = "" }
    $pattern = "(?m)^\s*$([regex]::Escape($Key))\s*=.*$"
    $replacement = "$Key=`"$Value`""
    if ($content -match $pattern) {
        $content = [regex]::Replace($content, $pattern, $replacement, 1)
    } else {
        $content = $content.TrimEnd() + "`r`n$replacement`r`n"
    }
    Set-Content -Path $Path -Value $content -NoNewline
}

# --------------------------------------------------------------------------- #
# Network helpers
# --------------------------------------------------------------------------- #

function Test-Port {
    param([int]$Port, [string]$TargetHost = "127.0.0.1")
    # Get-NetTCPConnection sees wildcard binds (0.0.0.0) that a loopback connect
    # can miss, and it does not depend on Task.IsCompletedSuccessfully, which
    # behaves differently between Windows PowerShell 5.1 and PowerShell 7.
    try {
        $listening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
        if ($listening) { return $true }
    } catch { }
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $task = $client.ConnectAsync($TargetHost, $Port)
        $done = $task.Wait(1000)
        $client.Close()
        return [bool]$done
    } catch { return $false }
}

function Find-FreePort {
    param([int]$Start = 8010, [int]$End = 8099)
    for ($port = $Start; $port -le $End; $port++) {
        if (-not (Test-Port -Port $port)) { return $port }
    }
    return $null
}

# --------------------------------------------------------------------------- #
# Running stack: detect, stop, restart
# --------------------------------------------------------------------------- #

<#
    Returns the process listening on a port, but only when it looks like one of
    ours (python for the backend, node for the frontend). Anything else is
    reported as foreign so a script never kills a service it did not start.
#>
function Get-ProjectListener {
    param(
        [int]$Port,
        [string[]]$ExpectedNames = @("python", "node")
    )
    $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $connection) { return $null }

    $process = Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
    if (-not $process) { return $null }

    $isOurs = $false
    foreach ($name in $ExpectedNames) {
        if ($process.ProcessName -like "$name*") { $isOurs = $true; break }
    }

    return [pscustomobject]@{
        Port    = $Port
        Pid     = $connection.OwningProcess
        Name    = $process.ProcessName
        IsOurs  = $isOurs
        Foreign = -not $isOurs
    }
}

<#
    Describes what is running right now: the backend, the frontend and the
    Docker database container.
#>
function Get-RunningStack {
    param([int]$BackendPort = 8010, [int]$FrontendPort = 5173)

    $backend = Get-ProjectListener -Port $BackendPort -ExpectedNames @("python")
    $frontend = Get-ProjectListener -Port $FrontendPort -ExpectedNames @("node")

    $database = "not running"
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        try {
            $status = (docker inspect --format "{{.State.Health.Status}}" marketpulse-mysql 2>$null)
            if ($status) { $database = $status }
        } catch { $database = "not running" }
    }

    return [pscustomobject]@{
        Backend      = $backend
        Frontend     = $frontend
        BackendUp    = [bool]$backend
        FrontendUp   = [bool]$frontend
        BackendPort  = $BackendPort
        FrontendPort = $FrontendPort
        Database     = $database
        AnythingUp   = [bool]($backend -or $frontend)
    }
}

<#
    Stops the backend and the frontend, but only processes that look like ours.
    Returns the number of processes stopped.
#>
function Stop-ProjectStack {
    param([int]$BackendPort = 8010, [int]$FrontendPort = 5173)

    $stopped = 0
    foreach ($port in @($BackendPort, $FrontendPort)) {
        $listener = Get-ProjectListener -Port $port
        if (-not $listener) { continue }
        if (-not $listener.IsOurs) {
            Write-Warn "Port $port is held by '$($listener.Name)' (PID $($listener.Pid)), which is not part of this project. Leaving it alone."
            continue
        }
        try {
            Stop-Process -Id $listener.Pid -Force -ErrorAction Stop
            Write-Ok "Stopped $($listener.Name) on port $port (PID $($listener.Pid))"
            $stopped++
        } catch {
            Write-Warn "Could not stop PID $($listener.Pid) on port $port"
        }
    }
    return $stopped
}

<#
    Waits until a port is free again, so a restart never races the old process.
#>
function Wait-PortFree {
    param([int]$Port, [int]$TimeoutSeconds = 15)
    for ($i = 0; $i -lt ($TimeoutSeconds * 2); $i++) {
        if (-not (Test-Port -Port $Port)) { return $true }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

<#
    Restarts the stack in place: stops what is ours, waits for the ports to be
    free, then starts the backend and the frontend detached.

    Returns $true when the stack is answering afterwards.
#>
function Restart-ProjectStack {
    param(
        [int]$BackendPort = 8010,
        [int]$FrontendPort = 5173,
        [string]$Root
    )

    Write-Step "Restarting the app"
    $stopped = Stop-ProjectStack -BackendPort $BackendPort -FrontendPort $FrontendPort
    if ($stopped -eq 0) { Write-Note "Nothing of ours was running." }

    if (-not (Wait-PortFree -Port $BackendPort)) {
        Write-Fail "Port $BackendPort is still busy; not starting."
        return $false
    }
    if (-not (Wait-PortFree -Port $FrontendPort)) {
        Write-Fail "Port $FrontendPort is still busy; not starting."
        return $false
    }

    $startScript = Join-Path $Root "scripts\start.ps1"
    & $startScript -BackendPort $BackendPort -FrontendPort $FrontendPort -SkipDatabase -Detach
    return $true
}

<#
    Asks whether to restart, only when something is actually running.
    `$Reason` explains why a restart is needed.
#>
<#
    Asks the running API to re-read backend/.env, so a key or model change
    applies without a restart.

    Returns one of: "reloaded", "not-running", "failed".
#>
function Invoke-ApiReload {
    param([int]$BackendPort = 8010)

    if (-not (Test-Port -Port $BackendPort)) { return "not-running" }

    try {
        $result = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$BackendPort/api/admin/reload" -TimeoutSec 10
        Write-Ok "The running API reloaded its configuration."
        if ($result.llm) { Write-Note "LLM: $($result.llm)$(if ($result.llm_model) { " ($($result.llm_model))" })" }
        if ($result.changes -and $result.changes.Count -gt 0) {
            foreach ($change in $result.changes) { Write-Note "changed: $change" }
        } else {
            Write-Note "No value changed relative to what the process already held."
        }
        return "reloaded"
    } catch {
        Write-Warn "The API did not accept the reload: $($_.Exception.Message)"
        return "failed"
    }
}

function Invoke-RestartPrompt {
    param(
        [string]$Reason,
        [int]$BackendPort = 8010,
        [int]$FrontendPort = 5173,
        [string]$Root
    )

    $stack = Get-RunningStack -BackendPort $BackendPort -FrontendPort $FrontendPort
    if (-not $stack.AnythingUp) {
        Write-Note "The app is not running, so nothing needs restarting."
        return
    }

    Write-Host ""
    Write-Warn $Reason
    Write-Note "The backend reads its settings at startup, so it must be restarted."
    $answer = Read-Choice -Prompt "Restart now?" -Options @("yes", "no") -Default "yes"
    if ($answer -ne "yes") {
        Write-Note "Restart skipped. The change takes effect the next time you start the app."
        return
    }

    Restart-ProjectStack -BackendPort $BackendPort -FrontendPort $FrontendPort -Root $Root | Out-Null
}

# --------------------------------------------------------------------------- #
# OpenRouter model discovery
# --------------------------------------------------------------------------- #

<#
    Fetches the public OpenRouter catalogue and returns the models that cost
    nothing to use. No API key is required for the catalogue itself.

    Returns objects with: Id, Name, ContextLength, PromptPrice, CompletionPrice.
    Returns $null when the catalogue cannot be reached, so callers can fall back
    to a manual model id instead of failing.
#>
function Get-OpenRouterFreeModels {
    param([int]$TimeoutSeconds = 25)

    $uri = "https://openrouter.ai/api/v1/models"
    try {
        $response = Invoke-RestMethod -Uri $uri -TimeoutSec $TimeoutSeconds -Headers @{ Accept = "application/json" }
    } catch {
        return $null
    }

    if (-not $response -or -not $response.data) { return $null }

    $free = foreach ($model in $response.data) {
        $promptPrice = "$($model.pricing.prompt)"
        $completionPrice = "$($model.pricing.completion)"
        # "0" means free. Some entries use "0.0" or an empty string.
        $isFree = ($promptPrice -match '^0(\.0+)?$') -and ($completionPrice -match '^0(\.0+)?$')
        if (-not $isFree) { continue }

        # Windows PowerShell 5.1 has no ?? operator, so use an explicit check.
        $contextLength = 0
        if ($null -ne $model.context_length) { $contextLength = [int]$model.context_length }

        [pscustomobject]@{
            Id              = $model.id
            Name            = if ($model.name) { $model.name } else { $model.id }
            ContextLength   = $contextLength
            PromptPrice     = $promptPrice
            CompletionPrice = $completionPrice
        }
    }

    return @($free | Sort-Object -Property @{ Expression = "ContextLength"; Descending = $true }, Id)
}

<#
    Lets the user pick an OpenRouter model.

    - Fetches the free catalogue and shows it as a numbered list.
    - Offers "manual" to type any model id (for paid models or when offline).
    - Offers "keep" to leave the current value untouched.
    - Returns the chosen model id, or the current value when kept.
#>
function Select-OpenRouterModel {
    param([string]$Current = "")

    Write-Host ""
    Write-Host "    Fetching the free model catalogue from OpenRouter..." -ForegroundColor Gray
    $models = Get-OpenRouterFreeModels

    if ($null -eq $models) {
        Write-Warn "Could not reach https://openrouter.ai/api/v1/models."
        Write-Note "Check your connection, or type a model id by hand."
        $manual = Read-Text -Prompt "OpenRouter model id" -Default $Current
        return $manual
    }

    if ($models.Count -eq 0) {
        Write-Warn "The catalogue returned no free models right now."
        $manual = Read-Text -Prompt "OpenRouter model id" -Default $Current
        return $manual
    }

    Write-Ok "$($models.Count) free models available"

    # The default is the model the project ships with. It is marked in the list
    # and pressing Enter picks it.
    $defaultModel = "stealth/crouton-alpha"
    $defaultIndex = 0
    for ($i = 0; $i -lt $models.Count; $i++) {
        if ($models[$i].Id -eq $defaultModel) { $defaultIndex = $i + 1; break }
    }
    if ($defaultIndex -eq 0 -and $Current) {
        for ($i = 0; $i -lt $models.Count; $i++) {
            if ($models[$i].Id -eq $Current) { $defaultIndex = $i + 1; break }
        }
    }
    if ($defaultIndex -eq 0) { $defaultIndex = 1 }

    Write-Host ""
    Write-Host "      Large-context free models are marked 1M / 256k." -ForegroundColor DarkGray
    Write-Host ""

    $index = 1
    foreach ($model in $models) {
        $context = if ($model.ContextLength -gt 0) { "{0:N0}k ctx" -f ($model.ContextLength / 1000) } else { "ctx ?" }
        $isDefault = ($index -eq $defaultIndex)
        $isCurrent = ($Current -and $model.Id -eq $Current)

        $marker = "   "
        if ($isDefault) { $marker = " * " }
        Write-Host ("      [{0,2}]  " -f $index) -ForegroundColor Magenta -NoNewline
        Write-Host ("{0}" -f $model.Id) -ForegroundColor $(if ($isDefault) { "Green" } else { "White" }) -NoNewline
        Write-Host ("  ({0})" -f $context) -ForegroundColor DarkGray -NoNewline
        if ($isCurrent) { Write-Host "  <- current" -ForegroundColor Cyan } else { Write-Host "" }
        if ($model.Name -ne $model.Id) {
            Write-Host ("            {0}" -f $model.Name) -ForegroundColor DarkGray
        }
        $index++
    }

    Write-Host ""
    Write-Host "      *  default for this project" -ForegroundColor DarkGray
    Write-Host "      [ m]  type a model id by hand" -ForegroundColor DarkGray
    if ($Current) {
        Write-Host "      [ k]  keep the current value ($Current)" -ForegroundColor DarkGray
    }
    Write-Host ""

    while ($true) {
        $answer = Read-Host "    Choose a model by number (Enter = $defaultModel)"
        if ([string]::IsNullOrWhiteSpace($answer)) {
            return $models[$defaultIndex - 1].Id
        }
        $answer = $answer.Trim().ToLower()

        if ($answer -eq "k" -and $Current) { return $Current }
        if ($answer -eq "m") {
            return (Read-Text -Prompt "OpenRouter model id" -Default $Current)
        }
        if ($answer -match '^\d+$') {
            $position = [int]$answer
            if ($position -ge 1 -and $position -le $models.Count) {
                return $models[$position - 1].Id
            }
        }
        Write-Warn "Enter a number between 1 and $($models.Count), 'm', or 'k'."
    }
}

<#
    Quick, non-interactive probe used by the status views: does the configured
    model still exist in the catalogue and is it still free?
#>
function Test-OpenRouterModel {
    param([string]$ModelId)
    if ([string]::IsNullOrWhiteSpace($ModelId)) { return $null }
    $models = Get-OpenRouterFreeModels
    if ($null -eq $models) { return $null }
    $match = $models | Where-Object { $_.Id -eq $ModelId } | Select-Object -First 1
    if ($match) { return "free" }
    return "not-free-or-unknown"
}
