import { describe,expect,it } from 'vitest'
import { readingBeats,readingTerms } from './reading'
describe('Course reading beats',()=>{
 it('keeps text and order while grouping at most two short sentences',()=>{
  const text='One small idea. A second idea. A third idea. A final idea.'
  const beats=readingBeats(text)
  expect(beats).toHaveLength(2)
  expect(beats.map(b=>b.text).join('')).toBe(text)
  expect(beats[1]!.start).toBe(beats[0]!.end)
 })
 it('preserves versions, URLs, punctuation and a one-sentence explanation',()=>{
  for(const text of ['Use Ruby 3.3.6 with Rails 7.2.2.2.','See https://example.com/docs. Try the example.','Why? Because it retries safely!','   ']) {
   expect(readingBeats(text).map(b=>b.text).join('')).toBe(text.trim()?text:'')
  }
 })
 it('does not insert a reading boundary inside a protected inline example',()=>{
  const text='Keep this inline example: first. Second. Third. Then continue with the rule. End here.'
  const start=text.indexOf('first'),end=text.indexOf(' Then')
  const beats=readingBeats(text,[{start,end}])
  expect(beats.every(b=>b.end<=start || b.end>=end)).toBe(true)
  expect(beats.map(b=>b.text).join('')).toBe(text)
 })
 it('explains a small number of real prose terms and ignores fenced or inline code',()=>{
  expect(readingTerms('An invariant must hold. Idempotency helps retries. Latency is measured. Throughput matters.')).toHaveLength(3)
  expect(readingTerms('```text\nidempotency\n```\nUse `latency` as a field name.')).toEqual([])
  expect(readingTerms('This is an orchestration decision.')[0]?.[1]).toContain('coordinates')
 })
})
