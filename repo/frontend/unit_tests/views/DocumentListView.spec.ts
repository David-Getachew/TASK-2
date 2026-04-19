// FE-UNIT: DocumentListView — checklist rendered, documents table, empty state, resubmission reason shown.

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import DocumentListView from '@/views/candidate/documents/DocumentListView.vue'
import { useDocumentStore } from '@/stores/document'
import { useCandidateStore } from '@/stores/candidate'
import { useAuthStore } from '@/stores/auth'

vi.mock('@/services/documentApi', () => ({
  listDocuments: vi.fn().mockResolvedValue([]),
  uploadDocument: vi.fn(),
  reviewDocument: vi.fn(),
  downloadDocument: vi.fn(),
}))

vi.mock('@/services/candidateApi', () => ({
  getProfile: vi.fn().mockResolvedValue(null),
  getChecklist: vi.fn().mockResolvedValue([
    {
      requirement_id: 'req-1',
      requirement_code: 'TRANSCRIPT',
      display_name: 'Official Transcript',
      is_mandatory: true,
      status: null,
      document_id: null,
      version_number: null,
    },
    {
      requirement_id: 'req-2',
      requirement_code: 'ID',
      display_name: 'Government ID',
      is_mandatory: true,
      status: 'approved',
      document_id: 'doc-9',
      version_number: 1,
    },
  ]),
  updateProfile: vi.fn(),
  listExamScores: vi.fn().mockResolvedValue([]),
  listTransferPreferences: vi.fn().mockResolvedValue([]),
  addExamScore: vi.fn(),
  addTransferPreference: vi.fn(),
  updateTransferPreference: vi.fn(),
  createProfileForUser: vi.fn(),
  createSelfProfile: vi.fn().mockResolvedValue({
    id: 'cand-new',
    user_id: 'user-1',
    preferred_name: null,
    application_year: null,
    application_status: null,
    program_code: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }),
}))

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/candidate/documents', component: DocumentListView },
    { path: '/candidate/documents/upload', component: { template: '<div />' } },
  ],
})

describe('DocumentListView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const auth = useAuthStore()
    auth.user = { id: 'user-1', username: 'testuser', role: 'candidate', full_name: 'Test User', is_active: true, last_login_at: null }
    auth.candidateId = 'cand-1'
  })

  it('renders the document list container', async () => {
    const wrapper = mount(DocumentListView, { global: { plugins: [router] } })
    await flushPromises()
    expect(wrapper.find('[data-testid="document-list-view"]').exists()).toBe(true)
  })

  it('shows empty state when no documents uploaded', async () => {
    const wrapper = mount(DocumentListView, { global: { plugins: [router] } })
    await flushPromises()
    expect(wrapper.text()).toContain('No documents uploaded yet.')
  })

  it('renders checklist items from store', async () => {
    const wrapper = mount(DocumentListView, { global: { plugins: [router] } })
    await flushPromises()
    const candidateStore = useCandidateStore()
    expect(candidateStore.checklist).toHaveLength(2)
    expect(candidateStore.checklist[0].display_name).toBe('Official Transcript')
  })

  it('shows documents table when documents are present', async () => {
    const wrapper = mount(DocumentListView, { global: { plugins: [router] } })
    await flushPromises()
    const docStore = useDocumentStore()
    docStore.documents = [
      {
        id: 'doc-1',
        candidate_id: 'cand-1',
        requirement_id: 'req-1',
        requirement_code: 'TRANSCRIPT',
        document_type: 'transcript',
        current_status: 'pending_review',
        current_version: 1,
        resubmission_reason: null,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        latest_version: null,
      },
    ]
    await wrapper.vm.$nextTick()
    expect(wrapper.find('table').exists()).toBe(true)
    expect(wrapper.text()).toContain('TRANSCRIPT')
  })

  it('displays resubmission reason when present', async () => {
    const wrapper = mount(DocumentListView, { global: { plugins: [router] } })
    await flushPromises()
    const docStore = useDocumentStore()
    docStore.documents = [
      {
        id: 'doc-1',
        candidate_id: 'cand-1',
        requirement_id: 'req-1',
        requirement_code: 'TRANSCRIPT',
        document_type: 'transcript',
        current_status: 'needs_resubmission',
        current_version: 1,
        resubmission_reason: 'Document is blurry',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        latest_version: null,
      },
    ]
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Document is blurry')
  })

  it('shows upload button link', async () => {
    const wrapper = mount(DocumentListView, { global: { plugins: [router] } })
    await flushPromises()
    expect(wrapper.find('a[href="/candidate/documents/upload"]').exists()).toBe(true)
  })

  it('shows missing-profile banner when candidateId is absent', async () => {
    const auth = useAuthStore()
    auth.candidateId = null
    const wrapper = mount(DocumentListView, { global: { plugins: [router] } })
    await flushPromises()
    expect(wrapper.text()).toContain('Candidate profile not yet initialized')
    expect(wrapper.find('[data-testid="candidate-self-init-btn"]').exists()).toBe(true)
  })

  it('clicking init button calls createSelfProfile and sets candidateId', async () => {
    const auth = useAuthStore()
    auth.candidateId = null
    const wrapper = mount(DocumentListView, { global: { plugins: [router] } })
    await flushPromises()
    const btn = wrapper.find('[data-testid="candidate-self-init-btn"]')
    expect(btn.exists()).toBe(true)
    await btn.trigger('click')
    await flushPromises()
    expect(auth.candidateId).toBe('cand-new')
  })
})
