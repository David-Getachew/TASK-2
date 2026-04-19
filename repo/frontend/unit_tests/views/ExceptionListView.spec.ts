// FE-UNIT: ExceptionListView — list renders, empty state shown, pagination present, cards linked.

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import ExceptionListView from '@/views/candidate/attendance/ExceptionListView.vue'
import { useAttendanceStore } from '@/stores/attendance'
import type { AttendanceException } from '@/types/attendance'

vi.mock('@/services/attendanceApi', () => ({
  listExceptions: vi.fn().mockResolvedValue({ data: [], pagination: { page: 1, page_size: 20, total: 0, total_pages: 0 } }),
  createException: vi.fn(),
  getException: vi.fn(),
  uploadProof: vi.fn(),
  submitReview: vi.fn(),
  listAnomalies: vi.fn().mockResolvedValue([]),
  flagAnomaly: vi.fn(),
}))

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/candidate/attendance', component: ExceptionListView },
    { path: '/candidate/attendance/new', component: { template: '<div />' } },
    { path: '/candidate/attendance/:exceptionId', component: { template: '<div />' } },
  ],
})

function makeException(id: string): AttendanceException {
  return {
    id, candidate_id: 'user-1', anomaly_id: 'anom-1',
    status: 'pending_proof', current_stage: 'initial',
    candidate_statement: 'I was absent due to illness.',
    submitted_at: '2024-01-01T00:00:00Z',
    review_steps: [],
    proofs: [],
    created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z',
  }
}

describe('ExceptionListView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders exception list container', async () => {
    const wrapper = mount(ExceptionListView, { global: { plugins: [router] } })
    await flushPromises()
    expect(wrapper.find('[data-testid="exception-list-view"]').exists()).toBe(true)
  })

  it('shows empty state when no exceptions', async () => {
    const wrapper = mount(ExceptionListView, { global: { plugins: [router] } })
    await flushPromises()
    expect(wrapper.text()).toContain('No attendance exceptions filed.')
  })

  it('renders exception cards when exceptions exist', async () => {
    const wrapper = mount(ExceptionListView, { global: { plugins: [router] } })
    await flushPromises()
    const store = useAttendanceStore()
    store.exceptions = [makeException('exc-1'), makeException('exc-2')]
    await wrapper.vm.$nextTick()
    expect(wrapper.findAll('.exception-card')).toHaveLength(2)
  })

  it('exception card shows candidate statement', async () => {
    const wrapper = mount(ExceptionListView, { global: { plugins: [router] } })
    await flushPromises()
    const store = useAttendanceStore()
    store.exceptions = [makeException('exc-1')]
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('I was absent due to illness.')
  })

  it('shows file exception link', async () => {
    const wrapper = mount(ExceptionListView, { global: { plugins: [router] } })
    await flushPromises()
    expect(wrapper.find('a[href="/candidate/attendance/new"]').exists()).toBe(true)
  })

  it('renders view links for each exception', async () => {
    const wrapper = mount(ExceptionListView, { global: { plugins: [router] } })
    await flushPromises()
    const store = useAttendanceStore()
    store.exceptions = [makeException('exc-1')]
    await wrapper.vm.$nextTick()
    expect(wrapper.find('a[href="/candidate/attendance/exc-1"]').exists()).toBe(true)
  })
})
