// FE-UNIT: ExceptionReviewView — approve/reject/escalate radios, escalate only at initial stage, submit records decision.

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import ExceptionReviewView from '@/views/staff/attendance/ExceptionReviewView.vue'
import { useAttendanceStore } from '@/stores/attendance'
import type { AttendanceException } from '@/types/attendance'

vi.mock('@/services/attendanceApi', () => ({
  listExceptions: vi.fn().mockResolvedValue({ data: [], pagination: { page: 1, page_size: 20, total: 0, total_pages: 0 } }),
  createException: vi.fn(),
  getException: vi.fn().mockResolvedValue(null),
  uploadProof: vi.fn(),
  submitReview: vi.fn().mockResolvedValue({ id: 'step-1', decision: 'approve' }),
  listAnomalies: vi.fn().mockResolvedValue([]),
  flagAnomaly: vi.fn(),
}))

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/staff/exceptions/:exceptionId/review', component: ExceptionReviewView },
    { path: '/staff/exceptions', component: { template: '<div />' } },
  ],
})

function makeException(stage: 'initial' | 'final' = 'initial'): AttendanceException {
  return {
    id: 'exc-1', candidate_id: 'user-1', anomaly_id: 'anom-1',
    status: 'pending_initial_review', current_stage: stage,
    candidate_statement: 'I was ill that day.',
    submitted_at: '2024-01-01T00:00:00Z',
    review_steps: [],
    proofs: [],
    created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z',
  }
}

describe('ExceptionReviewView', () => {
  beforeEach(async () => {
    setActivePinia(createPinia())
    await router.push('/staff/exceptions/exc-1/review')
    await router.isReady()
  })

  it('renders the exception review container', async () => {
    const wrapper = mount(ExceptionReviewView, { global: { plugins: [router] } })
    await flushPromises()
    expect(wrapper.find('[data-testid="exception-review-view"]').exists()).toBe(true)
  })

  it('shows approve and reject radio buttons', async () => {
    const wrapper = mount(ExceptionReviewView, { global: { plugins: [router] } })
    await flushPromises()
    const store = useAttendanceStore()
    store.currentException = makeException('initial')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="decision-approve"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="decision-reject"]').exists()).toBe(true)
  })

  it('shows escalate option when current_stage is initial', async () => {
    const wrapper = mount(ExceptionReviewView, { global: { plugins: [router] } })
    await flushPromises()
    const store = useAttendanceStore()
    store.currentException = makeException('initial')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="decision-escalate"]').exists()).toBe(true)
  })

  it('hides escalate option when current_stage is final', async () => {
    const wrapper = mount(ExceptionReviewView, { global: { plugins: [router] } })
    await flushPromises()
    const store = useAttendanceStore()
    store.currentException = makeException('final')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="decision-escalate"]').exists()).toBe(false)
  })

  it('shows candidate statement when exception is loaded', async () => {
    const wrapper = mount(ExceptionReviewView, { global: { plugins: [router] } })
    await flushPromises()
    const store = useAttendanceStore()
    store.currentException = makeException('initial')
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('I was ill that day.')
  })

  it('shows success banner and submit becomes disabled after review', async () => {
    const wrapper = mount(ExceptionReviewView, { global: { plugins: [router] } })
    await flushPromises()
    const store = useAttendanceStore()
    store.currentException = makeException('initial')
    store.submitReview = vi.fn().mockResolvedValue(true)
    await wrapper.vm.$nextTick()
    await (wrapper.vm as any).submit()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Decision recorded')
    const btn = wrapper.find('[data-testid="exception-review-submit"]')
    expect((btn.element as HTMLButtonElement).disabled).toBe(true)
  })

  it('renders review form', async () => {
    const wrapper = mount(ExceptionReviewView, { global: { plugins: [router] } })
    await flushPromises()
    const store = useAttendanceStore()
    store.currentException = makeException('initial')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="exception-review-form"]').exists()).toBe(true)
  })

  it('renders proof metadata when proofs are present', async () => {
    const wrapper = mount(ExceptionReviewView, { global: { plugins: [router] } })
    await flushPromises()
    const store = useAttendanceStore()
    store.currentException = {
      ...makeException('initial'),
      proofs: [
        {
          id: 'proof-1', exception_id: 'exc-1', document_version_id: 'dv-1',
          uploaded_by: 'user-1', description: 'Doctor note',
          uploaded_at: '2024-01-03T00:00:00Z',
        },
      ],
    }
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="exception-proofs"]').exists()).toBe(true)
    expect(wrapper.findAll('[data-testid="exception-proof-item"]').length).toBe(1)
    expect(wrapper.text()).toContain('Doctor note')
  })

  it('renders empty-proofs message when no proofs are attached', async () => {
    const wrapper = mount(ExceptionReviewView, { global: { plugins: [router] } })
    await flushPromises()
    const store = useAttendanceStore()
    store.currentException = makeException('initial')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="exception-proofs-empty"]').exists()).toBe(true)
  })

  it('shows prior review steps when present', async () => {
    const wrapper = mount(ExceptionReviewView, { global: { plugins: [router] } })
    await flushPromises()
    const store = useAttendanceStore()
    store.currentException = {
      ...makeException('final'),
      review_steps: [
        {
          id: 'step-1', exception_id: 'exc-1', step_order: 1,
          stage: 'initial', reviewer_id: 'rev-1', reviewer_role: 'proctor',
          decision: 'escalate', notes: 'Needs supervisor review.',
          is_escalated: true, decided_at: '2024-01-02T00:00:00Z',
        },
      ],
    }
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Needs supervisor review.')
  })
})
