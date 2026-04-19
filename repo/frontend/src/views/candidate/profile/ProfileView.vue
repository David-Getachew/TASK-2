<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useCandidateStore } from '@/stores/candidate'
import BannerAlert from '@/components/common/BannerAlert.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import CandidateProfileInitBanner from '@/components/candidate/CandidateProfileInitBanner.vue'
import type { CandidateProfileUpdate } from '@/types/candidate'

const auth = useAuthStore()
const store = useCandidateStore()
// Candidate profile UUID — distinct from user.id. Resolved by GET /auth/me
// into auth.candidateId (see stores/auth.ts). Using user.id here would
// mismatch backend since CandidateProfile has its own PK.
const candidateId = computed(() => auth.candidateId ?? '')
const missingProfile = computed(() => auth.user?.role === 'candidate' && !auth.candidateId)
const saved = ref(false)

const form = reactive<CandidateProfileUpdate>({
  preferred_name: '',
  application_year: null,
  program_code: null,
  notes: null,
})

onMounted(async () => {
  if (!candidateId.value) return
  await store.loadProfile(candidateId.value)
  if (store.profile) {
    form.preferred_name = store.profile.preferred_name ?? ''
    form.application_year = store.profile.application_year
    form.program_code = store.profile.program_code
  }
})

async function submit(): Promise<void> {
  if (!candidateId.value) return
  saved.value = false
  const ok = await store.saveProfile(candidateId.value, { ...form })
  if (ok) saved.value = true
}

async function onProfileInitialized(id: string): Promise<void> {
  await store.loadProfile(id)
  if (store.profile) {
    form.preferred_name = store.profile.preferred_name ?? ''
    form.application_year = store.profile.application_year
    form.program_code = store.profile.program_code
  }
}
</script>

<template>
  <div class="profile-view" data-testid="profile-view">
    <h2>My Profile</h2>

    <CandidateProfileInitBanner
      v-if="missingProfile"
      @initialized="onProfileInitialized"
    />

    <LoadingSpinner v-if="store.loading" label="Loading profile…" />

    <BannerAlert v-if="saved" type="success" message="Profile saved." :dismissible="true" @dismiss="saved = false" />
    <BannerAlert v-if="store.error" type="error" :message="store.error" :dismissible="true" @dismiss="store.clearError()" />

    <section v-if="store.profile" class="profile-view__masked">
      <h3>Identity (masked)</h3>
      <table class="masked-table">
        <tr><th>SSN</th><td>{{ store.profile.ssn_display ?? '—' }}</td></tr>
        <tr><th>DOB</th><td>{{ store.profile.dob_display ?? '—' }}</td></tr>
        <tr><th>Phone</th><td>{{ store.profile.phone_display ?? '—' }}</td></tr>
        <tr><th>Email</th><td>{{ store.profile.email_display ?? '—' }}</td></tr>
      </table>
      <p class="masked-note">These fields are masked by default — the full values are only visible to approved staff roles.</p>
    </section>

    <form v-if="!missingProfile" class="profile-form" @submit.prevent="submit" data-testid="profile-form">
      <label class="profile-form__field">
        <span>Preferred Name</span>
        <input v-model="form.preferred_name" type="text" data-testid="field-preferred-name" />
      </label>

      <label class="profile-form__field">
        <span>Application Year</span>
        <input
          :value="form.application_year ?? ''"
          type="number"
          min="2000"
          max="2100"
          data-testid="field-application-year"
          @input="(e) => (form.application_year = (e.target as HTMLInputElement).value ? Number((e.target as HTMLInputElement).value) : null)"
        />
      </label>

      <label class="profile-form__field">
        <span>Program Code</span>
        <input v-model="form.program_code" type="text" data-testid="field-program-code" />
      </label>

      <label class="profile-form__field">
        <span>Notes</span>
        <textarea v-model="form.notes" rows="3" data-testid="field-notes" />
      </label>

      <div class="profile-form__actions">
        <button type="submit" class="btn-primary" :disabled="store.loading" data-testid="profile-save">
          {{ store.loading ? 'Saving…' : 'Save Profile' }}
        </button>
        <router-link to="/candidate/profile/exam-scores" class="link-action">Exam Scores →</router-link>
        <router-link to="/candidate/profile/transfer-preferences" class="link-action">Transfer Preferences →</router-link>
      </div>
    </form>
  </div>
</template>

<style scoped>
.profile-view { display: flex; flex-direction: column; gap: 1.25rem; }
.profile-view h2 { margin: 0; }
.profile-view__masked { border: 1px solid #e0e0e0; border-radius: 6px; padding: 1rem; display: flex; flex-direction: column; gap: 0.5rem; }
.profile-view__masked h3 { margin: 0; font-size: 1rem; }
.masked-table { border-collapse: collapse; font-size: 0.875rem; }
.masked-table th, .masked-table td { padding: 0.3rem 0.6rem; border-bottom: 1px solid #e0e0e0; }
.masked-table th { width: 120px; color: #555; font-weight: 500; text-align: left; }
.masked-note { font-size: 0.75rem; color: #777; margin: 0; }
.profile-form { display: flex; flex-direction: column; gap: 1rem; max-width: 480px; }
.profile-form__field { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.9rem; }
.profile-form__field input, .profile-form__field textarea {
  padding: 0.4rem 0.5rem; border: 1px solid #bdbdbd; border-radius: 4px; font-size: 0.9rem;
}
.profile-form__actions { display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; margin-top: 0.5rem; }
.btn-primary { padding: 0.5rem 1.25rem; background: #1565c0; color: white; border: none; border-radius: 4px; cursor: pointer; }
.btn-primary:disabled { opacity: 0.6; cursor: wait; }
.link-action { font-size: 0.875rem; color: #1565c0; text-decoration: none; }
.link-action:hover { text-decoration: underline; }
</style>
