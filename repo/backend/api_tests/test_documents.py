"""BE-API: Document upload, review, download."""
from __future__ import annotations

import hashlib
import io
import uuid

import pytest

from .conftest import build_multipart, login, make_signing_headers, register_device

_MINIMAL_PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\nxref\n0 1\n0000000000 65535 f\ntrailer<</Root 1 0 R>>\nstartxref\n9\n%%EOF"
_MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n"
    + b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    + b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
    + b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


async def _do_upload(client, cand_token: str, profile_id: str, file_bytes: bytes, filename: str, mime: str = "application/pdf"):
    """Upload a document with ECDSA signing. Returns the response."""
    auth = {"Authorization": f"Bearer {cand_token}"}
    device_id, priv = await register_device(client, auth)
    path = f"/api/v1/candidates/{profile_id}/documents/upload"
    body_bytes, content_type = build_multipart(file_bytes, filename, mime)
    sign_hdrs = make_signing_headers(priv, "POST", path, b"", device_id)
    return await client.post(path, headers={**auth, **sign_hdrs, "Content-Type": content_type}, content=body_bytes)


async def _create_candidate_profile(client, reviewer_token: str, candidate_user_id: uuid.UUID) -> str:
    resp = await client.post(
        "/api/v1/candidates",
        params={"user_id": str(candidate_user_id)},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert resp.status_code == 201
    return resp.json()["data"]["id"]


@pytest.mark.asyncio
async def test_upload_valid_pdf(client, seeded_user, seeded_reviewer, tmp_file_store):
    rev_token = await login(client, seeded_reviewer)
    profile_id = await _create_candidate_profile(client, rev_token, seeded_user["id"])

    cand_token = await login(client, seeded_user)
    resp = await _do_upload(client, cand_token, profile_id, _MINIMAL_PDF, "test.pdf")
    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["sha256_hash"] == hashlib.sha256(_MINIMAL_PDF).hexdigest()
    assert body["data"]["version_number"] == 1


@pytest.mark.asyncio
async def test_upload_wrong_mime(client, seeded_user, seeded_reviewer, tmp_file_store):
    rev_token = await login(client, seeded_reviewer)
    profile_id = await _create_candidate_profile(client, rev_token, seeded_user["id"])

    cand_token = await login(client, seeded_user)
    resp = await _do_upload(client, cand_token, profile_id, b"PK\x03\x04", "bad.zip", "application/zip")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "POLICY_VIOLATION"


@pytest.mark.asyncio
async def test_upload_too_large(client, seeded_user, seeded_reviewer, tmp_file_store):
    rev_token = await login(client, seeded_reviewer)
    profile_id = await _create_candidate_profile(client, rev_token, seeded_user["id"])

    big_data = b"A" * (25 * 1024 * 1024 + 1)
    cand_token = await login(client, seeded_user)
    resp = await _do_upload(client, cand_token, profile_id, big_data, "big.pdf")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "POLICY_VIOLATION"


@pytest.mark.asyncio
async def test_resubmission_increments_version(client, seeded_user, seeded_reviewer, tmp_file_store):
    rev_token = await login(client, seeded_reviewer)
    profile_id = await _create_candidate_profile(client, rev_token, seeded_user["id"])

    cand_token = await login(client, seeded_user)

    r1 = await _do_upload(client, cand_token, profile_id, _MINIMAL_PDF, "doc.pdf")
    assert r1.status_code == 201
    assert r1.json()["data"]["version_number"] == 1

    r2 = await _do_upload(client, cand_token, profile_id, _MINIMAL_PDF + b" ", "doc_v2.pdf")
    assert r2.status_code == 201
    assert r2.json()["data"]["version_number"] == 2


@pytest.mark.asyncio
async def test_review_approve(client, seeded_user, seeded_reviewer, tmp_file_store):
    rev_token = await login(client, seeded_reviewer)
    rev_headers = {"Authorization": f"Bearer {rev_token}"}
    profile_id = await _create_candidate_profile(client, rev_token, seeded_user["id"])

    cand_token = await login(client, seeded_user)
    up = await _do_upload(client, cand_token, profile_id, _MINIMAL_PDF, "doc.pdf")
    assert up.status_code == 201
    doc_id = up.json()["data"]["document_id"]
    version_id = up.json()["data"]["version_number"]

    # Get the version UUID from the document
    doc_resp = await client.get(
        f"/api/v1/candidates/{profile_id}/documents/{doc_id}",
        headers=rev_headers,
    )
    assert doc_resp.status_code == 200
    version_uuid = doc_resp.json()["data"]["latest_version"]["id"]

    review = await client.post(
        f"/api/v1/documents/{doc_id}/review",
        headers=rev_headers,
        json={"version_id": version_uuid, "status": "approved"},
    )
    assert review.status_code == 200
    assert review.json()["data"]["status"] == "approved"


@pytest.mark.asyncio
async def test_review_needs_resubmission_without_reason(client, seeded_user, seeded_reviewer, tmp_file_store):
    rev_token = await login(client, seeded_reviewer)
    rev_headers = {"Authorization": f"Bearer {rev_token}"}
    profile_id = await _create_candidate_profile(client, rev_token, seeded_user["id"])

    cand_token = await login(client, seeded_user)
    up = await _do_upload(client, cand_token, profile_id, _MINIMAL_PDF, "doc.pdf")
    doc_id = up.json()["data"]["document_id"]
    doc_resp = await client.get(
        f"/api/v1/candidates/{profile_id}/documents/{doc_id}",
        headers=rev_headers,
    )
    version_uuid = doc_resp.json()["data"]["latest_version"]["id"]

    review = await client.post(
        f"/api/v1/documents/{doc_id}/review",
        headers=rev_headers,
        json={"version_id": version_uuid, "status": "needs_resubmission"},
    )
    assert review.status_code == 422


@pytest.mark.asyncio
async def test_review_needs_resubmission_with_reason(client, seeded_user, seeded_reviewer, tmp_file_store):
    rev_token = await login(client, seeded_reviewer)
    rev_headers = {"Authorization": f"Bearer {rev_token}"}
    profile_id = await _create_candidate_profile(client, rev_token, seeded_user["id"])

    cand_token = await login(client, seeded_user)
    up = await _do_upload(client, cand_token, profile_id, _MINIMAL_PDF, "doc.pdf")
    doc_id = up.json()["data"]["document_id"]
    doc_resp = await client.get(
        f"/api/v1/candidates/{profile_id}/documents/{doc_id}",
        headers=rev_headers,
    )
    version_uuid = doc_resp.json()["data"]["latest_version"]["id"]

    review = await client.post(
        f"/api/v1/documents/{doc_id}/review",
        headers=rev_headers,
        json={
            "version_id": version_uuid,
            "status": "needs_resubmission",
            "resubmission_reason": "Please provide a notarized copy.",
        },
    )
    assert review.status_code == 200
    assert review.json()["data"]["status"] == "needs_resubmission"


@pytest.mark.asyncio
async def test_download_candidate_forbidden(client, seeded_user, seeded_reviewer, tmp_file_store):
    rev_token = await login(client, seeded_reviewer)
    profile_id = await _create_candidate_profile(client, rev_token, seeded_user["id"])

    cand_token = await login(client, seeded_user)
    up = await _do_upload(client, cand_token, profile_id, _MINIMAL_PDF, "doc.pdf")
    assert up.status_code == 201
    doc_id = up.json()["data"]["document_id"]

    download = await client.get(
        f"/api/v1/documents/{doc_id}/download",
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert download.status_code == 403


@pytest.mark.asyncio
async def test_download_reviewer_allowed(client, seeded_user, seeded_reviewer, tmp_file_store):
    rev_token = await login(client, seeded_reviewer)
    rev_headers = {"Authorization": f"Bearer {rev_token}"}
    profile_id = await _create_candidate_profile(client, rev_token, seeded_user["id"])

    cand_token = await login(client, seeded_user)
    up = await _do_upload(client, cand_token, profile_id, _MINIMAL_PDF, "doc.pdf")
    assert up.status_code == 201
    doc_id = up.json()["data"]["document_id"]

    download = await client.get(
        f"/api/v1/documents/{doc_id}/download",
        headers=rev_headers,
    )
    assert download.status_code == 200
    assert "Content-Disposition" in download.headers
    assert "attachment" in download.headers["Content-Disposition"]
    assert len(download.content) > 0
    # X-File-Hash is SHA-256 of the bytes served (post-watermark for PDFs)
    # per docs/api-spec.md. Clients can verify integrity from the header.
    assert "X-File-Hash" in download.headers or "x-file-hash" in download.headers
    served_hash = download.headers.get("X-File-Hash") or download.headers.get("x-file-hash")
    assert served_hash is not None and len(served_hash) == 64
    import hashlib as _hashlib
    assert served_hash == _hashlib.sha256(download.content).hexdigest()


@pytest.mark.asyncio
async def test_list_documents_cross_user_forbidden(
    client, seeded_user, seeded_reviewer, _install_jwt_keys, test_session_factory
):
    """Candidate B cannot list Candidate A's documents → 403."""
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
    profile_a_id = await _create_candidate_profile(client, rev_token, seeded_user["id"])
    await _create_candidate_profile(client, rev_token, user_b_data["id"])

    cand_b_token = await login(client, user_b_data)
    resp = await client.get(
        f"/api/v1/candidates/{profile_a_id}/documents",
        headers={"Authorization": f"Bearer {cand_b_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_document_read_includes_requirement_code_when_bound(
    client, seeded_user, seeded_reviewer, tmp_file_store, test_session_factory
):
    """DocumentRead surfaces requirement_code when the document is bound to a
    DocumentRequirement. FE uses this to render the checklist / doc-table
    without a separate requirements lookup per row.
    """
    from src.persistence.models.document import Document, DocumentRequirement

    rev_token = await login(client, seeded_reviewer)
    profile_id = await _create_candidate_profile(client, rev_token, seeded_user["id"])

    async with test_session_factory() as session:
        req = DocumentRequirement(
            requirement_code="TRANSCRIPT_B1",
            display_name="Official Transcript",
            description=None,
            is_mandatory=True,
            allowed_mime_types=["application/pdf"],
            max_size_bytes=25 * 1024 * 1024,
            is_active=True,
        )
        session.add(req)
        await session.flush()
        doc = Document(
            candidate_id=uuid.UUID(profile_id),
            requirement_id=req.id,
            document_type="transcript",
            current_version=0,
            current_status="pending_review",
        )
        session.add(doc)
        await session.commit()

    cand_token = await login(client, seeded_user)
    listing = await client.get(
        f"/api/v1/candidates/{profile_id}/documents",
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert listing.status_code == 200
    rows = listing.json()["data"]
    bound = [r for r in rows if r["requirement_id"] is not None]
    assert len(bound) == 1
    assert bound[0]["requirement_code"] == "TRANSCRIPT_B1"


@pytest.mark.asyncio
async def test_document_read_requirement_code_null_when_unbound(
    client, seeded_user, seeded_reviewer, tmp_file_store
):
    """DocumentRead.requirement_code is null when requirement_id is null."""
    rev_token = await login(client, seeded_reviewer)
    profile_id = await _create_candidate_profile(client, rev_token, seeded_user["id"])

    cand_token = await login(client, seeded_user)
    resp = await _do_upload(client, cand_token, profile_id, _MINIMAL_PDF, "unbound.pdf")
    assert resp.status_code == 201

    listing = await client.get(
        f"/api/v1/candidates/{profile_id}/documents",
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert listing.status_code == 200
    rows = listing.json()["data"]
    assert len(rows) == 1
    assert rows[0]["requirement_id"] is None
    assert rows[0]["requirement_code"] is None


@pytest.mark.asyncio
async def test_upload_cross_user_forbidden(
    client, seeded_user, seeded_reviewer, _install_jwt_keys, tmp_file_store, test_session_factory
):
    """Candidate B cannot upload documents to Candidate A's profile → 403."""
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
    profile_a_id = await _create_candidate_profile(client, rev_token, seeded_user["id"])
    await _create_candidate_profile(client, rev_token, user_b_data["id"])

    cand_b_token = await login(client, user_b_data)
    resp = await _do_upload(client, cand_b_token, profile_a_id, _MINIMAL_PDF, "doc.pdf")
    assert resp.status_code == 403
