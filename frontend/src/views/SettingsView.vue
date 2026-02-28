<script setup lang="ts">
import { ref } from 'vue'
import { useProgress } from '../composables/useProgress'

const { exportProgress, importProgress, state } = useProgress()

const showImportDialog = ref(false)
const importText = ref('')
const importStatus = ref<'idle' | 'success' | 'error'>('idle')
const exportStatus = ref<'idle' | 'done'>('idle')

function doExport() {
  const json = exportProgress()
  const blob = new Blob([json], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `dsa-progress-${new Date().toISOString().slice(0, 10)}.json`
  a.click()
  URL.revokeObjectURL(url)
  exportStatus.value = 'done'
  setTimeout(() => exportStatus.value = 'idle', 2000)
}

function doImport() {
  try {
    importProgress(importText.value)
    importStatus.value = 'success'
    setTimeout(() => {
      importStatus.value = 'idle'
      showImportDialog.value = false
      importText.value = ''
    }, 1500)
  } catch {
    importStatus.value = 'error'
  }
}

function handleFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    importText.value = reader.result as string
  }
  reader.readAsText(file)
}

function clearAll() {
  if (confirm('Are you sure you want to clear ALL progress? This cannot be undone.')) {
    Object.keys(state.solved).forEach(k => delete state.solved[k])
    Object.keys(state.notes).forEach(k => delete state.notes[k])
    Object.keys(state.reflections).forEach(k => delete state.reflections[k])
  }
}

const totalSolved = Object.keys(state.solved).length
const totalNotes = Object.keys(state.notes).length
const totalReflections = Object.keys(state.reflections).length
</script>

<template>
  <div class="container settings-view">
    <header class="sv-header animate-in">
      <span class="terminal-prompt">settings.config()</span>
      <h1 class="sv-title">Settings</h1>
    </header>

    <!-- ═══ Progress Stats ═══ -->
    <section class="card card-flat animate-in stagger-1" style="margin-bottom: var(--space-lg)">
      <h3 class="section-heading">📊 Your Data</h3>
      <div class="data-stats">
        <div class="data-stat">
          <span class="ds-num mono">{{ totalSolved }}</span>
          <span class="ds-label">problems solved</span>
        </div>
        <div class="data-stat">
          <span class="ds-num mono">{{ totalNotes }}</span>
          <span class="ds-label">notes written</span>
        </div>
        <div class="data-stat">
          <span class="ds-num mono">{{ totalReflections }}</span>
          <span class="ds-label">reflections</span>
        </div>
      </div>
    </section>

    <!-- ═══ Export/Import ═══ -->
    <section class="card card-flat animate-in stagger-2" style="margin-bottom: var(--space-lg)">
      <h3 class="section-heading">💾 Backup & Restore</h3>
      <p class="setting-desc">Your progress is stored in localStorage. Export to back it up.</p>

      <div class="action-row">
        <button class="btn btn-primary" @click="doExport">
          {{ exportStatus === 'done' ? '✓ Downloaded!' : '↓ Export Progress' }}
        </button>
        <button class="btn" @click="showImportDialog = !showImportDialog">
          ↑ Import Progress
        </button>
        <div style="flex:1"></div>
        <button class="btn btn-ghost" style="color: var(--accent-red)" @click="clearAll">
          ✕ Clear All Data
        </button>
      </div>

      <!-- Import Dialog -->
      <div v-if="showImportDialog" class="import-dialog animate-in" style="margin-top: var(--space-md)">
        <div class="import-methods">
          <label class="file-upload-label">
            <input type="file" accept=".json" @change="handleFile" class="file-input" />
            📁 Choose JSON file
          </label>
          <span class="import-or">or paste JSON below:</span>
        </div>
        <textarea
          v-model="importText"
          class="import-textarea"
          placeholder='{"solved": {...}, "notes": {...}, "reflections": {...}}'
          rows="4"
        ></textarea>
        <div class="import-actions">
          <button
            class="btn btn-primary"
            :disabled="!importText.trim()"
            @click="doImport"
          >
            {{ importStatus === 'success' ? '✓ Imported!' : importStatus === 'error' ? '✗ Invalid JSON' : 'Import' }}
          </button>
          <button class="btn btn-ghost" @click="showImportDialog = false">Cancel</button>
        </div>
      </div>
    </section>

    <!-- ═══ Smart Features ═══ -->
    <section class="card card-flat animate-in stagger-3" style="margin-bottom: var(--space-lg)">
      <h3 class="section-heading">⚡ Smart Features</h3>
      <p class="setting-desc">What makes DSA Pattern Lab different from a plain problem list.</p>
      <ul class="smart-list">
        <li>
          <span class="smart-icon">🧠</span>
          <div>
            <strong>Smart Random</strong>
            <span class="smart-desc">Weighted problem selection based on your confidence scores, difficulty progression, pattern momentum, and stale-pattern detection — not just random.</span>
          </div>
        </li>
        <li>
          <span class="smart-icon">🔄</span>
          <div>
            <strong>Spaced Repetition</strong>
            <span class="smart-desc">Problems resurface for review at intervals based on confidence: 1 day (shaky), 3 days (okay), 7 days (solid).</span>
          </div>
        </li>
        <li>
          <span class="smart-icon">🪞</span>
          <div>
            <strong>Reflection-Driven Learning</strong>
            <span class="smart-desc">After solving, a 4-step reflection prompts you to articulate the pattern, the signal, the deviation, and your confidence — reinforcing long-term retention.</span>
          </div>
        </li>
        <li>
          <span class="smart-icon">🔗</span>
          <div>
            <strong>Bridge Problems</strong>
            <span class="smart-desc">Problems that appear in both NeetCode and Striver sheets are flagged as high-value overlap — the must-solve intersection of two curated lists.</span>
          </div>
        </li>
        <li>
          <span class="smart-icon">🎯</span>
          <div>
            <strong>LLM-Generated Insights</strong>
            <span class="smart-desc">Every problem has AI-generated pattern hints, key insights, template deviations, and common mistakes — not just a link to LeetCode.</span>
          </div>
        </li>
        <li>
          <span class="smart-icon">🧩</span>
          <div>
            <strong>Pattern-First Learning</strong>
            <span class="smart-desc">Problems grouped by 17 algorithmic patterns with template code, trigger phrases, and mental models — learn the pattern, then grind the problems.</span>
          </div>
        </li>
        <li>
          <span class="smart-icon">🎮</span>
          <div>
            <strong>Pattern Quiz</strong>
            <span class="smart-desc">Test yourself: given a problem description, can you identify the pattern before looking? Score tracking and session history included.</span>
          </div>
        </li>
      </ul>
    </section>

    <!-- ═══ About ═══ -->
    <section class="card card-flat animate-in stagger-4">
      <h3 class="section-heading">ℹ️ About</h3>
      <p class="setting-desc">
        DSA Pattern Lab — master DSA through pattern recognition.
        <br/>Built with Vue 3 + TypeScript. Data generated with LLMs (Gemini + Groq).
      </p>
      <p class="setting-desc mono" style="font-size: var(--text-xs); margin-top: var(--space-sm)">
        17 patterns · 200 problems · 100% local · zero backend
      </p>
      <p class="setting-desc mono" style="font-size: var(--text-xs); margin-top: var(--space-sm)">
        Architected by Human Overlord: Chaitanya Gupta 🧠✨
      </p>
    </section>
  </div>
</template>

<style scoped>
.sv-header {
  margin-bottom: var(--space-xl);
}

.sv-title {
  font-size: var(--text-2xl);
  font-weight: 800;
}

.section-heading {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: var(--text-base);
  font-weight: 700;
  margin-bottom: var(--space-md);
}

.setting-desc {
  color: var(--text-secondary);
  font-size: var(--text-sm);
  line-height: 1.6;
  margin-bottom: var(--space-md);
}

.data-stats {
  display: flex;
  gap: var(--space-xl);
}

.data-stat {
  display: flex;
  flex-direction: column;
}

.ds-num {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--accent-cyan);
}

.ds-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.action-row {
  display: flex;
  gap: var(--space-sm);
  flex-wrap: wrap;
  align-items: center;
}

.import-dialog {
  padding: var(--space-md);
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.import-methods {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  margin-bottom: var(--space-md);
}

.file-upload-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border: 1px dashed var(--border-default);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.file-upload-label:hover {
  border-color: var(--accent-cyan);
  color: var(--accent-cyan);
}

.file-input {
  display: none;
}

.import-or {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.import-textarea {
  width: 100%;
  padding: var(--space-sm) var(--space-md);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: 1.6;
  resize: vertical;
  margin-bottom: var(--space-sm);
}

.import-textarea:focus {
  outline: none;
  border-color: var(--accent-cyan);
}

.import-actions {
  display: flex;
  gap: var(--space-sm);
}

/* ── Smart Features ────────────────── */
.smart-list {
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.smart-list li {
  display: flex;
  gap: var(--space-md);
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  transition: border-color var(--transition-fast);
}

.smart-list li:hover {
  border-color: var(--border-default);
}

.smart-icon {
  font-size: var(--text-lg);
  flex-shrink: 0;
  line-height: 1.6;
}

.smart-list strong {
  display: block;
  font-size: var(--text-sm);
  color: var(--text-primary);
  margin-bottom: 2px;
}

.smart-desc {
  display: block;
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: 1.5;
}

@media (max-width: 768px) {
  .data-stats {
    flex-direction: column;
    gap: var(--space-md);
  }
}
</style>
