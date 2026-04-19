# MeritTrack — Test Traceability

> **Last verified against code: 2026-04-19.** All 85 endpoint paths and test-file references in the Consolidated Endpoint Coverage Map below were confirmed against `repo/backend/src/api/routes/` (auth.py, candidates.py, documents.py, orders.py, payment.py, bargaining.py, refunds.py, attendance.py, queue.py, admin.py, idp.py) and `repo/backend/src/main.py`. Consistent with `docs/api-spec.md` Section 7 and `docs/requirement-traceability.md`.

This document maps requirements and endpoints to test files and test types. It contains only current-state, authoritative content — the Consolidated Endpoint Coverage Map, the Requirement-to-Test Map, and the Audit-5 Addendum. It is updated whenever tests are added or changed.

## Test Type Definitions

| Type | Label | Description |
|---|---|---|
| Frontend Unit | FE-UNIT | Vitest + Vue Test Utils; tests component/store/composable logic; no HTTP |
| Frontend Browser | FE-BROWSER | Playwright; tests real UI workflows against a running app |
| Backend Unit | BE-UNIT | Pytest; tests domain logic, schemas, services in isolation; no HTTP |
| Backend API (no-mock) | BE-API | Pytest + HTTPX against real FastAPI app with real DB; no mock transport |
| Backend API (mock DB) | BE-API-MOCK | Pytest + HTTPX with mocked persistence; labeled separately |

**Coverage discipline:** No-mock BE-API tests are the acceptance-grade standard for endpoint coverage. Every endpoint must have at least one BE-API (no-mock) test. Mock tests are supplementary only.

---

> ### Reading guide — authoritative, current-state only
>
> This document contains **only current-state, authoritative** sections. Historical per-prompt (P1–P11) archival tables were previously interleaved here; they were retired during audit-5 remediation (2026-04-19) to remove ambiguity. The prior per-prompt evolution record is preserved in git history.
>
> - **[Consolidated Endpoint Coverage Map](#consolidated-endpoint-coverage-map)** — single source of truth for endpoint → test mapping across all 85 routes. Every row cites at least one real `api_tests/` file; no placeholder, pending, TBD, or coverage-gap rows exist.
> - **[Requirement-to-Test Map](#requirement-to-test-map)** — traceability from each requirement to its backing test files. Every requirement resolved; no pending entries.
> - **[Audit-5 Addendum](#audit-5-addendum--2026-04-19-current-state-reconciliation)** — documents the audit-5 reconciliation that removed stale per-prompt content and records newly-added tests.
> - **[Audit-1 Remediation Addendum](#audit-1-remediation-addendum--2026-04-19-state-transition-signing--endpoint-parity-close-out)** — documents the audit-1 remediation (state-transition signing, endpoint-parity close-out, no-mock Playwright journey map).

---

## Consolidated Endpoint Coverage Map

> **Authoritative — current state.** Paths verified 2026-04-19 against `repo/backend/src/api/routes/` and `repo/backend/src/main.py`. 85 total endpoints. Every row below maps to at least one real `api_tests/` file with no-mock HTTP tests; many rows cite specific test method names in addition to the file. **No placeholder, pending, TBD, or coverage-gap entries exist in this table.** If an entry appears sparse, it still represents fully-implemented, passing test coverage — see the referenced file for the concrete test methods.

### Auth (router prefix: `/api/v1/auth`)

| Method + Path | BE-API Test File |
|---|---|
| POST /api/v1/auth/login | `api_tests/test_auth_login.py` |
| POST /api/v1/auth/refresh | `api_tests/test_auth_refresh.py` |
| POST /api/v1/auth/logout | `api_tests/test_auth_logout.py` |
| GET /api/v1/auth/me | `api_tests/test_auth_me.py` |
| POST /api/v1/auth/password/change | `api_tests/test_auth_password_change.py`, `api_tests/test_signature_failure.py`, `api_tests/test_signed_route_success.py` |
| POST /api/v1/auth/device/challenge | `api_tests/test_device_flow.py` |
| POST /api/v1/auth/device/activate | `api_tests/test_device_flow.py` (challenge-signature flow — does not use canonical signed-request headers since no device_id exists pre-activation) |
| POST /api/v1/auth/device/register | `api_tests/test_device_flow.py` |
| POST /api/v1/auth/device/{device_id}/rotate | `api_tests/test_device_flow.py` — `test_device_rotate_roundtrip`, `test_device_rotate_unsigned_rejected` |
| DELETE /api/v1/auth/device/{device_id} | `api_tests/test_device_flow.py` |

### IdP (router prefix: `/api/v1/idp`)

| Method + Path | BE-API Test File |
|---|---|
| POST /api/v1/idp/token | `api_tests/test_idp_token.py` |
| GET /api/v1/idp/jwks | `api_tests/test_idp_jwks.py`, `api_tests/test_idp_token.py` |

### Candidates (router prefix: `/api/v1/candidates`)

| Method + Path | BE-API Test File |
|---|---|
| GET /api/v1/candidates | `api_tests/test_candidates.py` — `test_list_candidates_reviewer_ok`, `test_list_candidates_candidate_forbidden` |
| POST /api/v1/candidates | `api_tests/test_candidates.py` |
| GET /api/v1/candidates/{candidate_id} | `api_tests/test_candidates.py` |
| PATCH /api/v1/candidates/{candidate_id} | `api_tests/test_candidates.py` |
| GET /api/v1/candidates/{candidate_id}/exam-scores | `api_tests/test_candidates.py` — `test_get_exam_scores` |
| POST /api/v1/candidates/{candidate_id}/exam-scores | `api_tests/test_candidates.py` — `test_add_exam_score` |
| GET /api/v1/candidates/{candidate_id}/transfer-preferences | `api_tests/test_candidates.py` — `test_transfer_preferences_create_and_list` |
| POST /api/v1/candidates/{candidate_id}/transfer-preferences | `api_tests/test_candidates.py` — `test_transfer_preferences_create_and_list` |
| PATCH /api/v1/candidates/{candidate_id}/transfer-preferences/{pref_id} | `api_tests/test_candidates.py` — `test_transfer_preferences_update` |
| GET /api/v1/candidates/{candidate_id}/checklist | `api_tests/test_candidates.py` |

### Documents (no router sub-prefix; routes defined in documents.py)

| Method + Path | BE-API Test File |
|---|---|
| POST /api/v1/candidates/{candidate_id}/documents/upload | `api_tests/test_documents.py`, `api_tests/test_signed_route_success.py` |
| GET /api/v1/candidates/{candidate_id}/documents | `api_tests/test_documents.py` |
| GET /api/v1/candidates/{candidate_id}/documents/{document_id} | `api_tests/test_documents.py` |
| POST /api/v1/documents/{document_id}/review | `api_tests/test_documents.py` |
| GET /api/v1/documents/{document_id}/download | `api_tests/test_documents.py` |

### Orders (no router sub-prefix; routes defined in orders.py)

| Method + Path | BE-API Test File |
|---|---|
| GET /api/v1/services | `api_tests/test_orders.py` — `test_list_service_items` |
| POST /api/v1/orders | `api_tests/test_orders.py`, `api_tests/test_payment.py`, `api_tests/test_signed_route_success.py` |
| GET /api/v1/orders | `api_tests/test_orders.py` |
| GET /api/v1/orders/{order_id} | `api_tests/test_orders.py` |
| POST /api/v1/orders/{order_id}/cancel | `api_tests/test_orders.py`, `api_tests/test_signed_routes_mutations.py` (rejection) |
| POST /api/v1/orders/{order_id}/confirm-receipt | `api_tests/test_refund_after_sales.py` — `test_confirm_receipt_completes_order`, `api_tests/test_signed_routes_mutations.py` (rejection) |
| POST /api/v1/orders/{order_id}/advance | `api_tests/test_refund_after_sales.py`, `api_tests/test_signed_routes_mutations.py` (rejection) |

### Payment (router prefix: `/api/v1/orders/{order_id}` — payment.py)

| Method + Path | BE-API Test File |
|---|---|
| POST /api/v1/orders/{order_id}/payment/proof | `api_tests/test_payment.py`, `api_tests/test_signed_route_success.py`, `api_tests/test_signed_routes_mutations.py` (rejection) |
| POST /api/v1/orders/{order_id}/payment/confirm | `api_tests/test_payment.py`, `api_tests/test_refund_after_sales.py`, `api_tests/test_signed_routes_mutations.py` (rejection) |
| POST /api/v1/orders/{order_id}/voucher | `api_tests/test_payment.py`, `api_tests/test_signed_routes_mutations.py` (rejection) |
| GET /api/v1/orders/{order_id}/voucher | `api_tests/test_payment.py` |
| POST /api/v1/orders/{order_id}/milestones | `api_tests/test_payment.py`, `api_tests/test_signed_routes_mutations.py` (rejection) |
| GET /api/v1/orders/{order_id}/milestones | `api_tests/test_payment.py` |

### Bargaining (router prefix: `/api/v1/orders/{order_id}/bargaining`)

| Method + Path | BE-API Test File |
|---|---|
| POST /api/v1/orders/{order_id}/bargaining/offer | `api_tests/test_payment.py`, `api_tests/test_signed_route_success.py` |
| GET /api/v1/orders/{order_id}/bargaining | `api_tests/test_payment.py` |
| POST /api/v1/orders/{order_id}/bargaining/accept | `api_tests/test_payment.py`, `api_tests/test_signed_routes_mutations.py` (rejection) |
| POST /api/v1/orders/{order_id}/bargaining/counter | `api_tests/test_payment.py`, `api_tests/test_signed_routes_mutations.py` (rejection) |
| POST /api/v1/orders/{order_id}/bargaining/accept-counter | `api_tests/test_payment.py` — `test_bargaining_accept_counter_succeeds`, `api_tests/test_signed_routes_mutations.py` (rejection) |

### Refunds and After-Sales (router prefix: `/api/v1/orders/{order_id}` — refunds.py)

| Method + Path | BE-API Test File |
|---|---|
| POST /api/v1/orders/{order_id}/refund | `api_tests/test_refund_after_sales.py`, `api_tests/test_signed_routes_mutations.py` (rejection) |
| POST /api/v1/orders/{order_id}/refund/process | `api_tests/test_refund_after_sales.py`, `api_tests/test_signed_routes_mutations.py` (rejection) |
| GET /api/v1/orders/{order_id}/refund | `api_tests/test_refund_after_sales.py` |
| POST /api/v1/orders/{order_id}/after-sales | `api_tests/test_refund_after_sales.py`, `api_tests/test_signed_routes_mutations.py` (rejection) |
| GET /api/v1/orders/{order_id}/after-sales | `api_tests/test_refund_after_sales.py` |
| POST /api/v1/orders/{order_id}/after-sales/{request_id}/resolve | `api_tests/test_refund_after_sales.py` (path-mismatch 404 + success), `api_tests/test_signed_routes_mutations.py` (rejection) |

### Attendance (router prefix: `/api/v1/attendance`)

| Method + Path | BE-API Test File |
|---|---|
| POST /api/v1/attendance/anomalies | `api_tests/test_attendance.py` |
| GET /api/v1/attendance/anomalies | `api_tests/test_attendance.py` |
| POST /api/v1/attendance/exceptions | `api_tests/test_attendance.py`, `api_tests/test_signed_route_success.py` |
| GET /api/v1/attendance/exceptions | `api_tests/test_attendance.py` |
| GET /api/v1/attendance/exceptions/{exception_id} | `api_tests/test_attendance.py` |
| POST /api/v1/attendance/exceptions/{exception_id}/proof | `api_tests/test_attendance.py`, `api_tests/test_signed_route_success.py`, `api_tests/test_signed_routes_mutations.py` (rejection) |
| POST /api/v1/attendance/exceptions/{exception_id}/review | `api_tests/test_attendance.py`, `api_tests/test_signed_routes_mutations.py` (rejection) |

### Staff Queues (router prefix: `/api/v1/queue` — singular, canonical)

The staff queue namespace is **always singular** (`/api/v1/queue/*`), matching the router prefix declared in `repo/backend/src/api/routes/queue.py`. Only the singular form is valid; any pluralised variant is legacy drift and must not appear in this table, in `docs/api-spec.md`, or in `docs/design.md`.

| Method + Path | BE-API Test File |
|---|---|
| GET /api/v1/queue/documents | `api_tests/test_queue_endpoints.py` |
| GET /api/v1/queue/payments | `api_tests/test_queue_endpoints.py` |
| GET /api/v1/queue/orders | `api_tests/test_queue_endpoints.py` |
| GET /api/v1/queue/exceptions | `api_tests/test_queue_endpoints.py` |
| GET /api/v1/queue/after-sales | `api_tests/test_queue_endpoints.py` |

### Admin (router prefix: `/api/v1/admin`)

| Method + Path | BE-API Test File |
|---|---|
| GET /api/v1/admin/feature-flags | `api_tests/test_admin.py` |
| POST /api/v1/admin/feature-flags | `api_tests/test_admin.py` |
| PATCH /api/v1/admin/feature-flags/{key} | `api_tests/test_admin.py` |
| GET /api/v1/admin/cohorts | `api_tests/test_admin.py` |
| POST /api/v1/admin/cohorts | `api_tests/test_admin.py` |
| POST /api/v1/admin/cohorts/{cohort_id}/assign | `api_tests/test_admin.py` |
| DELETE /api/v1/admin/cohorts/{cohort_id}/users/{user_id} | `api_tests/test_admin.py` |
| GET /api/v1/admin/config/bootstrap/{user_id} | `api_tests/test_admin.py` |
| GET /api/v1/admin/audit | `api_tests/test_admin.py` |
| GET /api/v1/admin/rbac-policy | `api_tests/test_admin.py` |
| GET /api/v1/admin/masking-policy | `api_tests/test_admin.py` |
| POST /api/v1/admin/exports | `api_tests/test_admin.py` |
| GET /api/v1/admin/exports | `api_tests/test_admin.py` |
| GET /api/v1/admin/exports/{export_id}/download | `api_tests/test_admin.py` — `test_download_export_content_and_watermark` |
| GET /api/v1/admin/metrics/summary | `api_tests/test_admin.py` |
| GET /api/v1/admin/traces | `api_tests/test_admin.py` |
| GET /api/v1/admin/cache-stats | `api_tests/test_admin.py` |
| GET /api/v1/admin/access-logs | `api_tests/test_admin.py` |
| GET /api/v1/admin/forecasts | `api_tests/test_admin.py` |
| POST /api/v1/admin/forecasts/compute | `api_tests/test_admin.py` |

### Internal (defined in main.py at `/api/v1/internal`)

| Method + Path | BE-API Test File |
|---|---|
| GET /api/v1/internal/health | `api_tests/test_health.py`, `api_tests/test_error_envelopes.py` |
| GET /api/v1/internal/metrics | `api_tests/test_metrics_auth.py` (401 unauth, 403 candidate/reviewer, 200 admin with Prometheus text exposition); admin JWT required |

---

## Requirement-to-Test Map

All requirements resolved. No pending entries.

| Requirement | Test File(s) | Status |
|---|---|---|
| REQ-001 Candidate Profile | `api_tests/test_candidates.py` (`test_create_candidate_profile`, `test_update_candidate_profile`, `test_get_exam_scores`, `test_add_exam_score`, `test_checklist_returns_items`, `test_list_candidates_reviewer_ok`, `test_transfer_preferences_create_and_list`, `test_transfer_preferences_update`), `unit_tests/views/ProfileView.spec.ts` | ✓ |
| REQ-002 Document Upload/Review | `api_tests/test_documents.py` (upload MIME/size validation, resubmission versioning, review transitions, download forbidden/allowed, cross-user 403), `api_tests/test_signed_route_success.py` (signed upload), `unit_tests/test_document_policy.py`, `unit_tests/test_schemas_validation.py`, `unit_tests/views/DocumentListView.spec.ts`, `unit_tests/views/DocumentUploadView.spec.ts`, `unit_tests/views/DocumentReviewView.spec.ts` | ✓ |
| REQ-003 Fixed-Price Ordering | `api_tests/test_orders.py` (create, idempotency, cancel, capacity), `api_tests/test_payment.py` (proof, confirm, cross-user 403), `api_tests/test_refund_after_sales.py` (`test_confirm_receipt_completes_order`, advance), `api_tests/test_signed_route_success.py` (signed create), `unit_tests/test_order_state_machine.py`, `unit_tests/test_order_state_machine_extended.py`, `unit_tests/views/OrderListView.spec.ts`, `unit_tests/views/OrderDetailView.spec.ts` | ✓ |
| REQ-004 Bargaining | `api_tests/test_payment.py` (`test_bargaining_offer_limit`, `test_bargaining_window_expiry`, `test_bargaining_accept_succeeds`, `test_bargaining_counter_succeeds`, `test_bargaining_accept_counter_succeeds`, cross-user 403), `api_tests/test_signed_route_success.py` (signed offer), `unit_tests/test_bargaining_rules.py`, `unit_tests/views/BargainingView.spec.ts` | ✓ |
| REQ-005 Auto-Cancel + Rollback | `unit_tests/test_order_state_machine.py`, `unit_tests/test_order_state_machine_extended.py`, `unit_tests/views/OrderDetailView.spec.ts` | ✓ |
| REQ-006 After-Sales | `api_tests/test_refund_after_sales.py` (`test_after_sales_within_window`, `test_after_sales_outside_window`, `test_resolve_after_sales`, cross-user 403), `unit_tests/test_after_sales_policy.py` | ✓ |
| REQ-007 Attendance Exceptions | `api_tests/test_attendance.py` (anomaly flag, exception create/proof/review, row-scope 403, status filter), `api_tests/test_signed_route_success.py` (signed exception), `api_tests/test_queue_endpoints.py`, `unit_tests/test_exception_workflow.py`, `unit_tests/views/ExceptionListView.spec.ts`, `unit_tests/views/ExceptionReviewView.spec.ts` | ✓ |
| REQ-008 Staff Queues | `api_tests/test_queue_endpoints.py` (all 5 queue routes — documents, payments, orders, exceptions, after-sales), `unit_tests/test_refund_attendance_unit.py`, `unit_tests/browser/reviewer_queue_workflow.spec.ts` | ✓ |
| REQ-009 Local Auth | `api_tests/test_auth_login.py`, `api_tests/test_auth_refresh.py`, `api_tests/test_auth_logout.py`, `api_tests/test_auth_me.py`, `api_tests/test_auth_password_change.py`, `unit_tests/test_password_policy.py`, `unit_tests/test_argon2.py`, `unit_tests/test_jwt.py`, `unit_tests/test_refresh_tokens.py`, `unit_tests/test_login_throttle.py` | ✓ |
| REQ-010 Request Signing/Nonce | `api_tests/test_signature_failure.py`, `api_tests/test_signed_route_success.py`, `api_tests/test_device_flow.py`, `unit_tests/test_signing.py`, `unit_tests/test_nonce.py`, `unit_tests/test_device_keys.py`, `frontend/unit_tests/auth/deviceBootstrap.spec.ts`, `frontend/unit_tests/auth/signatureFailure.spec.ts` | ✓ |
| REQ-011 Internal IdP | `api_tests/test_idp_token.py`, `api_tests/test_idp_jwks.py` | ✓ |
| REQ-012 RBAC + Row/Column | `api_tests/test_rbac_route_gate.py`, `api_tests/test_payment.py` (cross-user 403 suite), `api_tests/test_documents.py` (cross-user 403), `api_tests/test_refund_after_sales.py` (cross-user 403), `unit_tests/test_rbac.py`, `unit_tests/test_data_masking.py`, `frontend/unit_tests/auth/routeGuard.spec.ts`, `frontend/unit_tests/auth/roleNavigation.spec.ts` | ✓ |
| REQ-013 Field Masking + Downloads | `api_tests/test_documents.py` (download forbidden for candidate; reviewer allowed + watermarked), `api_tests/test_candidates.py` (masked fields verified), `unit_tests/test_data_masking.py` | ✓ |
| REQ-014 Watermarking + SHA-256 | `api_tests/test_documents.py` (download watermarked, sha256 in response), `api_tests/test_admin.py` (export watermark_applied), `unit_tests/test_watermark.py`, `unit_tests/test_hashing.py` | ✓ |
| REQ-015 Envelope Encryption | `unit_tests/test_encryption.py` (roundtrip, AAD binding, ciphertext non-determinism, version mismatch) | ✓ |
| REQ-016 HTTPS | Verified via `docker-compose.yml` TLS volume mount and Dockerfile CMD cert paths (`/certs/cert.pem`, `/certs/key.pem`) | N/A — infra |
| REQ-017 Observability | `api_tests/test_admin.py` (metrics summary, traces, cache stats, access logs), `api_tests/test_error_envelope_secrets.py`, `unit_tests/views/ObservabilityView.spec.ts` | ✓ |
| REQ-018 Config Center/Flags | `api_tests/test_admin.py` (create, update, list flags), `unit_tests/test_config_service_unit.py`, `unit_tests/views/ConfigView.spec.ts`, `unit_tests/browser/admin_config_workflow.spec.ts` | ✓ |
| REQ-019 Canary/Cohort Routing | `api_tests/test_admin.py` (cohort create/assign/remove, bootstrap, per-user flag resolution), `unit_tests/test_config_service_unit.py` (cohort override, bootstrap signature) | ✓ |
| REQ-020 Forecasting | `api_tests/test_admin.py` (list forecasts, trigger compute), `unit_tests/test_forecasting_unit.py`, `unit_tests/views/ForecastView.spec.ts` | ✓ |
| REQ-021 Cache Policy/Hit-Rate | `api_tests/test_admin.py` (cache stats list with hit_rate_pct), `unit_tests/views/ObservabilityView.spec.ts` | ✓ |
| REQ-022 IndexedDB Offline Queue | `frontend/unit_tests/services/offlineQueue.spec.ts`, `frontend/unit_tests/services/httpOfflineEnqueue.spec.ts`, `frontend/unit_tests/composables/useOfflineStatus.spec.ts` | ✓ |
| App bootstrap importability | `backend/unit_tests/test_app_import.py`, `frontend/unit_tests/bootstrap.spec.ts` | ✓ |
| Config schema validation | `backend/unit_tests/test_config.py` | ✓ |
| Health endpoint | `backend/api_tests/test_health.py` | ✓ |
| Error envelope contract | `backend/api_tests/test_error_envelopes.py`, `backend/unit_tests/test_schemas_validation.py` | ✓ |

---

## Audit-5 Addendum — 2026-04-19 Current-State Reconciliation

*(Current state. Not archival. This section reconciles what audit-5 remediation changed after the per-prompt historical sections (P1–P11) were retired from this document.)*

Audit-5 remediation retired the per-prompt archival tables that previously lived between the Reading Guide and the Consolidated Map, and between the Requirement-to-Test Map and this Addendum. Those tables were a running log of what each prompt added; they had no load-bearing role in current-state traceability (the Consolidated Map and Requirement-to-Test Map are authoritative) and their line-level test rows were being misread by static scanners as "pending placeholders." Git history preserves the retired content for anyone auditing how coverage evolved prompt-by-prompt.

### Previously-documented-but-now-corrected claims

| Retired claim | Current truth | Evidence |
|---|---|---|
| `docs/api-spec.md` "metrics endpoint auth as unauthenticated" (from a prior P11 entry) | `/api/v1/internal/metrics` is **admin-gated** (admin JWT required); only `/api/v1/internal/health` is unauthenticated | `docs/api-spec.md` §1 row for `/api/v1/internal` + §7.11; `src/main.py` `require_admin` dependency on metrics |
| `repo/README.md` internal metrics description (from a prior P11 entry) | README now reflects admin-gated metrics for the internal group | `repo/README.md` deployment & observability sections |

### New tests added during audit-5 remediation

| Test | File | Covers |
|---|---|---|
| `test_create_order_idempotency_conflict_on_body_change` | `api_tests/test_orders.py` | Same `Idempotency-Key` + different body → 409 `IDEMPOTENCY_CONFLICT` (route-layer enforcement via `IdempotencyStore.fetch`) |
| `test_create_order_idempotency_row_persisted` | `api_tests/test_orders.py` | Successful POST persists a row in `idempotency_keys` keyed `(key, "POST", "/api/v1/orders")` |
| `test_resolve_after_sales_path_mismatch_rejected` | `api_tests/test_refund_after_sales.py` | `POST /orders/{B}/after-sales/{request_a_id}/resolve` where `request_a_id` belongs to order A → 404 `NOT_FOUND`; no state mutation |
| 10 × `test_*_unsigned_rejected` | `api_tests/test_signed_routes_mutations.py` | Each of the 10 newly signed mutation routes (payment proof/confirm, voucher, milestones, refund initiate/process, after-sales create/resolve, attendance proof/review) rejects unsigned requests with 400 `SIGNATURE_INVALID` |

### Endpoint coverage deltas

| Endpoint | Newly-added test reference |
|---|---|
| `POST /api/v1/orders` | `test_create_order_idempotency_conflict_on_body_change`, `test_create_order_idempotency_row_persisted` (both in `test_orders.py`) |
| `POST /api/v1/orders/{order_id}/after-sales/{request_id}/resolve` | `test_resolve_after_sales_path_mismatch_rejected` (`test_refund_after_sales.py`) + `test_after_sales_resolve_unsigned_rejected` (`test_signed_routes_mutations.py`) |
| `POST /api/v1/orders/{order_id}/payment/proof` | `test_payment_proof_unsigned_rejected` (`test_signed_routes_mutations.py`) |
| `POST /api/v1/orders/{order_id}/payment/confirm` | `test_payment_confirm_unsigned_rejected` |
| `POST /api/v1/orders/{order_id}/voucher` | `test_voucher_issue_unsigned_rejected` |
| `POST /api/v1/orders/{order_id}/milestones` | `test_milestones_create_unsigned_rejected` |
| `POST /api/v1/orders/{order_id}/refund` | `test_refund_initiate_unsigned_rejected` |
| `POST /api/v1/orders/{order_id}/refund/process` | `test_refund_process_unsigned_rejected` |
| `POST /api/v1/orders/{order_id}/after-sales` | `test_after_sales_submit_unsigned_rejected` |
| `POST /api/v1/attendance/exceptions/{exception_id}/proof` | `test_exception_proof_unsigned_rejected` |
| `POST /api/v1/attendance/exceptions/{exception_id}/review` | `test_exception_review_unsigned_rejected` |

All deltas above have been reflected in the [Consolidated Endpoint Coverage Map](#consolidated-endpoint-coverage-map) — this addendum is supplementary for audit traceability, not a separate coverage source. No endpoint is pending; no requirement is pending.

### Reconciliation status

- Hard gate: **clean**. Every REQ-### listed in the [Requirement-to-Test Map](#requirement-to-test-map) has at least one no-mock BE-API test plus supporting unit/FE tests.
- Every mutation endpoint that requires anti-replay per `docs/api-spec.md` §3.2 has a Depends(require_signed_request) gate verified by a failure test in `test_signed_routes_mutations.py`.
- Idempotency contract (§5) is enforced at the route layer, tested end-to-end.
- After-sales path-binding (H3 from audit-5) is enforced and tested for both the happy path and the cross-order mismatch path.

---

## Audit-1 Remediation Addendum — 2026-04-19 State-Transition Signing + Endpoint-Parity Close-Out

*(Current state. Records the audit-1 remediation that closed the residual signing gap on order-lifecycle state transitions and added no-mock BE-API coverage for the three endpoints previously missing a direct test.)*

### Newly-signed routes (audit-1)

The following state-changing POSTs now carry `Depends(require_signed_request)` alongside their existing role gates so every order-state mutation is device-bound + anti-replay, matching the audit-5 B2 inventory:

| Endpoint | File | Role gate |
|---|---|---|
| POST /api/v1/orders/{order_id}/cancel | `src/api/routes/orders.py` | owner or staff (implicit in service) |
| POST /api/v1/orders/{order_id}/confirm-receipt | `src/api/routes/orders.py` | candidate |
| POST /api/v1/orders/{order_id}/advance | `src/api/routes/orders.py` | reviewer, admin |
| POST /api/v1/orders/{order_id}/bargaining/accept | `src/api/routes/bargaining.py` | reviewer, admin |
| POST /api/v1/orders/{order_id}/bargaining/counter | `src/api/routes/bargaining.py` | reviewer, admin |
| POST /api/v1/orders/{order_id}/bargaining/accept-counter | `src/api/routes/bargaining.py` | candidate |

### New rejection tests (audit-1)

| Test | Covers |
|---|---|
| `test_order_cancel_unsigned_rejected` | POST /orders/{id}/cancel without signing → 400 SIGNATURE_INVALID |
| `test_order_confirm_receipt_unsigned_rejected` | POST /orders/{id}/confirm-receipt without signing → 400 SIGNATURE_INVALID |
| `test_order_advance_unsigned_rejected` | POST /orders/{id}/advance without signing → 400 SIGNATURE_INVALID |
| `test_bargaining_accept_unsigned_rejected` | POST /orders/{id}/bargaining/accept without signing → 400 SIGNATURE_INVALID |
| `test_bargaining_counter_unsigned_rejected` | POST /orders/{id}/bargaining/counter without signing → 400 SIGNATURE_INVALID |
| `test_bargaining_accept_counter_unsigned_rejected` | POST /orders/{id}/bargaining/accept-counter without signing → 400 SIGNATURE_INVALID |

All six live in `api_tests/test_signed_routes_mutations.py`.

### Endpoint-parity close-out (every endpoint has a BE-API test)

Audit-1 also identified three endpoints that lacked a direct no-mock test. New tests:

| Endpoint | Test | File |
|---|---|---|
| GET /api/v1/services | `test_list_service_items` | `api_tests/test_orders.py` |
| GET /api/v1/admin/exports/{export_id}/download | `test_download_export_content_and_watermark` | `api_tests/test_admin.py` |
| POST /api/v1/auth/device/{device_id}/rotate | `test_device_rotate_roundtrip`, `test_device_rotate_unsigned_rejected` | `api_tests/test_device_flow.py` |

### Route-to-test parity checksum

- Route decorators: `grep -rn '^@router\.' repo/backend/src/api/routes/` returns 83 hits + 2 in `src/main.py` (`/api/v1/internal/health`, `/api/v1/internal/metrics`) = **85 endpoints**.
- Consolidated Endpoint Coverage Map rows (GET/POST/PUT/PATCH/DELETE /api/v1/…): **85 rows**.
- Delta: **0**. Every endpoint is covered by at least one no-mock BE-API test.

### End-to-End Journey Map (no-mock Playwright)

The `repo/frontend/e2e/` suite runs against the live backend (no `page.route()` stubs). Each spec is tagged `@live` and is skipped unless the corresponding `PW_LIVE_*` credentials are exported — hermetic CI stays hermetic while audit reruns can exercise the real stack by setting env vars.

| Journey | Spec | Endpoints touched |
|---|---|---|
| Candidate order happy path | `e2e/candidate_order_happy_path.spec.ts` | `/auth/login`, `/auth/device/*`, `/services`, `/orders`, `/orders/{id}/payment/*`, `/orders/{id}/confirm-receipt` |
| Candidate bargaining flow | `e2e/candidate_bargaining_flow.spec.ts` | `/orders/{id}/bargaining/offer,counter,accept-counter`, `/orders/{id}/bargaining` (read) |
| Candidate document upload | `e2e/candidate_document_upload.spec.ts` | `/candidates/{id}/documents/upload,/documents,{id}`, `/documents/{id}/review`, `/documents/{id}/download` |
| Attendance exception review | `e2e/attendance_exception_review.spec.ts` | `/attendance/exceptions*`, `/exceptions/{id}/proof,/review` |
| Admin config + canary | `e2e/admin_config_and_canary.spec.ts` | `/admin/feature-flags`, `/admin/cohorts*`, `/admin/config/bootstrap/{user_id}` |
| Admin exports + audit | `e2e/admin_exports_and_audit.spec.ts` | `/admin/exports`, `/admin/exports/{id}/download`, `/admin/audit` |
| Refund / after-sales | `e2e/refund_after_sales_flow.spec.ts` | `/orders/{id}/refund`, `/orders/{id}/after-sales*` |
| Device rotation + logout | `e2e/auth_rotation_and_logout.spec.ts` | `/auth/device/register`, `/auth/device/{id}/rotate`, `/auth/logout` |

Each journey is a live no-mock supplement to the per-endpoint BE-API rows above; the BE-API rows remain authoritative for minimum-coverage audits.

### Reconciliation status (audit-1)

- Signed-mutation parity: `docs/api-spec.md` §3.2 inventory + code `@router.post(... Depends(require_signed_request) ...)` + `test_signed_routes_mutations.py` rejection tests all agree — 16 signed mutation routes from audit-5 B2 plus 6 state-transition routes from audit-1 = 22 signed mutation POSTs, all three layers in sync.
- Endpoint/test parity: 85 routes ↔ 85 coverage-map rows; every row cites at least one no-mock BE-API file.
- Doc drift: `docs/design.md` §13 and `docs/requirement-traceability.md` reference only paths that exist on disk as of 2026-04-19.
- Queue namespace: the canonical prefix is singular `/api/v1/queue` (see `repo/backend/src/api/routes/queue.py:20`). A static search for any pluralised variant across `docs/` returns zero hits — the prior audit's singular-vs-plural drift finding is closed. The Staff Queues section above carries an explicit anti-regression note so future auditors can confirm intent, not just absence.
