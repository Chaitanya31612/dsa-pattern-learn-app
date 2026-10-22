import { describe, expect, it } from 'vitest'
import { newSoftwareDraft, softwareEvidence, validateSoftwareProgress, validateSoftwareReport } from './softwareLearning'
import { DAY, gradeQuiz, scheduleReview } from './hldLearning'
import type { SoftwareModule, SoftwareModuleProgress } from '../types/software'
import type { HLDCard } from '../types/hld'

const module = { id:'ruby-values', sections:[{id:'idea'}], exercises:[{id:'repair'},{id:'transfer'}] } as SoftwareModule
const emptyModule = (): SoftwareModuleProgress => ({completed:[],drafts:{},attempts:[],quizzes:[],quizDraft:{},quizSubmitted:false,notes:''})
const card = (): HLDCard => ({id:'ruby-values-recall',moduleId:module.id,kind:'recall',question:'why?',answer:'because',dueAt:DAY,step:0,lapses:0,lastReviewed:null,lastResponse:''})

describe('Software learning evidence', () => {
  it('does not equate reading with consolidation', () => {
    const p=emptyModule();p.completed=['idea']
    expect(softwareEvidence(module,p).count).toBe(1)
    expect(softwareEvidence(module,p).complete).toBe(false)
  })
  it('requires every requested practice type and the latest quiz', () => {
    const p=emptyModule();p.completed=['idea']
    p.attempts=[{...newSoftwareDraft(),id:'1',exerciseId:'repair',createdAt:0}]
    p.quizzes=[{score:2,total:2,choices:{},createdAt:0},{score:1,total:2,choices:{},createdAt:1}]
    const evidence=softwareEvidence(module,p)
    expect(evidence.practice).toBe(false);expect(evidence.quiz).toBe(false)
  })
  it('requires seven elapsed days after practice for delayed evidence', () => {
    const p=emptyModule();p.attempts=[{...newSoftwareDraft(),id:'1',exerciseId:'repair',createdAt:DAY}]
    const c={...card(),lastRating:'good' as const,lastReviewed:7*DAY}
    expect(softwareEvidence(module,p,[c]).delayed).toBe(false)
    c.lastReviewed=8*DAY
    expect(softwareEvidence(module,p,[c]).delayed).toBe(true)
    c.kind='quiz'
    expect(softwareEvidence(module,p,[c]).delayed).toBe(false)
  })
  it('records a good first scheduled recall with a three-day next gap', () => {
    const c=scheduleReview(card(),'good',DAY)
    expect(c.dueAt).toBe(4*DAY)
    expect(scheduleReview(c,'again',5*DAY).dueAt).toBe(5*DAY+600000)
  })
  it('does not grade an incomplete quiz', () => {
    expect(()=>gradeQuiz([{id:'x',prompt:'?',options:['a','b'],correctIndex:1,explanation:'why'}],{})).toThrow()
  })
})
describe('Backups and AI feedback', () => {
  it('round-trips attempts, notes, and recall without losing false assistance flags', () => {
    const p=emptyModule();p.drafts.repair=newSoftwareDraft();p.notes='A concrete failure'
    const data={schemaVersion:1,modules:{[module.id]:p},cards:{[card().id]:card()}}
    expect(validateSoftwareProgress(JSON.parse(JSON.stringify(data)))).toEqual(data)
  })
  it('keeps original module work alongside new tracks and cumulative quiz keys', () => {
    const old=emptyModule(), expanded=emptyModule()
    old.notes='Earlier Ruby reasoning'
    expanded.quizDraft={'review-ops-redis-correctness':2,'q1':0}
    expanded.quizzes=[{createdAt:10,score:18,total:24,choices:{...expanded.quizDraft}}]
    const backup={schemaVersion:1,modules:{'ruby-values':old,'ops-toolkit-capstone':expanded},cards:{}}
    expect(validateSoftwareProgress(JSON.parse(JSON.stringify(backup)))).toEqual(backup)
  })
  it('rejects malformed progress rather than overwriting it', () => {
    expect(()=>validateSoftwareProgress({schemaVersion:1,modules:{x:{completed:[]}},cards:{}})).toThrow()
    const p=emptyModule();p.drafts.repair={...newSoftwareDraft(),phases:{predict:'x'} as never}
    expect(()=>validateSoftwareProgress({schemaVersion:1,modules:{x:p},cards:{}})).toThrow()
  })
  it('rejects prototype keys and impossible review dates/steps', () => {
    expect(()=>validateSoftwareProgress(JSON.parse('{"schemaVersion":1,"modules":{"__proto__":{}},"cards":{}}'))).toThrow()
    expect(()=>validateSoftwareProgress({schemaVersion:1,modules:{},cards:{[card().id]:{...card(),step:99}}})).toThrow()
  })
  it('requires evidence for four distinct dimensions, not a fake total', () => {
    const r={source:'ai',summary:'Partial',next_exercise:'Test a failure',dimensions:['predict','change','verify','explain'].map(id=>({id,score:1,evidence:'A proposed test',feedback:'Run it'}))}
    expect(validateSoftwareReport(r)).toEqual(r)
    expect(()=>validateSoftwareReport({...r,dimensions:[r.dimensions[0],r.dimensions[0],r.dimensions[2],r.dimensions[3]]})).toThrow()
    expect(()=>validateSoftwareReport({...r,dimensions:r.dimensions.map(d=>({...d,evidence:' '}))})).toThrow()
  })
})
