<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useCandidateStore } from '@/stores/candidate'
import BannerAlert from '@/components/common/BannerAlert.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import TimestampDisplay from '@/components/common/TimestampDisplay.vue'
import CandidateProfileInitBanner from '@/components/candidate/CandidateProfileInitBanner.vue'
import type { ExamScoreCreate } from '@/types/candidate'

const auth = useAuthStore()
const store = useCandidateStore()
const candidateId = computed(() => auth.candidateId ?? '')
const missingProfile = computed(() => auth.user?.role === 'candidate' && !auth.candidateId)
const saved = ref(false)

const newScore = reactive<ExamScoreCreate>({
  subject_code: '',
  subject_name: '',
  score: '',
  max_score: null,
  exam_date: null,
})

onMounted(async () => {
  if (!candidateId.value) return
  await store.loadExamScores(candidateId.value)
})

async function onProfileInitialized(id: string): Promise<void> {
  await store.loadExamScores(id)
}

async function submit(): Promise<void> {
  if (!candidateId.value) return
  saved.value = false
  const ok = await store.addExamScore(candidateId.value, { ...newScore })
  if (ok) {
    saved.value = true
    newScore.subject_code = ''
    newScore.subject_name = ''
    newScore.score = ''
    newScore.max_score = null
    newScore.exam_date = null
  }
}
</script>

<template>
  <div class="exam-scores-view" data-testid="exam-scores-view">
    <h2>Exam Scores</h2>
    <router-link to="/candidate/profile" class="back-link">← Back to Profile</router-link>

    <CandidateProfileInitBanner
      v-if="missingProfile"
      @initialized="onProfileInitialized"
    />

    <LoadingSpinner v-if="store.loading" label="Loading…" />
    <BannerAlert v-if="saved" type="success" message="Score added." :dismissible="true" @dismiss="saved = false" />
    <BannerAlert v-if="store.error" type="error" :message="store.error" :dismissible="true" @dismiss="store.clearError()" />

    <table v-if="store.examScores.length > 0" class="scores-table">
      <thead>
        <tr><th>Subject Code</th><th>Subject</th><th>Score</th><th>Max</th><th>Date</th></tr>
      </thead>
      <tbody>
        <tr v-for="s in store.examScores" :key="s.id">
          <td>{{ s.subject_code }}</td>
          <td>{{ s.subject_name }}</td>
          <td>{{ s.score }}</td>
          <td>{{ s.max_score ?? '—' }}</td>
          <td><TimestampDisplay v-if="s.exam_date" :value="s.exam_date" date-only /><span v-else>—</span></td>
        </tr>
      </tbody>
    </table>
    <EmptyState v-else message="No exam scores recorded yet." />

    <section v-if="!missingProfile" class="add-score">
      <h3>Add Score</h3>
      <form class="add-score__form" @submit.prevent="submit" data-testid="add-score-form">
        <label>Subject Code <input v-model="newScore.subject_code" type="text" required data-testid="field-subject-code" /></label>
        <label>Subject Name <input v-model="newScore.subject_name" type="text" required data-testid="field-subject-name" /></label>
        <label>Score <input v-model="newScore.score" type="text" required /></label>
        <label>Max Score <input v-model="newScore.max_score" type="text" /></label>
        <label>Date <input v-model="newScore.exam_date" type="date" /></label>
        <button type="submit" class="btn-primary" :disabled="store.loading">Add</button>
      </form>
    </section>
  </div>
</template>

<style scoped>
.exam-scores-view { display: flex; flex-direction: column; gap: 1.25rem; }
.exam-scores-view h2 { margin: 0; }
.back-link { font-size: 0.875rem; color: #1565c0; text-decoration: none; }
.back-link:hover { text-decoration: underline; }
.scores-table { border-collapse: collapse; font-size: 0.875rem; width: 100%; }
.scores-table th, .scores-table td { padding: 0.5rem 0.75rem; border-bottom: 1px solid #e0e0e0; text-align: left; }
.scores-table th { background: #f5f5f5; font-weight: 600; }
.add-score h3 { margin: 0 0 0.5rem; font-size: 1rem; }
.add-score__form { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: flex-end; }
.add-score__form label { display: flex; flex-direction: column; gap: 0.2rem; font-size: 0.875rem; }
.add-score__form input { padding: 0.35rem 0.5rem; border: 1px solid #bdbdbd; border-radius: 4px; }
.btn-primary { padding: 0.5rem 1.25rem; background: #1565c0; color: white; border: none; border-radius: 4px; cursor: pointer; }
.btn-primary:disabled { opacity: 0.6; }
</style>
