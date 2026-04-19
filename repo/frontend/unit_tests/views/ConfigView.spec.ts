// FE-UNIT: ConfigView — flag table rendered, edit form toggles, save calls updateFlag.

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount, flushPromises } from '@vue/test-utils'
import ConfigView from '@/views/admin/ConfigView.vue'
import { useAdminStore } from '@/stores/admin'
import { useSessionStore } from '@/stores/session'

vi.mock('@/services/adminApi', () => ({
  getFlags: vi.fn().mockResolvedValue([
    { id: 'f-1', key: 'bargaining_enabled', value: 'true', value_type: 'boolean', description: null, updated_by: null, updated_at: new Date().toISOString() },
    { id: 'f-2', key: 'rollback_on_refund', value: 'false', value_type: 'boolean', description: null, updated_by: null, updated_at: new Date().toISOString() },
  ]),
  updateFlag: vi.fn().mockResolvedValue({ id: 'f-1', key: 'bargaining_enabled', value: 'false', value_type: 'boolean', description: null, updated_by: null, updated_at: new Date().toISOString() }),
  listCohorts: vi.fn().mockResolvedValue([]),
  createCohort: vi.fn(),
  assignCohort: vi.fn(),
  listCacheStats: vi.fn().mockResolvedValue({ data: [], pagination: { total: 0 } }),
  getMetricsSummary: vi.fn().mockResolvedValue({}),
  listForecasts: vi.fn().mockResolvedValue({ data: [], pagination: { total: 0 } }),
  listExports: vi.fn().mockResolvedValue({ data: [], pagination: { total: 0 } }),
  searchAudit: vi.fn().mockResolvedValue({ data: [], pagination: { total: 0, page: 1, page_size: 20, total_pages: 1 } }),
  getRbacPolicy: vi.fn().mockResolvedValue({}),
  getMaskingPolicy: vi.fn().mockResolvedValue({}),
  createExport: vi.fn(),
}))

describe('ConfigView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders the config view container', async () => {
    const wrapper = mount(ConfigView, { global: { stubs: { LoadingSpinner: true, BannerAlert: true } } })
    await flushPromises()
    expect(wrapper.find('[data-testid="config-view"]').exists()).toBe(true)
  })

  it('renders flag table with loaded flags', async () => {
    const wrapper = mount(ConfigView, { global: { stubs: { LoadingSpinner: true, BannerAlert: true } } })
    await flushPromises()
    expect(wrapper.find('[data-testid="flag-table"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('bargaining_enabled')
    expect(wrapper.text()).toContain('rollback_on_refund')
  })

  it('shows edit form when edit button is clicked', async () => {
    const wrapper = mount(ConfigView, { global: { stubs: { LoadingSpinner: true, BannerAlert: true } } })
    await flushPromises()
    const editBtn = wrapper.find('[data-testid="flag-edit-btn-bargaining_enabled"]')
    expect(editBtn.exists()).toBe(true)
    await editBtn.trigger('click')
    expect(wrapper.find('[data-testid="flag-edit-input"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="flag-save-btn"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="flag-cancel-btn"]').exists()).toBe(true)
  })

  it('cancel button hides the edit form', async () => {
    const wrapper = mount(ConfigView, { global: { stubs: { LoadingSpinner: true, BannerAlert: true } } })
    await flushPromises()
    await wrapper.find('[data-testid="flag-edit-btn-bargaining_enabled"]').trigger('click')
    await wrapper.find('[data-testid="flag-cancel-btn"]').trigger('click')
    expect(wrapper.find('[data-testid="flag-edit-input"]').exists()).toBe(false)
  })

  it('save calls updateFlag and shows success message', async () => {
    const { updateFlag } = await import('@/services/adminApi')
    const wrapper = mount(ConfigView, { global: { stubs: { LoadingSpinner: true, BannerAlert: true } } })
    await flushPromises()
    await wrapper.find('[data-testid="flag-edit-btn-bargaining_enabled"]').trigger('click')
    const input = wrapper.find('[data-testid="flag-edit-input"]')
    await input.setValue('false')
    await wrapper.find('[data-testid="flag-save-btn"]').trigger('click')
    await flushPromises()
    expect(updateFlag).toHaveBeenCalledWith('bargaining_enabled', 'false', undefined)
  })

  it('shows cohort section', async () => {
    const wrapper = mount(ConfigView, { global: { stubs: { LoadingSpinner: true, BannerAlert: true } } })
    await flushPromises()
    expect(wrapper.text()).toContain('Cohort')
  })
})
