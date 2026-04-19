import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as candidateApi from '@/services/candidateApi'
import type { CandidateProfile, CandidateProfileUpdate, ExamScore, ExamScoreCreate, TransferPreference, TransferPreferenceCreate, TransferPreferenceUpdate, ChecklistItem } from '@/types/candidate'

export const useCandidateStore = defineStore('candidate', () => {
  const profile = ref<CandidateProfile | null>(null)
  const examScores = ref<ExamScore[]>([])
  const transferPreferences = ref<TransferPreference[]>([])
  const checklist = ref<ChecklistItem[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function initSelfProfile(): Promise<CandidateProfile | null> {
    loading.value = true
    error.value = null
    try {
      const created = await candidateApi.createSelfProfile()
      profile.value = created
      return created
    } catch (e) {
      error.value = (e as Error).message
      return null
    } finally {
      loading.value = false
    }
  }

  async function loadProfile(candidateId: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      profile.value = await candidateApi.getProfile(candidateId)
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  async function saveProfile(candidateId: string, data: CandidateProfileUpdate): Promise<boolean> {
    loading.value = true
    error.value = null
    try {
      profile.value = await candidateApi.updateProfile(candidateId, data)
      return true
    } catch (e) {
      error.value = (e as Error).message
      return false
    } finally {
      loading.value = false
    }
  }

  async function loadExamScores(candidateId: string): Promise<void> {
    try {
      examScores.value = await candidateApi.listExamScores(candidateId)
    } catch (e) {
      error.value = (e as Error).message
    }
  }

  async function addExamScore(candidateId: string, data: ExamScoreCreate): Promise<boolean> {
    try {
      const score = await candidateApi.addExamScore(candidateId, data)
      examScores.value = [...examScores.value, score]
      return true
    } catch (e) {
      error.value = (e as Error).message
      return false
    }
  }

  async function loadTransferPreferences(candidateId: string): Promise<void> {
    try {
      transferPreferences.value = await candidateApi.listTransferPreferences(candidateId)
    } catch (e) {
      error.value = (e as Error).message
    }
  }

  async function addTransferPreference(
    candidateId: string,
    data: TransferPreferenceCreate,
  ): Promise<boolean> {
    try {
      const pref = await candidateApi.addTransferPreference(candidateId, data)
      transferPreferences.value = [...transferPreferences.value, pref]
      return true
    } catch (e) {
      error.value = (e as Error).message
      return false
    }
  }

  async function updateTransferPreference(
    candidateId: string,
    prefId: string,
    data: TransferPreferenceUpdate,
  ): Promise<boolean> {
    try {
      const updated = await candidateApi.updateTransferPreference(candidateId, prefId, data)
      transferPreferences.value = transferPreferences.value.map((p) =>
        p.id === prefId ? updated : p,
      )
      return true
    } catch (e) {
      error.value = (e as Error).message
      return false
    }
  }

  async function loadChecklist(candidateId: string): Promise<void> {
    try {
      checklist.value = await candidateApi.getChecklist(candidateId)
    } catch (e) {
      error.value = (e as Error).message
    }
  }

  function clearError(): void {
    error.value = null
  }

  function reset(): void {
    profile.value = null
    examScores.value = []
    transferPreferences.value = []
    checklist.value = []
    error.value = null
  }

  return {
    profile,
    examScores,
    transferPreferences,
    checklist,
    loading,
    error,
    initSelfProfile,
    loadProfile,
    saveProfile,
    loadExamScores,
    addExamScore,
    loadTransferPreferences,
    addTransferPreference,
    updateTransferPreference,
    loadChecklist,
    clearError,
    reset,
  }
})
