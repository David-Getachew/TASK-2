// FE-BROWSER: Admin updates a feature flag — flag table visible, edit form, save success.

import { test, expect } from '@playwright/test'
import { seedAuth } from './helpers/seedAuth'

const FAKE_AUTH = {
  access_token: 'fake.jwt.token',
  user: {
    id: 'admin-1',
    username: 'carol_admin',
    role: 'admin',
    full_name: 'Carol Admin',
    is_active: true,
    last_login_at: null,
  },
  device_id: 'device-1',
  refresh_token: null,
  session_expires_at: null,
}

const FLAGS = [
  {
    id: 'f-1',
    key: 'bargaining_enabled',
    value: 'true',
    value_type: 'boolean',
    description: 'Enable bargaining mode for orders',
    updated_by: null,
    updated_at: new Date().toISOString(),
  },
  {
    id: 'f-2',
    key: 'rollback_on_refund',
    value: 'true',
    value_type: 'boolean',
    description: 'Enable capacity rollback on cancel/refund',
    updated_by: null,
    updated_at: new Date().toISOString(),
  },
]

test.describe('Admin feature flag update workflow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await seedAuth(page, {
      user: FAKE_AUTH.user,
      role: 'admin',
      tokens: { access_token: FAKE_AUTH.access_token, refresh_token: 'fake.refresh.token', token_type: 'bearer', expires_in: 900 },
      deviceId: FAKE_AUTH.device_id,
      candidateId: null,
    })

    await page.route('**/api/v1/admin/feature-flags', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, data: FLAGS }),
        })
      } else {
        await route.continue()
      }
    })

    await page.route('**/api/v1/admin/feature-flags/bargaining_enabled', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { ...FLAGS[0], value: 'false' },
        }),
      })
    })

    await page.route('**/api/v1/admin/cohorts', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [] }),
      })
    })
  })

  test('config view is accessible and shows flag table', async ({ page }) => {
    await page.goto('/admin/config')
    await expect(page.getByTestId('config-view')).toBeVisible({ timeout: 5000 })
    await expect(page.getByTestId('flag-table')).toBeVisible({ timeout: 5000 })
  })

  test('flag keys are displayed in the table', async ({ page }) => {
    await page.goto('/admin/config')
    await expect(page.getByText('bargaining_enabled')).toBeVisible({ timeout: 5000 })
    await expect(page.getByText('rollback_on_refund')).toBeVisible({ timeout: 5000 })
  })

  test('clicking edit shows edit form', async ({ page }) => {
    await page.goto('/admin/config')
    await page.getByTestId('flag-edit-btn-bargaining_enabled').click()
    await expect(page.getByTestId('flag-edit-input')).toBeVisible({ timeout: 3000 })
    await expect(page.getByTestId('flag-save-btn')).toBeVisible({ timeout: 3000 })
  })

  test('saving flag update shows success message', async ({ page }) => {
    await page.goto('/admin/config')
    await page.getByTestId('flag-edit-btn-bargaining_enabled').click()
    await page.getByTestId('flag-edit-input').fill('false')
    await page.getByTestId('flag-save-btn').click()
    await expect(page.getByText(/bargaining_enabled.*updated/i)).toBeVisible({ timeout: 5000 })
  })

  test('cancel hides the edit form', async ({ page }) => {
    await page.goto('/admin/config')
    await page.getByTestId('flag-edit-btn-bargaining_enabled').click()
    await page.getByTestId('flag-cancel-btn').click()
    await expect(page.getByTestId('flag-edit-input')).not.toBeVisible()
  })
})
