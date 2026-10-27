<script setup lang="ts">
import { ref } from 'vue'
const status = ref('')
const busy = ref(false)
async function checkAI() {
  busy.value = true
  try {
    const base = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
    const response = await fetch(`${base}/api/health`, { signal: AbortSignal.timeout(5000) })
    const data = await response.json()
    if (!response.ok || data.status !== 'ok') throw new Error()
    status.value = `Backend connected · ${data.provider} · ${data.model}. This checks configuration; the next AI request checks provider availability.`
  } catch { status.value = 'AI backend is unavailable. Your lessons, drafts, quizzes, recall, and self-review still work. Start the backend on port 8000, then check again.' }
  finally { busy.value = false }
}
</script>
<template>
  <details class="hld-howto"><summary>How to use this course · when AI and solutions appear</summary>
    <ol><li><strong>Learn:</strong> read one short idea. Study its example and picture. Write it back in your words. “Mark explored” saves progress; it does not grade your notes.</li>
      <li><strong>Worked example:</strong> predict the next decision before reading its explanation.</li>
      <li><strong>Design & repair:</strong> try Design, then Transfer with a changed rule, then Repair a broken design. Use the seven tabs as your answer structure.</li>
      <li><strong>Save & submit:</strong> saves a fixed copy. It unlocks review and the reference. It does not run AI automatically.</li>
      <li><strong>Get AI rubric feedback:</strong> compares that saved copy with the problem, a course reference, and eight design scoring areas. Focused repairs use four areas. Different sound designs are welcome. Read the reasons, not only the score.</li>
      <li><strong>Reveal reference:</strong> opens the prepared explanation. Try AI feedback first. Fix one gap, then save another attempt. Later, close all notes and try a fresh draft.</li>
      <li><strong>Quiz → Spaced recall:</strong> submit all answers before seeing explanations. Missed concepts return now. Other cards return after a delay. Explain from memory before revealing.</li></ol>
    <p>A current attempt using hints or a visible reference is assisted. A later closed-book attempt may be unaided; mark assistance honestly. AI and self-scores are provisional. They do not prove interview or production readiness.</p>
    <p>At 7 hours/week, choose one module and its reviews. The full two-volume track has 136 planned learning hours. Finish by evidence, not by rushing to a date.</p>
    <button class="btn" :disabled="busy" @click="checkAI">{{ busy ? 'Checking…' : 'Check AI backend connection' }}</button><p role="status">{{ status }}</p>
  </details>
</template>
