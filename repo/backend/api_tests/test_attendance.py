"""BE-API: Anomaly flagging, attendance exceptions, proof upload, exception review."""
from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone

import pytest

import json

from .conftest import (
    login,
    make_signing_headers,
    register_device,
    signed_post_json,
    signed_post_multipart,
)

_MINIMAL_PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\nxref\n0 1\n0000000000 65535 f\ntrailer<</Root 1 0 R>>\nstartxref\n9\n%%EOF"


async def _create_profile(client, reviewer_token: str, candidate_user_id) -> str:
    resp = await client.post(
        "/api/v1/candidates",
        params={"user_id": str(candidate_user_id)},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


async def _create_exception(client, cand_token: str, statement="I was ill.") -> str:
    auth = {"Authorization": f"Bearer {cand_token}"}
    device_id, priv = await register_device(client, auth)
    path = "/api/v1/attendance/exceptions"
    body = json.dumps({"candidate_statement": statement}, separators=(",", ":")).encode()
    sign_hdrs = make_signing_headers(priv, "POST", path, body, device_id)
    resp = await client.post(path, headers={**auth, **sign_hdrs, "Content-Type": "application/json"}, content=body)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


async def _upload_proof(client, cand_token: str, exc_id: str) -> None:
    """Upload proof via signed multipart (require_signed_request active after audit-5 B2)."""
    resp = await signed_post_multipart(
        client, cand_token,
        f"/api/v1/attendance/exceptions/{exc_id}/proof",
        _MINIMAL_PDF, "proof.pdf",
    )
    assert resp.status_code == 201, resp.text


@pytest.mark.asyncio
async def test_flag_anomaly(client, seeded_user, seeded_reviewer, seeded_proctor):
    """Proctor creates an attendance anomaly → 201."""
    rev_token = await login(client, seeded_reviewer)
    profile_id = await _create_profile(client, rev_token, seeded_user["id"])

    proctor_token = await login(client, seeded_proctor)
    resp = await client.post(
        "/api/v1/attendance/anomalies",
        headers={"Authorization": f"Bearer {proctor_token}"},
        json={
            "candidate_id": profile_id,
            "anomaly_type": "absent",
            "session_date": datetime.now(timezone.utc).isoformat(),
            "description": "Candidate was not present.",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["anomaly_type"] == "absent"


@pytest.mark.asyncio
async def test_create_exception(client, seeded_user, seeded_reviewer):
    """Candidate creates an attendance exception → 201 with status=pending_proof."""
    rev_token = await login(client, seeded_reviewer)
    await _create_profile(client, rev_token, seeded_user["id"])

    cand_token = await login(client, seeded_user)
    exc_id = await _create_exception(client, cand_token, "I was ill on the exam date.")
    resp = await client.get(
        f"/api/v1/attendance/exceptions/{exc_id}",
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["status"] == "pending_proof"


@pytest.mark.asyncio
async def test_exception_row_scope(client, seeded_user, seeded_reviewer, _install_jwt_keys, test_session_factory):
    """Candidate A cannot see candidate B's exception → 403."""
    from src.persistence.models.auth import User
    from src.security.passwords import hash_password

    # Create candidate B and their profile
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
    # Create profiles for both candidates
    await _create_profile(client, rev_token, seeded_user["id"])
    await _create_profile(client, rev_token, user_b_data["id"])

    # Candidate B creates exception
    token_b = await login(client, user_b_data)
    exc_id = await _create_exception(client, token_b)

    # Candidate A tries to read it → 403
    token_a = await login(client, seeded_user)
    get_resp = await client.get(
        f"/api/v1/attendance/exceptions/{exc_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert get_resp.status_code == 403


@pytest.mark.asyncio
async def test_upload_proof_transitions_status(client, seeded_user, seeded_reviewer, tmp_file_store):
    """After proof upload, exception status becomes pending_initial_review."""
    rev_token = await login(client, seeded_reviewer)
    await _create_profile(client, rev_token, seeded_user["id"])

    cand_token = await login(client, seeded_user)
    exc_id = await _create_exception(client, cand_token)
    await _upload_proof(client, cand_token, exc_id)

    get_resp = await client.get(
        f"/api/v1/attendance/exceptions/{exc_id}",
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert get_resp.json()["data"]["status"] == "pending_initial_review"


@pytest.mark.asyncio
async def test_exception_read_embeds_proof_metadata(
    client, seeded_user, seeded_reviewer, tmp_file_store
):
    """ExceptionRead payload must embed proof metadata so reviewers can
    inspect evidence without a second round-trip. Covers audit-3 High #4.
    """
    rev_token = await login(client, seeded_reviewer)
    await _create_profile(client, rev_token, seeded_user["id"])

    cand_token = await login(client, seeded_user)
    exc_id = await _create_exception(client, cand_token, "Illness with documentation.")
    await _upload_proof(client, cand_token, exc_id)

    get_resp = await client.get(
        f"/api/v1/attendance/exceptions/{exc_id}",
        headers={"Authorization": f"Bearer {rev_token}"},
    )
    assert get_resp.status_code == 200
    body = get_resp.json()["data"]
    assert "proofs" in body, "ExceptionRead must expose 'proofs'"
    assert isinstance(body["proofs"], list)
    assert len(body["proofs"]) == 1
    proof = body["proofs"][0]
    for field in ("id", "exception_id", "document_version_id", "uploaded_by", "uploaded_at"):
        assert field in proof, f"proof metadata missing '{field}'"


@pytest.mark.asyncio
async def test_review_initial_approve(client, seeded_user, seeded_reviewer, seeded_proctor, tmp_file_store):
    """Proctor approves at initial stage → status=approved."""
    rev_token = await login(client, seeded_reviewer)
    await _create_profile(client, rev_token, seeded_user["id"])

    cand_token = await login(client, seeded_user)
    exc_id = await _create_exception(client, cand_token, "Documented illness.")
    await _upload_proof(client, cand_token, exc_id)

    proctor_token = await login(client, seeded_proctor)
    review_resp = await signed_post_json(
        client, proctor_token,
        f"/api/v1/attendance/exceptions/{exc_id}/review",
        {"decision": "approve", "notes": "Valid medical certificate provided."},
    )
    assert review_resp.status_code == 200, review_resp.text

    exc_resp = await client.get(
        f"/api/v1/attendance/exceptions/{exc_id}",
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert exc_resp.json()["data"]["status"] == "approved"


@pytest.mark.asyncio
async def test_review_initial_escalate(client, seeded_user, seeded_reviewer, seeded_proctor, tmp_file_store):
    """Proctor escalates → status=pending_final_review, current_stage=final."""
    rev_token = await login(client, seeded_reviewer)
    await _create_profile(client, rev_token, seeded_user["id"])

    cand_token = await login(client, seeded_user)
    exc_id = await _create_exception(client, cand_token, "Needs further review.")
    await _upload_proof(client, cand_token, exc_id)

    proctor_token = await login(client, seeded_proctor)
    review_resp = await signed_post_json(
        client, proctor_token,
        f"/api/v1/attendance/exceptions/{exc_id}/review",
        {"decision": "escalate", "notes": "Complex case, needs senior review."},
    )
    assert review_resp.status_code == 200

    exc_resp = await client.get(
        f"/api/v1/attendance/exceptions/{exc_id}",
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    data = exc_resp.json()["data"]
    assert data["status"] == "pending_final_review"
    assert data["current_stage"] == "final"


@pytest.mark.asyncio
async def test_review_final_reject(client, seeded_user, seeded_reviewer, seeded_proctor, tmp_file_store):
    """Reviewer rejects at final stage → status=rejected."""
    rev_token = await login(client, seeded_reviewer)
    await _create_profile(client, rev_token, seeded_user["id"])

    cand_token = await login(client, seeded_user)
    exc_id = await _create_exception(client, cand_token, "Exception request.")
    await _upload_proof(client, cand_token, exc_id)

    # Escalate first (signed)
    proctor_token = await login(client, seeded_proctor)
    await signed_post_json(
        client, proctor_token,
        f"/api/v1/attendance/exceptions/{exc_id}/review",
        {"decision": "escalate"},
    )

    # Reviewer rejects at final (signed)
    reject_resp = await signed_post_json(
        client, rev_token,
        f"/api/v1/attendance/exceptions/{exc_id}/review",
        {"decision": "reject", "notes": "Insufficient evidence."},
    )
    assert reject_resp.status_code == 200

    exc_resp = await client.get(
        f"/api/v1/attendance/exceptions/{exc_id}",
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert exc_resp.json()["data"]["status"] == "rejected"


@pytest.mark.asyncio
async def test_exception_searchable_by_status(client, seeded_user, seeded_reviewer, tmp_file_store):
    """List filter status=pending_initial_review returns only exceptions with that status."""
    rev_token = await login(client, seeded_reviewer)
    await _create_profile(client, rev_token, seeded_user["id"])

    cand_token = await login(client, seeded_user)
    exc_id = await _create_exception(client, cand_token, "Awaiting review.")
    await _upload_proof(client, cand_token, exc_id)

    list_resp = await client.get(
        "/api/v1/attendance/exceptions",
        headers={"Authorization": f"Bearer {rev_token}"},
        params={"status": "pending_initial_review"},
    )
    assert list_resp.status_code == 200
    data = list_resp.json()["data"]
    assert all(e["status"] == "pending_initial_review" for e in data)
    assert any(e["id"] == exc_id for e in data)


@pytest.mark.asyncio
async def test_candidate_sees_own_anomaly_by_profile_id(client, seeded_user, seeded_reviewer, seeded_proctor):
    """Candidate lists anomalies and sees only their own (scoped to profile id, not user id)."""
    rev_token = await login(client, seeded_reviewer)
    profile_id = await _create_profile(client, rev_token, seeded_user["id"])

    proctor_token = await login(client, seeded_proctor)
    anomaly_resp = await client.post(
        "/api/v1/attendance/anomalies",
        headers={"Authorization": f"Bearer {proctor_token}"},
        json={
            "candidate_id": profile_id,
            "anomaly_type": "absent",
            "session_date": datetime.now(timezone.utc).isoformat(),
            "description": "Candidate was not present.",
        },
    )
    assert anomaly_resp.status_code == 201
    anomaly_id = anomaly_resp.json()["data"]["id"]

    cand_token = await login(client, seeded_user)
    list_resp = await client.get(
        "/api/v1/attendance/anomalies",
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert list_resp.status_code == 200
    ids = [a["id"] for a in list_resp.json()["data"]]
    assert anomaly_id in ids


@pytest.mark.asyncio
async def test_candidate_exception_access_own(client, seeded_user, seeded_reviewer, tmp_file_store):
    """Candidate can read and upload proof for their own exception (profile-aware ownership)."""
    rev_token = await login(client, seeded_reviewer)
    await _create_profile(client, rev_token, seeded_user["id"])

    cand_token = await login(client, seeded_user)
    exc_id = await _create_exception(client, cand_token)

    # Candidate reads own exception → 200
    get_resp = await client.get(
        f"/api/v1/attendance/exceptions/{exc_id}",
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["status"] == "pending_proof"

    # Candidate uploads proof → 201
    await _upload_proof(client, cand_token, exc_id)
    get_resp2 = await client.get(
        f"/api/v1/attendance/exceptions/{exc_id}",
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert get_resp2.status_code == 200
    assert get_resp2.json()["data"]["status"] == "pending_initial_review"
