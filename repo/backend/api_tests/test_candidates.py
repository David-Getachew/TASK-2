"""BE-API: Candidate profile, exam scores, transfer preferences, checklist."""
from __future__ import annotations

import uuid

import pytest

from .conftest import login


@pytest.mark.asyncio
async def test_create_profile_candidate(client, seeded_user, seeded_reviewer):
    """Reviewer creates a profile for a candidate user → 201."""
    token = await login(client, seeded_reviewer)
    resp = await client.post(
        "/api/v1/candidates",
        params={"user_id": str(seeded_user["id"])},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["user_id"] == str(seeded_user["id"])


@pytest.mark.asyncio
async def test_create_profile_duplicate(client, seeded_user, seeded_reviewer):
    """Creating a second profile for the same user → 409 BUSINESS_RULE_VIOLATION."""
    token = await login(client, seeded_reviewer)
    headers = {"Authorization": f"Bearer {token}"}
    params = {"user_id": str(seeded_user["id"])}
    first = await client.post("/api/v1/candidates", params=params, headers=headers)
    assert first.status_code == 201
    second = await client.post("/api/v1/candidates", params=params, headers=headers)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


@pytest.mark.asyncio
async def test_get_profile_row_scoped(client, seeded_user, seeded_reviewer, test_session_factory):
    """Candidate A cannot read candidate B's profile → 403."""
    from src.persistence.models.auth import User
    from src.security.passwords import hash_password

    # Create second candidate in DB
    async with test_session_factory() as session:
        user_b = User(
            username=f"bob-{uuid.uuid4().hex[:8]}",
            password_hash=hash_password("correct horse battery staple"),
            role="candidate",
            full_name="Bob Other",
            is_active=True,
            is_locked=False,
        )
        session.add(user_b)
        await session.commit()
        await session.refresh(user_b)
        user_b_id = user_b.id

    rev_token = await login(client, seeded_reviewer)
    rev_headers = {"Authorization": f"Bearer {rev_token}"}

    # Reviewer creates profile for user_b
    create_resp = await client.post(
        "/api/v1/candidates",
        params={"user_id": str(user_b_id)},
        headers=rev_headers,
    )
    assert create_resp.status_code == 201
    profile_b_id = create_resp.json()["data"]["id"]

    # Candidate A (seeded_user) tries to read user_b's profile → 403
    cand_token = await login(client, seeded_user)
    resp = await client.get(
        f"/api/v1/candidates/{profile_b_id}",
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_profile_writes_history(client, seeded_user, seeded_reviewer):
    """PATCH profile → 200 (history is written server-side)."""
    rev_token = await login(client, seeded_reviewer)
    rev_headers = {"Authorization": f"Bearer {rev_token}"}

    create_resp = await client.post(
        "/api/v1/candidates",
        params={"user_id": str(seeded_user["id"])},
        headers=rev_headers,
    )
    assert create_resp.status_code == 201
    profile_id = create_resp.json()["data"]["id"]

    # PATCH as reviewer
    patch_resp = await client.patch(
        f"/api/v1/candidates/{profile_id}",
        json={"preferred_name": "Alice Updated", "program_code": "CS-2026"},
        headers=rev_headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["data"]["preferred_name"] == "Alice Updated"


@pytest.mark.asyncio
async def test_add_exam_score(client, seeded_user, seeded_reviewer):
    """Reviewer adds exam score for candidate → 201."""
    rev_token = await login(client, seeded_reviewer)
    rev_headers = {"Authorization": f"Bearer {rev_token}"}

    create_resp = await client.post(
        "/api/v1/candidates",
        params={"user_id": str(seeded_user["id"])},
        headers=rev_headers,
    )
    assert create_resp.status_code == 201
    profile_id = create_resp.json()["data"]["id"]

    score_resp = await client.post(
        f"/api/v1/candidates/{profile_id}/exam-scores",
        json={
            "subject_code": "MATH101",
            "subject_name": "Calculus I",
            "score": "95",
            "max_score": "100",
        },
        headers=rev_headers,
    )
    assert score_resp.status_code == 201
    assert score_resp.json()["data"]["subject_code"] == "MATH101"


@pytest.mark.asyncio
async def test_get_exam_scores(client, seeded_user, seeded_reviewer):
    """GET exam-scores returns list including a previously added score."""
    rev_token = await login(client, seeded_reviewer)
    rev_headers = {"Authorization": f"Bearer {rev_token}"}

    create_resp = await client.post(
        "/api/v1/candidates",
        params={"user_id": str(seeded_user["id"])},
        headers=rev_headers,
    )
    assert create_resp.status_code == 201
    profile_id = create_resp.json()["data"]["id"]

    await client.post(
        f"/api/v1/candidates/{profile_id}/exam-scores",
        json={"subject_code": "ENG201", "subject_name": "English Lit", "score": "88", "max_score": "100"},
        headers=rev_headers,
    )

    get_resp = await client.get(
        f"/api/v1/candidates/{profile_id}/exam-scores",
        headers=rev_headers,
    )
    assert get_resp.status_code == 200
    scores = get_resp.json()["data"]
    assert any(s["subject_code"] == "ENG201" for s in scores)


@pytest.mark.asyncio
async def test_checklist_returns_items(client, seeded_user, seeded_reviewer):
    """Checklist endpoint returns list (empty when no requirements seeded)."""
    rev_token = await login(client, seeded_reviewer)
    rev_headers = {"Authorization": f"Bearer {rev_token}"}

    create_resp = await client.post(
        "/api/v1/candidates",
        params={"user_id": str(seeded_user["id"])},
        headers=rev_headers,
    )
    assert create_resp.status_code == 201
    profile_id = create_resp.json()["data"]["id"]

    checklist_resp = await client.get(
        f"/api/v1/candidates/{profile_id}/checklist",
        headers=rev_headers,
    )
    assert checklist_resp.status_code == 200
    body = checklist_resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)


@pytest.mark.asyncio
async def test_list_candidates_reviewer_ok(client, seeded_reviewer, seeded_user):
    """Reviewer can list all candidate profiles → 200, paginated response."""
    rev_token = await login(client, seeded_reviewer)
    rev_headers = {"Authorization": f"Bearer {rev_token}"}

    # Seed one profile so the list is non-trivially testable
    await client.post(
        "/api/v1/candidates",
        params={"user_id": str(seeded_user["id"])},
        headers=rev_headers,
    )

    resp = await client.get("/api/v1/candidates", headers=rev_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)
    assert "pagination" in body
    assert body["pagination"]["total"] >= 1


@pytest.mark.asyncio
async def test_list_candidates_candidate_forbidden(client, seeded_user):
    """Candidate role cannot list all profiles → 403."""
    from .conftest import login
    token = await login(client, seeded_user)
    resp = await client.get(
        "/api/v1/candidates",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_candidate_self_profile_init(client, seeded_user):
    """Candidate can bootstrap their own profile via POST /candidates/self → 201."""
    token = await login(client, seeded_user)
    resp = await client.post(
        "/api/v1/candidates/self",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["user_id"] == str(seeded_user["id"])


@pytest.mark.asyncio
async def test_candidate_self_profile_idempotent(client, seeded_user):
    """Re-calling POST /candidates/self returns the existing profile, not 409."""
    token = await login(client, seeded_user)
    first = await client.post(
        "/api/v1/candidates/self",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first.status_code == 201
    profile_id = first.json()["data"]["id"]

    second = await client.post(
        "/api/v1/candidates/self",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second.status_code == 201, second.text
    assert second.json()["data"]["id"] == profile_id


@pytest.mark.asyncio
async def test_candidate_self_profile_forbidden_for_reviewer(client, seeded_reviewer):
    """Non-candidate roles cannot use the self-init endpoint → 403."""
    token = await login(client, seeded_reviewer)
    resp = await client.post(
        "/api/v1/candidates/self",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_transfer_preferences_create_and_list(client, seeded_user, seeded_reviewer):
    """POST then GET transfer-preferences roundtrip for a candidate profile."""
    rev_token = await login(client, seeded_reviewer)
    create_resp = await client.post(
        "/api/v1/candidates",
        params={"user_id": str(seeded_user["id"])},
        headers={"Authorization": f"Bearer {rev_token}"},
    )
    assert create_resp.status_code == 201
    candidate_id = create_resp.json()["data"]["id"]

    cand_token = await login(client, seeded_user)
    auth = {"Authorization": f"Bearer {cand_token}"}

    post_resp = await client.post(
        f"/api/v1/candidates/{candidate_id}/transfer-preferences",
        headers=auth,
        json={"institution_name": "State University", "program_code": "CS101", "priority_rank": 1},
    )
    assert post_resp.status_code == 201, post_resp.text
    pref = post_resp.json()["data"]
    assert pref["institution_name"] == "State University"

    list_resp = await client.get(
        f"/api/v1/candidates/{candidate_id}/transfer-preferences",
        headers=auth,
    )
    assert list_resp.status_code == 200
    items = list_resp.json()["data"]
    assert any(p["institution_name"] == "State University" for p in items)


@pytest.mark.asyncio
async def test_transfer_preferences_update(client, seeded_user, seeded_reviewer):
    """PATCH transfer-preference updates institution name."""
    rev_token = await login(client, seeded_reviewer)
    create_resp = await client.post(
        "/api/v1/candidates",
        params={"user_id": str(seeded_user["id"])},
        headers={"Authorization": f"Bearer {rev_token}"},
    )
    candidate_id = create_resp.json()["data"]["id"]

    cand_token = await login(client, seeded_user)
    auth = {"Authorization": f"Bearer {cand_token}"}

    post_resp = await client.post(
        f"/api/v1/candidates/{candidate_id}/transfer-preferences",
        headers=auth,
        json={"institution_name": "Old College", "priority_rank": 1},
    )
    assert post_resp.status_code == 201
    pref_id = post_resp.json()["data"]["id"]

    patch_resp = await client.patch(
        f"/api/v1/candidates/{candidate_id}/transfer-preferences/{pref_id}",
        headers=auth,
        json={"institution_name": "New University"},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    assert patch_resp.json()["data"]["institution_name"] == "New University"
