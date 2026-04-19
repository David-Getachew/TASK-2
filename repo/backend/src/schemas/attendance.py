import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from ..domain.enums import AnomalyType, ExceptionStatus, ReviewDecision, ReviewStage


class AttendanceExceptionCreate(BaseModel):
    anomaly_id: uuid.UUID | None = None
    candidate_statement: str | None = Field(None, max_length=5000)


class AnomalyCreate(BaseModel):
    candidate_id: uuid.UUID
    anomaly_type: AnomalyType
    session_date: datetime
    session_identifier: str | None = Field(None, max_length=200)
    description: str | None = None


class AnomalyRead(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    anomaly_type: AnomalyType
    session_date: datetime
    session_identifier: str | None
    flagged_by: uuid.UUID
    flagged_at: datetime
    description: str | None


class ProofUploadResponse(BaseModel):
    proof_id: uuid.UUID
    exception_id: uuid.UUID
    document_version_id: uuid.UUID
    original_filename: str
    uploaded_at: datetime


class ReviewDecisionCreate(BaseModel):
    decision: ReviewDecision
    notes: str | None = Field(None, max_length=3000)


class ExceptionReviewStepRead(BaseModel):
    id: uuid.UUID
    exception_id: uuid.UUID
    step_order: int
    stage: ReviewStage
    reviewer_id: uuid.UUID
    reviewer_role: str
    decision: ReviewDecision
    notes: str | None
    decided_at: datetime
    is_escalated: bool


class ExceptionApprovalRead(BaseModel):
    id: uuid.UUID
    step_id: uuid.UUID
    exception_id: uuid.UUID
    approved_by: uuid.UUID
    approved_at: datetime
    outcome: str
    signature_hash: str | None


class ExceptionProofRead(BaseModel):
    """Metadata for an exception proof attachment.

    Embedded in ExceptionRead so reviewers/proctors can inspect the
    uploaded evidence (filename, uploader, timestamp) without an extra
    round-trip. The actual bytes remain behind the signed document
    download endpoint.
    """

    id: uuid.UUID
    exception_id: uuid.UUID
    document_version_id: uuid.UUID
    uploaded_by: uuid.UUID
    uploaded_at: datetime
    description: str | None = None


class ExceptionRead(BaseModel):
    id: uuid.UUID
    anomaly_id: uuid.UUID | None
    candidate_id: uuid.UUID
    status: ExceptionStatus
    current_stage: ReviewStage
    candidate_statement: str | None
    submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    review_steps: list[ExceptionReviewStepRead] = []
    proofs: list[ExceptionProofRead] = []
