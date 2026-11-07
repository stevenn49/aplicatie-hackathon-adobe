<#
.SYNOPSIS
    Cold setup for MarketPulse AI on Windows.

.DESCRIPTION
    Checks the toolchain, prepares the MySQL database (Docker or a native
    install), writes the local .env files, and installs the Python and Node
    dependencies. Safe to run more than once: every step checks before acting.

.PARAMETER Database
    "docker" (default) or "native". Docker runs MySQL 8.4 in a container on host
    port 3307. Native uses a MySQL server you already have installed.

.PARAMETER DbHost
    Native only. Default 127.0.0.1.

.PARAMETER DbPort
    Native only. Default 3306.

.PARAMETER DbUser
    Native only. Default marketpulse.

.PARAMETER DbPassword
    Native only. Default marketpulse.

.PARAMETER DbName
    Database name. Default marketpulse.

.EXAMPLE
    .\scripts\setup.ps1

.EXAMPLE
    .\scripts\setup.ps1 -Database native -DbPort 3306 -DbUser root -DbPassword secret
#>
[CmdletBinding()]
param(
    [ValidateSet("docker", "native")]
    [string]$Database = "docker",
    [string]$DbHost = "127.0.0.1",
    [int]$DbPort = 3306,
    [string]$DbUser = "marketpulse",
    [string]$DbPassword = "marketpulse",
    [string]$DbName = "marketpulse"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Write-Step($Message) { Write-Host "`n==> $Message" -ForegroundColor Cyan }
function Write-Ok($Message) { Write-Host "    OK  $Message" -ForegroundColor Green }
function Write-Warn($Message) { Write-Host "    !   $Message" -ForegroundColor Yellow }
function Write-Fail($Message) { Write-Host "    X   $Message" -ForegroundColor Red }

Write-Host @"
MarketPulse AI - cold setup
Repository: $Root
Database mode: $Database
"@ -ForegroundColor White

# ---------------------------------------------------------------------------
# 1. Toolchain
# ---------------------------------------------------------------------------
Write-Step "Checking the toolchain"

$missing = @()

try { $node = (node --version) 2>$null; Write-Ok "Node $node" } catch { $missing += "Node.js 18+ (https://nodejs.org)" }
try { $npm = (npm --version) 2>$null; Write-Ok "npm $npm" } catch { $missing += "npm (ships with Node.js)" }
try { $py = (python --version) 2>$null; Write-Ok "Python $py" } catch { $missing += "Python 3.11+ (https://python.org)" }

if ($Database -eq "docker") {
    try {
        $dockerVersion = (docker --version) 2>$null
        Write-Ok $dockerVersion
        $daemon = (docker info --format "{{.ServerVersion}}" 2>$null)
        if (-not $daemon) { $missing += "Docker Desktop running (start it, then re-run)" } else { Write-Ok "Docker daemon $daemon" }
    } catch {
        $missing += "Docker Desktop (https://docker.com/products/docker-desktop) or run with -Database native"
    }
}

if ($missing.Count -gt 0) {
    Write-Host "`nMissing prerequisites:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Host "`nInstall them and run this script again." -ForegroundColor Yellow
    exit 1
}

# ---------------------------------------------------------------------------
# 2. Database
# ---------------------------------------------------------------------------
Write-Step "Preparing the MySQL database ($Database)"

if ($Database -eq "docker") {
    docker compose up -d | Out-Null
    Write-Host "    Waiting for MySQL to become healthy..."
    $healthy = $false
    for ($i = 0; $i -lt 60; $i++) {
        $status = (docker inspect --format "{{.State.Health.Status}}" marketpulse-mysql 2>$null)
        if ($status -eq "healthy") { $healthy = $true; break }
        Start-Sleep -Seconds 2
    }
    if (-not $healthy) {
        Write-Fail "The MySQL container did not become healthy. Run: docker compose logs mysql"
        exit 1
    }
    Write-Ok "MySQL container healthy on 127.0.0.1:3307"
    $databaseUrl = "mysql+pymysql://marketpulse:marketpulse@127.0.0.1:3307/marketpulse"
} else {
    Write-Host "    Testing $DbHost`:$DbPort as $DbUser ..."
    $env:MYSQL_PWD = $DbPassword
    try {
        $ping = (mysql -h $DbHost -P $DbPort -u $DbUser -e "SELECT 1;" 2>&1)
        if ($LASTEXITCODE -ne 0) { throw $ping }
        Write-Ok "Connected to the MySQL server"
        mysql -h $DbHost -P $DbPort -u $DbUser -e "CREATE DATABASE IF NOT EXISTS $DbName CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Could not create the database $DbName" }
        Write-Ok "Database '$DbName' ready"
    } catch {
        Write-Fail "Cannot connect to MySQL at $DbHost`:$DbPort as $DbUser"
        Write-Host "    The mysql CLI must be on PATH for this check." -ForegroundColor Yellow
        Write-Host "    Create the database manually, then set DATABASE_URL in backend/.env:" -ForegroundColor Yellow
        Write-Host "      CREATE DATABASE $DbName CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" -ForegroundColor Yellow
        Write-Host "      CREATE USER '$DbUser'@'%' IDENTIFIED BY '<password>';" -ForegroundColor Yellow
        Write-Host "      GRANT ALL PRIVILEGES ON $DbName.* TO '$DbUser'@'%';" -ForegroundColor Yellow
        exit 1
    } finally {
        Remove-Item Env:\MYSQL_PWD -ErrorAction SilentlyContinue
    }
    $databaseUrl = "mysql+pymysql://${DbUser}:${DbPassword}@${DbHost}:${DbPort}/${DbName}"
}

# ---------------------------------------------------------------------------
# 3. Environment files
# ---------------------------------------------------------------------------
Write-Step "Writing local environment files"

$backendEnv = Join-Path $Root "backend\.env"
if (Test-Path $backendEnv) {
    $content = Get-Content $backendEnv -Raw
    if ($content -match 'DATABASE_URL="([^"]*)"') {
        $existing = $Matches[1]
        if ($existing -ne $databaseUrl) {
            $content = $content -replace 'DATABASE_URL="[^"]*"', "DATABASE_URL=`"$databaseUrl`""
            Set-Content -Path $backendEnv -Value $content -NoNewline
            Write-Ok "backend/.env updated with the new DATABASE_URL"
        } else {
            Write-Ok "backend/.env already points at $($databaseUrl.Split('@')[1])"
        }
    }
} else {
    Copy-Item (Join-Path $Root "backend\.env.example") $backendEnv
    $content = Get-Content $backendEnv -Raw
    $content = $content -replace 'DATABASE_URL="[^"]*"', "DATABASE_URL=`"$databaseUrl`""
    Set-Content -Path $backendEnv -Value $content -NoNewline
    Write-Ok "backend/.env created"
}

$frontendEnv = Join-Path $Root ".env.local"
if (Test-Path $frontendEnv) {
    Write-Ok ".env.local already exists"
} else {
    Copy-Item (Join-Path $Root ".env.example") $frontendEnv
    Write-Ok ".env.local created (VITE_API_URL=http://localhost:8010)"
}

# ---------------------------------------------------------------------------
# 4. Dependencies
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# 5. Done
# ---------------------------------------------------------------------------
Write-Host @"

Setup complete.

  Database : $($databaseUrl.Split('@')[1])
  Backend  : http://127.0.0.1:8010  (docs at /docs)
  Frontend : http://127.0.0.1:5173

Start everything with:
    .\scripts\start.ps1

Optional - enable the LLM surfaces:
    put OPENROUTER_API_KEY and OPENROUTER_MODEL in backend/.env
    (a free model id from https://openrouter.ai/models?max_price=0)

"@ -ForegroundColor Green
