<script setup lang="ts">
import { aiHeaders } from '../lib/aiConnection'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSoftware, useAILearnings } from '../composables/useSoftware'
import { softwareEvidence, validateSoftwareReport } from '../lib/softwareLearning'
import { WORK_FIELDS, type SoftwareAttempt } from '../types/software'
import LearningText from '../components/LearningText.vue'
import HLDMarkdown from '../components/HLDMarkdown.vue'
import HLDDiagram from '../components/HLDDiagram.vue'
import AIChatPanel from '../components/AIChatPanel.vue'
import SoftwareMechanismLab from '../components/SoftwareMechanismLab.vue'
import AILearningLab from '../components/AILearningLab.vue'
import '../styles/software.css'
const props = withDefaults(defineProps<{area?: 'software'|'ai'}>(),{area:'software'})
const isAI = props.area==='ai'
const basePath = isAI?'/ai':'/software'
const title = isAI?'AI Learnings':'Software Learnings'
const route = useRoute(); const router = useRouter()
const { course, error, load, state, draft: getDraft, completeStep, submit, submitQuiz, newDraft, progress, storageError } = (isAI?useAILearnings():useSoftware())
const module = computed(() => course.value?.modules.find(m=>m.id===route.params.id))
const mp = computed(() => module.value ? state(module.value.id) : null)
const tab = computed(() => ['learn','trace','lab','practice','quiz','references'].includes(String(route.query.tab)) ? String(route.query.tab) : 'learn')
const lab = computed(() => module.value?.lab ? course.value?.labs[module.value.lab] : undefined)
const selectedFile = ref('README.md')
const labFile = computed(() => lab.value?.files.find(f=>f.path===selectedFile.value) ?? lab.value?.files[0])
const tabs = computed(() => ['learn','trace',...(lab.value?['lab']:[]),'practice','quiz','references'])
const step = ref(0); const traceStep = ref(0)
const exerciseId = computed(() => String(route.query.exercise ?? 'repair'))
const exercise = computed(() => module.value?.exercises.find(e=>e.id===exerciseId.value) ?? module.value?.exercises[0])
const draft = computed(() => module.value && exercise.value ? getDraft(module.value.id,exercise.value.id) : null)
const selectedAttempt = ref('')
const attempts = computed(() => mp.value?.attempts.filter(a=>a.exerciseId===exercise.value?.id) ?? [])
const attempt = computed(() => attempts.value.find(a=>a.id===selectedAttempt.value) ?? attempts.value[attempts.value.length-1])
const showReference = ref(false); const message = ref(''); const evaluating = ref(false)
const quizIndex = ref(0)
const quizAnswered = computed(() => module.value?.questions.filter(q=>mp.value?.quizDraft[q.id]!==undefined).length ?? 0)
const quizQuestions = computed(() => module.value?.questions.filter((_q,i)=>module.value!.questions.length<=10 || mp.value?.quizSubmitted || i===quizIndex.value) ?? [])
const predictionChoice = ref<number | null>(null); const predictionReveal = ref(false)
const evidence = computed(() => module.value ? softwareEvidence(module.value,mp.value ?? undefined,Object.values(progress.value.cards)) : null)
const nextModule = computed(() => {
  const list=course.value?.modules ?? []
  return isAI ? list[list.findIndex(m=>m.id===module.value?.id)+1] : list.find(m=>m.prerequisite===module.value?.id)
})
const section = computed(() => module.value?.sections[step.value])
const lessonVisuals = computed(() => module.value?.visuals.filter(v=>v.placement===(step.value===module.value!.sections.length-1?'recap':'overview')) ?? [])
const coaching = computed(() => ({mode: (showReference.value ? 'review' : tab.value==='practice' ? 'practice' : 'learn') as 'learn'|'practice'|'review',exercise_id:exercise.value?.id,section_id:tab.value==='trace'?'trace':section.value?.id,file_path:tab.value==='lab'?labFile.value?.path:undefined,attempt:draft.value ?? undefined}))
watch(() => [route.params.id, exerciseId.value], () => { step.value=0;traceStep.value=0;quizIndex.value=0;selectedFile.value='README.md';showReference.value=false;selectedAttempt.value='';message.value='';predictionChoice.value=null;predictionReveal.value=false })
function switchTab(value: string) { showReference.value=false; message.value=''; router.replace({query:{...route.query,tab:value}}) }
function saveAttempt() { try { if (!module.value || !exercise.value) return; const a=submit(module.value,exercise.value.id);selectedAttempt.value=a.id;message.value='Attempt saved. You can now compare the reference or request feedback.' } catch(e) {message.value=(e as Error).message} }
function revealReference() { if (!attempt.value || !draft.value) return; draft.value.assisted=true;showReference.value=true }
function fresh() { if (!module.value || !exercise.value) return; mp.value!.drafts[exercise.value.id]=newDraft();showReference.value=false;message.value='Fresh draft started. Earlier snapshots are kept.' }
async function evaluate(a: SoftwareAttempt) {
  if (!module.value || !exercise.value || evaluating.value) return
  evaluating.value=true;message.value=''
  try {
    const base=(import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/,'')
    const response=await fetch(`${base}/api/${isAI?'ai-course':'software'}/evaluate`,{method:'POST',headers:aiHeaders(),body:JSON.stringify({module_id:module.value.id,exercise_id:exercise.value.id,attempt:{phases:a.phases,diagram:a.diagram,assisted:a.assisted}})})
    const data=await response.json().catch(() => null)
    if (!data) throw new Error('AI feedback is unavailable. Your saved attempt is kept. Check the backend and retry.')
    if (!response.ok) throw new Error(typeof data.detail==='string'?data.detail:'AI feedback is unavailable. Your attempt is saved.')
    a.report=validateSoftwareReport(data)
    if (draft.value) draft.value.assisted=true
  } catch(e) {message.value=e instanceof Error?e.message:'AI feedback is unavailable.'}
  finally {evaluating.value=false}
}
function quiz() { try { if(module.value)submitQuiz(module.value);message.value='' } catch(e) {message.value=(e as Error).message} }
function markAssisted() { if(draft.value)draft.value.assisted=true }
function lessonNext() { if(module.value && section.value){completeStep(module.value,section.value.id);if(step.value<module.value.sections.length-1)step.value++;else switchTab('trace')} }
function cleanLinks(content:string) { return content.replace(/\[([^\]]+)\]\((?!https?:|#)[^)]+\)/g,'$1 (see journal reference)') }
</script>
<template>
  <div class="container sw-page">
    <router-link class="sw-back" :to="`${basePath}?track=${module?.track ?? (isAI?'models':'ruby')}`">← {{ title }}</router-link>
    <p v-if="storageError" class="sw-alert" role="alert">{{ storageError }}</p>
    <div v-if="error" role="alert">{{ error }} <button class="btn" @click="load">Retry</button></div><p v-else-if="!course">Loading module…</p><section v-else-if="!module" class="sw-card"><h1>Module not found</h1><router-link :to="basePath">Choose a course module</router-link></section>
    <template v-else-if="mp && draft && exercise">
      <header class="sw-module-header"><p class="sw-eyebrow">{{ module.track }} · {{ module.level }} · Chapter {{ module.sequence }} · ~{{ module.hours }} hours with practice</p><h1>{{ module.title }}</h1><p class="sw-lead">{{ module.outcome }}</p><p class="sw-muted">{{ module.version }}</p><div class="sw-evidence"><span :class="{done:evidence?.lesson}">Lesson</span><span :class="{done:evidence?.practice}">Both attempts</span><span :class="{done:evidence?.quiz}">Quiz ≥75%</span><span :class="{done:evidence?.delayed}">Recall ≥7 days later</span></div><p v-if="module.prerequisite" class="sw-muted">Builds on <router-link :to="`${basePath}/${module.prerequisite}`">the previous module</router-link>. You can revisit it anytime.</p></header>
      <details v-if="module.useCase" class="sw-practical"><summary>Where this helps at work</summary><p>{{ module.useCase }}</p><p><strong>Benefit:</strong> {{ module.benefits }}</p><p><strong>Cost or limit:</strong> {{ module.drawbacks }}</p></details>
      <nav class="sw-tabs" aria-label="Module activities"><button v-for="item in tabs" :key="item" class="btn" :class="{selected:tab===item}" @click="switchTab(item)">{{ {learn:'1 · Learn',trace:'2 · Predict',lab:'Code lab',practice:'3 · Practice',quiz:'4 · Quiz',references:'References'}[item] }}</button></nav>
      <p v-if="message" class="sw-alert" role="status">{{ message }}</p>
      <template v-if="tab==='learn' && section">
        <nav class="sw-steps" aria-label="Lesson steps"><button v-for="(s,i) in module.sections" :key="s.id" :class="{selected:step===i}" @click="step=i">{{ mp.completed.includes(s.id)?'✓':i+1 }} · {{ s.title }}</button></nav>
        <div class="sw-learning-grid"><article class="sw-card"><p class="sw-eyebrow">Step {{ step+1 }} of {{ module.sections.length }}</p><div v-if="step===0" class="sw-lesson-hook"><span>The idea to keep</span><LearningText :text="module.cue"/></div><HLDMarkdown :content="section.content"/><div class="sw-row"><button class="btn btn-ghost" :disabled="step===0" @click="step--">Previous</button><button class="btn" @click="lessonNext">{{ step===module.sections.length-1?'Mark read · try a prediction':'Mark read · next step' }}</button></div></article><aside class="sw-aside"><HLDDiagram v-for="v in lessonVisuals" :key="v.placement" :title="v.title" :code="v.code"/><div class="sw-cue"><strong>Remember this</strong><p>{{ module.cue }}</p></div></aside></div>
      </template>
      <section v-else-if="tab==='trace'" class="sw-card">
        <h2>Predict, then follow the path</h2><p>This is a guided trace. It does not execute your code. Run the sandbox when you want to check real behavior.</p><div class="sw-steps"><button v-for="(t,i) in module.trace" :key="i" :class="{selected:traceStep===i}" @click="traceStep=i">{{ i+1 }} · {{ t.title }}</button></div><HLDMarkdown :content="module.trace[traceStep]!.detail"/><div class="sw-row"><button class="btn" :disabled="traceStep===0" @click="traceStep--">Back</button><button class="btn" :disabled="traceStep===(module?.trace.length ?? 0)-1" @click="traceStep++">Next trace step</button></div>
        <AILearningLab v-if="isAI" :module-id="module.id"/><SoftwareMechanismLab v-else :key="module.id" :module-id="module.id"/>
        <div class="sw-prediction"><p class="sw-eyebrow">Pause here</p><h3>{{ module.questions[1]!.prompt }}</h3><label v-for="(option,i) in module.questions[1]!.options" :key="i" class="sw-option"><input v-model="predictionChoice" type="radio" :value="i" :disabled="predictionReveal" name="prediction"/>{{ option }}</label><button class="btn" :disabled="predictionChoice===null || predictionReveal" @click="predictionReveal=true">Check my prediction</button><div v-if="predictionReveal" role="status"><h3>{{ predictionChoice===module.questions[1]!.correctIndex?'That matches.':'Try this explanation.' }}</h3><p>{{ module.questions[1]!.explanation }}</p><p>The quiz later checks this idea again. Try to explain it before recognizing an option.</p></div></div><button class="btn" @click="switchTab('practice')">Try the repair →</button>
      </section>
      <section v-else-if="tab==='lab' && lab" class="sw-card">
        <p class="sw-eyebrow">Read-only training files · run in your own local sandbox</p><h2>{{ lab.title }}</h2><p>{{ lab.version }}</p><p class="sw-muted">Journal folder: {{ lab.journalPath }}. Start with README, then follow the file map. The app shows the files; it does not run Docker, deploy AWS, or execute your code.</p>
        <div class="sw-file-browser"><nav aria-label="Lab files"><button v-for="file in lab.files" :key="file.path" class="btn" :class="{selected:labFile?.path===file.path}" :aria-pressed="labFile?.path===file.path" @click="selectedFile=file.path">{{ file.path }}</button></nav><article v-if="labFile" class="sw-file-content"><h3>{{ labFile.path }}</h3><HLDMarkdown v-if="labFile.path.endsWith('.md')" :content="cleanLinks(labFile.content)"/><HLDMarkdown v-else :content="'```'+labFile.language+'\n'+labFile.content+'\n```'"/></article></div>
        <p class="sw-cue">Predict a result before running a command. Record expected and actual results in your practice attempt.</p>
      </section>
      <template v-else-if="tab==='lab'"><section class="sw-card"><h2>This chapter uses guided examples</h2><p>Follow Learn and Predict, then try the separate practice. Chapters with runnable files show a Code lab tab.</p><button class="btn" @click="switchTab('learn')">Open the lesson</button></section></template>
      <template v-else-if="tab==='practice'">
        <label class="sw-label sw-select">Choose an exercise<select :value="exercise.id" @change="router.replace({query:{tab:'practice',exercise:($event.target as HTMLSelectElement).value}})"><option v-for="e in module.exercises" :key="e.id" :value="e.id">{{ e.title }} · {{ e.minutes }} min</option></select></label>
        <div class="sw-practice-grid"><article class="sw-card"><HLDMarkdown :content="exercise.prompt"/><p class="sw-cue">{{ draft.assisted?'This draft used help. That is useful practice.':'Try an unaided draft first.' }}</p></article><section class="sw-card"><h2>Your attempt</h2><label v-for="field in WORK_FIELDS" :key="field.id" class="sw-label">{{ field.title }}<textarea v-model="draft.phases[field.id]" :placeholder="field.prompt" rows="4" maxlength="6000"/></label><details><summary>Optional diagram · Mermaid or plain text</summary><textarea v-model="draft.diagram" rows="6" maxlength="8000" aria-label="Your diagram"/></details><label class="sw-checkbox"><input v-model="draft.assisted" type="checkbox"/>I used hints, a reference, or a previous answer.</label><div class="sw-row"><button class="btn" @click="saveAttempt">Save &amp; submit attempt</button><button class="btn btn-ghost" @click="fresh">Fresh draft</button></div><p class="sw-muted">Draft autosaves. Submission preserves a snapshot. Use a separate sandbox for execution.</p></section></div>
        <section v-if="attempt" class="sw-card sw-result"><h2>Compare and improve</h2><label class="sw-label">Saved snapshot<select :value="attempt.id" @change="selectedAttempt=($event.target as HTMLSelectElement).value"><option v-for="a in attempts" :key="a.id" :value="a.id">{{ new Date(a.createdAt).toLocaleString() }} · {{ a.assisted?'with help':'unaided' }}</option></select></label><details><summary>Read this saved attempt</summary><div v-for="field in WORK_FIELDS" :key="field.id"><h3>{{ field.title }}</h3><pre class="sw-plain">{{ attempt.phases[field.id] || 'No evidence written.' }}</pre></div><pre v-if="attempt.diagram" class="sw-plain">{{ attempt.diagram }}</pre></details><div class="sw-row"><button class="btn" @click="revealReference">Open reference answer</button><button class="btn" :disabled="evaluating" @click="evaluate(attempt)">{{ evaluating?'Reviewing saved snapshot…':'Ask AI to review this snapshot' }}</button></div><p class="sw-muted">AI compares this saved work with the course reference. It does not run your code. Scores are provisional, out of 3 for each area.</p><p class="sw-muted">Self-review: compare your prediction, repair, test evidence, and explanation. Write one missing check in your notes below.</p>
          <div v-if="attempt.report" class="sw-report"><h3>AI feedback · {{ attempt.report.dimensions.reduce((n,d)=>n+d.score,0) }}/12</h3><p>{{ attempt.report.summary }}</p><article v-for="d in attempt.report.dimensions" :key="d.id"><strong>{{ WORK_FIELDS.find(f=>f.id===d.id)?.title }} · {{ d.score }}/3</strong><p><b>Evidence:</b> {{ d.evidence }}</p><p>{{ d.feedback }}</p></article><p><strong>Next small step:</strong> {{ attempt.report.next_exercise }}</p></div>
          <article v-if="showReference" class="sw-reference"><p class="sw-eyebrow">One valid answer · compare the reasoning</p><HLDMarkdown :content="exercise.solution"/><HLDDiagram :title="module.visuals[1]!.title" :code="module.visuals[1]!.code"/></article>
        </section><section v-else class="sw-card"><p>Reference answers and AI scoring unlock after your first submission for this exercise.</p></section>
      </template>
      <section v-else-if="tab==='quiz'" class="sw-card"><h2>{{ module.questions.length>10?'Cumulative check · connect the course':'Check the idea' }}</h2><p>Answer all questions before checking. The guided prediction may look familiar; explain why the other options fail.</p><div v-if="module.questions.length>10 && !mp.quizSubmitted" class="sw-cumulative"><p role="status">{{ quizAnswered }}/{{ module.questions.length }} answered · answers stay hidden until you check the full quiz.</p><div class="sw-row"><button v-for="(q,i) in module.questions" :key="q.id" class="btn" :class="{selected:quizIndex===i}" :aria-label="`Question ${i+1}${mp.quizDraft[q.id]!==undefined?', answered':''}`" @click="quizIndex=i">{{ mp.quizDraft[q.id]!==undefined?'✓ ':'' }}{{ i+1 }}</button></div></div><fieldset v-for="q in quizQuestions" :key="q.id" class="sw-question"><legend>{{ module.questions.indexOf(q)+1 }}. {{ q.prompt }}</legend><label v-for="(option,i) in q.options" :key="i" class="sw-option"><input v-model="mp.quizDraft[q.id]" :disabled="mp.quizSubmitted" type="radio" :name="q.id" :value="i"/>{{ option }}</label><div v-if="mp.quizSubmitted" class="sw-answer"><strong>{{ mp.quizDraft[q.id]===q.correctIndex?'Correct':'Review this idea' }} · {{ q.options[q.correctIndex] }}</strong><p>{{ q.explanation }}</p></div></fieldset><div v-if="module.questions.length>10 && !mp.quizSubmitted" class="sw-row"><button class="btn" :disabled="quizIndex===0" @click="quizIndex--">Previous question</button><button class="btn" :disabled="quizIndex===module.questions.length-1" @click="quizIndex++">Next question</button></div><button v-if="!mp.quizSubmitted" class="btn" :disabled="quizAnswered!==module.questions.length" @click="quiz">Check all answers · {{ quizAnswered }}/{{ module.questions.length }}</button><template v-else><p class="sw-cue">Latest quiz: {{ mp.quizzes[mp.quizzes.length-1]?.score }}/{{ module.questions.length }}. Missed ideas return in spaced recall.</p><button class="btn" @click="mp.quizDraft={};mp.quizSubmitted=false">Try a fresh quiz</button></template><p class="sw-muted">A quiz checks recognition and reasoning. Practice and delayed recall provide separate evidence.</p></section>
      <section v-else-if="tab==='references'" class="sw-card"><h2>Go deeper when you need it</h2><p v-if="module.book">{{ module.book }}</p><p class="sw-muted">Journal folder: {{ module.journalPath }}. Existing longer notes are available below. Practice solutions stay in the Practice tab after submission.</p><details v-for="r in module.reading" :key="r.path"><summary>{{ r.title }}</summary><HLDMarkdown :content="cleanLinks(r.content)"/></details><h3>Official references</h3><ul><li v-for="source in module.sources" :key="source.url"><a :href="source.url" target="_blank" rel="noopener noreferrer">{{ source.title }}</a></li></ul><h3>Run a separate sandbox</h3><p v-if="isAI">The Code lab contains complete synthetic Rails files and offline checks. Start with its README. Code is displayed here; it runs in a separate training environment. Never run these training commands in a work project.</p><p v-else>Use the journal’s software-learnings/labs folder for Ruby, Git, and JavaScript. The Spring project lives in spring-boot/labs/task-service. Run training commands there. Chapters marked Code lab show the complete training files and setup. Other fragments illustrate a boundary; use a separate configured training app to run them.</p></section>
      <section class="sw-card sw-notes"><label class="sw-label">Your bug diary<textarea v-model="mp.notes" rows="3" placeholder="Symptom → cause → repair → regression check. Use synthetic examples only." /></label><p class="sw-muted">Saved in this browser. Export in Settings. Do not paste private work code, secrets, or real user data into notes or AI chat.</p></section><div class="sw-row sw-bottom"><router-link class="btn" :to="`${basePath}?tab=review`">Open recall queue</router-link><router-link v-if="nextModule" class="btn" :to="`${basePath}/${nextModule.id}`">Next · {{ nextModule.title }} →</router-link></div>
      <AIChatPanel :key="`${module.id}-${tab}-${exercise.id}-${showReference}-${selectedFile}`" :context-type="isAI?'ai-course':'software'" :context-id="module.id" :context-label="module.title" :learning-context="coaching" :quick-chips="tab==='practice' && !showReference?['Clarify the task without solving it','Ask me one useful question']:['Explain this with a tiny example','Follow the execution step by step','What can go wrong here?']" @message="markAssisted"/>
    </template>
  </div>
</template>
