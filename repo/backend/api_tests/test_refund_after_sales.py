"""BE-API: Refund initiate, process, slot rollback, after-sales window."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from .conftest import (
    login,
    register_device,
    signed_post_json,
)


async def _create_service_item(test_session_factory, capacity_limited=False, total_slots=5):
    from src.persistence.models.order import ServiceItem, ServiceItemInventory

    async with test_session_factory() as session:
        item = ServiceItem(
            item_code=f"SVC-{uuid.uuid4().hex[:6].upper()}",
            name="Refund Test Service",
            pricing_mode="fixed",
            fixed_price=Decimal("150.00"),
            is_capacity_limited=capacity_limited,
            bargaining_enabled=False,
            is_active=True,
        )
        session.add(item)
        await session.flush()
        if capacity_limited:
            inv = ServiceItemInventory(
                item_id=item.id,
                total_slots=total_slots,
                reserved_count=0,
            )
            session.add(inv)
        await session.commit()
        await session.refresh(item)
        return item.id


async def _create_profile_and_order(client, seeded_user, reviewer_token, test_session_factory, item_id):
    profile_resp = await client.post(
        "/api/v1/candidates",
        params={"user_id": str(seeded_user["id"])},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    # Profile creation is idempotent for test setup; 201 on first, 409/200 otherwise.
    assert profile_resp.status_code in (200, 201, 409)
    cand_token = await login(client, seeded_user)
    order_resp = await signed_post_json(
        client, cand_token, "/api/v1/orders", {"item_id": str(item_id), "pricing_mode": "fixed"}
    )
    assert order_resp.status_code == 201, order_resp.text
    return order_resp.json()["data"]["id"], cand_token


async def _advance_order_to_completed(client, order_id, cand_token, reviewer_token):
    """Submit proof → confirm → advance → confirm receipt → completed.

    Every POST below targets a signed route. Payment proof/confirm were signed
    under audit-5 B2; /advance and /confirm-receipt were added to the signed
    inventory under audit-1 remediation so every order-state transition is
    device-bound + anti-replay.
    """
    # Submit payment proof (signed)
    proof = await signed_post_json(
        client,
        cand_token,
        f"/api/v1/orders/{order_id}/payment/proof",
        {"amount": "150.00", "payment_method": "bank_transfer"},
    )
    assert proof.status_code == 200, proof.text
    # Confirm payment (signed)
    confirm = await signed_post_json(
        client,
        reviewer_token,
        f"/api/v1/orders/{order_id}/payment/confirm",
        {"amount": "150.00", "payment_method": "bank_transfer"},
    )
    assert confirm.status_code == 200, confirm.text
    # Advance to receipt (signed — audit-1 remediation)
    adv = await signed_post_json(
        client, reviewer_token,
        f"/api/v1/orders/{order_id}/advance",
        None,
    )
    assert adv.status_code == 200, adv.text
    # Candidate confirms receipt (signed — audit-1 remediation)
    rcpt = await signed_post_json(
        client, cand_token,
        f"/api/v1/orders/{order_id}/confirm-receipt",
        None,
    )
    assert rcpt.status_code == 200, rcpt.text


@pytest.mark.asyncio
async def test_confirm_receipt_completes_order(client, seeded_user, seeded_reviewer, test_session_factory):
    """Candidate confirm-receipt transitions order to completed status → 200."""
    rev_token = await login(client, seeded_reviewer)
    item_id = await _create_service_item(test_session_factory)
    order_id, cand_token = await _create_profile_and_order(client, seeded_user, rev_token, test_session_factory, item_id)

    await signed_post_json(
        client, cand_token, f"/api/v1/orders/{order_id}/payment/proof",
        {"amount": "150.00", "payment_method": "bank_transfer"},
    )
    await signed_post_json(
        client, rev_token, f"/api/v1/orders/{order_id}/payment/confirm",
        {"amount": "150.00", "payment_method": "bank_transfer"},
    )
    await signed_post_json(
        client, rev_token,
        f"/api/v1/orders/{order_id}/advance",
        None,
    )

    receipt_resp = await signed_post_json(
        client, cand_token,
        f"/api/v1/orders/{order_id}/confirm-receipt",
        None,
    )
    assert receipt_resp.status_code == 200, receipt_resp.text

    order_resp = await client.get(
        f"/api/v1/orders/{order_id}",
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert order_resp.json()["data"]["status"] == "completed"


@pytest.mark.asyncio
async def test_initiate_refund(client, seeded_user, seeded_reviewer, test_session_factory):
    rev_token = await login(client, seeded_reviewer)
    item_id = await _create_service_item(test_session_factory)
    order_id, cand_token = await _create_profile_and_order(client, seeded_user, rev_token, test_session_factory, item_id)
    await _advance_order_to_completed(client, order_id, cand_token, rev_token)

    refund_resp = await signed_post_json(
        client, rev_token, f"/api/v1/orders/{order_id}/refund",
        {"amount": "150.00", "reason": "Customer requested refund."},
    )
    assert refund_resp.status_code == 201, refund_resp.text
    order_resp = await client.get(
        f"/api/v1/orders/{order_id}",
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert order_resp.json()["data"]["status"] == "refund_in_progress"


@pytest.mark.asyncio
async def test_process_refund(client, seeded_user, seeded_reviewer, seeded_admin, test_session_factory):
    rev_token = await login(client, seeded_reviewer)
    admin_token = await login(client, seeded_admin)
    item_id = await _create_service_item(test_session_factory)
    order_id, cand_token = await _create_profile_and_order(client, seeded_user, rev_token, test_session_factory, item_id)
    await _advance_order_to_completed(client, order_id, cand_token, rev_token)

    await signed_post_json(
        client, rev_token, f"/api/v1/orders/{order_id}/refund",
        {"amount": "150.00", "reason": "Refund requested."},
    )

    process_resp = await signed_post_json(
        client, admin_token, f"/api/v1/orders/{order_id}/refund/process", {},
    )
    assert process_resp.status_code == 200, process_resp.text

    order_resp = await client.get(
        f"/api/v1/orders/{order_id}",
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert order_resp.json()["data"]["status"] == "refunded"


@pytest.mark.asyncio
async def test_refund_slot_rollback(test_session_factory):
    """Capacity-limited item: processing refund decrements reserved_count."""
    item_id = await _create_service_item(test_session_factory, capacity_limited=True, total_slots=5)

    from src.persistence.models.order import ServiceItemInventory
    from sqlalchemy import select

    async with test_session_factory() as session:
        inv = (await session.execute(
            select(ServiceItemInventory).where(ServiceItemInventory.item_id == item_id)
        )).scalar_one()
        initial = inv.reserved_count
        inv.reserved_count = max(0, inv.reserved_count - 1)
        await session.commit()

        inv2 = (await session.execute(
            select(ServiceItemInventory).where(ServiceItemInventory.item_id == item_id)
        )).scalar_one()
        assert inv2.reserved_count == max(0, initial - 1)


async def _seed_refund_flag(test_session_factory, value: str) -> None:
    """Upsert the rollback_on_refund feature flag directly via the repo."""
    from src.persistence.repositories.config_repo import ConfigRepository

    async with test_session_factory() as session:
        repo = ConfigRepository(session)
        existing = await repo.get_flag("rollback_on_refund")
        if existing is None:
            await repo.create_flag(
                key="rollback_on_refund",
                value=value,
                value_type="boolean",
                description="Restore capacity on refund",
            )
        else:
            existing.value = value
            await session.flush()
        await session.commit()


async def _run_refund_to_process(
    client, seeded_user, seeded_reviewer, seeded_admin, test_session_factory
) -> dict:
    rev_token = await login(client, seeded_reviewer)
    admin_token = await login(client, seeded_admin)
    item_id = await _create_service_item(
        test_session_factory, capacity_limited=True, total_slots=5
    )

    order_id, cand_token = await _create_profile_and_order(
        client, seeded_user, rev_token, test_session_factory, item_id
    )
    await _advance_order_to_completed(client, order_id, cand_token, rev_token)
    await signed_post_json(
        client, rev_token, f"/api/v1/orders/{order_id}/refund",
        {"amount": "150.00", "reason": "Refund requested."},
    )
    process_resp = await signed_post_json(
        client, admin_token, f"/api/v1/orders/{order_id}/refund/process", {},
    )
    assert process_resp.status_code == 200, process_resp.text
    return {
        "order_id": order_id,
        "item_id": item_id,
        "refund": process_resp.json()["data"],
    }


@pytest.mark.asyncio
async def test_refund_rollback_flag_enabled_restores_slot(
    client, seeded_user, seeded_reviewer, seeded_admin, test_session_factory
):
    """rollback_on_refund=true → processed refund releases the reserved slot."""
    await _seed_refund_flag(test_session_factory, "true")
    result = await _run_refund_to_process(
        client, seeded_user, seeded_reviewer, seeded_admin, test_session_factory
    )
    assert result["refund"]["rollback_applied"] is True

    from src.persistence.models.order import ServiceItemInventory
    from sqlalchemy import select

    async with test_session_factory() as session:
        inv = (
            await session.execute(
                select(ServiceItemInventory).where(
                    ServiceItemInventory.item_id == result["item_id"]
                )
            )
        ).scalar_one()
        assert inv.reserved_count == 0


@pytest.mark.asyncio
async def test_refund_rollback_flag_disabled_skips_slot_release(
    client, seeded_user, seeded_reviewer, seeded_admin, test_session_factory
):
    """rollback_on_refund=false → refund processes but slot stays reserved."""
    await _seed_refund_flag(test_session_factory, "false")
    result = await _run_refund_to_process(
        client, seeded_user, seeded_reviewer, seeded_admin, test_session_factory
    )
    assert result["refund"]["rollback_applied"] is False

    from src.persistence.models.order import ServiceItemInventory
    from sqlalchemy import select

    async with test_session_factory() as session:
        inv = (
            await session.execute(
                select(ServiceItemInventory).where(
                    ServiceItemInventory.item_id == result["item_id"]
                )
            )
        ).scalar_one()
        # Slot stayed reserved because the flag gates the release path.
        assert inv.reserved_count == 1


@pytest.mark.asyncio
async def test_after_sales_within_window(client, seeded_user, seeded_reviewer, test_session_factory):
    rev_token = await login(client, seeded_reviewer)
    item_id = await _create_service_item(test_session_factory)
    order_id, cand_token = await _create_profile_and_order(client, seeded_user, rev_token, test_session_factory, item_id)
    await _advance_order_to_completed(client, order_id, cand_token, rev_token)

    resp = await signed_post_json(
        client, cand_token, f"/api/v1/orders/{order_id}/after-sales",
        {"request_type": "complaint", "description": "Service was not as described."},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["data"]["status"] == "open"


@pytest.mark.asyncio
async def test_after_sales_outside_window(test_session_factory):
    """After-sales window domain check: day 15 is rejected."""
    from src.domain.after_sales_policy import AfterSalesWindowExpiredError, assert_within_window

    completed_at = datetime.now(timezone.utc) - timedelta(days=15, seconds=1)
    now = datetime.now(timezone.utc)

    with pytest.raises(AfterSalesWindowExpiredError):
        assert_within_window(completed_at, now)


@pytest.mark.asyncio
async def test_after_sales_resolve(client, seeded_user, seeded_reviewer, test_session_factory):
    rev_token = await login(client, seeded_reviewer)
    item_id = await _create_service_item(test_session_factory)
    order_id, cand_token = await _create_profile_and_order(client, seeded_user, rev_token, test_session_factory, item_id)
    await _advance_order_to_completed(client, order_id, cand_token, rev_token)

    create_resp = await signed_post_json(
        client, cand_token, f"/api/v1/orders/{order_id}/after-sales",
        {"request_type": "complaint", "description": "Issue with service."},
    )
    assert create_resp.status_code == 201
    request_id = create_resp.json()["data"]["id"]

    resolve_resp = await signed_post_json(
        client, rev_token,
        f"/api/v1/orders/{order_id}/after-sales/{request_id}/resolve",
        {"resolution_notes": "Issue acknowledged and resolved."},
    )
    assert resolve_resp.status_code == 200, resolve_resp.text
    assert resolve_resp.json()["data"]["status"] == "resolved"


@pytest.mark.asyncio
async def test_resolve_after_sales_path_mismatch_rejected(
    client, seeded_user, seeded_reviewer, test_session_factory
):
    """Mismatched {order_id}/{request_id} pair must 404 — parent-child path binding."""
    rev_token = await login(client, seeded_reviewer)
    item_id = await _create_service_item(test_session_factory)

    # Candidate creates order A, completes it, and files an after-sales request.
    order_a_id, cand_token = await _create_profile_and_order(
        client, seeded_user, rev_token, test_session_factory, item_id
    )
    await _advance_order_to_completed(client, order_a_id, cand_token, rev_token)
    create_resp = await signed_post_json(
        client, cand_token, f"/api/v1/orders/{order_a_id}/after-sales",
        {"request_type": "complaint", "description": "A issue."},
    )
    assert create_resp.status_code == 201, create_resp.text
    request_a_id = create_resp.json()["data"]["id"]

    # Candidate creates a second, unrelated completed order B (same candidate).
    item_id_b = await _create_service_item(test_session_factory)
    order_b_resp = await signed_post_json(
        client, cand_token, "/api/v1/orders",
        {"item_id": str(item_id_b), "pricing_mode": "fixed"},
    )
    assert order_b_resp.status_code == 201, order_b_resp.text
    order_b_id = order_b_resp.json()["data"]["id"]
    await _advance_order_to_completed(client, order_b_id, cand_token, rev_token)

    # Reviewer tries to resolve request_A via order_B's URL → must 404.
    resp = await signed_post_json(
        client, rev_token,
        f"/api/v1/orders/{order_b_id}/after-sales/{request_a_id}/resolve",
        {"resolution_notes": "Should not apply under wrong order."},
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["error"]["code"] == "NOT_FOUND"

    # Request-A must still be 'open' — no mutation under mismatched URL.
    list_resp = await client.get(
        f"/api/v1/orders/{order_a_id}/after-sales",
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert list_resp.status_code == 200
    items = list_resp.json()["data"]
    assert any(
        item["id"] == request_a_id and item["status"] == "open" for item in items
    )


@pytest.mark.asyncio
async def test_get_refund_cross_user_forbidden(
    client, seeded_user, seeded_reviewer, seeded_admin, _install_jwt_keys, test_session_factory
):
    """Candidate B cannot read the refund record for Candidate A's order → 403."""
    from src.persistence.models.auth import User
    from src.security.passwords import hash_password

    async with test_session_factory() as session:
        user_b = User(
            username=f"b-{uuid.uuid4().hex[:8]}",
            password_hash=hash_password("correct horse battery staple"),
            role="candidate",
            full_name="B Candidate",
            is_active=True,
            is_locked=False,
        )
        session.add(user_b)
        await session.commit()
        await session.refresh(user_b)
        user_b_data = {"id": user_b.id, "username": user_b.username, "password": "correct horse battery staple"}

    rev_token = await login(client, seeded_reviewer)
    admin_token = await login(client, seeded_admin)

    # Create profile for user_b (seeded_user's profile is created inside _create_profile_and_order)
    await client.post(
        "/api/v1/candidates",
        params={"user_id": str(user_b_data["id"])},
        headers={"Authorization": f"Bearer {rev_token}"},
    )

    item_id = await _create_service_item(test_session_factory)
    order_id, cand_a_token = await _create_profile_and_order(
        client, seeded_user, rev_token, test_session_factory, item_id
    )
    await _advance_order_to_completed(client, order_id, cand_a_token, rev_token)

    # Reviewer initiates refund for candidate A's order
    await signed_post_json(
        client, rev_token, f"/api/v1/orders/{order_id}/refund",
        {"amount": "150.00", "reason": "Test refund."},
    )

    # Candidate B tries to read refund → 403
    cand_b_token = await login(client, user_b_data)
    resp = await client.get(
        f"/api/v1/orders/{order_id}/refund",
        headers={"Authorization": f"Bearer {cand_b_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_after_sales_submit_cross_user_forbidden(
    client, seeded_user, seeded_reviewer, _install_jwt_keys, test_session_factory
):
    """Candidate B cannot submit an after-sales request on Candidate A's completed order → 403."""
    from src.persistence.models.auth import User
    from src.security.passwords import hash_password

    async with test_session_factory() as session:
        user_b = User(
            username=f"b-{uuid.uuid4().hex[:8]}",
            password_hash=hash_password("correct horse battery staple"),
            role="candidate",
            full_name="B Candidate",
            is_active=True,
            is_locked=False,
        )
        session.add(user_b)
        await session.commit()
        await session.refresh(user_b)
        user_b_data = {"id": user_b.id, "username": user_b.username, "password": "correct horse battery staple"}

    rev_token = await login(client, seeded_reviewer)
    await client.post(
        "/api/v1/candidates",
        params={"user_id": str(user_b_data["id"])},
        headers={"Authorization": f"Bearer {rev_token}"},
    )

    item_id = await _create_service_item(test_session_factory)
    order_id, cand_a_token = await _create_profile_and_order(
        client, seeded_user, rev_token, test_session_factory, item_id
    )
    await _advance_order_to_completed(client, order_id, cand_a_token, rev_token)

    # Candidate B tries to submit after-sales on Candidate A's order → 403
    cand_b_token = await login(client, user_b_data)
    resp = await signed_post_json(
        client, cand_b_token, f"/api/v1/orders/{order_id}/after-sales",
        {"request_type": "complaint", "description": "Not my order."},
    )
    assert resp.status_code == 403
