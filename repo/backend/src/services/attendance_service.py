from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.document_policy import validate_upload
from ..domain.enums import (
    AuditEventType,
    ExceptionStatus,
    ReviewDecision,
    ReviewStage,
    UserRole,
)
from ..domain.exception_workflow import (
    can_adjudicate,
    initial_stage,
    resolve_status,
    validate_decision,
    UnauthorizedReviewError,
    InvalidDecisionError,
    WorkflowError,
)
from ..persistence.models.document import DocumentVersion
from ..persistence.repositories.attendance_repo import AttendanceRepository
from ..persistence.repositories.document_repo import DocumentRepository
from ..schemas.attendance import (
    AnomalyCreate,
    AnomalyRead,
    AttendanceExceptionCreate,
    ExceptionProofRead,
    ExceptionRead,
    ExceptionReviewStepRead,
    ProofUploadResponse,
    ReviewDecisionCreate,
)
from ..security import audit as audit_mod
from ..security.errors import BusinessRuleError, ForbiddenError, ResourceNotFoundError
from ..security.hashing import sha256_of_bytes
from ..security.rbac import Actor, assert_roles_or_owner
from ..storage.file_store import FileStore


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _sig_hash(step_id: uuid.UUID, exception_id: uuid.UUID, outcome: str, approved_by: uuid.UUID, approved_at: datetime) -> str:
    payload = f"{step_id}:{exception_id}:{outcome}:{approved_by}:{approved_at.isoformat()}"
    return hashlib.sha256(payload.encode()).hexdigest()


class AttendanceService:
    def __init__(self, session: AsyncSession, file_store: FileStore) -> None:
        self._session = session
        self._repo = AttendanceRepository(session)
        self._doc_repo = DocumentRepository(session)
        self._file_store = file_store

    # ── Anomalies ─────────────────────────────────────────────────────────────

    async def flag_anomaly(self, actor: Actor, data: AnomalyCreate) -> AnomalyRead:
        anomaly = await self._repo.create_anomaly(
            candidate_id=data.candidate_id,
            anomaly_type=data.anomaly_type.value,
            session_date=data.session_date,
            flagged_by=uuid.UUID(actor.user_id),
            session_identifier=data.session_identifier,
            description=data.description,
        )
        return AnomalyRead(
            id=anomaly.id,
            candidate_id=anomaly.candidate_id,
            anomaly_type=data.anomaly_type,
            session_date=anomaly.session_date,
            session_identifier=anomaly.session_identifier,
            flagged_by=anomaly.flagged_by,
            flagged_at=anomaly.flagged_at,
            description=anomaly.description,
        )

    async def list_anomalies(
        self, actor: Actor, candidate_id: uuid.UUID | None = None
    ) -> list[AnomalyRead]:
        if actor.role == UserRole.candidate:
            from ..persistence.repositories.candidate_repo import CandidateRepository
            profile = await CandidateRepository(self._session).get_by_user_id(uuid.UUID(actor.user_id))
            candidate_id = profile.id if profile else None
        anomalies = await self._repo.list_anomalies(candidate_id)
        return [
            AnomalyRead(
                id=a.id,
                candidate_id=a.candidate_id,
                anomaly_type=a.anomaly_type,
                session_date=a.session_date,
                session_identifier=a.session_identifier,
                flagged_by=a.flagged_by,
                flagged_at=a.flagged_at,
                description=a.description,
            )
            for a in anomalies
        ]

    # ── Exceptions ────────────────────────────────────────────────────────────

    async def create_exception(
        self,
        candidate_id: uuid.UUID,
        actor: Actor,
        data: AttendanceExceptionCreate,
    ) -> ExceptionRead:
        await self._assert_exception_access(actor, candidate_id)
        stage = initial_stage()
        exception = await self._repo.create_exception(
            candidate_id=candidate_id,
            current_stage=stage.value,
            anomaly_id=data.anomaly_id,
            candidate_statement=data.candidate_statement,
        )
        await audit_mod.record_audit(
            self._session,
            event_type=AuditEventType.exception_created,
            actor_id=uuid.UUID(actor.user_id),
            actor_role=actor.role.value,
            resource_type="attendance_exception",
            resource_id=str(exception.id),
            outcome="created",
        )
        loaded = await self._repo.get_exception(exception.id)
        return _exception_to_read(loaded or exception)

    async def list_exceptions(
        self,
        actor: Actor,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ExceptionRead], int]:
        candidate_id = None
        if actor.role == UserRole.candidate:
            from ..persistence.repositories.candidate_repo import CandidateRepository
            profile = await CandidateRepository(self._session).get_by_user_id(uuid.UUID(actor.user_id))
            candidate_id = profile.id if profile else None
        exceptions, total = await self._repo.list_exceptions(
            candidate_id=candidate_id,
            status=status,
            page=page,
            page_size=page_size,
        )
        return [_exception_to_read(e) for e in exceptions], total

    async def _assert_exception_access(self, actor: Actor, exception_candidate_id: uuid.UUID) -> None:
        """Ownership check that resolves candidate profile ID for the actor when role=candidate."""
        from ..security.rbac import has_role
        if has_role(actor, [UserRole.reviewer, UserRole.admin, UserRole.proctor]):
            return
        from ..persistence.repositories.candidate_repo import CandidateRepository
        profile = await CandidateRepository(self._session).get_by_user_id(uuid.UUID(actor.user_id))
        actor_profile_id = profile.id if profile else None
        if actor_profile_id is None or actor_profile_id != exception_candidate_id:
            raise ForbiddenError("Actor is neither privileged nor the resource owner.")

    async def get_exception(
        self, exception_id: uuid.UUID, actor: Actor
    ) -> ExceptionRead:
        exception = await self._repo.get_exception(exception_id)
        if exception is None:
            raise ResourceNotFoundError("Attendance exception not found.")
        await self._assert_exception_access(actor, exception.candidate_id)
        return _exception_to_read(exception)

    async def upload_proof(
        self,
        exception_id: uuid.UUID,
        actor: Actor,
        file_bytes: bytes,
        original_filename: str,
        content_type: str,
    ) -> ProofUploadResponse:
        exception = await self._repo.get_exception(exception_id)
        if exception is None:
            raise ResourceNotFoundError("Attendance exception not found.")
        await self._assert_exception_access(actor, exception.candidate_id)

        size_bytes = len(file_bytes)
        validate_upload(content_type, size_bytes)
        sha256 = sha256_of_bytes(file_bytes)

        doc_version_id = uuid.uuid4()
        stored_filename = f"{uuid.uuid4().hex}_{original_filename}"
        storage_path = await self._file_store.write_proof(
            exception_id=exception_id,
            doc_version_id=doc_version_id,
            filename=stored_filename,
            data=file_bytes,
        )

        # Create a real Document row first (FK-valid parent for DocumentVersion)
        now = _now()
        proof_doc = await self._doc_repo.create_document(
            candidate_id=exception.candidate_id,
            requirement_id=None,
            document_type="exception_proof",
        )
        # Create DocumentVersion with correct FK (document_id → documents.id)
        proof_doc.current_version = 1
        version = DocumentVersion(
            id=doc_version_id,
            document_id=proof_doc.id,
            version_number=1,
            original_filename=original_filename,
            stored_filename=stored_filename,
            storage_path=storage_path,
            content_type=content_type,
            size_bytes=size_bytes,
            sha256_hash=sha256,
            uploaded_by=uuid.UUID(actor.user_id),
            uploaded_at=now,
            is_active=True,
        )
        self._session.add(version)
        await self._session.flush()

        proof = await self._repo.add_proof(
            exception_id=exception_id,
            document_version_id=doc_version_id,
            uploaded_by=uuid.UUID(actor.user_id),
            description=None,
        )

        # Advance status from pending_proof → pending_initial_review
        if exception.status == ExceptionStatus.pending_proof.value:
            await self._repo.update_exception_status(
                exception, ExceptionStatus.pending_initial_review.value
            )
            exception.submitted_at = now

        await audit_mod.record_audit(
            self._session,
            event_type=AuditEventType.document_uploaded,
            actor_id=uuid.UUID(actor.user_id),
            actor_role=actor.role.value,
            resource_type="exception_proof",
            resource_id=str(exception_id),
            outcome="proof_uploaded",
        )

        return ProofUploadResponse(
            proof_id=proof.id,
            exception_id=exception_id,
            document_version_id=doc_version_id,
            original_filename=original_filename,
            uploaded_at=now,
        )

    async def submit_review(
        self,
        exception_id: uuid.UUID,
        reviewer_actor: Actor,
        data: ReviewDecisionCreate,
    ) -> ExceptionReviewStepRead:
        exception = await self._repo.get_exception(exception_id)
        if exception is None:
            raise ResourceNotFoundError("Attendance exception not found.")

        stage = ReviewStage(exception.current_stage)
        decision = data.decision

        try:
            can_adjudicate(stage, reviewer_actor.role)
            validate_decision(stage, decision)
        except UnauthorizedReviewError as exc:
            raise ForbiddenError(str(exc)) from exc
        except InvalidDecisionError as exc:
            raise BusinessRuleError(str(exc)) from exc

        new_status = resolve_status(stage, decision)
        is_escalated = (decision == ReviewDecision.escalate)

        step_order = (await self._repo.count_review_steps(exception_id)) + 1
        now = _now()
        step = await self._repo.add_review_step(
            exception_id=exception_id,
            step_order=step_order,
            stage=stage.value,
            reviewer_id=uuid.UUID(reviewer_actor.user_id),
            reviewer_role=reviewer_actor.role.value,
            decision=decision.value,
            notes=data.notes,
            is_escalated=is_escalated,
        )

        new_stage = None
        if is_escalated:
            new_stage = ReviewStage.final.value

        await self._repo.update_exception_status(
            exception, new_status.value, current_stage=new_stage
        )

        # Create immutable approval for terminal decisions
        if decision in (ReviewDecision.approve, ReviewDecision.reject):
            sig = _sig_hash(step.id, exception_id, new_status.value, uuid.UUID(reviewer_actor.user_id), now)
            await self._repo.add_approval(
                step_id=step.id,
                exception_id=exception_id,
                approved_by=uuid.UUID(reviewer_actor.user_id),
                outcome=new_status.value,
                signature_hash=sig,
            )

        await audit_mod.record_audit(
            self._session,
            event_type=AuditEventType.exception_reviewed,
            actor_id=uuid.UUID(reviewer_actor.user_id),
            actor_role=reviewer_actor.role.value,
            resource_type="attendance_exception",
            resource_id=str(exception_id),
            outcome=new_status.value,
        )
        if decision in (ReviewDecision.approve, ReviewDecision.reject):
            await audit_mod.record_audit(
                self._session,
                event_type=AuditEventType.exception_approved,
                actor_id=uuid.UUID(reviewer_actor.user_id),
                actor_role=reviewer_actor.role.value,
                resource_type="attendance_exception",
                resource_id=str(exception_id),
                outcome=new_status.value,
            )

        return ExceptionReviewStepRead(
            id=step.id,
            exception_id=step.exception_id,
            step_order=step.step_order,
            stage=ReviewStage(step.stage),
            reviewer_id=step.reviewer_id,
            reviewer_role=step.reviewer_role,
            decision=ReviewDecision(step.decision),
            notes=step.notes,
            decided_at=step.decided_at,
            is_escalated=step.is_escalated,
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _exception_to_read(exception) -> ExceptionRead:
    steps = []
    for s in sorted(exception.review_steps or [], key=lambda x: x.step_order):
        steps.append(
            ExceptionReviewStepRead(
                id=s.id,
                exception_id=s.exception_id,
                step_order=s.step_order,
                stage=ReviewStage(s.stage),
                reviewer_id=s.reviewer_id,
                reviewer_role=s.reviewer_role,
                decision=ReviewDecision(s.decision),
                notes=s.notes,
                decided_at=s.decided_at,
                is_escalated=s.is_escalated,
            )
        )
    proofs = []
    for p in sorted(exception.proofs or [], key=lambda x: x.uploaded_at):
        proofs.append(
            ExceptionProofRead(
                id=p.id,
                exception_id=p.exception_id,
                document_version_id=p.document_version_id,
                uploaded_by=p.uploaded_by,
                uploaded_at=p.uploaded_at,
                description=p.description,
            )
        )
    return ExceptionRead(
        id=exception.id,
        anomaly_id=exception.anomaly_id,
        candidate_id=exception.candidate_id,
        status=ExceptionStatus(exception.status),
        current_stage=ReviewStage(exception.current_stage),
        candidate_statement=exception.candidate_statement,
        submitted_at=exception.submitted_at,
        created_at=exception.created_at,
        updated_at=exception.updated_at,
        review_steps=steps,
        proofs=proofs,
    )
