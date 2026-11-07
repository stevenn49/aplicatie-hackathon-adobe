#!/usr/bin/env bash
#
# MarketPulse AI - settings manager for macOS / Linux.
#
#   ./scripts/settings.sh
#   ./scripts/settings.sh --show
#
# View and change everything the app is configured with: the database
# connection, the backend port, the OpenRouter key and model (chosen from the
# live free catalogue), the AI assistant provider, the X/Twitter token and the
# Reddit user agent. Secrets are masked on screen.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND_ENV="$ROOT/backend/.env"
FRONTEND_ENV="$ROOT/.env.local"
SHOW_ONLY=0
[[ "${1:-}" == "--show" ]] && SHOW_ONLY=1

step() { printf '\n==> %s\n' "$1"; }
ok()   { printf '    OK   %s\n' "$1"; }
warn() { printf '    !    %s\n' "$1"; }
fail() { printf '    X    %s\n' "$1" >&2; }
note() { printf '         %s\n' "$1"; }

env_get() {
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

env_set() {
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

mask() {
  local value="$1"
  if [[ -z "$value" ]]; then echo "(empty)"; return; fi
  if [[ ${#value} -le 8 ]]; then echo "****"; return; fi
  echo "${value:0:6}…${value: -4}"
}

port_open() {
  python3 - "$1" <<'PY'
import socket, sys
s = socket.socket(); s.settimeout(0.7)
try:
    s.connect(("127.0.0.1", int(sys.argv[1]))); print("yes")
except Exception:
    print("no")
finally:
    s.close()
PY
}

ask_text() {
  local answer
  read -r -p "    $1 (default: $2): " answer
  echo "${answer:-$2}"
}

ask_secret() {
  local answer
  read -r -s -p "    $1 (Enter keeps the current value): " answer
  echo ""
  echo "${answer:-$2}"
}

ask_number() {
  local prompt="$1" default="$2" answer
  while true; do
    read -r -p "    $prompt (default: $default): " answer
    answer="${answer:-$default}"
    [[ "$answer" =~ ^[0-9]+$ ]] && { echo "$answer"; return; }
    warn "Enter a number."
  done
}

# --------------------------------------------------------------------------- #
# OpenRouter free catalogue
# --------------------------------------------------------------------------- #

fetch_free_models() {
  python3 - <<'PY'
import json, urllib.request
try:
    req = urllib.request.Request("https://openrouter.ai/api/v1/models", headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as response:
        data = json.load(response)
except Exception:
    print("ERROR"); raise SystemExit

models = []
for model in data.get("data", []):
    pricing = model.get("pricing") or {}
    prompt = str(pricing.get("prompt", ""))
    completion = str(pricing.get("completion", ""))
    def is_zero(value):
        try:
            return float(value) == 0.0
        except (TypeError, ValueError):
            return False
    if is_zero(prompt) and is_zero(completion):
        models.append({
            "id": model.get("id", ""),
            "name": model.get("name", ""),
            "ctx": int(model.get("context_length") or 0),
        })
models.sort(key=lambda m: (-m["ctx"], m["id"]))
print(json.dumps(models))
PY
}

select_openrouter_model() {
  local current="$1"
  printf '\n    Fetching the free model catalogue from OpenRouter...\n'
  local payload
  payload="$(fetch_free_models)"

  if [[ "$payload" == "ERROR" ]]; then
    warn "Could not reach https://openrouter.ai/api/v1/models."
    note "Check your connection, or type a model id by hand."
    ask_text "OpenRouter model id" "$current"
    return
  fi

  local count
  count="$(echo "$payload" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')"
  if [[ "$count" -eq 0 ]]; then
    warn "The catalogue returned no free models right now."
    ask_text "OpenRouter model id" "$current"
    return
  fi

  ok "$count free models available"

  # The default is the model the project ships with. It is marked in the list
  # and pressing Enter picks it.
  local default_model="stealth/crouton-alpha"
  local default_index
  default_index="$(echo "$payload" | python3 -c "
import json, sys
models = json.load(sys.stdin)
target = '$default_model'
current = '''$current'''
for index, model in enumerate(models, 1):
    if model['id'] == target:
        print(index); break
else:
    for index, model in enumerate(models, 1):
        if current and model['id'] == current:
            print(index); break
    else:
        print(1)
")"

  printf '\n'
  printf '      Large-context free models are marked 1M / 256k.\n\n'
  echo "$payload" | python3 -c "
import json, sys
models = json.load(sys.stdin)
default_index = $default_index
current = '''$current'''
for index, model in enumerate(models, 1):
    ctx = f'{model[\"ctx\"]/1000:.0f}k ctx' if model['ctx'] else 'ctx ?'
    is_default = index == default_index
    colour = '\033[92m' if is_default else '\033[97m'
    suffix = '  \033[96m<- current\033[0m' if current and model['id'] == current else ''
    print(f'      [{index:2}]  {colour}{model[\"id\"]}\033[0m  \033[90m({ctx})\033[0m{suffix}')
    if model['name'] and model['name'] != model['id']:
        print(f'            \033[90m{model[\"name\"]}\033[0m')
"
  printf '\n'
  printf '      *  default for this project\n'
  printf '      [ m]  type a model id by hand\n'
  [[ -n "$current" ]] && printf '      [ k]  keep the current value (%s)\n' "$current"
  printf '\n'

  while true; do
    local answer
    read -r -p "    Choose a model by number (Enter = $default_model): " answer
    answer="${answer,,}"
    if [[ -z "$answer" ]]; then
      echo "$payload" | python3 -c "import json,sys; print(json.load(sys.stdin)[$((default_index-1))]['id'])"
      return
    fi
    [[ "$answer" == "k" && -n "$current" ]] && { echo "$current"; return; }
    if [[ "$answer" == "m" ]]; then
      ask_text "OpenRouter model id" "$current"
      return
    fi
    if [[ "$answer" =~ ^[0-9]+$ ]] && [[ "$answer" -ge 1 && "$answer" -le "$count" ]]; then
      echo "$payload" | python3 -c "import json,sys; print(json.load(sys.stdin)[$((answer-1))]['id'])"
      return
    fi
    warn "Enter a number between 1 and $count, 'm', or 'k'."
  done
}

# --------------------------------------------------------------------------- #
# Views and editors
# --------------------------------------------------------------------------- #

show_settings() {
  step "Current settings"

  if [[ ! -f "$BACKEND_ENV" ]]; then
    fail "backend/.env does not exist. Run scripts/setup.sh first."
    return
  fi

  local database_url port openrouter_key openrouter_model provider groq gemini ollama twitter reddit_ua frontend_url ai_url
  database_url="$(env_get "$BACKEND_ENV" DATABASE_URL)"
  port="$(env_get "$BACKEND_ENV" PORT)"
  openrouter_key="$(env_get "$BACKEND_ENV" OPENROUTER_API_KEY)"
  openrouter_model="$(env_get "$BACKEND_ENV" OPENROUTER_MODEL)"
  provider="$(env_get "$BACKEND_ENV" AI_PROVIDER)"
  groq="$(env_get "$BACKEND_ENV" GROQ_API_KEY)"
  gemini="$(env_get "$BACKEND_ENV" GEMINI_API_KEY)"
  ollama="$(env_get "$BACKEND_ENV" OLLAMA_URL)"
  twitter="$(env_get "$BACKEND_ENV" TWITTER_BEARER_TOKEN)"
  reddit_ua="$(env_get "$BACKEND_ENV" REDDIT_USER_AGENT)"
  frontend_url="$(env_get "$FRONTEND_ENV" VITE_API_URL)"
  ai_url="$(env_get "$FRONTEND_ENV" VITE_AI_API_URL)"

  printf '\n  Database\n'
  printf '    DATABASE_URL        %s\n' "$(echo "$database_url" | sed -E 's#://[^@]+@#://***@#')"
  printf '    Backend port        %s\n' "$port"
  printf '    Frontend API URL    %s\n' "$frontend_url"

  printf '\n  LLM (OpenRouter)\n'
  printf '    API key             %s\n' "$(mask "$openrouter_key")"
  printf '    Model               %s\n' "${openrouter_model:-(none - LLM disabled)}"

  printf '\n  AI assistant\n'
  printf '    Provider            %s\n' "${provider:-(not set)}"
  case "$provider" in
    groq)   printf '    Groq key            %s\n' "$(mask "$groq")" ;;
    gemini) printf '    Gemini key          %s\n' "$(mask "$gemini")" ;;
    ollama) printf '    Ollama URL          %s\n' "$ollama" ;;
  esac
  printf '    Frontend AI URL     %s\n' "${ai_url:-(empty - assistant hidden)}"

  printf '\n  Data sources\n'
  printf '    X/Twitter token     %s\n' "$(mask "$twitter")"
  printf '    Reddit User-Agent   %s\n' "$reddit_ua"
  printf '    eMAG / Google Trends / Hacker News   no key needed\n'

  printf '\n  Files\n'
  printf '    backend/.env        %s\n' "$([[ -f "$BACKEND_ENV" ]] && echo present || echo missing)"
  printf '    .env.local          %s\n\n' "$([[ -f "$FRONTEND_ENV" ]] && echo present || echo missing)"
}

edit_database() {
  step "Database connection"
  note "Current: $(env_get "$BACKEND_ENV" DATABASE_URL | sed -E 's#://[^@]+@#://***@#')"
  printf '\n'
  printf '      [1]  Docker container (127.0.0.1:3307)\n'
  printf '      [2]  Native MySQL on this machine (127.0.0.1:3306)\n'
  printf '      [3]  Another server (host, port, user, password)\n'
  printf '      [4]  Back\n\n'
  read -r -p "    Which database? [1/2/3/4] (default: 4): " choice
  case "${choice:-4}" in
    1)
      env_set "$BACKEND_ENV" DATABASE_URL "mysql+pymysql://marketpulse:marketpulse@127.0.0.1:3307/marketpulse"
      ok "DATABASE_URL -> 127.0.0.1:3307/marketpulse"
      note "Start the container with: docker compose up -d"
      ;;
    2)
      local user password database
      user="$(ask_text "MySQL user" "root")"
      password="$(ask_secret "MySQL password" "")"
      database="$(ask_text "Database name" "marketpulse")"
      env_set "$BACKEND_ENV" DATABASE_URL "mysql+pymysql://${user}:${password}@127.0.0.1:3306/${database}"
      ok "DATABASE_URL -> 127.0.0.1:3306/$database"
      ;;
    3)
      local hostname port user password database
      hostname="$(ask_text "MySQL host" "127.0.0.1")"
      port="$(ask_number "MySQL port" "3306")"
      user="$(ask_text "MySQL user" "marketpulse")"
      password="$(ask_secret "MySQL password" "")"
      database="$(ask_text "Database name" "marketpulse")"
      env_set "$BACKEND_ENV" DATABASE_URL "mysql+pymysql://${user}:${password}@${hostname}:${port}/${database}"
      ok "DATABASE_URL -> ${hostname}:${port}/$database"
      ;;
    *) return ;;
  esac
}

edit_port() {
  step "Backend port"
  local current
  current="$(env_get "$BACKEND_ENV" PORT)"
  [[ -z "$current" ]] && current="8010"

  if [[ "$(port_open "$current")" == "yes" ]]; then
    warn "Port $current is currently in use."
  else
    ok "Port $current is free"
  fi

  local port
  port="$(ask_number "Backend port" "$current")"
  [[ "$(port_open "$port")" == "yes" ]] && warn "Port $port is already in use."
  env_set "$BACKEND_ENV" PORT "$port"
  env_set "$FRONTEND_ENV" VITE_API_URL "http://localhost:$port"
  ok "Backend port -> $port (VITE_API_URL updated)"
}

edit_openrouter() {
  step "OpenRouter (LLM)"
  local current_key current_model
  current_key="$(env_get "$BACKEND_ENV" OPENROUTER_API_KEY)"
  current_model="$(env_get "$BACKEND_ENV" OPENROUTER_MODEL)"

  note "Key:   $(mask "$current_key")"
  note "Model: ${current_model:-(none)}"
  printf '\n'
  printf '      [1]  Set or replace the API key\n'
  printf '      [2]  Choose a free model from the live catalogue\n'
  printf '      [3]  Clear the key and the model (disable the LLM)\n'
  printf '      [4]  Back\n\n'
  read -r -p "    What do you want to change? [1/2/3/4] (default: 4): " choice
  case "${choice:-4}" in
    1)
      local key
      key="$(ask_secret "OpenRouter API key" "$current_key")"
      if [[ -n "$key" ]]; then
        env_set "$BACKEND_ENV" OPENROUTER_API_KEY "$key"
        ok "Key saved ($(mask "$key"))"
        [[ -z "$current_model" ]] && note "No model set yet; choose one with option 2."
      else
        note "Unchanged."
      fi
      ;;
    2)
      local model
      model="$(select_openrouter_model "$current_model")"
      if [[ -n "$model" ]]; then
        env_set "$BACKEND_ENV" OPENROUTER_MODEL "$model"
        ok "Model -> $model"
        [[ -z "$current_key" ]] && warn "No API key set; the LLM stays off until OPENROUTER_API_KEY is filled."
      fi
      ;;
    3)
      env_set "$BACKEND_ENV" OPENROUTER_API_KEY ""
      env_set "$BACKEND_ENV" OPENROUTER_MODEL ""
      ok "LLM disabled; the AI surfaces will report source=derived"
      ;;
    *) return ;;
  esac
}

edit_assistant() {
  step "AI assistant (backend/server.py)"
  note "Provider: $(env_get "$BACKEND_ENV" AI_PROVIDER)"
  printf '\n'
  printf '      [1]  ollama  (local, no key)\n'
  printf '      [2]  groq    (free key)\n'
  printf '      [3]  gemini  (free key)\n'
  printf '      [4]  Disable the assistant\n'
  printf '      [5]  Back\n\n'
  read -r -p "    Which provider? [1/2/3/4/5] (default: 5): " choice
  case "${choice:-5}" in
    1)
      local url
      url="$(ask_text "Ollama URL" "$(env_get "$BACKEND_ENV" OLLAMA_URL)")"
      [[ -z "$url" ]] && url="http://localhost:11434"
      env_set "$BACKEND_ENV" AI_PROVIDER ollama
      env_set "$BACKEND_ENV" OLLAMA_URL "$url"
      set_assistant_url
      ok "Assistant -> ollama at $url"
      note "Pull a model once: ollama pull llama3.2"
      ;;
    2)
      local key
      key="$(ask_secret "Groq API key" "$(env_get "$BACKEND_ENV" GROQ_API_KEY)")"
      env_set "$BACKEND_ENV" AI_PROVIDER groq
      if [[ -n "$key" ]]; then env_set "$BACKEND_ENV" GROQ_API_KEY "$key"; ok "Groq key saved ($(mask "$key"))"
      else warn "No key; the assistant will fail until GROQ_API_KEY is set."; fi
      set_assistant_url
      ok "Assistant -> groq"
      ;;
    3)
      local key
      key="$(ask_secret "Gemini API key" "$(env_get "$BACKEND_ENV" GEMINI_API_KEY)")"
      env_set "$BACKEND_ENV" AI_PROVIDER gemini
      if [[ -n "$key" ]]; then env_set "$BACKEND_ENV" GEMINI_API_KEY "$key"; ok "Gemini key saved ($(mask "$key"))"
      else warn "No key; the assistant will fail until GEMINI_API_KEY is set."; fi
      set_assistant_url
      ok "Assistant -> gemini"
      ;;
    4)
      env_set "$BACKEND_ENV" AI_PROVIDER ""
      env_set "$FRONTEND_ENV" VITE_AI_API_URL ""
      ok "Assistant disabled"
      ;;
    *) return ;;
  esac
}

set_assistant_url() {
  [[ -n "$(env_get "$FRONTEND_ENV" VITE_AI_API_URL)" ]] && return
  local port
  port="$(ask_number "AI assistant port (server.py)" "8020")"
  env_set "$FRONTEND_ENV" VITE_AI_API_URL "http://localhost:$port"
}

edit_twitter() {
  step "X / Twitter"
  local current
  current="$(env_get "$BACKEND_ENV" TWITTER_BEARER_TOKEN)"
  note "Token: $(mask "$current")"
  note "Get one at https://developer.x.com/en/portal/dashboard"
  local token
  token="$(ask_secret "Bearer token ('-' clears it)" "$current")"
  if [[ "$token" == "-" ]]; then
    env_set "$BACKEND_ENV" TWITTER_BEARER_TOKEN ""
    ok "Token cleared"
  elif [[ -n "$token" && "$token" != "$current" ]]; then
    env_set "$BACKEND_ENV" TWITTER_BEARER_TOKEN "$token"
    ok "Token saved ($(mask "$token"))"
  else
    note "Unchanged."
  fi
}

edit_reddit() {
  step "Reddit"
  note "The connector uses the public .json endpoints, so no key is needed."
  local current ua
  current="$(env_get "$BACKEND_ENV" REDDIT_USER_AGENT)"
  ua="$(ask_text "User-Agent" "${current:-MarketPulseAI/1.0 by MarketPulseTeam}")"
  env_set "$BACKEND_ENV" REDDIT_USER_AGENT "$ua"
  ok "User-Agent -> $ua"
}

check_connections() {
  step "Checking the configuration"

  local database_url port model
  database_url="$(env_get "$BACKEND_ENV" DATABASE_URL)"

  if [[ "$database_url" =~ ^mysql\+pymysql://([^:]+):([^@]*)@([^:]+):([0-9]+)/(.+)$ ]]; then
    local user="${BASH_REMATCH[1]}" password="${BASH_REMATCH[2]}" hostname="${BASH_REMATCH[3]}" dbport="${BASH_REMATCH[4]}"
    note "MySQL $hostname:$dbport as $user"

    if [[ "$database_url" == *":3307/"* ]] && command -v docker >/dev/null 2>&1; then
      if docker inspect --format '{{.State.Health.Status}}' marketpulse-mysql 2>/dev/null | grep -q healthy; then
        ok "Docker container healthy"
      else
        fail "Docker container is not healthy (docker compose up -d)"
      fi
    fi

    if command -v mysql >/dev/null 2>&1; then
      if MYSQL_PWD="$password" mysql -h "$hostname" -P "$dbport" -u "$user" -e "SELECT 1;" >/dev/null 2>&1; then
        ok "MySQL answers and the credentials work"
      else
        fail "MySQL did not answer with those credentials"
      fi
    else
      note "The mysql client is not on PATH; skipped the direct probe."
    fi
  else
    fail "DATABASE_URL is not a mysql+pymysql:// URL"
  fi

  port="$(env_get "$BACKEND_ENV" PORT)"
  if [[ -n "$port" && "$(port_open "$port")" == "yes" ]]; then
    ok "Something is listening on the backend port $port"
    if curl -fsS "http://127.0.0.1:$port/health" >/dev/null 2>&1; then
      ok "API health: $(curl -fsS "http://127.0.0.1:$port/health")"
    else
      note "Port $port is busy but /health did not answer; it may be another service."
    fi
  else
    note "The backend is not running on port $port."
  fi

  model="$(env_get "$BACKEND_ENV" OPENROUTER_MODEL)"
  if [[ -n "$model" ]]; then
    local payload
    payload="$(fetch_free_models)"
    if [[ "$payload" == "ERROR" ]]; then
      note "Could not reach the OpenRouter catalogue."
    elif echo "$payload" | grep -q "\"id\": \"$model\""; then
      ok "OpenRouter model '$model' is free and available"
    else
      warn "OpenRouter model '$model' is not in the free list (paid, renamed, or removed)"
    fi
  fi
}

# --------------------------------------------------------------------------- #
# Applying a change to the running app
# --------------------------------------------------------------------------- #

# API keys and the LLM model are reloadable: the admin endpoint re-reads
# backend/.env and rebuilds the LLM client, so a running server picks the change
# up without dropping its database connections. The database URL and the port
# are bound at startup and need a real restart.
apply_change() {
  local kind="$1"
  local port
  port="$(env_get "$BACKEND_ENV" PORT)"
  [[ -z "$port" ]] && port="8010"

  if [[ "$(port_open "$port")" != "yes" ]]; then
    note "The API is not running; the change applies the next time you start it."
    return
  fi

  if [[ "$kind" == "reload" ]]; then
    local result
    if result="$(curl -fsS -X POST "http://127.0.0.1:$port/api/admin/reload" 2>/dev/null)"; then
      ok "The running API reloaded its configuration."
      echo "$result" | python3 -c '
import json, sys
data = json.load(sys.stdin)
print(f"         LLM: {data.get(\"llm\")}" + (f" ({data[\"llm_model\"]})" if data.get("llm_model") else ""))
changes = data.get("changes") or []
for change in changes:
    print(f"         changed: {change}")
' 2>/dev/null || true
    else
      warn "The API did not accept the reload. Restart it to be sure."
    fi
    return
  fi

  warn "This setting is bound when the backend starts."
  read -r -p "    Restart the app now? [Y/n] " answer
  if [[ "${answer,,}" =~ ^(n|no|nu)$ ]]; then
    note "Restart skipped. The change applies the next time you start the app."
    return
  fi

  local stopped=0 pid name
  for p in "$port" 5173; do
    command -v lsof >/dev/null 2>&1 || continue
    pid="$(lsof -iTCP:"$p" -sTCP:LISTEN -t 2>/dev/null | head -1 || true)"
    [[ -z "$pid" ]] && continue
    name="$(ps -p "$pid" -o comm= 2>/dev/null || echo "")"
    case "$name" in
      python*|node*) kill "$pid" 2>/dev/null && { ok "Stopped $name on port $p (PID $pid)"; stopped=1; } ;;
    esac
  done
  [[ "$stopped" -eq 0 ]] && note "Nothing of ours was running."

  sleep 2
  bash "$ROOT/scripts/start.sh" --backend-port "$port" --skip-database --detach
}

# --------------------------------------------------------------------------- #
# Menu
# --------------------------------------------------------------------------- #

if [[ "$SHOW_ONLY" -eq 1 ]]; then
  show_settings
  exit 0
fi

if [[ ! -f "$BACKEND_ENV" ]]; then
  fail "backend/.env does not exist. Run scripts/setup.sh first."
  exit 1
fi

while true; do
  clear 2>/dev/null || true
  printf '\n  \033[35mMarketPulse AI - settings\033[0m\n'
  printf '  \033[90m%s\033[0m\n\n' "$ROOT"
  printf '   \033[35m[1]\033[0m  Show        everything currently configured\n'
  printf '   \033[35m[2]\033[0m  Database    Docker, native MySQL, or another host\n'
  printf '   \033[35m[3]\033[0m  Port        the backend port and VITE_API_URL\n'
  printf '   \033[35m[4]\033[0m  OpenRouter  key and free model\n'
  printf '   \033[35m[5]\033[0m  Assistant   ollama / groq / gemini / off\n'
  printf '   \033[35m[6]\033[0m  X/Twitter   bearer token\n'
  printf '   \033[35m[7]\033[0m  Reddit      user agent\n'
  printf '   \033[35m[8]\033[0m  Check       verify the database, the port, the model\n'
  printf '   \033[90m[q]\033[0m  Back\n\n'

  read -r -p "  Choose an option: " choice
  case "${choice,,}" in
    1) show_settings ;;
    2) edit_database; apply_change "restart" ;;
    3) edit_port; apply_change "restart" ;;
    4) edit_openrouter; apply_change "reload" ;;
    5) edit_assistant; apply_change "reload" ;;
    6) edit_twitter; apply_change "reload" ;;
    7) edit_reddit; apply_change "reload" ;;
    8) check_connections ;;
    q|quit|exit) break ;;
    "") continue ;;
    *) warn "Unknown option: $choice"; sleep 1; continue ;;
  esac

  printf '\n'
  read -r -p "  Press Enter to return to the menu" _ || true
done

printf '\n  \033[90mDone.\033[0m\n\n'
