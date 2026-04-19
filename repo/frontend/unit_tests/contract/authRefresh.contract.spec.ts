// FE<->BE contract: `/api/v1/auth/refresh` request body.
//
// Regression pin for audit-2 blocker. The BE `RefreshRequest` schema
// (src/schemas/auth.py) requires refresh_token, nonce, timestamp — if any is
// missing the handler returns 422 and the user is logged out instead of
// rotated. This test captures the request the FE actually puts on the wire
// and asserts every required field is present with the right shape.

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

describe('FE<->BE contract: POST /auth/refresh body', () => {
  const originalFetch = globalThis.fetch
  let capturedBody: Record<string, unknown> | null = null

  beforeEach(() => {
    setActivePinia(createPinia())
    capturedBody = null
    globalThis.fetch = vi.fn(async (_url: RequestInfo | URL, init?: RequestInit) => {
      capturedBody = init?.body ? JSON.parse(init.body as string) : null
      return new Response(
        JSON.stringify({
          success: true,
          data: {
            access_token: 'a',
            refresh_token: 'r2',
            token_type: 'bearer',
            expires_in: 900,
          },
          meta: { trace_id: 't', timestamp: new Date().toISOString() },
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      )
    }) as unknown as typeof fetch
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
  })

  it('sends refresh_token, nonce, and timestamp fields', async () => {
    const auth = useAuthStore()
    auth.setTokens({
      access_token: 'a',
      refresh_token: 'r1',
      token_type: 'bearer',
      expires_in: 900,
    })
    const ok = await auth.refresh()
    expect(ok).toBe(true)
    expect(capturedBody).not.toBeNull()
    const body = capturedBody as Record<string, unknown>
    expect(typeof body.refresh_token).toBe('string')
    expect(body.refresh_token).toBe('r1')
    expect(typeof body.nonce).toBe('string')
    expect((body.nonce as string).length).toBeGreaterThan(0)
    expect(typeof body.timestamp).toBe('string')
    expect((body.timestamp as string).length).toBeGreaterThan(0)
  })
})
