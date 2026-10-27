import { computed, reactive, ref, watch } from 'vue'
import type { HLDCourse, HLDModule, HLDModuleProgress, HLDDraft, HLDAttempt, HLDReview, HLDCard, HLDProgress } from '../types/hld'
import { assessmentPass, DAY, emptyProgress, gradeQuiz, newDraft, remainingSeconds, scheduleReview, validateProgress } from '../lib/hldLearning'

const KEY = 'hld-architecture-progress-v1'
const storageError = ref('')
let blockedStorage = false
function load(): HLDProgress {
  try { const raw = localStorage.getItem(KEY); return raw ? validateProgress(JSON.parse(raw)) : emptyProgress() }
  catch { blockedStorage = true; storageError.value = 'Saved HLD data could not be read. Export it for recovery, then restore a valid backup to enable saving.'; return emptyProgress() }
}
const state = reactive<HLDProgress>(load())
const course = ref<HLDCourse | null>(null)
const loading = ref(false)
const error = ref('')
const now = ref(Date.now())
let pending: ReturnType<typeof setTimeout> | undefined
let request: Promise<void> | null = null
function persist() {
  clearTimeout(pending)
  if (blockedStorage) return
  try { localStorage.setItem(KEY, JSON.stringify(state)); storageError.value = '' }
  catch { storageError.value = 'Browser storage is full or unavailable. Export your HLD progress now to keep a backup.' }
}
watch(state, () => { clearTimeout(pending); pending = setTimeout(persist, 200) }, { deep: true })
if (typeof window !== 'undefined') {
  window.setInterval(() => { now.value = Date.now() }, 1000)
  window.addEventListener('pagehide', persist)
}
async function loadCourse() {
  if (course.value) return
  if (request) return request
  loading.value = true; error.value = ''
  request = (async () => {
    try {
      const res = await fetch(`${import.meta.env.BASE_URL}hld-course.json`)
      if (!res.ok) throw new Error('The HLD course could not be loaded.')
      const data = await res.json()
      if (data.schemaVersion !== 1 || !Array.isArray(data.modules) || data.modules.length < 1 || new Set(data.modules.map((m: HLDModule) => m.id)).size !== data.modules.length) throw new Error('Invalid HLD course catalog.')
      course.value = data
    } catch (err) { error.value = err instanceof Error ? err.message : 'Could not load course.' }
    finally { loading.value = false; request = null }
  })()
  return request
}
function progress(moduleId: string): HLDModuleProgress {
  return state.modules[moduleId] ??= { completedSections: [], notes: '', drafts: {}, attempts: [], quizAttempts: [] }
}
function draft(moduleId: string, exerciseId: string, minutes: number): HLDDraft {
  return progress(moduleId).drafts[exerciseId] ??= newDraft(minutes)
}
function addCard(card: Omit<HLDCard, 'step' | 'lapses' | 'lastReviewed' | 'lastResponse'>) {
  if (!state.cards[card.id]) state.cards[card.id] = { ...card, step: 0, lapses: 0, lastReviewed: null, lastResponse: '' }
}
function completeSection(module: HLDModule, sectionId: string) {
  const p = progress(module.id)
  if (!p.completedSections.includes(sectionId)) p.completedSections.push(sectionId)
  if (module.sections.every(s => p.completedSections.includes(s.id))) {
    addCard({ id: `${module.id}:recall`, moduleId: module.id, kind: 'recall', question: module.recallPrompt,
      answer: module.sections.map(s => `### ${s.quick?.title ?? s.title}\n${s.quick?.explanation ?? s.content}\n\n${s.quick?.tip ?? ''}`).join('\n\n'), dueAt: now.value + DAY })
  }
}
function submitAttempt(module: HLDModule, exerciseId: string): HLDAttempt {
  const exercise = module.exercises.find(e => e.id === exerciseId)!
  const d = draft(module.id, exerciseId, exercise.minutes)
  if (![...Object.values(d.phases), d.diagram].some(text => text.trim())) throw new Error('Write your design before saving an attempt.')
  const attempt: HLDAttempt = { id: crypto.randomUUID(), exerciseId, createdAt: Date.now(), phases: { ...d.phases }, diagram: d.diagram, assisted: d.assisted }
  progress(module.id).attempts.push(attempt)
  d.timer.remaining = remainingSeconds(d, Date.now()); d.timer.runningSince = null
  addCard({ id: `${module.id}:${exerciseId}`, moduleId: module.id, kind: 'recall', question: `Redesign ${exercise.title} without notes. ${module.recallPrompt}`,
    answer: exercise.solution, dueAt: now.value + DAY })
  persist()
  return attempt
}
function saveReview(moduleId: string, attemptId: string, review: HLDReview) {
  const attempt = progress(moduleId).attempts.find(a => a.id === attemptId)
  if (!attempt) throw new Error('The saved attempt could not be found.')
  review.total = review.dimensions.reduce((n, d) => n + d.score, 0)
  review.passed = assessmentPass(review, attempt.assisted)
  attempt.review = review
  persist()
}
function submitQuiz(module: HLDModule, choices: Record<string, number>) {
  const score = gradeQuiz(module.questions, choices)
  const result = { choices: { ...choices }, score, total: module.questions.length, createdAt: Date.now() }
  progress(module.id).quizAttempts.push(result)
  for (const q of module.questions) {
    const id = `${module.id}:${q.id}`
    addCard({ id, moduleId: module.id, kind: 'quiz', question: q.prompt,
      answer: `${q.options[q.correctIndex]}\n\n${q.explanation}`, dueAt: now.value + (choices[q.id] === q.correctIndex ? DAY : 0) })
    if (choices[q.id] !== q.correctIndex) { state.cards[id]!.dueAt = now.value; state.cards[id]!.step = 0 }
  }
  persist()
  return result
}
function reviewCard(id: string, rating: 'again' | 'hard' | 'good', response: string) {
  if (!response.trim()) throw new Error('Write a recall attempt before rating it.')
  const card = state.cards[id]
  if (!card) throw new Error('Review card not found.')
  state.cards[id] = { ...scheduleReview(card, rating, Date.now()), lastResponse: response }
  persist()
}
function importProgress(raw: string) {
  const validated = validateProgress(JSON.parse(raw))
  // Validate first: a failed import never changes existing progress.
  state.modules = validated.modules; state.cards = validated.cards; blockedStorage = false
  persist()
}
export function useHLD() {
  void loadCourse()
  const dueCards = computed(() => Object.values(state.cards).filter(c => c.dueAt <= now.value).sort((a, b) => a.dueAt - b.dueAt))
  const nextDue = computed(() => Object.values(state.cards).filter(c => c.dueAt > now.value).sort((a, b) => a.dueAt - b.dueAt)[0]?.dueAt)
  return { course, loading, error, state, storageError, now, progress, draft, completeSection, submitAttempt, saveReview, submitQuiz, reviewCard,
    dueCards, nextDue, loadCourse, addCard, importProgress, exportProgress: () => blockedStorage ? localStorage.getItem(KEY) ?? JSON.stringify(state) : JSON.stringify(state, null, 2) }
}
