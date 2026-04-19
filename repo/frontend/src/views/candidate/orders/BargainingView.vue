<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useBargainingStore } from '@/stores/bargaining'
import CountdownTimer from '@/components/common/CountdownTimer.vue'
import StatusChip from '@/components/common/StatusChip.vue'
import BannerAlert from '@/components/common/BannerAlert.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import TimestampDisplay from '@/components/common/TimestampDisplay.vue'

const route = useRoute()
const store = useBargainingStore()
const orderId = route.params.orderId as string
const offerAmount = ref('')

onMounted(async () => {
  await store.loadThread(orderId)
})

async function submitOffer(): Promise<void> {
  if (!offerAmount.value) return
  await store.submitOffer(orderId, offerAmount.value)
  offerAmount.value = ''
}

async function handleAcceptCounter(): Promise<void> {
  await store.acceptCounter(orderId)
}
</script>

<template>
  <div class="bargaining-view" data-testid="bargaining-view">
    <div class="bargaining-view__header">
      <h2>Bargaining Thread</h2>
      <router-link :to="`/candidate/orders/${orderId}`" class="back-link">← Order Detail</router-link>
    </div>

    <LoadingSpinner v-if="store.loading" label="Loading thread…" />
    <BannerAlert v-if="store.error" type="error" :message="store.error" :dismissible="true" @dismiss="store.clearError()" />

    <template v-if="store.thread">
      <div class="bargaining-meta">
        <StatusChip :status="store.thread.status" />
        <CountdownTimer :expires-at="store.thread.window_expires_at" label="Window" @expired="store.loadThread(orderId)" />
        <span class="bargaining-meta__offers">Offers remaining: <strong>{{ store.offersRemaining }}/3</strong></span>
      </div>

      <BannerAlert v-if="store.isExpired" type="warning" message="The bargaining window has expired." />

      <section class="bargaining-offers">
        <h3>Offer History</h3>
        <table class="offers-table">
          <thead>
            <tr><th>#</th><th>Amount</th><th>Outcome</th><th>Submitted</th></tr>
          </thead>
          <tbody>
            <tr v-if="store.thread.offers.length === 0">
              <td colspan="4">No offers submitted yet.</td>
            </tr>
            <tr v-for="offer in store.thread.offers" :key="offer.id">
              <td>{{ offer.offer_number }}</td>
              <td>{{ offer.amount }}</td>
              <td><StatusChip :status="offer.outcome" size="sm" /></td>
              <td><TimestampDisplay :value="offer.submitted_at" /></td>
            </tr>
          </tbody>
        </table>
      </section>

      <div v-if="store.thread.counter_amount" class="counter-offer">
        <h3>Staff Counter Offer</h3>
        <p class="counter-offer__amount">{{ store.thread.counter_amount }}</p>
        <button
          v-if="store.canAcceptCounter"
          type="button"
          class="btn-primary"
          :disabled="store.submitting"
          data-testid="accept-counter-btn"
          @click="handleAcceptCounter"
        >
          Accept Counter
        </button>
      </div>

      <form v-if="store.canSubmitOffer" class="offer-form" @submit.prevent="submitOffer" data-testid="offer-form">
        <h3>Submit Offer</h3>
        <label class="offer-form__field">
          Amount
          <input
            v-model="offerAmount"
            type="number"
            min="0"
            step="0.01"
            required
            placeholder="0.00"
            data-testid="offer-amount-input"
          />
        </label>
        <button type="submit" class="btn-primary" :disabled="store.submitting || !offerAmount">
          {{ store.submitting ? 'Submitting…' : 'Submit Offer' }}
        </button>
      </form>

      <BannerAlert
        v-if="['accepted', 'counter_accepted'].includes(store.thread.status)"
        type="success"
        message="Bargaining resolved. Proceed to payment."
      />
    </template>
  </div>
</template>

<style scoped>
.bargaining-view { display: flex; flex-direction: column; gap: 1.25rem; }
.bargaining-view__header { display: flex; align-items: center; justify-content: space-between; }
.bargaining-view__header h2 { margin: 0; }
.back-link { font-size: 0.875rem; color: #1565c0; text-decoration: none; }
.bargaining-meta { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }
.bargaining-meta__offers { font-size: 0.875rem; color: #555; }
.bargaining-offers h3, .counter-offer h3, .offer-form h3 { margin: 0 0 0.5rem; font-size: 1rem; }
.offers-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.offers-table th, .offers-table td { padding: 0.4rem 0.6rem; border-bottom: 1px solid #e0e0e0; text-align: left; }
.offers-table th { background: #f5f5f5; }
.counter-offer { display: flex; flex-direction: column; gap: 0.5rem; border: 1px solid #f59e0b; border-radius: 6px; padding: 1rem; background: #fef3c7; }
.counter-offer__amount { font-size: 1.25rem; font-weight: 700; color: #92400e; margin: 0; }
.offer-form { display: flex; flex-direction: column; gap: 0.75rem; max-width: 280px; }
.offer-form__field { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.875rem; }
.offer-form__field input { padding: 0.4rem 0.5rem; border: 1px solid #bdbdbd; border-radius: 4px; }
.btn-primary { padding: 0.5rem 1.25rem; background: #1565c0; color: white; border: none; border-radius: 4px; cursor: pointer; }
.btn-primary:disabled { opacity: 0.6; cursor: wait; }
</style>
