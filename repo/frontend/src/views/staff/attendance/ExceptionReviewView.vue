<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAttendanceStore } from '@/stores/attendance'
import StatusChip from '@/components/common/StatusChip.vue'
import BannerAlert from '@/components/common/BannerAlert.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import TimestampDisplay from '@/components/common/TimestampDisplay.vue'
import type { ReviewDecisionCreate } from '@/types/attendance'

const route = useRoute()
const router = useRouter()
const store = useAttendanceStore()
const exceptionId = route.params.exceptionId as string
const reviewed = ref(false)

const decision = reactive<ReviewDecisionCreate>({
  decision: 'approve',
  notes: null,
})

onMounted(async () => {
  await store.loadException(exceptionId)
})

const canEscalate = computed(() =>
  store.currentException?.current_stage === 'initial',
)

async function submit(): Promise<void> {
  const ok = await store.submitReview(exceptionId, { ...decision })
  if (ok) {
    reviewed.value = true
    setTimeout(() => router.push('/staff/exceptions'), 1500)
  }
}
</script>

<template>
  <div class="exception-review-view" data-testid="exception-review-view">
    <div class="exception-review-view__header">
      <h2>Review Attendance Exception</h2>
      <router-link to="/staff/exceptions" class="back-link">← Exception Queue</router-link>
    </div>

    <LoadingSpinner v-if="store.loading" label="Loading…" />
    <BannerAlert v-if="reviewed" type="success" message="Decision recorded. Redirecting…" />
    <BannerAlert v-if="store.error" type="error" :message="store.error" :dismissible="true" @dismiss="store.clearError()" />

    <template v-if="store.currentException">
      <div class="exception-summary">
        <StatusChip :status="store.currentException.status" />
        <span>Stage: <strong>{{ store.currentException.current_stage }}</strong></span>
      </div>

      <p class="exception-statement">
        <strong>Candidate Statement:</strong> {{ store.currentException.candidate_statement }}
      </p>

      <section v-if="(store.currentException.proofs?.length ?? 0) > 0" class="proofs-section" data-testid="exception-proofs">
        <h3>Proof Documents</h3>
        <ul>
          <li v-for="proof in (store.currentException.proofs ?? [])" :key="proof.id" data-testid="exception-proof-item">
            Uploaded by {{ proof.uploaded_by }} at <TimestampDisplay :value="proof.uploaded_at" />
            <span v-if="proof.description"> — {{ proof.description }}</span>
          </li>
        </ul>
      </section>
      <p v-else class="proofs-empty" data-testid="exception-proofs-empty">No proof documents attached.</p>

      <section v-if="store.currentException.review_steps.length > 0" class="prior-reviews">
        <h3>Prior Review Steps</h3>
        <div v-for="step in store.currentException.review_steps" :key="step.id" class="review-step">
          <strong>{{ step.stage }}</strong> — {{ step.decision }}
          <span v-if="step.notes"> — {{ step.notes }}</span>
        </div>
      </section>

      <form class="review-form" @submit.prevent="submit" data-testid="exception-review-form">
        <fieldset class="review-form__fieldset">
          <legend>Decision</legend>
          <label>
            <input v-model="decision.decision" type="radio" value="approve" data-testid="decision-approve" />
            Approve
          </label>
          <label>
            <input v-model="decision.decision" type="radio" value="reject" data-testid="decision-reject" />
            Reject
          </label>
          <label v-if="canEscalate">
            <input v-model="decision.decision" type="radio" value="escalate" data-testid="decision-escalate" />
            Escalate to Final Review
          </label>
        </fieldset>

        <label class="review-form__field">
          Notes
          <textarea v-model="decision.notes" rows="2" data-testid="field-review-notes" />
        </label>

        <button
          type="submit"
          class="btn-primary"
          :disabled="store.submitting || reviewed"
          data-testid="exception-review-submit"
        >
          {{ store.submitting ? 'Submitting…' : 'Submit Decision' }}
        </button>
      </form>
    </template>
  </div>
</template>

<style scoped>
.exception-review-view { display: flex; flex-direction: column; gap: 1.25rem; max-width: 560px; }
.exception-review-view__header { display: flex; align-items: center; justify-content: space-between; }
.exception-review-view__header h2 { margin: 0; }
.back-link { font-size: 0.875rem; color: #1565c0; text-decoration: none; }
.exception-summary { display: flex; align-items: center; gap: 0.75rem; }
.exception-statement { font-size: 0.9rem; margin: 0; }
.proofs-section h3, .prior-reviews h3 { font-size: 1rem; margin: 0 0 0.4rem; }
.proofs-section ul { margin: 0; padding-left: 1rem; font-size: 0.875rem; }
.review-step { font-size: 0.875rem; padding: 0.25rem 0; border-bottom: 1px solid #f5f5f5; }
.review-form { display: flex; flex-direction: column; gap: 1rem; }
.review-form__fieldset { border: 1px solid #e0e0e0; border-radius: 6px; padding: 0.75rem; display: flex; flex-direction: column; gap: 0.4rem; }
.review-form__fieldset label { display: flex; align-items: center; gap: 0.4rem; font-size: 0.9rem; }
.review-form__field { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.875rem; }
.review-form__field textarea { padding: 0.4rem 0.5rem; border: 1px solid #bdbdbd; border-radius: 4px; }
.btn-primary { padding: 0.5rem 1.25rem; background: #1565c0; color: white; border: none; border-radius: 4px; cursor: pointer; align-self: flex-start; }
.btn-primary:disabled { opacity: 0.6; }
</style>
