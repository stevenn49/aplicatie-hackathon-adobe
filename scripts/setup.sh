#!/usr/bin/env bash
#
# Cold setup for MarketPulse AI on macOS / Linux.
#
#   ./scripts/setup.sh                        # detect the database, ask, write envs
#   ./scripts/setup.sh --database docker      # force the container
#   ./scripts/setup.sh --database native --db-user root --db-password secret
#   ./scripts/setup.sh --non-interactive --start
#
# Every step checks before acting, so the script is safe to run again.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DATABASE="auto"
NON_INTERACTIVE=0
START=0
DB_HOST="127.0.0.1"
DB_PORT="3306"
DB_USER="root"
DB_PASSWORD=""
DB_NAME="marketpulse"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --database) DATABASE="$2"; shift 2 ;;
    --db-host) DB_HOST="$2"; shift 2 ;;
    --db-port) DB_PORT="$2"; shift 2 ;;
    --db-user) DB_USER="$2"; shift 2 ;;
    --db-password) DB_PASSWORD="$2"; shift 2 ;;
    --db-name) DB_NAME="$2"; shift 2 ;;
    --non-interactive) NON_INTERACTIVE=1; shift ;;
    --start) START=1; shift ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

step() { printf '\n==> %s\n' "$1"; }
ok()   { printf '    OK   %s\n' "$1"; }
warn() { printf '    !    %s\n' "$1"; }
fail() { printf '    X    %s\n' "$1" >&2; }
note() { printf '         %s\n' "$1"; }

# Prompt helpers. In non-interactive mode every prompt returns its default.
ask_choice() {  # $1 prompt, $2 default, rest options
  local prompt="$1" default="$2"; shift 2
  local options=("$@")
  if [[ "$NON_INTERACTIVE" -eq 1 ]]; then echo "$default"; return; fi
  local list
  list="$(IFS='/'; echo "${options[*]}")"
  while true; do
    read -r -p "    $prompt [$list] (default: $default): " answer
    answer="${answer:-$default}"
    for option in "${options[@]}"; do
      if [[ "$answer" == "$option" ]]; then echo "$option"; return; fi
    done
    warn "Choose one of: $list"
  done
}

ask_text() {  # $1 prompt, $2 default
  if [[ "$NON_INTERACTIVE" -eq 1 ]]; then echo "$2"; return; fi
  local answer
  read -r -p "    $1 (default: $2): " answer
  echo "${answer:-$2}"
}

ask_secret() {  # $1 prompt, $2 current value
  if [[ "$NON_INTERACTIVE" -eq 1 ]]; then echo "$2"; return; fi
  local hint=" (Enter skips)"
  [[ -n "$2" ]] && hint=" (Enter keeps the current value)"
  local answer
  read -r -s -p "    $1$hint: " answer
  echo ""
  echo "${answer:-$2}"
}

mask() {
  local value="$1"
  if [[ -z "$value" ]]; then echo "(empty)"; return; fi
  if [[ ${#value} -le 8 ]]; then echo "****"; return; fi
  echo "${value:0:6}…${value: -4}"
}

env_get() {  # $1 file, $2 key
  [[ -f "$1" ]] || { echo ""; return; }
  python3 - "$1" "$2" <<'PY'
import re, sys, pathlib
path, key = pathlib.Path(sys.argv[1]), sys.argv[2]
if not path.exists():
    print(""); raise SystemExit
for line in path.read_text(encoding="utf-8").splitlines():
    m = re.match(rf'\s*{re.escape(key)}\s*=\s*(.*)$', line)
    if m:
        print(m.group(1).strip().strip('"')); raise SystemExit
print("")
PY
}

env_set() {  # $1 file, $2 key, $3 value
  python3 - "$1" "$2" "$3" <<'PY'
import re, sys, pathlib
path, key, value = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
text = path.read_text(encoding="utf-8") if path.exists() else ""
pattern = re.compile(rf'(?m)^\s*{re.escape(key)}\s*=.*$')
line = f'{key}="{value}"'
if pattern.search(text):
    text = pattern.sub(line, text, count=1)
else:
    text = text.rstrip() + "\n" + line + "\n"
path.write_text(text, encoding="utf-8", newline="")
PY
}

port_open() {  # $1 port, $2 host
  python3 - "$1" "${2:-127.0.0.1}" <<'PY'
import socket, sys
port, host = int(sys.argv[1]), sys.argv[2]
s = socket.socket(); s.settimeout(1.2)
try:
    s.connect((host, port)); print("yes")
except Exception:
    print("no")
finally:
    s.close()
PY
}

printf 'MarketPulse AI - cold setup\nRepository: %s\n' "$ROOT"

# ---------------------------------------------------------------------------
# 1. Toolchain
# ---------------------------------------------------------------------------
step "Checking the toolchain"
missing=()

command -v node >/dev/null 2>&1 && ok "Node $(node --version)" || missing+=("Node.js 18+  https://nodejs.org")
command -v npm  >/dev/null 2>&1 && ok "npm $(npm --version)"   || missing+=("npm (ships with Node.js)")
command -v python3 >/dev/null 2>&1 && ok "Python $(python3 --version)" || missing+=("Python 3.11+  https://python.org")

docker_available=0
if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then docker_available=1; else warn "Docker is installed but the daemon is not running"; fi
else
  note "Docker is not installed"
fi

native_available=0
if command -v mysql >/dev/null 2>&1 && [[ "$(port_open 3306 127.0.0.1)" == "yes" ]]; then
  native_available=1
elif command -v mysql >/dev/null 2>&1; then
  warn "The mysql client is installed but nothing answers on 127.0.0.1:3306"
else
  note "No native MySQL client on PATH"
fi

if [[ ${#missing[@]} -gt 0 ]]; then
  printf '\nMissing prerequisites:\n' >&2
  printf '  - %s\n' "${missing[@]}" >&2
  printf '\nInstall them and run this script again.\n' >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# 2. Database: detect, then let the user choose
# ---------------------------------------------------------------------------
step "Looking for a MySQL database"
[[ "$docker_available" -eq 1 ]] && ok "Docker is running (MySQL 8.4 in a container on port 3307)"
[[ "$native_available" -eq 1 ]] && ok "A MySQL server answers on 127.0.0.1:3306"

mode="$DATABASE"
if [[ "$mode" == "auto" ]]; then
  if [[ "$docker_available" -eq 1 && "$native_available" -eq 1 ]]; then
    printf '\n    Both options are available.\n'
    printf '      docker  - MySQL 8.4 in a container on port 3307, nothing installed on your system\n'
    printf '      native  - the MySQL already running on your machine, port 3306\n'
    mode="$(ask_choice "Which database should the app use?" "docker" docker native)"
  elif [[ "$docker_available" -eq 1 ]]; then
    mode="docker"; ok "Using Docker (the only option available)"
  elif [[ "$native_available" -eq 1 ]]; then
    mode="native"; ok "Using the native MySQL server (the only option available)"
  else
    fail "No MySQL available."
    note "Install Docker Desktop: https://docker.com/products/docker-desktop"
    note "or install MySQL 8:     https://dev.mysql.com/downloads/installer/"
    exit 1
  fi
fi

if [[ "$mode" == "docker" && "$docker_available" -ne 1 ]]; then
  fail "--database docker was requested but the Docker daemon is not running."; exit 1
fi

if [[ "$mode" == "docker" ]]; then
  step "Starting the MySQL container"
  docker compose up -d
  note "Waiting for MySQL to become healthy..."
  healthy=0
  for _ in $(seq 1 60); do
    status="$(docker inspect --format '{{.State.Health.Status}}' marketpulse-mysql 2>/dev/null || true)"
    [[ "$status" == "healthy" ]] && { healthy=1; break; }
    sleep 2
  done
  [[ "$healthy" -eq 1 ]] || { fail "The container did not become healthy. Run: docker compose logs mysql"; exit 1; }
  ok "MySQL container healthy on 127.0.0.1:3307"
  DB_USER="marketpulse"; DB_PASSWORD="marketpulse"; DB_HOST="127.0.0.1"; DB_PORT="3307"
else
  step "Configuring the native MySQL connection"
  DB_HOST="$(ask_text "MySQL host" "$DB_HOST")"
  DB_PORT="$(ask_text "MySQL port" "$DB_PORT")"
  DB_USER="$(ask_text "MySQL user" "$DB_USER")"
  DB_PASSWORD="$(ask_secret "MySQL password" "$DB_PASSWORD")"

  if MYSQL_PWD="$DB_PASSWORD" mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -e "SELECT 1;" >/dev/null 2>&1; then
    ok "Connected to MySQL at $DB_HOST:$DB_PORT"
    MYSQL_PWD="$DB_PASSWORD" mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" \
      -e "CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    ok "Database '$DB_NAME' ready"
  else
    fail "Cannot connect to MySQL at $DB_HOST:$DB_PORT as $DB_USER"
    note "Create the database and user manually, then re-run:"
    note "  CREATE DATABASE $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    note "  CREATE USER '$DB_USER'@'%' IDENTIFIED BY '<password>';"
    note "  GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'%';"
    exit 1
  fi
fi

if [[ "$mode" == "docker" ]]; then
  echo "GRANT ALL PRIVILEGES ON ${DB_NAME}_test.* TO 'marketpulse'@'%'; FLUSH PRIVILEGES;" \
    | docker exec -i marketpulse-mysql mysql -u root -pmarketpulse_root >/dev/null 2>&1 || true
fi

DATABASE_URL="mysql+pymysql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

# ---------------------------------------------------------------------------
# 3. Environment files
# ---------------------------------------------------------------------------
step "Writing backend/.env"
if [[ -f backend/.env ]]; then
  ok "Keeping the existing file"
else
  cp backend/.env.example backend/.env
  ok "Created from backend/.env.example"
fi
env_set backend/.env DATABASE_URL "$DATABASE_URL"
ok "DATABASE_URL -> ${DATABASE_URL#*@}"

# ---------------------------------------------------------------------------
# 4. API keys
# ---------------------------------------------------------------------------
printf '\n==> API keys\n\n'
printf '    Everything below is optional. The dashboard runs without any of them;\n'
printf '    each one only enables a specific feature. Press Enter to skip a key.\n\n'
printf '    No key needed (already working):\n'
printf '      eMAG            public catalogue, HTML parsing\n'
printf '      Reddit          public .json endpoints\n'
printf '      Google Trends   pytrends\n'
printf '      Hacker News     Algolia search API\n\n'

current_key="$(env_get backend/.env OPENROUTER_API_KEY)"
current_model="$(env_get backend/.env OPENROUTER_MODEL)"
printf '    OpenRouter - powers the executive summary, the review summary and\n'
printf '                 the marketing opportunities. Free models available.\n'
printf '                 https://openrouter.ai/keys\n'
openrouter_key="$(ask_secret "OpenRouter API key" "$current_key")"
if [[ -n "$openrouter_key" ]]; then
  model="$(ask_text "OpenRouter model id" "$current_model")"
  [[ -z "$model" ]] && warn "No model id given. The key is saved but the LLM stays off until OPENROUTER_MODEL is set."
  env_set backend/.env OPENROUTER_API_KEY "$openrouter_key"
  env_set backend/.env OPENROUTER_MODEL "$model"
  ok "OpenRouter configured ($(mask "$openrouter_key")), model: ${model:-(none)}"
else
  note "Skipped. AI surfaces will report source=derived."
fi

printf '\n'
printf '    AI assistant (the Ask AI panel) - a separate service in backend/server.py.\n'
printf '      ollama  runs locally, no key, needs https://ollama.com\n'
printf '      groq    free key, fast          https://console.groq.com/keys\n'
printf '      gemini  free key                https://aistudio.google.com/apikey\n'
printf '      off     do not enable the assistant\n'
current_provider="$(env_get backend/.env AI_PROVIDER)"
[[ -z "$current_provider" ]] && current_provider="ollama"
default_provider="$current_provider"
[[ "$NON_INTERACTIVE" -eq 1 ]] && default_provider="off"
provider="$(ask_choice "Assistant provider" "$default_provider" ollama groq gemini off)"

if [[ "$provider" != "off" ]]; then
  env_set backend/.env AI_PROVIDER "$provider"
  case "$provider" in
    groq)
      groq_key="$(ask_secret "Groq API key" "$(env_get backend/.env GROQ_API_KEY)")"
      if [[ -n "$groq_key" ]]; then env_set backend/.env GROQ_API_KEY "$groq_key"; ok "Groq configured ($(mask "$groq_key"))"
      else warn "No Groq key; the assistant will fail until GROQ_API_KEY is set."; fi
      ;;
    gemini)
      gemini_key="$(ask_secret "Gemini API key" "$(env_get backend/.env GEMINI_API_KEY)")"
      if [[ -n "$gemini_key" ]]; then env_set backend/.env GEMINI_API_KEY "$gemini_key"; ok "Gemini configured ($(mask "$gemini_key"))"
      else warn "No Gemini key; the assistant will fail until GEMINI_API_KEY is set."; fi
      ;;
    ollama)
      ollama_url="$(ask_text "Ollama URL" "$(env_get backend/.env OLLAMA_URL)")"
      [[ -z "$ollama_url" ]] && ollama_url="http://localhost:11434"
      env_set backend/.env OLLAMA_URL "$ollama_url"
      ok "Ollama configured at $ollama_url"
      note "Pull a model once:  ollama pull llama3.2"
      ;;
  esac
  ai_port="$(ask_text "AI assistant port (server.py)" "8020")"
  env_set .env.local VITE_AI_API_URL "http://localhost:$ai_port"
else
  note "Assistant disabled. VITE_AI_API_URL stays empty."
fi

printf '\n'
printf '    X / Twitter - brand mention collection. Needs a bearer token.\n'
printf '                  https://developer.x.com/en/portal/dashboard\n'
twitter_token="$(ask_secret "X/Twitter bearer token" "$(env_get backend/.env TWITTER_BEARER_TOKEN)")"
if [[ -n "$twitter_token" ]]; then
  env_set backend/.env TWITTER_BEARER_TOKEN "$twitter_token"
  ok "X/Twitter configured ($(mask "$twitter_token"))"
else
  note "Skipped. The Twitter connector returns nothing until a token is set."
fi

printf '\n'
printf '    Reddit - the connector uses the public .json endpoints, so no key is\n'
printf '             required. A descriptive User-Agent is recommended.\n'
reddit_ua="$(ask_text "Reddit User-Agent" "$(env_get backend/.env REDDIT_USER_AGENT)")"
[[ -z "$reddit_ua" ]] && reddit_ua="MarketPulseAI/1.0 by MarketPulseTeam"
env_set backend/.env REDDIT_USER_AGENT "$reddit_ua"
ok "Reddit User-Agent: $reddit_ua"

# ---------------------------------------------------------------------------
# 5. Frontend environment
# ---------------------------------------------------------------------------
step "Writing .env.local"
if [[ -f .env.local ]]; then
  ok "Keeping the existing file"
else
  cp .env.example .env.local
  ok "Created from .env.example"
fi
default_port="$(env_get backend/.env PORT)"
[[ -z "$default_port" ]] && default_port="8010"

# Port 8000 is taken by an unrelated service on some machines. If the configured
# port is busy, propose the next free one instead of writing a URL that will not
# answer.
if [[ "$(port_open "$default_port")" == "yes" ]]; then
  free_port=$((default_port + 1))
  while [[ "$free_port" -lt 8100 && "$(port_open "$free_port")" == "yes" ]]; do
    free_port=$((free_port + 1))
  done
  warn "Port $default_port is already in use on this machine."
  note "Another service owns it; the backend would fail to bind."
  default_port="$free_port"
  note "Suggesting $free_port instead."
fi

backend_port="$(ask_text "Backend port" "$default_port")"
if [[ "$(port_open "$backend_port")" == "yes" ]]; then
  warn "Port $backend_port is already in use. The backend will fail to start."
  note "Stop that service, or re-run setup and choose another port."
fi
env_set backend/.env PORT "$backend_port"
env_set .env.local VITE_API_URL "http://localhost:$backend_port"
ok "VITE_API_URL -> http://localhost:$backend_port"

# ---------------------------------------------------------------------------
# 6. Dependencies
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
# 7. Summary
# ---------------------------------------------------------------------------
llm_state="not configured (derived engine)"
[[ -n "$openrouter_key" && -n "$(env_get backend/.env OPENROUTER_MODEL)" ]] && llm_state="configured"
assistant_state="disabled"; [[ "$provider" != "off" ]] && assistant_state="$provider"
twitter_state="not configured"; [[ -n "$twitter_token" ]] && twitter_state="configured"

printf '\nSetup complete.\n\n'
printf '  Database  : %s  [%s]\n' "${DATABASE_URL#*@}" "$mode"
printf '  Backend   : http://127.0.0.1:%s   (docs at /docs)\n' "$backend_port"
printf '  Frontend  : http://127.0.0.1:5173\n'
printf '  LLM       : %s\n' "$llm_state"
printf '  Assistant : %s\n' "$assistant_state"
printf '  X/Twitter : %s\n\n' "$twitter_state"
printf '  Secrets live in backend/.env and .env.local. Both are gitignored.\n\n'

# ---------------------------------------------------------------------------
# 8. Start
# ---------------------------------------------------------------------------
# A running instance holds the old configuration. Keys and the model can be
# hot-reloaded; the database URL and the port need a real restart.
if [[ "$(port_open "$backend_port")" == "yes" ]]; then
  printf '\n'
  warn "The app is already running with the previous settings."
  if curl -fsS -X POST "http://127.0.0.1:$backend_port/api/admin/reload" >/dev/null 2>&1; then
    ok "The running API reloaded its keys and LLM model."
    note "A database or port change still needs a restart."
    default_restart="no"
  else
    default_restart="yes"
  fi
  answer="$(ask_choice "Restart it now so every setting matches?" "$default_restart" yes no)"
  if [[ "$answer" == "yes" ]]; then
    bash "$ROOT/scripts/start.sh" --backend-port "$backend_port" --skip-database --detach >/dev/null 2>&1 || true
    note "Restart the app with ./run.sh (option 3 then 2) if it does not come back."
  else
    note "Restart skipped. The new settings apply the next time you start the app."
  fi
  exit 0
fi

if [[ "$START" -eq 0 && "$NON_INTERACTIVE" -eq 0 ]]; then
  answer="$(ask_choice "Start the app now?" "yes" yes no)"
  [[ "$answer" == "yes" ]] && START=1
fi

if [[ "$START" -eq 1 ]]; then
  exec "$ROOT/scripts/start.sh" --backend-port "$backend_port" --skip-database
else
  printf 'Start it later with:  ./scripts/start.sh\n'
fi
