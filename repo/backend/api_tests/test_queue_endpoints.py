"""BE-API: Queue endpoints — role gates and pagination envelope for all 5 queue routes.

All tests use real FastAPI ASGI against a real PostgreSQL database (via conftest fixtures; no dependency overrides).
No data is seeded, so every list returns an empty array; the assertions verify
routing, auth enforcement, pagination structure, and query-param forwarding.
"""
from __future__ import annotations

import pytest

from .conftest import login

BASE = "/api/v1/queue"


# ---------------------------------------------------------------------------
# /queue/documents
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pending_documents_reviewer_ok(client, seeded_reviewer):
    token = await login(client, seeded_reviewer)
    resp = await client.get(
        f"{BASE}/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)
    assert "pagination" in body
    assert body["pagination"]["page"] == 1
    assert body["pagination"]["page_size"] == 20
    assert body["pagination"]["total"] == 0


@pytest.mark.asyncio
async def test_pending_documents_candidate_forbidden(client, seeded_user):
    token = await login(client, seeded_user)
    resp = await client.get(
        f"{BASE}/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# /queue/payments
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pending_payments_reviewer_ok(client, seeded_reviewer):
    token = await login(client, seeded_reviewer)
    resp = await client.get(
        f"{BASE}/payments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)
    assert "pagination" in body
    assert body["pagination"]["total"] == 0


@pytest.mark.asyncio
async def test_pending_payments_candidate_forbidden(client, seeded_user):
    token = await login(client, seeded_user)
    resp = await client.get(
        f"{BASE}/payments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# /queue/orders
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pending_orders_reviewer_ok(client, seeded_reviewer):
    token = await login(client, seeded_reviewer)
    resp = await client.get(
        f"{BASE}/orders",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)
    assert "pagination" in body
    assert body["pagination"]["total"] == 0


# ---------------------------------------------------------------------------
# /queue/exceptions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pending_exceptions_reviewer_ok(client, seeded_reviewer):
    token = await login(client, seeded_reviewer)
    resp = await client.get(
        f"{BASE}/exceptions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)
    assert "pagination" in body
    assert body["pagination"]["total"] == 0


@pytest.mark.asyncio
async def test_pending_exceptions_status_filter(client, seeded_reviewer):
    """Query-param ?status= is forwarded to the service layer without raising."""
    token = await login(client, seeded_reviewer)
    resp = await client.get(
        f"{BASE}/exceptions",
        params={"status": "pending_initial_review"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)
    # All items in the result must match the requested status (empty DB → none)
    for item in body["data"]:
        assert item["status"] == "pending_initial_review"


# ---------------------------------------------------------------------------
# /queue/after-sales
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pending_after_sales_reviewer_ok(client, seeded_reviewer):
    token = await login(client, seeded_reviewer)
    resp = await client.get(
        f"{BASE}/after-sales",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)
    assert "pagination" in body
    assert body["pagination"]["total"] == 0


# ---------------------------------------------------------------------------
# Admin role also has access to all queue routes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_can_access_queue_documents(client, seeded_admin):
    token = await login(client, seeded_admin)
    resp = await client.get(
        f"{BASE}/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_can_access_queue_payments(client, seeded_admin):
    token = await login(client, seeded_admin)
    resp = await client.get(
        f"{BASE}/payments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_can_access_queue_orders(client, seeded_admin):
    token = await login(client, seeded_admin)
    resp = await client.get(
        f"{BASE}/orders",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_can_access_queue_exceptions(client, seeded_admin):
    token = await login(client, seeded_admin)
    resp = await client.get(
        f"{BASE}/exceptions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_can_access_queue_after_sales(client, seeded_admin):
    token = await login(client, seeded_admin)
    resp = await client.get(
        f"{BASE}/after-sales",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Proctor role policy — exceptions queue only (audit-3 High #3 remediation)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_proctor_can_access_queue_exceptions(client, seeded_proctor):
    """Proctor is the frontline attendance adjudicator; the exceptions queue
    MUST admit proctor so the staff exception-review flow works end-to-end.
    """
    token = await login(client, seeded_proctor)
    resp = await client.get(
        f"{BASE}/exceptions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)
    assert "pagination" in body


@pytest.mark.asyncio
async def test_proctor_forbidden_from_document_queue(client, seeded_proctor):
    """Proctor must NOT be able to read the document review queue —
    that queue is reviewer/admin only."""
    token = await login(client, seeded_proctor)
    resp = await client.get(
        f"{BASE}/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_proctor_forbidden_from_payment_queue(client, seeded_proctor):
    token = await login(client, seeded_proctor)
    resp = await client.get(
        f"{BASE}/payments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_proctor_forbidden_from_order_queue(client, seeded_proctor):
    token = await login(client, seeded_proctor)
    resp = await client.get(
        f"{BASE}/orders",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_proctor_forbidden_from_after_sales_queue(client, seeded_proctor):
    token = await login(client, seeded_proctor)
    resp = await client.get(
        f"{BASE}/after-sales",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Unauthenticated request is rejected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_queue_documents_unauthenticated(client):
    resp = await client.get(f"{BASE}/documents")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Pagination parameters are honoured
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_queue_pagination_params(client, seeded_reviewer):
    token = await login(client, seeded_reviewer)
    resp = await client.get(
        f"{BASE}/documents",
        params={"page": 2, "page_size": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    pagination = resp.json()["pagination"]
    assert pagination["page"] == 2
    assert pagination["page_size"] == 5
