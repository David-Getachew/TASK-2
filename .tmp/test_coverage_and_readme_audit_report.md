# Test Coverage Audit

## Project Type Detection
- README top describes the system as "A full-stack offline-ready platform" in repo/README.md:3.
- Required exact label set (backend/fullstack/web/android/ios/desktop) is not explicitly declared as a strict token at top.
- Inferred project type (strict mode): fullstack.

## Backend Endpoint Inventory
Resolved from FastAPI route wiring in repo/backend/src/api/routes/__init__.py and repo/backend/src/main.py.

| # | Endpoint (METHOD PATH) | Source |
|---|---|---|
| 1 | GET /api/v1/internal/health | repo/backend/src/main.py (health) |
| 2 | GET /api/v1/internal/metrics | repo/backend/src/main.py (metrics_endpoint) |
| 3 | POST /api/v1/auth/login | repo/backend/src/api/routes/auth.py (login) |
| 4 | POST /api/v1/auth/refresh | repo/backend/src/api/routes/auth.py (refresh) |
| 5 | POST /api/v1/auth/logout | repo/backend/src/api/routes/auth.py (logout) |
| 6 | GET /api/v1/auth/me | repo/backend/src/api/routes/auth.py (me) |
| 7 | POST /api/v1/auth/password/change | repo/backend/src/api/routes/auth.py (change_password) |
| 8 | POST /api/v1/auth/device/challenge | repo/backend/src/api/routes/auth.py (device_challenge) |
| 9 | POST /api/v1/auth/device/activate | repo/backend/src/api/routes/auth.py (device_activate) |
| 10 | POST /api/v1/auth/device/register | repo/backend/src/api/routes/auth.py (device_register) |
| 11 | POST /api/v1/auth/device/{device_id}/rotate | repo/backend/src/api/routes/auth.py (device_rotate) |
| 12 | DELETE /api/v1/auth/device/{device_id} | repo/backend/src/api/routes/auth.py (device_revoke) |
| 13 | POST /api/v1/idp/token | repo/backend/src/api/routes/idp.py (issue_token) |
| 14 | GET /api/v1/idp/jwks | repo/backend/src/api/routes/idp.py (jwks) |
| 15 | GET /api/v1/candidates | repo/backend/src/api/routes/candidates.py (list_candidate_profiles) |
| 16 | POST /api/v1/candidates | repo/backend/src/api/routes/candidates.py (create_candidate_profile) |
| 17 | GET /api/v1/candidates/{candidate_id} | repo/backend/src/api/routes/candidates.py (get_candidate_profile) |
| 18 | PATCH /api/v1/candidates/{candidate_id} | repo/backend/src/api/routes/candidates.py (update_candidate_profile) |
| 19 | GET /api/v1/candidates/{candidate_id}/exam-scores | repo/backend/src/api/routes/candidates.py (list_exam_scores) |
| 20 | POST /api/v1/candidates/{candidate_id}/exam-scores | repo/backend/src/api/routes/candidates.py (add_exam_score) |
| 21 | GET /api/v1/candidates/{candidate_id}/transfer-preferences | repo/backend/src/api/routes/candidates.py (list_transfer_preferences) |
| 22 | POST /api/v1/candidates/{candidate_id}/transfer-preferences | repo/backend/src/api/routes/candidates.py (add_transfer_preference) |
| 23 | PATCH /api/v1/candidates/{candidate_id}/transfer-preferences/{pref_id} | repo/backend/src/api/routes/candidates.py (update_transfer_preference) |
| 24 | GET /api/v1/candidates/{candidate_id}/checklist | repo/backend/src/api/routes/candidates.py (get_checklist) |
| 25 | POST /api/v1/candidates/{candidate_id}/documents/upload | repo/backend/src/api/routes/documents.py (upload_document) |
| 26 | GET /api/v1/candidates/{candidate_id}/documents | repo/backend/src/api/routes/documents.py (list_documents) |
| 27 | GET /api/v1/candidates/{candidate_id}/documents/{document_id} | repo/backend/src/api/routes/documents.py (get_document) |
| 28 | POST /api/v1/documents/{document_id}/review | repo/backend/src/api/routes/documents.py (review_document) |
| 29 | GET /api/v1/documents/{document_id}/download | repo/backend/src/api/routes/documents.py (download_document) |
| 30 | GET /api/v1/services | repo/backend/src/api/routes/orders.py (list_service_items) |
| 31 | POST /api/v1/orders | repo/backend/src/api/routes/orders.py (create_order) |
| 32 | GET /api/v1/orders | repo/backend/src/api/routes/orders.py (list_orders) |
| 33 | GET /api/v1/orders/{order_id} | repo/backend/src/api/routes/orders.py (get_order) |
| 34 | POST /api/v1/orders/{order_id}/cancel | repo/backend/src/api/routes/orders.py (cancel_order) |
| 35 | POST /api/v1/orders/{order_id}/confirm-receipt | repo/backend/src/api/routes/orders.py (confirm_receipt) |
| 36 | POST /api/v1/orders/{order_id}/advance | repo/backend/src/api/routes/orders.py (advance_order) |
| 37 | POST /api/v1/orders/{order_id}/payment/proof | repo/backend/src/api/routes/payment.py (submit_payment_proof) |
| 38 | POST /api/v1/orders/{order_id}/payment/confirm | repo/backend/src/api/routes/payment.py (confirm_payment) |
| 39 | POST /api/v1/orders/{order_id}/voucher | repo/backend/src/api/routes/payment.py (issue_voucher) |
| 40 | GET /api/v1/orders/{order_id}/voucher | repo/backend/src/api/routes/payment.py (get_voucher) |
| 41 | POST /api/v1/orders/{order_id}/milestones | repo/backend/src/api/routes/payment.py (add_milestone) |
| 42 | GET /api/v1/orders/{order_id}/milestones | repo/backend/src/api/routes/payment.py (list_milestones) |
| 43 | POST /api/v1/orders/{order_id}/bargaining/offer | repo/backend/src/api/routes/bargaining.py (submit_offer) |
| 44 | GET /api/v1/orders/{order_id}/bargaining | repo/backend/src/api/routes/bargaining.py (get_bargaining_thread) |
| 45 | POST /api/v1/orders/{order_id}/bargaining/accept | repo/backend/src/api/routes/bargaining.py (accept_offer) |
| 46 | POST /api/v1/orders/{order_id}/bargaining/counter | repo/backend/src/api/routes/bargaining.py (counter_offer) |
| 47 | POST /api/v1/orders/{order_id}/bargaining/accept-counter | repo/backend/src/api/routes/bargaining.py (accept_counter) |
| 48 | POST /api/v1/orders/{order_id}/refund | repo/backend/src/api/routes/refunds.py (initiate_refund) |
| 49 | POST /api/v1/orders/{order_id}/refund/process | repo/backend/src/api/routes/refunds.py (process_refund) |
| 50 | GET /api/v1/orders/{order_id}/refund | repo/backend/src/api/routes/refunds.py (get_refund) |
| 51 | POST /api/v1/orders/{order_id}/after-sales | repo/backend/src/api/routes/refunds.py (submit_after_sales) |
| 52 | GET /api/v1/orders/{order_id}/after-sales | repo/backend/src/api/routes/refunds.py (list_after_sales) |
| 53 | POST /api/v1/orders/{order_id}/after-sales/{request_id}/resolve | repo/backend/src/api/routes/refunds.py (resolve_after_sales) |
| 54 | GET /api/v1/queue/documents | repo/backend/src/api/routes/queue.py (pending_documents) |
| 55 | GET /api/v1/queue/payments | repo/backend/src/api/routes/queue.py (pending_payments) |
| 56 | GET /api/v1/queue/orders | repo/backend/src/api/routes/queue.py (pending_orders) |
| 57 | GET /api/v1/queue/exceptions | repo/backend/src/api/routes/queue.py (pending_exceptions) |
| 58 | GET /api/v1/queue/after-sales | repo/backend/src/api/routes/queue.py (pending_after_sales) |
| 59 | POST /api/v1/attendance/anomalies | repo/backend/src/api/routes/attendance.py (flag_anomaly) |
| 60 | GET /api/v1/attendance/anomalies | repo/backend/src/api/routes/attendance.py (list_anomalies) |
| 61 | POST /api/v1/attendance/exceptions | repo/backend/src/api/routes/attendance.py (create_exception) |
| 62 | GET /api/v1/attendance/exceptions | repo/backend/src/api/routes/attendance.py (list_exceptions) |
| 63 | GET /api/v1/attendance/exceptions/{exception_id} | repo/backend/src/api/routes/attendance.py (get_exception) |
| 64 | POST /api/v1/attendance/exceptions/{exception_id}/proof | repo/backend/src/api/routes/attendance.py (upload_proof) |
| 65 | POST /api/v1/attendance/exceptions/{exception_id}/review | repo/backend/src/api/routes/attendance.py (submit_exception_review) |
| 66 | GET /api/v1/admin/feature-flags | repo/backend/src/api/routes/admin.py (list_feature_flags) |
| 67 | POST /api/v1/admin/feature-flags | repo/backend/src/api/routes/admin.py (create_feature_flag) |
| 68 | PATCH /api/v1/admin/feature-flags/{key} | repo/backend/src/api/routes/admin.py (update_feature_flag) |
| 69 | GET /api/v1/admin/cohorts | repo/backend/src/api/routes/admin.py (list_cohorts) |
| 70 | POST /api/v1/admin/cohorts | repo/backend/src/api/routes/admin.py (create_cohort) |
| 71 | POST /api/v1/admin/cohorts/{cohort_id}/assign | repo/backend/src/api/routes/admin.py (assign_user_to_cohort) |
| 72 | DELETE /api/v1/admin/cohorts/{cohort_id}/users/{user_id} | repo/backend/src/api/routes/admin.py (remove_user_from_cohort) |
| 73 | GET /api/v1/admin/config/bootstrap/{user_id} | repo/backend/src/api/routes/admin.py (get_bootstrap_config) |
| 74 | GET /api/v1/admin/audit | repo/backend/src/api/routes/admin.py (search_audit) |
| 75 | GET /api/v1/admin/rbac-policy | repo/backend/src/api/routes/admin.py (get_rbac_policy) |
| 76 | GET /api/v1/admin/masking-policy | repo/backend/src/api/routes/admin.py (get_masking_policy) |
| 77 | POST /api/v1/admin/exports | repo/backend/src/api/routes/admin.py (create_export) |
| 78 | GET /api/v1/admin/exports | repo/backend/src/api/routes/admin.py (list_exports) |
| 79 | GET /api/v1/admin/exports/{export_id}/download | repo/backend/src/api/routes/admin.py (download_export) |
| 80 | GET /api/v1/admin/metrics/summary | repo/backend/src/api/routes/admin.py (get_metrics_summary) |
| 81 | GET /api/v1/admin/traces | repo/backend/src/api/routes/admin.py (list_traces) |
| 82 | GET /api/v1/admin/cache-stats | repo/backend/src/api/routes/admin.py (get_cache_stats) |
| 83 | GET /api/v1/admin/access-logs | repo/backend/src/api/routes/admin.py (get_access_log_summaries) |
| 84 | GET /api/v1/admin/forecasts | repo/backend/src/api/routes/admin.py (list_forecasts) |
| 85 | POST /api/v1/admin/forecasts/compute | repo/backend/src/api/routes/admin.py (trigger_forecast) |

## API Test Mapping Table
Coverage criterion: exact METHOD + PATH request call to routed handler.

| Endpoint | Covered | Test Type | Test Files | Evidence |
|---|---|---|---|---|
| GET /api/v1/internal/health | yes | true no-mock HTTP | test_health.py | test_health_ok: client.get('/api/v1/internal/health') |
| GET /api/v1/internal/metrics | yes | true no-mock HTTP | test_metrics_auth.py | test_metrics_admin_ok: client.get('/api/v1/internal/metrics') |
| POST /api/v1/auth/login | yes | true no-mock HTTP | test_auth_login.py | test_login_happy_path: client.post('/api/v1/auth/login') |
| POST /api/v1/auth/refresh | yes | true no-mock HTTP | test_auth_refresh.py | test_refresh_ok: client.post('/api/v1/auth/refresh') |
| POST /api/v1/auth/logout | yes | true no-mock HTTP | test_auth_logout.py | test_logout_ok: client.post('/api/v1/auth/logout') |
| GET /api/v1/auth/me | yes | true no-mock HTTP | test_auth_me.py | test_me_ok: client.get('/api/v1/auth/me') |
| POST /api/v1/auth/password/change | yes | true no-mock HTTP | test_auth_password_change.py | test_change_password_happy_path |
| POST /api/v1/auth/device/challenge | yes | true no-mock HTTP | test_device_flow.py | test_device_enrollment_challenge |
| POST /api/v1/auth/device/activate | yes | true no-mock HTTP | test_device_flow.py | test_device_activate |
| POST /api/v1/auth/device/register | yes | true no-mock HTTP | test_device_flow.py | test_register_direct |
| POST /api/v1/auth/device/{device_id}/rotate | yes | true no-mock HTTP | test_device_flow.py | test_device_rotate (path f'/api/v1/auth/device/{device_id}/rotate') |
| DELETE /api/v1/auth/device/{device_id} | yes | true no-mock HTTP | test_device_flow.py | test_revoke |
| POST /api/v1/idp/token | yes | true no-mock HTTP | test_idp_token.py | test_valid_client_issues_verifiable_token |
| GET /api/v1/idp/jwks | yes | true no-mock HTTP | test_idp_jwks.py, test_idp_token.py | test_jwks_is_well_formed |
| GET /api/v1/candidates | yes | true no-mock HTTP | test_candidates.py | test_list_candidates_reviewer_sees_all |
| POST /api/v1/candidates | yes | true no-mock HTTP | test_candidates.py | test_create_ok |
| GET /api/v1/candidates/{candidate_id} | yes | true no-mock HTTP | test_candidates.py | test_get_ok |
| PATCH /api/v1/candidates/{candidate_id} | yes | true no-mock HTTP | test_candidates.py | test_patch_profile |
| GET /api/v1/candidates/{candidate_id}/exam-scores | yes | true no-mock HTTP | test_candidates.py | test_list_exam_scores |
| POST /api/v1/candidates/{candidate_id}/exam-scores | yes | true no-mock HTTP | test_candidates.py | test_add_exam_score |
| GET /api/v1/candidates/{candidate_id}/transfer-preferences | yes | true no-mock HTTP | test_candidates.py | test_list_transfer_preferences |
| POST /api/v1/candidates/{candidate_id}/transfer-preferences | yes | true no-mock HTTP | test_candidates.py | test_add_transfer_preference |
| PATCH /api/v1/candidates/{candidate_id}/transfer-preferences/{pref_id} | yes | true no-mock HTTP | test_candidates.py | test_patch_transfer_preference |
| GET /api/v1/candidates/{candidate_id}/checklist | yes | true no-mock HTTP | test_candidates.py | test_get_checklist |
| POST /api/v1/candidates/{candidate_id}/documents/upload | yes | true no-mock HTTP | test_documents.py | test_upload_ok |
| GET /api/v1/candidates/{candidate_id}/documents | yes | true no-mock HTTP | test_documents.py | test_list_my_documents |
| GET /api/v1/candidates/{candidate_id}/documents/{document_id} | yes | true no-mock HTTP | test_documents.py | test_get_ok |
| POST /api/v1/documents/{document_id}/review | yes | true no-mock HTTP | test_documents.py | test_review_happy_path |
| GET /api/v1/documents/{document_id}/download | yes | true no-mock HTTP | test_documents.py | test_download_ok |
| GET /api/v1/services | yes | true no-mock HTTP | test_orders.py | test_list_service_items |
| POST /api/v1/orders | yes | true no-mock HTTP | test_orders.py, test_signed_route_success.py | test_create_order_fixed_price |
| GET /api/v1/orders | no | none | none | No direct client.get('/api/v1/orders') request found in repo/backend/api_tests/*.py |
| GET /api/v1/orders/{order_id} | yes | true no-mock HTTP | test_orders.py, test_payment.py, test_refund_after_sales.py | test_order_row_scope |
| POST /api/v1/orders/{order_id}/cancel | yes | true no-mock HTTP | test_orders.py | test_cancel_order |
| POST /api/v1/orders/{order_id}/confirm-receipt | yes | true no-mock HTTP | test_refund_after_sales.py | test_confirm_receipt_completes_order |
| POST /api/v1/orders/{order_id}/advance | yes | true no-mock HTTP | test_refund_after_sales.py | _advance_order_to_completed |
| POST /api/v1/orders/{order_id}/payment/proof | yes | true no-mock HTTP | test_payment.py | test_submit_proof |
| POST /api/v1/orders/{order_id}/payment/confirm | yes | true no-mock HTTP | test_payment.py | test_confirm_payment_transitions_order |
| POST /api/v1/orders/{order_id}/voucher | yes | true no-mock HTTP | test_payment.py | test_issue_voucher_happy_path |
| GET /api/v1/orders/{order_id}/voucher | yes | true no-mock HTTP | test_payment.py | test_get_voucher_cross_user_forbidden |
| POST /api/v1/orders/{order_id}/milestones | yes | true no-mock HTTP | test_payment.py | test_add_milestone |
| GET /api/v1/orders/{order_id}/milestones | yes | true no-mock HTTP | test_payment.py | test_get_milestones_cross_user_forbidden |
| POST /api/v1/orders/{order_id}/bargaining/offer | yes | true no-mock HTTP | test_payment.py | test_bargaining_offer_submit |
| GET /api/v1/orders/{order_id}/bargaining | yes | true no-mock HTTP | test_payment.py | test_bargaining_offer_submit |
| POST /api/v1/orders/{order_id}/bargaining/accept | yes | true no-mock HTTP | test_payment.py | test_bargaining_accept_sets_agreed_price |
| POST /api/v1/orders/{order_id}/bargaining/counter | yes | true no-mock HTTP | test_payment.py | test_bargaining_counter |
| POST /api/v1/orders/{order_id}/bargaining/accept-counter | yes | true no-mock HTTP | test_payment.py | test_bargaining_accept_counter_succeeds |
| POST /api/v1/orders/{order_id}/refund | yes | true no-mock HTTP | test_refund_after_sales.py | test_initiate_refund |
| POST /api/v1/orders/{order_id}/refund/process | yes | true no-mock HTTP | test_refund_after_sales.py | test_process_refund |
| GET /api/v1/orders/{order_id}/refund | yes | true no-mock HTTP | test_refund_after_sales.py | test_get_refund_cross_user_forbidden |
| POST /api/v1/orders/{order_id}/after-sales | yes | true no-mock HTTP | test_refund_after_sales.py | test_after_sales_within_window |
| GET /api/v1/orders/{order_id}/after-sales | yes | true no-mock HTTP | test_refund_after_sales.py | test_resolve_after_sales_path_mismatch_rejected |
| POST /api/v1/orders/{order_id}/after-sales/{request_id}/resolve | yes | true no-mock HTTP | test_refund_after_sales.py | test_after_sales_resolve |
| GET /api/v1/queue/documents | yes | true no-mock HTTP | test_queue_endpoints.py | test_pending_documents_reviewer_ok |
| GET /api/v1/queue/payments | yes | true no-mock HTTP | test_queue_endpoints.py | test_pending_payments_reviewer_ok |
| GET /api/v1/queue/orders | yes | true no-mock HTTP | test_queue_endpoints.py | test_pending_orders_reviewer_ok |
| GET /api/v1/queue/exceptions | yes | true no-mock HTTP | test_queue_endpoints.py | test_pending_exceptions_reviewer_ok |
| GET /api/v1/queue/after-sales | yes | true no-mock HTTP | test_queue_endpoints.py | test_pending_after_sales_reviewer_ok |
| POST /api/v1/attendance/anomalies | yes | true no-mock HTTP | test_attendance.py | test_flag_anomaly |
| GET /api/v1/attendance/anomalies | yes | true no-mock HTTP | test_attendance.py | test_list_anomalies |
| POST /api/v1/attendance/exceptions | yes | true no-mock HTTP | test_attendance.py | test_create_exception |
| GET /api/v1/attendance/exceptions | yes | true no-mock HTTP | test_attendance.py | test_list_exceptions |
| GET /api/v1/attendance/exceptions/{exception_id} | yes | true no-mock HTTP | test_attendance.py | test_get_exception |
| POST /api/v1/attendance/exceptions/{exception_id}/proof | yes | true no-mock HTTP | test_attendance.py | test_upload_proof |
| POST /api/v1/attendance/exceptions/{exception_id}/review | yes | true no-mock HTTP | test_attendance.py | test_submit_review_ok |
| GET /api/v1/admin/feature-flags | yes | true no-mock HTTP | test_admin.py | test_list_feature_flags_admin |
| POST /api/v1/admin/feature-flags | yes | true no-mock HTTP | test_admin.py | test_create_feature_flag |
| PATCH /api/v1/admin/feature-flags/{key} | yes | true no-mock HTTP | test_admin.py | test_update_feature_flag |
| GET /api/v1/admin/cohorts | yes | true no-mock HTTP | test_admin.py | test_list_cohorts |
| POST /api/v1/admin/cohorts | yes | true no-mock HTTP | test_admin.py | test_create_cohort |
| POST /api/v1/admin/cohorts/{cohort_id}/assign | yes | true no-mock HTTP | test_admin.py | test_assign_user_to_cohort |
| DELETE /api/v1/admin/cohorts/{cohort_id}/users/{user_id} | yes | true no-mock HTTP | test_admin.py | test_remove_user_from_cohort |
| GET /api/v1/admin/config/bootstrap/{user_id} | yes | true no-mock HTTP | test_admin.py | test_bootstrap_config_for_user |
| GET /api/v1/admin/audit | yes | true no-mock HTTP | test_admin.py | test_audit_search_returns_list |
| GET /api/v1/admin/rbac-policy | yes | true no-mock HTTP | test_admin.py | test_rbac_policy_endpoint |
| GET /api/v1/admin/masking-policy | yes | true no-mock HTTP | test_admin.py | test_masking_policy_endpoint |
| POST /api/v1/admin/exports | yes | true no-mock HTTP | test_admin.py | test_create_export_audit_csv |
| GET /api/v1/admin/exports | yes | true no-mock HTTP | test_admin.py | test_list_exports |
| GET /api/v1/admin/exports/{export_id}/download | yes | true no-mock HTTP | test_admin.py | test_download_export_content_and_watermark |
| GET /api/v1/admin/metrics/summary | yes | true no-mock HTTP | test_admin.py | test_metrics_summary_returns_dict |
| GET /api/v1/admin/traces | yes | true no-mock HTTP | test_admin.py | test_list_traces_returns_list |
| GET /api/v1/admin/cache-stats | yes | true no-mock HTTP | test_admin.py | test_cache_stats_empty_returns_list |
| GET /api/v1/admin/access-logs | yes | true no-mock HTTP | test_admin.py | test_list_access_logs_returns_list |
| GET /api/v1/admin/forecasts | yes | true no-mock HTTP | test_admin.py | test_list_forecasts_empty |
| POST /api/v1/admin/forecasts/compute | yes | true no-mock HTTP | test_admin.py | test_trigger_forecast |

## API Test Classification

1. True No-Mock HTTP
- Primary category for endpoint coverage tests.
- Evidence: repo/backend/api_tests/conftest.py fixture `client` uses `AsyncClient(ASGITransport(app=app))` against `src.main.app`; comments explicitly state real get_db and real Postgres path.
- Representative files: test_auth_login.py, test_candidates.py, test_documents.py, test_orders.py, test_payment.py, test_refund_after_sales.py, test_attendance.py, test_queue_endpoints.py, test_admin.py.

2. HTTP with Mocking
- No API tests found that mock/stub transport, controllers, or service providers in endpoint execution path.
- Result: none.

3. Non-HTTP (unit/integration without HTTP)
- Present inside api_tests package but not endpoint HTTP coverage:
- repo/backend/api_tests/test_refund_after_sales.py: `test_refund_slot_rollback` and `test_after_sales_outside_window` (direct domain/repository checks).

## Mock Detection

| What | Where | Impact |
|---|---|---|
| Environment patching (`monkeypatch.setenv`) | repo/backend/api_tests/conftest.py (`_patch_env`), test_admin.py (EXPORTS_ROOT), test_health.py, test_error_envelopes.py | Configuration-only patching, not route/service mocking |
| JWT test key install (`install_keys`) | repo/backend/api_tests/conftest.py (`_install_jwt_keys`) | Injects signing keys for auth flow; no transport/controller mock |
| KEK install override (`install_kek`) | repo/backend/api_tests/conftest.py (`_install_kek`) | Crypto material setup; no route/service bypass |
| Separate synthetic app route `/admin-only` | repo/backend/api_tests/test_rbac_route_gate.py | HTTP test of dependency gate; not a project endpoint |

Strict classification effect: these do not constitute HTTP transport/controller/service mocking for project endpoint execution.

## Coverage Summary
- Total endpoints: 85
- Endpoints with HTTP tests: 84
- Endpoints with true no-mock HTTP tests: 84
- HTTP coverage: 98.82% (84/85)
- True API coverage: 98.82% (84/85)

Uncovered endpoint:
- GET /api/v1/orders

## Unit Test Summary

### Backend Unit Tests
- Unit test files detected: 31 files in repo/backend/unit_tests.
- Modules covered (evidence by file names):
- Services: test_config_service_unit.py, test_document_service_unit.py, test_payment_service_unit.py
- Domain/state machine/policy: test_order_state_machine.py, test_order_state_machine_extended.py, test_after_sales_policy.py, test_document_policy.py, test_refund_attendance_unit.py
- Security/auth/guards: test_rbac.py, test_jwt.py, test_nonce.py, test_login_throttle.py, test_password_policy.py, test_signing.py, test_device_keys.py, test_argon2.py, test_hashing.py, test_encryption.py, test_data_masking.py
- Repository/storage-adjacent behavior: test_idempotency_store.py, test_cache_stats_logbacked.py, test_audit.py

Important backend modules not clearly unit-tested:
- API route/controller layer itself (expected if covered by API tests, but no route-unit tests)
- Middleware modules in repo/backend/src/api/middleware (TraceIdMiddleware, AccessLogMiddleware)
- Worker loop orchestration in repo/backend/src/workers (auto_cancel, bargaining_expiry, stale_queue, forecasting, refund_progression)
- Repository classes under repo/backend/src/persistence/repositories (direct unit tests not evident by naming)

### Frontend Unit Tests (STRICT)
- Frontend unit test files: present (52 files under repo/frontend/unit_tests with .spec.ts/.contract.spec.ts).
- Framework/tools detected:
- Vitest imports in unit test files (e.g., repo/frontend/unit_tests/bootstrap.spec.ts)
- Vue Test Utils imports (e.g., repo/frontend/unit_tests/views/ProfileView.spec.ts)
- Vue component mount/render assertions (e.g., `mount(ProfileView)` in ProfileView.spec.ts)
- Components/modules covered (representative):
- Views: ProfileView, OrderListView, OrderDetailView, DocumentUploadView, DocumentReviewView, BargainingView, PaymentView, Queue/admin views
- Primitives/components: UploadPanel, BannerAlert, CountdownTimer, StatusChip
- Services/composables/stores/auth flows: attendanceApi, requestSigner, offlineQueue, useOfflineStatus, authSessionRefresh, routeGuard

Important frontend modules not clearly tested:
- App root composition and startup wiring in repo/frontend/src/main.ts and full App.vue integration behavior (no direct dedicated unit spec observed by file naming)
- Some router-level end-to-end navigation permutations rely more on browser tests than unit-only assertions

Mandatory verdict:
- Frontend unit tests: PRESENT

CRITICAL GAP check (fullstack/web + frontend missing/insufficient):
- Not triggered (frontend unit tests are present with direct component mounting and vitest execution artifacts).

### Cross-Layer Observation
- Coverage is backend-heavy but frontend is not untested.
- Balance is acceptable: strong backend API tests plus substantial frontend unit suite and live E2E specs under repo/frontend/e2e.

## API Observability Check
- Strong in many API tests: explicit method/path calls, concrete inputs, and response body assertions.
- Strong examples:
- repo/backend/api_tests/test_auth_login.py (`test_login_happy_path`) validates payload and response fields.
- repo/backend/api_tests/test_admin.py export download test validates status, response headers, and payload hash.
- Weak spots:
- Some queue tests mainly assert status and generic pagination shape with empty datasets (less business-content depth).

## Tests Check
- Success paths: broadly covered.
- Failure/auth/permission cases: broadly covered (401/403/404/409/422/429).
- Edge cases: present for idempotency conflicts, signing failures, cross-user access, after-sales path mismatch.
- Assertions quality: generally meaningful, not purely superficial.
- Over-mocking risk: low for API tests.
- run_tests.sh audit:
- Docker-based orchestration: yes (passes Docker-first requirement for test execution path).
- Local dependency requirement: no host pip/npm install in script.
- Note: Playwright install step occurs inside container (`npx playwright install --with-deps`), not host-local.

## End-to-End Expectations (Fullstack)
- Fullstack expectation met partially to strongly:
- Live FE↔BE E2E tests exist in repo/frontend/e2e/*.spec.ts and Playwright `live` project configured in repo/frontend/playwright.config.ts.
- This complements API + unit suites.

## Test Coverage Score (0-100)
- Score: 92

## Score Rationale
- -7: one uncovered endpoint (GET /api/v1/orders) in strict endpoint-to-test mapping.
- -1: some queue assertions shallow in business payload depth.
- High marks retained for breadth of real HTTP no-mock API coverage, auth/permission failures, and cross-layer test assets.

## Key Gaps
1. Missing direct HTTP test for GET /api/v1/orders (list endpoint).
2. Worker/middleware unit-level granularity is limited.
3. Some queue tests verify structure/status more than domain-rich content.

## Confidence & Assumptions
- Confidence: high.
- Assumptions:
- Static analysis only; no runtime execution performed.
- Endpoint inventory excludes non-project synthetic test routes (e.g., `/admin-only` in test_rbac_route_gate.py).

---

# README Audit

Target file: repo/README.md

## Hard Gate Evaluation

### Formatting
- PASS.
- README is structured, readable markdown with clear sections/tables.

### Startup Instructions (backend/fullstack)
- PASS.
- Contains `docker compose up --build` and `docker compose up` under startup section.

### Access Method
- PASS.
- Explicit URL and port provided: `https://localhost:8443`.

### Verification Method
- PASS.
- Includes health curl check, authenticated login curl, admin endpoint check, and UI verification flow.

### Environment Rules (STRICT Docker-contained)
- PASS.
- README now documents Docker-contained generation commands for certs/keys/secrets (containerized `openssl`) and removes host-local package/runtime install requirements from setup steps.

### Demo Credentials (conditional auth exists)
- PASS.
- Includes username/password for all roles (Candidate, Reviewer, Admin, Proctor).

## Engineering Quality
- Tech stack clarity: strong.
- Architecture explanation: strong.
- Testing instructions: strong and detailed.
- Security/roles explanation: strong.
- Workflow coverage: strong.
- Presentation quality: strong.
- No hard-gate compliance weakness remains.

## High Priority Issues
None.

## Medium Priority Issues
1. Project type label is described as "full-stack" prose rather than explicitly declaring one normalized token (backend/fullstack/web/android/ios/desktop) at top.

## Low Priority Issues
1. README is very large; operational essentials are mixed with deep architectural detail, reducing quick-start signal density.

## Hard Gate Failures
None.

## README Verdict
- PASS

Reason: all required hard gates are now satisfied, including strict Docker-contained environment setup guidance.

---

# Final Verdicts
- Test Coverage Audit Verdict: PARTIAL PASS (strong but not complete due uncovered GET /api/v1/orders).
- README Audit Verdict: PASS.
