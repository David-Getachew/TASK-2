// FE-UNIT: candidate AfterSalesView — form submits to store.submitAfterSales
// with the exact request_type/description payload the BE expects, and the
// surfaced history reflects the listAfterSales response.

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import AfterSalesView from '@/views/candidate/orders/AfterSalesView.vue'
import { useOrderStore } from '@/stores/order'

const submitAfterSalesMock = vi.fn()
const listAfterSalesMock = vi.fn()

vi.mock('@/services/refundApi', () => ({
  submitAfterSales: submitAfterSalesMock,
  listAfterSales: listAfterSalesMock,
  initiateRefund: vi.fn(),
  processRefund: vi.fn(),
  getRefund: vi.fn(),
  resolveAfterSales: vi.fn(),
}))

vi.mock('@/services/orderApi', () => ({
  getOrder: vi.fn().mockResolvedValue(null),
  listOrdersPaginated: vi.fn(),
  listServiceItems: vi.fn().mockResolvedValue([]),
  createOrder: vi.fn(),
  cancelOrder: vi.fn(),
  confirmReceipt: vi.fn(),
  advanceOrder: vi.fn(),
}))

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/candidate/orders/:orderId/after-sales', component: AfterSalesView },
    { path: '/candidate/orders/:orderId', component: { template: '<div />' } },
  ],
})

describe('Candidate AfterSalesView', () => {
  beforeEach(async () => {
    setActivePinia(createPinia())
    submitAfterSalesMock.mockReset()
    listAfterSalesMock.mockReset().mockResolvedValue([])
    await router.push('/candidate/orders/order-1/after-sales')
    await router.isReady()
  })

  it('renders the after-sales view container', async () => {
    const wrapper = mount(AfterSalesView, { global: { plugins: [router] } })
    await flushPromises()
    expect(wrapper.find('[data-testid="candidate-after-sales-view"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="after-sales-form"]').exists()).toBe(true)
  })

  it('submit button is disabled until both fields are filled', async () => {
    const wrapper = mount(AfterSalesView, { global: { plugins: [router] } })
    await flushPromises()
    const btn = wrapper.get('[data-testid="after-sales-submit"]').element as HTMLButtonElement
    expect(btn.disabled).toBe(true)

    await wrapper.get('[data-testid="after-sales-type"]').setValue('complaint')
    await wrapper.get('[data-testid="after-sales-description"]').setValue('Missed delivery')
    expect((wrapper.get('[data-testid="after-sales-submit"]').element as HTMLButtonElement).disabled).toBe(false)
  })

  it('submit calls store.submitAfterSales with the exact FE/BE payload shape', async () => {
    const wrapper = mount(AfterSalesView, { global: { plugins: [router] } })
    await flushPromises()
    const store = useOrderStore()
    const spy = vi.spyOn(store, 'submitAfterSales').mockResolvedValue({
      id: 'req-1',
      order_id: 'order-1',
      requested_by: 'u1',
      request_type: 'complaint',
      description: 'Missed delivery',
      status: 'open',
      window_expires_at: '2026-01-15T00:00:00Z',
      resolved_by: null,
      resolved_at: null,
      resolution_notes: null,
      created_at: '2026-01-01T00:00:00Z',
    })

    await wrapper.get('[data-testid="after-sales-type"]').setValue('complaint')
    await wrapper.get('[data-testid="after-sales-description"]').setValue('Missed delivery')
    await wrapper.get('[data-testid="after-sales-form"]').trigger('submit')
    await flushPromises()

    expect(spy).toHaveBeenCalledWith('order-1', {
      request_type: 'complaint',
      description: 'Missed delivery',
    })
  })

  it('history section renders prior after-sales requests', async () => {
    listAfterSalesMock.mockResolvedValueOnce([
      {
        id: 'req-1',
        order_id: 'order-1',
        requested_by: 'u1',
        request_type: 'refund_request',
        description: 'Service not delivered',
        status: 'resolved',
        window_expires_at: '2026-01-15T00:00:00Z',
        resolved_by: 'rev-1',
        resolved_at: '2026-01-05T00:00:00Z',
        resolution_notes: 'Processed refund',
        created_at: '2026-01-01T00:00:00Z',
      },
    ])
    const wrapper = mount(AfterSalesView, { global: { plugins: [router] } })
    await flushPromises()
    expect(wrapper.text()).toContain('refund_request')
    expect(wrapper.text()).toContain('Processed refund')
  })
})
