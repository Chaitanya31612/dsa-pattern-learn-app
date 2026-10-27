/** Short reading beats. Sentence boundaries never change the original wording. */
export interface ReadingBeat { start: number; end: number; text: string }
type SentenceSegmenter = { segment: (value: string) => Iterable<{ index: number; segment: string }> }
const Segmenter = (Intl as unknown as {Segmenter?:new(locale:string,options:{granularity:string})=>SentenceSegmenter}).Segmenter
const segmenter = Segmenter ? new Segmenter('en',{granularity:'sentence'}) : null
export function readingBeats(text: string, protectedRanges: {start:number;end:number}[] = []): ReadingBeat[] {
  if (!text.trim()) return []
  const raw = segmenter ? Array.from(segmenter.segment(text)).map(s=>({start:s.index,end:s.index+s.segment.length,text:s.segment})) :
    Array.from(text.matchAll(/[^.!?]+(?:[.!?]+(?:\s+|$)|$)/g)).map(m=>({start:m.index!,end:m.index!+m[0].length,text:m[0]}))
  const sentences: ReadingBeat[]=[]
  let pendingStart=0
  for(const sentence of raw) {
    if(protectedRanges.some(range=>sentence.end>range.start && sentence.end<range.end))continue
    sentences.push({start:pendingStart,end:sentence.end,text:text.slice(pendingStart,sentence.end)});pendingStart=sentence.end
  }
  const result: ReadingBeat[]=[]
  let start=0,end=0,words=0,count=0
  for(const sentence of sentences) {
    const size=sentence.text.trim().split(/\s+/).length
    if(count && (count===2 || words+size>32)) {
      result.push({start,end,text:text.slice(start,end)});start=sentence.start;words=0;count=0
    }
    end=sentence.end;words+=size;count++
  }
  if(count)result.push({start,end,text:text.slice(start,end)})
  return result
}

/** Clone DOM ranges so emphasis, links and inline code survive sentence breaks. */
export function spaceReadingParagraphs(root: HTMLElement) {
  for(const item of Array.from(root.querySelectorAll('li'))) {
    if(item.querySelector('p,ul,ol,pre,input,button,div,table,svg,img'))continue
    if(readingBeats(item.textContent??'').length<2)continue
    const p=document.createElement('p')
    while(item.firstChild)p.append(item.firstChild)
    item.append(p)
  }
  for (const paragraph of Array.from(root.querySelectorAll('p'))) {
    if(paragraph.closest('pre,code,table') || paragraph.querySelector('br,img,svg')) continue
    const text=paragraph.textContent??''
    const walker=document.createTreeWalker(paragraph,NodeFilter.SHOW_TEXT)
    const nodes:{node:Node;start:number;end:number}[]=[]
    let node:Node|null,offset=0
    while((node=walker.nextNode())) { const length=node.textContent?.length??0;nodes.push({node,start:offset,end:offset+length});offset+=length }
    const protectedRanges=nodes.filter(n=>n.node.parentElement?.closest('code,a')).map(n=>({start:n.start,end:n.end}))
    const beats=readingBeats(text,protectedRanges)
    if(beats.length<2)continue
    const group=document.createElement('div');group.className='reading-group'
    for(const beat of beats) {
      const first=nodes.find(n=>n.end>beat.start),last=nodes.find(n=>n.end>=beat.end)
      if(!first || !last)continue
      const range=document.createRange();range.setStart(first.node,beat.start-first.start);range.setEnd(last.node,beat.end-last.start)
      const part=document.createElement('p');part.className='reading-beat';part.append(range.cloneContents());group.append(part)
    }
    if(group.childNodes.length===beats.length)paragraph.replaceWith(group)
  }
}

export const READING_TERMS:Record<string,string>={
 'quorum':'The minimum number of members or responses an operation requires.',
 'lease':'Permission that expires unless it is renewed.',
 'outbox':'A database table that saves an event in the same transaction as its business change.',
 'inbox':'A record of received events that helps detect repeated delivery.',
 'schema evolution':'Changing a data format while older producers or readers may still exist.',
 'predicate':'A condition that evaluates to true or false.',
 'canonical':'The chosen standard or authoritative form.',
 'invariant':'A rule that must stay true, even when work is retried or fails.',
 'idempotency':'Repeating the same intended operation does not repeat its effect.',
 'provenance':'Where a fact came from, including its source and version.',
 'entailment':'Whether the evidence actually supports a claim.',
 'probabilistic':'The output can vary. A likely answer can still be wrong.',
 'deterministic':'The same input and state give the same result.',
 'reconciliation':'Compare what should have happened with what did happen. Repair the difference.',
 'orchestration':'Code that coordinates several steps or services.',
 'latency':'The time you wait for an operation to finish.',
 'throughput':'How much work a system finishes in a given time.',
 'cardinality':'How many distinct values a field has.',
 'projection':'A saved view built from other data, often for faster reads.',
 'hydration':'Connect browser behavior to HTML that the server already rendered.',
 'calibration':'Check whether confidence scores match measured correctness.',
 'serialization':'Turn a value into a form that can be stored or sent.',
 'deserialization':'Read stored or received data back into a usable value.',
 'backpressure':'Slow the producer when the next step cannot keep up.',
 'atomicity':'A group of changes commits together or does not commit at all.',
 'encapsulation':'Keep data and the rules for changing it behind a small public interface.',
 'polymorphism':'Call the same operation on different types. Each type supplies its own behavior.',
 'fan-out':'One item causes work for many recipients or destinations.',
 'eventual consistency':'Copies can differ briefly. They should agree once updates finish.',
}
export function readingTerms(text:string) {
  // Explain prose terms only. Code and diagrams keep their exact technical form.
  const prose=text.replace(/```[\s\S]*?```|`[^`]*`/g,'')
  return Object.entries(READING_TERMS).filter(([term])=>new RegExp(`\\b${term}\\b`,'i').test(prose)).slice(0,3)
}
