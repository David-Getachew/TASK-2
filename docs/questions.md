# docs/questions.md — MeritTrack Ambiguity Log

All blocker-level or implementation-shaping ambiguities are recorded here.
Format per entry: **The Gap** / **The Interpretation** / **Proposed Implementation**

---

## 1. Local payment handling in an offline-only deployment

**The Gap**
The prompt requires order states such as `pending payment`, `completed`, `refund in progress`, and `refunded`, plus order confirmation and voucher issuance, but it does not define an external or internal payment rail.

**The Interpretation**
Treat payments as local, first-party operational records inside the platform rather than as third-party gateway transactions. Keep the order state machine real, but avoid inventing cloud payment providers or banking integrations.

**Proposed Implementation**
Implement local payment intent / settlement records, manual or internal payment confirmation steps, voucher issuance, and refund records entirely within FastAPI + PostgreSQL. Keep staff/reviewer queues responsible for confirmation and downstream operational status changes.

---

## 2. Internal identity-provider scope

**The Gap**
The prompt says SSO is implemented as an internal identity provider without external dependencies, but it does not define whether that IdP serves only this application or multiple bundled first-party surfaces.

**The Interpretation**
Treat the internal IdP as a first-party FastAPI module that serves this platform and any bundled internal admin surface inside the same trust boundary.

**Proposed Implementation**
Implement an internal token issuer and trusted-client registry inside the backend, document the supported flows and trust boundaries, and avoid external IdP products or cross-organization federation.

---

## 3. Local HTTPS certificate provisioning and trust bootstrap

**The Gap**
The prompt requires end-to-end HTTPS using locally provisioned certificates, but it does not specify how certificates are created, trusted, or rotated.

**The Interpretation**
Treat certificate material as externally provisioned local infrastructure input that the repository documents and loads, but does not generate automatically with secrets embedded in the repo.

**Proposed Implementation**
Document certificate paths, mount points, and trust assumptions in README and config templates. Provide non-secret sample configuration and a clear manual bootstrap path, but keep the actual cert/key files outside version control.

---

## 4. Envelope-encryption key custody and rotation

**The Gap**
The prompt requires envelope encryption with locally managed keys, but it does not specify master-key storage, rotation cadence, or recovery behavior.

**The Interpretation**
Treat the key-encryption key as a locally mounted secret outside the repo and track key versions explicitly in the database so data remains decryptable across rotations.

**Proposed Implementation**
Store a KEK reference and DEK metadata per encrypted record or file, load the KEK from a mounted local secret or equivalent local secure store, and persist key-version identifiers for later rotation tooling without hardcoding secrets.

---

## 5. Device-bound request signing in a browser client

**The Gap**
The prompt requires device-bound anti-replay using API signing plus a 5-minute nonce window, but browser applications do not have a stable hardware identity by default.

**The Interpretation**
Treat "device-bound" as a first-party registered client installation or browser context that receives a signed device registration and stores an app-managed keypair or equivalent credential locally.

**Proposed Implementation**
Implement a device-registration record tied to the authenticated user, store a client-side signing credential in secure browser storage as far as the platform permits, canonicalize requests for signing, and enforce nonce freshness server-side with replay rejection.

---

## 6. Bargaining resolution after the reviewer counter

**The Gap**
The prompt says the Reviewer can accept one offer or counter once, after which the order reverts to fixed-price or expires, but it does not define the exact post-counter candidate path.

**The Interpretation**
Treat the reviewer counter as the final bargaining action. After that counter, the bargaining thread closes and the order either proceeds on the final quoted price within the remaining validity window or drops back to the configured fixed-price path / expiry rule.

**Proposed Implementation**
Persist a closed bargaining thread after the reviewer counter, expose the final payable amount and expiry deadline to the candidate, and, if the candidate does not act before the window ends, either revert the item to its configured fixed-price path or expire the order according to the item policy documented in code and UI copy.

---

## 7. Capacity-limited rollback on cancellation and refund

**The Gap**
The prompt requires inventory/slot rollback for capacity-limited items on pending-payment auto-cancel and mentions rollback on refunds as optional, but it does not define when rollback is allowed after fulfillment has started.

**The Interpretation**
Treat rollback as always required on pending-payment auto-cancel for reserved capacity, and as policy-driven for refunds depending on whether fulfillment has consumed irreversible capacity.

**Proposed Implementation**
Implement rollback-on-timeout as mandatory for reserved capacity. For refunds, allow rollback only when the item policy enables it and the fulfillment state has not crossed a non-reversible operational milestone. Record the decision and resulting rollback event in the audit trail.

---

## 8. Document version retention and resubmission semantics

**The Gap**
The prompt requires visible resubmission status and reasons, but it does not define whether prior rejected or superseded files remain accessible.

**The Interpretation**
Treat every document upload as a versioned submission so reviewers and candidates can see the current active version while preserving prior versions for audit purposes.

**Proposed Implementation**
Persist version metadata, hash values, uploader identity, review status, and resubmission reason per file version. Display only the latest active version by default, but keep prior versions available to authorized reviewers and auditors.

---

## 9. Attendance-exception routing chain

**The Gap**
The prompt requires a routed review decision with an immutable approval trail, but it does not state whether Proctors/Teachers, Admissions Reviewers, or both participate in the decision chain.

**The Interpretation**
Treat attendance exceptions as a routed workflow that can include an initial operational review by Proctors/Teachers and a final adjudication by Admissions Reviewers when escalation or policy review is needed.

**Proposed Implementation**
Model the workflow with configurable review stages, defaulting to Proctor/Teacher intake plus Admissions Reviewer final decision. Record each stage immutably with actor, timestamp, comment, and outcome.

---

## 10. Watermark scope for downloads and exports

**The Gap**
The prompt says every export and downloaded PDF is watermarked with username and timestamp, but it does not clarify whether all PDF downloads are transformed or only generated exports.

**The Interpretation**
Treat watermarking as mandatory for any PDF the platform serves for download, including generated exports and stored PDF documents, while still auditing all non-PDF downloads.

**Proposed Implementation**
Apply watermarking dynamically or during export generation for every PDF response, stamp the requesting username and timestamp, and keep non-PDF downloads hash-verified and audit-logged without forcing a format transformation.

---

## 11. Canary release routing semantics

**The Gap**
The prompt requires canary release routing by user cohort, but it does not define whether the routing changes frontend bundles, backend behavior, feature flags, or all three.

**The Interpretation**
Treat canary routing as a local cohort-assignment and configuration-resolution system that can influence frontend feature exposure and backend rule selection without introducing an external traffic router.

**Proposed Implementation**
Persist cohort rules and user assignments in PostgreSQL, expose a signed configuration/profile payload at login or bootstrap time, and let the backend and frontend resolve feature flags and rollout behavior from the same cohort-aware config source.

---

## 12. Forecasting methodology and reporting cadence

**The Gap**
The prompt requires capacity/bandwidth forecasting based on request volumes and document-size distributions, but it does not define the mathematical approach or update cadence.

**The Interpretation**
Treat forecasting as an operational planning feature rather than a machine-learning deliverable. Use transparent, explainable statistical methods that operate fully offline.

**Proposed Implementation**
Implement rolling-window aggregates, percentile-based bandwidth estimates, and short-horizon trend projections using stored historical metrics and document-size distributions. Recompute forecasts on a scheduled local job and persist snapshots for admin review.

---

## 13. Cache hit-rate reporting source of truth

**The Gap**
The prompt requires cache hit-rate reporting from local access logs for static assets served by the same deployment, but it does not define the exact logging source or aggregation approach.

**The Interpretation**
Treat local access logs from the same deployment boundary that serves the static assets as the source of truth for cache-hit reporting.

**Proposed Implementation**
Capture cache-related response metadata in local access logs, parse or aggregate those logs on a scheduled backend job, store summarized hit/miss ratios in PostgreSQL, and surface them through admin reporting endpoints.

---

## 14. After-sales service scope and fulfillment definition

**The Gap**
The prompt allows after-sales requests within 14 days of completion but does not specify what constitutes an after-sales service type or what workflow it triggers.

**The Interpretation**
Treat after-sales as a post-completion follow-up request that creates a child order or service ticket linked to the original completed order, visible to both the candidate and the staff queue.

**Proposed Implementation**
Implement after-sales as a separate order sub-type with a parent_order_id reference, a 14-day eligibility window enforced on the backend, and routing to the staff fulfillment queue.

---

## 15. Static asset serving and cache policy implementation

**The Gap**
The prompt replaces CDN references with offline cache policy controls but does not define whether a service worker is required or whether cache policy headers alone suffice.

**The Interpretation**
Use HTTP cache-control headers for static assets as the primary mechanism, supplemented by a service worker only where asset caching or upload resumption materially benefits offline operation.

**Proposed Implementation**
Configure Vite build output with stable content-hash filenames, set explicit Cache-Control and ETag headers in the FastAPI static file handler, and optionally add a minimal service worker for asset prefetching. Log cache header resolution per request for hit-rate reporting.

---

## 16. WebCrypto fallback for browsers without non-extractable ECDSA

**The Gap**
The prompt specifies device-bound signing but the backing browsers vary: WebKit and some hardened Chromium profiles have historically lacked non-extractable ECDSA via `crypto.subtle`. A deployment that assumes uniform WebCrypto support will silently lose device binding on those browsers.

**The Interpretation**
Primary path is a non-extractable ECDSA P-256 keypair generated with `crypto.subtle.generateKey({name:"ECDSA",namedCurve:"P-256"}, false, ["sign","verify"])`. When the browser refuses non-extractable ECDSA, fall back to an HMAC-SHA256 secret stored in IndexedDB (behind a feature flag) and bind it to the device registration exactly like the ECDSA public key path.

**Proposed Implementation**
`WEBCRYPTO_FALLBACK_ENABLED` config flag defaults to `false`. When enabled, `services/requestSigner.ts` exposes a detection branch that upgrades to HMAC-IndexedDB. The fallback is recorded as `device_registrations.algorithm = "hmac-idb"` on enrollment; the signing verifier in `src/security/signing.py` dispatches on algorithm and logs the event. The fallback is *not* activated in the default deployment for this repository.

---

## 17. KEK directory layout and rotation

**The Gap**
`KEK_PATH` is described as a path but its shape was not specified: a single file vs. a versioned directory. Encryption + rotation behavior differ sharply between the two.

**The Interpretation**
`KEK_PATH` points to a directory containing numeric-version key files: `v1.key`, `v2.key`, ... Each file holds 32 raw bytes. The active version is the highest-numbered file present; older files remain so stored ciphertexts encrypted under prior KEKs can still be decrypted.

**Proposed Implementation**
`src/security/encryption.py` reads `kek_path/v{N}.key` on demand; ciphertext stores its `key_version` alongside the wrapped DEK so decryption can locate the correct KEK without a manifest. Rotation is a pure filesystem op (drop `v{N+1}.key`); no re-encryption of historical rows is required.

---

## 18. JWT algorithm selection

**The Gap**
The prompt specifies JWT for access tokens but does not mandate HMAC vs. asymmetric signing.

**The Interpretation**
RS256 over a locally provisioned RSA-2048 keypair. Chosen because the internal IdP exposes a JWKS endpoint (RFC 7517) and verifiers — including the backend itself for IdP-issued client_credentials tokens — must resolve the signing key from public material without sharing an HMAC secret.

**Proposed Implementation**
`jwt_private_key_path` / `jwt_public_key_path` mount RSA keys; `src/security/jwt.load_signing_keys()` lazy-loads them. `kid = mt-signing-1` published at `GET /api/v1/idp/jwks`. Access tokens use 15-minute TTL; the IdP reuses the same signer for client_credentials with `aud="internal"`.

---

## 19. Background worker deployment model

**The Gap**
The platform needs auto-cancel, bargaining expiry, and stale-record cleanup workers. The prompt does not specify whether these should run as separate processes (Celery/RQ) or in-process.

**The Interpretation**
In-process asyncio tasks started in the FastAPI lifespan context manager. This is appropriate for the local single-deployment model — no external queue broker (Redis, RabbitMQ) is available or required.

**Proposed Implementation**
Three `asyncio.create_task(...)` calls in `src/main.py` lifespan: `run_auto_cancel_loop`, `run_bargaining_expiry_loop`, `run_stale_queue_loop`. Each loop gets its own `AsyncSession` via `get_session_factory()`. Tasks are cancelled gracefully on app shutdown via `await asyncio.gather(*tasks, return_exceptions=True)`.

---

## 20. Voucher code format

**The Gap**
The prompt requires a fulfillment voucher but does not specify format, entropy, or external provider.

**The Interpretation**
16-character uppercase hex string generated server-side: `uuid4().hex[:16].upper()`. No external voucher provider is used. This yields 64 bits of entropy — sufficient for internal tracking at this scale and avoids external dependencies.

**Proposed Implementation**
`PaymentService.issue_voucher` generates the code server-side and stores it in `vouchers.voucher_code`. The code is returned in `VoucherRead.voucher_code` to the caller (reviewer).

---

## 21. After-sales resolve vs. refund independence

**The Gap**
The prompt defines both after-sales requests and refund flows as separate actions. It was unclear whether resolving an after-sales complaint should automatically trigger a refund.

**The Interpretation**
After-sales resolve and refund initiation are independent. Resolving a complaint (e.g., answering a question, providing clarification) does not automatically create a `RefundRecord` or transition the order state. A reviewer who determines a refund is warranted must explicitly call `POST /api/v1/orders/{id}/refund` separately.

**Proposed Implementation**
`AfterSalesService.resolve` only updates `AfterSalesRequest.status = resolved` and sets `resolved_by`, `resolved_at`, `resolution_notes`. No order state transition or refund creation occurs. This keeps the two flows independently auditable.


---

## 22. Frontend IndexedDB fallback in test environments

**The Gap**
The jsdom environment used by Vitest does not implement IndexedDB. The offline queue requires a real storage backend.

**The Interpretation**
Provide an `InMemoryQueue` fallback and a feature-detect function `isIndexedDbAvailable()`. In test environments the singleton automatically uses InMemory, preserving the same interface contract.

**Proposed Implementation**
`src/services/offlineQueue.ts` exports both `IndexedDbQueue` and `InMemoryQueue`. `getOfflineQueue()` calls `isIndexedDbAvailable()` before constructing the singleton. Tests call `__resetOfflineQueueForTests()` in `beforeEach` to reset the singleton between runs.

---

## 23. Paginated list endpoints use raw fetch instead of JSON envelope helper

**The Gap**
The `request<T>()` helper in `http.ts` unwraps `envelope.data` and returns type `T`, but paginated endpoints return `{ data: T[], pagination: {...} }` — the pagination metadata would be lost.

**The Interpretation**
Use raw `fetch()` with manual header injection for paginated list endpoints, extracting both `.data` and `.pagination` from the response body directly.

**Proposed Implementation**
`listOrdersPaginated`, `listExceptions`, and the internal `fetchQueue()` helper in `queueApi.ts` use raw `fetch()` calls. Auth header is injected via `await import('@/stores/auth')` (dynamic ESM import, not CommonJS `require()`).

---

## 24. File upload uses raw fetch, not the JSON http.ts wrapper

**The Gap**
The `request<T>()` wrapper sends JSON with `Content-Type: application/json`. Multipart file uploads require `FormData` without a `Content-Type` header (so the browser sets the boundary automatically).

**The Interpretation**
File upload and proof upload endpoints bypass `request()` and use raw `fetch()` with `FormData`. Auth header is still injected manually.

**Proposed Implementation**
`uploadDocumentFile()` in `documentApi.ts` and `uploadProof()` in `attendanceApi.ts` use raw `fetch()` with `FormData`. The auth token is extracted via `(await import('@/stores/auth')).useAuthStore().accessToken`.

---

## 25. In-process cache-hit detection heuristic

**The Gap**
The observability spec calls for cache-hit reporting, but FastAPI serves every request directly — there is no HTTP cache layer (Varnish, nginx proxy cache, CDN) that would emit real cache hit/miss headers or events.

**The Interpretation**
Model "cache hits" as routes served from assets the browser already has (static file prefix routes) vs. routes that hit the DB (API routes). Any non-error 2xx response to a static-prefix route is treated as a cache hit. This is a proxy metric, not a true cache measurement.

**Proposed Implementation**
`workers/cache_stats.py` classifies routes by prefix (`/static/`, `/assets/`, `/favicon`, `/manifest`) as static. Non-error 2xx responses to static prefixes are counted as cache hits; API routes are counted as requests only. Results are written to `CacheHitStat` rows. The heuristic is documented in `design.md §25`.

---

## 26. Forecast projection uses flat rolling average, not regression

**The Gap**
The forecasting spec requires projecting future request volume and bandwidth, but does not specify the projection method. Statistical methods (linear regression, exponential smoothing) require external libraries not included in the stack.

**The Interpretation**
Use a flat rolling average: compute the mean daily request volume from the input window, then project that constant value forward for each horizon day. This is simple, explainable, and requires no additional dependencies.

**Proposed Implementation**
`ForecastingService.compute_forecast()` sums request counts across all `AccessLogSummary` rows in the input window, divides by the number of windows, scales by 96 (15-minute windows per day), and writes that constant value for each horizon day. Bandwidth is estimated at 5% of requests × per-file size constants (p50=500KB, p95=5MB). Future replacement with ARIMA or similar can slot in at the same interface.

---

## 27. Export format is CSV only; watermark applied as metadata, not PDF overlay

**The Gap**
The export spec mentions watermarking exports, but the only export formats produced are CSV (audit log, forecast snapshot). CSV is plain text — a visual PDF watermark overlay does not apply.

**The Interpretation**
Record watermark metadata (username, timestamp, SHA-256) in the `ExportJob` record so every download is auditable. For future PDF exports, the `apply_pdf_watermark()` primitive from `security/watermark.py` will be called at download time. CSV exports carry the watermark metadata in the DB row only.

**Proposed Implementation**
`ExportService._persist()` computes SHA-256 of the file bytes and writes it to `export_jobs.sha256_hash`. `ExportJob.watermark_applied=True` and `watermark_username=actor.username` are set on every export. `download_export()` re-reads the file and includes `X-Watermark-User` and `X-SHA256` response headers so the caller can verify integrity.

---

## 28. Backend API tests target real PostgreSQL (no SQLite substitute, no dependency overrides)

**The Gap**
Originally `conftest.py` used `sqlite+aiosqlite:///:memory:` with `@compiles` hooks translating `UUID → CHAR(36)` and `JSONB → JSON`, plus `app.dependency_overrides[get_db]` in every `client` fixture. Under strict no-mock audit criteria any `app.dependency_overrides` install counts as mocking, so 84 of 85 endpoints registered as "mocked HTTP" even though the FastAPI route code and schemas were fully exercised.

**The Interpretation**
Fidelity to the production DB path is more valuable than the convenience of a schema-less runner. Dropping the override and pointing `DATABASE_URL` at the compose `db` service costs one extra container during test runs but eliminates the mock classification entirely.

**Proposed Implementation**
`conftest.pytest_configure` runs `Base.metadata.create_all` via a sync `psycopg2` engine against the real Postgres, then reconfigures the app's async engine with `NullPool` (asyncpg connections are loop-bound and pooled connections break across pytest-asyncio's per-test event loops). An autouse async fixture `_clean_tables` truncates every public table before each test. The `client` / `client_raw` fixtures install no dependency overrides. `run_tests.sh backend-api` now runs `docker compose up -d db`, waits for `pg_isready`, and runs pytest with `DATABASE_URL=postgresql+psycopg2://…@db:5432/merittrack`.

---

## 29. Frontend browser tests require a running Vite dev server

**The Gap**
Playwright browser tests (`unit_tests/browser/`) navigate to `http://localhost:5173`. Running `npx playwright test` without a dev server causes "connection refused" on all tests.

**The Interpretation**
Playwright's `webServer` configuration in `playwright.config.ts` auto-starts `npx vite --port 5173` before the test suite and shuts it down after. The tests themselves do not require a live backend: all API calls are intercepted via `page.route()` with mock responses, and auth state is injected via `page.addInitScript()`. The `reuseExistingServer: !process.env.CI` option allows running against an already-running dev server locally.

**Proposed Implementation**
`playwright.config.ts` includes:
```ts
webServer: {
  command: 'npx vite --port 5173',
  port: 5173,
  reuseExistingServer: !process.env.CI,
},
baseURL: 'http://localhost:5173',
```
This makes `npx playwright test` (run inside the `frontend-builder` Docker container via `run_tests.sh`) fully self-contained.


---

## 30. `_CHALLENGE_CACHE` in-process dict not shared across workers

**The Gap**
`src/api/routes/auth.py` stores device enrollment challenges in a module-level dict `_CHALLENGE_CACHE: dict[str, tuple[str, str, uuid.UUID]]`. In a multi-worker deployment (e.g., `uvicorn --workers N` or multiple containers), a challenge issued by one worker process would be invisible to another, causing `POST /api/v1/auth/device/activate` to fail with "challenge not found" when load-balanced to a different worker.

**The Interpretation**
The docker-compose deployment runs a single Uvicorn worker process (no `--workers` flag, no replica scaling). All requests share the same process and the in-memory cache is always valid. Enrollment challenges expire quickly (5-minute window), so the missing persistence is not a security gap in the current deployment model.

**Proposed Implementation**
Accepted as-is for single-worker deployment. If multi-worker deployment is required in the future, migrate `_CHALLENGE_CACHE` to the existing `nonces` table (which already carries `nonce_value`, `expires_at`, and `user_id` columns) or a Redis-style shared store. No code change required now.

---

## 31. `signature_required_paths` in config.py is informational-only for the frontend

**The Gap**
`config.py` contains `signature_required_paths: list[str]`, which could be misread as a middleware allowlist that enforces request signing server-side. In fact, the backend enforces signing at the individual route level via `Depends(require_signed_request)` injected into each `@router.*` decorator. The config list is used only by the frontend's `SIGNED_PATHS` constant in `services/http.ts` to decide which outbound requests to sign.

**The Interpretation**
The `signature_required_paths` list in config.py is purely informational metadata surfaced to the frontend configuration system. Backend enforcement does not depend on this list. Adding a path here without also adding `Depends(require_signed_request)` to the corresponding route has no security effect.

**Proposed Implementation**
Accepted as-is. The distinction is now documented in `docs/api-spec.md` Section 3.2 and in the comment on `signature_required_paths` in `config.py`. Any future route that requires signing must add `Depends(require_signed_request)` to the route decorator; the config list should be kept in sync as documentation.
