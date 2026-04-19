import { describe, it, expect } from 'vitest'
import { isNullableString, isRecord, isString, loadFixture } from './helpers'

function isReviewStep(value: unknown): boolean {
  if (!isRecord(value)) return false
  return (
    isString(value.id) &&
    isString(value.exception_id) &&
    typeof value.step_order === 'number' &&
    isString(value.stage) &&
    isString(value.reviewer_id) &&
    isString(value.reviewer_role) &&
    isString(value.decision) &&
    isNullableString(value.notes) &&
    isString(value.decided_at) &&
    typeof value.is_escalated === 'boolean'
  )
}

function isProof(value: unknown): boolean {
  if (!isRecord(value)) return false
  return (
    isString(value.id) &&
    isString(value.exception_id) &&
    isString(value.document_version_id) &&
    isString(value.uploaded_by) &&
    isString(value.uploaded_at)
  )
}

function isAttendanceException(value: unknown): boolean {
  if (!isRecord(value)) return false
  if (!Array.isArray(value.review_steps)) return false
  if (!Array.isArray(value.proofs)) return false
  return (
    isString(value.id) &&
    isNullableString(value.anomaly_id) &&
    isString(value.candidate_id) &&
    isString(value.status) &&
    isString(value.current_stage) &&
    isNullableString(value.candidate_statement) &&
    isNullableString(value.submitted_at) &&
    isString(value.created_at) &&
    isString(value.updated_at) &&
    value.review_steps.every(isReviewStep) &&
    value.proofs.every(isProof)
  )
}

describe('FE<->BE contract: attendance exception', () => {
  it('matches ExceptionRead fixture shape', () => {
    const fixture = loadFixture<unknown>('attendanceException.json')
    expect(isAttendanceException(fixture)).toBe(true)
  })
})
