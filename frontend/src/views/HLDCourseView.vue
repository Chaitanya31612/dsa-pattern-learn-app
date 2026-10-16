<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useHLD } from '../composables/useHLD'
import { moduleEvidence, DAY } from '../lib/hldLearning'
import HLDReviewQueue from '../components/HLDReviewQueue.vue'
import HLDMarkdown from '../components/HLDMarkdown.vue'
import HLDBackup from '../components/HLDBackup.vue'
import HLDHowTo from '../components/HLDHowTo.vue'
import HLDMechanismLab from '../components/HLDMechanismLab.vue'
import type { HLDModule } from '../types/hld'
const { course, loading, error, loadCourse, state, dueCards, storageError, addCard } = useHLD()
const route = useRoute()
const router = useRouter()
const views = ['course', 'review', 'labs', 'method'] as const
const active = computed({ get: () => views.includes(route.query.tab as typeof views[number]) ? route.query.tab as typeof views[number] : 'course',
  set: value => { void router.replace({ query: { ...route.query, tab: value } }) } })
const track = computed({ get: () => route.query.track === 'volume-2' ? 'volume-2' : 'volume-1',
  set: value => { void router.replace({ query: { ...route.query, track: value } }) } })
const filter = ref('')
const modules = computed(() => course.value?.modules ?? [])
const trackModules = computed(() => modules.value.filter(m => m.track === track.value))
const filtered = computed(() => trackModules.value.filter(m => `${m.title} ${m.outcome} ${m.book}`.toLowerCase().includes(filter.value.toLowerCase())))
watch(track, () => { filter.value = '' })
const sectionsRead = computed(() => modules.value.reduce((n,m) => n + (state.modules[m.id]?.completedSections.filter(id => m.sections.some(s => s.id === id)).length ?? 0), 0))
const totalSections = computed(() => modules.value.reduce((n,m) => n + m.sections.length, 0))
const attempts = computed(() => Object.values(state.modules).reduce((n,m) => n + m.attempts.length, 0))
const quizCorrect = computed(() => Object.values(state.modules).reduce((n,m) => n + (m.quizAttempts[m.quizAttempts.length - 1]?.score ?? 0), 0))
const quizTotal = computed(() => Object.values(state.modules).reduce((n,m) => n + (m.quizAttempts[m.quizAttempts.length - 1]?.total ?? 0), 0))
const evidence = (m: HLDModule) => moduleEvidence(m, state.modules[m.id], Object.values(state.cards))
const practiced = computed(() => trackModules.value.filter(m => { const e = evidence(m); return e.design && e.transfer && e.repair }).length)
const independent = computed(() => trackModules.value.filter(m => evidence(m).independent).length)
const delayed = computed(() => trackModules.value.filter(m => evidence(m).delayed).length)
const resume = computed(() => trackModules.value.find(m => { const e = evidence(m); return !(e.lesson && e.design && e.transfer && e.repair && e.quiz) }) ?? trackModules.value[trackModules.value.length - 1])
const nextAction = computed(() => {
  const m = resume.value
  if (!m) return null
  const e = evidence(m)
  if (!e.lesson) return { label: 'Learn the next idea', to: `/hld/${m.id}` }
  for (const kind of ['design','transfer','repair'] as const) {
    if (!e[kind]) return { label: kind === 'design' ? 'Try your design' : kind === 'transfer' ? 'Try a changed requirement' : 'Repair a broken design', to: `/hld/${m.id}?tab=practice&exercise=${m.exercises.find(x => x.kind === kind)?.id}` }
  }
  return { label: e.quiz ? 'Revisit the final assessment' : 'Check the key decisions', to: `/hld/${m.id}?tab=${e.quiz ? 'practice' : 'quiz'}` }
})
function status(m: HLDModule) {
  const e = evidence(m)
  if (e.complete) return 'Evidence collected · provisional'
  if (e.independent) return 'Independent attempt reviewed'
  if (e.design && e.transfer && e.repair) return 'All practice types tried'
  if (e.design) return 'Design submitted'
  return e.lesson ? 'Ready to practice' : state.modules[m.id]?.completedSections.length ? 'Learning' : 'Start here'
}
function remember(question: string, answer: string) {
  const ids = { 'Can a queue catch up when arrivals stay above processing capacity?': '20-message-queue', 'Can two buyers safely reserve the last seat after separate reads?': '23-reservations', 'What happens when a successful remote effect loses its reply?': '27-payments', 'Why does a nearby search need cells across the border?': '17-proximity' }
  const moduleId = ids[question as keyof typeof ids] ?? '00-design-framework'
  addCard({ id: `${moduleId}:decision:${crypto.randomUUID()}`, moduleId, kind: 'decision', question, answer, dueAt: Date.now() + DAY })
}
</script>
<template>
  <div class="container hld-page">
    <div class="hld-row"><router-link to="/system-design/lld">← LLD track</router-link><span class="hld-eyebrow">SYSTEM DESIGN / HLD</span></div>
    <header class="hld-hero">
      <div><p class="hld-eyebrow">Your architecture practice space</p><h1>Build designs you can explain.</h1><p>Two volumes. One steady framework. Learn with short examples and pictures. Try a design, get feedback, then explain it again after a delay.</p>
        <div class="hld-row"><router-link v-if="nextAction" class="btn btn-primary" :to="nextAction.to">{{ nextAction.label }} →</router-link><button class="btn" @click="active = 'review'">Review {{ dueCards.length }} due</button></div><p v-if="resume" class="hld-muted">Next in {{ track === 'volume-1' ? 'Volume 1' : 'Volume 2' }}: {{ resume.title }}</p></div>
      <div class="hld-hero-aside"><span class="hld-eyebrow">The structure to remember</span><p class="hld-framework">Contract → Size → Model → Flow → Stress → Operate → Explain</p><p class="hld-muted">{{ modules.length }} modules · {{ modules.reduce((n,m) => n + m.questions.length,0) }} questions · {{ modules.reduce((n,m) => n + m.hours,0) }} planned hours</p></div>
    </header>
    <HLDHowTo />
    <p v-if="storageError" class="hld-error" role="alert">{{ storageError }}</p>
    <div class="hld-stats"><div><strong>{{ sectionsRead }}<small>/{{ totalSections }}</small></strong><span>lesson steps explored</span></div><div><strong>{{ attempts }}</strong><span>design attempts saved</span></div><div><strong>{{ quizCorrect }}<small>/{{ quizTotal }}</small></strong><span>latest quiz answers correct</span></div><div><strong>{{ dueCards.length }}</strong><span>recall cards due</span></div></div>
    <nav class="hld-tabs" aria-label="HLD course views"><button v-for="t in views" :key="t" :class="{ selected: active === t }" :aria-pressed="active === t" @click="active = t">{{ t === 'course' ? 'Course map' : t === 'review' ? 'Spaced recall' : t === 'labs' ? 'Visual labs' : 'Learning method' }}</button></nav>
    <p v-if="loading" role="status">Loading your course…</p>
    <div v-else-if="error" role="alert"><p>{{ error }}</p><button class="btn" @click="loadCourse">Retry loading</button></div>
    <template v-else-if="course">
      <section v-if="active === 'course'">
        <nav class="hld-track-picker" aria-label="Choose a volume"><button v-for="t in course.tracks" :key="t.id" :aria-pressed="track === t.id" :class="{ selected: track === t.id }" @click="track = t.id"><strong>{{ t.title }}</strong><span>{{ t.description }}</span></button></nav>
        <div class="hld-track-evidence"><strong>Your evidence in this volume</strong><p>{{ practiced }}/{{ trackModules.length }} modules: all three practice types tried · {{ independent }}: unaided design reviewed · {{ delayed }}: delayed design recall.</p><p class="hld-muted">Reading alone does not finish a module. Open “Your learning evidence” inside a module to see the checks. Scores and self-rated recall are provisional.</p></div>
        <div class="hld-row"><h2>{{ track === 'volume-1' ? 'Build the foundations' : 'Apply the ideas to deeper systems' }}</h2><label class="hld-search">Find a module<input v-model="filter" class="hld-input" placeholder="caching, payments, maps…" /></label></div>
        <div class="hld-module-grid"><router-link v-for="m in filtered" :key="m.id" :to="`/hld/${m.id}`" class="hld-module-card">
          <div class="hld-row"><span class="hld-eyebrow">{{ String(m.number).padStart(2,'0') }} / {{ m.hours }}h</span><span class="hld-status">{{ status(m) }}</span></div><h3>{{ m.title }}</h3><p>{{ m.outcome }}</p>
          <div class="hld-progress" role="progressbar" :aria-label="`${m.title} lesson progress`" :aria-valuenow="state.modules[m.id]?.completedSections.length ?? 0" :aria-valuemin="0" :aria-valuemax="m.sections.length"><span :style="{ width: `${100 * (state.modules[m.id]?.completedSections.length ?? 0) / m.sections.length}%` }"></span></div>
          <span class="hld-muted">{{ m.sections.length }} short steps · {{ m.exercises.length }} exercises · {{ m.questions.length }} questions · evidence {{ evidence(m).count }}/7</span>
        </router-link></div><p v-if="!filtered.length">No modules match that search in this volume.</p>
      </section>
      <HLDReviewQueue v-else-if="active === 'review'" />
      <HLDMechanismLab v-else-if="active === 'labs'" @remember="remember" />
      <section v-else><HLDMarkdown :content="course.materials.protocol ?? ''" /><details><summary>Assessment rubric</summary><HLDMarkdown :content="course.materials.rubric ?? ''" /></details><details><summary>Course sources</summary><HLDMarkdown :content="course.materials.sources ?? ''" /></details></section>
    </template>
    <footer class="hld-course-footer"><p class="hld-muted">Progress, drafts, scores, and review dates are saved in this browser. Export a backup to move devices or preserve your work.</p><HLDBackup /></footer>
  </div>
</template>
