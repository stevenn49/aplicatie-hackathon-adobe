#!/usr/bin/env bash
#
# Start MarketPulse AI (database, backend, frontend) on macOS / Linux.
#
#   ./scripts/start.sh
#   ./scripts/start.sh --backend-port 8010 --frontend-port 5173
#   ./scripts/start.sh --skip-database
#
# Ctrl+C stops the two processes this script started; the database container
# keeps running.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND_PORT=8010
FRONTEND_PORT=5173
SKIP_DATABASE=0
DETACH=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backend-port) BACKEND_PORT="$2"; shift 2 ;;
    --frontend-port) FRONTEND_PORT="$2"; shift 2 ;;
    --skip-database) SKIP_DATABASE=1; shift ;;
    --detach) DETACH=1; shift ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

step() { printf '\n==> %s\n' "$1"; }
ok()   { printf '    OK  %s\n' "$1"; }
fail() { printf '    X   %s\n' "$1" >&2; }

if [[ ! -f backend/.env ]]; then
  fail "backend/.env is missing. Run ./scripts/setup.sh first."
  exit 1
fi

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
if [[ "$SKIP_DATABASE" -eq 0 ]]; then
  step "Ensuring the database is running"
  if grep -q ':3307/' backend/.env && [[ -f docker-compose.yml ]]; then
    docker compose up -d
    for _ in $(seq 1 60); do
      status="$(docker inspect --format '{{.State.Health.Status}}' marketpulse-mysql 2>/dev/null || true)"
      [[ "$status" == "healthy" ]] && break
      sleep 2
    done
    if [[ "$status" != "healthy" ]]; then
      fail "MySQL container is not healthy. Run: docker compose logs mysql"
      exit 1
    fi
    ok "MySQL container healthy"
  else
    ok "Using the MySQL server configured in backend/.env"
  fi
fi

# ---------------------------------------------------------------------------
# Ports
# ---------------------------------------------------------------------------
# A port held by our own backend or frontend is not an error: report it and skip
# that component instead of starting a second copy. A foreign process is a hard
# stop.
already_running=0
for port in "$BACKEND_PORT" "$FRONTEND_PORT"; do
  command -v lsof >/dev/null 2>&1 || continue
  pid="$(lsof -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null | head -1 || true)"
  [[ -z "$pid" ]] && continue
  name="$(ps -p "$pid" -o comm= 2>/dev/null || echo "")"
  case "$name" in
    python*|node*)
      warn "$name is already listening on port $port (PID $pid)."
      already_running=$((already_running + 1))
      ;;
    *)
      fail "Port $port is held by '$name' (PID $pid), which is not part of this project."
      exit 1
      ;;
  esac
done

if [[ "$already_running" -eq 2 ]]; then
  ok "The app is already running: http://127.0.0.1:$FRONTEND_PORT"
  printf '    To restart it, use option 3 (Stop) then option 2 (Start), or the settings manager.\n' >&2
  exit 0
fi

# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------
BACKEND_LOG="${TMPDIR:-/tmp}/marketpulse-backend.log"
BACKEND_PID=""

if [[ "$(port_open "$BACKEND_PORT")" == "yes" ]]; then
  step "Backend already running on $BACKEND_PORT"
  ok "Leaving it alone"
else
  step "Starting the backend on $BACKEND_PORT"
  (
    cd backend
    exec python3 -m uvicorn main:app --host 127.0.0.1 --port "$BACKEND_PORT"
  ) >"$BACKEND_LOG" 2>&1 &
  BACKEND_PID=$!

  ready=0
  for _ in $(seq 1 45); do
    if curl -fsS "http://127.0.0.1:$BACKEND_PORT/health" >/dev/null 2>&1; then ready=1; break; fi
    sleep 2
  done
  if [[ "$ready" -ne 1 ]]; then
    fail "The backend did not start. Last lines of $BACKEND_LOG:"
    tail -20 "$BACKEND_LOG" >&2 || true
    kill "$BACKEND_PID" 2>/dev/null || true
    exit 1
  fi
  ok "Backend healthy: $(curl -fsS "http://127.0.0.1:$BACKEND_PORT/health")"
fi

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------
FRONTEND_LOG="${TMPDIR:-/tmp}/marketpulse-frontend.log"
FRONTEND_PID=""

if [[ "$(port_open "$FRONTEND_PORT")" == "yes" ]]; then
  step "Frontend already running on $FRONTEND_PORT"
  ok "Leaving it alone"
else
  step "Starting the frontend on $FRONTEND_PORT"
  npm run dev -- --port "$FRONTEND_PORT" --host 127.0.0.1 >"$FRONTEND_LOG" 2>&1 &
  FRONTEND_PID=$!

  vite_ready=0
  for _ in $(seq 1 45); do
    if curl -fsS "http://127.0.0.1:$FRONTEND_PORT/" >/dev/null 2>&1; then vite_ready=1; break; fi
    sleep 2
  done
  if [[ "$vite_ready" -ne 1 ]]; then
    fail "The frontend did not start. Last lines of $FRONTEND_LOG:"
    tail -20 "$FRONTEND_LOG" >&2 || true
    [[ -n "$BACKEND_PID" ]] && kill "$BACKEND_PID" 2>/dev/null || true
    kill "$FRONTEND_PID" 2>/dev/null || true
    exit 1
  fi
  ok "Frontend serving"
fi

printf '\nMarketPulse AI is running.\n\n'
printf '  Dashboard : http://127.0.0.1:%s\n' "$FRONTEND_PORT"
printf '  API       : http://127.0.0.1:%s\n' "$BACKEND_PORT"
printf '  API docs  : http://127.0.0.1:%s/docs\n\n' "$BACKEND_PORT"
printf '  Logs      : %s\n              %s\n\n' "$BACKEND_LOG" "$FRONTEND_LOG"

# --detach: the caller (setup or settings) keeps the processes running and
# returns to its own flow.
if [[ "$DETACH" -eq 1 ]]; then
  printf 'Started in the background. Stop it with ./run.sh (option 3).\n'
  exit 0
fi

cleanup() {
  printf '\nStopping the processes this script started...\n'
  [[ -n "$BACKEND_PID" ]] && kill "$BACKEND_PID" 2>/dev/null || true
  [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
  wait 2>/dev/null || true
  printf 'Stopped. The database container is left running.\n'
}
trap cleanup EXIT INT TERM

if [[ -z "$BACKEND_PID" && -z "$FRONTEND_PID" ]]; then
  printf 'Both components were already running; nothing to wait for.\n'
  trap - EXIT INT TERM
  exit 0
fi

printf 'Press Ctrl+C to stop.\n'
wait
