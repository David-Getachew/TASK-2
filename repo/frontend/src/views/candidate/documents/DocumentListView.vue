<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCandidateStore } from '@/stores/candidate'
import { useDocumentStore } from '@/stores/document'
import StatusChip from '@/components/common/StatusChip.vue'
import ChecklistWidget from '@/components/common/ChecklistWidget.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import BannerAlert from '@/components/common/BannerAlert.vue'
import TimestampDisplay from '@/components/common/TimestampDisplay.vue'
import CandidateProfileInitBanner from '@/components/candidate/CandidateProfileInitBanner.vue'

const auth = useAuthStore()
const candidateStore = useCandidateStore()
const docStore = useDocumentStore()
const router = useRouter()
// Candidate profile UUID (distinct from user.id), resolved via /auth/me.
const candidateId = computed(() => auth.candidateId ?? '')
const missingProfile = computed(() => auth.user?.role === 'candidate' && !auth.candidateId)

async function onProfileInitialized(id: string): Promise<void> {
  await Promise.all([
    docStore.loadDocuments(id),
    candidateStore.loadChecklist(id),
  ])
}

onMounted(async () => {
  if (!candidateId.value) return
  await Promise.all([
    docStore.loadDocuments(candidateId.value),
    candidateStore.loadChecklist(candidateId.value),
  ])
})
</script>

<template>
  <div class="document-list-view" data-testid="document-list-view">
    <div class="document-list-view__header">
      <h2>Documents</h2>
      <router-link to="/candidate/documents/upload" class="btn-primary btn-sm">
        + Upload Document
      </router-link>
    </div>

    <CandidateProfileInitBanner
      v-if="missingProfile"
      @initialized="onProfileInitialized"
    />

    <LoadingSpinner v-if="docStore.loading" label="Loading documents…" />
    <BannerAlert v-if="docStore.error" type="error" :message="docStore.error" :dismissible="true" @dismiss="docStore.clearError()" />

    <section class="section-block">
      <h3>Document Checklist</h3>
      <ChecklistWidget :items="candidateStore.checklist" />
    </section>

    <section class="section-block">
      <h3>Uploaded Documents</h3>
      <table v-if="docStore.documents.length > 0" class="docs-table">
        <thead>
          <tr>
            <th>Type</th>
            <th>Requirement</th>
            <th>Status</th>
            <th>Version</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="doc in docStore.documents" :key="doc.id" class="docs-table__row">
            <td>{{ doc.document_type }}</td>
            <td>{{ doc.requirement_code ?? '—' }}</td>
            <td>
              <StatusChip :status="doc.current_status" size="sm" />
              <p v-if="doc.resubmission_reason" class="docs-table__reason">
                Reason: {{ doc.resubmission_reason }}
              </p>
            </td>
            <td>v{{ doc.current_version }}</td>
            <td><TimestampDisplay :value="doc.updated_at" /></td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty-msg">No documents uploaded yet.</p>
    </section>
  </div>
</template>

<style scoped>
.document-list-view { display: flex; flex-direction: column; gap: 1.5rem; }
.document-list-view__header { display: flex; align-items: center; justify-content: space-between; }
.document-list-view__header h2 { margin: 0; }
.section-block h3 { font-size: 1rem; margin: 0 0 0.75rem; }
.docs-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.docs-table th, .docs-table td { padding: 0.5rem 0.75rem; border-bottom: 1px solid #e0e0e0; text-align: left; vertical-align: top; }
.docs-table th { background: #f5f5f5; font-weight: 600; }
.docs-table__reason { font-size: 0.75rem; color: #f97316; margin: 0.25rem 0 0; }
.empty-msg { color: #888; font-size: 0.875rem; }
.btn-primary { display: inline-block; padding: 0.5rem 1rem; background: #1565c0; color: white; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; font-size: 0.875rem; }
.btn-sm { padding: 0.35rem 0.75rem; font-size: 0.8rem; }
</style>
