<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useHLD } from '../composables/useHLD'
import { HLD_PHASES, type HLDPhase, type HLDQuizAttempt } from '../types/hld'
import { DAY, newDraft, remainingSeconds } from '../lib/hldLearning'
import HLDMarkdown from '../components/HLDMarkdown.vue'
import HLDDiagram from '../components/HLDDiagram.vue'
import HLDReviewQueue from '../components/HLDReviewQueue.vue'
import HLDAssessment from '../components/HLDAssessment.vue'
import HLDWorkedExample from '../components/HLDWorkedExample.vue'
import HLDHowTo from '../components/HLDHowTo.vue'
import HLDEvidence from '../components/HLDEvidence.vue'
import HLDMechanismLab from '../components/HLDMechanismLab.vue'
import AIChatPanel from '../components/AIChatPanel.vue'
import type { HLDChatContext } from '../composables/useAIChat'

const route = useRoute()
const router = useRouter()
const { course, loading, error, loadCourse, storageError, now, progress, draft, completeSection, submitAttempt, submitQuiz, addCard } = useHLD()
const module = computed(() => course.value?.modules.find(m => m.id === route.params.id))
const moduleProgress = computed(() => module.value ? progress(module.value.id) : null)
const tabs = computed(() => ['learn', ...(module.value?.examples.length ? ['examples'] : []), ...(module.value?.lab ? ['lab'] : []), 'practice', 'quiz', 'recall'])
const tab = computed({ get: () => tabs.value.includes(String(route.query.tab)) ? String(route.query.tab) : 'learn',
  set: value => { void router.replace({ query: { ...route.query, tab: value } }) } })
const sectionIndex = ref(0)
const exampleIndex = ref(0)
const exerciseId = ref('p1')
const activePhase = ref<HLDPhase>('contract')
const selectedAttemptId = ref('')
const solutionVisible = ref(false)
const submission = ref<HTMLElement | null>(null)
const previewDiagram = ref(false)
const notice = ref('')
const quizResult = ref<HLDQuizAttempt | null>(null)
const quizIndex = ref(0)
const decisionQuestion = ref('')
const decisionAnswer = ref('')
const exercise = computed(() => module.value?.exercises.find(e => e.id === exerciseId.value) ?? module.value?.exercises[0])
const work = computed(() => module.value && exercise.value ? draft(module.value.id, exercise.value.id, exercise.value.minutes) : null)
const section = computed(() => module.value?.sections[sectionIndex.value])
const attempts = computed(() => moduleProgress.value?.attempts.filter(a => a.exerciseId === exercise.value?.id) ?? [])
const attempt = computed(() => attempts.value.find(a => a.id === selectedAttemptId.value) ?? attempts.value[attempts.value.length - 1])
const choices = computed(() => moduleProgress.value ? moduleProgress.value.quizDraft ??= {} : {})
const answered = computed(() => module.value?.questions.filter(q => choices.value[q.id] !== undefined).length ?? 0)
const nextModule = computed(() => { const index = course.value?.modules.findIndex(m => m.id === module.value?.id) ?? -1; return index >= 0 ? course.value?.modules[index + 1] : undefined })
const seconds = computed(() => work.value ? remainingSeconds(work.value, now.value) : 0)
const timerText = computed(() => `${Math.floor(seconds.value / 60).toString().padStart(2,'0')}:${(seconds.value % 60).toString().padStart(2,'0')}`)
const phase = computed(() => HLD_PHASES.find(p => p.id === activePhase.value)!)
const phaseTime = computed(() => { const bounds = phase.value.time.replace(' min','').split('–').map(Number); return bounds.map(n => Math.round(n! * (exercise.value?.minutes ?? 45) / 45)).join('–') + ' min' })
const chatContext = computed<HLDChatContext>(() => ({ mode: tab.value === 'practice' ? solutionVisible.value ? 'review' : 'practice' : 'learn',
  ...(tab.value === 'practice' && exercise.value ? { exercise_id: exercise.value.id } : {}), section_id: section.value?.id,
  ...(tab.value === 'examples' ? { example_id: module.value?.examples[exampleIndex.value]?.id } : {}),
  ...(work.value && tab.value === 'practice' ? { attempt: { phases: work.value.phases, diagram: work.value.diagram, assisted: work.value.assisted } } : {}) }))
const coachChips = computed(() => tab.value === 'practice' && !solutionVisible.value
  ? ['Clarify the requirements without giving a design', 'Ask me one question about my weakest assumption', 'Give me one narrow hint']
  : ['Explain the current mechanism with an example', 'What failure should I reason about?', 'Ask me a self-explanation question'])

watch(() => module.value?.id, () => {
  sectionIndex.value = module.value?.sections.findIndex(s => !moduleProgress.value?.completedSections.includes(s.id)) ?? 0
  if (sectionIndex.value < 0) sectionIndex.value = 0
  exampleIndex.value = 0; exerciseId.value = module.value?.exercises.find(e => e.id === route.query.exercise)?.id ?? module.value?.exercises[0]?.id ?? 'p1'; activePhase.value = 'contract'
  solutionVisible.value = false; previewDiagram.value = false; selectedAttemptId.value = ''; notice.value = ''
  const previousQuiz = moduleProgress.value?.quizAttempts[moduleProgress.value.quizAttempts.length - 1]
  quizResult.value = previousQuiz && module.value?.questions.every(q => choices.value[q.id] === previousQuiz.choices[q.id]) ? previousQuiz : null
  quizIndex.value = 0
  decisionQuestion.value = ''; decisionAnswer.value = ''
}, { immediate: true })
watch(exerciseId, () => { solutionVisible.value = false; selectedAttemptId.value = ''; previewDiagram.value = false; notice.value = '' })
watch([exerciseId, tab], ([id, activity]) => {
  if (activity === 'practice' && module.value?.exercises.some(e => e.id === id) && route.query.exercise !== id) {
    void router.replace({ query: { ...route.query, exercise: id } })
  }
})
function nextLesson() {
  if (!module.value || !section.value) return
  completeSection(module.value, section.value.id)
  if (sectionIndex.value < module.value.sections.length - 1) sectionIndex.value++
  else tab.value = module.value.examples.length ? 'examples' : 'practice'
}
function toggleTimer() {
  if (!work.value) return
  if (work.value.timer.runningSince === null) {
    if (!seconds.value) { notice.value = 'Time is up. Save your attempt or reset the timer for another practice round.'; return }
    work.value.timer.runningSince = Date.now()
  } else { work.value.timer.remaining = seconds.value; work.value.timer.runningSince = null }
}
async function saveAttempt() {
  if (!module.value || !exercise.value) return
  try { selectedAttemptId.value = submitAttempt(module.value, exercise.value.id).id; notice.value = 'Attempt saved. You can now compare the reference or request feedback.'; await nextTick(); submission.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }); submission.value?.focus({ preventScroll: true }) }
  catch (err) { notice.value = err instanceof Error ? err.message : 'Could not save attempt.' }
}
function reveal() {
  if (!attempt.value || !work.value) return
  solutionVisible.value = true
  // Preserve the already submitted unaided snapshot; future submissions use assisted status.
  work.value.assisted = true
}
function freshDraft() {
  if (!moduleProgress.value || !exercise.value) return
  if (confirm('Start a fresh draft? Submitted attempts stay in your history. The current draft will be replaced.')) {
    moduleProgress.value.drafts[exercise.value.id] = newDraft(exercise.value.minutes)
    solutionVisible.value = false; previewDiagram.value = false; selectedAttemptId.value = ''; notice.value = 'Fresh draft ready. Earlier submissions are preserved.'
  }
}
function finishQuiz() {
  if (!module.value) return
  try { quizResult.value = submitQuiz(module.value, choices.value) }
  catch (err) { notice.value = err instanceof Error ? err.message : 'Could not submit quiz.' }
}
function retryQuiz() {
  if (!moduleProgress.value) return
  moduleProgress.value.quizDraft = {}; quizResult.value = null; quizIndex.value = 0; notice.value = ''
}
function saveLabCard(question: string, answer: string) {
  if (!module.value) return
  addCard({ id: `${module.value.id}:decision:${crypto.randomUUID()}`, moduleId: module.value.id, kind: 'decision', question, answer, dueAt: Date.now() + DAY })
}
function saveDecision() {
  if (!module.value || !decisionQuestion.value.trim() || !decisionAnswer.value.trim()) return
  addCard({ id: `${module.value.id}:decision:${crypto.randomUUID()}`, moduleId: module.value.id, kind: 'decision', question: decisionQuestion.value,
    answer: decisionAnswer.value, dueAt: Date.now() + DAY })
  decisionQuestion.value = ''; decisionAnswer.value = ''; notice.value = 'Decision card saved. It returns tomorrow.'
}
</script>

<template>
  <div class="container hld-page">
    <router-link :to="`/system-design/hld?track=${module?.track ?? 'volume-1'}`">← HLD course map</router-link>
    <p v-if="loading" role="status">Loading module…</p>
    <div v-else-if="error" role="alert"><p>{{ error }}</p><button class="btn" @click="loadCourse">Retry</button></div>
    <div v-else-if="!module"><h1>Module not found</h1><router-link to="/system-design/hld">Choose a course module</router-link></div>
    <template v-else>
      <header class="hld-module-heading"><span class="hld-eyebrow">{{ module.track === 'volume-2' ? 'VOLUME 2' : 'VOLUME 1' }} / MODULE {{ String(module.number).padStart(2,'0') }} · {{ module.hours }} HOURS</span><h1>{{ module.title }}</h1><p>{{ module.outcome }}</p><details><summary>Book connection and prerequisites</summary><p>{{ module.book }}</p><p>Prerequisites: {{ module.prerequisites }}</p></details></header>
      <p v-if="storageError" class="hld-error" role="alert">{{ storageError }}</p>
      <HLDHowTo /><HLDEvidence :module="module" />
      <nav class="hld-tabs" aria-label="Module activities"><button v-for="t in tabs" :key="t" :class="{ selected: tab === t }" :aria-pressed="tab === t" @click="tab = t">{{ t === 'learn' ? 'Learn' : t === 'examples' ? 'Worked examples' : t === 'lab' ? 'Visual lab' : t === 'practice' ? 'Design & repair' : t === 'quiz' ? 'Quiz' : 'Spaced recall' }}</button></nav>

      <div v-if="tab === 'learn' && section" class="hld-learning-layout">
        <aside class="hld-lesson-nav"><p class="hld-eyebrow">One small idea at a time</p><label class="hld-mobile-step-selector">Choose a step<select v-model.number="sectionIndex" class="hld-input"><option v-for="(s, i) in module.sections" :key="s.id" :value="i">{{ i + 1 }}. {{ s.quick?.title ?? s.title }}</option></select></label><button v-for="(s, i) in module.sections" :key="s.id" :class="{ selected: sectionIndex === i }" @click="sectionIndex = i"><span>{{ moduleProgress?.completedSections.includes(s.id) ? '✓' : String(i + 1).padStart(2,'0') }}</span>{{ s.quick?.title ?? s.title }}</button></aside>
        <article class="hld-content-pane"><span class="hld-muted">Step {{ sectionIndex + 1 }} of {{ module.sections.length }}</span><h2>{{ section.quick?.title ?? section.title }}</h2>
          <template v-if="section.quick"><p class="hld-simple-explanation">{{ section.quick.explanation }}</p><div class="hld-example"><strong>A small example</strong><p>{{ section.quick.example }}</p></div><p class="hld-memory-tip"><strong>Remember:</strong> {{ section.quick.tip }}</p><details><summary>Go deeper · optional technical explanation</summary><HLDMarkdown :content="section.content" /></details></template>
          <HLDMarkdown v-else :content="section.content" />
          <template v-if="sectionIndex === 0"><HLDDiagram v-for="v in module.visuals.filter(v => v.placement === 'overview')" :key="v.id" :title="v.title" :caption="v.caption" :code="v.code" /></template>
          <template v-if="sectionIndex === module.sections.length - 1"><HLDDiagram v-for="v in module.visuals.filter(v => v.placement === 'recap')" :key="v.id" :title="v.title" :caption="v.caption" :code="v.code" /></template>
          <label class="hld-label" for="hld-notes">Your explanation or questions</label><textarea v-if="moduleProgress" id="hld-notes" v-model="moduleProgress.notes" class="hld-input" rows="3" placeholder="What constraint does this mechanism solve? When would you choose an alternative?"></textarea>
          <div class="hld-row"><button class="btn" :disabled="sectionIndex === 0" @click="sectionIndex--">Previous</button><button class="btn btn-primary" @click="nextLesson">{{ sectionIndex === module.sections.length - 1 ? 'Finish lesson · try it' : 'Mark explored · next step' }}</button></div>
        </article>
      </div>

      <section v-else-if="tab === 'examples'">
        <div class="hld-row"><button v-for="(e, i) in module.examples" :key="e.id" class="btn" :aria-pressed="exampleIndex === i" @click="exampleIndex = i">{{ e.title.split('—')[0] }}</button></div>
        <p class="hld-muted">Teaching examples are intentionally solved. Predict the next decision and explain why before moving on.</p>
        <HLDWorkedExample v-if="module.examples[exampleIndex]" :example="module.examples[exampleIndex]!" :visuals="module.visuals" />
        <button class="btn btn-primary" @click="tab = 'practice'">Try a changed problem</button>
      </section>

      <HLDMechanismLab v-else-if="tab === 'lab'" :initial="module.lab" @remember="saveLabCard" />
      <section v-else-if="tab === 'practice' && exercise && work">
        <div class="hld-row"><label class="hld-label">Choose an exercise<select v-model="exerciseId" class="hld-input"><option v-for="e in module.exercises" :key="e.id" :value="e.id">{{ e.kind === 'repair' ? 'Repair' : e.kind === 'transfer' ? 'Transfer' : 'Design' }} · {{ e.title }}</option></select></label>
          <div class="hld-timer"><strong>{{ timerText }}</strong><button class="btn" @click="toggleTimer">{{ work.timer.runningSince === null ? 'Start timer' : 'Pause' }}</button><button class="btn btn-ghost" @click="work.timer = { remaining: exercise.minutes * 60, runningSince: null }">Reset timer</button></div></div>
        <p v-if="exercise.kind === 'repair'" class="hld-muted">For a repair, name the broken rule in Contract. Focus on Flow and Stress. Add recovery and a test under Operate. Other phases are optional when they do not affect the repair.</p>
        <div class="hld-practice-layout"><article class="hld-prompt"><span class="hld-eyebrow">{{ exercise.kind }} · {{ exercise.minutes }} min</span><h2>{{ exercise.title }}</h2><HLDMarkdown :content="exercise.prompt" /></article>
          <div class="hld-workspace"><div class="hld-row"><h2>Your design</h2><span class="hld-status">{{ work.assisted ? 'Assisted draft' : 'Unaided draft' }}</span></div>
            <nav class="hld-phase-tabs" aria-label="Design structure"><button v-for="p in HLD_PHASES" :key="p.id" :aria-pressed="activePhase === p.id" :class="{ selected: activePhase === p.id }" @click="activePhase = p.id">{{ p.title }}{{ work.phases[p.id].trim() ? ' ✓' : '' }}</button></nav>
            <label class="hld-label" :for="`phase-${activePhase}`">{{ phase.title }} <span class="hld-muted">{{ phaseTime }}</span></label><p class="hld-muted">{{ phase.prompt }}</p>
            <textarea :id="`phase-${activePhase}`" v-model="work.phases[activePhase]" class="hld-input hld-design-input" rows="10" maxlength="3400" :placeholder="phase.prompt"></textarea>
            <details><summary>Architecture diagram · Mermaid or text</summary><textarea v-model="work.diagram" class="hld-input hld-code-input" rows="6" maxlength="8000" placeholder="flowchart LR&#10;  Client --> API&#10;  API --> Database"></textarea><button class="btn" :disabled="!work.diagram.trim()" @click="previewDiagram = !previewDiagram">{{ previewDiagram ? 'Hide preview' : 'Preview diagram' }}</button><HLDMarkdown v-if="previewDiagram" :content="`\`\`\`mermaid\n${work.diagram}\n\`\`\``" /></details>
            <label class="hld-label"><input v-model="work.assisted" type="checkbox" /> I used hints or looked at a reference during this attempt</label>
            <div class="hld-row"><button class="btn btn-primary" @click="saveAttempt">Save & submit attempt</button><button class="btn" @click="freshDraft">Fresh draft</button></div><p class="hld-muted">Draft autosaves here. Submission preserves a snapshot. Then choose AI feedback or reveal the reference below.</p>
          </div></div>
        <p v-if="notice" role="status">{{ notice }}</p>
        <section v-if="attempt" ref="submission" class="hld-submission" tabindex="-1"><div class="hld-row"><h2>Saved attempts & feedback</h2><label class="hld-label">Attempt<select v-model="selectedAttemptId" class="hld-input"><option value="">Latest submission</option><option v-for="a in attempts" :key="a.id" :value="a.id">{{ new Date(a.createdAt).toLocaleString() }} · {{ a.assisted ? 'Assisted' : 'Unaided' }}</option></select></label></div>
          <details><summary>View this submitted snapshot</summary><div v-for="p in HLD_PHASES" :key="p.id"><h3>{{ p.title }}</h3><HLDMarkdown :content="attempt.phases[p.id] || 'Not recorded in this attempt.'" /></div><pre v-if="attempt.diagram">{{ attempt.diagram }}</pre></details>
          <HLDAssessment :key="attempt.id" :module="module" :attempt="attempt" />
          <button v-if="!solutionVisible" class="btn" @click="reveal">Reveal reference after submission</button><div v-else class="hld-feedback"><h3>A reference solution, explained</h3><HLDMarkdown :content="exercise.solution" /><p class="hld-muted">Compare assumptions and consequences. This current draft is now assisted. Later, close the reference and try a fresh draft from memory; mark any help you use.</p></div>
        </section><p v-else class="hld-muted">Reference solutions and rubric review unlock after your first submitted attempt.</p>
      </section>

      <section v-else-if="tab === 'quiz'">
        <div class="hld-row"><h2>Choose, then explain the mechanism</h2><span class="hld-muted">{{ answered }}/{{ module.questions.length }} answered</span></div>
        <p class="hld-muted">Answers and explanations appear after you submit the complete quiz. Scores measure these questions, not architecture mastery.</p>
        <div class="hld-row"><button v-for="(q, index) in module.questions" :key="q.id" class="btn" :aria-pressed="quizIndex === index" @click="quizIndex = index">{{ index + 1 }}{{ choices[q.id] !== undefined ? ' ✓' : '' }}</button><span class="hld-muted">Question {{ quizIndex + 1 }} of {{ module.questions.length }}</span></div>
        <article v-for="q in module.questions.filter((_, index) => index === quizIndex)" :key="q.id" class="hld-question"><h3>{{ quizIndex + 1 }}. {{ q.prompt }}</h3><label v-for="(option, index) in q.options" :key="index" class="hld-option" :class="{ chosen: choices[q.id] === index }"><input v-model="choices[q.id]" type="radio" :name="q.id" :value="index" :disabled="!!quizResult" /><span>{{ String.fromCharCode(65 + index) }}.</span>{{ option }}</label>
          <div v-if="quizResult" class="hld-feedback"><strong>{{ quizResult.choices[q.id] === q.correctIndex ? 'Correct' : 'Revisit this mechanism' }}</strong><p>{{ q.options[q.correctIndex] }}</p><p>{{ q.explanation }}</p></div>
        </article>
        <div class="hld-row"><button class="btn" :disabled="quizIndex === 0" @click="quizIndex--">Previous question</button><button class="btn" :disabled="quizIndex === module.questions.length - 1" @click="quizIndex++">Next question</button></div>
        <button v-if="!quizResult" class="btn btn-primary" :disabled="answered !== module.questions.length" @click="finishQuiz">Submit quiz</button><div v-else class="hld-row"><strong>{{ quizResult.score }}/{{ quizResult.total }} correct</strong><button class="btn" @click="retryQuiz">New quiz attempt</button><button class="btn btn-primary" @click="tab = 'recall'">Review missed concepts</button></div>
        <details v-if="moduleProgress?.quizAttempts.length"><summary>Quiz history · {{ moduleProgress.quizAttempts.length }} attempts</summary><p v-for="q in moduleProgress.quizAttempts" :key="q.createdAt">{{ new Date(q.createdAt).toLocaleString() }} · {{ q.score }}/{{ q.total }}</p></details>
      </section>

      <section v-else-if="tab === 'recall'"><HLDReviewQueue :module-id="module.id" /><details><summary>Add your own decision card</summary><label class="hld-label">Decision question<input v-model="decisionQuestion" class="hld-input" placeholder="When would I choose a different consistency model?" /></label><label class="hld-label">Your reference reasoning<textarea v-model="decisionAnswer" class="hld-input" rows="4" placeholder="Constraint → choice → alternative → cost → failure → condition that changes the choice"></textarea></label><button class="btn" :disabled="!decisionQuestion.trim() || !decisionAnswer.trim()" @click="saveDecision">Schedule for tomorrow</button><p role="status">{{ notice }}</p></details></section>
      <div class="hld-row hld-activity-next"><button v-if="tab === 'practice' && attempt" class="btn btn-primary" @click="tab = 'quiz'">Next: check the key decisions →</button><button v-if="tab === 'learn' && sectionIndex === module.sections.length - 1 && module.lab" class="btn" @click="tab = 'lab'">Try the visual lab →</button></div>
      <footer class="hld-row hld-course-footer"><router-link :to="`/system-design/hld?track=${module.track}`">Course map</router-link><router-link v-if="nextModule" class="btn" :to="`/hld/${nextModule.id}`">Next module →</router-link></footer>
      <AIChatPanel v-if="['learn', 'examples', 'practice'].includes(tab)" :key="`${module.id}-${chatContext.mode}-${chatContext.exercise_id ?? 'lesson'}`" context-type="hld" :context-id="module.id" :context-label="module.title" :hld-context="chatContext" :quick-chips="coachChips" @message="work && tab === 'practice' && (work.assisted = true)" />
    </template>
  </div>
</template>
