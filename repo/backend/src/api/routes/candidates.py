from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from ...domain.enums import UserRole
from ...persistence.models.candidate import CandidateProfile, ExamScore, TransferPreference
from ...schemas.candidate import (
    CandidateProfileRead,
    CandidateProfileUpdate,
    ExamScoreCreate,
    ExamScoreRead,
    TransferPreferenceCreate,
    TransferPreferenceRead,
    TransferPreferenceUpdate,
)
from ...schemas.common import PaginatedResponse, PaginationMeta, SuccessResponse, make_success, ApiMeta
from ...schemas.document import ChecklistItemRead
from ...security.data_masking import is_privileged
from ...security.errors import ResourceNotFoundError
from ...services.candidate_service import CandidateService
from ...services.document_service import DocumentService
from ...storage.file_store import get_file_store
from ..dependencies import CurrentActor, CurrentUser, DbSession, require_role

router = APIRouter(prefix="/candidates", tags=["candidates"])


def _profile_to_read(profile: CandidateProfile, privileged: bool) -> CandidateProfileRead:
    from ...security.encryption import decrypt_field

    def _try_decrypt(enc: bytes | None, ver: str | None) -> str | None:
        if enc is None:
            return None
        try:
            return decrypt_field(enc, ver, profile.id.bytes)
        except Exception:
            return None

    ssn_raw = _try_decrypt(profile.ssn_encrypted, profile.ssn_key_version)
    dob_raw = _try_decrypt(profile.date_of_birth_encrypted, profile.dob_key_version)
    phone_raw = _try_decrypt(profile.contact_phone_encrypted, profile.phone_key_version)
    email_raw = _try_decrypt(profile.contact_email_encrypted, profile.email_key_version)

    if privileged:
        ssn_disp = ssn_raw
        dob_disp = dob_raw
        phone_disp = phone_raw
        email_disp = email_raw
    else:
        from ...schemas.candidate import _mask_ssn, _mask_dob, _mask_phone, _mask_email
        ssn_disp = _mask_ssn(ssn_raw)
        dob_disp = _mask_dob(dob_raw)
        phone_disp = _mask_phone(phone_raw)
        email_disp = _mask_email(email_raw)

    return CandidateProfileRead(
        id=profile.id,
        user_id=profile.user_id,
        preferred_name=profile.preferred_name,
        application_year=profile.application_year,
        application_status=profile.application_status,
        program_code=profile.program_code,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        ssn_display=ssn_disp,
        dob_display=dob_disp,
        phone_display=phone_disp,
        email_display=email_disp,
    )


def _score_to_read(score: ExamScore) -> ExamScoreRead:
    return ExamScoreRead(
        id=score.id,
        candidate_id=score.candidate_id,
        subject_code=score.subject_code,
        subject_name=score.subject_name,
        score=score.score,
        max_score=score.max_score,
        exam_date=score.exam_date,
        recorded_by=score.recorded_by,
        created_at=score.created_at,
    )


def _pref_to_read(pref: TransferPreference) -> TransferPreferenceRead:
    return TransferPreferenceRead(
        id=pref.id,
        candidate_id=pref.candidate_id,
        institution_name=pref.institution_name,
        program_code=pref.program_code,
        priority_rank=pref.priority_rank,
        notes=pref.notes,
        is_active=pref.is_active,
        created_at=pref.created_at,
    )


# 0. GET /candidates — list all profiles (reviewer/admin, paginated)
@router.get(
    "",
    response_model=PaginatedResponse[CandidateProfileRead],
    dependencies=[Depends(require_role(UserRole.reviewer, UserRole.admin))],
)
async def list_candidate_profiles(
    session: DbSession,
    actor: CurrentActor,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[CandidateProfileRead]:
    svc = CandidateService(session)
    profiles, total = await svc.list_profiles(actor, page=page, page_size=page_size)
    privileged = is_privileged(actor.role)
    items = [_profile_to_read(p, privileged) for p in profiles]
    total_pages = max(1, (total + page_size - 1) // page_size)
    return PaginatedResponse(
        data=items,
        pagination=PaginationMeta(page=page, page_size=page_size, total=total, total_pages=total_pages),
        meta=ApiMeta.now(),
    )


# 1. POST /candidates — create profile (reviewer/admin)
@router.post(
    "",
    response_model=SuccessResponse[CandidateProfileRead],
    status_code=201,
    dependencies=[Depends(require_role(UserRole.reviewer, UserRole.admin))],
)
async def create_candidate_profile(
    user_id: uuid.UUID,
    session: DbSession,
    actor: CurrentActor,
) -> SuccessResponse[CandidateProfileRead]:
    svc = CandidateService(session)
    profile = await svc.create_profile(user_id, actor)
    return make_success(_profile_to_read(profile, is_privileged(actor.role)))


# 1b. POST /candidates/self — candidate-initiated self-profile creation.
# Enforces row ownership (profile.user_id == authenticated user.id) and only
# allows role=candidate. Returns existing profile idempotently on re-invocation.
@router.post(
    "/self",
    response_model=SuccessResponse[CandidateProfileRead],
    status_code=201,
    dependencies=[Depends(require_role(UserRole.candidate))],
)
async def create_own_candidate_profile(
    session: DbSession,
    user: CurrentUser,
    actor: CurrentActor,
) -> SuccessResponse[CandidateProfileRead]:
    svc = CandidateService(session)
    profile = await svc.create_self_profile(user.id, actor)
    return make_success(_profile_to_read(profile, is_privileged(actor.role)))


# 2. GET /candidates/{candidate_id} — get profile (auth, row-scoped)
@router.get(
    "/{candidate_id}",
    response_model=SuccessResponse[CandidateProfileRead],
)
async def get_candidate_profile(
    candidate_id: uuid.UUID,
    session: DbSession,
    actor: CurrentActor,
) -> SuccessResponse[CandidateProfileRead]:
    svc = CandidateService(session)
    profile = await svc.get_profile(candidate_id, actor)
    return make_success(_profile_to_read(profile, is_privileged(actor.role)))


# 3. PATCH /candidates/{candidate_id} — update profile (auth, row-scoped)
@router.patch(
    "/{candidate_id}",
    response_model=SuccessResponse[CandidateProfileRead],
)
async def update_candidate_profile(
    candidate_id: uuid.UUID,
    data: CandidateProfileUpdate,
    session: DbSession,
    actor: CurrentActor,
) -> SuccessResponse[CandidateProfileRead]:
    svc = CandidateService(session)
    profile = await svc.update_profile(candidate_id, actor, data)
    return make_success(_profile_to_read(profile, is_privileged(actor.role)))


# 4. GET /candidates/{candidate_id}/exam-scores — list (auth, row-scoped)
@router.get(
    "/{candidate_id}/exam-scores",
    response_model=SuccessResponse[list[ExamScoreRead]],
)
async def list_exam_scores(
    candidate_id: uuid.UUID,
    session: DbSession,
    actor: CurrentActor,
) -> SuccessResponse[list[ExamScoreRead]]:
    svc = CandidateService(session)
    scores = await svc.list_exam_scores(candidate_id, actor)
    return make_success([_score_to_read(s) for s in scores])


# 5. POST /candidates/{candidate_id}/exam-scores — add score (reviewer/admin)
@router.post(
    "/{candidate_id}/exam-scores",
    response_model=SuccessResponse[ExamScoreRead],
    status_code=201,
    dependencies=[Depends(require_role(UserRole.reviewer, UserRole.admin))],
)
async def add_exam_score(
    candidate_id: uuid.UUID,
    data: ExamScoreCreate,
    session: DbSession,
    actor: CurrentActor,
) -> SuccessResponse[ExamScoreRead]:
    svc = CandidateService(session)
    score = await svc.add_exam_score(candidate_id, actor, data)
    return make_success(_score_to_read(score))


# 6. GET /candidates/{candidate_id}/transfer-preferences — list (auth, row-scoped)
@router.get(
    "/{candidate_id}/transfer-preferences",
    response_model=SuccessResponse[list[TransferPreferenceRead]],
)
async def list_transfer_preferences(
    candidate_id: uuid.UUID,
    session: DbSession,
    actor: CurrentActor,
) -> SuccessResponse[list[TransferPreferenceRead]]:
    svc = CandidateService(session)
    prefs = await svc.list_transfer_preferences(candidate_id, actor)
    return make_success([_pref_to_read(p) for p in prefs])


# 7. POST /candidates/{candidate_id}/transfer-preferences — add (auth, row-scoped)
@router.post(
    "/{candidate_id}/transfer-preferences",
    response_model=SuccessResponse[TransferPreferenceRead],
    status_code=201,
)
async def add_transfer_preference(
    candidate_id: uuid.UUID,
    data: TransferPreferenceCreate,
    session: DbSession,
    actor: CurrentActor,
) -> SuccessResponse[TransferPreferenceRead]:
    svc = CandidateService(session)
    pref = await svc.add_transfer_preference(candidate_id, actor, data)
    return make_success(_pref_to_read(pref))


# 8. PATCH /candidates/{candidate_id}/transfer-preferences/{pref_id} — update (auth, owner/staff)
@router.patch(
    "/{candidate_id}/transfer-preferences/{pref_id}",
    response_model=SuccessResponse[TransferPreferenceRead],
)
async def update_transfer_preference(
    candidate_id: uuid.UUID,
    pref_id: uuid.UUID,
    data: TransferPreferenceUpdate,
    session: DbSession,
    actor: CurrentActor,
) -> SuccessResponse[TransferPreferenceRead]:
    svc = CandidateService(session)
    pref = await svc.update_transfer_preference(pref_id, actor, data)
    return make_success(_pref_to_read(pref))


# 9. GET /candidates/{candidate_id}/checklist — checklist (auth, row-scoped)
@router.get(
    "/{candidate_id}/checklist",
    response_model=SuccessResponse[list[ChecklistItemRead]],
)
async def get_checklist(
    candidate_id: uuid.UUID,
    session: DbSession,
    actor: CurrentActor,
) -> SuccessResponse[list[ChecklistItemRead]]:
    svc = CandidateService(session)
    await svc.get_profile(candidate_id, actor)
    doc_svc = DocumentService(session, get_file_store())
    items = await doc_svc.get_checklist(candidate_id)
    return make_success(items)
