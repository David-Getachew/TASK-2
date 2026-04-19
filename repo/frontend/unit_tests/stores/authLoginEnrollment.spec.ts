// FE-UNIT: auth store login path invokes device enrollment after a
// successful login, so signed mutations issued immediately afterward
// already have a persisted device_id. Covers audit-3 Blocker #1.

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

const loginMock = vi.fn()
const meMock = vi.fn()
const ensureEnrolledMock = vi.fn()

vi.mock('@/services/authApi', () => ({
  login: (args: unknown) => loginMock(args),
  me: () => meMock(),
  refresh: vi.fn(),
  logout: vi.fn(),
}))

vi.mock('@/composables/useDeviceKey', () => ({
  useDeviceKey: () => ({
    ensureEnrolled: ensureEnrolledMock,
  }),
}))

describe('auth store login → device enrollment', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    loginMock.mockReset().mockResolvedValue({
      access_token: 'at',
      refresh_token: 'rt',
      token_type: 'bearer',
      expires_in: 900,
      role: 'candidate',
      cohort_config: null,
    })
    meMock.mockReset().mockResolvedValue({
      user: {
        id: 'u1',
        username: 'candidate1',
        role: 'candidate',
        full_name: 'C1',
        is_active: true,
        last_login_at: null,
      },
      cohort_config: null,
      device_id: null,
      candidate_id: 'c1',
    })
    ensureEnrolledMock.mockReset().mockResolvedValue('dev-42')
  })

  it('invokes useDeviceKey().ensureEnrolled() after a successful login', async () => {
    const { useAuthStore } = await import('@/stores/auth')
    const auth = useAuthStore()
    await auth.login({ username: 'candidate1', password: 'pw' })

    expect(loginMock).toHaveBeenCalledTimes(1)
    expect(meMock).toHaveBeenCalledTimes(1)
    expect(ensureEnrolledMock).toHaveBeenCalledTimes(1)
  })

  it('does not roll back the session if enrollment fails', async () => {
    ensureEnrolledMock.mockRejectedValueOnce(new Error('WebCrypto unavailable'))
    const { useAuthStore } = await import('@/stores/auth')
    const auth = useAuthStore()

    await auth.login({ username: 'candidate1', password: 'pw' })

    expect(auth.isAuthenticated).toBe(true)
    expect(auth.lastError).toContain('WebCrypto')
  })
})
