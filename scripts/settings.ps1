<#
.SYNOPSIS
    MarketPulse AI - settings manager.

.DESCRIPTION
    View and change everything the app is configured with, without editing files
    by hand: the database connection, the backend port, the OpenRouter key and
    model (chosen from the live free catalogue), the AI assistant provider and
    its key, the X/Twitter token, and the Reddit user agent.

    Every change is written to backend/.env or .env.local. Secrets are masked
    on screen and never printed in full.

.EXAMPLE
    .\scripts\settings.ps1

.EXAMPLE
    .\scripts\settings.ps1 -Show
#>
[CmdletBinding()]
param(
    [switch]$Show
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

. (Join-Path $PSScriptRoot "lib.ps1")
$global:MP_NONINTERACTIVE = $false

$BackendEnv = Join-Path $Root "backend\.env"
$FrontendEnv = Join-Path $Root ".env.local"

function Test-Configured {
    if (-not (Test-Path $BackendEnv)) {
        Write-Fail "backend/.env does not exist. Run scripts/setup.ps1 first."
        return $false
    }
    return $true
}

function Show-Settings {
    Write-Step "Current settings"

    if (-not (Test-Path $BackendEnv)) {
        Write-Fail "backend/.env does not exist. Run scripts/setup.ps1 first."
        return
    }

    $databaseUrl = Get-EnvValue -Path $BackendEnv -Key "DATABASE_URL"
    $port = Get-EnvValue -Path $BackendEnv -Key "PORT"
    $openRouterKey = Get-EnvValue -Path $BackendEnv -Key "OPENROUTER_API_KEY"
    $openRouterModel = Get-EnvValue -Path $BackendEnv -Key "OPENROUTER_MODEL"
    $provider = Get-EnvValue -Path $BackendEnv -Key "AI_PROVIDER"
    $groqKey = Get-EnvValue -Path $BackendEnv -Key "GROQ_API_KEY"
    $geminiKey = Get-EnvValue -Path $BackendEnv -Key "GEMINI_API_KEY"
    $ollamaUrl = Get-EnvValue -Path $BackendEnv -Key "OLLAMA_URL"
    $twitter = Get-EnvValue -Path $BackendEnv -Key "TWITTER_BEARER_TOKEN"
    $redditUa = Get-EnvValue -Path $BackendEnv -Key "REDDIT_USER_AGENT"
    $frontendUrl = Get-EnvValue -Path $FrontendEnv -Key "VITE_API_URL"
    $aiUrl = Get-EnvValue -Path $FrontendEnv -Key "VITE_AI_API_URL"

    Write-Host ""
    Write-Host "  Database" -ForegroundColor White
    Write-Host "    DATABASE_URL        $($databaseUrl -replace '://[^@]+@', '://***@')" -ForegroundColor Gray
    Write-Host "    Backend port        $port" -ForegroundColor Gray
    Write-Host "    Frontend API URL    $frontendUrl" -ForegroundColor Gray

    Write-Host ""
    Write-Host "  LLM (OpenRouter)" -ForegroundColor White
    Write-Host "    API key             $(Mask $openRouterKey)" -ForegroundColor Gray
    Write-Host "    Model               $(if ($openRouterModel) { $openRouterModel } else { '(none - LLM disabled)' })" -ForegroundColor Gray

    Write-Host ""
    Write-Host "  AI assistant" -ForegroundColor White
    Write-Host "    Provider            $(if ($provider) { $provider } else { '(not set)' })" -ForegroundColor Gray
    switch ($provider) {
        "groq"   { Write-Host "    Groq key            $(Mask $groqKey)" -ForegroundColor Gray }
        "gemini" { Write-Host "    Gemini key          $(Mask $geminiKey)" -ForegroundColor Gray }
        "ollama" { Write-Host "    Ollama URL          $ollamaUrl" -ForegroundColor Gray }
    }
    Write-Host "    Frontend AI URL     $(if ($aiUrl) { $aiUrl } else { '(empty - assistant hidden)' })" -ForegroundColor Gray

    Write-Host ""
    Write-Host "  Data sources" -ForegroundColor White
    Write-Host "    X/Twitter token     $(Mask $twitter)" -ForegroundColor Gray
    Write-Host "    Reddit User-Agent   $redditUa" -ForegroundColor Gray
    Write-Host "    eMAG / Google Trends / Hacker News   no key needed" -ForegroundColor DarkGray

    Write-Host ""
    Write-Host "  Files" -ForegroundColor White
    Write-Host "    backend/.env        $(if (Test-Path $BackendEnv) { 'present' } else { 'missing' })" -ForegroundColor Gray
    Write-Host "    .env.local          $(if (Test-Path $FrontendEnv) { 'present' } else { 'missing' })" -ForegroundColor Gray
    Write-Host ""
}

# --------------------------------------------------------------------------- #
# Individual editors
# --------------------------------------------------------------------------- #

function Edit-Database {
    Write-Step "Database connection"
    $current = Get-EnvValue -Path $BackendEnv -Key "DATABASE_URL"
    Write-Note "Current: $($current -replace '://[^@]+@', '://***@')"
    Write-Host ""
    Write-Host "      [1]  Docker container (127.0.0.1:3307)" -ForegroundColor Gray
    Write-Host "      [2]  Native MySQL on this machine (127.0.0.1:3306)" -ForegroundColor Gray
    Write-Host "      [3]  Another server (host, port, user, password)" -ForegroundColor Gray
    Write-Host "      [4]  Back" -ForegroundColor DarkGray
    Write-Host ""

    $choice = Read-Choice -Prompt "Which database?" -Options @("1", "2", "3", "4") -Default "4"
    switch ($choice) {
        "1" {
            Set-EnvValue -Path $BackendEnv -Key "DATABASE_URL" -Value "mysql+pymysql://marketpulse:marketpulse@127.0.0.1:3307/marketpulse"
            Write-Ok "DATABASE_URL -> 127.0.0.1:3307/marketpulse"
            Write-Note "Start the container with: docker compose up -d"
        }
        "2" {
            $user = Read-Text -Prompt "MySQL user" -Default "root"
            $password = Read-Secret -Prompt "MySQL password"
            $database = Read-Text -Prompt "Database name" -Default "marketpulse"
            Set-EnvValue -Path $BackendEnv -Key "DATABASE_URL" -Value "mysql+pymysql://${user}:${password}@127.0.0.1:3306/${database}"
            Write-Ok "DATABASE_URL -> 127.0.0.1:3306/$database"
        }
        "3" {
            $hostName = Read-Text -Prompt "MySQL host" -Default "127.0.0.1"
            $port = Read-Number -Prompt "MySQL port" -Default 3306 -Min 1 -Max 65535
            $user = Read-Text -Prompt "MySQL user" -Default "marketpulse"
            $password = Read-Secret -Prompt "MySQL password"
            $database = Read-Text -Prompt "Database name" -Default "marketpulse"
            Set-EnvValue -Path $BackendEnv -Key "DATABASE_URL" -Value "mysql+pymysql://${user}:${password}@${hostName}:${port}/${database}"
            Write-Ok "DATABASE_URL -> ${hostName}:${port}/$database"
        }
        default { return }
    }
}

function Edit-Port {
    Write-Step "Backend port"
    $current = Get-EnvValue -Path $BackendEnv -Key "PORT"
    if (-not $current) { $current = "8010" }

    if (Test-Port -Port ([int]$current)) {
        Write-Warn "Port $current is currently in use."
        $free = Find-FreePort -Start ([int]$current + 1)
        if ($free) { Write-Note "The next free port is $free." }
    } else {
        Write-Ok "Port $current is free"
    }

    $port = Read-Number -Prompt "Backend port" -Default ([int]$current) -Min 1024 -Max 65535
    if (Test-Port -Port $port) {
        Write-Warn "Port $port is already in use. The backend will fail to start until it is free."
    }
    Set-EnvValue -Path $BackendEnv -Key "PORT" -Value "$port"
    Set-EnvValue -Path $FrontendEnv -Key "VITE_API_URL" -Value "http://localhost:$port"
    Write-Ok "Backend port -> $port (VITE_API_URL updated)"
}

function Edit-OpenRouter {
    Write-Step "OpenRouter (LLM)"
    $currentKey = Get-EnvValue -Path $BackendEnv -Key "OPENROUTER_API_KEY"
    $currentModel = Get-EnvValue -Path $BackendEnv -Key "OPENROUTER_MODEL"
    if (-not $currentModel) { $currentModel = "dots-studio/dots-3-note-preview:free" }

    Write-Note "Key:   $(Mask $currentKey)"
    Write-Note "Model: $currentModel"
    Write-Host ""
    Write-Host "      [1]  Set or replace the API key" -ForegroundColor Gray
    Write-Host "      [2]  Choose a free model from the live catalogue" -ForegroundColor Gray
    Write-Host "      [3]  Clear the key and the model (disable the LLM)" -ForegroundColor Gray
    Write-Host "      [4]  Back" -ForegroundColor DarkGray
    Write-Host ""

    $choice = Read-Choice -Prompt "What do you want to change?" -Options @("1", "2", "3", "4") -Default "4"
    switch ($choice) {
        "1" {
            $key = Read-Secret -Prompt "OpenRouter API key" -Default $currentKey
            if ($key) {
                Set-EnvValue -Path $BackendEnv -Key "OPENROUTER_API_KEY" -Value $key
                Write-Ok "Key saved ($(Mask $key))"
                if (-not $currentModel) {
                    Write-Note "No model set yet; choose one with option 2."
                }
            } else {
                Write-Note "Unchanged."
            }
        }
        "2" {
            $model = Select-OpenRouterModel -Current $currentModel
            if ($model) {
                Set-EnvValue -Path $BackendEnv -Key "OPENROUTER_MODEL" -Value $model
                Write-Ok "Model -> $model"
                if (-not $currentKey) {
                    Write-Warn "No API key set; the LLM stays off until OPENROUTER_API_KEY is filled."
                }
            }
        }
        "3" {
            Set-EnvValue -Path $BackendEnv -Key "OPENROUTER_API_KEY" -Value ""
            Set-EnvValue -Path $BackendEnv -Key "OPENROUTER_MODEL" -Value ""
            Write-Ok "LLM disabled; the AI surfaces will report source=derived"
        }
        default { return }
    }
}

function Edit-Assistant {
    Write-Step "AI assistant (backend/server.py)"
    $currentProvider = Get-EnvValue -Path $BackendEnv -Key "AI_PROVIDER"
    if (-not $currentProvider) { $currentProvider = "openrouter" }
    $openRouterKey = Get-EnvValue -Path $BackendEnv -Key "OPENROUTER_API_KEY"
    $openRouterModel = Get-EnvValue -Path $BackendEnv -Key "OPENROUTER_MODEL"

    Write-Note "Current provider: $currentProvider"
    if ($currentProvider -eq "openrouter") {
        Write-Note "Uses OPENROUTER_API_KEY ($(Mask $openRouterKey)) and model $(if ($openRouterModel) { $openRouterModel } else { '(none)' })"
    }
    Write-Host ""
    Write-Host "      [1]  openrouter  reuses the OpenRouter key and model  (default)" -ForegroundColor Gray
    Write-Host "      [2]  ollama      local, no key" -ForegroundColor Gray
    Write-Host "      [3]  groq        free key" -ForegroundColor Gray
    Write-Host "      [4]  gemini      free key" -ForegroundColor Gray
    Write-Host "      [5]  Disable the assistant" -ForegroundColor Gray
    Write-Host "      [6]  Back" -ForegroundColor DarkGray
    Write-Host ""

    $choice = Read-Choice -Prompt "Which provider?" -Options @("1", "2", "3", "4", "5", "6") -Default "6"
    switch ($choice) {
        "1" {
            Set-EnvValue -Path $BackendEnv -Key "AI_PROVIDER" -Value "openrouter"
            Set-AssistantUrl
            if ($openRouterKey) {
                Write-Ok "Assistant -> openrouter, model $(if ($openRouterModel) { $openRouterModel } else { '(none)' })"
            } else {
                Write-Warn "No OpenRouter key yet; set one with option 4 in the main menu."
            }
        }
        "2" {
            $url = Read-Text -Prompt "Ollama URL" -Default $(if (Get-EnvValue -Path $BackendEnv -Key "OLLAMA_URL") { Get-EnvValue -Path $BackendEnv -Key "OLLAMA_URL" } else { "http://localhost:11434" })
            Set-EnvValue -Path $BackendEnv -Key "AI_PROVIDER" -Value "ollama"
            Set-EnvValue -Path $BackendEnv -Key "OLLAMA_URL" -Value $url
            Set-AssistantUrl
            Write-Ok "Assistant -> ollama at $url"
            Write-Note "Pull a model once: ollama pull llama3.2"
        }
        "3" {
            $key = Read-Secret -Prompt "Groq API key" -Default (Get-EnvValue -Path $BackendEnv -Key "GROQ_API_KEY")
            Set-EnvValue -Path $BackendEnv -Key "AI_PROVIDER" -Value "groq"
            if ($key) { Set-EnvValue -Path $BackendEnv -Key "GROQ_API_KEY" -Value $key; Write-Ok "Groq key saved ($(Mask $key))" }
            else { Write-Warn "No key; the assistant will fail until GROQ_API_KEY is set." }
            Set-AssistantUrl
            Write-Ok "Assistant -> groq"
        }
        "4" {
            $key = Read-Secret -Prompt "Gemini API key" -Default (Get-EnvValue -Path $BackendEnv -Key "GEMINI_API_KEY")
            Set-EnvValue -Path $BackendEnv -Key "AI_PROVIDER" -Value "gemini"
            if ($key) { Set-EnvValue -Path $BackendEnv -Key "GEMINI_API_KEY" -Value $key; Write-Ok "Gemini key saved ($(Mask $key))" }
            else { Write-Warn "No key; the assistant will fail until GEMINI_API_KEY is set." }
            Set-AssistantUrl
            Write-Ok "Assistant -> gemini"
        }
        "5" {
            Set-EnvValue -Path $BackendEnv -Key "AI_PROVIDER" -Value ""
            Set-EnvValue -Path $FrontendEnv -Key "VITE_AI_API_URL" -Value ""
            Write-Ok "Assistant disabled"
        }
        default { return }
    }
}

function Set-AssistantUrl {
    $current = Get-EnvValue -Path $FrontendEnv -Key "VITE_AI_API_URL"
    if ($current) { return }
    $port = Read-Number -Prompt "AI assistant port (server.py)" -Default 8020 -Min 1024 -Max 65535
    Set-EnvValue -Path $FrontendEnv -Key "VITE_AI_API_URL" -Value "http://localhost:$port"
}

function Edit-Twitter {
    Write-Step "X / Twitter"
    $current = Get-EnvValue -Path $BackendEnv -Key "TWITTER_BEARER_TOKEN"
    Write-Note "Token: $(Mask $current)"
    Write-Note "Get one at https://developer.x.com/en/portal/dashboard"
    $token = Read-Secret -Prompt "Bearer token (Enter keeps the current value, '-' clears it)" -Default $current
    if ($token -eq "-") {
        Set-EnvValue -Path $BackendEnv -Key "TWITTER_BEARER_TOKEN" -Value ""
        Write-Ok "Token cleared"
    } elseif ($token -and $token -ne $current) {
        Set-EnvValue -Path $BackendEnv -Key "TWITTER_BEARER_TOKEN" -Value $token
        Write-Ok "Token saved ($(Mask $token))"
    } else {
        Write-Note "Unchanged."
    }
}

function Edit-Reddit {
    Write-Step "Reddit"
    Write-Note "The connector uses the public .json endpoints, so no key is needed."
    $current = Get-EnvValue -Path $BackendEnv -Key "REDDIT_USER_AGENT"
    $ua = Read-Text -Prompt "User-Agent" -Default $(if ($current) { $current } else { "MarketPulseAI/1.0 by MarketPulseTeam" })
    Set-EnvValue -Path $BackendEnv -Key "REDDIT_USER_AGENT" -Value $ua
    Write-Ok "User-Agent -> $ua"
}

function Test-Connections {
    Write-Step "Checking the configuration"

    $databaseUrl = Get-EnvValue -Path $BackendEnv -Key "DATABASE_URL"
    if ($databaseUrl -match '^mysql\+pymysql://([^:]+):([^@]*)@([^:]+):(\d+)/(.+)$') {
        $user = $Matches[1]; $password = $Matches[2]; $hostName = $Matches[3]; $port = $Matches[4]; $database = $Matches[5]
        Write-Note "MySQL $hostName`:$port as $user"

        if ($databaseUrl -match ':3307/') {
            if (Get-Command docker -ErrorAction SilentlyContinue) {
                $status = (docker inspect --format "{{.State.Health.Status}}" marketpulse-mysql 2>$null)
                if ($status -eq "healthy") { Write-Ok "Docker container healthy" }
                else { Write-Fail "Docker container is not healthy (docker compose up -d)" }
            }
        }

        if (Get-Command mysql -ErrorAction SilentlyContinue) {
            $env:MYSQL_PWD = $password
            try {
                $probe = mysql -h $hostName -P $port -u $user -e "SELECT 1;" 2>&1
                if ($LASTEXITCODE -eq 0) { Write-Ok "MySQL answers and the credentials work" }
                else { Write-Fail "MySQL did not answer: $probe" }
            } finally {
                Remove-Item Env:\MYSQL_PWD -ErrorAction SilentlyContinue
            }
        } else {
            Write-Note "The mysql client is not on PATH; skipped the direct probe."
        }
    } else {
        Write-Fail "DATABASE_URL is not a mysql+pymysql:// URL"
    }

    $port = Get-EnvValue -Path $BackendEnv -Key "PORT"
    if ($port -and (Test-Port -Port ([int]$port))) {
        Write-Ok "Something is listening on the backend port $port"
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:$port/health" -TimeoutSec 3
            Write-Ok "API health: database=$($health.database), llm=$($health.llm)"
        } catch {
            Write-Note "Port $port is busy but /health did not answer; it may be another service."
        }
    } else {
        Write-Note "The backend is not running on port $port."
    }

    $model = Get-EnvValue -Path $BackendEnv -Key "OPENROUTER_MODEL"
    if ($model) {
        $state = Test-OpenRouterModel -ModelId $model
        switch ($state) {
            "free" { Write-Ok "OpenRouter model '$model' is free and available" }
            "not-free-or-unknown" { Write-Warn "OpenRouter model '$model' is not in the free list (paid, renamed, or removed)" }
            default { Write-Note "Could not reach the OpenRouter catalogue." }
        }
    }
}

# --------------------------------------------------------------------------- #
# Menu
# --------------------------------------------------------------------------- #

if ($Show) {
    Show-Settings
    exit 0
}

if (-not (Test-Configured)) { exit 1 }

$options = @(
    @{ Key = "1"; Label = "Show        everything currently configured";       Action = { Show-Settings } },
    @{ Key = "2"; Label = "Database    Docker, native MySQL, or another host"; Action = { Edit-Database } },
    @{ Key = "3"; Label = "Port        the backend port and VITE_API_URL";     Action = { Edit-Port } },
    @{ Key = "4"; Label = "OpenRouter  key and free model";                    Action = { Edit-OpenRouter } },
    @{ Key = "5"; Label = "Assistant   ollama / groq / gemini / off";          Action = { Edit-Assistant } },
    @{ Key = "6"; Label = "X/Twitter   bearer token";                          Action = { Edit-Twitter } },
    @{ Key = "7"; Label = "Reddit      user agent";                            Action = { Edit-Reddit } },
    @{ Key = "8"; Label = "Check       verify the database, the port, the model"; Action = { Test-Connections } },
    @{ Key = "q"; Label = "Back";                                              Action = { $null } }
)

while ($true) {
    Clear-Host
    Write-Host ""
    Write-Host "  MarketPulse AI - settings" -ForegroundColor Magenta
    Write-Host "  $Root" -ForegroundColor DarkGray
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
        Write-Warn "Unknown option: $choice"
        Start-Sleep -Seconds 1
        continue
    }
    if ($selected.Key -eq "q") { break }

    $needsRestart = $false
    $reloadable = $false
    try {
        & $selected.Action
        # API keys and the LLM model are reloadable: the admin endpoint re-reads
        # backend/.env and rebuilds the LLM client, so a running server picks the
        # change up without dropping its database connections.
        $reloadable = $selected.Key -in @("4", "5", "6", "7")
        # The database URL and the port are bound at startup and cannot be
        # swapped under live connections.
        $needsRestart = $selected.Key -in @("2", "3")
    } catch {
        Write-Fail "The action failed: $($_.Exception.Message)"
    }

    $port = Get-EnvValue -Path $BackendEnv -Key "PORT"
    if (-not $port) { $port = "8010" }

    if ($reloadable) {
        $assistantUrl = Get-EnvValue -Path $FrontendEnv -Key "VITE_AI_API_URL"
        $result = Invoke-ApiReload -BackendPort ([int]$port) -AssistantUrl $assistantUrl
        if ($result -eq "not-running") {
            Write-Note "Neither service is running; the change applies the next time you start them."
        } elseif ($result -eq "failed") {
            Write-Note "Restart the app to be sure the change is applied."
        }
    }

    if ($needsRestart) {
        Invoke-RestartPrompt -Reason "This setting is bound when the backend starts." -BackendPort ([int]$port) -FrontendPort 5173 -Root $Root
    }

    Write-Host ""
    Read-Host "  Press Enter to return to the menu" | Out-Null
}

Write-Host ""
Write-Host "  Done." -ForegroundColor DarkGray
Write-Host ""
