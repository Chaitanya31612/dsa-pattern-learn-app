<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSoftware } from '../composables/useSoftware'
import { softwareEvidence } from '../lib/softwareLearning'
import HLDMarkdown from '../components/HLDMarkdown.vue'
import SoftwareBackup from '../components/SoftwareBackup.vue'
import '../styles/software.css'
const { course, error, load, progress, due, rate, storageError, refreshTime } = useSoftware()
const route = useRoute(); const router = useRouter()
const tab = computed(() => ['course','review','guide','backup'].includes(String(route.query.tab)) ? String(route.query.tab) : 'course')
const track = computed(() => course.value?.tracks.some(t => t.id===String(route.query.track)) ? String(route.query.track) : 'frontend')
const search = ref('')
const level = computed(() => ['beginner','intermediate'].includes(String(route.query.level)) ? String(route.query.level) : 'all')
const modules = computed(() => course.value?.modules.filter(m => m.track === track.value && (level.value==='all' || m.level===level.value) && `${m.title} ${m.outcome} ${m.tags.join(' ')}`.toLowerCase().includes(search.value.trim().toLowerCase())) ?? [])
const groups = computed(() => (['beginner','intermediate'] as const).map(id => ({id,modules:modules.value.filter(m=>m.level===id)})).filter(g=>g.modules.length))
const currentCard = computed(() => due.value[0])
const response = ref(''); const reveal = ref(false)
const guide = computed(() => course.value?.guide.replace(/\[([^\]]+)\]\((?!https?:)[^)]+\)/g,'$1') ?? '')
function chooseTrack(id: string) { search.value='';router.replace({query:{track:id}}) }
function changeTab(value: string) { router.replace({ query: { ...route.query, tab: value } }); refreshTime() }
function grade(rating: 'again' | 'hard' | 'good') {
  if (!currentCard.value || !response.value.trim()) return
  currentCard.value.lastResponse = response.value; rate(currentCard.value.id, rating); response.value = ''; reveal.value = false
}
function evidence(id: string) {
  const m = course.value!.modules.find(x => x.id === id)!
  return softwareEvidence(m, progress.value.modules[id], Object.values(progress.value.cards))
}
</script>
<template>
  <div class="container sw-page">
    <header class="sw-hero"><div><p class="sw-eyebrow">Learn by following what runs</p><h1>Software Learnings</h1><p class="sw-lead">Small steps. Real examples. Recall that lasts beyond today.</p><p>Beginner builds the model. Intermediate connects it to work. Start with frontend and UX for your current work, then follow one main track at a time.</p></div><div class="sw-hero-note"><strong>See → Predict → Do → Explain</strong><p>About 7 hours a week.<br>One honest attempt beats another reread.</p><button class="btn" @click="changeTab('review')">Recall · {{ due.length }} due</button></div></header>
    <p v-if="storageError" class="sw-alert" role="alert">{{ storageError }}</p>
    <nav class="sw-tabs" aria-label="Software learning area"><button v-for="item in ['course','review','guide','backup']" :key="item" class="btn" :class="{selected:tab===item}" @click="changeTab(item)">{{ {course:'Your tracks',review:'Spaced recall',guide:'How to learn',backup:'Backup'}[item] }}</button></nav>
    <div v-if="error" class="sw-card" role="alert">{{ error }} <button class="btn" @click="load">Retry</button></div><p v-else-if="!course" role="status">Loading your learning space…</p>
    <template v-else>
      <template v-if="tab==='course'">
        <div class="sw-tracks"><button v-for="t in course.tracks" :aria-pressed="track===t.id" :key="t.id" class="sw-track" :class="{selected:track===t.id}" @click="chooseTrack(t.id)"><span class="sw-eyebrow">{{ ['frontend','ux'].includes(t.id) ? 'Useful for your current work' : 'Practical track' }}</span><h2>{{ t.title }}</h2><small>{{ course.modules.filter(m=>m.track===t.id).length }} modules · ~{{ t.hours }} hours</small></button></div>
        <div class="sw-section-head"><div><h2>{{ course.tracks.find(t=>t.id===track)?.title }}</h2><p>{{ course.tracks.find(t=>t.id===track)?.description }}</p><p>{{ course.tracks.find(t=>t.id===track)?.version }}</p></div><span class="sw-muted">Lesson · Practice · Quiz · Delayed recall</span></div>
        <div class="sw-filters"><label class="sw-label">Find a chapter<input v-model="search" type="search" placeholder="Search this track…"/></label><label class="sw-label">Learning level<select :value="level" @change="router.replace({query:{...route.query,level:($event.target as HTMLSelectElement).value}})"><option value="all">Beginner + Intermediate</option><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option></select></label></div>
        <p class="sw-muted" role="status">{{ modules.length }} chapters shown. Choose a chapter to see its example, diagrams, practice, and quiz.</p>
        <section v-for="group in groups" :key="group.id" class="sw-level-group"><h2>{{ group.id==='beginner'?'Beginner · build a clear mental model':'Intermediate · handle real constraints' }}</h2><p class="sw-muted">{{ group.id==='beginner'?'Explain the core path. Predict a simple change.':'Trace a failure. Make a tradeoff. Verify a repair.' }}</p><div class="sw-module-list"><router-link v-for="m in group.modules" :key="m.id" :to="`/software/${m.id}`" class="sw-module-card"><span class="sw-number">{{ String(m.sequence).padStart(2,'0') }}</span><div><span class="sw-level">{{ m.level }}{{ m.lab ? ' · code lab' : '' }}</span><h3>{{ m.title }}</h3><p>{{ m.outcome }}</p><div class="sw-evidence"><span :class="{done:evidence(m.id).lesson}">Read</span><span :class="{done:evidence(m.id).practice}">Tried</span><span :class="{done:evidence(m.id).quiz}">Quiz</span><span :class="{done:evidence(m.id).delayed}">Recalled later</span></div></div><div class="sw-module-tail"><strong>{{ evidence(m.id).complete ? 'Consolidated' : `${evidence(m.id).count}/4 checks` }}</strong><small>~{{ m.hours }} hours →</small></div></router-link></div></section><p v-if="!modules.length" class="sw-card">No chapters match. Try a shorter search or another level.</p>
        <p class="sw-muted">Checks record practice and recall. They do not certify mastery. Open “How to learn” for hands-on completion gates and the weekly routine.</p>
      </template>
      <section v-else-if="tab==='review'" class="sw-card">
        <h2>Recall before rereading</h2><p>Explain the answer from memory. Then compare. Choose Again if you needed the answer, Hard if it was shaky, or Good if you explained it clearly.</p>
        <template v-if="currentCard"><p class="sw-eyebrow">{{ course.modules.find(m=>m.id===currentCard?.moduleId)?.title }} · {{ due.length }} due</p><h3>{{ currentCard.question }}</h3><label class="sw-label">Your recall<textarea v-model="response" rows="5" placeholder="Use a concrete example. What can go wrong?" /></label><button class="btn" :disabled="!response.trim()" @click="reveal=true">Compare my recall</button><template v-if="reveal"><HLDMarkdown :content="currentCard.answer"/><div class="sw-row"><button class="btn" @click="grade('again')">Again · 10 min</button><button class="btn" @click="grade('hard')">Hard · 1 day</button><button class="btn" @click="grade('good')">Good · longer gap</button></div></template></template>
        <template v-else><h3>You have no recall due right now.</h3><p>Finish a lesson step or submit practice to schedule the first recall for tomorrow. Missed quiz ideas are added too.</p><p v-if="Object.keys(progress.cards).length">Next recall: {{ new Date(Math.min(...Object.values(progress.cards).map(c=>c.dueAt))).toLocaleString() }}</p><button class="btn" @click="changeTab('course')">Continue a module</button></template>
      </section>
      <section v-else-if="tab==='guide'" class="sw-card"><HLDMarkdown :content="guide"/><details><summary>Version notes and book reading map</summary><HLDMarkdown :content="course.versions"/></details></section>
      <SoftwareBackup v-else-if="tab==='backup'"/>
    </template>
  </div>
</template>
