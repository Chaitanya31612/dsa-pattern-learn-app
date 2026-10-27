import { afterEach,describe,expect,it,vi } from 'vitest'
import { contextBudget,cosineDistance,evidenceCheck,approvalValid,confusion } from './aiLearningLabs'
import { decodeLearningBackup,encodeLearningBackup } from './learningBackup'
import { createLearningSpace } from '../composables/useSoftware'
import type { SoftwareProgress } from '../types/software'
const empty=():SoftwareProgress=>({schemaVersion:1,modules:{},cards:{}})
afterEach(()=>vi.unstubAllGlobals())
describe('Visible AI boundaries',()=>{
 it('reserves output space and identifies overflow',()=>{
  expect(contextBudget([120,180,60,140,300],200,1000)).toEqual({used:1000,remaining:0,fits:true})
  expect(contextBudget([801],200,1000).fits).toBe(false)
 })
 it('compares directions and rejects invalid vectors',()=>{
  expect(cosineDistance([1,0],[2,0])).toBeCloseTo(0)
  expect(cosineDistance([1,0],[0,1])).toBeCloseTo(1)
  expect(cosineDistance([1,0],[-1,0])).toBeCloseTo(2)
  for(const vector of [[0,0],[1],[NaN,1]])expect(()=>cosineDistance([1,0],vector)).toThrow()
 })
 it('separates citation membership from agreement with a typed fact',()=>{
  expect(evidenceCheck('F1','released_count',2)).toEqual({knownSource:true,exactField:false})
  expect(evidenceCheck('F9','held_count',2).knownSource).toBe(false)
  expect(evidenceCheck('__proto__','held_count',2).knownSource).toBe(false)
  expect(evidenceCheck('F1','held_count',2).exactField).toBe(true)
 })
 it('expires approval and rejects changed operations or versions',()=>{
  const approved={digest:'op1',version:3,expires:100}
  expect(approvalValid(approved,{digest:'op1',version:3,now:99})).toBe(true)
  expect(approvalValid(approved,{digest:'op1',version:3,now:100})).toBe(false)
  expect(approvalValid(approved,{digest:'op2',version:3,now:1})).toBe(false)
  expect(approvalValid(approved,{digest:'op1',version:4,now:1})).toBe(false)
 })
 it('keeps a confidently wrong accept visible and reports undefined precision honestly',()=>{
  const cases=[{score:.9,correct:false},{score:.8,correct:true},{score:.2,correct:true},{score:.1,correct:false}]
  expect(confusion(cases,.7)).toEqual({tp:1,fp:1,fn:1,tn:1,precision:.5,recall:.5})
  expect(confusion(cases,1).precision).toBeNull()
 })
})
describe('Independent learning progress',()=>{
 it('accepts old Software backups but blocks cross-space imports',()=>{
  expect(decodeLearningBackup(empty(),'software')).toEqual(empty())
  const ai=JSON.parse(encodeLearningBackup(empty(),'ai'))
  expect(decodeLearningBackup(ai,'ai')).toEqual(empty())
  expect(()=>decodeLearningBackup(ai,'software')).toThrow('other learning space')
  expect(()=>decodeLearningBackup(JSON.parse(encodeLearningBackup(empty(),'software')),'ai')).toThrow()
  expect(()=>decodeLearningBackup(empty(),'ai')).toThrow()
 })
 it('isolates autosaves and restores without resetting the other course',async()=>{
  const values=new Map<string,string>()
  vi.stubGlobal('localStorage',{getItem:(key:string)=>values.get(key)??null,setItem:(key:string,value:string)=>values.set(key,value)})
  vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({schemaVersion:1,modules:[{id:'test'}]})})))
  const software=createLearningSpace('software')(),ai=createLearningSpace('ai')()
  await Promise.all([software.load(),ai.load()])
  software.state('ruby-values').notes='My earlier work'
  ai.state('ai-boundary').notes='My AI boundary'
  expect(JSON.parse(values.get('software-learnings-progress-v1')!).modules['ruby-values'].notes).toBe('My earlier work')
  expect(JSON.parse(values.get('ai-learnings-progress-v1')!).modules['ai-boundary'].notes).toBe('My AI boundary')
  ai.replaceBackup(empty())
  expect(software.state('ruby-values').notes).toBe('My earlier work')
  expect(vi.mocked(fetch).mock.calls.map(c=>String(c[0]))).toEqual(['/software-course.json','/ai-course.json'])
 })
 it('preserves corrupt stored data until a valid successful replacement',()=>{
  const values=new Map([['ai-learnings-progress-v1','broken original']])
  vi.stubGlobal('fetch',vi.fn(async()=>({ok:false})))
  vi.stubGlobal('localStorage',{getItem:(key:string)=>values.get(key)??null,setItem:(key:string,value:string)=>values.set(key,value)})
  const ai=createLearningSpace('ai')()
  ai.state('ai-boundary').notes='Temporary work'
  expect(ai.blocked.value).toBe(true)
  expect(values.get('ai-learnings-progress-v1')).toBe('broken original')
  expect(()=>ai.replaceBackup({})).toThrow()
  expect(values.get('ai-learnings-progress-v1')).toBe('broken original')
  ai.replaceBackup(empty());expect(ai.blocked.value).toBe(false)
 })
})
