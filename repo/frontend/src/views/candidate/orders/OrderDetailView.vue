<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useOrderStore } from '@/stores/order'
import StatusChip from '@/components/common/StatusChip.vue'
import TimelineList from '@/components/common/TimelineList.vue'
import CountdownTimer from '@/components/common/CountdownTimer.vue'
import BannerAlert from '@/components/common/BannerAlert.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import TimestampDisplay from '@/components/common/TimestampDisplay.vue'
import type { TimelineEntry } from '@/components/common/TimelineList.vue'

const route = useRoute()
const store = useOrderStore()
const orderId = route.params.orderId as string

const timeline = computed<TimelineEntry[]>(() => {
  if (!store.currentOrder?.events) return []
  return store.currentOrder.events.map((e) => ({
    id: e.id,
    label: `${e.previous_state ?? '—'} → ${e.new_state}`,
    description: e.notes ?? null,
    timestamp: e.occurred_at,
    actor: e.actor_role,
  }))
})

onMounted(async () => {
  await store.loadOrder(orderId)
})

async function cancel(): Promise<void> {
  await store.cancelOrder(orderId)
}

async function confirmReceipt(): Promise<void> {
  await store.confirmReceipt(orderId)
}
</script>

<template>
  <div class="order-detail-view" data-testid="order-detail-view">
    <div class="order-detail-view__header">
      <h2>Order Detail</h2>
      <router-link to="/candidate/orders" class="back-link">← My Orders</router-link>
    </div>

    <LoadingSpinner v-if="store.loading" label="Loading order…" />
    <BannerAlert v-if="store.error" type="error" :message="store.error" :dismissible="true" @dismiss="store.clearError()" />

    <template v-if="store.currentOrder">
      <div class="order-detail__summary">
        <h3>{{ store.currentItem?.name ?? 'Order' }}</h3>
        <StatusChip :status="store.currentOrder.status" />
        <table class="order-detail__table">
          <tr><th>ID</th><td><code>{{ store.currentOrder.id }}</code></td></tr>
          <tr><th>Catalog Price</th><td>{{ store.currentItem?.fixed_price ?? '—' }}</td></tr>
          <tr><th>Agreed Price</th><td>{{ store.currentOrder.agreed_price ?? '—' }}</td></tr>
          <tr><th>Pricing Mode</th><td>{{ store.currentOrder.pricing_mode }}</td></tr>
          <tr><th>Created</th><td><TimestampDisplay :value="store.currentOrder.created_at" /></td></tr>
          <tr v-if="store.currentOrder.completed_at">
            <th>Completed</th><td><TimestampDisplay :value="store.currentOrder.completed_at" /></td>
          </tr>
          <tr v-if="store.currentOrder.canceled_at">
            <th>Canceled</th><td><TimestampDisplay :value="store.currentOrder.canceled_at" /></td>
          </tr>
          <tr v-if="store.currentOrder.cancellation_reason">
            <th>Cancel Reason</th><td>{{ store.currentOrder.cancellation_reason }}</td>
          </tr>
        </table>
      </div>

      <BannerAlert
        v-if="store.currentOrder.status === 'pending_payment'"
        type="warning"
        :message="`Auto-cancel countdown`"
      />
      <CountdownTimer
        v-if="store.currentOrder.status === 'pending_payment'"
        :expires-at="store.currentOrder.auto_cancel_at"
        label="Auto-cancel in"
      />

      <div class="order-detail__actions">
        <router-link
          v-if="store.currentOrder.status === 'pending_payment'"
          :to="`/candidate/orders/${orderId}/payment`"
          class="btn-primary"
        >
          Submit Payment
        </router-link>
        <router-link
          v-if="store.currentOrder.status === 'pending_payment' && store.currentOrder.pricing_mode === 'bargaining'"
          :to="`/candidate/orders/${orderId}/bargaining`"
          class="btn-secondary"
        >
          Bargaining Thread
        </router-link>
        <button
          v-if="['pending_payment', 'pending_fulfillment'].includes(store.currentOrder.status)"
          type="button"
          class="btn-danger"
          :disabled="store.submitting"
          @click="cancel"
        >
          Cancel Order
        </button>
        <button
          v-if="store.currentOrder.status === 'pending_receipt'"
          type="button"
          class="btn-primary"
          :disabled="store.submitting"
          @click="confirmReceipt"
        >
          Confirm Receipt
        </button>
        <router-link
          v-if="['completed', 'pending_receipt'].includes(store.currentOrder.status)"
          :to="`/candidate/orders/${orderId}/after-sales`"
          class="btn-secondary"
          data-testid="open-after-sales"
        >
          After-Sales / Refund
        </router-link>
      </div>

      <section class="order-detail__timeline">
        <h3>Order History</h3>
        <TimelineList :entries="timeline" />
      </section>
    </template>
  </div>
</template>

<style scoped>
.order-detail-view { display: flex; flex-direction: column; gap: 1.25rem; }
.order-detail-view__header { display: flex; align-items: center; justify-content: space-between; }
.order-detail-view__header h2 { margin: 0; }
.back-link { font-size: 0.875rem; color: #1565c0; text-decoration: none; }
.order-detail__summary { display: flex; flex-direction: column; gap: 0.75rem; }
.order-detail__summary h3 { margin: 0; }
.order-detail__table { border-collapse: collapse; font-size: 0.875rem; }
.order-detail__table th, .order-detail__table td { padding: 0.3rem 0.6rem; text-align: left; border-bottom: 1px solid #e0e0e0; }
.order-detail__table th { width: 130px; color: #555; font-weight: 500; }
.order-detail__actions { display: flex; gap: 0.75rem; flex-wrap: wrap; }
.order-detail__timeline h3 { margin: 0 0 0.5rem; font-size: 1rem; }
.btn-primary { display: inline-block; padding: 0.5rem 1rem; background: #1565c0; color: white; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; font-size: 0.875rem; }
.btn-secondary { display: inline-block; padding: 0.5rem 1rem; background: white; color: #1565c0; border: 1px solid #1565c0; border-radius: 4px; cursor: pointer; text-decoration: none; font-size: 0.875rem; }
.btn-danger { padding: 0.5rem 1rem; background: #ef4444; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.875rem; }
.btn-danger:disabled, .btn-primary:disabled { opacity: 0.6; cursor: wait; }
</style>
