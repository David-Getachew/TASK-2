// FE<->BE contract: bargaining mutation bodies.
//
// Regression pin for audit-2 blocker on bargaining. The BE schemas
// (src/schemas/bargaining.py) require nonce+timestamp on OfferCreate,
// BargainingAcceptRequest, and CounterAcceptRequest. Missing fields would
// pre-emptively 422 the candidate/reviewer mutation despite the signed
// request headers passing. Each mutation here is driven by the real
// bargainingApi wrapper and the fetch body is asserted field-by-field.

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import { getOrCreateDeviceKey } from '@/services/deviceKey'
import * as bargainingApi from '@/services/bargainingApi'

vi.mock('@/services/deviceKey', async () => {
  const actual = await vi.importActual<typeof import('@/services/deviceKey')>(
    '@/services/deviceKey',
  )
  return {
    ...actual,
    getOrCreateDeviceKey: vi.fn(),
  }
})

vi.mock('@/services/requestSigner', async () => {
  const actual = await vi.importActual<typeof import('@/services/requestSigner')>(
    '@/services/requestSigner',
  )
  return {
    ...actual,
    signRequest: vi.fn().mockResolvedValue('stub-signature'),
  }
})

const originalFetch = globalThis.fetch

function stubFetch(): { capture: () => Record<string, unknown> | null } {
  let body: Record<string, unknown> | null = null
  globalThis.fetch = vi.fn(async (_url: RequestInfo | URL, init?: RequestInit) => {
    body = init?.body ? JSON.parse(init.body as string) : null
    return new Response(
      JSON.stringify({
        success: true,
        data: {
          id: 't-1',
          order_id: 'order-1',
          status: 'open',
          window_starts_at: '2026-01-01T00:00:00Z',
          window_expires_at: '2026-01-02T00:00:00Z',
          offers: [],
          counter_amount: null,
          counter_count: 0,
          counter_at: null,
          resolved_at: null,
        },
        meta: { trace_id: 't', timestamp: new Date().toISOString() },
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } },
    )
  }) as unknown as typeof fetch
  return { capture: () => body }
}

describe('FE<->BE contract: bargaining mutation bodies', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const auth = useAuthStore()
    auth.setTokens({
      access_token: 'a',
      refresh_token: 'r',
      token_type: 'bearer',
      expires_in: 900,
    })
    ;(getOrCreateDeviceKey as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      deviceId: 'dev-1',
      privateKey: {} as unknown as CryptoKey,
    })
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
    vi.clearAllMocks()
  })

  it('submitOffer sends amount, nonce, timestamp', async () => {
    const sink = stubFetch()
    await bargainingApi.submitOffer('order-1', '150.00')
    const body = sink.capture() as Record<string, unknown>
    expect(body.amount).toBe('150.00')
    expect(typeof body.nonce).toBe('string')
    expect(typeof body.timestamp).toBe('string')
  })

  it('acceptOffer sends offer_id, nonce, timestamp', async () => {
    const sink = stubFetch()
    await bargainingApi.acceptOffer('order-1', 'offer-1')
    const body = sink.capture() as Record<string, unknown>
    expect(body.offer_id).toBe('offer-1')
    expect(typeof body.nonce).toBe('string')
    expect(typeof body.timestamp).toBe('string')
  })

  it('acceptCounter sends nonce, timestamp', async () => {
    const sink = stubFetch()
    await bargainingApi.acceptCounter('order-1')
    const body = sink.capture() as Record<string, unknown>
    expect(typeof body.nonce).toBe('string')
    expect(typeof body.timestamp).toBe('string')
  })
})
