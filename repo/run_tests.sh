#!/usr/bin/env bash
# run_tests.sh — Docker-first test orchestration for MeritTrack
# Usage: bash run_tests.sh [suite]
# Suites: all (default), backend-unit, backend-api, frontend-unit, frontend-browser, frontend-browser-live, e2e
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
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
DEV_MATERIAL_DIR="$REPO_DIR/.dev-material"
DEV_CERT_DIR="$DEV_MATERIAL_DIR/certs"
DEV_SECRETS_DIR="$DEV_MATERIAL_DIR/secrets"
PROJECT_NAME="merittrack_test"
LIVE_PROJECT_NAME="${PROJECT_NAME}_live"
POSTGRES_USER_EFFECTIVE="${POSTGRES_USER:-merittrack}"
POSTGRES_PASSWORD_EFFECTIVE="${POSTGRES_PASSWORD:-merittrack_pw}"
DEMO_PASSWORD_EFFECTIVE="${DEMO_PASSWORD:-MeritTrack!23456}"

log() { echo "[run_tests] $*"; }

ensure_dev_crypto_material() {
  local cert_dir="$DEV_CERT_DIR"
  local secrets_dir="$DEV_SECRETS_DIR"
  local kek_dir="$secrets_dir/kek"

  mkdir -p "$cert_dir" "$kek_dir"

  if [ ! -f "$cert_dir/cert.pem" ] || [ ! -f "$cert_dir/key.pem" ]; then
    log "Generating local TLS cert/key for test stack..."
    docker run --rm -v "$DEV_MATERIAL_DIR:/work" -w /work alpine/openssl \
      req -x509 -newkey rsa:2048 -sha256 -nodes \
      -keyout certs/key.pem \
      -out certs/cert.pem \
      -days 365 \
      -subj "/CN=localhost" \
      -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
  fi

  if [ ! -f "$secrets_dir/jwt_private.pem" ]; then
    log "Generating local JWT private key for test stack..."
    docker run --rm -v "$DEV_MATERIAL_DIR:/work" -w /work alpine/openssl \
      genrsa -out secrets/jwt_private.pem 2048
  fi

  if [ ! -f "$secrets_dir/jwt_public.pem" ]; then
    log "Generating local JWT public key for test stack..."
    docker run --rm -v "$DEV_MATERIAL_DIR:/work" -w /work alpine/openssl \
      rsa -in secrets/jwt_private.pem -pubout -out secrets/jwt_public.pem
  fi

  if [ ! -f "$kek_dir/v1.key" ]; then
    log "Generating local KEK key material for test stack..."
    docker run --rm -v "$DEV_MATERIAL_DIR:/work" -w /work alpine/openssl \
      rand -out secrets/kek/v1.key 32
  fi
}

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
  start_db
  log "Running backend API tests against real Postgres..."
  docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" run --rm --no-deps \
    -e DATABASE_URL="postgresql+psycopg2://${POSTGRES_USER_EFFECTIVE}:${POSTGRES_PASSWORD_EFFECTIVE}@db:5432/merittrack" \
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
  ensure_dev_crypto_material

  log "Preparing isolated live backend stack for no-mock Playwright E2E..."
  TLS_CERT_DIR="$DEV_CERT_DIR" KEK_DIR="$DEV_SECRETS_DIR" \
    docker compose -f "$COMPOSE_FILE" -p "$LIVE_PROJECT_NAME" down -v --remove-orphans >/dev/null 2>&1 || true
  TLS_CERT_DIR="$DEV_CERT_DIR" KEK_DIR="$DEV_SECRETS_DIR" \
    docker compose -f "$COMPOSE_FILE" -p "$LIVE_PROJECT_NAME" build backend frontend-builder
  TLS_CERT_DIR="$DEV_CERT_DIR" KEK_DIR="$DEV_SECRETS_DIR" \
    docker compose -f "$COMPOSE_FILE" -p "$LIVE_PROJECT_NAME" up -d db backend

  log "Waiting for live backend health endpoint..."
  local attempts=60
  while [ $attempts -gt 0 ]; do
    if docker compose -f "$COMPOSE_FILE" -p "$LIVE_PROJECT_NAME" exec -T backend \
      curl -kf https://localhost:8443/api/v1/internal/health >/dev/null 2>&1; then
      log "Live backend is healthy."
      break
    fi
    attempts=$((attempts - 1))
    sleep 2
  done
  if [ $attempts -eq 0 ]; then
    echo "ERROR: Live backend did not become healthy in time" >&2
    TLS_CERT_DIR="$DEV_CERT_DIR" KEK_DIR="$DEV_SECRETS_DIR" \
      docker compose -f "$COMPOSE_FILE" -p "$LIVE_PROJECT_NAME" logs --no-color --tail=200 backend >&2 || true
    exit 1
  fi

  log "Seeding deterministic demo users for e2e..."
  TLS_CERT_DIR="$DEV_CERT_DIR" KEK_DIR="$DEV_SECRETS_DIR" \
    docker compose -f "$COMPOSE_FILE" -p "$LIVE_PROJECT_NAME" exec -T \
    -e ENVIRONMENT=development \
    -e DEMO_PASSWORD="$DEMO_PASSWORD_EFFECTIVE" \
    backend python seed_demo.py

  log "Ensuring a live catalog service item exists for e2e..."
  TLS_CERT_DIR="$DEV_CERT_DIR" KEK_DIR="$DEV_SECRETS_DIR" \
    docker compose -f "$COMPOSE_FILE" -p "$LIVE_PROJECT_NAME" exec -T backend python - <<'PY'
from decimal import Decimal
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from src.config import get_settings
from src.persistence.models.order import ServiceItem


def main() -> None:
    engine = create_engine(get_settings().database_url, future=True)
    try:
        with Session(engine) as session:
            existing = session.execute(select(ServiceItem).limit(1)).scalars().first()
            if existing is not None:
                print(f"service item exists: {existing.item_code}")
                return

            session.add(
                ServiceItem(
                    item_code="LIVE-E2E-001",
                    name="Live E2E Service",
                    description="Auto-seeded service for e2e",
                    pricing_mode="fixed",
                    fixed_price=Decimal("100.00"),
                    is_capacity_limited=False,
                    bargaining_enabled=True,
                    is_active=True,
                )
            )
            session.commit()
            print("created service item: LIVE-E2E-001")
    finally:
        engine.dispose()


main()
PY

  log "Running no-mock Playwright E2E suite..."
  TLS_CERT_DIR="$DEV_CERT_DIR" KEK_DIR="$DEV_SECRETS_DIR" \
    docker compose -f "$COMPOSE_FILE" -p "$LIVE_PROJECT_NAME" run --rm \
    -e API_PROXY_TARGET="https://backend:8443" \
    -e PLAYWRIGHT_HTML_OPEN=never \
    -e CI=1 \
    -e PW_ENABLE_LIVE_E2E=1 \
    -e PW_LIVE_USERNAME="${PW_LIVE_USERNAME:-demo_candidate}" \
    -e PW_LIVE_PASSWORD="${PW_LIVE_PASSWORD:-$DEMO_PASSWORD_EFFECTIVE}" \
    -e PW_LIVE_REVIEWER_USERNAME="${PW_LIVE_REVIEWER_USERNAME:-demo_reviewer}" \
    -e PW_LIVE_REVIEWER_PASSWORD="${PW_LIVE_REVIEWER_PASSWORD:-$DEMO_PASSWORD_EFFECTIVE}" \
    -e PW_LIVE_ADMIN_USERNAME="${PW_LIVE_ADMIN_USERNAME:-demo_admin}" \
    -e PW_LIVE_ADMIN_PASSWORD="${PW_LIVE_ADMIN_PASSWORD:-$DEMO_PASSWORD_EFFECTIVE}" \
    frontend-builder \
    sh -c "npx playwright install --with-deps chromium && npx playwright test --project=live"

  log "Stopping isolated live backend stack..."
  TLS_CERT_DIR="$DEV_CERT_DIR" KEK_DIR="$DEV_SECRETS_DIR" \
    docker compose -f "$COMPOSE_FILE" -p "$LIVE_PROJECT_NAME" down -v --remove-orphans >/dev/null 2>&1 || true
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
  e2e)
    run_frontend_browser_live
    ;;
  all)
    run_backend_unit
    run_backend_api
    run_frontend_unit
    run_frontend_browser
    run_frontend_browser_live
    log "All suites passed."
    ;;
  *)
    echo "Unknown suite: $SUITE" >&2
    echo "Usage: $0 [all|backend-unit|backend-api|frontend-unit|frontend-browser|frontend-browser-live|e2e]" >&2
    exit 1
    ;;
esac
