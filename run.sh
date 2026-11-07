#!/usr/bin/env bash
#
# MarketPulse AI - interactive launcher for macOS / Linux.
#
#   ./run.sh
#
# One entry point for everything: cold setup, start, stop, status, tests and a
# database reset. It calls scripts/setup.sh and scripts/start.sh, so the
# behaviour is identical whether you use this menu or the scripts directly.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

SETUP_SCRIPT="$ROOT/scripts/setup.sh"
START_SCRIPT="$ROOT/scripts/start.sh"
BACKEND_ENV="$ROOT/backend/.env"
FRONTEND_ENV="$ROOT/.env.local"

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

banner() {
  clear 2>/dev/null || true
  printf '\n'
  printf '  \033[35m███  MarketPulse AI\033[0m\n'
  printf '       \033[90mMarket intelligence, in focus.\033[0m\n\n'
  printf '  \033[90m%s\033[0m\n\n' "$ROOT"
}

section() { printf '\n  \033[36m%s\033[0m\n  \033[90m%s\033[0m\n' "$1" "$(printf '─%.0s' $(seq 1 58))"; }
good()    { printf '  \033[32m✔\033[0m  %s\n' "$1"; }
bad()     { printf '  \033[31m✖\033[0m  %s\n' "$1"; }
info()    { printf '  \033[90m·\033[0m  %s\n' "$1"; }
warn()    { printf '  \033[33m!\033[0m  %s\n' "$1"; }

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

backend_port() {
  local port
  port="$(env_get "$BACKEND_ENV" PORT)"
  echo "${port:-8010}"
}

is_configured() { [[ -f "$BACKEND_ENV" && -f "$FRONTEND_ENV" ]]; }

# --------------------------------------------------------------------------- #
# Actions
# --------------------------------------------------------------------------- #

show_status() {
  section "Status"

  if ! is_configured; then
    warn "Not configured yet. Run option 1 (Setup)."
    return
  fi

  local url db_target port
  url="$(env_get "$BACKEND_ENV" DATABASE_URL)"
  db_target="${url#*@}"
  port="$(backend_port)"

  info "Database   ${db_target:-(unset)}"

  if [[ "$url" == *":3307/"* ]]; then
    if docker inspect --format '{{.State.Health.Status}}' marketpulse-mysql 2>/dev/null | grep -q healthy; then
      good "Docker MySQL container healthy"
    else
      bad "Docker MySQL container is not healthy (docker compose up -d)"
    fi
  fi

  if [[ "$(port_open "$port")" == "yes" ]]; then
    good "Backend answering on http://127.0.0.1:$port"
    if curl -fsS "http://127.0.0.1:$port/health" >/dev/null 2>&1; then
      local health
      health="$(curl -fsS "http://127.0.0.1:$port/health")"
      if echo "$health" | grep -q '"database":"healthy"'; then
        good "Database reachable from the API"
      else
        bad "API reports: $health"
      fi
      info "LLM        $(echo "$health" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("llm","?") + (f" ({d[\"llm_model\"]})" if d.get("llm_model") else ""))' 2>/dev/null || echo "?")"
    fi
  else
    bad "Backend is not running"
  fi

  if [[ "$(port_open 5173)" == "yes" ]]; then
    good "Frontend answering on http://127.0.0.1:5173"
  else
    bad "Frontend is not running"
  fi

  local assistant twitter
  assistant="$(env_get "$BACKEND_ENV" AI_PROVIDER)"
  twitter="$(env_get "$BACKEND_ENV" TWITTER_BEARER_TOKEN)"
  info "Assistant  ${assistant:-disabled}"
  info "X/Twitter  $([[ -n "$twitter" ]] && echo configured || echo "not configured")"
}

run_setup() {
  section "Cold setup"
  info "Detects Docker and a native MySQL, asks which to use, then asks for API keys."
  echo ""
  bash "$SETUP_SCRIPT"
}

run_start() {
  if ! is_configured; then
    section "Start"
    bad "Not configured yet."
    read -r -p "  Run the setup now? [y/N] " answer
    if [[ "$answer" =~ ^(y|yes|da)$ ]]; then run_setup; fi
    return
  fi
  section "Starting"
  info "Ctrl+C stops the backend and the frontend. The database container keeps running."
  echo ""
  bash "$START_SCRIPT" --backend-port "$(backend_port)"
}

run_stop() {
  section "Stop"
  local stopped=0 port pid name

  for port in "$(backend_port)" 8020 5173; do
    if command -v lsof >/dev/null 2>&1; then
      pid="$(lsof -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null | head -1 || true)"
      [[ -z "$pid" ]] && continue
      name="$(ps -p "$pid" -o comm= 2>/dev/null || echo "")"
      case "$name" in
        python*|node*)
          kill "$pid" 2>/dev/null && { good "Stopped $name on port $port (PID $pid)"; stopped=1; }
          ;;
      esac
    fi
  done

  [[ "$stopped" -eq 0 ]] && info "Nothing was running on the project ports."

  read -r -p "  Stop the MySQL container too? [y/N] " answer
  if [[ "$answer" =~ ^(y|yes|da)$ ]]; then
    docker compose stop >/dev/null 2>&1 && good "MySQL container stopped (data kept)"
  fi
}

run_settings() {
  local script="$ROOT/scripts/settings.sh"
  if [[ ! -f "$script" ]]; then
    bad "scripts/settings.sh is missing."
    return
  fi
  bash "$script"
}

run_reload() {
  section "Apply keys without a restart"
  local port
  port="$(backend_port)"

  if [[ "$(port_open "$port")" != "yes" ]]; then
    warn "The backend is not running, so there is nothing to reload."
    info "Start it with option 2; the settings in backend/.env are read at startup."
    return
  fi

  local result
  if result="$(curl -fsS -X POST "http://127.0.0.1:$port/api/admin/reload" 2>/dev/null)"; then
    good "The running API reloaded its configuration."
    echo "$result" | python3 -c '
import json, sys
data = json.load(sys.stdin)
print(f"         LLM: {data.get(\"llm\")}" + (f" ({data[\"llm_model\"]})" if data.get("llm_model") else ""))
changes = data.get("changes") or []
if changes:
    for change in changes:
        print(f"         changed: {change}")
else:
    print("         No value changed relative to what the process already held.")
' 2>/dev/null || true
    info "Database and port changes still need a restart (option 3 then 2)."
  else
    warn "The API did not accept the reload. Restart it with option 3 then 2."
  fi
}

run_tests() {
  section "Tests"
  local failed=0

  info "Backend unit and contract tests (scratch database)"
  ( cd "$ROOT/backend" && python3 -m pytest tests -q --no-header -p no:warnings ) || failed=$((failed + 1))

  echo ""
  info "Production build"
  npm run build >/tmp/mp-build.log 2>&1 && tail -3 /tmp/mp-build.log || { failed=$((failed + 1)); tail -20 /tmp/mp-build.log; }

  echo ""
  if [[ "$(port_open "$(backend_port)")" == "yes" && "$(port_open 5173)" == "yes" ]]; then
    info "End-to-end tests (Playwright)"
    npx playwright test --reporter=list 2>&1 | tail -6 || failed=$((failed + 1))
  else
    warn "End-to-end tests skipped: the app is not running. Start it with option 2."
  fi

  echo ""
  if [[ "$failed" -eq 0 ]]; then good "Everything passed."; else bad "$failed suite(s) failed."; fi
}

run_reset_db() {
  section "Reset database"
  local url
  url="$(env_get "$BACKEND_ENV" DATABASE_URL)"
  if [[ -z "$url" ]]; then bad "No DATABASE_URL in backend/.env."; return; fi
  if [[ "$url" != *":3307/"* ]]; then
    warn "This only works for the Docker database."
    info "For a native server, drop and recreate the schema yourself."
    return
  fi

  warn "This deletes every row in the marketpulse database and reseeds it."
  info "The schema and the seed are recreated on the next backend start."
  read -r -p "  Type RESET to continue: " answer
  [[ "$answer" != "RESET" ]] && { info "Cancelled."; return; }

  docker exec marketpulse-mysql mysql -u marketpulse -pmarketpulse \
    -e "DROP DATABASE IF EXISTS marketpulse; CREATE DATABASE marketpulse CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" >/dev/null 2>&1
  good "Database dropped and recreated"
  info "Restart the backend (option 2) so the seed runs again."
}

run_docs() {
  section "Documentation"
  info "README.md                     setup, ports, troubleshooting"
  info "docs/BRIEF-MarketPulse.md     what the project is and what changed"
  info ".orchestration/               queue, working notes, handoff, specs"
  echo ""
  if [[ "$(port_open "$(backend_port)")" == "yes" ]]; then
    read -r -p "  Open the API docs in the browser? [y/N] " answer
    if [[ "$answer" =~ ^(y|yes|da)$ ]]; then
      xdg-open "http://127.0.0.1:$(backend_port)/docs" >/dev/null 2>&1 || open "http://127.0.0.1:$(backend_port)/docs" >/dev/null 2>&1 || true
    fi
  else
    info "Start the app to browse the API docs at /docs."
  fi
}

# --------------------------------------------------------------------------- #
# Menu
# --------------------------------------------------------------------------- #

while true; do
  banner

  if is_configured; then
    backend_text="backend down"; frontend_text="frontend down"
    [[ "$(port_open "$(backend_port)")" == "yes" ]] && backend_text="backend up"
    [[ "$(port_open 5173)" == "yes" ]] && frontend_text="frontend up"
    printf '  \033[90m%s · %s\033[0m\n' "$backend_text" "$frontend_text"
  else
    printf '  \033[33mnot configured yet\033[0m\n'
  fi

  printf '\n'
  printf '   \033[35m[1]\033[0m  Setup       install everything, choose the database, add API keys\n'
  printf '   \033[35m[2]\033[0m  Start       run the database, the backend and the dashboard\n'
  printf '   \033[35m[3]\033[0m  Stop        stop the backend and the frontend\n'
  printf '   \033[35m[4]\033[0m  Status      what is running and what is configured\n'
  printf '   \033[35m[5]\033[0m  Settings    database, port, API keys, LLM model\n'
  printf '   \033[35m[6]\033[0m  Reload      apply new API keys without a restart\n'
  printf '   \033[35m[7]\033[0m  Tests       backend, build and end-to-end\n'
  printf '   \033[35m[8]\033[0m  Reset DB    drop and reseed the Docker database\n'
  printf '   \033[35m[9]\033[0m  Docs        where the documentation lives\n'
  printf '   \033[90m[q]\033[0m  Quit\n\n'

  read -r -p "  Choose an option: " choice
  case "${choice,,}" in
    1) run_setup ;;
    2) run_start ;;
    3) run_stop ;;
    4) show_status ;;
    5) run_settings ;;
    6) run_reload ;;
    7) run_tests ;;
    8) run_reset_db ;;
    9) run_docs ;;
    q|quit|exit) break ;;
    "") continue ;;
    *) warn "Unknown option: $choice"; sleep 1; continue ;;
  esac

  echo ""
  read -r -p "  Press Enter to return to the menu" _ || true
done

printf '\n  \033[90mBye.\033[0m\n\n'
