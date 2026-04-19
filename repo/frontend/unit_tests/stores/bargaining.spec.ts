// FE-UNIT: bargaining store — computed offer state, expiry, canSubmitOffer.

import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useBargainingStore } from '@/stores/bargaining'
import type { BargainingThread } from '@/types/order'

function makeThread(overrides: Partial<BargainingThread> = {}): BargainingThread {
  return {
    id: 't1',
    order_id: 'o1',
    status: 'open',
    window_starts_at: new Date(Date.now() - 1000).toISOString(),
    window_expires_at: new Date(Date.now() + 48 * 3600 * 1000).toISOString(),
    offers: [],
    counter_amount: null,
    counter_count: 0,
    counter_at: null,
    resolved_at: null,
    ...overrides,
  }
}

describe('useBargainingStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('offersRemaining defaults to 3 with no thread', () => {
    const store = useBargainingStore()
    expect(store.offersRemaining).toBe(3)
  })

  it('offersRemaining decrements with each offer', () => {
    const store = useBargainingStore()
    store.thread = makeThread({
      offers: [
        { id: 'o1', thread_id: 't1', offer_number: 1, amount: '100', submitted_by: 'u', outcome: 'pending', submitted_at: '2026-01-01T00:00:00Z' },
        { id: 'o2', thread_id: 't1', offer_number: 2, amount: '120', submitted_by: 'u', outcome: 'pending', submitted_at: '2026-01-01T00:00:00Z' },
      ],
    })
    expect(store.offersRemaining).toBe(1)
  })

  it('isExpired is false for future window', () => {
    const store = useBargainingStore()
    store.thread = makeThread()
    expect(store.isExpired).toBe(false)
  })

  it('isExpired is true for past window', () => {
    const store = useBargainingStore()
    store.thread = makeThread({
      window_expires_at: new Date(Date.now() - 1000).toISOString(),
    })
    expect(store.isExpired).toBe(true)
  })

  it('canSubmitOffer is true for open thread with offers remaining', () => {
    const store = useBargainingStore()
    store.thread = makeThread({ status: 'open' })
    expect(store.canSubmitOffer).toBe(true)
  })

  it('canSubmitOffer is false when thread status is not open', () => {
    const store = useBargainingStore()
    store.thread = makeThread({ status: 'countered' })
    expect(store.canSubmitOffer).toBe(false)
  })

  it('canAcceptCounter is true when status is countered', () => {
    const store = useBargainingStore()
    store.thread = makeThread({ status: 'countered' })
    expect(store.canAcceptCounter).toBe(true)
  })

  it('canAcceptCounter is false when expired', () => {
    const store = useBargainingStore()
    store.thread = makeThread({
      status: 'countered',
      window_expires_at: new Date(Date.now() - 1000).toISOString(),
    })
    expect(store.canAcceptCounter).toBe(false)
  })
})
