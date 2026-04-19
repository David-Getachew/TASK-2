"""
BE-API: POST /api/v1/auth/refresh.

Covers successful rotation, consumed-token reuse → family invalidation,
and that the invalidated family's tokens can no longer refresh.
"""
from datetime import datetime, timezone
import uuid

import pytest


def _signed(body: dict) -> dict:
    body.setdefault("nonce", f"n-{uuid.uuid4().hex}")
    body.setdefault(
        "timestamp",
        datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    return body


async def _login(client, user):
    resp = await client.post(
        "/api/v1/auth/login",
        json=_signed(
            {"username": user["username"], "password": user["password"]}
        ),
    )
    assert resp.status_code == 200
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_refresh_rotates_token(client, seeded_user):
    tokens = await _login(client, seeded_user)
    resp = await client.post(
        "/api/v1/auth/refresh",
        json=_signed({"refresh_token": tokens["refresh_token"]}),
    )
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["refresh_token"] != tokens["refresh_token"]
    assert body["access_token"]


@pytest.mark.asyncio
async def test_refresh_reuse_invalidates_family(client, seeded_user):
    tokens = await _login(client, seeded_user)
    # First rotation: ok
    r1 = await client.post(
        "/api/v1/auth/refresh",
        json=_signed({"refresh_token": tokens["refresh_token"]}),
    )
    assert r1.status_code == 200
    # Reuse the original (now consumed) token → triggers reuse detection
    r2 = await client.post(
        "/api/v1/auth/refresh",
        json=_signed({"refresh_token": tokens["refresh_token"]}),
    )
    assert r2.status_code == 401
    assert r2.json()["error"]["code"] == "AUTH_REQUIRED"
    # Even the newly rotated token can no longer refresh — family invalidated
    rotated = r1.json()["data"]["refresh_token"]
    r3 = await client.post(
        "/api/v1/auth/refresh",
        json=_signed({"refresh_token": rotated}),
    )
    assert r3.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_unknown_token_returns_401(client):
    resp = await client.post(
        "/api/v1/auth/refresh",
        json=_signed({"refresh_token": "nonexistent-opaque-token"}),
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTH_REQUIRED"


@pytest.mark.asyncio
async def test_refresh_payload_requires_nonce_and_timestamp(client, seeded_user):
    """FE/BE contract guard: refresh body must include nonce+timestamp.

    Regression pin for audit-2 blocker (FE sent only refresh_token, BE required
    nonce+timestamp). 422 validation error must come back if either is omitted.
    """
    tokens = await _login(client, seeded_user)

    no_nonce = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": tokens["refresh_token"],
            "timestamp": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )
    assert no_nonce.status_code == 422

    no_ts = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": tokens["refresh_token"],
            "nonce": f"n-{uuid.uuid4().hex}",
        },
    )
    assert no_ts.status_code == 422

    neither = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert neither.status_code == 422
