#!/usr/bin/env bash
# run_tests.sh — Docker-first test orchestration for MeritTrack
# Usage: bash run_tests.sh [suite]
# Suites: all (default), backend-unit, backend-api, frontend-unit, frontend-browser, frontend-browser-live
#
# Backend unit tests do not open a database; DATABASE_URL is set only to satisfy
# Settings validation. They run with --no-deps so Postgres is not started.
#
# Backend API tests run against a real Postgres: `db` is brought up first and
# DATABASE_URL is pointed at the db service. conftest.py creates the schema
# once and truncates all tables before every test for isolation. No FastAPI
# dependency overrides are installed, so route handlers exercise the full
# production DB wiring (asyncpg + Postgres types).
#
# frontend-builder is a run-once build step invoked via `docker compose run --rm
# frontend-builder ...`. It is required by `backend.depends_on` so it runs under
# the default profile on `docker compose up` — do NOT gate it behind a profile.

set -euo pipefail

SUITE="${1:-all}"
COMPOSE_FILE="$(dirname "$0")/docker-compose.yml"
PROJECT_NAME="merittrack_test"
POSTGRES_USER_EFFECTIVE="${POSTGRES_USER:-merittrack}"

log() { echo "[run_tests] $*"; }

require_docker() {
  if ! command -v docker &>/dev/null; then
    echo "ERROR: docker is not installed or not in PATH" >&2
    exit 1
  fi
  if ! docker info &>/dev/null; then
    echo "ERROR: Docker daemon is not running" >&2
    exit 1
  fi
}

require_postgres_password() {
  if [ -z "${POSTGRES_PASSWORD:-}" ]; then
    echo "ERROR: POSTGRES_PASSWORD must be exported for backend-api tests (real Postgres)" >&2
    echo "       e.g. export POSTGRES_PASSWORD=testpass" >&2
    exit 1
  fi
}

start_db() {
  log "Bringing up Postgres (db service)..."
  docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d db
  log "Waiting for Postgres to become healthy..."
  # Poll healthcheck up to ~60s.
  local attempts=30
  while [ $attempts -gt 0 ]; do
    if docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" exec -T db \
        pg_isready -U "$POSTGRES_USER_EFFECTIVE" -d merittrack >/dev/null 2>&1; then
      log "Postgres is ready."
      return 0
    fi
    attempts=$((attempts - 1))
    sleep 2
  done
  echo "ERROR: Postgres did not become healthy in time" >&2
  exit 1
}

run_backend_unit() {
  log "Running backend unit tests..."
  docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" run --rm --no-deps \
    -e DATABASE_URL="postgresql+psycopg2://${POSTGRES_USER_EFFECTIVE}:unused@localhost/unused" \
    -e SECRET_KEY="${SECRET_KEY:-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa}" \
    backend \
    python -m pytest unit_tests/ -v --tb=short
}

run_backend_api() {
  require_postgres_password
  start_db
  log "Running backend API tests against real Postgres..."
  docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" run --rm --no-deps \
    -e DATABASE_URL="postgresql+psycopg2://${POSTGRES_USER_EFFECTIVE}:${POSTGRES_PASSWORD}@db:5432/merittrack" \
    -e SECRET_KEY="${SECRET_KEY:-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa}" \
    backend \
    python -m pytest api_tests/ -v --tb=short
}

run_frontend_unit() {
  log "Running frontend unit tests..."
  docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" run --rm \
    frontend-builder \
    npx vitest run --reporter=verbose
}

run_frontend_browser() {
  log "Running frontend browser (Playwright) stubbed tests..."
  docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" run --rm \
    frontend-builder \
    sh -c "npx playwright install --with-deps chromium && npx playwright test unit_tests/browser/"
}

run_frontend_browser_live() {
  # No-mock end-to-end Playwright suite (repo/frontend/e2e/). Each spec is tagged
  # @live and skips silently unless PW_LIVE_* env vars are exported, mirroring
  # the existing live_auth_smoke.spec.ts pattern. A live backend must be reachable
  # via the Vite proxy (run `docker compose up` in another shell).
  #
  # Required env vars (forwarded into the container):
  #   PW_LIVE_USERNAME / PW_LIVE_PASSWORD               — candidate credentials
  #   PW_LIVE_REVIEWER_USERNAME / PW_LIVE_REVIEWER_PASSWORD
  #   PW_LIVE_ADMIN_USERNAME / PW_LIVE_ADMIN_PASSWORD
  log "Running no-mock Playwright E2E suite (requires live backend)..."
  docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" run --rm \
    -e PW_LIVE_USERNAME="${PW_LIVE_USERNAME:-}" \
    -e PW_LIVE_PASSWORD="${PW_LIVE_PASSWORD:-}" \
    -e PW_LIVE_REVIEWER_USERNAME="${PW_LIVE_REVIEWER_USERNAME:-}" \
    -e PW_LIVE_REVIEWER_PASSWORD="${PW_LIVE_REVIEWER_PASSWORD:-}" \
    -e PW_LIVE_ADMIN_USERNAME="${PW_LIVE_ADMIN_USERNAME:-}" \
    -e PW_LIVE_ADMIN_PASSWORD="${PW_LIVE_ADMIN_PASSWORD:-}" \
    frontend-builder \
    sh -c "npx playwright install --with-deps chromium && npx playwright test --project=live"
}

require_docker

case "$SUITE" in
  backend-unit)
    run_backend_unit
    ;;
  backend-api)
    run_backend_api
    ;;
  frontend-unit)
    run_frontend_unit
    ;;
  frontend-browser)
    run_frontend_browser
    ;;
  frontend-browser-live)
    run_frontend_browser_live
    ;;
  all)
    # `all` stays hermetic — frontend-browser-live is opt-in because it needs a
    # running backend and PW_LIVE_* credentials. Invoke it explicitly.
    run_backend_unit
    run_backend_api
    run_frontend_unit
    run_frontend_browser
    log "All suites passed."
    ;;
  *)
    echo "Unknown suite: $SUITE" >&2
    echo "Usage: $0 [all|backend-unit|backend-api|frontend-unit|frontend-browser|frontend-browser-live]" >&2
    exit 1
    ;;
esac
