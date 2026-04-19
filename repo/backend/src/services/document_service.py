from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.document_policy import (
    DocumentPolicyViolation,
    validate_review_decision,
    validate_upload,
)
from ..domain.enums import AuditEventType, DocumentStatus, UserRole
from ..persistence.repositories.candidate_repo import CandidateRepository
from ..persistence.repositories.document_repo import DocumentRepository
from ..schemas.document import (
    ChecklistItemRead,
    DocumentRead,
    DocumentReviewCreate,
    DocumentReviewRead,
    DocumentUploadResponse,
    DocumentVersionRead,
)
from ..security import audit as audit_mod
from ..security.errors import ForbiddenError, PolicyViolationError, ResourceNotFoundError
from ..security.hashing import sha256_of_bytes, verify_sha256_bytes
from ..security.rbac import Actor, assert_roles_or_owner, can_download_restricted
from ..security.watermark import apply_pdf_watermark
from ..storage.file_store import FileStore


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


class DocumentService:
    def __init__(self, session: AsyncSession, file_store: FileStore) -> None:
        self._session = session
        self._repo = DocumentRepository(session)
        self._file_store = file_store

    async def upload(
        self,
        candidate_id: uuid.UUID,
        actor: Actor,
        requirement_code: str | None,
        file_bytes: bytes,
        original_filename: str,
        content_type: str,
    ) -> DocumentUploadResponse:
        if actor.role == UserRole.candidate:
            profile = await CandidateRepository(self._session).get_by_id(candidate_id)
            if profile is None or str(profile.user_id) != str(actor.user_id):
                raise ForbiddenError("Candidates may only upload documents for their own profile.")
        size_bytes = len(file_bytes)
        try:
            validate_upload(content_type, size_bytes)
        except DocumentPolicyViolation as exc:
            raise PolicyViolationError(str(exc)) from exc
        sha256 = sha256_of_bytes(file_bytes)

        requirement = None
        if requirement_code:
            requirement = await self._repo.get_requirement_by_code(requirement_code)

        # Create or reuse document record (one doc per requirement per candidate)
        doc = None
        docs = await self._repo.list_candidate_documents(candidate_id)
        if requirement:
            for d in docs:
                if d.requirement_id == requirement.id:
                    doc = d
                    break
        else:
            for d in docs:
                if d.requirement_id is None and d.document_type == "generic_upload":
                    doc = d
                    break

        if doc is None:
            doc = await self._repo.create_document(
                candidate_id=candidate_id,
                requirement_id=requirement.id if requirement else None,
                document_type=requirement_code or "generic_upload",
            )

        # Determine stored filename
        stored_filename = f"{uuid.uuid4().hex}_{original_filename}"
        storage_path = await self._file_store.write_document(
            candidate_id=candidate_id,
            document_id=doc.id,
            version=doc.current_version + 1,
            filename=stored_filename,
            data=file_bytes,
        )

        version = await self._repo.add_version(
            document=doc,
            original_filename=original_filename,
            stored_filename=stored_filename,
            storage_path=storage_path,
            content_type=content_type,
            size_bytes=size_bytes,
            sha256_hash=sha256,
            uploaded_by=uuid.UUID(actor.user_id),
        )
        await self._repo.update_document_status(doc, DocumentStatus.pending_review.value)

        await audit_mod.record_audit(
            self._session,
            event_type=AuditEventType.document_uploaded,
            actor_id=uuid.UUID(actor.user_id),
            actor_role=actor.role.value,
            resource_type="document",
            resource_id=str(doc.id),
            outcome="uploaded",
            detail={"version": version.version_number, "sha256": sha256},
        )

        return DocumentUploadResponse(
            document_id=doc.id,
            version_number=version.version_number,
            original_filename=original_filename,
            content_type=content_type,
            size_bytes=size_bytes,
            sha256_hash=sha256,
            status=DocumentStatus.pending_review,
            uploaded_at=version.uploaded_at,
        )

    async def list_documents(
        self, candidate_id: uuid.UUID, actor: Actor
    ) -> list[DocumentRead]:
        profile = await CandidateRepository(self._session).get_by_id(candidate_id)
        owner_user_id = str(profile.user_id) if profile else ""
        assert_roles_or_owner(actor, [UserRole.reviewer, UserRole.admin, UserRole.proctor], owner_user_id)
        docs = await self._repo.list_candidate_documents(candidate_id)
        code_map = await self._requirement_code_map(
            [d.requirement_id for d in docs if d.requirement_id is not None]
        )
        return [_doc_to_read(d, code_map.get(d.requirement_id)) for d in docs]

    async def get_document(
        self, document_id: uuid.UUID, actor: Actor
    ) -> DocumentRead:
        doc = await self._repo.get_document(document_id)
        if doc is None:
            raise ResourceNotFoundError("Document not found.")
        profile = await CandidateRepository(self._session).get_by_id(doc.candidate_id)
        owner_user_id = str(profile.user_id) if profile else ""
        assert_roles_or_owner(
            actor,
            [UserRole.reviewer, UserRole.admin, UserRole.proctor],
            owner_user_id,
        )
        code_map = await self._requirement_code_map(
            [doc.requirement_id] if doc.requirement_id else []
        )
        return _doc_to_read(doc, code_map.get(doc.requirement_id))

    async def _requirement_code_map(
        self, requirement_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, str]:
        """Return {requirement_id: requirement_code} for the given IDs.

        Fetches in a single SELECT; callers pre-filter out None requirement_ids.
        Returns an empty dict when the input is empty (no query issued).
        """
        if not requirement_ids:
            return {}
        from sqlalchemy import select
        from ..persistence.models.document import DocumentRequirement

        q = select(
            DocumentRequirement.id, DocumentRequirement.requirement_code
        ).where(DocumentRequirement.id.in_(set(requirement_ids)))
        rows = (await self._session.execute(q)).all()
        return {rid: code for rid, code in rows}

    async def review_decision(
        self,
        document_id: uuid.UUID,
        reviewer_actor: Actor,
        data: DocumentReviewCreate,
    ) -> DocumentReviewRead:
        doc = await self._repo.get_document(document_id)
        if doc is None:
            raise ResourceNotFoundError("Document not found.")
        try:
            validate_review_decision(data.status, data.resubmission_reason)
        except DocumentPolicyViolation as exc:
            raise PolicyViolationError(str(exc)) from exc

        review = await self._repo.add_review(
            document_id=document_id,
            version_id=data.version_id,
            reviewer_id=uuid.UUID(reviewer_actor.user_id),
            status=data.status.value,
            resubmission_reason=data.resubmission_reason,
            reviewer_notes=data.reviewer_notes,
        )
        await self._repo.update_document_status(
            doc,
            data.status.value,
            resubmission_reason=data.resubmission_reason,
        )

        await audit_mod.record_audit(
            self._session,
            event_type=AuditEventType.document_reviewed,
            actor_id=uuid.UUID(reviewer_actor.user_id),
            actor_role=reviewer_actor.role.value,
            resource_type="document",
            resource_id=str(document_id),
            outcome=data.status.value,
        )

        return DocumentReviewRead(
            id=review.id,
            document_id=review.document_id,
            version_id=review.version_id,
            reviewer_id=review.reviewer_id,
            status=DocumentStatus(review.status),
            resubmission_reason=review.resubmission_reason,
            reviewer_notes=review.reviewer_notes,
            decided_at=review.decided_at,
            created_at=review.decided_at,
        )

    async def download(
        self, document_id: uuid.UUID, actor: Actor
    ) -> tuple[bytes, str, str, str]:
        """Return (content_bytes, content_type, filename, served_hash).

        The fourth element is the SHA-256 of the bytes actually served to
        the caller — post-watermark for PDFs, raw hash for other types.
        The route handler emits it as the ``X-File-Hash`` response header
        so clients can verify served-payload integrity per the documented
        contract in docs/api-spec.md.
        """
        if not can_download_restricted(actor.role):
            raise PolicyViolationError(
                "Only reviewers and admins may download documents."
            )
        doc = await self._repo.get_document(document_id)
        if doc is None:
            raise ResourceNotFoundError("Document not found.")

        version = await self._repo.get_latest_version(doc)
        if version is None:
            raise ResourceNotFoundError("Document version not found.")

        raw = await self._file_store.read(version.storage_path)
        if not verify_sha256_bytes(raw, version.sha256_hash):
            raise PolicyViolationError("Document hash mismatch — file may be corrupted.")

        content_type = version.content_type
        if content_type == "application/pdf":
            raw = apply_pdf_watermark(raw, actor.username, _now())

        served_hash = sha256_of_bytes(raw)

        await audit_mod.record_audit(
            self._session,
            event_type=AuditEventType.document_downloaded,
            actor_id=uuid.UUID(actor.user_id),
            actor_role=actor.role.value,
            resource_type="document",
            resource_id=str(document_id),
            outcome="downloaded",
        )

        return raw, content_type, version.original_filename, served_hash

    async def get_checklist(
        self, candidate_id: uuid.UUID
    ) -> list[ChecklistItemRead]:
        items = await self._repo.get_checklist(candidate_id)
        return [
            ChecklistItemRead(
                requirement_id=item["requirement_id"],
                requirement_code=item["requirement_code"],
                display_name=item["display_name"],
                is_mandatory=item["is_mandatory"],
                status=DocumentStatus(item["status"]) if item["status"] else None,
                document_id=item["document_id"],
                version_number=item["version_number"],
            )
            for item in items
        ]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _doc_to_read(doc, requirement_code: str | None = None) -> DocumentRead:
    from ..persistence.models.document import DocumentVersion

    latest: DocumentVersion | None = None
    if doc.versions:
        latest = max(doc.versions, key=lambda v: v.version_number)

    return DocumentRead(
        id=doc.id,
        candidate_id=doc.candidate_id,
        requirement_id=doc.requirement_id,
        requirement_code=requirement_code,
        document_type=doc.document_type,
        current_version=doc.current_version,
        current_status=DocumentStatus(doc.current_status),
        resubmission_reason=doc.resubmission_reason,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        latest_version=DocumentVersionRead(
            id=latest.id,
            document_id=latest.document_id,
            version_number=latest.version_number,
            original_filename=latest.original_filename,
            content_type=latest.content_type,
            size_bytes=latest.size_bytes,
            sha256_hash=latest.sha256_hash,
            uploaded_by=latest.uploaded_by,
            uploaded_at=latest.uploaded_at,
            is_active=latest.is_active,
        ) if latest else None,
    )
