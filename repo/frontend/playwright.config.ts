import { defineConfig, devices } from '@playwright/test'

const liveE2EEnabled = process.env.PW_ENABLE_LIVE_E2E === '1'

// Playwright is set up with two projects:
//
//   1. `chromium` — default, runs stubbed specs from `unit_tests/browser/`.
//      These are FE-BROWSER unit-of-interaction tests that use page.route()
//      stubs for deterministic UI-logic assertions. `@live`-tagged specs are
//      excluded so the default project stays hermetic.
//
//   2. `live`    — runs no-mock end-to-end specs from `e2e/`. These drive real
//      HTTP traffic through the Vite /api proxy to a running backend (no
//      page.route() stubs). Each spec gates itself on PW_LIVE_* env vars and
//      skips silently when they are absent, matching the existing
//      `live_auth_smoke.spec.ts` discipline. This project is only registered
//      when PW_ENABLE_LIVE_E2E=1.
export default defineConfig({
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'html',

  // Auto-start the Vite dev server for both projects. The Vite proxy forwards
  // /api/* to the live backend for the `live` project; the `chromium` project
  // never hits /api because its specs install page.route() stubs.
  webServer: {
    command: 'npx vite --port 5173',
    port: 5173,
    reuseExistingServer: !process.env.CI,
  },

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      testDir: './unit_tests/browser',
      grepInvert: /@live/,
      use: { ...devices['Desktop Chrome'] },
    },
    ...(liveE2EEnabled
      ? [
          {
            name: 'live',
            testDir: './e2e',
            grep: /@live/,
            use: { ...devices['Desktop Chrome'] },
          },
        ]
      : []),
  ],
})
