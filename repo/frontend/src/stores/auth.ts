// Pinia auth store: owns tokens, user identity, and session-lifecycle
// transitions. Tokens live in-memory only (avoids localStorage XSS pivot);
// IndexedDB handles the device keypair separately in deviceKey.ts.

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import * as authApi from '@/services/authApi'
import type { LoginResponse, Role, TokenPair, User } from '@/types/auth'
import { HttpError } from '@/services/http'
import { currentTimestamp, generateNonce } from '@/services/requestSigner'

interface LoginArgs {
  username: string
  password: string
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const role = ref<Role | null>(null)
  const tokens = ref<TokenPair | null>(null)
  const cohortConfig = ref<Record<string, unknown> | null>(null)
  const deviceId = ref<string | null>(null)
  // Resolved candidate profile UUID for role='candidate' (distinct from user.id).
  // Populated from GET /auth/me. null for non-candidates and before session load.
  const candidateId = ref<string | null>(null)
  const lastError = ref<string | null>(null)

  const isAuthenticated = computed(() => tokens.value !== null && user.value !== null)

  function setTokens(next: TokenPair | null): void {
    tokens.value = next
  }

  function applyLoginResponse(resp: LoginResponse): void {
    tokens.value = {
      access_token: resp.access_token,
      refresh_token: resp.refresh_token,
      token_type: resp.token_type,
      expires_in: resp.expires_in,
    }
    role.value = resp.role
    cohortConfig.value = resp.cohort_config ?? null
  }

  async function login(args: LoginArgs): Promise<void> {
    lastError.value = null
    try {
      const resp = await authApi.login({
        username: args.username,
        password: args.password,
        nonce: generateNonce(),
        timestamp: currentTimestamp(),
      })
      applyLoginResponse(resp)
      await loadSession()
      // Enroll device key immediately after session bootstrap so signed
      // mutations (document upload, order/attendance state changes,
      // password change) have a persisted device_id before they are
      // issued. Enrollment is idempotent: if the key already has a
      // device_id it returns that id without re-hitting the challenge
      // endpoint. Failure here is non-fatal — we surface it via
      // lastError so the UI can prompt re-enrollment, but we do not
      // roll back the successful login.
      try {
        const { useDeviceKey } = await import('@/composables/useDeviceKey')
        await useDeviceKey().ensureEnrolled()
      } catch (enrollErr) {
        lastError.value = (enrollErr as Error).message
      }
    } catch (err) {
      if (err instanceof HttpError) {
        lastError.value = err.envelope?.error?.message ?? err.message
      } else {
        lastError.value = (err as Error).message
      }
      throw err
    }
  }

  async function loadSession(): Promise<void> {
    if (!tokens.value) return
    const resp = await authApi.me()
    user.value = resp.user
    role.value = resp.user.role
    cohortConfig.value = resp.cohort_config ?? null
    deviceId.value = resp.device_id ?? null
    candidateId.value = resp.candidate_id ?? null
  }

  async function refresh(): Promise<boolean> {
    if (!tokens.value?.refresh_token) return false
    try {
      const resp = await authApi.refresh({
        refresh_token: tokens.value.refresh_token,
        nonce: generateNonce(),
        timestamp: currentTimestamp(),
      })
      tokens.value = {
        access_token: resp.access_token,
        refresh_token: resp.refresh_token,
        token_type: resp.token_type,
        expires_in: resp.expires_in,
      }
      return true
    } catch {
      clearSession()
      return false
    }
  }

  async function logout(): Promise<void> {
    const refreshToken = tokens.value?.refresh_token
    try {
      if (refreshToken) await authApi.logout(refreshToken)
    } catch {
      // Logout is best-effort; clear local state regardless of server result.
    } finally {
      clearSession()
    }
  }

  function clearSession(): void {
    user.value = null
    role.value = null
    tokens.value = null
    cohortConfig.value = null
    deviceId.value = null
    candidateId.value = null
  }

  function setDeviceId(id: string | null): void {
    deviceId.value = id
  }

  function setCandidateId(id: string | null): void {
    candidateId.value = id
  }

  return {
    user,
    role,
    tokens,
    cohortConfig,
    deviceId,
    candidateId,
    lastError,
    isAuthenticated,
    login,
    logout,
    refresh,
    loadSession,
    clearSession,
    setTokens,
    setDeviceId,
    setCandidateId,
  }
})
