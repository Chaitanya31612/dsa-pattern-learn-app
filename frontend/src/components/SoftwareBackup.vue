<script setup lang="ts">
import { ref } from 'vue'
import { useSoftware } from '../composables/useSoftware'
import { validateSoftwareProgress } from '../lib/softwareLearning'
const { progress, replaceBackup, rawBackup, storageError } = useSoftware()
const message = ref('')
const candidate = ref<unknown>(null)
const file = ref<HTMLInputElement | null>(null)
const exportText = ref('')
const importText = ref('')
function validateText() {
  candidate.value = null
  try {
    if (importText.value.length > 10_000_000) throw new Error('Backup is too large (10 MB maximum).')
    candidate.value = validateSoftwareProgress(JSON.parse(importText.value))
    message.value = 'Valid backup. Export your current progress first. Import replaces Software Learnings progress only.'
  } catch (err) { message.value = err instanceof Error ? err.message : 'Invalid backup.' }
}
function download(raw = false) {
  const content = raw ? rawBackup() : JSON.stringify(progress.value, null, 2)
  if (!content) { message.value = 'No saved copy exists.'; return }
  const url = URL.createObjectURL(new Blob([content], { type: 'application/json' }))
  const a = document.createElement('a'); a.href = url; a.download = `software-learnings-${raw ? 'stored-' : ''}${new Date().toISOString().slice(0,10)}.json`; a.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
async function inspect(event: Event) {
  candidate.value = null; message.value = ''
  const selected = (event.target as HTMLInputElement).files?.[0]
  if (!selected) return
  try {
    if (selected.size > 10_000_000) throw new Error('Backup is too large (10 MB maximum).')
    candidate.value = validateSoftwareProgress(JSON.parse(await selected.text()))
    message.value = 'Valid backup. Export your current progress first. Import replaces Software Learnings progress only.'
  } catch (err) { message.value = err instanceof Error ? err.message : 'Invalid backup.' }
  if (file.value) file.value.value = ''
}
function restore() {
  if (!candidate.value) return
  try { replaceBackup(candidate.value); candidate.value = null; message.value = 'Software Learnings backup imported.' }
  catch { message.value = 'Could not save the backup. Current progress was kept.' }
}
</script>
<template>
  <section class="card software-backup">
    <h3>Software Learnings backup</h3><p>Progress lives in this browser. Export regularly to keep your drafts, attempts, quizzes, and recall schedule.</p>
    <p v-if="storageError" role="alert">{{ storageError }}</p>
    <div class="sw-row"><button class="btn" @click="download()">Export progress</button><button class="btn btn-ghost" @click="download(true)">Export stored copy</button><label class="btn">Choose backup<input ref="file" type="file" accept="application/json,.json" @change="inspect" /></label></div>
    <details><summary>Copy or paste backup text</summary><p>Use this when downloads are unavailable. Keep a copy outside this browser.</p><button class="btn" @click="exportText = JSON.stringify(progress, null, 2)">Show backup text</button><label v-if="exportText">Current backup JSON<textarea aria-label="Current backup JSON" :value="exportText" readonly rows="5" /></label><label>Paste backup JSON<textarea v-model="importText" aria-label="Paste backup JSON" rows="5" /></label><button class="btn" :disabled="!importText.trim()" @click="validateText">Validate pasted backup</button></details>
    <p role="status">{{ message }}</p><div v-if="candidate" class="sw-row"><button class="btn" @click="restore">Replace with this backup</button><button class="btn btn-ghost" @click="candidate = null; message = ''">Cancel import</button></div>
  </section>
</template>
<style scoped>.software-backup{padding:24px;margin:24px 0}.software-backup p{margin:12px 0;line-height:1.6}.sw-row{display:flex;gap:12px;flex-wrap:wrap}input{display:block;max-width:220px;margin-top:8px}details{margin:20px 0}summary{cursor:pointer;color:var(--accent-cyan)}label{display:block;margin:12px 0}textarea{display:block;width:100%;margin-top:8px;padding:12px;background:var(--bg-primary);color:var(--text-primary);border:1px solid var(--border-default);border-radius:8px;font:inherit}</style>
