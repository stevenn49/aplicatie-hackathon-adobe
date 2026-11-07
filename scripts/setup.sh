#!/usr/bin/env bash
#
# Cold setup for MarketPulse AI on macOS / Linux.
#
#   ./scripts/setup.sh                      # MySQL in Docker (host port 3307)
#   ./scripts/setup.sh --database native    # MySQL already installed locally
#   ./scripts/setup.sh --database native --db-user root --db-password secret
#
# Safe to run more than once: every step checks before acting.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DATABASE="docker"
DB_HOST="127.0.0.1"
DB_PORT="3306"
DB_USER="marketpulse"
DB_PASSWORD="marketpulse"
DB_NAME="marketpulse"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --database) DATABASE="$2"; shift 2 ;;
    --db-host) DB_HOST="$2"; shift 2 ;;
    --db-port) DB_PORT="$2"; shift 2 ;;
    --db-user) DB_USER="$2"; shift 2 ;;
    --db-password) DB_PASSWORD="$2"; shift 2 ;;
    --db-name) DB_NAME="$2"; shift 2 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

step() { printf '\n==> %s\n' "$1"; }
ok()   { printf '    OK  %s\n' "$1"; }
fail() { printf '    X   %s\n' "$1" >&2; }

printf 'MarketPulse AI - cold setup\nRepository: %s\nDatabase mode: %s\n' "$ROOT" "$DATABASE"

# ---------------------------------------------------------------------------
# 1. Toolchain
# ---------------------------------------------------------------------------
step "Checking the toolchain"
missing=()

command -v node >/dev/null 2>&1 && ok "Node $(node --version)" || missing+=("Node.js 18+ (https://nodejs.org)")
command -v npm  >/dev/null 2>&1 && ok "npm $(npm --version)"   || missing+=("npm (ships with Node.js)")
command -v python3 >/dev/null 2>&1 && ok "Python $(python3 --version)" || missing+=("Python 3.11+ (https://python.org)")

if [[ "$DATABASE" == "docker" ]]; then
  if command -v docker >/dev/null 2>&1; then
    ok "$(docker --version)"
    if docker info >/dev/null 2>&1; then ok "Docker daemon running"; else missing+=("Docker daemon running (start Docker Desktop)"); fi
  else
    missing+=("Docker (https://docker.com) or run with --database native")
  fi
fi

if [[ ${#missing[@]} -gt 0 ]]; then
  printf '\nMissing prerequisites:\n' >&2
  printf '  - %s\n' "${missing[@]}" >&2
  printf '\nInstall them and run this script again.\n' >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# 2. Database
# ---------------------------------------------------------------------------
step "Preparing the MySQL database ($DATABASE)"

if [[ "$DATABASE" == "docker" ]]; then
  docker compose up -d
  printf '    Waiting for MySQL to become healthy...\n'
  healthy=0
  for _ in $(seq 1 60); do
    status="$(docker inspect --format '{{.State.Health.Status}}' marketpulse-mysql 2>/dev/null || true)"
    if [[ "$status" == "healthy" ]]; then healthy=1; break; fi
    sleep 2
  done
  if [[ "$healthy" -ne 1 ]]; then
    fail "The MySQL container did not become healthy. Run: docker compose logs mysql"
    exit 1
  fi
  ok "MySQL container healthy on 127.0.0.1:3307"
  DATABASE_URL="mysql+pymysql://marketpulse:marketpulse@127.0.0.1:3307/marketpulse"
else
  if ! command -v mysql >/dev/null 2>&1; then
    fail "The mysql client is not on PATH; create the database manually, then set DATABASE_URL in backend/.env"
    exit 1
  fi
  if MYSQL_PWD="$DB_PASSWORD" mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -e "SELECT 1;" >/dev/null 2>&1; then
    ok "Connected to the MySQL server"
    MYSQL_PWD="$DB_PASSWORD" mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" \
      -e "CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    ok "Database '$DB_NAME' ready"
  else
    fail "Cannot connect to MySQL at $DB_HOST:$DB_PORT as $DB_USER"
    printf '    Create the database manually, then set DATABASE_URL in backend/.env:\n'
    printf '      CREATE DATABASE %s CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\n' "$DB_NAME"
    exit 1
  fi
  DATABASE_URL="mysql+pymysql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
fi

# ---------------------------------------------------------------------------
# 3. Environment files
# ---------------------------------------------------------------------------
step "Writing local environment files"

if [[ -f backend/.env ]]; then
  python3 - "$DATABASE_URL" <<'PY'
import re, sys, pathlib
url = sys.argv[1]
path = pathlib.Path("backend/.env")
text = path.read_text(encoding="utf-8")
new = re.sub(r'DATABASE_URL="[^"]*"', f'DATABASE_URL="{url}"', text, count=1)
if new != text:
    path.write_text(new, encoding="utf-8", newline="")
    print("    OK  backend/.env updated with the new DATABASE_URL")
else:
    print("    OK  backend/.env already points at the right database")
PY
else
  sed "s|^DATABASE_URL=.*|DATABASE_URL=\"${DATABASE_URL}\"|" backend/.env.example > backend/.env
  ok "backend/.env created"
fi

if [[ -f .env.local ]]; then
  ok ".env.local already exists"
else
  cp .env.example .env.local
  ok ".env.local created (VITE_API_URL=http://localhost:8010)"
fi

# ---------------------------------------------------------------------------
# 4. Dependencies
# ---------------------------------------------------------------------------
step "Installing Python dependencies"
python3 -m pip install --upgrade pip --quiet
python3 -m pip install -r backend/requirements.txt --quiet
ok "Python dependencies installed"

step "Installing Node dependencies"
if [[ -d node_modules/vite ]]; then
  ok "node_modules already present"
else
  npm install --no-fund --no-audit
  ok "Node dependencies installed"
fi

# ---------------------------------------------------------------------------
# 5. Done
# ---------------------------------------------------------------------------
printf '\nSetup complete.\n\n'
printf '  Backend  : http://127.0.0.1:8010  (docs at /docs)\n'
printf '  Frontend : http://127.0.0.1:5173\n\n'
printf 'Start everything with:\n    ./scripts/start.sh\n\n'
printf 'Optional - enable the LLM surfaces:\n'
printf '    put OPENROUTER_API_KEY and OPENROUTER_MODEL in backend/.env\n'
printf '    (a free model id from https://openrouter.ai/models?max_price=0)\n\n'
