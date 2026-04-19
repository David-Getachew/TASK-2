<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useOrderStore } from '@/stores/order'
import { listAfterSales } from '@/services/refundApi'
import type { AfterSalesRequest } from '@/types/order'
import StatusChip from '@/components/common/StatusChip.vue'
import BannerAlert from '@/components/common/BannerAlert.vue'
import TimestampDisplay from '@/components/common/TimestampDisplay.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

const route = useRoute()
const store = useOrderStore()
const orderId = route.params.orderId as string

const requestType = ref('')
const description = ref('')
const submitting = ref(false)
const notification = ref<string | null>(null)
const errorMsg = ref<string | null>(null)
const history = ref<AfterSalesRequest[]>([])
const loadingHistory = ref(false)

async function loadHistory(): Promise<void> {
  loadingHistory.value = true
  try {
    history.value = await listAfterSales(orderId)
  } catch (e) {
    errorMsg.value = (e as Error).message
  } finally {
    loadingHistory.value = false
  }
}

async function submit(): Promise<void> {
  if (!requestType.value.trim() || !description.value.trim()) return
  submitting.value = true
  notification.value = null
  errorMsg.value = null
  const created = await store.submitAfterSales(orderId, {
    request_type: requestType.value.trim(),
    description: description.value.trim(),
  })
  submitting.value = false
  if (created) {
    notification.value = 'After-sales request submitted.'
    requestType.value = ''
    description.value = ''
    await loadHistory()
  } else {
    errorMsg.value = store.error ?? 'Failed to submit after-sales request.'
  }
}

onMounted(async () => {
  await store.loadOrder(orderId)
  await loadHistory()
})
</script>

<template>
  <div class="after-sales-view" data-testid="candidate-after-sales-view">
    <div class="after-sales-view__header">
      <h2>After-Sales Request</h2>
      <router-link :to="`/candidate/orders/${orderId}`" class="back-link">← Order Detail</router-link>
    </div>

    <BannerAlert v-if="notification" type="success" :message="notification" :dismissible="true" @dismiss="notification = null" />
    <BannerAlert v-if="errorMsg" type="error" :message="errorMsg" :dismissible="true" @dismiss="errorMsg = null" />

    <form class="after-sales-form" data-testid="after-sales-form" @submit.prevent="submit">
      <label for="as-type">Request Type
        <input
          id="as-type"
          v-model="requestType"
          type="text"
          required
          maxlength="100"
          placeholder="e.g. refund_request, service_complaint"
          data-testid="after-sales-type"
        />
      </label>
      <label for="as-desc">Description
        <textarea
          id="as-desc"
          v-model="description"
          required
          rows="4"
          maxlength="5000"
          placeholder="Describe the issue and the outcome you expect"
          data-testid="after-sales-description"
        />
      </label>
      <button
        type="submit"
        class="btn-primary"
        :disabled="submitting || !requestType.trim() || !description.trim()"
        data-testid="after-sales-submit"
      >
        {{ submitting ? 'Submitting…' : 'Submit After-Sales' }}
      </button>
    </form>

    <section class="after-sales-history" data-testid="after-sales-history">
      <h3>My Requests</h3>
      <LoadingSpinner v-if="loadingHistory" label="Loading…" />
      <p v-else-if="history.length === 0" class="empty-msg">You have not filed any after-sales requests for this order.</p>
      <div v-else class="history-list">
        <div v-for="item in history" :key="item.id" class="history-item">
          <div class="history-item__head">
            <span class="history-item__type">{{ item.request_type }}</span>
            <StatusChip :status="item.status" size="sm" />
          </div>
          <p class="history-item__desc">{{ item.description }}</p>
          <div class="history-item__meta">
            <span>Filed <TimestampDisplay :value="item.created_at" /></span>
            <span v-if="item.window_expires_at">
              Window expires <TimestampDisplay :value="item.window_expires_at" />
            </span>
            <span v-if="item.resolved_at">
              Resolved <TimestampDisplay :value="item.resolved_at" />
            </span>
          </div>
          <p v-if="item.resolution_notes" class="history-item__resolution">
            <strong>Resolution:</strong> {{ item.resolution_notes }}
          </p>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.after-sales-view { display: flex; flex-direction: column; gap: 1.25rem; }
.after-sales-view__header { display: flex; align-items: center; justify-content: space-between; }
.after-sales-view__header h2 { margin: 0; }
.back-link { font-size: 0.875rem; color: #1565c0; text-decoration: none; }
.after-sales-form { display: flex; flex-direction: column; gap: 0.75rem; max-width: 600px; }
.after-sales-form label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.875rem; color: #333; }
.after-sales-form input,
.after-sales-form textarea { padding: 0.4rem 0.5rem; border: 1px solid #bdbdbd; border-radius: 4px; font-size: 0.875rem; font-family: inherit; }
.btn-primary { padding: 0.5rem 1rem; background: #1565c0; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.875rem; align-self: flex-start; }
.btn-primary:disabled { opacity: 0.6; cursor: wait; }
.after-sales-history h3 { margin: 0 0 0.5rem; font-size: 1rem; }
.history-list { display: flex; flex-direction: column; gap: 0.75rem; }
.history-item { border: 1px solid #e0e0e0; border-radius: 8px; padding: 0.75rem 1rem; display: flex; flex-direction: column; gap: 0.4rem; }
.history-item__head { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
.history-item__type { font-weight: 600; font-size: 0.9rem; }
.history-item__desc { margin: 0; font-size: 0.875rem; color: #333; }
.history-item__meta { display: flex; gap: 0.75rem; flex-wrap: wrap; font-size: 0.8rem; color: #666; }
.history-item__resolution { margin: 0; font-size: 0.85rem; color: #2e7d32; }
.empty-msg { color: #888; font-size: 0.875rem; }
</style>
