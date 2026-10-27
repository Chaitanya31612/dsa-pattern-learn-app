import { computed, ref, watch } from 'vue'
import type { SoftwareCourse, SoftwareModule, SoftwareProgress, SoftwareAttempt } from '../types/software'
import { newSoftwareDraft, validateSoftwareProgress } from '../lib/softwareLearning'
import { DAY, gradeQuiz, scheduleReview } from '../lib/hldLearning'

export type LearningArea = 'software' | 'ai'
export function createLearningSpace(area: LearningArea) {
const label = area==='ai'?'AI Learnings':'Software Learnings'
const KEY = `${area==='ai'?'ai':'software'}-learnings-progress-v1`
const course = ref<SoftwareCourse | null>(null)
const error = ref('')
const storageError = ref('')
const blocked = ref(false)
const progress = ref<SoftwareProgress>({ schemaVersion: 1, modules: {}, cards: {} })
let pending: Promise<void> | null = null
try {
  const raw = localStorage.getItem(KEY)
  if (raw) progress.value = validateSoftwareProgress(JSON.parse(raw))
} catch { blocked.value = true; storageError.value = `Saved ${label} progress could not be read. It has not been overwritten. Export the stored copy in Settings before replacing it.` }
watch(progress, data => {
  if (blocked.value) return
  try { localStorage.setItem(KEY, JSON.stringify(data)); storageError.value = '' }
  catch { storageError.value = 'Browser storage failed. Export your progress before closing this tab.' }
}, { deep: true, flush: 'sync' })

async function load() {
  if (course.value || pending) return pending
  pending = (async () => {
    try {
      const response = await fetch(`${import.meta.env.BASE_URL}${area}-course.json`)
      if (!response.ok) throw new Error('load')
      const data = await response.json()
      if (data.schemaVersion !== 1 || !Array.isArray(data.modules) || !data.modules.length) throw new Error('schema')
      course.value = data; error.value = ''
    } catch { error.value = `The ${label} course could not load. Check the server and retry.` }
    finally { pending = null }
  })()
  return pending
}
function state(id: string) {
  if (!progress.value.modules[id]) progress.value.modules[id] = { completed: [], drafts: {}, attempts: [], quizDraft: {}, quizzes: [], quizSubmitted: false, notes: '' }
  return progress.value.modules[id]!
}
function draft(id: string, exercise: string) {
  const m = state(id)
  if (!m.drafts[exercise]) m.drafts[exercise] = newSoftwareDraft()
  return m.drafts[exercise]!
}
function card(module: SoftwareModule, id: string, question: string, answer: string, kind: 'recall' | 'quiz') {
  const key = `${module.id}-${id}`
  if (!progress.value.cards[key]) progress.value.cards[key] = { id: key, moduleId: module.id, kind, question, answer, dueAt: Date.now() + DAY, step: 0, lapses: 0, lastReviewed: null, lastResponse: '' }
}
function completeStep(module: SoftwareModule, section: string) {
  const m = state(module.id)
  if (!m.completed.includes(section)) m.completed.push(section)
  card(module, 'recall', module.recallPrompt, module.cue + '\n\n' + module.sections.find(s => s.id === 'trace')!.content, 'recall')
}
function submit(module: SoftwareModule, exerciseId: string): SoftwareAttempt {
  const value = draft(module.id, exerciseId)
  if (!Object.values(value.phases).some(v => v.trim())) throw new Error('Write an attempt before submitting.')
  const snapshot = JSON.parse(JSON.stringify(value))
  const attempt = { ...snapshot, id: crypto.randomUUID(), exerciseId, createdAt: Date.now() }
  state(module.id).attempts.push(attempt)
  card(module, 'recall', module.recallPrompt, module.cue + '\n\n' + module.sections.find(s => s.id === 'trace')!.content, 'recall')
  return state(module.id).attempts[state(module.id).attempts.length - 1]!
}
function submitQuiz(module: SoftwareModule) {
  const m = state(module.id)
  const score = gradeQuiz(module.questions, m.quizDraft)
  m.quizzes.push({ createdAt: Date.now(), choices: { ...m.quizDraft }, score, total: module.questions.length })
  m.quizSubmitted = true
  for (const q of module.questions) if (m.quizDraft[q.id] !== q.correctIndex) card(module, q.id, q.prompt, q.options[q.correctIndex] + '\n\n' + q.explanation, 'quiz')
}
const now = ref(Date.now())
function refreshTime() { now.value = Date.now() }
if (typeof window !== 'undefined') {
  window.addEventListener('focus', refreshTime)
  window.setInterval(refreshTime, 30_000)
}
const due = computed(() => Object.values(progress.value.cards).filter(c => c.dueAt <= now.value).sort((a,b) => a.dueAt - b.dueAt))
function rate(id: string, rating: 'again' | 'hard' | 'good') {
  const c = progress.value.cards[id]
  if (c) progress.value.cards[id] = scheduleReview(c, rating, Date.now())
  refreshTime()
}
function replaceBackup(value: unknown) {
  const valid = validateSoftwareProgress(value)
  // Store successfully before replacing in-memory data or unblocking writes.
  localStorage.setItem(KEY, JSON.stringify(valid))
  blocked.value = false; progress.value = valid; storageError.value = ''
}
function useSpace() {
  void load()
  return { course, error, progress, storageError, blocked, due, load, state, draft, completeStep, submit, submitQuiz, rate, refreshTime, replaceBackup,
    rawBackup: () => localStorage.getItem(KEY), newDraft: newSoftwareDraft }
}

return useSpace
}
const softwareSpace = createLearningSpace('software')
const aiSpace = createLearningSpace('ai')
export const useSoftware = softwareSpace
export const useAILearnings = aiSpace
