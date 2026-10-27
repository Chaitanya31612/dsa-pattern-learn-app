/** Small deterministic teaching models. No live AI, credentials or work data. */
export function contextBudget(input: number[], reserve: number, limit: number) {
  const used=input.reduce((sum,n)=>sum+n,0)+reserve
  return {used,remaining:limit-used,fits:used<=limit}
}
export function cosineDistance(a:number[],b:number[]) {
  if(a.length!==b.length || !a.length || [...a,...b].some(n=>!Number.isFinite(n))) throw new Error('Invalid vectors')
  const norm=(v:number[])=>Math.sqrt(v.reduce((sum,n)=>sum+n*n,0))
  const denominator=norm(a)*norm(b)
  if(!denominator)throw new Error('Zero vector has no cosine direction')
  return 1-a.reduce((sum,n,i)=>sum+n*b[i]!,0)/denominator
}
export function evidenceCheck(citation:string,key:string,value:number) {
  const facts:Record<string,{key:string;value:number}>={F1:{key:'held_count',value:2}}
  const fact=Object.prototype.hasOwnProperty.call(facts,citation)?facts[citation]:undefined
  return {knownSource:!!fact,exactField:!!fact&&fact.key===key&&fact.value===value}
}
export function approvalValid(approved:{digest:string;version:number;expires:number},current:{digest:string;version:number;now:number}) {
  return approved.digest===current.digest&&approved.version===current.version&&current.now<approved.expires
}
export function confusion(cases:{score:number;correct:boolean}[],threshold:number) {
  let tp=0,fp=0,fn=0,tn=0
  for(const row of cases) { if(row.score>=threshold)row.correct?tp++:fp++;else row.correct?fn++:tn++ }
  return {tp,fp,fn,tn,precision:tp+fp?tp/(tp+fp):null,recall:tp+fn?tp/(tp+fn):null}
}
