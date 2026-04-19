"""
BE-API: role-gated route rejects unauthorized roles.

Stands up a fresh FastAPI app that wires the real `require_role` dependency
and the real `get_current_user` resolver so both the auth token and the
role enforcement are exercised end-to-end.
"""
from datetime import datetime, timezone
import uuid

import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.dependencies import require_role
from src.api.errors import register_exception_handlers
from src.domain.enums import UserRole


@pytest_asyncio.fixture
async def gated_client(_install_jwt_keys):
    """Minimal FastAPI app with a single admin-gated route. Uses the real
    `get_db` wired to Postgres — no dependency overrides."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/admin-only", dependencies=[Depends(require_role(UserRole.admin))])
    async def admin_only():
        return {"ok": True}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


async def _login(client, user):
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "username": user["username"],
            "password": user["password"],
            "nonce": f"n-{uuid.uuid4().hex}",
            "timestamp": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_candidate_rejected_from_admin_route(
    client, gated_client, seeded_user
):
    tokens = await _login(client, seeded_user)
    resp = await gated_client.get(
        "/admin-only",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_unauthenticated_rejected_from_gated_route(gated_client):
    resp = await gated_client.get("/admin-only")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTH_REQUIRED"
