<script setup lang="ts">
import { ref } from 'vue'
import { useHLD } from '../composables/useHLD'
const { exportProgress, importProgress } = useHLD()
const status = ref('')
function download() {
  const url = URL.createObjectURL(new Blob([exportProgress()], { type: 'application/json' }))
  const a = document.createElement('a'); a.href = url; a.download = `hld-progress-${new Date().toISOString().slice(0, 10)}.json`; a.click()
  URL.revokeObjectURL(url); status.value = 'HLD backup downloaded.'
}
async function restore(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    const raw = await file.text()
    if (confirm('Replace HLD progress with this backup? DSA and LLD data are unaffected.')) {
      importProgress(raw); status.value = 'HLD backup restored.'
    }
  } catch (err) { status.value = err instanceof Error ? err.message : 'Invalid backup.' }
  input.value = ''
}
</script>
<template>
  <div class="hld-backup">
    <button class="btn" @click="download">Export HLD progress</button>
    <label class="btn">Restore HLD backup<input type="file" accept="application/json,.json" @change="restore" /></label>
    <span role="status">{{ status }}</span>
  </div>
</template>
<style scoped>
.hld-backup { display:flex; gap:12px; flex-wrap:wrap; align-items:center; }
input { max-width:180px; font-size:var(--text-xs); margin-left:8px; }
span { font-size:var(--text-sm); color:var(--text-secondary); }
</style>
