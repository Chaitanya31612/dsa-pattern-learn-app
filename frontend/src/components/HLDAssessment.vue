<script setup lang="ts">
import { aiHeaders } from '../lib/aiConnection'
import { computed, ref } from 'vue'
import type { HLDAttempt, HLDModule, HLDReview } from '../types/hld'
import { DIMENSION_LABELS, HLD_DIMENSIONS } from '../types/hld'
import { useHLD } from '../composables/useHLD'
const props = defineProps<{ module: HLDModule; attempt: HLDAttempt }>()
const { saveReview } = useHLD()
const busy = ref(false)
const error = ref('')
const showSelf = ref(false)
const repair = computed(() => props.module.exercises.find(e => e.id === props.attempt.exerciseId)?.kind === 'repair')
const dimensions = computed(() => repair.value ? HLD_DIMENSIONS.filter(id => ['requirements','flows','correctness','failure_operations'].includes(id)) : HLD_DIMENSIONS)
const scores = ref(Object.fromEntries(HLD_DIMENSIONS.map(id => [id, 0])) as Record<typeof HLD_DIMENSIONS[number], number>)
const evidence = ref(Object.fromEntries(HLD_DIMENSIONS.map(id => [id, ''])) as Record<typeof HLD_DIMENSIONS[number], string>)
const critical = ref(false)
async function evaluate() {
  busy.value = true; error.value = ''
  const submitted = props.attempt
  const base = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
  try {
    const res = await fetch(`${base}/api/hld/evaluate`, { method: 'POST', headers: aiHeaders(),
      signal: AbortSignal.timeout(90_000), body: JSON.stringify({ module_id: props.module.id, exercise_id: submitted.exerciseId,
        attempt: { phases: submitted.phases, diagram: submitted.diagram, assisted: submitted.assisted } }) })
    const data = await res.json()
    if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'AI review unavailable.')
    saveReview(props.module.id, submitted.id, data as HLDReview)
  } catch (err) { error.value = err instanceof Error ? err.message : 'AI review unavailable. Continue with self-review.' }
  finally { busy.value = false }
}
function selfReview() {
  if (dimensions.value.some(id => !evidence.value[id].trim())) { error.value = 'Add specific evidence or explain what is missing for every dimension.'; return }
  saveReview(props.module.id, props.attempt.id, { source: 'self', scope: repair.value ? 'repair' : 'design', dimensions: dimensions.value.map(id => ({ id, score: scores.value[id],
    evidence: evidence.value[id], feedback: evidence.value[id] })), summary: 'Self-assessment: validate your reasoning with a counterexample or peer.',
    strengths: [], gaps: dimensions.value.filter(id => scores.value[id] < 2).map(id => DIMENSION_LABELS[id]), next_exercise: props.module.recallPrompt,
    critical_issue: critical.value, total: 0, passed: false })
  showSelf.value = false; error.value = ''
}
</script>
<template>
  <section class="hld-assessment">
    <div class="hld-row"><h3>Review this saved attempt</h3><span class="hld-muted">{{ new Date(attempt.createdAt).toLocaleString() }} · {{ attempt.assisted ? 'Assisted' : 'Unaided' }}</span></div>
    <div class="hld-row">
      <button class="btn btn-primary" :disabled="busy" @click="evaluate">{{ busy ? 'Reviewing your reasoning…' : 'Get AI rubric feedback' }}</button>
      <button class="btn" @click="showSelf = !showSelf">Self-review with evidence</button>
    </div>
    <p class="hld-muted">{{ repair ? 'Four repair areas, 0–3 each: broken rule, corrected flow, correctness, and recovery. A repair is practice, not a full-design pass.' : 'Eight areas, 0–3 each. A critical correctness issue blocks a passing result.' }} AI and self-review are provisional.</p>
    <p v-if="error" role="alert" class="hld-error">{{ error }}</p>
    <div v-if="showSelf" class="hld-self-review">
      <p>0 missing/wrong · 1 needs help · 2 works and is explained · 3 also handles a changed case</p>
      <div v-for="id in dimensions" :key="id" class="hld-rubric-row">
        <label :for="`score-${id}`">{{ DIMENSION_LABELS[id] }}</label>
        <select :id="`score-${id}`" v-model.number="scores[id]" class="hld-input"><option v-for="n in [0,1,2,3]" :key="n" :value="n">{{ n }}/3</option></select>
        <textarea v-model="evidence[id]" class="hld-input" rows="2" :aria-label="`${DIMENSION_LABELS[id]} evidence`" placeholder="Cite your reasoning, or explain the missing evidence."></textarea>
      </div>
      <label class="hld-label"><input v-model="critical" type="checkbox" /> Central invariant broken or guarantee unsupported</label>
      <button class="btn btn-primary" @click="selfReview">Save self-assessment</button>
    </div>
    <div v-if="attempt.review" class="hld-feedback">
      <div class="hld-row"><strong>{{ attempt.review.total }}/{{ attempt.review.scope === 'repair' ? 12 : 24 }}</strong><span>{{ attempt.review.source === 'ai' ? 'AI feedback' : 'Self-review' }} · {{ attempt.review.scope === 'repair' ? 'Focused repair feedback' : attempt.review.passed ? 'Course threshold met provisionally' : 'Keep practicing' }}</span></div>
      <p>{{ attempt.review.summary }}</p>
      <p v-if="attempt.review.critical_issue" class="hld-error">The key rule needs a safe mechanism before this design can pass.</p>
      <p><strong>Try one small step next:</strong> {{ attempt.review.next_exercise }}</p>
      <details v-for="d in attempt.review.dimensions" :key="d.id" class="hld-report-row">
        <summary>{{ DIMENSION_LABELS[d.id] }} · {{ d.score }}/3 · why?</summary>
        <p><strong>Evidence:</strong> {{ d.evidence }}</p><p>{{ d.feedback }}</p>
      </details>
      <h4 v-if="attempt.review.gaps.length">Focus on these first</h4><ul><li v-for="gap in attempt.review.gaps.slice(0,3)" :key="gap">{{ gap }}</li></ul>
    </div>
  </section>
</template>
