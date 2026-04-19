# audit_report-2 Fix Check (Fresh Static Re-Audit)

Date: 2026-04-20  
Scope: Re-audit only the five issues listed in [.tmp/audit_report-2.md](.tmp/audit_report-2.md), using current repository state.  
Execution boundary: Static inspection only (no runtime execution, no Docker/test execution).

## Overall Result
- Fixed: 5
- Partially Fixed: 0
- Not Fixed: 0

## Edited Parts From Original Audit
- Bargaining rule bypass on fixed-price/resolved-thread mutations: Fail -> Fixed.
- Refund rollback feature-flag namespace drift: Fail -> Fixed.
- Candidate onboarding staff-gated constraint: Partial Fail -> Fixed.
- Bargaining negative test-gap: Partial Fail -> Fixed.
- Traceability docs stale/incorrect module references: Partial Fail -> Fixed.

---

## 1) High: Bargaining rule bypass on fixed-price orders and unresolved thread-state guards
- Previous conclusion: Fail
- Current status: Fixed

Evidence:
- Terminal state guard set introduced: [repo/backend/src/services/bargaining_service.py](repo/backend/src/services/bargaining_service.py#L34)
- Submit flow now enforces bargaining pricing mode and blocks resolved threads: [repo/backend/src/services/bargaining_service.py](repo/backend/src/services/bargaining_service.py#L82), [repo/backend/src/services/bargaining_service.py](repo/backend/src/services/bargaining_service.py#L94)
- Accept flow now enforces bargaining pricing mode and blocks resolved threads: [repo/backend/src/services/bargaining_service.py](repo/backend/src/services/bargaining_service.py#L167), [repo/backend/src/services/bargaining_service.py](repo/backend/src/services/bargaining_service.py#L171)
- Counter flow now enforces bargaining pricing mode and blocks resolved threads: [repo/backend/src/services/bargaining_service.py](repo/backend/src/services/bargaining_service.py#L231), [repo/backend/src/services/bargaining_service.py](repo/backend/src/services/bargaining_service.py#L235)

---

## 2) High: Refund rollback feature-flag namespace drift (admin/frontend vs backend enforcement)
- Previous conclusion: Fail
- Current status: Fixed

Evidence:
- Backend canonical flag key is `rollback_on_refund`: [repo/backend/src/services/refund_service.py](repo/backend/src/services/refund_service.py#L20)
- Frontend admin and session stores use the same key: [repo/frontend/src/stores/admin.ts](repo/frontend/src/stores/admin.ts#L46), [repo/frontend/src/stores/session.ts](repo/frontend/src/stores/session.ts#L14)
- Unit/config tests aligned to `rollback_on_refund`: [repo/backend/unit_tests/test_config_service_unit.py](repo/backend/unit_tests/test_config_service_unit.py#L92)
- API refund behavior tests explicitly seed/read the same key: [repo/backend/api_tests/test_refund_after_sales.py](repo/backend/api_tests/test_refund_after_sales.py#L202)

---

## 3) High: Candidate onboarding creation is staff-gated, conflicting with candidate-maintained onboarding prompt
- Previous conclusion: Partial Fail
- Current status: Fixed

Evidence:
- Candidate self-init endpoint exists: [repo/backend/src/api/routes/candidates.py](repo/backend/src/api/routes/candidates.py#L142), [repo/backend/src/api/routes/candidates.py](repo/backend/src/api/routes/candidates.py#L151)
- Service supports candidate self-profile creation (ownership + idempotency): [repo/backend/src/services/candidate_service.py](repo/backend/src/services/candidate_service.py#L64)
- Frontend API/store wiring present: [repo/frontend/src/services/candidateApi.ts](repo/frontend/src/services/candidateApi.ts#L22), [repo/frontend/src/stores/candidate.ts](repo/frontend/src/stores/candidate.ts#L14)
- Candidate pages now include the self-init banner path: [repo/frontend/src/views/candidate/profile/ProfileView.vue](repo/frontend/src/views/candidate/profile/ProfileView.vue#L57), [repo/frontend/src/views/candidate/profile/ExamScoresView.vue](repo/frontend/src/views/candidate/profile/ExamScoresView.vue#L55), [repo/frontend/src/views/candidate/profile/TransferPreferencesView.vue](repo/frontend/src/views/candidate/profile/TransferPreferencesView.vue#L51), [repo/frontend/src/views/candidate/documents/DocumentListView.vue](repo/frontend/src/views/candidate/documents/DocumentListView.vue#L47), [repo/frontend/src/views/candidate/documents/DocumentUploadView.vue](repo/frontend/src/views/candidate/documents/DocumentUploadView.vue#L40)
- Backend tests added for candidate self-init and idempotency: [repo/backend/api_tests/test_candidates.py](repo/backend/api_tests/test_candidates.py#L220), [repo/backend/api_tests/test_candidates.py](repo/backend/api_tests/test_candidates.py#L234)

---

## 4) Medium: Static test suite missing bargaining negative cases (fixed-price misuse, post-resolution mutation)
- Previous conclusion: Partial Fail
- Current status: Fixed

Evidence:
- Dedicated negative-case API suite now exists: [repo/backend/api_tests/test_bargaining_invariants.py](repo/backend/api_tests/test_bargaining_invariants.py#L1)
- Fixed-price misuse rejection covered: [repo/backend/api_tests/test_bargaining_invariants.py](repo/backend/api_tests/test_bargaining_invariants.py#L92)
- Post-resolution accept/counter/submit rejection coverage present: [repo/backend/api_tests/test_bargaining_invariants.py](repo/backend/api_tests/test_bargaining_invariants.py#L148), [repo/backend/api_tests/test_bargaining_invariants.py](repo/backend/api_tests/test_bargaining_invariants.py#L182), [repo/backend/api_tests/test_bargaining_invariants.py](repo/backend/api_tests/test_bargaining_invariants.py#L215)

---

## 5) Medium: Traceability docs include stale or incorrect module references
- Previous conclusion: Partial Fail
- Current status: Fixed

Evidence:
- Traceability table now points to existing modules: [docs/design.md](docs/design.md#L323), [docs/design.md](docs/design.md#L324)
- Backend storage path is now aligned with implementation (`storage/file_store.py`): [docs/design.md](docs/design.md#L324), [repo/backend/src/storage/file_store.py](repo/backend/src/storage/file_store.py)
- Candidate onboarding wording now reflects both privileged and self-init flows: [docs/design.md](docs/design.md#L338), [repo/backend/src/api/routes/candidates.py](repo/backend/src/api/routes/candidates.py#L146)

---

## Final Fix-Check Conclusion
- Fresh static re-audit confirms all 5 of the 5 previously reported issues are now fixed in current code/docs/tests.
