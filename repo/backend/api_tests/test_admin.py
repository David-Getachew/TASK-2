"""
BE-API-HTTP: Admin endpoints — feature flags, cohort management, audit search,
export jobs, metrics summary, cache stats, forecasts, bootstrap config.

All tests use the real FastAPI route stack against real PostgreSQL (no dependency overrides).
"""
from __future__ import annotations

import pytest

from .conftest import login


# ── Helpers ───────────────────────────────────────────────────────────────────

async def admin_token(client, seeded_admin) -> str:
    return await login(client, seeded_admin)


async def seed_flag(client, token: str, key: str = "bargaining_enabled", value: str = "true") -> dict:
    resp = await client.post(
        f"/api/v1/admin/feature-flags?key={key}",
        json={"value": value, "change_reason": None},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["data"]


# ── Feature flags ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_feature_flags_admin(client, seeded_admin):
    token = await admin_token(client, seeded_admin)
    resp = await client.get(
        "/api/v1/admin/feature-flags",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)


@pytest.mark.asyncio
async def test_create_feature_flag(client, seeded_admin):
    token = await admin_token(client, seeded_admin)
    flag = await seed_flag(client, token, key="test_flag_create", value="false")
    assert flag["key"] == "test_flag_create"
    assert flag["value"] == "false"


@pytest.mark.asyncio
async def test_update_feature_flag(client, seeded_admin):
    token = await admin_token(client, seeded_admin)
    await seed_flag(client, token, key="update_test_flag", value="false")
    resp = await client.patch(
        "/api/v1/admin/feature-flags/update_test_flag",
        json={"value": "true", "change_reason": "test update"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["value"] == "true"


@pytest.mark.asyncio
async def test_feature_flag_update_history_recorded(client, seeded_admin, db_session):
    """Flag history row is created on update."""
    token = await admin_token(client, seeded_admin)
    await seed_flag(client, token, key="hist_flag", value="false")
    await client.patch(
        "/api/v1/admin/feature-flags/hist_flag",
        json={"value": "true", "change_reason": "audit test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    from src.persistence.models.config_audit import FeatureFlagHistory
    from sqlalchemy import select
    rows = list((await db_session.execute(
        select(FeatureFlagHistory).where(FeatureFlagHistory.flag_key == "hist_flag")
    )).scalars().all())
    assert len(rows) >= 1
    assert rows[0].old_value == "false"
    assert rows[0].new_value == "true"


@pytest.mark.asyncio
async def test_non_admin_cannot_access_flags(client, seeded_reviewer):
    token = await login(client, seeded_reviewer)
    resp = await client.get(
        "/api/v1/admin/feature-flags",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ── Cohorts ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_cohort(client, seeded_admin):
    token = await admin_token(client, seeded_admin)
    resp = await client.post(
        "/api/v1/admin/cohorts",
        json={"cohort_key": "pilot_cohort", "name": "Pilot Users", "flag_overrides": {"bargaining_enabled": "true"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201), resp.text
    data = resp.json()["data"]
    assert data["cohort_key"] == "pilot_cohort"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_list_cohorts(client, seeded_admin):
    token = await admin_token(client, seeded_admin)
    await client.post(
        "/api/v1/admin/cohorts",
        json={"cohort_key": "list_test", "name": "List Test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.get(
        "/api/v1/admin/cohorts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)


@pytest.mark.asyncio
async def test_assign_user_to_cohort(client, seeded_admin, seeded_user):
    token = await admin_token(client, seeded_admin)
    cohort_resp = await client.post(
        "/api/v1/admin/cohorts",
        json={"cohort_key": "assign_test", "name": "Assign Test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    cohort_id = cohort_resp.json()["data"]["id"]
    user_id = str(seeded_user["id"])

    resp = await client.post(
        f"/api/v1/admin/cohorts/{cohort_id}/assign",
        json={"user_id": user_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["user_id"] == user_id


# ── Audit search ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_search_returns_list(client, seeded_admin):
    token = await admin_token(client, seeded_admin)
    resp = await client.get(
        "/api/v1/admin/audit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "pagination" in body


@pytest.mark.asyncio
async def test_audit_search_by_event_type(client, seeded_admin):
    token = await admin_token(client, seeded_admin)
    resp = await client.get(
        "/api/v1/admin/audit?event_type=login_success",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    # All returned entries must be of the filtered event_type
    for entry in resp.json()["data"]:
        assert entry["event_type"] == "login_success"


@pytest.mark.asyncio
async def test_audit_search_by_outcome(client, seeded_admin):
    token = await admin_token(client, seeded_admin)
    resp = await client.get(
        "/api/v1/admin/audit?outcome=success",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_audit_search_date_range(client, seeded_admin):
    """Date range filters don't crash; empty range returns empty list."""
    token = await admin_token(client, seeded_admin)
    resp = await client.get(
        "/api/v1/admin/audit?from_date=2020-01-01T00:00:00Z&to_date=2020-01-02T00:00:00Z",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"] == []


# ── RBAC / masking policy ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rbac_policy_endpoint(client, seeded_admin):
    token = await admin_token(client, seeded_admin)
    resp = await client.get(
        "/api/v1/admin/rbac-policy",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "roles" in data
    assert "download_approved_roles" in data
    assert "admin" in data["roles"]


@pytest.mark.asyncio
async def test_masking_policy_endpoint(client, seeded_admin):
    token = await admin_token(client, seeded_admin)
    resp = await client.get(
        "/api/v1/admin/masking-policy",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "masked_fields" in data
    assert "restricted_downloads" in data


# ── Exports ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_export_audit_csv(client, seeded_admin, tmp_path, monkeypatch):
    monkeypatch.setenv("EXPORTS_ROOT", str(tmp_path))
    token = await admin_token(client, seeded_admin)
    resp = await client.post(
        "/api/v1/admin/exports",
        json={"export_type": "audit_csv", "filters": None},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201), resp.text
    data = resp.json()["data"]
    assert data["export_type"] == "audit_csv"
    assert data["status"] == "completed"
    assert data["sha256_hash"] is not None
    assert data["watermark_applied"] is True


@pytest.mark.asyncio
async def test_list_exports(client, seeded_admin):
    token = await admin_token(client, seeded_admin)
    resp = await client.get(
        "/api/v1/admin/exports",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "data" in resp.json()
    assert "pagination" in resp.json()


@pytest.mark.asyncio
async def test_download_export_content_and_watermark(
    client, seeded_admin, seeded_reviewer, tmp_path, monkeypatch
):
    """GET /admin/exports/{id}/download — admin gets CSV bytes; SHA-256 matches
    the hash returned at create; non-admin is blocked with 403."""
    import hashlib

    monkeypatch.setenv("EXPORTS_ROOT", str(tmp_path))
    token = await admin_token(client, seeded_admin)
    create = await client.post(
        "/api/v1/admin/exports",
        json={"export_type": "audit_csv", "filters": None},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create.status_code in (200, 201), create.text
    data = create.json()["data"]
    export_id = data["id"]
    expected_hash = data["sha256_hash"]

    resp = await client.get(
        f"/api/v1/admin/exports/{export_id}/download",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers.get("Content-Disposition", "").startswith("attachment;")
    assert ".csv" in resp.headers.get("Content-Disposition", "")
    body = resp.content
    assert body, "empty export body"
    assert hashlib.sha256(body).hexdigest() == expected_hash

    # Reviewer — admin-only surface, 403.
    rev_token = await login(client, seeded_reviewer)
    blocked = await client.get(
        f"/api/v1/admin/exports/{export_id}/download",
        headers={"Authorization": f"Bearer {rev_token}"},
    )
    assert blocked.status_code == 403


@pytest.mark.asyncio
async def test_non_admin_cannot_create_export(client, seeded_reviewer):
    token = await login(client, seeded_reviewer)
    resp = await client.post(
        "/api/v1/admin/exports",
        json={"export_type": "audit_csv", "filters": None},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ── Metrics summary ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_metrics_summary_returns_dict(client, seeded_admin):
    token = await admin_token(client, seeded_admin)
    resp = await client.get(
        "/api/v1/admin/metrics/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, dict)
    # At minimum the login_attempts counter should be present
    assert any("login" in k for k in data)


# ── Cache stats ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_stats_empty_returns_list(client, seeded_admin):
    token = await admin_token(client, seeded_admin)
    resp = await client.get(
        "/api/v1/admin/cache-stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)


# ── Forecasts ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_forecasts_empty(client, seeded_admin):
    token = await admin_token(client, seeded_admin)
    resp = await client.get(
        "/api/v1/admin/forecasts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)


@pytest.mark.asyncio
async def test_trigger_forecast(client, seeded_admin):
    token = await admin_token(client, seeded_admin)
    resp = await client.post(
        "/api/v1/admin/forecasts/compute?horizon_days=7&input_window_days=30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201), resp.text
    data = resp.json()["data"]
    assert data["forecast_horizon_days"] == 7
    assert data["input_window_days"] == 30
    assert isinstance(data["request_volume_forecast"], dict)
    assert len(data["request_volume_forecast"]) == 7


# ── Bootstrap config ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bootstrap_config_for_user(client, seeded_admin, seeded_user):
    token = await admin_token(client, seeded_admin)
    user_id = str(seeded_user["id"])
    resp = await client.get(
        f"/api/v1/admin/config/bootstrap/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["user_id"] == user_id
    assert "resolved_flags" in data
    assert "signature" in data
    assert data["signature"]


@pytest.mark.asyncio
async def test_bootstrap_config_unknown_user(client, seeded_admin):
    token = await admin_token(client, seeded_admin)
    import uuid
    resp = await client.get(
        f"/api/v1/admin/config/bootstrap/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ── Traces ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_traces_returns_list(client, seeded_admin):
    token = await admin_token(client, seeded_admin)
    resp = await client.get(
        "/api/v1/admin/traces",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert isinstance(body["data"], list)
    assert "pagination" in body
    assert "page" in body["pagination"]
    assert "total" in body["pagination"]


@pytest.mark.asyncio
async def test_list_traces_non_admin_forbidden(client, seeded_reviewer):
    token = await login(client, seeded_reviewer)
    resp = await client.get(
        "/api/v1/admin/traces",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ── Access logs ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_access_logs_returns_list(client, seeded_admin):
    token = await admin_token(client, seeded_admin)
    resp = await client.get(
        "/api/v1/admin/access-logs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert isinstance(body["data"], list)
    assert "pagination" in body
    assert "page" in body["pagination"]
    assert "total" in body["pagination"]


@pytest.mark.asyncio
async def test_list_access_logs_non_admin_forbidden(client, seeded_reviewer):
    token = await login(client, seeded_reviewer)
    resp = await client.get(
        "/api/v1/admin/access-logs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ── Cohort user removal ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_remove_user_from_cohort(client, seeded_admin, seeded_user):
    token = await admin_token(client, seeded_admin)
    user_id = str(seeded_user["id"])

    # Create a cohort
    cohort_resp = await client.post(
        "/api/v1/admin/cohorts",
        json={"cohort_key": "removal_test", "name": "Removal Test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert cohort_resp.status_code in (200, 201), cohort_resp.text
    cohort_id = cohort_resp.json()["data"]["id"]

    # Assign the user
    assign_resp = await client.post(
        f"/api/v1/admin/cohorts/{cohort_id}/assign",
        json={"user_id": user_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert assign_resp.status_code == 200, assign_resp.text

    # Remove the user
    del_resp = await client.delete(
        f"/api/v1/admin/cohorts/{cohort_id}/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_resp.status_code == 200
    body = del_resp.json()
    assert body["success"] is True


@pytest.mark.asyncio
async def test_remove_user_from_cohort_not_member(client, seeded_admin, seeded_user):
    """Removing a user not in the cohort returns 404."""
    import uuid as _uuid
    token = await admin_token(client, seeded_admin)

    cohort_resp = await client.post(
        "/api/v1/admin/cohorts",
        json={"cohort_key": "removal_missing", "name": "Removal Missing"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert cohort_resp.status_code in (200, 201), cohort_resp.text
    cohort_id = cohort_resp.json()["data"]["id"]

    del_resp = await client.delete(
        f"/api/v1/admin/cohorts/{cohort_id}/users/{_uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_resp.status_code == 404
