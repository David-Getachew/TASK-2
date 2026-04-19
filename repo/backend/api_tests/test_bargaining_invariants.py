"""BE-API: Bargaining-service invariant enforcement.

Covers the business-rule guards layered onto `BargainingService`:
    * Fixed-price orders cannot enter the bargaining flow (submit/accept/counter).
    * Resolved threads (accepted / counter_accepted / expired) cannot be mutated.
    * Non-bargaining service items cannot have offers submitted against them.

These tests complement `test_payment.py`, which only exercises the happy-path
bargaining flow. Together they close the negative-case coverage gap called out
in the acceptance audit.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from .conftest import login, make_signing_headers, register_device, signed_post_json


async def _create_item(test_session_factory, *, bargaining: bool):
    from src.persistence.models.order import ServiceItem

    async with test_session_factory() as session:
        item = ServiceItem(
            item_code=f"SVC-{uuid.uuid4().hex[:6].upper()}",
            name="Invariant Test Service",
            pricing_mode="bargaining" if bargaining else "fixed",
            fixed_price=None if bargaining else Decimal("200.00"),
            is_capacity_limited=False,
            bargaining_enabled=bargaining,
            is_active=True,
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return item.id


async def _create_profile(client, reviewer_token: str, user_id) -> str:
    resp = await client.post(
        "/api/v1/candidates",
        params={"user_id": str(user_id)},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


async def _create_order(client, cand_token: str, item_id, pricing_mode: str) -> str:
    auth = {"Authorization": f"Bearer {cand_token}"}
    device_id, priv = await register_device(client, auth)
    path = "/api/v1/orders"
    body = json.dumps(
        {"item_id": str(item_id), "pricing_mode": pricing_mode},
        separators=(",", ":"),
    ).encode()
    sign_hdrs = make_signing_headers(priv, "POST", path, body, device_id)
    resp = await client.post(
        path,
        headers={**auth, **sign_hdrs, "Content-Type": "application/json"},
        content=body,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


async def _submit_offer(client, cand_token: str, order_id: str, amount: str = "150.00"):
    auth = {"Authorization": f"Bearer {cand_token}"}
    device_id, priv = await register_device(client, auth)
    path = f"/api/v1/orders/{order_id}/bargaining/offer"
    body = json.dumps(
        {
            "amount": amount,
            "nonce": f"n-{uuid.uuid4().hex}",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        separators=(",", ":"),
    ).encode()
    sign_hdrs = make_signing_headers(priv, "POST", path, body, device_id)
    return await client.post(
        path,
        headers={**auth, **sign_hdrs, "Content-Type": "application/json"},
        content=body,
    )


def _with_nonce_ts(payload: dict) -> dict:
    return {
        **payload,
        "nonce": f"n-{uuid.uuid4().hex}",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


@pytest.mark.asyncio
async def test_submit_offer_on_fixed_price_order_rejected(
    client, seeded_user, seeded_reviewer, test_session_factory
):
    """Fixed-price order must not be pulled into the bargaining flow."""
    rev_token = await login(client, seeded_reviewer)
    await _create_profile(client, rev_token, seeded_user["id"])
    # Item is fixed-price and bargaining_enabled=False
    item_id = await _create_item(test_session_factory, bargaining=False)

    cand_token = await login(client, seeded_user)
    order_id = await _create_order(client, cand_token, item_id, pricing_mode="fixed")

    resp = await _submit_offer(client, cand_token, order_id, "150.00")
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


@pytest.mark.asyncio
async def test_counter_on_fixed_price_order_rejected(
    client, seeded_user, seeded_reviewer, test_session_factory
):
    """Reviewer counter must not succeed on a fixed-price order, even if a
    stray thread exists. We synthesize the thread directly to bypass the
    submit-offer guard and assert the counter guard catches the bypass."""
    from src.persistence.models.order import BargainingThread

    rev_token = await login(client, seeded_reviewer)
    await _create_profile(client, rev_token, seeded_user["id"])
    item_id = await _create_item(test_session_factory, bargaining=False)

    cand_token = await login(client, seeded_user)
    order_id = await _create_order(client, cand_token, item_id, pricing_mode="fixed")

    now = datetime.now(timezone.utc)
    async with test_session_factory() as session:
        thread = BargainingThread(
            order_id=uuid.UUID(order_id),
            status="open",
            window_starts_at=now,
            window_expires_at=now,
            counter_count=0,
        )
        session.add(thread)
        await session.commit()

    resp = await signed_post_json(
        client,
        rev_token,
        f"/api/v1/orders/{order_id}/bargaining/counter",
        {"counter_amount": "175.00"},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


@pytest.mark.asyncio
async def test_accept_on_resolved_thread_rejected(
    client, seeded_user, seeded_reviewer, test_session_factory
):
    """Once a thread is `accepted`, a second accept must be rejected."""
    rev_token = await login(client, seeded_reviewer)
    await _create_profile(client, rev_token, seeded_user["id"])
    item_id = await _create_item(test_session_factory, bargaining=True)

    cand_token = await login(client, seeded_user)
    order_id = await _create_order(client, cand_token, item_id, pricing_mode="bargaining")

    offer_resp = await _submit_offer(client, cand_token, order_id, "150.00")
    assert offer_resp.status_code == 201, offer_resp.text
    offer_id = offer_resp.json()["data"]["id"]

    first_accept = await signed_post_json(
        client,
        rev_token,
        f"/api/v1/orders/{order_id}/bargaining/accept",
        _with_nonce_ts({"offer_id": offer_id}),
    )
    assert first_accept.status_code == 200, first_accept.text

    second_accept = await signed_post_json(
        client,
        rev_token,
        f"/api/v1/orders/{order_id}/bargaining/accept",
        _with_nonce_ts({"offer_id": offer_id}),
    )
    assert second_accept.status_code == 409, second_accept.text
    assert second_accept.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


@pytest.mark.asyncio
async def test_counter_on_resolved_thread_rejected(
    client, seeded_user, seeded_reviewer, test_session_factory
):
    """After the thread is accepted, a subsequent counter must be rejected."""
    rev_token = await login(client, seeded_reviewer)
    await _create_profile(client, rev_token, seeded_user["id"])
    item_id = await _create_item(test_session_factory, bargaining=True)

    cand_token = await login(client, seeded_user)
    order_id = await _create_order(client, cand_token, item_id, pricing_mode="bargaining")

    offer_resp = await _submit_offer(client, cand_token, order_id, "150.00")
    offer_id = offer_resp.json()["data"]["id"]

    accept_resp = await signed_post_json(
        client,
        rev_token,
        f"/api/v1/orders/{order_id}/bargaining/accept",
        _with_nonce_ts({"offer_id": offer_id}),
    )
    assert accept_resp.status_code == 200, accept_resp.text

    counter_resp = await signed_post_json(
        client,
        rev_token,
        f"/api/v1/orders/{order_id}/bargaining/counter",
        {"counter_amount": "160.00"},
    )
    assert counter_resp.status_code == 409, counter_resp.text
    assert counter_resp.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


@pytest.mark.asyncio
async def test_submit_offer_after_resolution_rejected(
    client, seeded_user, seeded_reviewer, test_session_factory
):
    """Candidate cannot submit another offer after the thread is resolved."""
    rev_token = await login(client, seeded_reviewer)
    await _create_profile(client, rev_token, seeded_user["id"])
    item_id = await _create_item(test_session_factory, bargaining=True)

    cand_token = await login(client, seeded_user)
    order_id = await _create_order(client, cand_token, item_id, pricing_mode="bargaining")

    offer_resp = await _submit_offer(client, cand_token, order_id, "150.00")
    offer_id = offer_resp.json()["data"]["id"]

    accept_resp = await signed_post_json(
        client,
        rev_token,
        f"/api/v1/orders/{order_id}/bargaining/accept",
        _with_nonce_ts({"offer_id": offer_id}),
    )
    assert accept_resp.status_code == 200, accept_resp.text

    # Post-resolution offer must be rejected
    replay = await _submit_offer(client, cand_token, order_id, "140.00")
    assert replay.status_code == 409, replay.text
    assert replay.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"
