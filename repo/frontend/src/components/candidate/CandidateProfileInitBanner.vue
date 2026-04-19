<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useCandidateStore } from '@/stores/candidate'
import BannerAlert from '@/components/common/BannerAlert.vue'

const props = defineProps<{
  message?: string
}>()

const emit = defineEmits<{
  (e: 'initialized', candidateId: string): void
}>()

const auth = useAuthStore()
const candidateStore = useCandidateStore()
const initializing = ref(false)
const initError = ref<string | null>(null)

async function initializeProfile(): Promise<void> {
  initializing.value = true
  initError.value = null
  const created = await candidateStore.initSelfProfile()
  initializing.value = false
  if (!created) {
    initError.value = candidateStore.error ?? 'Failed to initialize profile.'
    return
  }
  auth.setCandidateId(created.id)
  emit('initialized', created.id)
}
</script>

<template>
  <section class="candidate-init-banner" data-testid="candidate-init-banner">
    <BannerAlert
      type="warning"
      :message="props.message ?? 'Candidate profile not yet initialized. Click below to set up your candidate record and begin onboarding.'"
    />
    <button
      type="button"
      class="btn-primary"
      data-testid="candidate-self-init-btn"
      :disabled="initializing"
      @click="initializeProfile"
    >
      {{ initializing ? 'Initializing…' : 'Initialize my profile' }}
    </button>
    <BannerAlert
      v-if="initError"
      type="error"
      :message="initError"
      :dismissible="true"
      @dismiss="initError = null"
    />
  </section>
</template>

<style scoped>
.candidate-init-banner { display: flex; flex-direction: column; gap: 0.5rem; align-items: flex-start; }
.btn-primary { padding: 0.5rem 1.25rem; background: #1565c0; color: white; border: none; border-radius: 4px; cursor: pointer; }
.btn-primary:disabled { opacity: 0.6; cursor: wait; }
</style>
