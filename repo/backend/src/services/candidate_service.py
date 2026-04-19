from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.enums import AuditEventType, UserRole
from ..persistence.models.candidate import CandidateProfile, ExamScore, TransferPreference
from ..persistence.repositories.candidate_repo import CandidateRepository
from ..schemas.candidate import (
    CandidateProfileRead,
    CandidateProfileUpdate,
    ExamScoreCreate,
    ExamScoreRead,
    TransferPreferenceCreate,
    TransferPreferenceRead,
    TransferPreferenceUpdate,
)
from ..security import audit as audit_mod
from ..security.data_masking import is_privileged
from ..security.encryption import decrypt_field, encrypt_field
from ..security.errors import BusinessRuleError, ForbiddenError, ResourceNotFoundError
from ..security.rbac import Actor, assert_roles_or_owner


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


_SENSITIVE_FIELDS = {
    "ssn": ("ssn_encrypted", "ssn_key_version"),
    "date_of_birth": ("date_of_birth_encrypted", "dob_key_version"),
    "contact_phone": ("contact_phone_encrypted", "phone_key_version"),
    "contact_email": ("contact_email_encrypted", "email_key_version"),
}


class CandidateService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CandidateRepository(session)

    # ── Profile ──────────────────────────────────────────────────────────────

    async def create_profile(
        self, user_id: uuid.UUID, actor: Actor
    ) -> CandidateProfile:
        existing = await self._repo.get_by_user_id(user_id)
        if existing:
            raise BusinessRuleError("A profile already exists for this user.")
        profile = await self._repo.create(user_id=user_id)
        await audit_mod.record_audit(
            self._session,
            event_type=AuditEventType.order_created,
            actor_id=uuid.UUID(actor.user_id),
            actor_role=actor.role.value,
            resource_type="candidate_profile",
            resource_id=str(profile.id),
            outcome="created",
        )
        return profile

    async def create_self_profile(
        self, user_id: uuid.UUID, actor: Actor
    ) -> CandidateProfile:
        """Candidate-initiated onboarding.

        Strict row ownership: `user_id` MUST match the authenticated actor's
        subject. If a profile already exists the call is idempotent — the
        caller receives their existing profile instead of a business error.
        """
        if str(user_id) != actor.user_id:
            raise ForbiddenError("Candidates may only initialize their own profile.")
        existing = await self._repo.get_by_user_id(user_id)
        if existing is not None:
            return existing
        profile = await self._repo.create(user_id=user_id)
        await audit_mod.record_audit(
            self._session,
            event_type=AuditEventType.order_created,
            actor_id=uuid.UUID(actor.user_id),
            actor_role=actor.role.value,
            resource_type="candidate_profile",
            resource_id=str(profile.id),
            outcome="self_created",
        )
        return profile

    async def list_profiles(
        self, actor: Actor, page: int, page_size: int
    ) -> tuple[list[CandidateProfile], int]:
        return await self._repo.list_paginated(page=page, page_size=page_size)

    async def get_profile(
        self, candidate_id: uuid.UUID, actor: Actor
    ) -> CandidateProfile:
        profile = await self._repo.get_by_id(candidate_id)
        if profile is None:
            raise ResourceNotFoundError("Candidate profile not found.")
        assert_roles_or_owner(
            actor,
            [UserRole.reviewer, UserRole.admin, UserRole.proctor],
            str(profile.user_id),
        )
        return profile

    async def get_profile_by_user(
        self, user_id: uuid.UUID, actor: Actor
    ) -> CandidateProfile:
        profile = await self._repo.get_by_user_id(user_id)
        if profile is None:
            raise ResourceNotFoundError("Candidate profile not found.")
        assert_roles_or_owner(
            actor,
            [UserRole.reviewer, UserRole.admin, UserRole.proctor],
            str(profile.user_id),
        )
        return profile

    async def update_profile(
        self,
        candidate_id: uuid.UUID,
        actor: Actor,
        data: CandidateProfileUpdate,
    ) -> CandidateProfile:
        profile = await self.get_profile(candidate_id, actor)
        update_fields = data.model_dump(exclude_none=True)
        await self._repo.update(profile, **update_fields)
        return profile

    async def update_sensitive_fields(
        self,
        candidate_id: uuid.UUID,
        actor: Actor,
        field_updates: dict[str, str],
    ) -> None:
        if not is_privileged(actor.role):
            raise ForbiddenError("Only privileged roles may update sensitive fields.")
        profile = await self._repo.get_by_id(candidate_id)
        if profile is None:
            raise ResourceNotFoundError("Candidate profile not found.")
        aad = candidate_id.bytes
        for field_name, new_value in field_updates.items():
            if field_name not in _SENSITIVE_FIELDS:
                raise BusinessRuleError(f"Unknown sensitive field: {field_name}")
            enc_col, ver_col = _SENSITIVE_FIELDS[field_name]
            old_enc = getattr(profile, enc_col)
            new_enc, new_ver = encrypt_field(new_value, aad)
            await self._repo.add_profile_history(
                candidate_id=candidate_id,
                changed_by=uuid.UUID(actor.user_id),
                field_name=field_name,
                old_value_encrypted=old_enc,
                new_value_encrypted=new_enc,
                change_reason="privileged_update",
            )
            setattr(profile, enc_col, new_enc)
            setattr(profile, ver_col, new_ver)
        await self._session.flush()
        await audit_mod.record_audit(
            self._session,
            event_type=AuditEventType.sensitive_field_accessed,
            actor_id=uuid.UUID(actor.user_id),
            actor_role=actor.role.value,
            resource_type="candidate_profile",
            resource_id=str(candidate_id),
            outcome="updated",
            detail={"fields": list(field_updates.keys())},
        )

    # ── Exam scores ───────────────────────────────────────────────────────────

    async def list_exam_scores(
        self, candidate_id: uuid.UUID, actor: Actor
    ) -> list[ExamScore]:
        await self.get_profile(candidate_id, actor)
        return await self._repo.list_exam_scores(candidate_id)

    async def add_exam_score(
        self, candidate_id: uuid.UUID, actor: Actor, data: ExamScoreCreate
    ) -> ExamScore:
        await self.get_profile(candidate_id, actor)
        score = await self._repo.add_exam_score(
            candidate_id=candidate_id,
            subject_code=data.subject_code,
            subject_name=data.subject_name,
            score=data.score,
            max_score=data.max_score,
            exam_date=data.exam_date,
            recorded_by=uuid.UUID(actor.user_id),
        )
        return score

    # ── Transfer preferences ──────────────────────────────────────────────────

    async def list_transfer_preferences(
        self, candidate_id: uuid.UUID, actor: Actor
    ) -> list[TransferPreference]:
        await self.get_profile(candidate_id, actor)
        return await self._repo.list_transfer_preferences(candidate_id)

    async def add_transfer_preference(
        self,
        candidate_id: uuid.UUID,
        actor: Actor,
        data: TransferPreferenceCreate,
    ) -> TransferPreference:
        profile = await self.get_profile(candidate_id, actor)
        assert_roles_or_owner(
            actor,
            [UserRole.reviewer, UserRole.admin],
            str(profile.user_id),
        )
        return await self._repo.add_transfer_preference(
            candidate_id=candidate_id,
            institution_name=data.institution_name,
            program_code=data.program_code,
            priority_rank=data.priority_rank,
            notes=data.notes,
        )

    async def update_transfer_preference(
        self,
        pref_id: uuid.UUID,
        actor: Actor,
        data: TransferPreferenceUpdate,
    ) -> TransferPreference:
        pref = await self._repo.get_transfer_preference(pref_id)
        if pref is None:
            raise ResourceNotFoundError("Transfer preference not found.")
        profile = await self._repo.get_by_id(pref.candidate_id)
        assert_roles_or_owner(
            actor,
            [UserRole.reviewer, UserRole.admin],
            str(profile.user_id) if profile else "",
        )
        update_fields = data.model_dump(exclude_none=True)
        await self._repo.update_transfer_preference(pref, **update_fields)
        return pref
