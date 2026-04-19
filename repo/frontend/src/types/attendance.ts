export type AnomalyType = 'absent' | 'late' | 'unauthorized_absence' | 'other'

export type ExceptionStatus =
  | 'pending_proof'
  | 'pending_initial_review'
  | 'pending_final_review'
  | 'approved'
  | 'rejected'

export type ReviewStage = 'initial' | 'final'

export interface AttendanceAnomaly {
  id: string
  candidate_id: string
  anomaly_type: AnomalyType
  session_date: string
  description: string | null
  flagged_by: string
  flagged_at: string
  created_at: string
}

export interface AnomalyCreate {
  candidate_id: string
  anomaly_type: AnomalyType
  session_date: string
  description?: string | null
}

export interface ExceptionProof {
  id: string
  exception_id: string
  document_version_id: string
  uploaded_by: string
  description: string | null
  // BE `ExceptionProofRead.uploaded_at` is the canonical upload timestamp.
  uploaded_at: string
}

export interface ExceptionApproval {
  id: string
  step_id: string
  exception_id: string
  approved_by: string
  outcome: 'approved' | 'rejected' | 'escalated'
  signature_hash: string
  created_at: string
}

export interface ExceptionReviewStep {
  id: string
  exception_id: string
  step_order: number
  stage: ReviewStage
  reviewer_id: string
  reviewer_role: string
  decision: 'approve' | 'reject' | 'escalate'
  notes: string | null
  is_escalated: boolean
  // Matches backend `ExceptionReviewStepRead.decided_at`. BE emits the
  // timestamp the decision was recorded; views must read this field.
  decided_at: string
}

export interface AttendanceException {
  id: string
  anomaly_id: string | null
  candidate_id: string
  status: ExceptionStatus
  current_stage: ReviewStage
  candidate_statement: string | null
  // Matches backend `ExceptionRead.submitted_at` — nullable until candidate
  // submits the exception (moves out of `draft`).
  submitted_at: string | null
  // BE `ExceptionRead.proofs` — embedded proof metadata so reviewers can
  // inspect evidence without a second round-trip.
  proofs: ExceptionProof[]
  review_steps: ExceptionReviewStep[]
  created_at: string
  updated_at: string
}

export interface AttendanceExceptionCreate {
  candidate_statement: string
}

export interface ReviewDecisionCreate {
  decision: 'approve' | 'reject' | 'escalate'
  notes?: string | null
}

export interface ProofUploadResponse {
  proof_id: string
  document_version_id: string
  sha256_hash: string
}
