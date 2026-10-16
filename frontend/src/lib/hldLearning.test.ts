import { describe, expect, it } from 'vitest'
import { assessmentPass, DAY, emptyProgress, gradeQuiz, newDraft, remainingSeconds, moduleEvidence, scheduleReview, validateProgress } from './hldLearning'
import { HLD_DIMENSIONS, type HLDCard, type HLDReview } from '../types/hld'

const card: HLDCard = { id: 'test:q1', moduleId: '00-design-framework', kind: 'quiz', question: 'Why?', answer: 'Because…', dueAt: 0, step: 0, lapses: 0, lastReviewed: null, lastResponse: '' }
const review: HLDReview = { source: 'ai', dimensions: HLD_DIMENSIONS.map((id, i) => ({ id, score: i < 2 ? 3 : 2, evidence: 'Specific design evidence', feedback: 'Reasoning' })),
  summary: 'Review', strengths: [], gaps: [], next_exercise: 'Try a changed constraint', critical_issue: false, total: 24, passed: true }

describe('HLD evidence and spaced practice', () => {
  it('uses elapsed wall-clock time so a timer survives reload and never goes negative', () => {
    const d = newDraft(45); d.timer.runningSince = 1000
    expect(remainingSeconds(d, 31_000)).toBe(2670)
    expect(remainingSeconds(d, 4_000_000)).toBe(0)
    d.timer.remaining = 2670; d.timer.runningSince = null
    expect(remainingSeconds(d, 4_000_000)).toBe(2670)
  })
  it('requires every MCQ to be answered and calculates the score from the key', () => {
    const qs = [{ id: 'q1', prompt: 'Pick', options: ['a','b','c','d'], correctIndex: 2, explanation: 'Why' }]
    expect(() => gradeQuiz(qs, {})).toThrow()
    expect(() => gradeQuiz(qs, { q1: 5 })).toThrow()
    expect(gradeQuiz(qs, { q1: 2 })).toBe(1)
    expect(gradeQuiz(qs, { q1: 1 })).toBe(0)
  })
  it('blocks assisted or critically broken designs regardless of total', () => {
    expect(assessmentPass(review, false)).toBe(true)
    expect(assessmentPass(review, true)).toBe(false)
    expect(assessmentPass({ ...review, scope: 'repair' }, false)).toBe(false)
    expect(assessmentPass({ ...review, critical_issue: true }, false)).toBe(false)
    expect(assessmentPass({ ...review, dimensions: review.dimensions.map((d, i) => i === 0 ? { ...d, score: 1 } : d) }, false)).toBe(false)
  })
  it('requires the whole rubric and actual evidence', () => {
    expect(assessmentPass({ ...review, dimensions: review.dimensions.slice(0, 7) }, false)).toBe(false)
    expect(assessmentPass({ ...review, dimensions: review.dimensions.map(d => ({ ...d, evidence: '' })) }, false)).toBe(false)
  })
  it('progresses recall intervals and resets failures to ten minutes', () => {
    const good = scheduleReview(card, 'good', 1000)
    expect(good.dueAt).toBe(1000 + 3 * DAY)
    const again = scheduleReview(good, 'again', 2000)
    expect(again.dueAt).toBe(602000); expect(again.step).toBe(0); expect(again.lapses).toBe(1)
    expect(scheduleReview(good, 'hard', 2000).dueAt).toBe(2000 + DAY)
    expect(scheduleReview({ ...card, step: 5 }, 'good', 0).dueAt).toBe(60 * DAY)
  })
  it('rejects malformed backups and unsafe keys, without accepting fabricated pass flags', () => {
    expect(() => validateProgress({ schemaVersion: 1, modules: [], cards: {} })).toThrow()
    expect(() => validateProgress({ ...emptyProgress(), cards: { x: { ...card, id: 'x', dueAt: NaN } } })).toThrow()
    expect(() => validateProgress(JSON.parse('{"schemaVersion":1,"modules":{"__proto__":{}},"cards":{}}'))).toThrow()
    const data = emptyProgress()
    data.modules['00-design-framework'] = { completedSections: [], notes: '', drafts: { p1: newDraft() }, quizAttempts: [], attempts: [
      { id: 'a', exerciseId: 'p1', createdAt: 1000, phases: newDraft().phases, diagram: '', assisted: true, review: structuredClone(review) },
    ] }
    const restored = validateProgress(data)
    expect(restored.modules['00-design-framework']!.attempts[0]!.review!.total).toBe(18)
    expect(restored.modules['00-design-framework']!.attempts[0]!.review!.passed).toBe(false)
  })
})

import { geoSearch, queueProjection, reservationTrace, retryTrace } from './hldLabs'
import type { HLDModule } from '../types/hld'

describe('HLD mechanism labs and honest learning evidence', () => {
  it('shows sustained overload, equilibrium, and net drain rather than total worker rate', () => {
    expect(queueProjection(600,300,200,60)).toEqual({ backlog:6600, growth:100, drainSeconds:null })
    expect(queueProjection(600,200,200,60).backlog).toBe(600)
    expect(queueProjection(600,100,200,2).drainSeconds).toBe(4)
    expect(queueProjection(600,100,200,60).backlog).toBe(0)
  })
  it('exposes two confirmations from a stale read and one from an atomic guard', () => {
    expect(reservationTrace(false,4).bookings).toBe(2)
    expect(reservationTrace(true,4).bookings).toBe(1)
    expect(reservationTrace(false,2).bookings).toBe(0)
  })
  it('reuses the same remote identity under the stated provider model', () => {
    expect(retryTrace(false,4).effects).toBe(2)
    expect(retryTrace(true,4).effects).toBe(1)
    expect(retryTrace(true,3).effects).toBe(1)
  })
  it('finds a nearby place across a cell border and removes distant candidates', () => {
    expect(geoSearch(95,95,40,false).missed.map(p=>p.id)).toContain('A')
    const covered = geoSearch(95,95,40,true)
    expect(covered.missed).toEqual([])
    expect(covered.candidates.map(p=>p.id)).toContain('C')
    expect(covered.matches.map(p=>p.id)).not.toContain('C')
  })
  it('restores scoped repair feedback without turning it into design evidence', () => {
    const data = emptyProgress()
    data.modules.test = { completedSections:[], notes:'', drafts:{}, quizAttempts:[], attempts:[{id:'a',exerciseId:'p3',createdAt:0,phases:newDraft().phases,diagram:'',assisted:false,review:{...structuredClone(review),scope:'repair',dimensions:structuredClone(review.dimensions).filter(d=>['requirements','flows','correctness','failure_operations'].includes(d.id))}}] }
    const restored = validateProgress(data)
    expect(restored.modules.test!.attempts[0]!.review!.passed).toBe(false)
    restored.modules.test!.attempts[0]!.review!.dimensions[0]!.id='scale'
    expect(() => validateProgress(restored)).toThrow()
  })
  it('does not confuse exploration, a quiz, or an assisted score with independent delayed evidence', () => {
    const module = { id:'test', sections:[{id:'s'}], exercises:[{id:'p1',kind:'design'},{id:'p2',kind:'transfer'},{id:'p3',kind:'repair'}] } as HLDModule
    const progress = { completedSections:['s'], notes:'', drafts:{}, quizAttempts:[{ createdAt:0,choices:{},score:4,total:4 }], attempts:[{ id:'a', exerciseId:'p1', createdAt:1000, phases:newDraft().phases, diagram:'', assisted:true, review:structuredClone(review) }] }
    const early = moduleEvidence(module,progress,[])
    expect(early.lesson).toBe(true); expect(early.quiz).toBe(true); expect(early.independent).toBe(false); expect(early.delayed).toBe(false); expect(early.complete).toBe(false)
    progress.attempts[0]!.assisted=false
    const delayed = moduleEvidence(module,progress,[{...card,moduleId:'test',kind:'recall',lastRating:'good',lastReviewed:1000+7*DAY}])
    expect(delayed.independent).toBe(true);expect(delayed.delayed).toBe(true)
    expect(moduleEvidence(module,progress,[{...card,moduleId:'test',kind:'recall',lastRating:'hard',lastReviewed:1000+7*DAY}]).delayed).toBe(false)
  })
})

import { withoutScaffold } from './learningEvidence'
it('does not count supplied LLD templates or starter lines as learner work', () => {
  const template = 'Must-haves:\n- \n\nAssumptions:\n- '
  expect(withoutScaffold(template,template)).toBe('')
  expect(withoutScaffold(template+'\n- Prevent duplicate parking tickets.',template)).toBe('- Prevent duplicate parking tickets.')
  expect(withoutScaffold('class Lot {\n// TODO\n}\n', 'class Lot {\n// TODO\n}')).toBe('')
})

it('requires every main round of the multi-round assessment', () => {
  const module = { id:'exam', sections:[{id:'s'}], exercises:[{id:'p1a',kind:'design'},{id:'p1b',kind:'design'},{id:'p2',kind:'transfer'},{id:'p3',kind:'repair'}] } as HLDModule
  const attempt = {id:'a',exerciseId:'p1a',createdAt:0,phases:newDraft().phases,diagram:'',assisted:false,review:structuredClone(review)}
  const progress = { completedSections:[],notes:'',drafts:{},quizAttempts:[],attempts:[attempt] }
  expect(moduleEvidence(module,progress,[]).design).toBe(false)
  expect(moduleEvidence(module,progress,[]).independent).toBe(false)
  progress.attempts.push({...attempt,id:'b',exerciseId:'p1b'})
  expect(moduleEvidence(module,progress,[]).design).toBe(true)
  expect(moduleEvidence(module,progress,[]).independent).toBe(true)
})
