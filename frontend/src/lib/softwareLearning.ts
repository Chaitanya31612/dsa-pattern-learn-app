import { WORK_FIELDS, type SoftwareDraft, type SoftwareModule, type SoftwareProgress, type SoftwareModuleProgress, type SoftwareReport } from '../types/software'
import { DAY } from './hldLearning'
import type { HLDCard } from '../types/hld'

export function newSoftwareDraft(): SoftwareDraft {
  return { phases: { predict: '', change: '', verify: '', explain: '' }, diagram: '', assisted: false }
}
export function softwareEvidence(module: SoftwareModule, progress?: SoftwareModuleProgress, cards: HLDCard[] = []) {
  const first = progress?.attempts.length ? Math.min(...progress.attempts.map(a => a.createdAt)) : Infinity
  const quiz = progress?.quizzes[progress.quizzes.length - 1]
  const checks = {
    lesson: module.sections.every(s => progress?.completed.includes(s.id)),
    practice: module.exercises.every(e => progress?.attempts.some(a => a.exerciseId === e.id)),
    quiz: !!quiz && quiz.score / quiz.total >= .75,
    delayed: cards.some(c => c.moduleId === module.id && c.kind === 'recall' && c.lastRating === 'good' && c.lastReviewed !== null && c.lastReviewed - first >= 7 * DAY),
  }
  return { ...checks, count: Object.values(checks).filter(Boolean).length, complete: Object.values(checks).every(Boolean) }
}
export function validateSoftwareReport(value: unknown): SoftwareReport {
  const r = value as SoftwareReport
  if (!r || !['ai','self'].includes(r.source) || typeof r.summary !== 'string' || !r.summary.trim() || typeof r.next_exercise !== 'string' || !r.next_exercise.trim() ||
    !Array.isArray(r.dimensions) || r.dimensions.length !== 4 || new Set(r.dimensions.map(d => d.id)).size !== 4 ||
    r.dimensions.some(d => !WORK_FIELDS.some(f => f.id === d.id) || !Number.isInteger(d.score) || d.score < 0 || d.score > 3 || typeof d.evidence !== 'string' || !d.evidence.trim() || typeof d.feedback !== 'string' || !d.feedback.trim())) throw new Error('Invalid feedback. No score was saved.')
  return r
}
export function validateSoftwareProgress(value: unknown): SoftwareProgress {
  const p = value as SoftwareProgress
  const obj = (v: unknown) => !!v && typeof v === 'object' && !Array.isArray(v)
  const safe = (key: string) => /^[\w-]+$/.test(key) && !['__proto__','prototype','constructor'].includes(key)
  const text = (v: unknown) => typeof v === 'string'
  const time = (v: unknown) => typeof v === 'number' && Number.isFinite(v) && v >= 0
  const choices = (v: unknown) => obj(v) && Object.entries(v as object).every(([k, n]) => safe(k) && Number.isInteger(n) && n >= 0 && n < 5)
  const draft = (d: SoftwareDraft) => obj(d) && obj(d.phases) && WORK_FIELDS.every(f => text(d.phases[f.id])) && Object.keys(d.phases).length === 4 && text(d.diagram) && typeof d.assisted === 'boolean'
  if (!p || p.schemaVersion !== 1 || !obj(p.modules) || !obj(p.cards)) throw new Error('Invalid Software Learnings backup.')
  for (const [id, m] of Object.entries(p.modules)) {
    if (!safe(id) || !obj(m) || !Array.isArray(m.completed) || !m.completed.every(text) || !obj(m.drafts) || !Array.isArray(m.attempts) || !Array.isArray(m.quizzes) || !choices(m.quizDraft) || typeof m.quizSubmitted !== 'boolean' || !text(m.notes)) throw new Error('Invalid module progress.')
    if (Object.entries(m.drafts).some(([key, d]) => !safe(key) || !draft(d))) throw new Error('Invalid practice draft.')
    for (const a of m.attempts) {
      if (!draft(a) || !text(a.id) || !safe(a.exerciseId) || !time(a.createdAt)) throw new Error('Invalid saved attempt.')
      if (a.report) validateSoftwareReport(a.report)
    }
    for (const q of m.quizzes) if (!time(q.createdAt) || !choices(q.choices) || !Number.isInteger(q.score) || !Number.isInteger(q.total) || q.total < 1 || q.score < 0 || q.score > q.total) throw new Error('Invalid quiz result.')
  }
  for (const [key, c] of Object.entries(p.cards)) {
    if (!safe(key) || !c || c.id !== key || !safe(c.moduleId) || !['recall','quiz','decision'].includes(c.kind) || !text(c.question) || !text(c.answer) || !time(c.dueAt) || !Number.isInteger(c.step) || c.step < 0 || c.step > 5 || !Number.isInteger(c.lapses) || c.lapses < 0 || !(c.lastReviewed === null || time(c.lastReviewed)) || !text(c.lastResponse) || (c.lastRating !== undefined && !['again','hard','good'].includes(c.lastRating))) throw new Error('Invalid recall card.')
  }
  return p
}
