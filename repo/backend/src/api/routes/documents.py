from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from ...domain.enums import UserRole  # noqa: F401
from ...schemas.common import SuccessResponse, make_success
from ...schemas.document import (
    ChecklistItemRead,
    DocumentRead,
    DocumentReviewCreate,
    DocumentReviewRead,
    DocumentUploadResponse,
)
from ...services.document_service import DocumentService
from ...storage.file_store import get_file_store
from ..dependencies import CurrentActor, DbSession, require_role, require_signed_request

router = APIRouter(tags=["documents"])


# 10. POST /candidates/{candidate_id}/documents/upload — candidate, signed, multipart
@router.post(
    "/candidates/{candidate_id}/documents/upload",
    response_model=SuccessResponse[DocumentUploadResponse],
    status_code=201,
    dependencies=[Depends(require_role(UserRole.candidate)), Depends(require_signed_request)],
)
async def upload_document(
    candidate_id: uuid.UUID,
    session: DbSession,
    actor: CurrentActor,
    file: UploadFile = File(...),
    requirement_code: str | None = Form(None),
) -> SuccessResponse[DocumentUploadResponse]:
    file_bytes = await file.read()
    svc = DocumentService(session, get_file_store())
    result = await svc.upload(
        candidate_id=candidate_id,
        actor=actor,
        requirement_code=requirement_code,
        file_bytes=file_bytes,
        original_filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
    )
    return make_success(result)


# 11. GET /candidates/{candidate_id}/documents — list (auth, row-scoped)
@router.get(
    "/candidates/{candidate_id}/documents",
    response_model=SuccessResponse[list[DocumentRead]],
)
async def list_documents(
    candidate_id: uuid.UUID,
    session: DbSession,
    actor: CurrentActor,
) -> SuccessResponse[list[DocumentRead]]:
    svc = DocumentService(session, get_file_store())
    docs = await svc.list_documents(candidate_id, actor)
    return make_success(docs)


# 12. GET /candidates/{candidate_id}/documents/{document_id} — get (auth, owner/staff)
@router.get(
    "/candidates/{candidate_id}/documents/{document_id}",
    response_model=SuccessResponse[DocumentRead],
)
async def get_document(
    candidate_id: uuid.UUID,
    document_id: uuid.UUID,
    session: DbSession,
    actor: CurrentActor,
) -> SuccessResponse[DocumentRead]:
    svc = DocumentService(session, get_file_store())
    doc = await svc.get_document(document_id, actor)
    return make_success(doc)


# 13. POST /documents/{document_id}/review — reviewer/admin, audit
@router.post(
    "/documents/{document_id}/review",
    response_model=SuccessResponse[DocumentReviewRead],
    dependencies=[Depends(require_role(UserRole.reviewer, UserRole.admin))],
)
async def review_document(
    document_id: uuid.UUID,
    data: DocumentReviewCreate,
    session: DbSession,
    actor: CurrentActor,
) -> SuccessResponse[DocumentReviewRead]:
    svc = DocumentService(session, get_file_store())
    review = await svc.review_decision(document_id, actor, data)
    return make_success(review)


# 14. GET /documents/{document_id}/download — reviewer/admin, role-gated, watermarked
@router.get(
    "/documents/{document_id}/download",
    dependencies=[Depends(require_role(UserRole.reviewer, UserRole.admin))],
)
async def download_document(
    document_id: uuid.UUID,
    session: DbSession,
    actor: CurrentActor,
) -> StreamingResponse:
    svc = DocumentService(session, get_file_store())
    content, content_type, filename, served_hash = await svc.download(document_id, actor)

    def _iter():
        yield content

    return StreamingResponse(
        _iter(),
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            # X-File-Hash: SHA-256 hex of the bytes actually served. For PDFs
            # this is the post-watermark hash, so clients that verify the
            # header match what they received (not the raw stored object).
            "X-File-Hash": served_hash,
        },
    )
