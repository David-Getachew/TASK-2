// FE-UNIT: BargainingView — offer form shown when canSubmitOffer, hidden when expired, counter accept button appears.

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import BargainingView from '@/views/candidate/orders/BargainingView.vue'
import { useBargainingStore } from '@/stores/bargaining'
import type { BargainingThread } from '@/types/order'

vi.mock('@/services/bargainingApi', () => ({
  getThread: vi.fn().mockResolvedValue(null),
  submitOffer: vi.fn(),
  acceptOffer: vi.fn(),
  counterOffer: vi.fn(),
  acceptCounter: vi.fn(),
}))

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/candidate/orders/:orderId/bargaining', component: BargainingView },
    { path: '/candidate/orders/:orderId', component: { template: '<div />' } },
  ],
})

function makeThread(overrides: Partial<BargainingThread> = {}): BargainingThread {
  const now = new Date()
  const expires = new Date(now.getTime() + 60 * 60 * 1000).toISOString()
  return {
    id: 'thread-1', order_id: 'order-1', status: 'open',
    window_starts_at: now.toISOString(), window_expires_at: expires,
    offers: [], counter_amount: null, counter_count: 0,
    counter_at: null, resolved_at: null,
    ...overrides,
  }
}

describe('BargainingView', () => {
  beforeEach(async () => {
    setActivePinia(createPinia())
    await router.push('/candidate/orders/order-1/bargaining')
    await router.isReady()
  })

  it('renders the bargaining view container', () => {
    const wrapper = mount(BargainingView, { global: { plugins: [router] } })
    expect(wrapper.find('[data-testid="bargaining-view"]').exists()).toBe(true)
  })

  it('shows offer form when canSubmitOffer is true', async () => {
    const wrapper = mount(BargainingView, { global: { plugins: [router] } })
    await flushPromises()
    const store = useBargainingStore()
    store.thread = makeThread()
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="offer-form"]').exists()).toBe(true)
  })

  it('hides offer form when bargaining window is expired', async () => {
    const wrapper = mount(BargainingView, { global: { plugins: [router] } })
    await flushPromises()
    const store = useBargainingStore()
    const pastExpiry = new Date(Date.now() - 1000).toISOString()
    store.thread = makeThread({ status: 'open', window_expires_at: pastExpiry })
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="offer-form"]').exists()).toBe(false)
  })

  it('shows accept counter button when thread has counter and status is countered', async () => {
    const wrapper = mount(BargainingView, { global: { plugins: [router] } })
    await flushPromises()
    const store = useBargainingStore()
    store.thread = makeThread({ status: 'countered', counter_amount: '950.00' })
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="accept-counter-btn"]').exists()).toBe(true)
  })

  it('hides offer form when thread has 3 offers (offersRemaining = 0)', async () => {
    const wrapper = mount(BargainingView, { global: { plugins: [router] } })
    await flushPromises()
    const store = useBargainingStore()
    store.thread = makeThread({
      offers: [
        { id: 'o1', thread_id: 'thread-1', offer_number: 1, amount: '800', submitted_by: 'u1', outcome: 'pending', submitted_at: '2026-01-01T00:00:00Z' },
        { id: 'o2', thread_id: 'thread-1', offer_number: 2, amount: '850', submitted_by: 'u1', outcome: 'pending', submitted_at: '2026-01-01T00:00:00Z' },
        { id: 'o3', thread_id: 'thread-1', offer_number: 3, amount: '900', submitted_by: 'u1', outcome: 'pending', submitted_at: '2026-01-01T00:00:00Z' },
      ],
    })
    await wrapper.vm.$nextTick()
    // offersRemaining computed is 3 - 3 = 0, canSubmitOffer returns false
    expect(store.offersRemaining).toBe(0)
    expect(wrapper.find('[data-testid="offer-form"]').exists()).toBe(false)
  })

  it('shows expired warning banner when isExpired is true', async () => {
    const wrapper = mount(BargainingView, { global: { plugins: [router] } })
    await flushPromises()
    const store = useBargainingStore()
    const pastExpiry = new Date(Date.now() - 1000).toISOString()
    store.thread = makeThread({ window_expires_at: pastExpiry })
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('bargaining window has expired')
  })

  it('shows offers remaining count', async () => {
    const wrapper = mount(BargainingView, { global: { plugins: [router] } })
    await flushPromises()
    const store = useBargainingStore()
    store.thread = makeThread({
      offers: [
        { id: 'o1', thread_id: 'thread-1', offer_number: 1, amount: '800', submitted_by: 'u1', outcome: 'pending', submitted_at: '2026-01-01T00:00:00Z' },
      ],
    })
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('2/3')
  })
})
