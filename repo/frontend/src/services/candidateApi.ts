import { request } from './http'
import type {
  CandidateProfile,
  CandidateProfileUpdate,
  ExamScore,
  ExamScoreCreate,
  TransferPreference,
  TransferPreferenceCreate,
  TransferPreferenceUpdate,
  ChecklistItem,
} from '@/types/candidate'
import type { ApiListSuccess } from '@/types'

export async function createProfileForUser(userId: string): Promise<CandidateProfile> {
  return request<CandidateProfile>({
    method: 'POST',
    path: `/api/v1/candidates?user_id=${encodeURIComponent(userId)}`,
    body: null,
  })
}

export async function createSelfProfile(): Promise<CandidateProfile> {
  return request<CandidateProfile>({
    method: 'POST',
    path: `/api/v1/candidates/self`,
    body: null,
  })
}

export function getProfile(candidateId: string): Promise<CandidateProfile> {
  return request<CandidateProfile>({
    method: 'GET',
    path: `/api/v1/candidates/${encodeURIComponent(candidateId)}`,
  })
}

export function updateProfile(
  candidateId: string,
  data: CandidateProfileUpdate,
): Promise<CandidateProfile> {
  return request<CandidateProfile>({
    method: 'PATCH',
    path: `/api/v1/candidates/${encodeURIComponent(candidateId)}`,
    body: data,
  })
}

export function listExamScores(candidateId: string): Promise<ExamScore[]> {
  return request<ExamScore[]>({
    method: 'GET',
    path: `/api/v1/candidates/${encodeURIComponent(candidateId)}/exam-scores`,
  })
}

export function addExamScore(
  candidateId: string,
  data: ExamScoreCreate,
): Promise<ExamScore> {
  return request<ExamScore>({
    method: 'POST',
    path: `/api/v1/candidates/${encodeURIComponent(candidateId)}/exam-scores`,
    body: data,
  })
}

export function listTransferPreferences(candidateId: string): Promise<TransferPreference[]> {
  return request<TransferPreference[]>({
    method: 'GET',
    path: `/api/v1/candidates/${encodeURIComponent(candidateId)}/transfer-preferences`,
  })
}

export function addTransferPreference(
  candidateId: string,
  data: TransferPreferenceCreate,
): Promise<TransferPreference> {
  return request<TransferPreference>({
    method: 'POST',
    path: `/api/v1/candidates/${encodeURIComponent(candidateId)}/transfer-preferences`,
    body: data,
  })
}

export function updateTransferPreference(
  candidateId: string,
  prefId: string,
  data: TransferPreferenceUpdate,
): Promise<TransferPreference> {
  return request<TransferPreference>({
    method: 'PATCH',
    path: `/api/v1/candidates/${encodeURIComponent(candidateId)}/transfer-preferences/${encodeURIComponent(prefId)}`,
    body: data,
  })
}

export function getChecklist(candidateId: string): Promise<ChecklistItem[]> {
  return request<ChecklistItem[]>({
    method: 'GET',
    path: `/api/v1/candidates/${encodeURIComponent(candidateId)}/checklist`,
  })
}
