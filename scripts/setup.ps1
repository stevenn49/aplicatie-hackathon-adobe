<#
.SYNOPSIS
    Cold setup for MarketPulse AI on Windows.

.DESCRIPTION
    Checks the toolchain, detects the available MySQL options (Docker and/or a
    native install) and lets you pick one, asks for the API keys you want to
    enable, writes backend/.env and .env.local, installs the dependencies and
    optionally starts the stack.

    Every step checks before acting, so the script is safe to run again.

.PARAMETER Database
    "auto" (default) detects what is available and asks. "docker" or "native"
    skip the question.

.PARAMETER NonInteractive
    Take every default, ask nothing. API keys are left empty. Useful for CI.

.PARAMETER Start
    Start the stack when setup finishes, without asking.

.PARAMETER DbHost
    Native MySQL host. Default 127.0.0.1.

.PARAMETER DbPort
    Native MySQL port. Default 3306.

.PARAMETER DbUser
    Native MySQL user. Default root.

.PARAMETER DbPassword
    Native MySQL password. Default empty (prompted in interactive mode).

.PARAMETER DbName
    Database name. Default marketpulse.

.EXAMPLE
    .\scripts\setup.ps1

.EXAMPLE
    .\scripts\setup.ps1 -Database native -DbUser root -DbPassword secret

.EXAMPLE
    .\scripts\setup.ps1 -NonInteractive -Start
#>
[CmdletBinding()]
param(
    [ValidateSet("auto", "docker", "native")]
    [string]$Database = "auto",
    [switch]$NonInteractive,
    [switch]$Start,
    [string]$DbHost = "127.0.0.1",
    [int]$DbPort = 3306,
    [string]$DbUser = "root",
    [string]$DbPassword = "",
    [string]$DbName = "marketpulse"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

# Shared helpers: output, prompts, .env read/write, port checks, OpenRouter models.
. (Join-Path $PSScriptRoot "lib.ps1")
$global:MP_NONINTERACTIVE = [bool]$NonInteractive

# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #

Write-Host @"
MarketPulse AI - cold setup
Repository: $Root
"@ -ForegroundColor White

# --------------------------------------------------------------------------- #
# 1. Toolchain
# --------------------------------------------------------------------------- #

Write-Step "Checking the toolchain"
$missing = @()

try { Write-Ok "Node $(node --version)" } catch { $missing += "Node.js 18+  https://nodejs.org" }
try { Write-Ok "npm $(npm --version)" } catch { $missing += "npm (ships with Node.js)" }
try { Write-Ok "Python $(python --version)" } catch { $missing += "Python 3.11+  https://python.org" }

$dockerCli = $null
try { $dockerCli = (docker --version) 2>$null } catch { $dockerCli = $null }
$dockerRunning = $false
if ($dockerCli) {
    try {
        $daemon = (docker info --format "{{.ServerVersion}}" 2>$null)
        if ($daemon) { $dockerRunning = $true }
    } catch { $dockerRunning = $false }
}

$mysqlCli = $null
try { $mysqlCli = (Get-Command mysql -ErrorAction Stop).Source } catch { $mysqlCli = $null }
$mysqlListening = Test-Port -Port 3306

if ($missing.Count -gt 0) {
    Write-Host "`nMissing prerequisites:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Host "`nInstall them and run this script again." -ForegroundColor Yellow
    exit 1
}

# --------------------------------------------------------------------------- #
# 2. Database: detect, then let the user choose
# --------------------------------------------------------------------------- #

Write-Step "Looking for a MySQL database"

$dockerAvailable = $dockerRunning
$nativeAvailable = [bool]($mysqlCli -and $mysqlListening)

if ($dockerAvailable) { Write-Ok "Docker is running (MySQL 8.4 can run in a container on port 3307)" }
elseif ($dockerCli) { Write-Warn "Docker is installed but the daemon is not running" }
else { Write-Note "Docker is not installed" }

if ($nativeAvailable) { Write-Ok "A MySQL server is listening on 127.0.0.1:3306" }
elseif ($mysqlCli) { Write-Warn "The mysql client is installed but nothing answers on 127.0.0.1:3306" }
else { Write-Note "No native MySQL client on PATH" }

$mode = $Database
if ($mode -eq "auto") {
    if ($dockerAvailable -and $nativeAvailable) {
        Write-Host ""
        Write-Host "    Both options are available." -ForegroundColor White
        Write-Host "      docker  - MySQL 8.4 in a container on port 3307, nothing installed on your system" -ForegroundColor Gray
        Write-Host "      native  - the MySQL already running on your machine, port 3306" -ForegroundColor Gray
        $mode = Read-Choice -Prompt "Which database should the app use?" -Options @("docker", "native") -Default "docker"
    } elseif ($dockerAvailable) {
        $mode = "docker"
        Write-Ok "Using Docker (the only option available)"
    } elseif ($nativeAvailable) {
        $mode = "native"
        Write-Ok "Using the native MySQL server (the only option available)"
    } else {
        Write-Fail "No MySQL available."
        Write-Host "    Install Docker Desktop: https://docker.com/products/docker-desktop" -ForegroundColor Yellow
        Write-Host "    or install MySQL 8:     https://dev.mysql.com/downloads/installer/" -ForegroundColor Yellow
        Write-Host "    then run this script again." -ForegroundColor Yellow
        exit 1
    }
}

if ($mode -eq "docker" -and -not $dockerAvailable) {
    Write-Fail "-Database docker was requested but the Docker daemon is not running."
    exit 1
}
if ($mode -eq "native" -and -not $nativeAvailable) {
    Write-Warn "Nothing answers on 127.0.0.1:3306; continuing so you can point at a remote server."
}

if ($mode -eq "docker") {
    Write-Step "Starting the MySQL container"
    docker compose up -d | Out-Null
    Write-Note "Waiting for MySQL to become healthy..."
    $healthy = $false
    for ($i = 0; $i -lt 60; $i++) {
        $status = (docker inspect --format "{{.State.Health.Status}}" marketpulse-mysql 2>$null)
        if ($status -eq "healthy") { $healthy = $true; break }
        Start-Sleep -Seconds 2
    }
    if (-not $healthy) {
        Write-Fail "The container did not become healthy. Run: docker compose logs mysql"
        exit 1
    }
    Write-Ok "MySQL container healthy on 127.0.0.1:3307"
    $dbUser = "marketpulse"
    $dbPassword = "marketpulse"
    $dbHost = "127.0.0.1"
    $dbPort = 3307
} else {
    Write-Step "Configuring the native MySQL connection"
    $dbHost = Read-Text -Prompt "MySQL host" -Default $DbHost
    $portText = Read-Text -Prompt "MySQL port" -Default "$DbPort"
    if ($portText -match '^\d+$') { $DbPort = [int]$portText }
    $dbUser = Read-Text -Prompt "MySQL user" -Default $DbUser
    $dbPassword = Read-Secret -Prompt "MySQL password" -Default $DbPassword

    $env:MYSQL_PWD = $dbPassword
    try {
        $probe = (mysql -h $dbHost -P $DbPort -u $dbUser -e "SELECT 1;" 2>&1)
        if ($LASTEXITCODE -ne 0) { throw ($probe | Out-String) }
        Write-Ok "Connected to MySQL at $dbHost`:$DbPort"
        mysql -h $dbHost -P $DbPort -u $dbUser -e "CREATE DATABASE IF NOT EXISTS ``$DbName`` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Could not create the database $DbName" }
        Write-Ok "Database '$DbName' ready"
    } catch {
        Write-Fail "Cannot connect to MySQL at $dbHost`:$DbPort as $dbUser"
        Write-Note "Create the database and user manually, then re-run:"
        Write-Note "  CREATE DATABASE $DbName CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        Write-Note "  CREATE USER '$dbUser'@'%' IDENTIFIED BY '<password>';"
        Write-Note "  GRANT ALL PRIVILEGES ON $DbName.* TO '$dbUser'@'%';"
        exit 1
    } finally {
        Remove-Item Env:\MYSQL_PWD -ErrorAction SilentlyContinue
    }
}

# The test suite creates and drops its own database, so the user needs CREATE.
# mysql writes its password warning to stderr; with ErrorActionPreference=Stop
# PowerShell would treat that as a fatal error, so it is silenced explicitly.
if ($mode -eq "docker") {
    $grantSql = "GRANT ALL PRIVILEGES ON $($DbName)_test.* TO 'marketpulse'@'%'; FLUSH PRIVILEGES;"
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $grantSql | docker exec -i marketpulse-mysql mysql -u root -pmarketpulse_root 2>&1 | Out-Null
    } catch {
        Write-Warn "Could not grant the test-database privilege; the test suite may be skipped."
    } finally {
        $ErrorActionPreference = $previousPreference
    }
}

$databaseUrl = "mysql+pymysql://${dbUser}:${dbPassword}@${dbHost}:${dbPort}/${DbName}"

# --------------------------------------------------------------------------- #
# 3. Environment files
# --------------------------------------------------------------------------- #

Write-Step "Writing backend/.env"
$backendEnv = Join-Path $Root "backend\.env"
if (-not (Test-Path $backendEnv)) {
    Copy-Item (Join-Path $Root "backend\.env.example") $backendEnv
    Write-Ok "Created from backend/.env.example"
} else {
    Write-Ok "Keeping the existing file"
}
Set-EnvValue -Path $backendEnv -Key "DATABASE_URL" -Value $databaseUrl
Write-Ok "DATABASE_URL -> $($databaseUrl.Split('@')[1])"

# --------------------------------------------------------------------------- #
# 4. API keys
# --------------------------------------------------------------------------- #

Write-Host @"

==> API keys

    Everything below is optional. The dashboard runs without any of them; each
    one only enables a specific feature. Press Enter to skip a key.

    No key needed (already working):
      eMAG            public catalogue, HTML parsing
      Reddit          public .json endpoints
      Google Trends   pytrends
      Hacker News     Algolia search API

"@ -ForegroundColor Cyan

$currentOpenRouterKey = Get-EnvValue -Path $backendEnv -Key "OPENROUTER_API_KEY"
$currentOpenRouterModel = Get-EnvValue -Path $backendEnv -Key "OPENROUTER_MODEL"
if (-not $currentOpenRouterModel) { $currentOpenRouterModel = "stealth/crouton-alpha" }

Write-Host "    OpenRouter - powers the executive summary, the review summary and" -ForegroundColor White
Write-Host "                 the marketing opportunities. Free models available." -ForegroundColor Gray
Write-Host "                 https://openrouter.ai/keys" -ForegroundColor DarkGray
$openRouterKey = Read-Secret -Prompt "OpenRouter API key" -Default $currentOpenRouterKey
if ($openRouterKey) {
    # The catalogue is public, so the free models can be listed before the key
    # is ever used. Choosing from it avoids typos in model ids.
    $model = Select-OpenRouterModel -Current $currentOpenRouterModel
    if (-not $model) {
        Write-Warn "No model chosen. The key is saved but the LLM stays off until OPENROUTER_MODEL is set."
    }
    Set-EnvValue -Path $backendEnv -Key "OPENROUTER_API_KEY" -Value $openRouterKey
    Set-EnvValue -Path $backendEnv -Key "OPENROUTER_MODEL" -Value $model
    Write-Ok "OpenRouter configured ($(Mask $openRouterKey)), model: $(if ($model) { $model } else { '(none)' })"
} else {
    Write-Note "Skipped. AI surfaces will report source=derived."
}

Write-Host ""
Write-Host "    AI assistant (the Ask AI panel) - a separate service in backend/server.py." -ForegroundColor White
Write-Host "      ollama  runs locally, no key, needs https://ollama.com" -ForegroundColor Gray
Write-Host "      groq    free key, fast          https://console.groq.com/keys" -ForegroundColor Gray
Write-Host "      gemini  free key                https://aistudio.google.com/apikey" -ForegroundColor Gray
Write-Host "      off     do not enable the assistant" -ForegroundColor Gray
$currentProvider = Get-EnvValue -Path $backendEnv -Key "AI_PROVIDER"
if (-not $currentProvider) { $currentProvider = "ollama" }
$provider = Read-Choice -Prompt "Assistant provider" -Options @("ollama", "groq", "gemini", "off") -Default $(if ($NonInteractive) { "off" } else { $currentProvider })

if ($provider -ne "off") {
    Set-EnvValue -Path $backendEnv -Key "AI_PROVIDER" -Value $provider
    if ($provider -eq "groq") {
        $groqKey = Read-Secret -Prompt "Groq API key" -Default (Get-EnvValue -Path $backendEnv -Key "GROQ_API_KEY")
        if ($groqKey) { Set-EnvValue -Path $backendEnv -Key "GROQ_API_KEY" -Value $groqKey; Write-Ok "Groq configured ($(Mask $groqKey))" }
        else { Write-Warn "No Groq key; the assistant will fail until GROQ_API_KEY is set." }
    } elseif ($provider -eq "gemini") {
        $geminiKey = Read-Secret -Prompt "Gemini API key" -Default (Get-EnvValue -Path $backendEnv -Key "GEMINI_API_KEY")
        if ($geminiKey) { Set-EnvValue -Path $backendEnv -Key "GEMINI_API_KEY" -Value $geminiKey; Write-Ok "Gemini configured ($(Mask $geminiKey))" }
        else { Write-Warn "No Gemini key; the assistant will fail until GEMINI_API_KEY is set." }
    } else {
        $ollamaUrl = Read-Text -Prompt "Ollama URL" -Default $(if (Get-EnvValue -Path $backendEnv -Key "OLLAMA_URL") { Get-EnvValue -Path $backendEnv -Key "OLLAMA_URL" } else { "http://localhost:11434" })
        Set-EnvValue -Path $backendEnv -Key "OLLAMA_URL" -Value $ollamaUrl
        Write-Ok "Ollama configured at $ollamaUrl"
        Write-Note "Pull a model once:  ollama pull llama3.2"
    }
    $aiPort = Read-Text -Prompt "AI assistant port (server.py)" -Default "8020"
    Set-EnvValue -Path $Root\.env.local -Key "VITE_AI_API_URL" -Value "http://localhost:$aiPort"
} else {
    Write-Note "Assistant disabled. VITE_AI_API_URL stays empty."
}

Write-Host ""
Write-Host "    X / Twitter - brand mention collection. Needs a bearer token." -ForegroundColor White
Write-Host "                  https://developer.x.com/en/portal/dashboard" -ForegroundColor DarkGray
$twitterToken = Read-Secret -Prompt "X/Twitter bearer token" -Default (Get-EnvValue -Path $backendEnv -Key "TWITTER_BEARER_TOKEN")
if ($twitterToken) {
    Set-EnvValue -Path $backendEnv -Key "TWITTER_BEARER_TOKEN" -Value $twitterToken
    Write-Ok "X/Twitter configured ($(Mask $twitterToken))"
} else {
    Write-Note "Skipped. The Twitter connector returns nothing until a token is set."
}

Write-Host ""
Write-Host "    Reddit - the connector uses the public .json endpoints, so no key is" -ForegroundColor White
Write-Host "             required. A descriptive User-Agent is recommended." -ForegroundColor Gray
$redditUa = Read-Text -Prompt "Reddit User-Agent" -Default $(if (Get-EnvValue -Path $backendEnv -Key "REDDIT_USER_AGENT") { Get-EnvValue -Path $backendEnv -Key "REDDIT_USER_AGENT" } else { "MarketPulseAI/1.0 by MarketPulseTeam" })
Set-EnvValue -Path $backendEnv -Key "REDDIT_USER_AGENT" -Value $redditUa
Write-Ok "Reddit User-Agent: $redditUa"

# --------------------------------------------------------------------------- #
# 5. Frontend environment
# --------------------------------------------------------------------------- #

Write-Step "Writing .env.local"
$frontendEnv = Join-Path $Root ".env.local"
if (-not (Test-Path $frontendEnv)) {
    Copy-Item (Join-Path $Root ".env.example") $frontendEnv
    Write-Ok "Created from .env.example"
} else {
    Write-Ok "Keeping the existing file"
}
$defaultPort = Get-EnvValue -Path $backendEnv -Key "PORT"
if (-not $defaultPort) { $defaultPort = "8010" }

# Port 8000 is taken by an unrelated service on some machines. If the configured
# port is busy, propose the next free one instead of writing a URL that will not
# answer.
if (Test-Port -Port ([int]$defaultPort)) {
    $free = [int]$defaultPort + 1
    while ($free -lt 8100 -and (Test-Port -Port $free)) { $free++ }
    Write-Warn "Port $defaultPort is already in use on this machine."
    Write-Note "Another service owns it; the backend would fail to bind."
    $defaultPort = "$free"
    Write-Note "Suggesting $free instead."
}

$backendPort = Read-Text -Prompt "Backend port" -Default $defaultPort
if (Test-Port -Port ([int]$backendPort)) {
    Write-Warn "Port $backendPort is already in use. The backend will fail to start."
    Write-Note "Stop that service, or re-run setup and choose another port."
}
Set-EnvValue -Path $backendEnv -Key "PORT" -Value $backendPort
Set-EnvValue -Path $frontendEnv -Key "VITE_API_URL" -Value "http://localhost:$backendPort"
Write-Ok "VITE_API_URL -> http://localhost:$backendPort"

# --------------------------------------------------------------------------- #
# 6. Dependencies
# --------------------------------------------------------------------------- #

Write-Step "Installing Python dependencies"
python -m pip install --upgrade pip --quiet
python -m pip install -r (Join-Path $Root "backend\requirements.txt") --quiet
if ($LASTEXITCODE -ne 0) { Write-Fail "pip install failed"; exit 1 }
Write-Ok "Python dependencies installed"

Write-Step "Installing Node dependencies"
if (Test-Path (Join-Path $Root "node_modules\vite")) {
    Write-Ok "node_modules already present"
} else {
    npm install --no-fund --no-audit
    if ($LASTEXITCODE -ne 0) { Write-Fail "npm install failed"; exit 1 }
    Write-Ok "Node dependencies installed"
}

# --------------------------------------------------------------------------- #
# 7. Summary
# --------------------------------------------------------------------------- #

$llmState = if ($openRouterKey -and (Get-EnvValue -Path $backendEnv -Key "OPENROUTER_MODEL")) { "configured" } else { "not configured (derived engine)" }

Write-Host @"

Setup complete.

  Database  : $($databaseUrl.Split('@')[1])  [$mode]
  Backend   : http://127.0.0.1:$backendPort   (docs at /docs)
  Frontend  : http://127.0.0.1:5173
  LLM       : $llmState
  Assistant : $(if ($provider -eq "off") { "disabled" } else { "$provider" })
  X/Twitter : $(if ($twitterToken) { "configured" } else { "not configured" })

  Secrets live in backend/.env and .env.local. Both are gitignored.

"@ -ForegroundColor Green

# --------------------------------------------------------------------------- #
# 8. Start
# --------------------------------------------------------------------------- #

$stack = Get-RunningStack -BackendPort ([int]$backendPort) -FrontendPort 5173

if ($stack.AnythingUp) {
    # Setup rewrote the configuration. Keys and the model can be hot-reloaded;
    # anything else (the database URL, the port) needs a real restart.
    Write-Host ""
    Write-Warn "The app is already running with the previous settings."
    $reload = Invoke-ApiReload -BackendPort ([int]$backendPort)
    if ($reload -eq "reloaded") {
        Write-Note "API keys and the LLM model are live. A database or port change still needs a restart."
        $answer = Read-Choice -Prompt "Restart anyway to be certain everything matches?" -Options @("yes", "no") -Default "no"
    } else {
        $answer = Read-Choice -Prompt "Restart it now so the new settings apply?" -Options @("yes", "no") -Default "yes"
    }
    if ($answer -eq "yes") {
        Restart-ProjectStack -BackendPort ([int]$backendPort) -FrontendPort 5173 -Root $Root | Out-Null
    } else {
        Write-Note "Restart skipped. The new settings apply the next time you start the app."
    }
} else {
    $shouldStart = $Start
    if (-not $Start -and -not $NonInteractive) {
        $answer = Read-Choice -Prompt "Start the app now?" -Options @("yes", "no") -Default "yes"
        $shouldStart = ($answer -eq "yes")
    }

    if ($shouldStart) {
        $startScript = Join-Path $PSScriptRoot "start.ps1"
        & $startScript -BackendPort ([int]$backendPort) -SkipDatabase
    } else {
        Write-Host "Start it later with:  .\scripts\start.ps1" -ForegroundColor Yellow
    }
}
