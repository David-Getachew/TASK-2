# MeritTrack — Admissions & Transaction Operations Platform

A full-stack offline-ready platform that unifies candidate onboarding, document management, fee-based service ordering (with bargaining), attendance exception handling, and staff operational queues. Designed to operate inside a disconnected facility network with no reliance on external internet services.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | Vue 3, TypeScript, Vite, Vue Router, Pinia |
| Frontend Testing | Vitest, Vue Test Utils, Playwright |
| Backend | Python 3.10, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic |
| Backend Testing | Pytest, HTTPX, pytest-asyncio |
| Database | PostgreSQL 14+ |
| Document Storage | Local filesystem (configurable mount path) |
| Auth | Local username/password, Argon2id, 15-min JWT + refresh, internal IdP |
| TLS | Docker-generated local certificates or internal CA-issued certificates |
| Containerization | Docker Compose |

---

## Repository Structure

```
TASK-2/
├── docs/
│   ├── design.md                    # Architecture, topology, security, module boundaries
│   ├── api-spec.md                  # Endpoint groups, envelopes, error model, headers
│   ├── questions.md                 # Ambiguity log (The Gap / Interpretation / Implementation)
│   ├── requirement-traceability.md  # Requirement → module mapping
│   └── test-traceability.md         # Requirement/endpoint → test file mapping
├── repo/
│   ├── README.md                    # This file
│   ├── docker-compose.yml           # All services: backend, db (PostgreSQL), frontend-builder (dist copy)
│   ├── run_tests.sh                 # Docker-first test orchestration
│   ├── frontend/
│   │   ├── Dockerfile
│   │   ├── src/
│   │   │   ├── main.ts              # Vue app entry point
│   │   │   ├── App.vue              # Root component
│   │   │   ├── router/              # Vue Router configuration
│   │   │   ├── stores/              # Pinia stores
│   │   │   ├── services/            # API client adapters, request signer, offline queue
│   │   │   ├── composables/         # Shared Vue composables (auth, permissions, feature flags)
│   │   │   ├── views/               # Page-level components (candidate/, staff/, admin/, auth/)
│   │   │   ├── components/          # Reusable UI components
│   │   │   ├── types/               # TypeScript type definitions
│   │   │   └── utils/               # Pure utility functions (datetime, format, validation)
│   │   ├── public/                  # Static assets (favicon, etc.)
│   │   ├── unit_tests/              # Vitest unit tests + Playwright browser workflow tests
│   │   │   └── browser/             # Playwright specs
│   │   ├── package.json
│   │   ├── vite.config.ts
│   │   ├── tsconfig.json
│   │   ├── vitest.config.ts
│   │   └── playwright.config.ts
│   └── backend/
│       ├── Dockerfile
│       ├── src/
│       │   ├── main.py              # FastAPI application + static file mount
│       │   ├── config.py            # Centralized configuration via env vars
│       │   ├── api/                 # FastAPI routers (one file per domain group)
│       │   ├── schemas/             # Pydantic v2 request/response schemas
│       │   ├── domain/              # Business rules: order state machine, bargaining, etc.
│       │   ├── services/            # Application services (orchestrate domain + persistence)
│       │   ├── persistence/         # SQLAlchemy repositories
│       │   ├── security/            # Auth, JWT, RBAC, encryption, watermark, signing, nonce
│       │   ├── workers/             # Background jobs: auto-cancel, forecasting, cache stats
│       │   ├── telemetry/           # Structured logging, metrics, trace correlation
│       │   └── storage/             # Local filesystem document store
│       ├── database/
│       │   └── migrations/          # Alembic migration files
│       ├── unit_tests/              # Pytest unit tests (domain logic, schemas, config)
│       ├── api_tests/               # Pytest + HTTPX no-mock API/integration tests
│       ├── requirements.txt
│       └── alembic.ini
├── sessions/                        # DO NOT TOUCH
├── execution_plan.md
├── metadata.json
└── CLAUDE.md
```

---

## Offline / Local Constraints

- **No internet egress required at runtime.** All services run locally.
- **No external IdP.** Authentication is strictly local username/password with an internal token issuer.
- **No external CDN.** The compiled Vue frontend is served by the same FastAPI process.
- **No cloud storage.** Documents, exports, and logs are stored on a local mounted filesystem.
- **No hosted payment gateway.** Payment records are local operational data managed by staff queues.
- **No external observability SaaS.** Metrics, logs, and traces are local.
- **TLS certificates** must be provisioned locally before first startup (see Configuration below).

---

## Services and Ports

| Service | Port | Notes |
|---|---|---|
| FastAPI (backend + frontend assets) | 8443 (HTTPS) | Primary application endpoint |
| PostgreSQL | 5432 | Internal; not exposed outside compose network |

---

## Configuration

All configuration is driven by environment variables. Copy `repo/backend/.env.example` to `repo/backend/.env` and fill in the required values:

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL DSN (e.g., `postgresql+psycopg2://user:pass@db:5432/merittrack`) |
| `SECRET_KEY` | Legacy HMAC secret (unused once RS256 keys are mounted; kept for transitional tooling) |
| `JWT_ALGORITHM` | JWT algorithm; default `RS256` |
| `JWT_PRIVATE_KEY_PATH` | Mounted RSA-2048 private key (PEM). Default `/secrets/jwt_private.pem` |
| `JWT_PUBLIC_KEY_PATH` | Mounted RSA-2048 public key (PEM). Default `/secrets/jwt_public.pem` |
| `JWT_KEY_ID` | `kid` published in JWKS; default `mt-signing-1` |
| `KEK_PATH` | Directory holding KEK versions (`v1.key`, `v2.key`, …), each 32 raw bytes |
| `LOGIN_THROTTLE_MAX_ATTEMPTS` | Default `5` |
| `LOGIN_THROTTLE_WINDOW_MINUTES` | Default `15` |
| `LOGIN_LOCKOUT_MINUTES` | Default `15` |
| `WEBCRYPTO_FALLBACK_ENABLED` | Default `false` — enables the HMAC-in-IndexedDB signing fallback for browsers without non-extractable ECDSA support (see `docs/questions.md`) |
| `TLS_CERT_PATH` | Path to the TLS certificate file |
| `TLS_KEY_PATH` | Path to the TLS private key file |
| `STORAGE_ROOT` | Root path for local document storage (default: `/data/uploads`) |
| `EXPORTS_ROOT` | Root path for watermarked exports (default: `/data/exports`) |
| `ACCESS_LOG_ROOT` | Root path for structured access logs (default: `/data/access-logs`) |
| `ENVIRONMENT` | `development` or `production` |

### Security & Configuration

Required secret material (mounted at runtime, never committed):

| File | Purpose | Generation |
|---|---|---|
| `/secrets/jwt_private.pem` | RSA-2048 private key for access/IdP tokens | `docker run --rm -v "$PWD:/work" -w /work alpine/openssl genrsa -out secrets/jwt_private.pem 2048` |
| `/secrets/jwt_public.pem` | RSA-2048 public key (published via JWKS) | `docker run --rm -v "$PWD:/work" -w /work alpine/openssl rsa -in secrets/jwt_private.pem -pubout -out secrets/jwt_public.pem` |
| `<KEK_PATH>/v1.key` | 32-byte KEK for envelope encryption; add `v2.key`, … to rotate | `docker run --rm -v "$PWD:/work" -w /work alpine/openssl rand -out secrets/kek/v1.key 32` |
| `/certs/cert.pem` | HTTPS certificate | `docker run --rm -v "$PWD:/work" -w /work alpine/openssl req -x509 -newkey rsa:2048 -sha256 -nodes -keyout certs/key.pem -out certs/cert.pem -days 365 -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"` |
| `/certs/key.pem` | HTTPS private key | (generated together with cert.pem above) |

Routes where the backend requires an ECDSA-signed request (frontend mirrors this list in `services/http.ts`):

- `POST /api/v1/auth/password/change`
- `POST /api/v1/auth/device/activate`
- `POST /api/v1/auth/device/{device_id}/rotate`
- `POST /api/v1/candidates/{candidate_id}/documents/upload`
- `POST /api/v1/orders`
- `POST /api/v1/orders/{order_id}/bargaining/offer`
- `POST /api/v1/attendance/exceptions`

Device registration flow (summary):

1. Browser generates a non-extractable ECDSA P-256 keypair via `crypto.subtle.generateKey`.
2. Client calls `POST /api/v1/auth/device/challenge` → receives `{ challenge_id, nonce }` (5-min validity).
3. Client signs the challenge nonce with the private key and calls `POST /api/v1/auth/device/activate`.
4. Client submits the SPKI-PEM public key to `POST /api/v1/auth/device/register`; server returns `device_id` and stores it with `fingerprint`, `public_key_pem`.
5. All subsequent signed requests include `X-Device-ID`, `X-Timestamp`, `X-Nonce`, `X-Request-Signature`.
6. `POST /api/v1/auth/device/{id}/rotate` swaps the key and `DELETE /api/v1/auth/device/{id}` revokes it.

Health and observability endpoints:

- `GET /api/v1/internal/health` — liveness probe (unauthenticated).
- `GET /api/v1/internal/metrics` — Prometheus text exposition (admin JWT required; intended for local Prometheus scraping by privileged operators).

---

## Certificate and Key Prerequisites

The following files must exist before `docker compose up`. Generate them with Docker commands only (no host-local package installs).

| File | Purpose | Generation Command |
|---|---|---|
| `./certs/cert.pem` | TLS certificate | `docker run --rm -v "$PWD:/work" -w /work alpine/openssl req -x509 -newkey rsa:2048 -sha256 -nodes -keyout certs/key.pem -out certs/cert.pem -days 365 -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"` |
| `./certs/key.pem` | TLS private key | (generated together with cert.pem above) |
| `./secrets/kek/v1.key` | AES-256 key-encryption key (32 raw bytes); `KEK_PATH` points to the directory, active key is `<KEK_PATH>/<KEK_CURRENT_VERSION>.key` | `docker run --rm -v "$PWD:/work" -w /work alpine/openssl rand -out secrets/kek/v1.key 32` |
| `./secrets/jwt_private.pem` | RS256 JWT signing key | `docker run --rm -v "$PWD:/work" -w /work alpine/openssl genrsa -out secrets/jwt_private.pem 2048` |
| `./secrets/jwt_public.pem` | RS256 JWT verification key | `docker run --rm -v "$PWD:/work" -w /work alpine/openssl rsa -in secrets/jwt_private.pem -pubout -out secrets/jwt_public.pem` |

```bash
# One-time setup (from repo/ directory)
mkdir -p certs secrets/kek
docker run --rm -v "$PWD:/work" -w /work alpine/openssl req -x509 -newkey rsa:2048 -sha256 -nodes -keyout certs/key.pem -out certs/cert.pem -days 365 -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
docker run --rm -v "$PWD:/work" -w /work alpine/openssl rand -out secrets/kek/v1.key 32
docker run --rm -v "$PWD:/work" -w /work alpine/openssl genrsa -out secrets/jwt_private.pem 2048
docker run --rm -v "$PWD:/work" -w /work alpine/openssl rsa -in secrets/jwt_private.pem -pubout -out secrets/jwt_public.pem
```

---

## Starting the Application

```bash
cd repo

# Build and start all services (requires cert/key prereqs above)
docker compose up --build

# Run with pre-built images
docker compose up
```

The application will be available at `https://localhost:8443`.

### Database migrations on boot

The backend container entrypoint (`repo/backend/entrypoint.sh`) runs
`alembic upgrade head` before starting Uvicorn, so a fresh container
brings an empty database up to the latest schema automatically. No
manual migration step is required for the documented startup path.

If you need to run migrations manually (for example, when running the
backend outside Docker), from `repo/backend/` execute:

```bash
alembic upgrade head
```

To skip the automatic migration at container boot — typically only for
test harnesses that manage their own schema via `Base.metadata.create_all`
— set `SKIP_MIGRATIONS=1` in the environment.

---

## Demo Credentials (development only)

The platform requires authentication for all non-public routes. For local verification, seed deterministic demo users (one per role) via the bundled helper:

```bash
cd repo

# One-time: seed demo users after `docker compose up` is running
docker compose exec -e ENVIRONMENT=development backend python seed_demo.py
```

| Role | Username | Password |
|---|---|---|
| Candidate | `demo_candidate` | `MeritTrack!23456` |
| Reviewer | `demo_reviewer` | `MeritTrack!23456` |
| Admin | `demo_admin` | `MeritTrack!23456` |
| Proctor | `demo_proctor` | `MeritTrack!23456` |

Override the password with `DEMO_PASSWORD=<value>` on the `docker compose exec` command. The seed script refuses to run when `ENVIRONMENT=production`.

> **⚠ Dev/test only.** These credentials exist solely for local verification and the no-mock Playwright suite. Do not ship them to a production environment — re-seed with strong passwords (or disable the helper) before any real deployment.

---

## Verifying the System (acceptance checks)

After `docker compose up` and seeding demo users, run these concrete checks to confirm the system is operational.

### 1. Health probe (no auth)

```bash
curl -k https://localhost:8443/api/v1/internal/health
```

**Expected:** HTTP 200 with body
```json
{"success": true, "data": {"status": "ok"}, "meta": {"trace_id": "..."}}
```

### 2. Authenticated login (admin role)

```bash
curl -k -X POST https://localhost:8443/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"demo_admin\",
    \"password\": \"MeritTrack!23456\",
    \"nonce\": \"n-$(uuidgen)\",
    \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
  }"
```

**Expected:** HTTP 200, body contains `"access_token"`, `"refresh_token"`, `"role": "admin"`, `"expires_in": 900`.

### 3. Authorized admin call

```bash
TOKEN=<access_token from step 2>
curl -k https://localhost:8443/api/v1/admin/feature-flags \
  -H "Authorization: Bearer $TOKEN"
```

**Expected:** HTTP 200 with `"success": true` and a `data` array of feature-flag objects.

### 4. Frontend UI verification

Open `https://localhost:8443` in a browser (accept the self-signed certificate) and verify:

1. The login page renders.
2. Logging in as `demo_candidate` redirects to the candidate dashboard with navigation items for Profile, Documents, Services, Bargaining, and Attendance.
3. Logging in as `demo_admin` redirects to the admin layout and the `/admin/config` page lists feature flags.
4. Logging out returns to the login page.

All four steps passing → system verified.

---

## Running Tests

Frontend tests run inside the `frontend-builder` container. Backend unit tests are hermetic. Backend API tests run against a real Postgres (the `db` service) — no SQLite, no dependency overrides, so every route exercises production DB wiring. All suites are Docker-first.

```bash
cd repo

# Run all test suites
bash run_tests.sh

# Individual suites
bash run_tests.sh backend-unit
bash run_tests.sh backend-api
bash run_tests.sh frontend-unit
bash run_tests.sh frontend-browser

# Optional: no-mock end-to-end Playwright suite against a real local backend
bash run_tests.sh frontend-browser-live
```

**Suite summary:**

| Suite | Runner | DB | Service Deps |
|---|---|---|---|
| `backend-unit` | `pytest unit_tests/` in backend container | None (pure logic) | None (`--no-deps`) |
| `backend-api` | `pytest api_tests/` in backend container | **Real Postgres** (auto-started `db` service) | `db` |
| `frontend-unit` | `npx vitest run` in frontend-builder | N/A | None |
| `frontend-browser` | `npx playwright test --project=chromium` (stubbed specs under `unit_tests/browser/`) | N/A | Vite dev server (auto-started) |
| `frontend-browser-live` | `npx playwright test --project=live` (no-mock specs under `e2e/`) | Live backend DB | Live backend + Vite proxy |

> `backend-api` now requires `POSTGRES_PASSWORD` to be exported before invocation (the `db` service validates it on startup). `run_tests.sh` fails fast if the variable is unset.

Notes:
- `npm run test:browser` runs the `chromium` project only — stubbed UI-logic specs with `page.route()`.
- `npm run test:browser:live` runs the `live` project only — every spec in `frontend/e2e/` drives real HTTPS through the Vite `/api` proxy (no stubs, no mocked responses).

### Running the no-mock E2E suite

The `frontend/e2e/` suite exercises real end-to-end journeys against a running backend. Every spec is tagged `@live` and **skips silently** when required env vars are not set, so hermetic CI stays green.

Required env vars (export before running):

| Variable | Used by |
|---|---|
| `PW_LIVE_USERNAME`, `PW_LIVE_PASSWORD` | candidate-role specs |
| `PW_LIVE_REVIEWER_USERNAME`, `PW_LIVE_REVIEWER_PASSWORD` | reviewer-role specs |
| `PW_LIVE_ADMIN_USERNAME`, `PW_LIVE_ADMIN_PASSWORD` | admin-role specs |

```bash
# In one shell: start the real backend
cd repo && docker compose up

# In another shell: export creds and run the live suite
cd repo
export PW_LIVE_USERNAME=<candidate>
export PW_LIVE_PASSWORD=<candidate_password>
export PW_LIVE_REVIEWER_USERNAME=<reviewer>
export PW_LIVE_REVIEWER_PASSWORD=<reviewer_password>
export PW_LIVE_ADMIN_USERNAME=<admin>
export PW_LIVE_ADMIN_PASSWORD=<admin_password>
bash run_tests.sh frontend-browser-live
```

---

## Storage Paths (configurable, not hardcoded)

| Purpose | Default Container Path | Configured By |
|---|---|---|
| Document uploads | `/data/uploads` | `STORAGE_ROOT` env var |
| Watermarked exports | `/data/exports` | `EXPORTS_ROOT` env var |
| Structured access logs | `/data/access-logs` | `ACCESS_LOG_ROOT` env var |
| Forecast snapshots | `/data/forecasts` | `FORECASTS_ROOT` env var |
| TLS certificates | `/certs/` | `TLS_CERT_PATH`, `TLS_KEY_PATH` env vars |

---

## Frontend Application (Prompts 5 & 6)

The Vue 3 frontend implements all primary user workflows with offline support:

### Screens and Flows

**Candidate flows:**
- Login → role-based redirect to candidate/staff/admin layout
- Profile: view/edit personal info, manage exam scores and transfer preferences
- Documents: checklist of requirements, upload (drag-and-drop with client-side MIME/size validation), resubmission status with reason
- Services & Orders: service catalog with capacity and bargaining indicators; order detail with countdown timer for auto-cancel; payment proof form with duplicate-submit guard
- Bargaining: submit offers within 48h window, view counter-offer, accept counter; offers-remaining counter
- Attendance Exceptions: list view, detail with proof upload, review history
- After-Sales / Refund request: candidate-initiated form at `/candidate/orders/:orderId/after-sales` with prior-request history (complaint / refund_request)

**Staff/Reviewer flows:**
- Staff Dashboard with queue count badges
- Document Queue → Document Review (approve/reject/needs-resubmission with reason enforcement)
- Payment Queue → confirm payment inline
- Order Queue → order detail with bargaining actions, voucher issuance, milestone recording, order advancement
- Exception Queue → Exception Review (approve/reject/escalate; escalate only at initial stage)
- After-Sales Queue → inline resolve action

**Admin flows:**
- Admin Dashboard with feature flag table
- Audit Log viewer
- Config/Feature Flags editor (cohort JSON)

### Frontend Module Map

```
src/
├── router/index.ts          — full route tree, beforeEach role guard, lazy loading
├── stores/                  — candidate, document, order, bargaining, attendance, queue, admin
├── services/                — candidateApi, documentApi, orderApi, paymentApi, bargainingApi,
│                              refundApi, attendanceApi, queueApi, http, offlineQueue, requestSigner
├── composables/             — useTimestamp, useMaskedValue, useOfflineStatus, useUpload, usePagination
├── components/common/       — 15 primitive UI components (see design.md §21.5)
└── views/
    ├── auth/LoginView.vue
    ├── candidate/           — layout + 13 route views
    ├── staff/               — layout + 9 route views
    └── admin/               — layout + 5 route views
```

### Offline Queue

IndexedDB-backed mutation queue with `InMemoryQueue` fallback in test environments. `replayQueue()` fires automatically on reconnect. `OfflineBanner` component shows current connectivity and conflict state.

---

## Business Engine Capabilities (Prompt 4)

The following flows are fully implemented with real persistence, validation, and audit trails:

- **Candidate onboarding** — Profile creation, encrypted PII (SSN/DOB/phone/email), exam scores, transfer preferences, profile history
- **Document pipeline** — Upload (PDF/JPG/PNG, 25MB max), SHA-256 hashing, versioned resubmissions, reviewer decisions, role-gated download with watermarking
- **Order lifecycle** — Service catalog, fixed-price and bargaining orders, 30-min auto-cancel, payment proof/confirm, vouchers, milestones, pending_receipt → completed
- **Bargaining** — Max 3 offers / 48h window / reviewer counter-once / expiry worker
- **Refunds** — Reviewer initiates, admin processes; capacity slot rollback is gated by the `rollback_on_refund` feature flag (defaults to enabled; when disabled the slot is not released and the audit event records `rollback_skipped_by_flag=true`)
- **After-sales** — 14-day window from completion, open → resolve workflow
- **Attendance exceptions** — Anomaly flagging, proof upload, initial/final staged review, immutable approval trail with ECDSA signature hash
- **Staff queues** — Five read-only paginated queue endpoints for pending work items

## API Surface

| Prefix | Port | Auth Required |
|--------|------|---------------|
| `/api/v1/auth/` | 8443 | Varies (login is public) |
| `/api/v1/candidates/` | 8443 | Bearer JWT (row-scoped) |
| `/api/v1/documents/` | 8443 | Bearer JWT (role-gated) |
| `/api/v1/orders/` | 8443 | Bearer JWT (row-scoped) |
| `/api/v1/attendance/` | 8443 | Bearer JWT (row-scoped) |
| `/api/v1/queue/` | 8443 | Reviewer or Admin JWT |
| `/api/v1/admin/` | 8443 | Admin JWT only |

## Background Workers

Three asyncio background tasks start automatically in FastAPI lifespan:

| Worker | Interval | Purpose |
|--------|----------|---------|
| `run_auto_cancel_loop` | 60s | Cancel pending_payment orders past auto_cancel_at; restore capacity slots |
| `run_bargaining_expiry_loop` | 60s | Expire open bargaining threads past window; set fixed_price or cancel order |
| `run_stale_queue_loop` | 600s | Delete expired nonces and idempotency_keys from DB |

Additionally, `run_refund_progression_loop` (3600s) monitors for stale refunds (>7 days in refund_in_progress) and emits a Prometheus counter — no auto-progression.

## Storage Paths

| Purpose | Path Pattern | Configured By |
|---------|-------------|---------------|
| Document files | `{STORAGE_ROOT}/{candidate_id}/{document_id}/v{N}/{filename}` | `STORAGE_ROOT` env var |
| Exception proofs | `{STORAGE_ROOT}/exceptions/{exception_id}/{version_id}/{filename}` | `STORAGE_ROOT` env var |

---

## Documentation

| Document | Purpose |
|---|---|
| `docs/design.md` | Architecture, topology, security boundaries, state machines, module map |
| `docs/api-spec.md` | Endpoint groups, request/response envelopes, error model, auth headers |
| `docs/questions.md` | Blocker-level ambiguities with forward-moving interpretations |
| `docs/requirement-traceability.md` | Every requirement → implementing module |
| `docs/test-traceability.md` | Every requirement/endpoint → test file |

---

## Admin Module Capabilities (Prompt 7)

The following admin surfaces are fully implemented with RBAC enforcement, audit trails, and structured persistence:

### Feature Flag Config Center
- **`GET /api/v1/admin/feature-flags`** — list all feature flags with current values and types
- **`POST /api/v1/admin/feature-flags`** — create a new flag (boolean, string, integer, json)
- **`PATCH /api/v1/admin/feature-flags/{key}`** — update flag value; writes `FeatureFlagHistory` row; emits `feature_flag_changed` audit event
- **Per-user flag resolution** — `GET /api/v1/admin/config/bootstrap/{user_id}` returns a merged view of base flags overridden by cohort `flag_overrides`, plus an HMAC-SHA256 signature keyed by the server `SECRET_KEY` so tampering with the payload in transit or at rest is detectable (verified by `verify_bootstrap_signature`)

### Canary Cohort Routing
- **`GET /api/v1/admin/cohorts`** — list cohort definitions
- **`POST /api/v1/admin/cohorts`** — create cohort with `flag_overrides` JSONB
- **`POST /api/v1/admin/cohorts/{id}/assign`** — assign a user to a cohort; emits `cohort_assigned` audit
- **`DELETE /api/v1/admin/cohorts/{id}/users/{uid}`** — remove cohort assignment

### Audit Log Access
- **`GET /api/v1/admin/audit`** — searchable audit log with filters: `event_type`, `actor_id`, `outcome`, `from_date`, `to_date`; paginated

### Policy Inspection
- **`GET /api/v1/admin/rbac-policy`** — returns the static RBAC policy map (which roles can access which route groups)
- **`GET /api/v1/admin/masking-policy`** — returns the field masking rules per role

### Export Jobs (admin-only)
- **`POST /api/v1/admin/exports`** — create a new export job (`audit_csv` or `forecast_csv`); content generated immediately; SHA-256 hash stored; watermark metadata recorded
- **`GET /api/v1/admin/exports`** — list export jobs (paginated)
- **`GET /api/v1/admin/exports/{id}/download`** — download export file; re-serves bytes from `EXPORTS_ROOT`; includes `X-SHA256` and `X-Watermark-User` response headers

### Observability Surfaces
- **`GET /api/v1/admin/metrics/summary`** — live snapshot of the in-process `MetricsRegistry` (counters and histograms with labels)
- **`GET /api/v1/admin/traces`** — paginated list of `TelemetryCorrelation` rows for trace-level search
- **`GET /api/v1/admin/cache-stats`** — paginated `CacheHitStat` rows (15-minute windows, route groups, hit rates)
- **`GET /api/v1/admin/access-logs`** — paginated `AccessLogSummary` rows (15-minute aggregated request volumes by route group)

### Forecasting
- **`GET /api/v1/admin/forecasts`** — paginated list of `ForecastSnapshot` rows
- **`POST /api/v1/admin/forecasts/compute`** — trigger an on-demand forecast computation; returns the new snapshot immediately

### Admin API Prefix

All admin endpoints are under `/api/v1/admin/` and require an `admin`-role JWT (`Authorization: Bearer <token>`).

| Prefix | Port | Auth Required |
|--------|------|---------------|
| `/api/v1/admin/` | 8443 | Admin JWT only |

### New Background Workers (added in Prompt 7)

| Worker | Interval | Purpose |
|--------|----------|---------|
| `run_cache_stats_loop` | 900s | Reads route-level histogram data from MetricsRegistry; writes `CacheHitStat` and `AccessLogSummary` rows per 15-min window |
| `run_forecasting_loop` | 3600s | Calls `ForecastingService.compute_forecast()` hourly; persists snapshot to `forecast_snapshots` table |

### New Frontend Admin Screens (Prompt 7)

Three new admin views added to the router at `/admin/`:

| Route | View | Capability |
|-------|------|-----------|
| `/admin/config` | `ConfigView.vue` | Feature flag table with inline edit form (value + change reason); save/cancel; success notification |
| `/admin/observability` | `ObservabilityView.vue` | Live metrics summary cards (counter totals, histogram avg/observations); cache stats table; trace search input |
| `/admin/forecasts` | `ForecastView.vue` | Forecast snapshot table (horizon, input window, bandwidth p50/p95 in MB, request volume); trigger on-demand button |
| `/admin/exports` | `ExportsView.vue` | Export type selector; create button; existing jobs table; download link for completed exports |

The `AuditLogView.vue` was expanded with a full filter form (event_type, actor_id, outcome, date range) and server-side search.

### New Metrics Counters (Prompt 7)

Six new Prometheus-style counters added to `telemetry/metrics.py`:

| Counter | Labels | Tracks |
|---------|--------|--------|
| `merittrack_document_uploads_total` | `outcome` | Document upload attempts by outcome |
| `merittrack_order_transitions_total` | `from_state`, `to_state` | Order state transitions |
| `merittrack_exception_approvals_total` | `outcome`, `stage` | Attendance exception review outcomes |
| `merittrack_queue_actions_total` | `queue`, `action` | Staff queue mutations |
| `merittrack_export_jobs_total` | `export_type`, `outcome` | Export job results |
| `merittrack_feature_flag_changes_total` | `key` | Feature flag update frequency |

### Export Storage Path

| Purpose | Path Pattern | Configured By |
|---------|-------------|---------------|
| Export files | `{EXPORTS_ROOT}/{job_id}_{type}.csv` | `EXPORTS_ROOT` env var |
