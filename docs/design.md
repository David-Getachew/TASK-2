# MeritTrack — System Design

## 1. Project Classification

MeritTrack is a **full-stack offline-ready admissions and transaction operations platform**. It unifies candidate onboarding, document management, fee-based service ordering with bargaining, attendance exception handling, and reviewer/staff operational queues into a single deployment that operates inside a disconnected facility network with no reliance on external internet services.

---

## 2. Offline Facility-Network Assumptions

- The platform runs inside a LAN or intranet with no public internet egress required at runtime.
- All runtime dependencies (auth, storage, identity, observability, payment records, certificate trust) are satisfied locally within the deployment boundary.
- TLS certificates are provisioned locally (mkcert, internal CA, or equivalent). Certificate and key files are mounted at runtime and never committed to the repository.
- No external CDN, cloud storage bucket, hosted payment gateway, third-party IdP, or SaaS observability endpoint is used.
- Static frontend assets are served by the same FastAPI process, eliminating any CDN dependency.
- Offline queue support in the browser (IndexedDB-backed) allows candidates to initiate uploads or actions during transient LAN interruptions, with retry on reconnect.

---

## 3. Role Model

| Role | Abbreviation | Responsibilities |
|---|---|---|
| Candidate | CAND | Profile management, document uploads, order placement, bargaining, after-sales, attendance exceptions |
| Proctor / Teacher | PRCT | Attendance flagging, initial attendance-exception intake, operational status updates |
| Admissions Reviewer | REVW | Document review, order confirmation, voucher issuance, bargaining response, appeal adjudication |
| System Administrator | ADMN | Config center, feature flags, cohort rules, user management, forecasting, audit log access |

Role boundaries are enforced at the route, function, object, row, and column level. Frontend navigation adapts to the authenticated role but does not substitute for backend enforcement.

---

## 4. System Topology

```
Browser Client (Vue 3 SPA)
        │  HTTPS (locally provisioned cert)
        │  Signed requests + nonce header
        ▼
FastAPI Application Server
  ├── Static Asset Handler  ← compiled Vue build (same process)
  ├── Auth / Internal IdP   ← JWT issuance, refresh, nonce verification
  ├── API Routers           ← domain-grouped endpoints
  ├── Background Workers    ← auto-cancel, forecasting, log aggregation
  └── Observability         ← structured logs, metrics, trace IDs
        │
        ├── PostgreSQL 14+   ← all relational state, audit trails, config
        └── Local Filesystem
              ├── /uploads       ← candidate document submissions
              ├── /exports       ← watermarked PDFs, generated reports
              ├── /access-logs   ← structured access log files
              ├── /forecasts     ← forecast snapshots
              └── /certs         ← TLS cert + key (mounted, not committed)
```

**Same-deployment static asset strategy:** The Vite production build output (`dist/`) is copied into the backend container during the Docker build. FastAPI serves it via `StaticFiles` mount with explicit `Cache-Control` and `ETag` headers. This eliminates any separate static server or CDN requirement.

---

## 5. Authentication and Security Architecture

### 5.1 Local Authentication
- Username/password login only. No external IdP.
- Password policy: minimum 12 characters enforced on registration and change.
- Hashing: Argon2id with per-user salt. Passwords never stored in plaintext or recoverable form.
- JWT access tokens: 15-minute lifetime, signed with a locally held HMAC or RSA key.
- Refresh tokens: longer-lived, stored server-side as hashed values with device binding, rotated on use.
- Token families track refresh reuse; detected reuse invalidates the entire family.

### 5.2 Internal Identity Provider (IdP)
- A first-party FastAPI module implements token issuance, trusted-client registration, and the SSO session lifecycle.
- No SAML, OAuth 2.0 external AS, OpenID Connect external OP, or LDAP integration.
- Trusted clients are registered locally; the IdP serves the platform and bundled internal admin surfaces within the same trust boundary.

### 5.3 Request Signing and Anti-Replay
- Each authenticated session receives a device registration record with a derived signing credential stored in the browser's secure storage (localStorage with HTTPS-only origin isolation as minimum; Web Crypto API for key generation where available).
- Requests are signed: canonical form = `METHOD + URL_PATH + TIMESTAMP + BODY_HASH`. Signature appended as `X-Request-Signature` header.
- Nonce: each request includes a `X-Nonce` UUID. Server stores seen nonces for 5 minutes in PostgreSQL. Duplicate nonces within the window are rejected with `409 Conflict`.
- Clock skew tolerance: ±30 seconds. Requests outside this window are rejected.

### 5.4 RBAC and Data-Level Controls
- Route-level: FastAPI dependency guards check JWT role claim before routing.
- Function-level: service layer checks role before executing sensitive operations.
- Object-level: ownership checks ensure candidates access only their own records.
- Row-level: queries filter by ownership or assigned reviewer scope.
- Column-level: sensitive fields (SSN, full date of birth, contact info) are masked in API responses by default; full values returned only to authorized roles with explicit justification.

### 5.5 Envelope Encryption
- Sensitive fields at rest (SSN, contact details, financial record notes) are encrypted using AES-256-GCM data encryption keys (DEK).
- Each DEK is encrypted with a key-encryption key (KEK) loaded from a locally mounted secret (environment variable or mounted file outside the repo).
- The encrypted DEK and a key-version identifier are stored alongside the ciphertext in the database.
- Key rotation: re-encrypt DEKs with the new KEK version; old KEK remains available to decrypt legacy records until rotation is complete.

### 5.6 HTTPS
- All traffic between browser and server is TLS-encrypted.
- Certificates are locally provisioned (internal CA or mkcert). Paths are configurable via environment variables.
- The application refuses to start without valid certificate material in production mode.

### 5.7 Trust Boundaries and Module Layout (Prompt 3)

| Boundary | Enforcement point | Implementation |
|---|---|---|
| Network edge | TLS termination at FastAPI | `main.py`, uvicorn TLS config |
| Request authenticity | Signed-request dependency | `api/dependencies.require_signed_request` |
| Identity | Bearer JWT verification | `security/jwt.decode_access_token` + `api/dependencies.get_current_user` |
| Route gate | Role-based dependency | `security/rbac.require_role` |
| Function gate | Explicit service checks | `services/auth_service.*`, `services/audit_service.*` |
| Object gate | Ownership assertion | `security/rbac.assert_owner` |
| Row gate | Scoped query helper | `security/rbac.scope_rows_to_actor` |
| Column gate | Role-aware serializer | `security/data_masking.*` + `CandidateProfileRead` |
| Persistence gate | Envelope encryption | `security/encryption.encrypt_field` / `decrypt_field` |
| Audit gate | Insert-only writer | `security/audit.record_audit` |

### 5.8 JWT and JWKS

- Algorithm: **RS256** over a locally provisioned RSA-2048 keypair mounted at `jwt_private_key_path` / `jwt_public_key_path`. `kid = mt-signing-1` (configurable).
- Access token TTL: **15 minutes**. Claims: `sub`, `role`, `aud="merittrack"`, `iat`, `exp`, `jti`, plus any short-lived `extra_claims` the service passes in.
- Refresh rotation: opaque 256-bit token. On each refresh, the prior row is marked `is_consumed=true`; reuse of a consumed token invalidates the entire `RefreshTokenFamily` with `invalidation_reason = "reuse_detected"`.
- `GET /api/v1/idp/jwks` returns RFC 7517 keys with `kty=RSA`, `alg=RS256`, `n`, `e`, `kid`, `use=sig`. Private components never leave the server.

### 5.9 Device Binding, Nonce Window, and Clock Skew

- Frontend generates a non-extractable ECDSA P-256 keypair via `crypto.subtle.generateKey`. Public key is exported as SPKI PEM and enrolled via `POST /auth/device/register`. Private key never leaves IndexedDB.
- Canonical signing form (bytes):
  ```
  METHOD\nPATH\nX-Timestamp\nX-Nonce\nX-Device-ID\nsha256_hex(body)\n
  ```
- Signature: `ECDSA(SHA-256)` over canonical, base64-encoded. Backend accepts raw `r||s` (64 bytes) and DER-encoded forms.
- Nonce policy: 5-minute window, persisted in `nonces` with `UNIQUE(nonce_value)`. Duplicate insert → `NONCE_REPLAY` (409).
- Clock skew policy: ±30 seconds between `X-Timestamp` and server time. Outside → `CLOCK_SKEW` (400).

### 5.10 Login Throttling

- Per-username rolling window. Defaults: **5 attempts / 15-minute window**, lockout **15 minutes**. Stored in `login_throttles`.
- After threshold: `locked_until = now + lockout_minutes`; subsequent attempts return **AUTH_THROTTLED (429)** without revealing whether the account exists.
- Throttle resets on successful login.

### 5.11 Envelope Encryption Layout

- KEK directory: `kek_path/v1.key`, `v2.key`, … (32 raw bytes per file).
- Per-field DEK generated per call; body wrapped via AES-256-GCM with AAD = resource id.
- Stored value: `version_id || base64(wrap_iv || wrapped_dek || data_iv || ciphertext)`.
- `*_key_version` column tracks KEK version so rotation can proceed without re-encrypting historical rows.

### 5.12 Audit Immutability

- Only INSERTs into `audit_events`; no UPDATE/DELETE paths exist in code.
- `record_audit(...)` runs automatic redaction on known-sensitive keys: `password`, `new_password`, `refresh_token`, `public_key_pem`, `client_secret` before persisting `detail`.
- `diff_fields(before, after, sensitive_keys)` produces a redacted field-change summary for change-tracking callers.

### 5.13 Error Envelope Safety

- `api/errors.register_exception_handlers` installs a generic `Exception` handler that returns `INTERNAL_ERROR` with only `trace_id` in the body. Stack traces, exception types, and raised messages are logged internally (structlog) but never echoed to the client.
- `RequestValidationError` is transformed to `VALIDATION_ERROR` with per-field messages — submitted secret fields are not echoed in the envelope.
- `SignatureInvalidError`, `NonceReplayError`, `ClockSkewError` return stable codes so frontend can branch without parsing prose.

---

## 6. Document Storage, Watermarking, and Hash Verification

### 6.1 Upload Flow
1. Candidate submits file via multipart POST.
2. Backend validates MIME type (PDF/JPG/PNG) and file size (≤ 25 MB).
3. SHA-256 hash computed server-side immediately after receiving the stream.
4. File saved to `/uploads/{candidate_id}/{doc_type}/{version}/` with a UUID filename.
5. Hash, original filename, content type, size, uploader identity, and upload timestamp stored in the database.
6. If the file is a resubmission, a new version record is created; the previous version is preserved.

### 6.2 Download Flow
1. Authenticated request to download a document.
2. Backend checks role authorization; only approved roles may download.
3. For PDF files: watermark applied dynamically (username + ISO timestamp burned into the PDF via reportlab/pypdf).
4. SHA-256 of the watermarked output computed and returned in the `X-File-Hash` response header.
5. Download event logged to the immutable audit trail.
6. For non-PDF files: served directly with hash verification header and audit log entry.

### 6.3 Export Flow
- All generated exports (reports, order histories, attendance records) are watermarked before delivery.
- Export metadata (requester, timestamp, hash) stored in the audit log.

---

## 7. Order State Machine

```
                ┌────────────────────────┐
                │      pending_payment    │ ◄─── created on checkout
                └────────┬───────────────┘
                         │ payment confirmed (staff/system)
                         │ [30-min timeout → canceled + rollback]
                         ▼
                ┌────────────────────────┐
                │   pending_fulfillment   │ ◄─── voucher issued, work begins
                └────────┬───────────────┘
                         │ fulfillment complete
                         ▼
                ┌────────────────────────┐
                │     pending_receipt     │ ◄─── awaiting candidate acknowledgement
                └────────┬───────────────┘
                         │ candidate acknowledges
                         ▼
                ┌────────────────────────┐
                │        completed        │ ◄─── 14-day after-sales window opens
                └────────┬───────────────┘
                         │ refund initiated
                         ▼
                ┌────────────────────────┐
                │    refund_in_progress   │
                └────────┬───────────────┘
                         │ refund processed
                         ▼
                ┌────────────────────────┐
                │        refunded         │
                └────────────────────────┘

  Any state → canceled  (explicit cancellation by authorized actor)
```

- **Auto-cancel:** A background worker checks orders in `pending_payment` state every minute. Orders older than 30 minutes without a payment confirmation event are atomically transitioned to `canceled`. If the item is capacity-limited, the reserved slot/inventory count is rolled back in the same transaction.
- **Rollback feature flag:** `rollback_on_refund` flag in the config center controls whether refunds on capacity-limited items restore inventory. Default is `true`; when the flag is unset or missing, `RefundService._is_rollback_enabled()` treats that as enabled so existing environments behave unchanged. When disabled, `process_refund` skips the capacity-slot release and the `refund_processed` audit event records `rollback_flag_enabled=false`, `rollback_skipped_by_flag=true` for operator visibility.
- All transitions are recorded in an immutable `order_events` table with actor, timestamp, and previous/new state.

---

## 8. Bargaining Module

- Bargaining is feature-flag controlled (`bargaining_enabled` per service item or globally).
- **Candidate offers:** up to 3 offers per order within 48 hours of order creation.
- **Reviewer actions:** accept one offer (transitions order to `pending_payment` at agreed price) or counter once (closes the bargaining thread; candidate sees final price and expiry).
- **Post-counter resolution:** candidate must confirm at the counter price before the window expires. If no action, the order expires or reverts to configured fixed price per item policy.
- All offer amounts, timestamps, actors, and outcomes are persisted in `bargaining_offers` table.
- Expired bargaining threads are marked `expired` by the auto-cancel worker.

---

## 9. Attendance Exception Workflow

1. Proctor/Teacher flags a missed check-in or late arrival and creates an exception record.
2. Candidate receives a notification and uploads proof (PDF/JPG/PNG, same upload rules as documents).
3. Initial review by Proctor/Teacher: can approve, reject, or escalate to Admissions Reviewer.
4. Admissions Reviewer makes the final adjudication decision.
5. Every stage is appended as an immutable record in `exception_events` (actor, timestamp, stage, decision, comment).
6. Approved exceptions are searchable by candidate, date range, reviewer, and outcome.

---

## 10. Config Center, Feature Flags, and Canary Routing

### 10.1 Config Center
- Feature flags stored in `feature_flags` table: `key`, `value`, `description`, `updated_by`, `updated_at`.
- Change history stored in `feature_flag_history` for audit purposes.
- Flags loaded into backend at request time (cached with short TTL) and surfaced to authenticated frontend clients in a signed config payload.

### 10.2 Feature Flags in Use
| Flag Key | Type | Description |
|---|---|---|
| `bargaining_enabled` | boolean | Global bargaining on/off |
| `rollback_on_refund` | boolean | Restore capacity on refund |
| `after_sales_window_days` | integer | Days after completion for after-sales (default 14) |
| `auto_cancel_minutes` | integer | Pending-payment timeout (default 30) |
| `canary_routing_enabled` | boolean | Enable cohort-based canary routing |

### 10.3 Canary / Cohort Routing
- Users are assigned to named cohorts (e.g., `stable`, `canary`) stored in the `user_cohorts` table.
- At login/bootstrap, the backend resolves feature flags and config overrides for the user's cohort and includes them in the signed session payload.
- Frontend reads the cohort config payload to resolve feature exposure without a separate network call.
- Cohort rules are defined in `cohort_rules` and evaluated server-side; no external traffic manager is involved.

---

## 11. Observability

### 11.1 Structured Logging
- All application logs are emitted as JSON with: `timestamp`, `level`, `trace_id`, `span_id`, `user_id` (where applicable), `event`, `module`, and contextual fields.
- Critical events logged with full context: login success/failure, document upload, order state transition, appeal approval/rejection.
- Logs never include raw passwords, private keys, full SSNs, or decrypted payloads.
- Log output to stdout (captured by Docker logging driver) and optionally to `/access-logs/` on local filesystem.

### 11.2 Metrics
- Prometheus-style counter and histogram exposition at `GET /internal/metrics` (restricted to ADMN role).
- Key metrics: request latency by endpoint, order state transition counts, upload sizes, login success/failure rates, auto-cancel counts, cache hit/miss counts.

### 11.3 Trace Correlation
- Each request receives a `X-Trace-ID` (generated or forwarded) and a `X-Span-ID`.
- These IDs propagate through all log entries and background worker events for that request lifecycle.

### 11.4 Cache Hit-Rate Reporting
- FastAPI static file handler logs each asset request with `cache_status: hit|miss` based on `If-None-Match` / `If-Modified-Since` header presence and response code (304 vs 200).
- A background job aggregates these log entries hourly into `cache_hit_stats` table.
- Admin endpoint `GET /internal/cache-stats` returns aggregated hit/miss ratios by asset group and time window.

---

## 12. Capacity and Bandwidth Forecasting

- A scheduled background worker runs every hour, reading from:
  - `request_volume_hourly` — aggregated request counts by endpoint and hour
  - `document_upload_stats` — file sizes and counts by document type and day
- Forecast method: rolling 7-day and 30-day windowed averages + 90th/95th percentile bandwidth estimates.
- Short-horizon trend: linear regression over the last 14 data points for upload volume forecasting.
- Forecast snapshots persisted in `forecast_snapshots` with computed_at timestamp.
- Admin endpoint `GET /internal/forecasts` returns the latest snapshot with trend indicators.

---

## 13. Requirement-to-Module Traceability

| Requirement | Frontend Module(s) | Backend Module(s) |
|---|---|---|
| Candidate profile (application details, scores, transfer prefs) | `views/candidate/`, `stores/candidate.ts`, `services/candidateApi.ts` | `api/routes/candidates.py`, `schemas/candidate.py`, `services/candidate_service.py`, `persistence/models/candidate.py`, `persistence/repositories/candidate_repo.py` |
| Document upload/review (PDF/JPG/PNG, 25MB, checklist, versioning, status) | `views/candidate/documents/DocumentListView.vue`, `views/candidate/documents/DocumentUploadView.vue`, `components/common/UploadPanel.vue`, `stores/document.ts` | `api/routes/documents.py`, `services/document_service.py`, `storage/file_store.py`, `security/watermark.py` |
| Fee-based ordering (fixed-price and bargaining modes) | `views/candidate/orders/OrderListView.vue`, `views/candidate/orders/OrderDetailView.vue`, `views/candidate/orders/BargainingView.vue`, `stores/order.ts` | `api/routes/orders.py`, `api/routes/bargaining.py`, `domain/order_state_machine.py`, `services/order_service.py`, `services/bargaining_service.py`, `workers/auto_cancel.py` |
| Order timeline (12-hour timestamps, all states) | `components/common/TimelineList.vue`, `composables/useTimestamp.ts` | `api/routes/orders.py`, `schemas/order.py` |
| 30-minute auto-cancel + rollback | `components/common/CountdownTimer.vue` (rendered by `views/candidate/orders/OrderDetailView.vue` when `auto_cancel_at` is set) | `workers/auto_cancel.py`, `domain/order_state_machine.py`, `persistence/order_repo.py` |
| After-sales service (14-day window) | `stores/order.ts` (submitAfterSales action), `services/refundApi.ts`; staff resolution UI: `views/staff/orders/AfterSalesQueueView.vue` (candidate-facing submission is composed via the store until a dedicated view ships) | `api/routes/refunds.py`, `services/after_sales_service.py`, `domain/after_sales_policy.py` |
| Attendance exceptions (proof upload, routed review, immutable trail) | `views/candidate/attendance/ExceptionListView.vue`, `views/candidate/attendance/ExceptionDetailView.vue`, `views/staff/attendance/ExceptionQueueView.vue`, `views/staff/attendance/ExceptionReviewView.vue` | `api/routes/attendance.py`, `services/attendance_service.py`, `persistence/repositories/attendance_repo.py` |
| Staff queues (confirmation, voucher, status, adjudication) | `views/staff/`, `stores/queue.ts` | `api/routes/queue.py`, `services/queue_service.py` |
| Order state machine + transactional guarantees | — | `domain/order_state_machine.py`, `persistence/order_repo.py` |
| Local auth (Argon2id, JWT 15-min, refresh) | `views/auth/`, `stores/auth.ts`, `services/authApi.ts`, `composables/useAuth.ts` | `security/passwords.py`, `security/jwt.py`, `security/refresh_tokens.py`, `api/routes/auth.py`, `services/auth_service.py` |
| Request signing + nonce anti-replay | `services/requestSigner.ts`, `composables/useDeviceKey.ts` | `security/nonce.py`, `security/signing.py` |
| Internal IdP / SSO | `services/authApi.ts` | `security/idp.py`, `api/routes/idp.py`, `api/routes/auth.py` |
| RBAC + row/column-level controls | `composables/usePermissions.ts`, `router/guards.ts` | `security/rbac.py`, `security/data_masking.py` |
| Sensitive field masking + restricted downloads | `views/candidate/profile/ProfileView.vue` | `security/data_masking.py`, `api/routes/documents.py` |
| Watermarking + SHA-256 verification | — | `security/watermark.py`, `storage/file_store.py` |
| Envelope encryption at rest | — | `security/encryption.py`, `persistence/` |
| HTTPS with local certs | — | `main.py`, Docker config |
| Observability (logs, metrics, traces) | — | `telemetry/logging.py`, `telemetry/metrics.py`, `telemetry/tracing.py` |
| Config center + feature flags | `composables/useFeatureFlag.ts` | `api/routes/admin.py`, `services/config_service.py`, `persistence/models/config_audit.py` |
| Canary / cohort routing | `stores/session.ts`, `composables/useFeatureFlag.ts` | `services/config_service.py`, `api/routes/admin.py`, `persistence/models/config_audit.py` |
| Capacity/bandwidth forecasting | `views/admin/ForecastView.vue` | `workers/forecasting.py`, `services/forecasting_service.py`, `api/routes/admin.py` |
| Offline cache policy + hit-rate reporting | `public/sw.js` (optional), Vite config | `api/routes/admin.py`, `workers/cache_stats.py` |
| IndexedDB offline queue | `services/offlineQueue.ts`, `composables/useOfflineQueue.ts` | — |

---

## 14. Candidate Onboarding Flow

Profile creation supports two paths: privileged provisioning by reviewer/admin via `POST /api/v1/candidates?user_id=<uuid>`, and candidate self-initialization via `POST /api/v1/candidates/self`. One profile per user is enforced; self-initialization is idempotent for an existing profile.

Sensitive PII (SSN, date of birth, phone, contact email) is stored AES-256-GCM encrypted via `encrypt_field(value, aad=candidate_id.bytes)`. Privileged roles see plaintext; candidate and proctor roles see masked values (last-4 SSN, year-only DOB, etc.) via `is_privileged(actor.role)`.

Every sensitive-field update writes an immutable `ProfileHistory` row capturing the encrypted old and new values, changed_by, and reason. This row is insert-only — no update or delete path exists. A `sensitive_field_accessed` audit event is emitted on every privileged PII write.

Exam scores and transfer preferences are scoped to the owning candidate. Candidates may manage their own preferences; reviewers and admins can manage any candidate's preferences. The `CandidateService` enforces row-level scoping via `assert_roles_or_owner` in every getter.

---

## 15. Document Pipeline

```
Candidate uploads → validate_upload(mime, size) → SHA-256 hash →
write to {storage_root}/{candidate_id}/{document_id}/v{N}/{filename} →
create/update Document + new DocumentVersion (version_number increments) →
status = pending_review → emit document_uploaded audit
```

Document resubmissions always create a new `DocumentVersion`; the previous version is never overwritten. `current_version` on the `Document` row is incremented atomically.

Reviewer decision flow:
- `approved` — status set, audit emitted. No reason required.
- `needs_resubmission` — status set; `resubmission_reason` is mandatory (validated by both `document_policy.validate_review_decision` and the Pydantic `model_validator`).
- `rejected` — status set, no reason required.

Download is role-gated: only `reviewer` and `admin` may call `GET /api/v1/documents/{id}/download`. The file is read from disk, SHA-256 re-verified (`verify_sha256_bytes` — raises `POLICY_VIOLATION / HASH_MISMATCH` on mismatch), and a PDF watermark is applied server-side via `apply_pdf_watermark(bytes, actor.username, now_utc())`. The original stored file is never modified. A `document_downloaded` audit event is emitted on every download.

---

## 16. Order and Payment Flow

```
GET /api/v1/services → candidate selects item →
POST /api/v1/orders (Idempotency-Key) →
  if capacity_limited: SELECT FOR UPDATE inventory → reserved_count++ →
  auto_cancel_at = now + 30min →
  status = pending_payment →
  OrderEvent(sequence=1, created) →
POST /api/v1/orders/{id}/payment/proof → PaymentRecord(confirmed_by=None) →
POST /api/v1/orders/{id}/payment/confirm → PaymentRecord.confirmed_by = reviewer →
  transition(pending_payment → pending_fulfillment) →
POST /api/v1/orders/{id}/milestones (reviewer) →
POST /api/v1/orders/{id}/advance (reviewer) → transition(→ pending_receipt) →
POST /api/v1/orders/{id}/confirm-receipt (candidate) → transition(→ completed) + completed_at
```

Idempotency is enforced by the `Idempotency-Key` header. Duplicate keys return the existing order without re-creating.

The auto-cancel worker (`run_auto_cancel_loop`, every 60s) queries `orders WHERE status='pending_payment' AND auto_cancel_at <= now()` and calls `OrderService.cancel(order, SYSTEM_ACTOR, "auto_cancel_inactivity")`. If `item.is_capacity_limited`, inventory is released atomically under `SELECT FOR UPDATE`.

Payment proof duplicate is blocked: if a `PaymentRecord` with `confirmed_by=None` already exists for the order, `submit_proof` raises `BUSINESS_RULE_VIOLATION`.

---

## 17. Bargaining Flow

Bargaining mode is enabled per `ServiceItem` (`bargaining_enabled=True`). When a candidate creates an order with `pricing_mode=bargaining`, a `BargainingThread` is opened automatically on the first `GET /bargaining` request (window starts at thread creation time, expires +48h).

Rules enforced by `src/domain/bargaining.py`:
- Max 3 candidate offers per thread (`OffersExhaustedError`)
- Offers only accepted within the 48h window (`BargainingWindowClosedError`)
- Reviewer may counter once (`CounterAlreadyMadeError`)

Resolution paths:
1. Reviewer accepts offer → `Order.agreed_price = offer.amount` → `pending_payment → pending_fulfillment`
2. Reviewer counters → candidate accepts counter → `Order.agreed_price = thread.counter_amount` → `pending_payment → pending_fulfillment`
3. Window expires (worker `run_bargaining_expiry_loop`, every 60s) → if `item.fixed_price` exists, set `agreed_price = fixed_price` and proceed; else cancel order

All resolution paths emit a `bargaining_resolved` audit event. Offer submission and counter-accept require ECDSA request signing (`SignedRequestUser`).

---

## 18. Refund and After-Sales Flow

**Refund flow:**
```
completed → reviewer: POST /refund → refund_in_progress + RefundRecord created →
admin: POST /refund/process → refunded + RefundRecord.processed_by set +
  if capacity_limited: SELECT FOR UPDATE → reserved_count-- + RollbackEvent created
```

Both `initiate_refund` and `process_refund` run within a single transaction. `rollback_applied` on `RefundRecord` is set to `True` after slot restoration.

The refund progression worker (`run_refund_progression_loop`, every 3600s) is monitoring-only — it logs a `merittrack_stale_refunds_total` Prometheus counter when refunds have been `refund_in_progress` for more than 7 days. No automatic progression is applied.

**After-sales flow:**
```
completed (within 14 days) → candidate: POST /after-sales → AfterSalesRequest(status=open) →
reviewer: POST /after-sales/{id}/resolve → status=resolved
```

The 14-day window is enforced by `after_sales_policy.assert_within_window(order.completed_at, now)` which raises `AfterSalesWindowExpiredError` → mapped to `BUSINESS_RULE_VIOLATION (409)`. After-sales and refund are independent flows — after-sales resolve does not trigger refund automatically.

---

## 19. Attendance Exception Workflow

```
Proctor/reviewer: POST /attendance/anomalies → AttendanceAnomaly →
Candidate: POST /attendance/exceptions → AttendanceException(status=pending_proof) →
Candidate: POST /exceptions/{id}/proof (multipart) → ExceptionProof + DocumentVersion →
  status = pending_initial_review →
Proctor: POST /exceptions/{id}/review (decision=approve|reject|escalate) →
  if approve/reject → ExceptionApproval(signature_hash=sha256(...)) → terminal status →
  if escalate → current_stage=final, status=pending_final_review →
Reviewer: POST /exceptions/{id}/review (decision=approve|reject) →
  ExceptionApproval(signature_hash=sha256(...)) → terminal status
```

**Approval signature hash:** `sha256(f"{step_id}:{exception_id}:{outcome}:{approved_by}:{approved_at.isoformat()}")`. This is immutable once written — no update path exists on `ExceptionApproval`.

Role adjudication matrix:
- Initial stage: proctor, reviewer, admin
- Final stage: reviewer, admin
- Candidates and proctors cannot adjudicate final stage

The `ExceptionApproval` model is insert-only. All review steps are preserved for full audit trail.

---

## 20. Staff Queue Operations

Five read-only paginated endpoints under `/api/v1/queue/` (reviewer/admin only):

| Endpoint | Filters | Source |
|----------|---------|--------|
| `GET /queue/documents` | page, page_size | Documents where `status IN (pending_review, needs_resubmission)` |
| `GET /queue/payments` | page, page_size | PaymentRecords where `confirmed_by IS NULL` joined to Order + ServiceItem |
| `GET /queue/orders` | page, page_size | Orders where `status = pending_fulfillment` |
| `GET /queue/exceptions` | status, page, page_size | Exceptions where `status IN (pending_initial_review, pending_final_review)` |
| `GET /queue/after-sales` | page, page_size | AfterSalesRequests where `status = open` |

All queues return `PaginatedResponse[<QueueItem>]` with pagination metadata. These are read-only — no state mutation is performed through queue endpoints.

---

## 21. Frontend Architecture

### 21.1 Layer Map

```
Browser (Vue 3 + TypeScript + Vite)
  ├── views/          ← route-level screens; one per URL segment
  ├── components/common/  ← stateless primitives (15 components)
  ├── stores/         ← Pinia state; one per domain
  ├── services/       ← typed API adapters; one per domain
  ├── composables/    ← reusable reactive logic
  ├── router/         ← role-aware Vue Router with navigation guards
  └── types/          ← TypeScript interfaces shared across layers
```

All view components use `<script setup lang="ts">` and Composition API. No Options API is used anywhere in the frontend.

### 21.2 Store and Service Boundaries

Each business domain maps to one Pinia store and one API service module:

| Domain | Store | Service |
|---|---|---|
| Authentication/session | `auth.ts`, `session.ts` | `authApi.ts` |
| Candidate profile | `candidate.ts` | `candidateApi.ts` |
| Documents | `document.ts` | `documentApi.ts` |
| Orders | `order.ts` | `orderApi.ts` |
| Bargaining | `bargaining.ts` | `bargainingApi.ts` |
| Payment/voucher/milestone | order store | `paymentApi.ts` |
| Refund/after-sales | order store | `refundApi.ts` |
| Attendance exceptions | `attendance.ts` | `attendanceApi.ts` |
| Staff queues | `queue.ts` | `queueApi.ts` |
| Admin/config | `admin.ts` | (inline `request()` calls) |

Service modules wrap `request<T>()` from `http.ts` for JSON endpoints. File upload and paginated-list endpoints use raw `fetch()` with manual header injection because they cannot be normalized through the JSON envelope helper.

### 21.3 Offline Queue Design

- Primary implementation: `IndexedDbQueue` using `indexedDB.open('merittrack-offline', 1)`.
- Fallback (jsdom / test environments): `InMemoryQueue` (checked via `isIndexedDbAvailable()`).
- The `getOfflineQueue()` factory returns a singleton; `__resetOfflineQueueForTests()` resets it between test runs.
- `replayQueue()` iterates all pending items, calls `request()` per item, removes on success, and leaves failed items for the next reconnect cycle.
- `useOfflineStatus()` composable listens to `window.online`/`offline` events and triggers `replayQueue()` automatically on reconnect.
- **Transparent enqueue in the shared request layer**: `services/http.ts` wraps every mutation (`POST`/`PUT`/`PATCH`/`DELETE`) — if `navigator.onLine` is false or `fetch()` throws a network error, the request is diverted to the offline queue with an auto-generated `Idempotency-Key` and the caller receives an `OfflineQueuedError` (`code = 'OFFLINE_QUEUED'`) instead of a raw network exception. Callers handle this by surfacing a “will retry when online” banner; `replayQueue()` runs the same request shape later with the preserved idempotency key so the backend de-duplicates replays.
- GET requests are **not** queued — they are read-only and simply fail until connectivity returns. Requests that fail after an in-flight retry are also not queued (the caller already saw the first attempt).

### 21.4 Request Signing (Browser-Side)

- `requestSigner.ts` implements ECDSA P-256 signing using the Web Crypto API.
- `buildCanonical(method, path, timestamp, nonce, deviceId, body)` constructs the 7-line canonical form (`METHOD\nPATH\nX-Timestamp\nX-Nonce\nX-Device-ID\nsha256_hex(body)\n`).
- `signRequest(canonical, privateKey)` produces a base64-encoded ECDSA signature appended as `X-Request-Signature`.
- Signed requests are used for: bargaining offer submission, counter-accept, and any mutation that requires non-repudiation.
- **Device enrollment is wired into the login path.** After `applyLoginResponse` + `loadSession` complete, `useAuthStore.login()` invokes `useDeviceKey().ensureEnrolled()` before returning to the caller. `ensureEnrolled` is idempotent — if IndexedDB already holds a `device_id`, it returns that id without contacting the challenge endpoint — so the cost on every login is one IndexedDB read after the first successful enrollment. Enrollment failure is surfaced via `auth.lastError` but does NOT roll back the login; the UI can prompt re-enrollment before the first signed mutation.

### 21.5 Shared UI Primitive Components

| Component | Purpose |
|---|---|
| `StatusChip` | Maps all backend status codes to label + color chip |
| `LoadingSpinner` | CSS spinner; sm/md/lg sizes |
| `EmptyState` | Icon + message for empty lists |
| `BannerAlert` | error/success/warning/info banners with optional dismiss |
| `OfflineBanner` | Shows offline/reconnecting/conflict states via `useOfflineStatus` |
| `MaskedValue` | Masked display with optional reveal for privileged roles |
| `TimestampDisplay` | `<time>` element rendering 12-hour local format |
| `CountdownTimer` | Live countdown with `setInterval`; emits `expired` event; urgent class <5min |
| `UploadPanel` | Drag-and-drop with MIME + 25MB validation before emit |
| `ModalDrawer` | `<teleport to="body">` overlay; Escape key + body scroll lock |
| `QueueBadge` | Red pill badge for queue counts in navigation |
| `TimelineList` | Vertical dot-line timeline for order event history |
| `ChecklistWidget` | Table view of document checklist with StatusChip per item |
| `PaginationControls` | Renders only when `total_pages > 1`; emits `page` events |
| `DataTable` | Generic typed table with Column render functions and action slot |

### 21.6 Timestamp Rule (Frontend)

All timestamps are stored and transmitted in UTC/ISO 8601. All display is in **12-hour local format** via the `useTimestamp` composable (`format12h` uses `toLocaleString` with `{ hour12: true }`). The `<time>` element's `datetime` attribute always contains the raw ISO value for accessibility.

### 21.7 Role-to-Screen Matrix

| Screen | candidate | proctor | reviewer | admin |
|---|---|---|---|---|
| Candidate Dashboard | ✓ | | | |
| My Profile | ✓ | | | |
| Documents (list/upload) | ✓ | | | |
| Services & Orders | ✓ | | | |
| Bargaining | ✓ | | | |
| Payment proof | ✓ | | | |
| Attendance Exceptions | ✓ | | | |
| Staff Dashboard | | ✓ | ✓ | ✓ |
| Document Queue | | | ✓ | ✓ |
| Document Review | | | ✓ | ✓ |
| Payment Queue | | | ✓ | ✓ |
| Order Queue | | | ✓ | ✓ |
| Exception Queue | | ✓ | ✓ | ✓ |
| Exception Review | | ✓ | ✓ | ✓ |
| After-Sales Queue | | | ✓ | ✓ |
| Admin Dashboard | | | | ✓ |
| Audit Log | | | | ✓ |
| Config/Feature Flags | | | | ✓ |

Route guards in `router/index.ts` enforce these boundaries client-side. Backend RBAC is the authoritative enforcement layer.

### 21.8 Feature Flag Gating (Frontend)

The `useSessionStore().bargainingEnabled` flag gates the bargaining pricing mode option in `ServiceCatalogView`. If the flag is `false`, all items are shown at fixed price regardless of their `bargaining_enabled` attribute. Flag values are loaded from the backend config center on session initialization.

---

## §22 Admin Security & Policy Surfaces

All admin routes are gated by `require_role(UserRole.admin)`. No reviewer can access these surfaces.

### 22.1 RBAC Policy Inspection
`GET /api/v1/admin/rbac-policy` exposes the static role-permission matrix from `security/rbac.py`: `DOWNLOAD_APPROVED_ROLES`, `PRIVILEGED_ROLES`, and the route-level restriction map. Read-only, no mutation.

### 22.2 Column Masking Policy
`GET /api/v1/admin/masking-policy` documents which fields are masked at what level, which roles see unmasked values, and which download paths apply watermarking. Sourced from `security/data_masking.py` + `security/rbac.py`.

### 22.3 Audit Search
`GET /api/v1/admin/audit` with query params `event_type`, `actor_id`, `resource_type`, `resource_id`, `outcome`, `from_date`, `to_date`. Uses `ConfigRepository.search_audit()` which queries `audit_events` with indexes on `event_type`, `actor_id`, `occurred_at`. Paginated.

---

## §23 Local Config Center & Canary Routing

### 23.1 Feature Flags
`FeatureFlag` table (key, value, value_type, description, updated_by). All mutations record a `FeatureFlagHistory` row (old_value, new_value, changed_by, changed_at, change_reason). `AuditEventType.feature_flag_changed` is recorded on every set. Admin-only CRUD via `ConfigService`.

### 23.2 Cohort Definitions
`CohortDefinition` (cohort_key, name, flag_overrides JSONB, is_active). `CanaryAssignment` links user→cohort (one assignment per user). Admin assigns/removes users via `POST /admin/cohorts/{id}/assign` and `DELETE /admin/cohorts/{id}/users/{uid}`.

### 23.3 Canary Routing Decision
`ConfigService.resolve_flags_for_user(user_id)` returns `(resolved_flags, cohort_key)`:
1. Load base flags from `feature_flags` table.
2. Load user's `CanaryAssignment` → `CohortDefinition`.
3. If cohort is active, merge `flag_overrides` on top of base flags.
4. Return merged dict.

`GET /admin/config/bootstrap/{user_id}` surfaces this decision (with `feature_flags`, `flag_overrides`, `resolved_flags`, `cohort_key`, `signature`) so admins can verify what config any user receives. The `signature` is an HMAC-SHA256 over the canonical JSON bootstrap payload, keyed by the server `SECRET_KEY`, so clients that know the shared secret can detect tampering; `verify_bootstrap_signature(...)` performs the constant-time comparison.

### 23.4 Frontend Config Bootstrap
`useSessionStore` holds `featureFlags` and `cohort`. On login the session store's `apply()` is called with the config returned from the backend. `bargainingEnabled` and `rollbackEnabled` are computed properties read by business views.

---

## §24 Observability

### 24.1 Structured Logging
`telemetry/logging.py`: structlog with `redact_processor` removing sensitive keys before emission. Every request binds a trace ID via `TraceIdMiddleware`. Log format: JSON with `trace_id`, `level`, `timestamp`, `event`, and contextual fields. Logs never emit passwords, tokens, signatures, or unmasked PII.

### 24.2 Metrics
`telemetry/metrics.py`: in-process `MetricsRegistry` with `Counter` and `Histogram`. Exposed at `GET /api/v1/internal/metrics` in Prometheus text format. Registered metrics:
- `merittrack_login_attempts_total{outcome}` — login success/failure counts
- `merittrack_signature_failures_total{reason}` — ECDSA rejection reasons
- `merittrack_request_duration_seconds{route,method,status}` — HTTP latency histogram
- `merittrack_document_uploads_total{outcome}` — upload success/failure
- `merittrack_order_transitions_total{from_state,to_state}` — order state changes
- `merittrack_exception_approvals_total{outcome,stage}` — attendance decision counts
- `merittrack_queue_actions_total{queue,action}` — staff queue operations
- `merittrack_export_jobs_total{export_type,outcome}` — export completions
- `merittrack_feature_flag_changes_total{key}` — flag mutation count

`GET /api/v1/admin/metrics/summary` returns a structured dict summary for admin UI.

### 24.3 Trace Correlation
`telemetry/tracing.py`: `span(operation, session, user_id)` async context manager. Writes `TelemetryCorrelation` rows (trace_id, span_id, operation, user_id, occurred_at, duration_ms, outcome, detail). Queryable via `GET /api/v1/admin/traces?trace_id=...`. The same trace ID echoed in `X-Request-ID` response header.

### 24.4 Access Log Summaries
`cache_stats` worker (15-min interval) reads histogram label data and writes `AccessLogSummary` (window_start/end, endpoint_group, total_requests, p50_latency_ms, p95_latency_ms, error_count). Queryable via `GET /api/v1/admin/access-logs`.

---

## §25 Capacity & Bandwidth Forecasting

`ForecastingService.compute_forecast(horizon_days, input_window_days)`:
1. Query `AccessLogSummary` rows for the input window.
2. Compute average requests/window (15-min). Scale to daily (×96 windows/day).
3. Build `request_volume_forecast: {date_str: int}` for each horizon day (flat projection from rolling average; extensible to linear regression).
4. Estimate bandwidth: 5% of forecast requests are uploads; `bandwidth_p50 = uploads × 500KB`, `bandwidth_p95 = uploads × 5MB`.
5. Persist `ForecastSnapshot` and return.

`run_forecasting_loop` (3600s interval) calls this automatically with horizon=30, input_window=90. Manual trigger: `POST /api/v1/admin/forecasts/compute`. Snapshots listed via `GET /api/v1/admin/forecasts`.

Forecast snapshots are stored in PostgreSQL (`forecast_snapshots` table), not on the filesystem. The `FORECASTS_ROOT` env var is reserved for future file-based snapshot export.

---

## §26 Cache-Hit Rate Reporting & Export Controls

### 26.1 Cache Hit Reporting
`run_cache_stats_loop` (900s interval) classifies requests by route prefix into `static` (assets/favicon/fonts), `api`, `other`. For static assets, 2xx non-error responses are treated as cache hits (same-deployment heuristic). Writes `CacheHitStat` rows (window_start/end, asset_group, total/hits/misses, hit_rate_pct). Exposed via `GET /api/v1/admin/cache-stats`.

### 26.2 Export Controls
All exports are admin-only. `ExportService`:
- Creates an `ExportJob` record (status=pending).
- Generates content (CSV from `audit_events` or `forecast_snapshots`).
- Computes SHA-256 and stores it in `ExportJob.sha256_hash`.
- Records watermark_username and watermark_timestamp (not applied to CSV — watermark is metadata recorded for audit; PDF watermark applies to document downloads only).
- Persists file to `EXPORTS_ROOT/{job_id}_{type}.csv`.
- Sets status=completed.

Download: `GET /api/v1/admin/exports/{id}/download` streams the file with `Content-Disposition: attachment`. Access is audited via `document_downloaded` event.

Policy-denied outcomes: non-admin actors receive 403 at route level. Export jobs that fail (bad export_type, filesystem error) set status=failed with error_message.

### 26.3 Frontend Admin Views
New admin screens added in Prompts 7:
- `/admin/config` (enhanced) — inline flag edit form with reason field, cohort table
- `/admin/audit` (enhanced) — search filters (event_type, actor_id, outcome, date range)
- `/admin/observability` — metrics summary cards, cache hit rate table, trace search input
- `/admin/forecasts` — snapshot table + manual trigger
- `/admin/exports` — export job creation form + history table with download links

---

## §27 Docker Topology

### 27.1 Runtime Service Map

| Service | Image | Port | Role |
|---|---|---|---|
| `backend` | Built from `repo/backend/Dockerfile` | 8443 (host-exposed) | FastAPI app + static asset server; sole HTTPS entrypoint |
| `db` | `postgres:14-alpine` | Internal only | PostgreSQL 14; no host port exposure |
| `frontend-builder` | Built from `repo/frontend/Dockerfile` (target: builder) | N/A | Vite build + test runner; only active under `--profile build` |

**Frontend asset serving:** The `frontend-builder` service compiles the Vue app into the `frontend_dist` Docker volume. The `backend` service mounts this volume at `/app/frontend_dist` and serves it via FastAPI `StaticFiles`. No separate static server or reverse proxy exists.

**TLS:** The backend container loads `/certs/cert.pem` and `/certs/key.pem` (mounted from the host `./certs/` directory) and passes them to uvicorn. These files must be pre-created; there is no auto-provisioning.

**Secret injection:** `./secrets/` is mounted read-only at `/secrets/` inside the backend container. The KEK file (`kek.key`) and JWT key files must exist before startup. The settings validator rejects a missing `KEK_PATH` at launch.

### 27.2 Network Isolation

All services share the `internal` bridge network. Only the `backend` service exposes a port to the host (`${HTTPS_PORT:-8443}:8443`). `db` is not directly reachable from the host.

### 27.3 Health Checks

- `db`: `pg_isready` every 10s (5 retries). Backend `depends_on: db: condition: service_healthy`.
- `backend`: `curl -kf https://localhost:8443/api/v1/internal/health` every 30s.

---

## §28 Test Isolation Strategy

### 28.1 Backend Tests

All backend API tests (`api_tests/`) run against a **real PostgreSQL** instance — no in-memory substitute, no FastAPI dependency overrides. `run_tests.sh backend-api` brings up the `db` compose service and points `DATABASE_URL` at `postgresql+psycopg2://…@db:5432/merittrack` before invoking pytest. `conftest.pytest_configure` runs `Base.metadata.create_all` once via a sync `psycopg2` engine and then reconfigures the app's async engine with `NullPool` (asyncpg connections are bound to the event loop that created them; pytest-asyncio gives each test a fresh loop, so pooled re-use would raise a "different loop" error). An autouse async fixture `_clean_tables` truncates every public table before each test for isolation.

Because `get_db` is not overridden, every route-handler exercises the production database path: asyncpg driver, Postgres-native types (UUID, JSONB, INET), server-side defaults, and real uniqueness / FK / cascade semantics.

**Why the earlier SQLite-based harness was dropped:** SQLite + `@compiles` worked for ORM-level query coverage but registered as *mocked HTTP* under strict no-mock criteria (because `app.dependency_overrides[get_db]` was installed). Any test audit that counts dependency overrides as mocking would classify 84 of 85 endpoints as mocked. Running the same suite against a real Postgres dissolves that classification at the cost of needing Docker's `db` service available — a small price given Docker is already the only supported orchestration.

### 28.2 Frontend Browser Tests

Playwright browser tests (`unit_tests/browser/`) do not require a live backend. All API calls are intercepted via `page.route()` with mocked responses. Auth state is initialized via `page.addInitScript()`. The Playwright `webServer` config in `playwright.config.ts` auto-starts the Vite dev server (`npx vite --port 5173`) so `npx playwright test` is self-contained inside the frontend-builder container.
