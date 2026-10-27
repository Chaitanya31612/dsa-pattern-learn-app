<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { eventFlowModel } from '../lib/softwareLabs'
const props = defineProps<{ moduleId: string }>()
const kafka = reactive(eventFlowModel())
const eventModule = computed(() => props.moduleId.startsWith('events-'))
const supported = computed(() => eventModule.value ||  ['ruby-values','git-snapshots','git-staging','spring-transactions','spring-persistence','ruby-rails-queries','frontend-runtime','frontend-vue-async','frontend-async-coordination'].includes(props.moduleId))
const step = ref(0)
const work = ref('base'); const index = ref('base'); const head = ref('base')
const throughProxy = ref(true)
const rows = ref(20); const preload = ref(false)
const guard = ref(true); const result = ref('No result'); const loading = ref(false); const finishedA = ref(false); const finishedB = ref(false); const started = ref(false)
const referenceSteps = [
  {code:'first = ["open"]',first:'Array A',second:'not assigned',a:'["open"]',b:'does not exist',why:'One name points at one array.'},
  {code:'second = first',first:'Array A',second:'Array A',a:'["open"]',b:'does not exist',why:'Assignment copied the reference. Both names point to A.'},
  {code:'second << "done"',first:'Array A',second:'Array A',a:'["open", "done"]',b:'does not exist',why:'The array changed. Both names still point to it.'},
  {code:'second = ["closed"]',first:'Array A',second:'Array B',a:'["open", "done"]',b:'["closed"]',why:'Reassignment moved only the second arrow. Array A kept its values.'},
]
function startRace() { started.value=true;loading.value=true;finishedA.value=false;finishedB.value=false;result.value='Waiting for B, the latest query' }
function finish(which:'A'|'B') {
  if(which==='A')finishedA.value=true;else finishedB.value=true
  if(!guard.value || which==='B'){result.value=`Results for ${which}`;loading.value=false}
}
</script>
<template>
  <section v-if="supported" class="sw-lab" aria-label="Interactive mechanism lab">
    <p class="sw-eyebrow">Move the pieces</p><h2>See why it happens</h2><p class="sw-muted">A small model of this mechanism. It does not execute Ruby, Java, Git, or SQL.</p>
    <template v-if="eventModule">
      <h3>Crash between the effect and the offset</h3><p>One synthetic event. One partition. The database effect is a counter. Try both timelines, then explain why they differ.</p>
      <label class="sw-checkbox"><input v-model="kafka.deduplicate" type="checkbox" :disabled="kafka.records.length>0"/>Use a transactional inbox to skip repeated event IDs</label>
      <div class="lab-state" role="status"><div><small>Outbox</small><strong>{{ kafka.pending?'Pending':'Marked published' }}</strong></div><div><small>Kafka copies · same event ID</small><strong>{{ kafka.records.length }}</strong></div><div><small>DB effect count</small><strong>{{ kafka.effects }}</strong></div><div><small>Committed next offset</small><strong>{{ kafka.committed }}</strong></div></div>
      <div class="lab-path"><span>Outbox → log</span><span>→ Read {{ kafka.inflight ? `offset ${kafka.inflight.index}` : '(none in hand)' }}</span><span>→ DB effect</span><span>→ Commit progress</span></div>
      <div class="sw-row"><button class="btn" :disabled="!kafka.pending" @click="kafka.publish()">Publish + mark outbox</button><button class="btn" :disabled="!kafka.pending" @click="kafka.publish(false)">Publish · crash before mark</button><button class="btn" :disabled="!!kafka.inflight || kafka.position>=kafka.records.length" @click="kafka.read()">Read next record</button><button class="btn" :disabled="!kafka.inflight" @click="kafka.apply()">Commit DB effect</button><button class="btn" :disabled="!kafka.inflight" @click="kafka.commit()">Commit next offset</button><button class="btn" @click="kafka.crash()">Crash + restart consumer</button><button class="btn btn-ghost" @click="Object.assign(kafka,eventFlowModel())">Reset event model</button></div>
      <p class="sw-cue">Try: publish → read → DB effect → crash → read → DB effect → commit. Then reset, remove the inbox, and repeat. Finally, try committing progress before the DB effect and crashing.</p><p>This deliberately allows a bad order so you can see a lost effect. It models one serial consumer and atomic DB writes. Real broker, rebalance, and DB behavior is checked in the Code lab.</p>
    </template>
    <template v-else-if="moduleId==='ruby-values'">
      <pre>{{ referenceSteps[step]!.code }}</pre><div class="lab-state"><div><small>Name</small><strong>first → {{ referenceSteps[step]!.first }}</strong><strong>second → {{ referenceSteps[step]!.second }}</strong></div><div><small>Objects</small><strong>A: {{ referenceSteps[step]!.a }}</strong><strong>B: {{ referenceSteps[step]!.b }}</strong></div></div><p role="status">{{ referenceSteps[step]!.why }}</p><div class="sw-row"><button class="btn" :disabled="step===0" @click="step--">Previous assignment</button><button class="btn" :disabled="step===3" @click="step++">Next assignment</button><button class="btn btn-ghost" @click="step=0">Reset model</button></div>
    </template>
    <template v-else-if="moduleId.startsWith('git-')">
      <div class="lab-state"><div><small>Working tree</small><strong>{{ work }}</strong></div><div><small>Index · proposed next snapshot</small><strong>{{ index }}</strong></div><div><small>HEAD · last commit</small><strong>{{ head }}</strong></div></div><div class="sw-row"><button class="btn" @click="work=work==='A'?'B':'A'">Edit file · A ↔ B</button><button class="btn" @click="index=work">git add file</button><button class="btn" @click="head=index">git commit</button><button class="btn btn-ghost" @click="work='base';index='base';head='base'">Reset model</button></div><p role="status">git diff: {{ index===work?'no unstaged difference':`${index} → ${work}` }}. git diff --cached: {{ head===index?'no staged difference':`${head} → ${index}` }}.</p><p>Try: edit to A → add → edit to B → commit. Which value is in HEAD?</p>
    </template>
    <template v-else-if="moduleId==='spring-transactions'">
      <label class="sw-checkbox"><input v-model="throughProxy" type="checkbox"/>Call reserve through the injected proxy</label><div class="lab-path"><span>Caller</span><span>→</span><span :class="{off:!throughProxy}">Transaction proxy {{ throughProxy?'entered':'skipped' }}</span><span>→</span><span>reserve()</span></div><p role="status">{{ throughProxy?'The proxy sees @Transactional and can start the transaction.':'The unannotated outer method calls this.reserve(). In the usual proxy setup, that self-call bypasses interception.' }}</p><p>Assumption: no transaction was already active. An existing outer transaction changes the result. Test the actual boundary in Spring.</p>
    </template>
    <template v-else-if="['frontend-runtime','frontend-vue-async','frontend-async-coordination'].includes(moduleId)">
      <label class="sw-checkbox"><input v-model="guard" :disabled="started" type="checkbox"/>Accept only the latest request for rows, loading, and errors</label><div class="sw-row"><button class="btn" @click="startRace">Start A, then B</button><button class="btn" :disabled="!started || finishedB" @click="finish('B')">Finish B first</button><button class="btn" :disabled="!started || finishedA" @click="finish('A')">Finish A later</button><button class="btn btn-ghost" @click="started=false;result='No result';loading=false">Reset race</button></div><div class="lab-state" role="status"><div><small>Visible rows</small><strong>{{ result }}</strong></div><div><small>Loading</small><strong>{{ loading?'Still waiting':'Finished' }}</strong></div></div><p>Finish B, then A. Reset, remove the guard, and repeat. Also finish A while B is still pending: should the spinner stop?</p>
    </template>
    <template v-else>
      <label class="sw-label">Tasks in the list · {{ rows }}<input v-model.number="rows" type="range" min="1" max="100" step="1"/></label><label class="sw-checkbox"><input v-model="preload" type="checkbox"/>Fetch the needed to-one owner relation together</label><div class="lab-state"><div><small>Task query</small><strong>1</strong></div><div><small>Owner queries</small><strong>{{ preload?1:rows }}</strong></div><div><small>Total queries</small><strong>{{ preload?2:rows+1 }}</strong></div></div><p>Model assumption: one uncached owner query per task versus one separate preload query for the whole list. A fetch join can use one query; real SQL depends on the chosen fetch plan and associations. Measure it.</p>
    </template>
  </section>
</template>
<style scoped>.sw-lab{padding:24px;border:1px solid var(--accent-cyan);border-radius:14px;background:var(--bg-secondary);margin:24px 0}.sw-lab pre{padding:16px;background:var(--bg-primary);white-space:pre-wrap;overflow-wrap:anywhere;font:1rem var(--font-mono)}.lab-state{display:flex;flex-wrap:wrap;gap:12px;margin:20px 0}.lab-state>div{padding:18px;border:1px solid var(--border-default);border-radius:10px;flex:1;min-width:160px;background:var(--bg-card)}.lab-state small,.lab-state strong{display:block;margin-bottom:10px}.lab-state strong{color:var(--accent-cyan);overflow-wrap:anywhere}.lab-path{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0;align-items:center}.lab-path span{padding:12px;border:1px solid var(--accent-cyan);border-radius:8px}.lab-path .off{opacity:.6;border-style:dashed;text-decoration:line-through}input[type=range]{display:block;width:min(450px,100%);margin:14px 0;accent-color:var(--accent-cyan)}</style>
