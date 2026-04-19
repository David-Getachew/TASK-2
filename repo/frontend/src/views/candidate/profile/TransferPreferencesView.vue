<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useCandidateStore } from '@/stores/candidate'
import BannerAlert from '@/components/common/BannerAlert.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import CandidateProfileInitBanner from '@/components/candidate/CandidateProfileInitBanner.vue'
import type { TransferPreferenceCreate } from '@/types/candidate'

const auth = useAuthStore()
const store = useCandidateStore()
const candidateId = computed(() => auth.candidateId ?? '')
const missingProfile = computed(() => auth.user?.role === 'candidate' && !auth.candidateId)
const saved = ref(false)

const newPref = reactive<TransferPreferenceCreate>({
  institution_name: '',
  program_code: null,
  priority_rank: 1,
  notes: null,
})

onMounted(async () => {
  if (!candidateId.value) return
  await store.loadTransferPreferences(candidateId.value)
})

async function onProfileInitialized(id: string): Promise<void> {
  await store.loadTransferPreferences(id)
}

async function submit(): Promise<void> {
  if (!candidateId.value) return
  saved.value = false
  const ok = await store.addTransferPreference(candidateId.value, { ...newPref })
  if (ok) {
    saved.value = true
    newPref.institution_name = ''
    newPref.program_code = null
    newPref.priority_rank = store.transferPreferences.length + 1
    newPref.notes = null
  }
}
</script>

<template>
  <div class="transfer-prefs-view" data-testid="transfer-prefs-view">
    <h2>Transfer Preferences</h2>
    <router-link to="/candidate/profile" class="back-link">← Back to Profile</router-link>

    <CandidateProfileInitBanner
      v-if="missingProfile"
      @initialized="onProfileInitialized"
    />

    <BannerAlert v-if="saved" type="success" message="Preference saved." :dismissible="true" @dismiss="saved = false" />
    <BannerAlert v-if="store.error" type="error" :message="store.error" :dismissible="true" @dismiss="store.clearError()" />

    <ol class="prefs-list" v-if="store.transferPreferences.length > 0">
      <li v-for="pref in store.transferPreferences.slice().sort((a, b) => a.priority_rank - b.priority_rank)" :key="pref.id" class="prefs-list__item">
        <div class="prefs-list__priority">#{{ pref.priority_rank }}</div>
        <div class="prefs-list__info">
          <strong>{{ pref.institution_name }}</strong>
          <span v-if="pref.program_code"> — {{ pref.program_code }}</span>
          <p v-if="pref.notes" class="prefs-list__notes">{{ pref.notes }}</p>
        </div>
        <span class="prefs-list__status">{{ pref.is_active ? 'active' : 'inactive' }}</span>
      </li>
    </ol>
    <EmptyState v-else message="No transfer preferences added yet." />

    <section v-if="!missingProfile" class="add-pref">
      <h3>Add Preference</h3>
      <form class="add-pref__form" @submit.prevent="submit" data-testid="add-pref-form">
        <label>Institution <input v-model="newPref.institution_name" type="text" required /></label>
        <label>Program Code <input v-model="newPref.program_code" type="text" /></label>
        <label>Priority Rank <input v-model.number="newPref.priority_rank" type="number" min="1" required /></label>
        <label>Notes <input v-model="newPref.notes" type="text" /></label>
        <button type="submit" class="btn-primary" :disabled="store.loading">Add</button>
      </form>
    </section>
  </div>
</template>

<style scoped>
.transfer-prefs-view { display: flex; flex-direction: column; gap: 1.25rem; }
.transfer-prefs-view h2 { margin: 0; }
.back-link { font-size: 0.875rem; color: #1565c0; text-decoration: none; }
.back-link:hover { text-decoration: underline; }
.prefs-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.75rem; }
.prefs-list__item { display: flex; align-items: flex-start; gap: 1rem; padding: 0.75rem; border: 1px solid #e0e0e0; border-radius: 6px; }
.prefs-list__priority { font-weight: 700; color: #1565c0; min-width: 28px; }
.prefs-list__info { flex: 1; font-size: 0.875rem; }
.prefs-list__notes { margin: 0.25rem 0 0; color: #777; font-size: 0.8rem; }
.prefs-list__status { font-size: 0.75rem; color: #555; }
.add-pref h3 { margin: 0 0 0.5rem; font-size: 1rem; }
.add-pref__form { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: flex-end; }
.add-pref__form label { display: flex; flex-direction: column; gap: 0.2rem; font-size: 0.875rem; }
.add-pref__form input { padding: 0.35rem 0.5rem; border: 1px solid #bdbdbd; border-radius: 4px; }
.btn-primary { padding: 0.5rem 1.25rem; background: #1565c0; color: white; border: none; border-radius: 4px; cursor: pointer; }
.btn-primary:disabled { opacity: 0.6; }
</style>
