import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  type AuditEntry,
  type CacheHitStat,
  type CohortDefinition,
  type ExportJob,
  type FeatureFlag,
  type ForecastSnapshot,
  type MaskingPolicy,
  type RbacPolicy,
  assignCohort,
  createCohort as apiCreateCohort,
  createExport as apiCreateExport,
  listCacheStats as listCacheStatsApi,
  getFlags,
  getMaskingPolicy as apiGetMaskingPolicy,
  getMetricsSummary,
  getRbacPolicy as apiGetRbacPolicy,
  listCohorts,
  listExports as apiListExports,
  listForecasts,
  searchAudit,
  updateFlag as apiUpdateFlag,
} from '@/services/adminApi'

export type { AuditEntry, CacheHitStat, CohortDefinition, ExportJob, FeatureFlag, ForecastSnapshot }

export interface TelemetrySummary {
  total_requests: number
  error_rate: number
  avg_latency_ms: number
  period: string
}

export const useAdminStore = defineStore('admin', () => {
  // Audit
  const auditLog = ref<AuditEntry[]>([])
  const auditTotal = ref(0)
  const auditFilters = ref<Record<string, string>>({})

  // Feature flags
  const flags = ref<FeatureFlag[]>([])
  const featureFlags = ref<Record<string, boolean>>({
    bargaining_enabled: true,
    rollback_on_refund: true,
  })

  // Cohorts
  const cohorts = ref<CohortDefinition[]>([])

  // Metrics
  const metricsSummary = ref<Record<string, unknown> | null>(null)

  // Forecasts
  const forecasts = ref<ForecastSnapshot[]>([])
  const forecastTotal = ref(0)

  // Cache stats
  const cacheStats = ref<CacheHitStat[]>([])
  const cacheTotal = ref(0)

  // Exports
  const exportJobs = ref<ExportJob[]>([])
  const exportTotal = ref(0)

  // Policies
  const rbacPolicy = ref<RbacPolicy | null>(null)
  const maskingPolicy = ref<MaskingPolicy | null>(null)

  // UI state
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ── Feature flags ────────────────────────────────────────────────────────
  async function loadFlags(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      flags.value = await getFlags()
      // Sync boolean map for session store compatibility
      const map: Record<string, boolean> = {}
      for (const f of flags.value) {
        map[f.key] = f.value === 'true' || f.value === '1'
      }
      featureFlags.value = { ...featureFlags.value, ...map }
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  async function updateFlag(key: string, value: string, reason?: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const updated = await apiUpdateFlag(key, value, reason)
      const idx = flags.value.findIndex((f) => f.key === key)
      if (idx >= 0) flags.value[idx] = updated
      featureFlags.value[key] = value === 'true' || value === '1'
    } catch (e) {
      error.value = (e as Error).message
      throw e
    } finally {
      loading.value = false
    }
  }

  // ── Cohorts ───────────────────────────────────────────────────────────────
  async function loadCohorts(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      cohorts.value = await listCohorts()
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  async function createCohort(
    cohort_key: string,
    name: string,
    flag_overrides?: Record<string, string>,
  ): Promise<CohortDefinition> {
    const cohort = await apiCreateCohort(cohort_key, name, flag_overrides)
    cohorts.value.push(cohort)
    return cohort
  }

  async function assignUserCohort(cohort_id: string, user_id: string): Promise<void> {
    await assignCohort(cohort_id, user_id)
  }

  // ── Audit log ─────────────────────────────────────────────────────────────
  async function loadAuditLog(params?: { page?: number; page_size?: number }): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const result = await searchAudit({ ...auditFilters.value, ...params })
      auditLog.value = result.data
      auditTotal.value = result.pagination.total
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  async function searchAuditLog(filters: Record<string, string>): Promise<void> {
    auditFilters.value = filters
    await loadAuditLog()
  }

  // ── Metrics ───────────────────────────────────────────────────────────────
  async function loadMetrics(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      metricsSummary.value = await getMetricsSummary()
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  // ── Forecasts ─────────────────────────────────────────────────────────────
  async function loadForecasts(page = 1): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const result = await listForecasts(page)
      forecasts.value = result.data
      forecastTotal.value = result.pagination.total
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  // ── Cache stats ───────────────────────────────────────────────────────────
  async function loadCacheStats(page = 1): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const result = await listCacheStatsApi(page)
      cacheStats.value = result.data
      cacheTotal.value = result.pagination.total
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  // ── Exports ───────────────────────────────────────────────────────────────
  async function loadExports(page = 1): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const result = await apiListExports(page)
      exportJobs.value = result.data
      exportTotal.value = result.pagination.total
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  async function createExport(export_type: string): Promise<ExportJob> {
    const job = await apiCreateExport(export_type)
    exportJobs.value.unshift(job)
    return job
  }

  // ── Policies ──────────────────────────────────────────────────────────────
  async function loadRbacPolicy(): Promise<void> {
    rbacPolicy.value = await apiGetRbacPolicy()
  }

  async function loadMaskingPolicy(): Promise<void> {
    maskingPolicy.value = await apiGetMaskingPolicy()
  }

  // ── Legacy compat ─────────────────────────────────────────────────────────
  function applyFeatureFlags(newFlags: Record<string, boolean>): void {
    featureFlags.value = { ...featureFlags.value, ...newFlags }
  }

  function clearError(): void {
    error.value = null
  }

  return {
    // state
    auditLog, auditTotal, auditFilters,
    flags, featureFlags,
    cohorts,
    metricsSummary,
    forecasts, forecastTotal,
    cacheStats, cacheTotal,
    exportJobs, exportTotal,
    rbacPolicy, maskingPolicy,
    loading, error,
    // actions
    loadFlags, updateFlag,
    loadCohorts, createCohort, assignUserCohort,
    loadAuditLog, searchAuditLog,
    loadMetrics,
    loadForecasts,
    loadCacheStats,
    loadExports, createExport,
    loadRbacPolicy, loadMaskingPolicy,
    applyFeatureFlags, clearError,
  }
})
