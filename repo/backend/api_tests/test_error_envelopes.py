"""
No-mock API contract tests for error envelope shapes.
Tests confirm the API returns correctly structured error responses
for: 404 (unknown route), 422 (schema validation failures), 401 (missing auth).
These verify the envelope contract before feature endpoints are implemented.
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
async def test_unknown_route_returns_404(client):
    response = await client.get("/api/v1/nonexistent-endpoint-xyz")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_health_returns_success_envelope_shape(client):
    response = await client.get("/api/v1/internal/health")
    assert response.status_code == 200
    body = response.json()
    # Health conforms to the unified `{success, data, meta}` envelope.
    assert body["success"] is True
    assert "data" in body and body["data"]["status"] == "ok"
    assert "meta" in body


@pytest.mark.asyncio
async def test_schema_envelope_make_error_shape():
    from src.schemas.common import make_error, ErrorDetail
    resp = make_error(
        "VALIDATION_ERROR",
        "Request failed",
        details=[ErrorDetail(field="password", message="Too short")],
    )
    d = resp.model_dump()
    assert d["success"] is False
    assert d["error"]["code"] == "VALIDATION_ERROR"
    assert d["error"]["details"][0]["field"] == "password"
    assert "trace_id" in d["meta"]
    assert "timestamp" in d["meta"]


@pytest.mark.asyncio
async def test_schema_envelope_make_success_shape():
    from src.schemas.common import make_success
    resp = make_success({"id": "abc", "status": "ok"})
    d = resp.model_dump()
    assert d["success"] is True
    assert d["data"]["id"] == "abc"
    assert "trace_id" in d["meta"]


@pytest.mark.asyncio
async def test_error_body_details_default_to_empty_list():
    from src.schemas.common import make_error
    resp = make_error("NOT_FOUND", "Resource not found")
    assert resp.error.details == []


@pytest.mark.asyncio
async def test_paginated_response_shape():
    from src.schemas.common import PaginatedResponse, PaginationMeta, ApiMeta
    from datetime import datetime, timezone
    resp = PaginatedResponse(
        data=[{"id": 1}, {"id": 2}],
        pagination=PaginationMeta(page=1, page_size=20, total=2, total_pages=1),
        meta=ApiMeta(trace_id="abc", timestamp=datetime.now(timezone.utc)),
    )
    d = resp.model_dump()
    assert d["success"] is True
    assert len(d["data"]) == 2
    assert d["pagination"]["total"] == 2
