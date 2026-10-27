import { HLD_DIMENSIONS, HLD_PHASES, type HLDCard, type HLDDraft, type HLDProgress, type HLDReview, type HLDQuestion, type HLDModule, type HLDModuleProgress } from '../types/hld'

export const DAY = 86_400_000
export const REVIEW_INTERVALS = [1, 3, 7, 14, 30, 60]
export function emptyProgress(): HLDProgress { return { schemaVersion: 1, modules: {}, cards: {} } }
export function newDraft(minutes = 45): HLDDraft {
  return { phases: Object.fromEntries(HLD_PHASES.map(p => [p.id, ''])) as HLDDraft['phases'], diagram: '', assisted: false,
    timer: { remaining: minutes * 60, runningSince: null } }
}
export function remainingSeconds(draft: HLDDraft, now: number): number {
  return Math.max(0, draft.timer.remaining - (draft.timer.runningSince === null ? 0 : Math.floor((now - draft.timer.runningSince) / 1000)))
}
export function gradeQuiz(questions: HLDQuestion[], choices: Record<string, number>): number {
  if (questions.some(q => !Number.isInteger(choices[q.id]) || choices[q.id]! < 0 || choices[q.id]! >= q.options.length)) {
    throw new Error('Answer every question before submitting.')
  }
  return questions.filter(q => choices[q.id] === q.correctIndex).length
}
export function assessmentPass(review: Pick<HLDReview, 'dimensions' | 'critical_issue' | 'scope'>, assisted: boolean): boolean {
  const dims = review.dimensions
  return review.scope !== 'repair' && !assisted && !review.critical_issue && dims.length === HLD_DIMENSIONS.length &&
    HLD_DIMENSIONS.every(id => dims.some(d => d.id === id && Number.isInteger(d.score) && d.score >= 2 && d.score <= 3 && d.evidence.trim())) &&
    dims.reduce((sum, d) => sum + d.score, 0) >= 18
}
export function scheduleReview(card: HLDCard, rating: 'again' | 'hard' | 'good', now: number): HLDCard {
  const step = rating === 'again' ? 0 : rating === 'good' ? Math.min(card.step + 1, REVIEW_INTERVALS.length - 1) : card.step
  const delay = rating === 'again' ? 10 * 60_000 : rating === 'hard' ? DAY : REVIEW_INTERVALS[step]! * DAY
  return { ...card, step, lastRating: rating, dueAt: now + delay, lastReviewed: now, lapses: card.lapses + (rating === 'again' ? 1 : 0) }
}

// Backups are user-controlled input. Validate the complete state before any mutation.
export function validateProgress(value: unknown): HLDProgress {
  const data = value as HLDProgress
  if (!data || data.schemaVersion !== 1 || !data.modules || typeof data.modules !== 'object' || Array.isArray(data.modules) ||
      !data.cards || typeof data.cards !== 'object' || Array.isArray(data.cards)) throw new Error('Invalid HLD backup format.')
  const timestamp = (v: unknown) => typeof v === 'number' && Number.isFinite(v) && v >= 0
  const text = (v: unknown) => typeof v === 'string'
  const phases = (v: unknown) => v && HLD_PHASES.every(p => text((v as HLDDraft['phases'])[p.id]))
  for (const [id, m] of Object.entries(data.modules)) {
    if (!/^[\w-]+$/.test(id) || ['__proto__','constructor','prototype'].includes(id) || !m || !Array.isArray(m.completedSections) || !m.completedSections.every(text) || !text(m.notes) ||
        !m.drafts || typeof m.drafts !== 'object' || Array.isArray(m.drafts) || !Array.isArray(m.attempts) || !Array.isArray(m.quizAttempts)) throw new Error('Invalid module progress.')
    for (const d of Object.values(m.drafts)) {
      if (!d || !phases(d.phases) || !text(d.diagram) || typeof d.assisted !== 'boolean' || !d.timer ||
          !timestamp(d.timer.remaining) || !(d.timer.runningSince === null || timestamp(d.timer.runningSince))) throw new Error('Invalid practice draft.')
    }
    for (const a of m.attempts) {
      if (!a || !text(a.id) || !text(a.exerciseId) || !timestamp(a.createdAt) || !phases(a.phases) || !text(a.diagram) || typeof a.assisted !== 'boolean') throw new Error('Invalid attempt.')
      if (a.review && (!Array.isArray(a.review.dimensions) || a.review.dimensions.length !== (a.review.scope === 'repair' ? 4 : 8) ||
          new Set(a.review.dimensions.map(d => d.id)).size !== (a.review.scope === 'repair' ? 4 : 8) ||
          (a.review.scope !== undefined && !['design','repair'].includes(a.review.scope)) ||
          (a.review.scope === 'repair' && a.review.dimensions.some(d => !['requirements','flows','correctness','failure_operations'].includes(d.id))) || a.review.dimensions.some(d => !HLD_DIMENSIONS.includes(d.id) || !Number.isInteger(d.score) || d.score < 0 || d.score > 3 || !text(d.evidence) || !text(d.feedback)) ||
          !['ai', 'self'].includes(a.review.source) || !text(a.review.summary) || !Array.isArray(a.review.gaps) || !a.review.gaps.every(text) ||
          !Array.isArray(a.review.strengths) || !a.review.strengths.every(text) || !text(a.review.next_exercise) || typeof a.review.critical_issue !== 'boolean')) throw new Error('Invalid assessment.')
      if (a.review) { a.review.total = a.review.dimensions.reduce((n, d) => n + d.score, 0); a.review.passed = assessmentPass(a.review, a.assisted) }
    }
    for (const q of m.quizAttempts) {
      if (!q || !timestamp(q.createdAt) || !q.choices || typeof q.choices !== 'object' || Array.isArray(q.choices) ||
          Object.values(q.choices).some(v => !Number.isInteger(v) || v < 0 || v > 3) || !Number.isInteger(q.score) || !Number.isInteger(q.total) || q.score < 0 || q.score > q.total || q.total < 1) throw new Error('Invalid quiz history.')
    }
    if (m.quizDraft && (typeof m.quizDraft !== 'object' || Array.isArray(m.quizDraft) || Object.values(m.quizDraft).some(v => !Number.isInteger(v) || v < 0 || v > 3))) throw new Error('Invalid quiz draft.')
  }
  for (const [id, c] of Object.entries(data.cards)) {
    if (!c || c.id !== id || !/^[\w-]+$/.test(c.moduleId) || !['recall', 'quiz', 'decision'].includes(c.kind) ||
        !text(c.question) || !text(c.answer) || !timestamp(c.dueAt) || !Number.isInteger(c.step) || c.step < 0 || c.step >= REVIEW_INTERVALS.length ||
        !Number.isInteger(c.lapses) || c.lapses < 0 || !(c.lastReviewed === null || timestamp(c.lastReviewed)) || !text(c.lastResponse) || (c.lastRating !== undefined && !['again','hard','good'].includes(c.lastRating))) throw new Error('Invalid review card.')
  }
  return data
}

// Separate exposure from evidence of independent reasoning. Old progress remains valid.
export function moduleEvidence(module: HLDModule, progress: HLDModuleProgress | undefined, cards: HLDCard[]) {
  const attempts = progress?.attempts ?? []
  const tried = (kind: string) => { const required = module.exercises.filter(e => e.kind === kind); return required.length > 0 && required.every(e => attempts.some(a => a.exerciseId === e.id)) }
  const first = attempts.length ? Math.min(...attempts.map(a => a.createdAt)) : Infinity
  const quiz = progress?.quizAttempts[progress.quizAttempts.length - 1]
  const fullDesigns = module.exercises.filter(e => e.kind === 'design')
  const reviewed = (id: string) => attempts.some(a => a.exerciseId === id && a.review && assessmentPass(a.review, a.assisted))
  const independent = fullDesigns.length > 1 ? fullDesigns.every(e => reviewed(e.id)) : attempts.some(a => a.review && assessmentPass(a.review, a.assisted) && module.exercises.some(e => e.id === a.exerciseId && e.kind !== 'repair'))
  const checks = {
    lesson: module.sections.every(s => progress?.completedSections.includes(s.id)),
    design: tried('design'), transfer: tried('transfer'), repair: tried('repair'),
    quiz: !!quiz && quiz.score / quiz.total >= .75,
    independent,
    delayed: cards.some(c => c.moduleId === module.id && c.kind !== 'quiz' && c.lastRating === 'good' && c.lastReviewed !== null && c.lastReviewed - first >= 7 * DAY),
  }
  return { ...checks, count: Object.values(checks).filter(Boolean).length, total: Object.keys(checks).length, complete: Object.values(checks).every(Boolean) }
}
