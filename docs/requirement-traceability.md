# MeritTrack — Requirement-to-Module Traceability

This document maps every major requirement from the original prompt to the implementing module(s). Updated each prompt.

## REQ-001: Candidate Profile Management
**Requirement:** Candidates maintain a profile with application details, initial exam scores, and transfer preferences.
**Frontend:** `src/views/candidate/profile/ProfileView.vue`, `src/views/candidate/profile/ExamScoresView.vue`, `src/views/candidate/profile/TransferPreferencesView.vue`, `src/stores/candidate.ts`, `src/services/candidateApi.ts`
**Backend:** `src/api/routes/candidates.py`, `src/schemas/candidate.py`, `src/services/candidate_service.py`, `src/persistence/repositories/candidate_repo.py`
**DB Table(s):** `candidate_profiles`, `exam_scores`, `transfer_preferences`, `profile_history`
**Schema Class(es):** `CandidateProfileRead`, `CandidateProfileUpdate`, `ExamScoreRead`, `ExamScoreUpdate`, `TransferPreferenceRead`, `TransferPreferenceUpdate`
**Test Coverage:** `api_tests/test_candidates.py` (profile create, duplicate 409, row-scope 403, update, exam score, checklist, list-all reviewer 200 / candidate 403)
**Status:** Implemented (Prompt 4); `GET /api/v1/candidates` list-all endpoint and tests added (Prompt 10)

## REQ-002: Document Upload and Review
**Requirement:** Upload PDF/JPG/PNG ≤ 25 MB, checklist tracking, versioned resubmissions, "Needs resubmission" status with reason, SHA-256 verification.
**Frontend:** `src/views/candidate/documents/DocumentListView.vue`, `src/views/candidate/documents/DocumentUploadView.vue`, `src/stores/document.ts`, `src/services/documentApi.ts`
**Backend:** `src/api/routes/documents.py`, `src/services/document_service.py`, `src/storage/file_store.py`, `src/security/watermark.py`, `src/schemas/document.py`, `src/domain/document_policy.py`
**DB Table(s):** `documents`, `document_versions`, `document_reviews`, `document_requirements`, `checklist_templates`, `checklist_template_items`, `document_access_grants`
**Schema Class(es):** `DocumentRead`, `DocumentVersionRead`, `DocumentReviewRead`, `DocumentReviewCreate`, `ChecklistItemRead`, `DocumentUploadResponse`
**Domain Invariants:** `validate_upload()` (MIME + size), `requires_resubmission_reason()`, `validate_review_decision()`
**Test Coverage:** `api_tests/test_documents.py` (upload valid/invalid/too-large, resubmission versioning, review, download, cross-user upload 403), `unit_tests/test_document_policy.py`, `unit_tests/test_schemas_validation.py`
**Status:** Implemented (Prompt 4); cross-user ownership enforcement added (Prompt 11)

## REQ-003: Fee-Based Service Ordering (Fixed-Price Mode)
**Requirement:** Order placement, order states, timeline with 12-hour timestamps.
**Frontend:** `src/views/candidate/orders/OrderListView.vue`, `src/views/candidate/orders/OrderDetailView.vue`, `src/stores/order.ts`, `src/composables/useTimestamp.ts`
**Backend:** `src/api/routes/orders.py`, `src/api/routes/payment.py`, `src/domain/order_state_machine.py`, `src/services/order_service.py`, `src/services/payment_service.py`, `src/persistence/repositories/order_repo.py`, `src/schemas/order.py`
**DB Table(s):** `service_items`, `service_item_inventory`, `orders`, `order_events`, `payment_records`, `fulfillment_milestones`, `vouchers`
**Schema Class(es):** `ServiceItemRead`, `OrderCreate`, `OrderRead`, `OrderEventRead`, `PaymentConfirmRequest`, `MilestoneCreate`, `VoucherRead`
**Domain Invariants:** `validate_transition()` in `order_state_machine.py`
**Test Coverage:** `api_tests/test_orders.py`, `api_tests/test_payment.py`, `api_tests/test_refund_after_sales.py`, `unit_tests/test_order_state_machine.py`, `unit_tests/test_order_state_machine_extended.py`, `unit_tests/views/OrderListView.spec.ts`, `unit_tests/views/OrderDetailView.spec.ts`
**Status:** Implemented (Prompt 4); test coverage expanded (Prompt 8); cross-user ownership checks added for proof submit and confirm-receipt (Prompt 11)

## REQ-004: Bargaining Mode
**Requirement:** Up to 3 candidate offers in 48 hours; reviewer may accept or counter once; post-counter resolution or expiry; feature-flag controlled.
**Frontend:** `src/views/candidate/orders/BargainingView.vue`, `src/stores/bargaining.ts`, `src/stores/order.ts`, `src/composables/useFeatureFlag.ts`
**Backend:** `src/api/routes/bargaining.py`, `src/domain/bargaining.py`, `src/services/bargaining_service.py`, `src/schemas/bargaining.py`
**DB Table(s):** `bargaining_threads`, `bargaining_offers`
**Schema Class(es):** `BargainingThreadRead`, `OfferCreate`, `OfferRead`, `CounterCreate`, `BargainingAcceptRequest`
**Domain Invariants:** `can_submit_offer()` (max 3, 48h window), `can_counter()` (max 1), `is_window_expired()`
**Test Coverage:** `api_tests/test_payment.py` (bargaining section), `unit_tests/test_bargaining_rules.py`, `unit_tests/test_schemas_validation.py`, `unit_tests/views/BargainingView.spec.ts`, `unit_tests/views/OrderDetailView.spec.ts`
**Status:** Implemented (Prompt 4); test coverage expanded (Prompt 8); cross-user ownership checks added for submit_offer and accept_counter (Prompt 11)

## REQ-005: 30-Minute Auto-Cancel and Capacity Rollback
**Requirement:** Orders auto-cancel after 30 minutes at pending_payment; atomic rollback of capacity/slots; feature flag for rollback on refund.
**Frontend:** `src/components/common/CountdownTimer.vue` (rendered by `src/views/candidate/orders/OrderDetailView.vue` when `auto_cancel_at` is set)
**Backend:** `src/workers/auto_cancel.py`, `src/domain/order_state_machine.py`, `src/persistence/order_repo.py`
**DB Table(s):** `orders`, `order_events`, `service_item_inventory`, `rollback_events`
**Schema Class(es):** `OrderRead`, `OrderEventRead`
**Domain Invariants:** Auto-cancel transition (`pending_payment → canceled`) in `order_state_machine.py`; `config.auto_cancel_minutes = 30`
**Test Coverage:** `unit_tests/test_order_state_machine.py` (terminal states), `unit_tests/test_order_state_machine_extended.py` (auto-cancel timing), `unit_tests/views/OrderDetailView.spec.ts` (countdown rendered)
**Status:** Implemented (Prompt 4); test coverage expanded (Prompt 8)

## REQ-006: After-Sales Service (14-Day Window)
**Requirement:** Candidates may request after-sales within 14 days of order completion.
**Frontend:** `src/stores/order.ts` (`submitAfterSales` action), `src/services/refundApi.ts` (`submitAfterSales`, `resolveAfterSales`); staff resolution UI: `src/views/staff/orders/AfterSalesQueueView.vue`. _No dedicated candidate-facing view currently exists — after-sales submission is composed within the order store/detail flow until a dedicated candidate view ships._
**Backend:** `src/api/routes/refunds.py` (after-sales section), `src/domain/after_sales_policy.py`, `src/services/after_sales_service.py`
**DB Table(s):** `after_sales_requests`
**Schema Class(es):** *(no dedicated schema module — uses `OrderRead` parent reference)*
**Domain Invariants:** `is_within_window()`, `assert_within_window()`, `compute_window_expiry()`; `config.after_sales_window_days = 14`
**Test Coverage:** `api_tests/test_refund_after_sales.py` (after-sales within/outside window, resolve), `unit_tests/test_after_sales_policy.py`
**Status:** Implemented (Prompt 4); cross-user ownership check added for after-sales submit (Prompt 11)

## REQ-007: Attendance Exception Handling
**Requirement:** Proof upload, routed review (Proctor → Reviewer), immutable approval trail, searchable outcomes.
**Frontend:** `src/views/candidate/attendance/ExceptionListView.vue`, `src/views/candidate/attendance/ExceptionDetailView.vue`, `src/views/staff/attendance/ExceptionQueueView.vue`, `src/views/staff/attendance/ExceptionReviewView.vue`, `src/stores/attendance.ts`
**Backend:** `src/api/routes/attendance.py`, `src/domain/exception_workflow.py`, `src/services/attendance_service.py`, `src/persistence/repositories/attendance_repo.py`, `src/schemas/attendance.py`
**DB Table(s):** `attendance_anomalies`, `attendance_exceptions`, `exception_proofs`, `exception_review_steps`, `exception_approvals`
**Schema Class(es):** `AttendanceExceptionCreate`, `ExceptionRead`, `ExceptionReviewStepRead`, `ReviewDecisionCreate`, `ProofUploadResponse`
**Domain Invariants:** `can_adjudicate()`, `validate_decision()`, `next_stage()`, `resolve_status()` in `exception_workflow.py`; `exception_review_steps` and `exception_approvals` are append-only (no UPDATE paths)
**Test Coverage:** `api_tests/test_attendance.py` (8 BE-API tests), `api_tests/test_queue_endpoints.py` (GET /queue/exceptions HTTP tests), `unit_tests/test_exception_workflow.py`, `unit_tests/views/ExceptionListView.spec.ts`, `unit_tests/views/ExceptionReviewView.spec.ts`
**Status:** Implemented (Prompt 4); test coverage expanded (Prompt 8)

## REQ-008: Staff Operational Queues
**Requirement:** Order confirmation, voucher issuance, milestone updates, appeal adjudication; searchable, consistent statuses.
**Frontend:** `src/views/staff/orders/OrderQueueView.vue`, `src/views/staff/orders/PaymentQueueView.vue`, `src/views/staff/orders/AfterSalesQueueView.vue`, `src/views/staff/attendance/ExceptionQueueView.vue`, `src/views/staff/documents/DocumentQueueView.vue`, `src/stores/queue.ts`
**Backend:** `src/api/routes/queue.py`, `src/services/queue_service.py`, `src/schemas/queue.py`
**DB Table(s):** `orders`, `order_events`, `attendance_exceptions`, `vouchers`, `fulfillment_milestones`
**Schema Class(es):** `OrderRead`, `OrderEventRead`, `VoucherRead`, `MilestoneCreate`, `ExceptionRead`
**Test Coverage:** `api_tests/test_queue_endpoints.py` (15 BE-API tests for all 5 queue routes with role gates, pagination, status filter), `unit_tests/test_refund_attendance_unit.py` (queue filter logic), `unit_tests/browser/reviewer_queue_workflow.spec.ts`
**Status:** Implemented (Prompt 4 backend; Prompt 6 frontend); BE-API queue coverage upgraded (Prompt 8)

## REQ-009: Local Authentication (Argon2id, JWT, Refresh)
**Requirement:** Min 12-char password, Argon2id, 15-min JWT access tokens, refresh token rotation, device binding.
**Frontend:** `src/views/auth/LoginView.vue`, `src/stores/auth.ts`, `src/stores/session.ts`, `src/services/authApi.ts`, `src/services/http.ts`, `src/composables/useAuth.ts`, `src/components/auth/LoginForm.vue`
**Backend:** `src/security/passwords.py`, `src/security/jwt.py`, `src/security/refresh_tokens.py`, `src/security/throttling.py`, `src/services/auth_service.py`, `src/api/routes/auth.py`, `src/api/dependencies.py`, `src/schemas/auth.py`
**DB Table(s):** `users`, `refresh_token_families`, `refresh_tokens`, `device_registrations`, `login_throttles`
**Schema Class(es):** `LoginRequest`, `TokenResponse`, `RefreshRequest`, `RefreshResponse`, `DeviceRegisterRequest`, `DeviceRegisterResponse`, `PasswordChangeRequest`, `LogoutRequest`
**Domain Invariants:** Argon2id (time=3, mem=64MiB, par=4); RS256 JWT with `mt-signing-1` kid, 15-min TTL; refresh reuse invalidates family with `reuse_detected`; per-username throttle (5 / 15 min)
**Status:** Security infrastructure (Prompt 3)

## REQ-010: Request Signing and Nonce Anti-Replay
**Requirement:** Device-bound API signing; 5-minute server-stored nonce window; replay rejection.
**Frontend:** `src/services/requestSigner.ts`, `src/services/deviceKey.ts`, `src/services/http.ts`, `src/composables/useDeviceKey.ts`
**Backend:** `src/security/nonce.py`, `src/security/signing.py`, `src/security/device_keys.py`, `src/api/dependencies.py` (`require_signed_request`)
**DB Table(s):** `nonces`, `device_registrations`
**Schema Class(es):** `DeviceRegisterRequest`, `DeviceChallengeRequest`, `DeviceChallengeResponse`, `DeviceActivateRequest`, `DeviceRotateRequest`, `DeviceRevokeRequest`
**Domain Invariants:** ECDSA P-256; canonical form `METHOD\nPATH\nX-Timestamp\nX-Nonce\nX-Device-ID\nsha256(body)\n`; `nonces.nonce_value` UNIQUE with 5-min expiry; ±30s clock skew
**Status:** Security infrastructure (Prompt 3). Audit-5 B2: `require_signed_request` dependency extended to all financial and workflow mutation endpoints — payment proof/confirm, voucher, milestones, refund initiate/process, after-sales create/resolve, attendance proof/review. Full signed-route inventory lives in `docs/api-spec.md` §3.2 and must stay in sync with `config.py:signature_required_paths` and the frontend `SIGNED_PATHS` prefix list in `services/http.ts`. Audit-1 B2: FE enrollment flow aligned with BE `DeviceChallengeRequest` (`{device_fingerprint, public_key_pem}`) and `DeviceActivateRequest` (five-field payload); enrollment signature now signs the **raw challenge nonce bytes** via new `signEnrollmentNonce` helper in `requestSigner.ts` — distinct from the in-session request-canonical form. The FE no longer double-posts to `/device/register` after activate (activate is atomic). Device-ID is read from the activate response.

## REQ-011: Internal Identity Provider (SSO)
**Requirement:** Internal IdP without external dependencies; trusted-client registry.
**Frontend:** `src/services/authApi.ts`
**Backend:** `src/security/idp.py`, `src/security/jwt.py`, `src/api/routes/idp.py`
**DB Table(s):** `idp_clients`, `users`
**Schema Class(es):** `TokenResponse` (reused for IdP token endpoint)
**Domain Invariants:** client_credentials only; IdP tokens signed with the same RS256 key; JWKS exposed at `GET /api/v1/idp/jwks`; private key material never exported
**Status:** Security infrastructure (Prompt 3)

## REQ-012: RBAC and Row/Column-Level Controls
**Requirement:** Route, function, object, row, and column-level access control; 4 role boundaries.
**Frontend:** `src/composables/usePermissions.ts`, `src/router/guards.ts`, `src/components/nav/RoleAwareNav.vue`
**Backend:** `src/security/rbac.py`, `src/security/data_masking.py`, `src/api/dependencies.py` (`require_role`)
**DB Table(s):** `users` (role CHECK constraint), `document_access_grants`
**Schema Class(es):** `CandidateProfileRead` (column-level masking via `@field_serializer`)
**Domain Invariants:** `rbac.require_role`, `rbac.assert_owner`, `rbac.scope_rows_to_actor`, `data_masking.is_privileged` — all four layers live in real code
**Status:** Security infrastructure (Prompt 3)

## REQ-013: Sensitive Field Masking and Restricted Downloads
**Requirement:** SSN masked to last 4, restricted document downloads to approved roles only.
**Frontend:** `src/components/common/ErrorEnvelope.vue` (safe rendering); `src/composables/usePermissions.ts`
**Backend:** `src/security/data_masking.py`, `src/security/rbac.DOWNLOAD_APPROVED_ROLES`
**DB Table(s):** `candidate_profiles` (encrypted `ssn_encrypted`, `dob_encrypted`, `phone_encrypted`, `email_encrypted` + `*_key_version` columns), `document_access_grants`
**Schema Class(es):** `CandidateProfileRead` (masking helpers consume `SerializationContext.role`)
**Domain Invariants:** SSN → last 4, DOB → year only, phone → last 4, email → domain only; full values only when context role ∈ {reviewer, admin}
**Test Coverage:** `unit_tests/test_data_masking.py`, `api_tests/test_documents.py` (download forbidden for candidate; reviewer allowed + watermarked), `api_tests/test_candidates.py` (masked fields in profile read)
**Status:** Implemented (Prompt 3 — primitives; Prompt 4 — download route integration)

## REQ-014: Watermarking and SHA-256 Verification
**Requirement:** Every exported/downloaded PDF watermarked (username + timestamp); SHA-256 on upload and download.
**Backend:** `src/security/watermark.py`, `src/security/hashing.py`
**DB Table(s):** `document_versions` (`sha256_hash` NOT NULL), `export_jobs` (`sha256_hash`, `watermark_applied` bool)
**Schema Class(es):** `ExportJobRead` (from `src/schemas/audit.py`)
**Domain Invariants:** `apply_pdf_watermark` idempotent (re-application replaces, not stacks); `sha256_of_stream` matches one-shot `sha256_of_bytes`; `verify_sha256` boolean return
**Test Coverage:** `unit_tests/test_watermark.py`, `unit_tests/test_hashing.py`, `api_tests/test_documents.py` (download serves watermarked content; SHA-256 header returned), `api_tests/test_admin.py` (export watermark_applied=True, sha256_hash stored)
**Status:** Implemented (Prompt 3 — primitives; Prompt 4 — route integration)

## REQ-015: Envelope Encryption at Rest
**Requirement:** Sensitive fields encrypted with AES-256-GCM DEK + locally managed KEK; key versioning.
**Backend:** `src/security/encryption.py`, `src/persistence/models/candidate.py`
**DB Table(s):** `candidate_profiles` (`*_encrypted` ciphertext columns + `*_key_version` columns)
**Schema Class(es):** *(encryption transparent at persistence layer; schemas work with plaintext values)*
**Domain Invariants:** KEK loaded from `kek_path/v{N}.key`; DEK per call wrapped with KEK (AES-256-GCM, AAD = resource id); `encrypt_field` returns `(ciphertext_b64, key_version)`; `decrypt_field` re-derives DEK
**Status:** Security infrastructure (Prompt 3)

## REQ-016: HTTPS with Local Certificates
**Requirement:** End-to-end TLS using locally provisioned certificates.
**Backend:** `src/main.py`, `repo/backend/Dockerfile`, `repo/docker-compose.yml`
**DB Table(s):** *(none — infrastructure concern)*
**Test Coverage:** Infrastructure only — verified via `docker-compose.yml` `TLS_CERT_PATH`/`TLS_KEY_PATH` env vars wired to Uvicorn `--ssl-certfile`/`--ssl-keyfile`; not testable in unit/API test layer
**Status:** Implemented (Prompt 9 — Docker/TLS hardening)

## REQ-017: Unified Observability (Logs, Metrics, Traces)
**Requirement:** Structured JSON logs, Prometheus-style metrics, trace correlation for critical flows.
**Backend:** `src/telemetry/logging.py`, `src/telemetry/metrics.py`, `src/telemetry/tracing.py`, `src/api/middleware.py` (`TraceIdMiddleware`, `AccessLogMiddleware`)
**DB Table(s):** `telemetry_correlations`, `access_log_summaries`
**Schema Class(es):** `AuditEventRead`, `CacheHitStatRead` (from `src/schemas/audit.py`)
**Domain Invariants:** structlog JSON output with secret redaction; counters `merittrack_login_attempts_total`, `merittrack_signature_failures_total`, histogram `merittrack_request_duration_seconds`; `X-Request-ID` propagated into structlog context
**Test Coverage:** `api_tests/test_error_envelope_secrets.py` (no stack trace in 500, no secret echo), `api_tests/test_admin.py` (metrics summary, traces, cache stats, access logs), `unit_tests/views/ObservabilityView.spec.ts`
**Status:** Implemented (Prompt 3 — infrastructure; Prompt 7 — admin surfaces)

## REQ-018: Config Center and Feature Flags
**Requirement:** Local config center; feature flags (bargaining on/off, rollback on/off); change audit trail.
**Frontend:** `src/composables/useFeatureFlag.ts`
**Backend:** `src/domain/feature_flags.py`, `src/api/routes/admin.py`, `src/services/config_service.py`, `src/schemas/config.py`
**DB Table(s):** `feature_flags`, `feature_flag_history`
**Schema Class(es):** `FeatureFlagRead`, `FeatureFlagUpdate`
**Test Coverage:** `api_tests/test_admin.py` (create, update, list flags; history recorded), `unit_tests/test_config_service_unit.py`, `unit_tests/views/ConfigView.spec.ts`, `unit_tests/browser/admin_config_workflow.spec.ts`
**Status:** Implemented (Prompt 7)

## REQ-019: Canary / Cohort Routing
**Requirement:** User cohort assignment; signed bootstrap config; cohort-aware feature resolution without external traffic manager.
**Frontend:** `src/stores/session.ts`, `src/composables/useFeatureFlag.ts`
**Backend:** `src/domain/cohort.py`, `src/api/routes/admin.py`, `src/services/config_service.py`, `src/schemas/config.py`
**DB Table(s):** `cohort_definitions`, `canary_assignments`
**Schema Class(es):** `CohortDefinitionRead`, `CohortAssignmentCreate`, `BootstrapConfigResponse`
**Domain Invariants:** `cohort_definitions.flag_overrides` JSONB; `canary_assignments (user_id, cohort_id)` UNIQUE; `BootstrapConfigResponse.signature` field for tamper detection
**Test Coverage:** `api_tests/test_admin.py` (cohort create/assign/remove, bootstrap config, per-user flag resolution), `unit_tests/test_config_service_unit.py` (cohort override wins, inactive cohort ignored, bootstrap signature)
**Status:** Implemented (Prompt 7)

## REQ-020: Capacity and Bandwidth Forecasting
**Requirement:** Rolling-window aggregates, percentile-based bandwidth, trend projections from historical data; offline local computation.
**Frontend:** `src/views/admin/ForecastView.vue`
**Backend:** `src/workers/forecasting.py`, `src/api/routes/admin.py` (forecast endpoints), `src/services/forecasting_service.py`
**DB Table(s):** `forecast_snapshots` (JSONB payload), `access_log_summaries`, `cache_hit_stats`
**Schema Class(es):** `ForecastSnapshotRead` (from `src/schemas/audit.py`)
**Test Coverage:** `api_tests/test_admin.py` (list forecasts, trigger forecast), `unit_tests/test_forecasting_unit.py` (empty baseline, daily avg, p50/p95, horizon length), `unit_tests/views/ForecastView.spec.ts`
**Status:** Implemented (Prompt 7)

## REQ-021: Offline Cache Policy and Hit-Rate Reporting
**Requirement:** Cache-Control/ETag headers on static assets; hit-rate reporting from local access logs; optional service worker.
**Frontend:** Vite build config, `public/sw.js` (optional)
**Backend:** `src/workers/cache_stats.py`, `src/api/routes/admin.py` (cache-stats endpoint), `src/main.py` (static file handler config)
**DB Table(s):** `cache_hit_stats`
**Schema Class(es):** `CacheHitStatRead` (from `src/schemas/audit.py`)
**Test Coverage:** `api_tests/test_admin.py` (cache stats empty returns list), `unit_tests/views/ObservabilityView.spec.ts` (cache stats table with hit_rate_pct)
**Status:** Implemented (Prompt 7)

## REQ-022: IndexedDB Offline Queue
**Requirement:** Browser-side offline queue with IndexedDB backing; retry on reconnect.
**Frontend:** `src/services/offlineQueue.ts`, `src/composables/useOfflineQueue.ts`
**DB Table(s):** *(none — browser-side IndexedDB only)*
**Test Coverage:** `unit_tests/services/offlineQueue.spec.ts` (enqueue/dequeue/remove/list/clear, replay success/failure, singleton reset), `unit_tests/composables/useOfflineStatus.spec.ts` (offline/online events, replayQueue on reconnect)
**Status:** Implemented (Prompt 5)

---

## REQ-023: Candidate Onboarding
**Requirement:** Profile creation, encrypted PII, exam scores, transfer preferences, audit trail.
**Backend:** `src/api/routes/candidates.py`, `src/services/candidate_service.py`, `src/persistence/repositories/candidate_repo.py`, `src/schemas/candidate.py`
**DB Table(s):** `candidate_profiles`, `profile_history`, `exam_scores`, `transfer_preferences`
**Test Coverage:** `api_tests/test_candidates.py` (6 BE-API-HTTP tests)
**Status:** Implemented (Prompt 4)

## REQ-024: Document Pipeline
**Requirement:** Upload/validate/store/hash/review/resubmit/download with SHA-256 + watermark.
**Backend:** `src/api/routes/documents.py`, `src/services/document_service.py`, `src/persistence/repositories/document_repo.py`, `src/storage/file_store.py`, `src/domain/document_policy.py`
**DB Table(s):** `documents`, `document_versions`, `document_reviews`, `document_requirements`, `checklist_items`
**Test Coverage:** `api_tests/test_documents.py` (9 BE-API-HTTP tests), `unit_tests/test_document_service_unit.py` (10 BE-UNIT tests)
**Status:** Implemented (Prompt 4)

## REQ-025: Fee-Based Ordering with Auto-Cancel
**Requirement:** Order create, capacity reservation, auto-cancel timer, payment proof/confirm, milestones, state machine.
**Backend:** `src/api/routes/orders.py`, `src/api/routes/payment.py`, `src/services/order_service.py`, `src/services/payment_service.py`, `src/persistence/repositories/order_repo.py`, `src/workers/auto_cancel.py`
**DB Table(s):** `orders`, `order_events`, `payment_records`, `service_items`, `service_item_inventory`, `fulfillment_milestones`, `vouchers`
**Test Coverage:** `api_tests/test_orders.py` (6 BE-API-HTTP), `api_tests/test_payment.py` (7 BE-API-HTTP), `unit_tests/test_order_state_machine_extended.py` (17 BE-UNIT), `unit_tests/test_payment_service_unit.py` (12 BE-UNIT)
**Status:** Implemented (Prompt 4)

## REQ-026: Bargaining Flow
**Requirement:** Max 3 candidate offers in 48h window, reviewer counter-once, expiry worker.
**Backend:** `src/api/routes/bargaining.py`, `src/services/bargaining_service.py`, `src/domain/bargaining.py`, `src/workers/bargaining_expiry.py`
**DB Table(s):** `bargaining_threads`, `bargaining_offers`
**Test Coverage:** `api_tests/test_payment.py` (bargaining section), `unit_tests/test_order_state_machine_extended.py`
**Status:** Implemented (Prompt 4)

## REQ-027: Refund and Capacity Rollback
**Requirement:** Reviewer initiates refund, admin processes, capacity slot restored atomically.
**Backend:** `src/api/routes/refunds.py`, `src/services/refund_service.py`, `src/workers/refund_progression.py`
**DB Table(s):** `refund_records`, `rollback_events`
**Test Coverage:** `api_tests/test_refund_after_sales.py` (3 refund tests), `unit_tests/test_refund_attendance_unit.py`
**Status:** Implemented (Prompt 4)

## REQ-028: After-Sales Service
**Requirement:** 14-day window post-completion, open/resolve lifecycle.
**Backend:** `src/api/routes/refunds.py` (after-sales section), `src/services/after_sales_service.py`, `src/domain/after_sales_policy.py`
**DB Table(s):** `after_sales_requests`
**Test Coverage:** `api_tests/test_refund_after_sales.py` (3 after-sales tests)
**Status:** Implemented (Prompt 4)

## REQ-029: Attendance Exceptions
**Requirement:** Proof upload, staged review, immutable approval trail with signature hash.
**Backend:** `src/api/routes/attendance.py`, `src/services/attendance_service.py`, `src/persistence/repositories/attendance_repo.py`, `src/domain/exception_workflow.py`
**DB Table(s):** `attendance_anomalies`, `attendance_exceptions`, `exception_proofs`, `exception_review_steps`, `exception_approvals`
**Test Coverage:** `api_tests/test_attendance.py` (8 BE-API-HTTP), `unit_tests/test_refund_attendance_unit.py`
**Status:** Implemented (Prompt 4)

## REQ-030: Staff Queue Operations
**Requirement:** Five read-only paginated queue endpoints for reviewer/admin.
**Backend:** `src/api/routes/queue.py`, `src/services/queue_service.py`, `src/schemas/queue.py`
**Frontend:** `src/views/staff/documents/DocumentQueueView.vue`, `src/views/staff/orders/PaymentQueueView.vue`, `src/views/staff/orders/OrderQueueView.vue`, `src/views/staff/attendance/ExceptionQueueView.vue`, `src/views/staff/orders/AfterSalesQueueView.vue`, `src/stores/queue.ts`, `src/services/queueApi.ts`
**DB Table(s):** (read-only views across existing tables)
**Test Coverage:** Queue endpoints covered by `unit_tests/test_refund_attendance_unit.py` (filter logic); browser workflow covered by `unit_tests/browser/reviewer_queue_workflow.spec.ts`
**Status:** Implemented (Prompt 4 backend; Prompt 6 frontend)

## REQ-031: Frontend Application Shell and Routing
**Requirement:** Vue 3 SPA with role-aware navigation, lazy-loaded routes, route guards, and layout shells for candidate/staff/admin.
**Frontend:** `src/router/index.ts`, `src/views/candidate/CandidateLayout.vue`, `src/views/staff/StaffLayout.vue`, `src/views/admin/AdminLayout.vue`
**Test Coverage:** `unit_tests/stores/authSessionRefresh.spec.ts` (session store), `unit_tests/browser/login.spec.ts`, `unit_tests/browser/forbidden.spec.ts`
**Status:** Implemented (Prompt 5)

## REQ-032: Offline Queue (IndexedDB)
**Requirement:** Browser-side mutation queue with IndexedDB persistence and automatic replay on reconnect.
**Frontend:** `src/services/offlineQueue.ts` (`IndexedDbQueue`, `InMemoryQueue`, `replayQueue`, `getOfflineQueue`), `src/composables/useOfflineStatus.ts`, `src/components/common/OfflineBanner.vue`
**Test Coverage:** `unit_tests/services/offlineQueue.spec.ts` (7 tests), `unit_tests/composables/useOfflineStatus.spec.ts` (4 tests)
**Status:** Implemented (Prompt 5)

## REQ-033: Request Signing (Browser-Side)
**Requirement:** ECDSA P-256 request signing in browser using Web Crypto API; canonical form matches backend.
**Frontend:** `src/services/requestSigner.ts` (`buildCanonical`, `signRequest`, `generateNonce`, `sha256Hex`)
**Test Coverage:** `unit_tests/services/requestSigner.spec.ts` (nonce uniqueness, timestamp format, known SHA-256 hash, canonical structure)
**Status:** Implemented (Prompt 5)

## REQ-034: Candidate Onboarding Screens
**Requirement:** Profile create/edit, exam scores management, transfer preferences management, document checklist and upload UI.
**Frontend:** `src/views/candidate/profile/ProfileView.vue`, `src/views/candidate/profile/ExamScoresView.vue`, `src/views/candidate/profile/TransferPreferencesView.vue`, `src/views/candidate/documents/DocumentListView.vue`, `src/views/candidate/documents/DocumentUploadView.vue`
**Test Coverage:** `unit_tests/views/ProfileView.spec.ts`, `unit_tests/views/DocumentListView.spec.ts`, `unit_tests/views/DocumentUploadView.spec.ts`, `unit_tests/browser/document_upload_workflow.spec.ts`
**Status:** Implemented (Prompt 6)

## REQ-035: Order and Payment UI
**Requirement:** Service catalog, order placement with bargaining option, countdown timer for auto-cancel, payment proof form with duplicate-submit guard.
**Frontend:** `src/views/candidate/orders/ServiceCatalogView.vue`, `src/views/candidate/orders/OrderListView.vue`, `src/views/candidate/orders/OrderDetailView.vue`, `src/views/candidate/orders/BargainingView.vue`, `src/views/candidate/orders/PaymentView.vue`
**Test Coverage:** `unit_tests/views/BargainingView.spec.ts`, `unit_tests/views/PaymentView.spec.ts`, `unit_tests/browser/order_payment_workflow.spec.ts`
**Status:** Implemented (Prompt 6)

## REQ-036: Attendance Exception UI
**Requirement:** Exception list with status, exception detail with proof upload, review history; inline new exception form.
**Frontend:** `src/views/candidate/attendance/ExceptionListView.vue`, `src/views/candidate/attendance/ExceptionDetailView.vue`
**Test Coverage:** `unit_tests/views/ExceptionListView.spec.ts`
**Status:** Implemented (Prompt 6)

## REQ-037: Reviewer Document Review UI
**Requirement:** Review form with approve/reject/needs-resubmission decisions; resubmission reason mandatory when selected; download button.
**Frontend:** `src/views/staff/documents/DocumentQueueView.vue`, `src/views/staff/documents/DocumentReviewView.vue`
**Test Coverage:** `unit_tests/views/DocumentReviewView.spec.ts`, `unit_tests/browser/reviewer_document_review_workflow.spec.ts`
**Status:** Implemented (Prompt 6)

## REQ-038: Exception Review UI (Staff)
**Requirement:** Approve/reject/escalate decisions; escalate option visible only at initial stage; approval records prior steps.
**Frontend:** `src/views/staff/attendance/ExceptionQueueView.vue`, `src/views/staff/attendance/ExceptionReviewView.vue`
**Test Coverage:** `unit_tests/views/ExceptionReviewView.spec.ts`, `unit_tests/browser/reviewer_queue_workflow.spec.ts`
**Status:** Implemented (Prompt 6)

---

# Prompt 7 — Admin Controls, Config Center, Observability, Forecasting, Cache Reporting

## REQ-039: Feature Flag Management
**Requirement:** Admin can create, read, update feature flags; every change records history with old/new value, changed_by, reason; audit event written.
**Backend:** `src/persistence/models/config_audit.py` (FeatureFlag, FeatureFlagHistory), `src/persistence/repositories/config_repo.py`, `src/services/config_service.py`, `src/api/routes/admin.py`
**Test Coverage:** `api_tests/test_admin.py::test_create_feature_flag`, `::test_update_feature_flag`, `::test_feature_flag_update_history_recorded`, `unit_tests/test_config_service_unit.py`
**Status:** Implemented (Prompt 7)

## REQ-040: Cohort Definitions & Canary Assignment
**Requirement:** Admin defines stable cohorts with `flag_overrides`; assigns users to cohorts; resolves per-user flags by merging base + cohort overrides; bootstrap config endpoint shows resolved state.
**Backend:** `src/persistence/models/config_audit.py` (CohortDefinition, CanaryAssignment), `src/services/config_service.py`, `src/api/routes/admin.py`
**Test Coverage:** `api_tests/test_admin.py::test_create_cohort`, `::test_assign_user_to_cohort`, `::test_bootstrap_config_for_user`, `unit_tests/test_config_service_unit.py::test_resolve_flags_with_cohort_override`
**Status:** Implemented (Prompt 7)

## REQ-041: Audit Search
**Requirement:** Admin can search audit events by event_type, actor_id, resource_type, resource_id, outcome, date range; results paginated; no mutation path.
**Backend:** `src/persistence/repositories/config_repo.py::search_audit`, `src/api/routes/admin.py::search_audit`
**Test Coverage:** `api_tests/test_admin.py::test_audit_search_*`
**Status:** Implemented (Prompt 7)

## REQ-042: RBAC & Masking Policy Inspection
**Requirement:** Admin can view static RBAC role matrix, download-approved roles, and column masking rules per field.
**Backend:** `src/api/routes/admin.py::get_rbac_policy`, `::get_masking_policy`; sourced from `src/security/rbac.py`, `src/security/data_masking.py`
**Test Coverage:** `api_tests/test_admin.py::test_rbac_policy_endpoint`, `::test_masking_policy_endpoint`, `unit_tests/test_export_policy_unit.py::test_download_approved_roles_*`
**Status:** Implemented (Prompt 7)

## REQ-043: Observability — Metrics, Traces, Access Logs, Cache Hit Rate
**Requirement:** Structured logs with trace correlation; Prometheus-text metrics endpoint; trace correlation records in DB; access log summaries per endpoint group; cache hit/miss rates for static assets aggregated by worker.
**Backend:** `src/telemetry/metrics.py`, `src/telemetry/logging.py`, `src/telemetry/tracing.py`, `src/api/middleware.py`, `src/workers/cache_stats.py`, `src/services/telemetry_service.py`, `src/api/routes/admin.py`
**Test Coverage:** `api_tests/test_admin.py::test_metrics_summary_returns_dict`, `::test_cache_stats_empty_returns_list`, `unit_tests/views/ObservabilityView.spec.ts`
**Status:** Implemented (Prompt 7)

## REQ-044: Capacity & Bandwidth Forecasting
**Requirement:** Historical request-volume aggregation from access log summaries; document-size distribution estimated; 30-day forecast persisted as ForecastSnapshot; admin UI shows snapshots; manual trigger available.
**Backend:** `src/services/forecasting_service.py`, `src/workers/forecasting.py`, `src/persistence/repositories/config_repo.py::create_forecast_snapshot`, `src/api/routes/admin.py::list_forecasts`, `::trigger_forecast`
**Test Coverage:** `api_tests/test_admin.py::test_trigger_forecast`, `::test_list_forecasts_empty`, `unit_tests/test_forecasting_unit.py`
**Status:** Implemented (Prompt 7)

## REQ-045: Export Controls & Report History
**Requirement:** Admin-only export job creation (audit CSV, forecast CSV); SHA-256 stored per job; watermark_username recorded; export history list; file download with Content-Disposition attachment; failed exports record error_message; policy violations return 403.
**Backend:** `src/services/export_service.py`, `src/persistence/repositories/config_repo.py::create_export_job`, `src/api/routes/admin.py::create_export`, `::list_exports`, `::download_export`
**Test Coverage:** `api_tests/test_admin.py::test_create_export_audit_csv`, `::test_list_exports`, `::test_non_admin_cannot_create_export`, `unit_tests/test_export_policy_unit.py`
**Status:** Implemented (Prompt 7)

---

# Prompt 8 — Test Suite Hardening

## REQ-003: Fee-Based Service Ordering (Fixed-Price Mode) — Test Coverage Expanded
**Additional Test Coverage (P8):** `unit_tests/views/OrderListView.spec.ts` (renders list, item name, detail link, payment link, empty state), `unit_tests/views/OrderDetailView.spec.ts` (status chip, payment link, cancel button, confirm receipt)
**Status:** Test coverage expanded (Prompt 8)

## REQ-004: Bargaining Mode — Test Coverage Expanded
**Additional Test Coverage (P8):** `unit_tests/views/OrderListView.spec.ts` (bargaining link shown for bargaining-mode pending_payment, hidden for fixed), `unit_tests/views/OrderDetailView.spec.ts` (Bargaining Thread link shown when pricing_mode=bargaining)
**Status:** Test coverage expanded (Prompt 8)

## REQ-005: 30-Minute Auto-Cancel — Test Coverage Expanded
**Additional Test Coverage (P8):** `unit_tests/views/OrderDetailView.spec.ts` — CountdownTimer rendered when `auto_cancel_at` is set and status is `pending_payment`; absent for completed orders
**Status:** Test coverage expanded (Prompt 8)

## REQ-007: Attendance Exception Handling — Test Coverage Expanded
**Additional Test Coverage (P8):** `api_tests/test_queue_endpoints.py::test_pending_exceptions_reviewer_ok`, `::test_pending_exceptions_status_filter` — real HTTP-level tests for GET /queue/exceptions with status filter query param
**Status:** Test coverage expanded (Prompt 8)

## REQ-030: Staff Queue Operations — Test Coverage Upgraded to BE-API
**Previous Coverage:** Queue endpoints covered only by unit tests (filter logic in `test_refund_attendance_unit.py`)
**Upgraded Coverage (P8):** `api_tests/test_queue_endpoints.py` — 15 real no-mock HTTP tests for all 5 queue routes; verifies role gates (reviewer 200, candidate 403, admin 200), pagination envelope, status filter param, unauthenticated 401
**Status:** Test coverage upgraded to BE-API (Prompt 8)

## REQ-035: Order and Payment UI — Test Coverage Expanded
**Previous Coverage:** `BargainingView.spec.ts`, `PaymentView.spec.ts`, `order_payment_workflow.spec.ts` — did not include OrderListView or OrderDetailView
**Additional Test Coverage (P8):** `unit_tests/views/OrderListView.spec.ts` (10 tests), `unit_tests/views/OrderDetailView.spec.ts` (13 tests)
**Status:** Test coverage expanded (Prompt 8)

## REQ-039: Feature Flag Management — Admin Endpoint Coverage Confirmed
**Additional Test Coverage (P8):** `api_tests/test_admin.py::test_list_traces_returns_list`, `::test_list_access_logs_returns_list`, `::test_remove_user_from_cohort`, `::test_remove_user_from_cohort_not_member` — previously listed as covered but tests not authored; now written and confirmed
**Status:** HTTP test coverage confirmed (Prompt 8)

---

# Prompt 10 — Final Static Audit Corrections

## REQ-001: Candidate Profile Management — List Endpoint Added
**Addition (P10):** `GET /api/v1/candidates` (list all, reviewer/admin, paginated) was missing from the implementation. Added at all three layers: `candidates.py` route, `candidate_service.py::list_profiles`, `candidate_repo.py::list_paginated`. Tests added: `test_list_candidates_reviewer_ok` and `test_list_candidates_candidate_forbidden` in `api_tests/test_candidates.py`.
**Status:** Implementation completed (Prompt 10)

## Cross-Cutting: Documentation Consistency Restored
- `docs/api-spec.md` Sections 1, 3.2, and 7.1–7.11 corrected to match actual route files (30+ path errors removed)
- `repo/backend/src/config.py` `signature_required_paths` corrected to reflect actual route paths
- `repo/README.md` cert paths corrected; redundant section removed
- `repo/backend/.env.example` rewritten to cover all `Settings` fields
- `docs/questions.md` Q30 (in-process `_CHALLENGE_CACHE` constraint) and Q31 (signing informational list vs route-level Depends) added
- All REQ-001–REQ-008 and REQ-013/014/016–022 statuses updated from "Domain modeled (Prompt 2)" to their actual completed statuses with test file references
