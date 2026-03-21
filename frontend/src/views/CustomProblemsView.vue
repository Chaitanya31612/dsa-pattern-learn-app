<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface CustomProblem {
  slug: string
  title: string
  difficulty: string
  pattern_name: string
  description_html?: string
  description_text?: string
  time_complexity?: string
  space_complexity?: string
}

const customProblems = ref<CustomProblem[]>([])
const loadingList = ref(true)

const newSlug = ref('')
const processing = ref(false)
const processStatus = ref('')
const error = ref<string | null>(null)

function getApiBaseUrl(): string {
  const base = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ?? ''
  return base.endsWith('/') ? base.slice(0, -1) : base
}

function getApiUrl(path: string): string {
  const base = getApiBaseUrl()
  return base ? `${base}${path}` : path
}

async function loadCustomProblems() {
  loadingList.value = true
  try {
    const res = await fetch(getApiUrl('/api/custom-problems'))
    if (!res.ok) throw new Error('Failed to load custom problems')
    customProblems.value = await res.json()
  } catch (err) {
    console.error(err)
  } finally {
    loadingList.value = false
  }
}

async function submitUrl() {
  let slug = newSlug.value.trim()
  
  if (slug.includes('leetcode.com/problems/')) {
    const parts = slug.split('leetcode.com/problems/')
    slug = parts[1]?.split('/')[0] || ''
  } else if (slug.includes('/')) {
    slug = slug.split('/')[0] || ''
  }

  if (!slug) return

  const url = `https://leetcode.com/problems/${slug}/`

  processing.value = true
  error.value = null
  processStatus.value = 'Extracting and processing problem from LeetCode...'

  try {
    const res = await fetch(getApiUrl('/api/process-leetcode'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    })

    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || `Failed with status ${res.status}`)
    }

    // After success, reload list and clear input
    newSlug.value = ''
    processStatus.value = 'Problem successfully added!'
    setTimeout(() => { processStatus.value = '' }, 3000)
    await loadCustomProblems()
  } catch (err: any) {
    error.value = err.message || 'An unknown error occurred'
    processStatus.value = ''
  } finally {
    processing.value = false
  }
}

onMounted(() => {
  loadCustomProblems()
})
</script>

<template>
  <div class="container custom-problems-view animate-in">
    <header class="page-header">
      <h1 class="page-title">Custom Problems</h1>
      <p class="page-subtitle terminal-prompt">Add external problems directly into your learning space.</p>
    </header>

    <div class="card card-flat importer-card" style="margin-bottom: var(--space-xl)">
      <h3 class="section-heading">🔗 Import from LeetCode</h3>
      <div class="import-row">
        <input
          v-model="newSlug"
          type="text"
          class="url-input"
          placeholder="https://leetcode.com/problems/your-problem-name/"
          :disabled="processing"
          @keyup.enter="submitUrl"
        />
        <button
          class="btn btn-primary"
          :disabled="!newSlug || processing"
          @click="submitUrl"
        >
          {{ processing ? 'Processing...' : 'Import Problem' }}
        </button>
      </div>

      <!-- Status or Error -->
      <div v-if="processStatus" class="status-msg success">{{ processStatus }}</div>
      <div v-if="error" class="status-msg error">⚠️ {{ error }}</div>
    </div>

    <div class="custom-problems-list">
      <h3 class="section-heading">Your Custom Database</h3>
      <div v-if="loadingList" class="terminal-prompt">loading...</div>
      <div v-else-if="customProblems.length === 0" class="empty-state">
        <span class="empty-icon">📂</span>
        <p>No custom problems imported yet.</p>
      </div>
      <div v-else class="problem-grid">
        <router-link
          v-for="prob in customProblems"
          :key="prob.slug"
          :to="`/problem/${prob.slug}`"
          class="card card-interactive problem-card"
        >
          <div class="card-header">
            <h4 class="prob-title">{{ prob.title }}</h4>
            <span
              class="badge"
              :class="`badge-${(prob.difficulty || 'easy').toLowerCase()}`"
            >
              {{ prob.difficulty || 'Easy' }}
            </span>
          </div>
          <div class="card-meta">
            <span class="tag" v-if="prob.pattern_name">{{ prob.pattern_name }}</span>
            <span class="mono-text" v-if="prob.time_complexity">⏱ {{ prob.time_complexity }}</span>
          </div>
        </router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.custom-problems-view {
  padding-bottom: var(--space-2xl);
}

.page-header {
  margin-bottom: var(--space-xl);
}

.page-title {
  font-size: var(--text-3xl);
  font-weight: 800;
  margin-bottom: var(--space-xs);
}

.page-subtitle {
  color: var(--text-muted);
}

.section-heading {
  font-size: var(--text-lg);
  font-weight: 700;
  margin-bottom: var(--space-md);
}

.importer-card {
  padding: var(--space-xl);
}

.import-row {
  display: flex;
  gap: var(--space-md);
  margin-bottom: var(--space-sm);
}

.url-input {
  flex: 1;
  padding: var(--space-sm) var(--space-md);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  transition: all var(--transition-fast);
}

.url-input:focus {
  outline: none;
  border-color: var(--accent-cyan);
  box-shadow: var(--glow-cyan);
}

.url-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.status-msg {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  margin-top: var(--space-md);
}

.status-msg.success {
  color: var(--accent-green);
}

.status-msg.error {
  color: var(--accent-red);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-2xl) 0;
  color: var(--text-muted);
}

.empty-icon {
  font-size: 48px;
  opacity: 0.5;
}

.problem-grid {
  display: grid;
  gap: var(--space-md);
}

@media (min-width: 768px) {
  .problem-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.problem-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.prob-title {
  font-weight: 700;
  font-size: var(--text-base);
  margin: 0;
}

.card-meta {
  display: flex;
  gap: var(--space-sm);
  align-items: center;
}

.mono-text {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
}
</style>
