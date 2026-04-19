// FE-UNIT: http.ts — offline/network-failure mutations get enqueued into
// the offline queue and surface as OfflineQueuedError. GETs and already-
// retried requests do NOT enqueue.

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { request, OfflineQueuedError } from '@/services/http'
import { getOfflineQueue, __resetOfflineQueueForTests } from '@/services/offlineQueue'

const originalFetch = globalThis.fetch
let originalOnLine: PropertyDescriptor | undefined

function setNavigatorOnline(value: boolean): void {
  Object.defineProperty(globalThis.navigator, 'onLine', {
    configurable: true,
    get: () => value,
  })
}

beforeEach(() => {
  setActivePinia(createPinia())
  __resetOfflineQueueForTests()
  originalOnLine = Object.getOwnPropertyDescriptor(globalThis.navigator, 'onLine')
})

afterEach(() => {
  globalThis.fetch = originalFetch
  if (originalOnLine) {
    Object.defineProperty(globalThis.navigator, 'onLine', originalOnLine)
  }
})

describe('http offline enqueue', () => {
  it('queues a POST mutation when navigator.onLine is false', async () => {
    setNavigatorOnline(false)
    globalThis.fetch = vi.fn(() => {
      throw new Error('fetch should not have been called while offline')
    }) as unknown as typeof fetch

    await expect(
      request({ method: 'POST', path: '/api/v1/orders/o1/cancel', body: { reason: 'x' } }),
    ).rejects.toBeInstanceOf(OfflineQueuedError)

    const items = await getOfflineQueue().list()
    expect(items).toHaveLength(1)
    expect(items[0].method).toBe('POST')
    expect(items[0].path).toBe('/api/v1/orders/o1/cancel')
    expect(items[0].idempotencyKey).toMatch(/^idem-/)
  })

  it('queues a mutation when fetch throws a network error', async () => {
    setNavigatorOnline(true)
    globalThis.fetch = vi.fn(() => {
      throw new TypeError('NetworkError when attempting to fetch resource.')
    }) as unknown as typeof fetch

    await expect(
      request({ method: 'PATCH', path: '/api/v1/orders/o2', body: { note: 'x' } }),
    ).rejects.toBeInstanceOf(OfflineQueuedError)

    const items = await getOfflineQueue().list()
    expect(items).toHaveLength(1)
    expect(items[0].path).toBe('/api/v1/orders/o2')
  })

  it('preserves caller-supplied idempotency keys', async () => {
    setNavigatorOnline(false)
    globalThis.fetch = vi.fn() as unknown as typeof fetch

    try {
      await request({
        method: 'POST',
        path: '/api/v1/orders',
        body: { x: 1 },
        idempotencyKey: 'caller-key-123',
      })
    } catch (e) {
      expect(e).toBeInstanceOf(OfflineQueuedError)
      expect((e as OfflineQueuedError).idempotencyKey).toBe('caller-key-123')
    }

    const items = await getOfflineQueue().list()
    expect(items[0].idempotencyKey).toBe('caller-key-123')
  })

  it('does NOT enqueue GET requests', async () => {
    setNavigatorOnline(false)
    const networkErr = new TypeError('offline')
    globalThis.fetch = vi.fn(() => {
      throw networkErr
    }) as unknown as typeof fetch

    await expect(
      request({ method: 'GET', path: '/api/v1/orders' }),
    ).rejects.toBe(networkErr)

    const items = await getOfflineQueue().list()
    expect(items).toHaveLength(0)
  })
})
