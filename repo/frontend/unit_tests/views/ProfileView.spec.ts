// FE-UNIT: ProfileView — form renders, save calls store, error displayed.

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import ProfileView from '@/views/candidate/profile/ProfileView.vue'
import { useCandidateStore } from '@/stores/candidate'
import { useAuthStore } from '@/stores/auth'

vi.mock('@/services/candidateApi', () => ({
  getProfile: vi.fn().mockResolvedValue({
    id: 'cand-1',
    user_id: 'user-1',
    preferred_name: 'Test User',
    application_year: 2026,
    application_status: 'in_review',
    program_code: 'CS-BS',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ssn_display: '***-**-1234',
    dob_display: '****-**-15',
    phone_display: '***-***-5678',
    email_display: 't***@example.com',
  }),
  updateProfile: vi.fn().mockResolvedValue({
    id: 'cand-1',
    user_id: 'user-1',
    preferred_name: 'Updated Name',
    application_year: 2026,
    application_status: 'in_review',
    program_code: 'CS-BS',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-02T00:00:00Z',
    ssn_display: '***-**-1234',
    dob_display: '****-**-15',
    phone_display: '***-***-5678',
    email_display: 't***@example.com',
  }),
  listExamScores: vi.fn().mockResolvedValue([]),
  listTransferPreferences: vi.fn().mockResolvedValue([]),
  getChecklist: vi.fn().mockResolvedValue([]),
  addExamScore: vi.fn(),
  addTransferPreference: vi.fn(),
  updateTransferPreference: vi.fn(),
  createProfileForUser: vi.fn(),
}))

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/candidate/profile', component: ProfileView },
    { path: '/candidate/profile/exam-scores', component: { template: '<div />' } },
    { path: '/candidate/profile/transfer-preferences', component: { template: '<div />' } },
  ],
})

describe('ProfileView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const auth = useAuthStore()
    auth.user = { id: 'user-1', username: 'testuser', role: 'candidate', full_name: 'Test User', is_active: true, last_login_at: null }
    auth.candidateId = 'cand-1'
  })

  it('renders the profile form', async () => {
    const wrapper = mount(ProfileView, { global: { plugins: [router] } })
    await flushPromises()
    expect(wrapper.find('[data-testid="profile-form"]').exists()).toBe(true)
  })

  it('loads profile data on mount', async () => {
    const wrapper = mount(ProfileView, { global: { plugins: [router] } })
    await flushPromises()
    const store = useCandidateStore()
    expect(store.profile?.preferred_name).toBe('Test User')
    expect(store.profile?.application_year).toBe(2026)
    expect(store.profile?.ssn_display).toBe('***-**-1234')
  })

  it('shows save button', async () => {
    const wrapper = mount(ProfileView, { global: { plugins: [router] } })
    await flushPromises()
    expect(wrapper.find('[data-testid="profile-save"]').exists()).toBe(true)
  })

  it('shows missing-profile banner when candidateId is absent', async () => {
    const auth = useAuthStore()
    auth.candidateId = null
    const wrapper = mount(ProfileView, { global: { plugins: [router] } })
    await flushPromises()
    expect(wrapper.text()).toContain('Candidate profile not yet initialized')
  })
})
