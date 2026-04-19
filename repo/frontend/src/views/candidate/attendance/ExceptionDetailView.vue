<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAttendanceStore } from '@/stores/attendance'
import StatusChip from '@/components/common/StatusChip.vue'
import UploadPanel from '@/components/common/UploadPanel.vue'
import BannerAlert from '@/components/common/BannerAlert.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import TimestampDisplay from '@/components/common/TimestampDisplay.vue'

const route = useRoute()
const store = useAttendanceStore()
const exceptionId = route.params.exceptionId as string
const proofUploaded = ref(false)

const canUploadProof = computed(
  () => store.currentException?.status === 'pending_proof',
)

onMounted(async () => {
  await store.loadException(exceptionId)
})

async function handleUpload(payload: { file: File }): Promise<void> {
  const result = await store.uploadProof(exceptionId, payload.file)
  if (result) proofUploaded.value = true
}

const createNew = ref(false)
const newStatement = ref('')
const router = useRouter()

async function fileNewException(): Promise<void> {
  if (!newStatement.value.trim()) return
  const exc = await store.createException(newStatement.value)
  if (exc) {
    router.push(`/candidate/attendance/${exc.id}`)
  }
}
</script>

<template>
  <div class="exception-detail-view" data-testid="exception-detail-view">
    <div class="exception-detail-view__header">
      <h2>Attendance Exception</h2>
      <router-link to="/candidate/attendance" class="back-link">← Exceptions</router-link>
    </div>

    <LoadingSpinner v-if="store.loading" label="Loading…" />
    <BannerAlert v-if="store.error" type="error" :message="store.error" :dismissible="true" @dismiss="store.clearError()" />
    <BannerAlert v-if="proofUploaded" type="success" message="Proof uploaded. Your exception is now under review." />

    <template v-if="store.currentException">
      <div class="exception-summary">
        <StatusChip :status="store.currentException.status" />
        <span>Stage: <strong>{{ store.currentException.current_stage }}</strong></span>
      </div>

      <p class="exception-statement">
        <strong>Your statement:</strong> {{ store.currentException.candidate_statement }}
      </p>

      <section v-if="canUploadProof">
        <h3>Upload Supporting Proof</h3>
        <UploadPanel
          label="Upload proof document"
          :disabled="store.submitting"
          @upload="handleUpload"
        />
      </section>

      <section v-if="store.currentException.review_steps.length > 0" class="review-trail">
        <h3>Review History</h3>
        <div v-for="step in store.currentException.review_steps" :key="step.id" class="review-step">
          <div class="review-step__head">
            <strong>{{ step.stage }} — {{ step.decision }}</strong>
            <StatusChip :status="step.decision" size="sm" />
            <TimestampDisplay :value="step.decided_at" />
          </div>
          <p v-if="step.notes" class="review-step__notes">{{ step.notes }}</p>
        </div>
      </section>
    </template>

    <template v-if="!store.currentException && !store.loading">
      <template v-if="!createNew">
        <p class="empty-msg">Exception not found.</p>
        <button type="button" class="btn-primary" @click="createNew = true">File New Exception</button>
      </template>
      <form v-else class="new-exception-form" @submit.prevent="fileNewException">
        <label>
          Statement *
          <textarea v-model="newStatement" rows="3" required data-testid="exception-statement-input" />
        </label>
        <button type="submit" class="btn-primary" :disabled="store.submitting">Submit</button>
      </form>
    </template>
  </div>
</template>

<style scoped>
.exception-detail-view { display: flex; flex-direction: column; gap: 1.25rem; }
.exception-detail-view__header { display: flex; align-items: center; justify-content: space-between; }
.exception-detail-view__header h2 { margin: 0; }
.back-link { font-size: 0.875rem; color: #1565c0; text-decoration: none; }
.exception-summary { display: flex; align-items: center; gap: 0.75rem; }
.exception-statement { margin: 0; font-size: 0.9rem; }
.review-trail h3 { margin: 0 0 0.5rem; font-size: 1rem; }
.review-step { border: 1px solid #e0e0e0; border-radius: 6px; padding: 0.75rem; margin-bottom: 0.5rem; }
.review-step__head { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; font-size: 0.875rem; }
.review-step__notes { margin: 0.25rem 0 0; font-size: 0.8rem; color: #555; }
.new-exception-form { display: flex; flex-direction: column; gap: 0.75rem; max-width: 480px; }
.new-exception-form label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.875rem; }
.new-exception-form textarea { padding: 0.4rem 0.5rem; border: 1px solid #bdbdbd; border-radius: 4px; }
.empty-msg { color: #888; font-size: 0.875rem; }
.btn-primary { padding: 0.5rem 1.25rem; background: #1565c0; color: white; border: none; border-radius: 4px; cursor: pointer; align-self: flex-start; }
.btn-primary:disabled { opacity: 0.6; }
</style>
