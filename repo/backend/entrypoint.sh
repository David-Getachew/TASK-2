#!/usr/bin/env bash
# Container entrypoint.
#
# Applies database migrations (alembic upgrade head) before starting the
# Uvicorn application process. Running migrations at boot guarantees the
# schema matches the deployed codebase without requiring an out-of-band
# operator step — this closes the audit finding about undocumented
# first-run DB bootstrap.
#
# The migration step is skipped when SKIP_MIGRATIONS=1 (used by test
# harnesses that manage their own schema via Base.metadata.create_all).
set -euo pipefail

if [[ "${SKIP_MIGRATIONS:-0}" != "1" ]]; then
  echo "[entrypoint] applying database migrations (alembic upgrade head)…"
  alembic upgrade head
else
  echo "[entrypoint] SKIP_MIGRATIONS=1 — skipping alembic upgrade"
fi

echo "[entrypoint] starting uvicorn…"
exec python -m uvicorn src.main:app \
  --host 0.0.0.0 \
  --port 8443 \
  --ssl-certfile /certs/cert.pem \
  --ssl-keyfile /certs/key.pem
