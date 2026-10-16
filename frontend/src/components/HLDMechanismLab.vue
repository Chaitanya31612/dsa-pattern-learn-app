<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { GEO_PLACES, geoSearch, queueProjection, reservationTrace, retryTrace } from '../lib/hldLabs'
const props = defineProps<{ initial?: 'geo' | 'queue' | 'reservation' | 'retry' | null }>()
const emit = defineEmits<{ remember: [question: string, answer: string] }>()
const lab = ref(props.initial ?? 'queue')
const names = { queue: 'Queue overload', reservation: 'Two buyers, one seat', retry: 'The lost reply', geo: 'Search across a border' }
const prediction = ref('')
const explanation = ref('')
const started = ref(false)
const step = ref(0)
const safe = ref(true)
const arrivals = ref(300)
const capacity = ref(200)
const initial = ref(600)
const userX = ref(95)
const radius = ref(40)
const saved = ref(false)
watch(lab, () => { prediction.value = ''; explanation.value = ''; started.value = false; step.value = 0; safe.value = true; saved.value = false })
watch(safe, () => { step.value = 0 })
const queue = computed(() => queueProjection(initial.value, arrivals.value, capacity.value, 60))
const series = computed(() => Array.from({ length: 13 }, (_, i) => queueProjection(initial.value, arrivals.value, capacity.value, i * 5).backlog))
const maxBacklog = computed(() => Math.max(1, ...series.value))
const path = computed(() => series.value.map((v, i) => `${20 + i * 25},${130 - 100 * v / maxBacklog.value}`).join(' '))
const reservation = computed(() => reservationTrace(safe.value, step.value))
const retry = computed(() => retryTrace(safe.value, step.value))
const geo = computed(() => geoSearch(userX.value, 95, radius.value, safe.value))
const question = computed(() => lab.value === 'queue' ? 'Can a queue catch up when arrivals stay above processing capacity?' : lab.value === 'reservation' ? 'Can two buyers safely reserve the last seat after separate reads?' : lab.value === 'retry' ? 'What happens when a successful remote effect loses its reply?' : 'Why does a nearby search need cells across the border?')
function remember() { emit('remember', question.value, explanation.value); saved.value = true }
</script>
<template>
  <section class="hld-lab hld-content-pane">
    <p class="hld-eyebrow">Try → predict → explain</p><h2>See the mechanism change</h2>
    <nav class="hld-tabs" aria-label="Mechanism labs"><button v-for="(name, id) in names" :key="id" :aria-pressed="lab === id" :class="{ selected: lab === id }" @click="lab = id">{{ name }}</button></nav>
    <p class="hld-muted">Small teaching models. These run locally. They do not model every production detail.</p>
    <h3>{{ question }}</h3><label class="hld-label">Predict before you try<textarea v-model="prediction" class="hld-input" rows="2" placeholder="I think… because…"></textarea></label>
    <button v-if="!started" class="btn btn-primary" :disabled="!prediction.trim()" @click="started = true">Try my prediction</button>
    <template v-else>
      <div v-if="lab === 'queue'" class="hld-lab-grid">
        <div><label class="hld-label">Arrivals: {{ arrivals }} jobs/s<input v-model.number="arrivals" type="range" min="0" max="1000" step="50" /></label><label class="hld-label">Processing: {{ capacity }} jobs/s<input v-model.number="capacity" type="range" min="0" max="1000" step="50" /></label><label class="hld-label">Starting backlog: {{ initial }} jobs<input v-model.number="initial" type="range" min="0" max="5000" step="100" /></label></div>
        <div aria-live="polite"><svg viewBox="0 0 340 160" role="img" aria-label="Backlog over the next sixty seconds"><path d="M20 20 V130 H325" fill="none" stroke="currentColor" /><polyline :points="path" fill="none" stroke="var(--accent-cyan)" stroke-width="3" /><text x="20" y="155" fill="currentColor">0 seconds</text><text x="245" y="155" fill="currentColor">60 seconds</text><text x="20" y="15" fill="currentColor">{{ Math.round(maxBacklog) }} jobs</text></svg><p><strong>{{ queue.backlog.toLocaleString() }} jobs</strong> after 60 seconds.</p><p>{{ queue.growth > 0 ? `Backlog grows by ${queue.growth} jobs/s.` : queue.growth === 0 ? 'Equal rates keep existing backlog. They do not drain it.' : `Spare capacity drains ${-queue.growth} jobs/s.` }}</p><p>{{ queue.drainSeconds === null ? 'No sustained catch-up while these rates stay the same.' : `Drain time from that point: about ${queue.drainSeconds} seconds at these same rates.` }}</p></div>
      </div>
      <div v-else-if="lab === 'reservation' || lab === 'retry'">
        <label class="hld-label"><input v-model="safe" type="checkbox" /> {{ lab === 'reservation' ? 'Use an atomic check-and-reserve' : 'Reuse the same provider idempotency key and parameters' }}</label>
        <div class="hld-row"><button class="btn btn-primary" :disabled="step === 4" @click="step++">Next event · {{ step }}/4</button><button class="btn" @click="step = 0">Replay timeline</button><strong aria-live="polite">{{ lab === 'reservation' ? `${reservation.bookings} confirmed for 1 seat` : `${retry.effects} remote effects for 1 intent` }}</strong></div>
        <ol class="hld-lab-timeline" aria-live="polite"><li v-for="(event, i) in (lab === 'reservation' ? reservation.events : retry.events)" :key="i">{{ event }}</li></ol>
        <p v-if="step === 4" class="hld-memory-tip">{{ safe ? 'The mechanism protects this small example. Now name the transaction or provider boundary it depends on.' : 'A repeat or race broke the promise. Turn on the guard and replay the same timeline.' }}</p>
        <p v-if="lab === 'retry'" class="hld-muted">This model assumes the provider supports the key within its documented scope and retention. A local key alone cannot force a remote effect to deduplicate.</p>
      </div>
      <div v-else class="hld-lab-grid">
        <div><label class="hld-label"><input v-model="safe" type="checkbox" /> Cover every cell intersecting the circle</label><label class="hld-label">User horizontal position: {{ userX }}<input v-model.number="userX" type="range" min="25" max="175" /></label><label class="hld-label">Radius: {{ radius }} map units<input v-model.number="radius" type="range" min="10" max="70" /></label><p>Blue cells are searched. The circle is the requested area. Candidate places still need a distance check.</p></div>
        <div><svg viewBox="-8 -8 230 230" role="img" aria-label="Four map cells with the user radius and nearby places"><rect x="0" y="0" width="200" height="200" fill="var(--bg-secondary)" stroke="currentColor" /><rect v-for="c in geo.selected" :key="`${c.x}-${c.y}`" :x="c.x" :y="c.y" width="100" height="100" fill="var(--accent-cyan)" opacity=".15" /><path d="M100 0 V200 M0 100 H200" stroke="currentColor" fill="none" /><circle :cx="userX" cy="95" :r="radius" fill="none" stroke="var(--accent-cyan)" stroke-width="2" /><circle :cx="userX" cy="95" r="4" fill="var(--accent-cyan)" /><g v-for="p in GEO_PLACES" :key="p.id"><circle :cx="p.x" :cy="p.y" r="4" fill="currentColor" /><text :x="p.x + 6" :y="p.y - 3" fill="currentColor">{{ p.id }}</text></g></svg><p aria-live="polite">Candidates: {{ geo.candidates.map(p => p.id).join(', ') || 'none' }}. Distance matches: {{ geo.matches.map(p => p.id).join(', ') || 'none' }}. <strong>Missed: {{ geo.missed.map(p => p.id).join(', ') || 'none' }}.</strong></p></div>
      </div>
      <label class="hld-label">What changed your thinking?<textarea v-model="explanation" class="hld-input" rows="3" placeholder="The mechanism works because… It fails when…"></textarea></label>
      <button class="btn" :disabled="!explanation.trim() || saved" @click="remember">{{ saved ? 'Recall card saved for tomorrow' : 'Keep my explanation as a recall card' }}</button>
    </template>
  </section>
</template>
