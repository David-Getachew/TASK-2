"""
Shared fixtures for backend API tests.

Targets the real Postgres database configured via DATABASE_URL, with no
FastAPI dependency overrides. Route handlers run against the same async
engine the production app wires at import — `get_db` is the real one,
so tests exercise the full production DB path (asyncpg + Postgres types,
row-level uniqueness, server-side defaults, JSONB, UUID).

Schema is created once per pytest session via `Base.metadata.create_all`
against a sync psycopg2 engine. Each test truncates all public tables
before running for isolation. The app's async engine is reconfigured to
use `NullPool` so asyncpg connections don't cross pytest-asyncio's
per-test event loop boundaries.
"""
from __future__ import annotations

import base64
import hashlib
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator

import pytest
import pytest_asyncio
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


@pytest.fixture(autouse=True)
def _patch_env(monkeypatch):
    # DATABASE_URL is expected to be set externally (run_tests.sh / docker env)
    # so src.persistence.database binds the real Postgres engine at import.
    monkeypatch.setenv("SECRET_KEY", "a" * 32)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("KEK_CURRENT_VERSION", "v1")


def pytest_configure(config):
    """One-shot session setup: create schema, reconfigure engine to NullPool."""
    # Force-import all models so Base.metadata contains every table.
    from src.persistence.models import (  # noqa: F401
        attendance,
        auth,
        candidate,
        config_audit,
        document,
        idempotency,
        order,
    )
    from src.persistence.models.base import Base
    from src.config import get_settings

    settings = get_settings()
    sync_url = settings.database_url
    if "+asyncpg" in sync_url:
        sync_url = sync_url.replace("+asyncpg", "+psycopg2")
    sync_engine = create_engine(sync_url, future=True)
    try:
        Base.metadata.create_all(sync_engine)
    finally:
        sync_engine.dispose()

    # Swap the app's async engine to NullPool. asyncpg connections are
    # bound to the event loop that created them; pytest-asyncio gives each
    # test a fresh loop, so a pooled connection from a previous test would
    # raise "attached to a different loop" when reused.
    import src.persistence.database as db_mod
    new_engine = create_async_engine(db_mod._async_url, poolclass=NullPool)
    db_mod.engine = new_engine
    db_mod.AsyncSessionLocal = async_sessionmaker(
        new_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )


async def _truncate_all(engine) -> None:
    async with engine.begin() as conn:
        def _names(sync_conn):
            from sqlalchemy import inspect
            return inspect(sync_conn).get_table_names()
        names = await conn.run_sync(_names)
        names = [n for n in names if n != "alembic_version"]
        if not names:
            return
        rendered = ", ".join(f'"{n}"' for n in names)
        await conn.execute(text(f"TRUNCATE TABLE {rendered} RESTART IDENTITY CASCADE"))


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables():
    from src.persistence.database import engine
    await _truncate_all(engine)
    yield


@pytest_asyncio.fixture
async def test_engine():
    from src.persistence.database import engine
    yield engine


@pytest_asyncio.fixture
async def test_session_factory():
    """Return the app's session factory so test seed-data and app routes
    share one engine/database."""
    from src.persistence.database import AsyncSessionLocal
    return AsyncSessionLocal


@pytest_asyncio.fixture
async def db_session(test_session_factory) -> AsyncIterator[AsyncSession]:
    async with test_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(_install_jwt_keys, _install_kek):
    """Test HTTP client — real get_db, real Postgres, no overrides."""
    from src.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest_asyncio.fixture
async def client_raw(_install_jwt_keys, _install_kek):
    """Alias of `client` — kept for signed-route rejection-test naming."""
    from src.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest.fixture
def _install_jwt_keys():
    from src.security import jwt as jwt_mod

    priv, pub = jwt_mod.generate_dev_keypair()
    jwt_mod.install_keys(priv, pub)
    yield
    jwt_mod.install_keys(None, None)  # type: ignore[arg-type]


@pytest.fixture
def _install_kek():
    import os

    from src.security import encryption

    encryption.install_kek("v1", os.urandom(32))
    yield
    encryption.clear_kek_overrides()


async def _create_user(test_session_factory, role: str, full_name: str) -> dict:
    from src.persistence.models.auth import User
    from src.security.passwords import hash_password

    password = "correct horse battery staple"
    username = f"{role}-{uuid.uuid4().hex[:8]}"
    async with test_session_factory() as session:
        user = User(
            username=username,
            password_hash=hash_password(password),
            role=role,
            full_name=full_name,
            is_active=True,
            is_locked=False,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return {"id": user.id, "username": username, "password": password, "role": role}


@pytest_asyncio.fixture
async def seeded_user(test_session_factory, _install_jwt_keys):
    """Create a candidate user with a known password and return (user_id, username, password)."""
    return await _create_user(test_session_factory, "candidate", "Alice Example")


@pytest_asyncio.fixture
async def seeded_reviewer(test_session_factory, _install_jwt_keys):
    """Create a reviewer user."""
    return await _create_user(test_session_factory, "reviewer", "Bob Reviewer")


@pytest_asyncio.fixture
async def seeded_admin(test_session_factory, _install_jwt_keys):
    """Create an admin user."""
    return await _create_user(test_session_factory, "admin", "Carol Admin")


@pytest_asyncio.fixture
async def seeded_proctor(test_session_factory, _install_jwt_keys):
    """Create a proctor user."""
    return await _create_user(test_session_factory, "proctor", "Dave Proctor")


def make_signing_headers(priv, method: str, path: str, body_bytes: bytes, device_id: str) -> dict:
    """Build ECDSA signing headers for a single request."""
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    nonce = f"n-{uuid.uuid4().hex}"
    body_hash = hashlib.sha256(body_bytes).hexdigest()
    canonical = "\n".join([method.upper(), path, timestamp, nonce, device_id, body_hash]) + "\n"
    sig = base64.b64encode(
        priv.sign(canonical.encode("utf-8"), ec.ECDSA(hashes.SHA256()))
    ).decode()
    return {"X-Timestamp": timestamp, "X-Nonce": nonce, "X-Device-ID": device_id, "X-Request-Signature": sig}


async def register_device(client, auth_headers: dict):
    """Register a new ECDSA device key and return (device_id, priv_key)."""
    priv = ec.generate_private_key(ec.SECP256R1())
    pub_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    resp = await client.post(
        "/api/v1/auth/device/register",
        headers=auth_headers,
        json={"device_fingerprint": f"fp-{uuid.uuid4().hex[:16]}", "public_key_pem": pub_pem, "label": "test"},
    )
    assert resp.status_code == 200, f"Device registration failed: {resp.text}"
    return resp.json()["data"]["device_id"], priv


async def signed_post_json(
    client, token: str, path: str, body_dict: dict | None = None, *, device: tuple | None = None
):
    """Helper: POST a signed JSON body to `path` authed with `token`.

    Reuses a caller-provided (device_id, priv) tuple when supplied — lets a test
    reuse one device across multiple signed calls instead of re-registering per call.

    Canonical form: METHOD\\nPATH\\nX-Timestamp\\nX-Nonce\\nX-Device-ID\\nsha256(body)\\n
    (see src/security/signing.py::build_canonical_string). The body is serialized
    with compact separators because `require_signed_request` re-reads the raw
    request body bytes and recomputes the SHA-256.
    """
    import json as _json

    auth = {"Authorization": f"Bearer {token}"}
    if device is None:
        device_id, priv = await register_device(client, auth)
    else:
        device_id, priv = device
    body_bytes = (
        _json.dumps(body_dict, separators=(",", ":")).encode() if body_dict is not None else b""
    )
    headers = make_signing_headers(priv, "POST", path, body_bytes, device_id)
    return await client.post(
        path,
        headers={**auth, **headers, "Content-Type": "application/json"},
        content=body_bytes,
    )


async def signed_post_params(
    client, token: str, path: str, params: dict, *, device: tuple | None = None
):
    """POST with query params (no body) — sign an empty body. Used for resolve_after_sales."""
    from urllib.parse import urlencode

    auth = {"Authorization": f"Bearer {token}"}
    if device is None:
        device_id, priv = await register_device(client, auth)
    else:
        device_id, priv = device
    body_bytes = b""
    # Path stored in canonical form does NOT include query string (see request.url.path).
    headers = make_signing_headers(priv, "POST", path, body_bytes, device_id)
    url = f"{path}?{urlencode(params)}"
    return await client.post(url, headers={**auth, **headers})


async def signed_post_multipart(
    client,
    token: str,
    path: str,
    file_bytes: bytes,
    filename: str,
    *,
    content_type: str = "application/pdf",
    device: tuple | None = None,
):
    """POST multipart/form-data (single 'file' field) with canonical signing."""
    auth = {"Authorization": f"Bearer {token}"}
    if device is None:
        device_id, priv = await register_device(client, auth)
    else:
        device_id, priv = device
    body, ct = build_multipart(file_bytes, filename, file_content_type=content_type)
    headers = make_signing_headers(priv, "POST", path, b"", device_id)
    return await client.post(
        path,
        headers={**auth, **headers, "Content-Type": ct},
        content=body,
    )


def build_multipart(file_bytes: bytes, filename: str, file_content_type: str = "application/pdf") -> tuple[bytes, str]:
    """Build a minimal multipart/form-data body for file upload signing."""
    boundary = b"btest" + uuid.uuid4().hex[:12].encode()
    body = (
        b"--" + boundary + b"\r\n"
        + f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
        + f"Content-Type: {file_content_type}\r\n".encode()
        + b"\r\n"
        + file_bytes
        + b"\r\n--" + boundary + b"--\r\n"
    )
    return body, f"multipart/form-data; boundary={boundary.decode()}"


async def login(client, user: dict) -> str:
    """Login and return access token."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "username": user["username"],
            "password": user["password"],
            "nonce": f"n-{uuid.uuid4().hex}",
            "timestamp": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["data"]["access_token"]


@pytest.fixture
def tmp_file_store(tmp_path):
    """Install a temp-directory FileStore for document upload tests."""
    from src.storage.file_store import FileStore, install_file_store

    store = FileStore(str(tmp_path))
    install_file_store(store)
    yield store
    install_file_store(None)  # type: ignore[arg-type]
