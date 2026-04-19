"""
No-mock API test for GET /api/v1/internal/health.
Uses HTTPX AsyncClient against the real FastAPI app instance (no separate server required).
"""
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport


@pytest.fixture(autouse=True)
def _patch_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://test:test@localhost/test")
    monkeypatch.setenv("SECRET_KEY", "a" * 32)
    monkeypatch.setenv("ENVIRONMENT", "development")


@pytest_asyncio.fixture
async def client():
    from src.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_ok(client):
    response = await client.get("/api/v1/internal/health")
    assert response.status_code == 200
    body = response.json()
    # Health endpoint conforms to the unified success envelope documented
    # in docs/api-spec.md §1 — `{ success, data, meta }`.
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
    assert body["data"]["service"] == "merittrack"
    assert "meta" in body and "trace_id" in body["meta"]


@pytest.mark.asyncio
async def test_health_returns_json(client):
    response = await client.get("/api/v1/internal/health")
    assert "application/json" in response.headers.get("content-type", "")
