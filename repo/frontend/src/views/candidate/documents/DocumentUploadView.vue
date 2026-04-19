<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useDocumentStore } from '@/stores/document'
import UploadPanel from '@/components/common/UploadPanel.vue'
import BannerAlert from '@/components/common/BannerAlert.vue'
import CandidateProfileInitBanner from '@/components/candidate/CandidateProfileInitBanner.vue'

const auth = useAuthStore()
const docStore = useDocumentStore()
const router = useRouter()
// Candidate profile UUID (distinct from user.id), resolved via /auth/me.
const candidateId = computed(() => auth.candidateId ?? '')
const missingProfile = computed(() => auth.user?.role === 'candidate' && !auth.candidateId)

const requirementCode = ref<string | null>(null)
const uploadedHash = ref<string | null>(null)

async function handleUpload(payload: { file: File; requirementCode?: string | null }): Promise<void> {
  if (!candidateId.value) return
  const result = await docStore.upload(candidateId.value, payload.file, payload.requirementCode ?? requirementCode.value)
  if (result) {
    uploadedHash.value = result.sha256_hash
  }
}

function goBack(): void {
  router.push('/candidate/documents')
}
</script>

<template>
  <div class="upload-view" data-testid="document-upload-view">
    <div class="upload-view__header">
      <h2>Upload Document</h2>
      <button type="button" class="back-btn" @click="goBack">← Back</button>
    </div>

    <CandidateProfileInitBanner v-if="missingProfile" />

    <BannerAlert v-if="docStore.uploadError" type="error" :message="docStore.uploadError" :dismissible="true" @dismiss="docStore.clearError()" />

    <div v-if="uploadedHash" class="upload-success" data-testid="upload-success">
      <BannerAlert type="success" message="Document uploaded successfully." />
      <p class="upload-success__hash">SHA-256: <code>{{ uploadedHash }}</code></p>
      <router-link to="/candidate/documents" class="btn-primary">View Documents</router-link>
    </div>

    <template v-else>
      <label class="req-code-label">
        Requirement Code (optional)
        <input
          v-model="requirementCode"
          type="text"
          placeholder="e.g. TRANSCRIPT"
          class="req-code-input"
          data-testid="field-requirement-code"
        />
      </label>

      <UploadPanel
        :requirement-code="requirementCode"
        :disabled="docStore.uploading"
        @upload="handleUpload"
      />

      <p v-if="docStore.uploading" class="uploading-msg">Uploading…</p>
    </template>
  </div>
</template>

<style scoped>
.upload-view { display: flex; flex-direction: column; gap: 1.25rem; max-width: 480px; }
.upload-view__header { display: flex; align-items: center; justify-content: space-between; }
.upload-view__header h2 { margin: 0; }
.back-btn { background: none; border: none; color: #1565c0; cursor: pointer; font-size: 0.875rem; }
.req-code-label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.875rem; }
.req-code-input { padding: 0.4rem 0.5rem; border: 1px solid #bdbdbd; border-radius: 4px; font-size: 0.875rem; }
.uploading-msg { color: #777; font-size: 0.875rem; }
.upload-success { display: flex; flex-direction: column; gap: 0.75rem; }
.upload-success__hash { font-size: 0.75rem; color: #555; word-break: break-all; }
.upload-success__hash code { background: #f5f5f5; padding: 0.125rem 0.25rem; border-radius: 3px; }
.btn-primary { display: inline-block; padding: 0.5rem 1rem; background: #1565c0; color: white; border-radius: 4px; text-decoration: none; font-size: 0.875rem; align-self: flex-start; }
</style>
