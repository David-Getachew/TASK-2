// Pinia session store: holds cohort config + feature-flag snapshot derived
// from the /auth/me response. Separate from auth.ts because the business
// views read flags without needing to touch token state.

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export const useSessionStore = defineStore('session', () => {
  const cohort = ref<Record<string, unknown> | null>(null)
  const featureFlags = ref<Record<string, boolean>>({})
  const bootstrapAt = ref<string | null>(null)

  const bargainingEnabled = computed(() => !!featureFlags.value.bargaining_enabled)
  const rollbackEnabled = computed(() => !!featureFlags.value.rollback_on_refund)

  function apply(cohortConfig: Record<string, unknown> | null): void {
    cohort.value = cohortConfig
    const flags = cohortConfig?.feature_flags
    featureFlags.value =
      flags && typeof flags === 'object' && !Array.isArray(flags)
        ? (flags as Record<string, boolean>)
        : {}
    bootstrapAt.value = new Date().toISOString()
  }

  function clear(): void {
    cohort.value = null
    featureFlags.value = {}
    bootstrapAt.value = null
  }

  return {
    cohort,
    featureFlags,
    bootstrapAt,
    bargainingEnabled,
    rollbackEnabled,
    apply,
    clear,
  }
})
