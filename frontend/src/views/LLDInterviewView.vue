<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLLDInterview, registerMergedProblems } from '../composables/useLLDInterview'
import { useLLDProblems } from '../composables/useLLDProblems'
import type { LLDPhaseId } from '../types'

const route = useRoute()
const router = useRouter()
const { getProblem, problems } = useLLDProblems()

// Bridge the JSON-loaded merged catalog into useLLDInterview's module-level cache.
// This runs once JSON finishes loading and on every subsequent update.
watch(problems, (merged) => {
  if (merged.length) registerMergedProblems(merged)
}, { immediate: true })
const {
  activeSession,
  currentProblem,
  isResponding,
  lastSavedAt,
  frameworkPhases,
  timeRemainingLabel,
  phaseProgress,
  contextDigest,
  startSession,
  restartSession,
  setActivePhase,
  updatePhaseNotes,
  toggleCheckpoint,
  updateCode,
  flushCodeSave,
  togglePause,
  sendMessage,
  submitSession,
} = useLLDInterview()

const chatInput = ref('')
const codeArea = ref<HTMLTextAreaElement | null>(null)

const routeProblem = computed(() => getProblem(String(route.params.id ?? '')))
const targetMode = computed<'guided' | 'interview'>(() => {
  return route.query.mode === 'guided' ? 'guided' : 'interview'
})

const phaseNotes = computed({
  get() {
    if (!activeSession.value) return ''
    return activeSession.value.phaseWork[activeSession.value.activePhase].notes
  },
  set(value: string) {
    if (!activeSession.value) return
    updatePhaseNotes(activeSession.value.activePhase, value)
  },
})

const phaseMeta = computed(() => {
  if (!activeSession.value) return frameworkPhases[0]
  return frameworkPhases.find(phase => phase.id === activeSession.value?.activePhase) ?? frameworkPhases[0]!
})
const phaseTitle = computed(() => phaseMeta.value?.title ?? 'Clarify')
const phaseTimebox = computed(() => phaseMeta.value?.timebox ?? '05-08 min')
const phaseFocus = computed(() => phaseMeta.value?.focus ?? '')
const phaseDeliverable = computed(() => phaseMeta.value?.deliverable ?? '')
const phaseCoachPrompt = computed(() => phaseMeta.value?.coachingPrompt ?? '')

const phaseHints = computed(() => {
  if (!currentProblem.value || !activeSession.value) return []
  return currentProblem.value.guided.phase_hints[activeSession.value.activePhase]
})

const checkpointItems = computed(() => {
  if (!currentProblem.value) return []
  return currentProblem.value.guided.checkpoints
})

const activePhaseChecklist = computed(() => {
  if (!activeSession.value) return []
  return activeSession.value.phaseWork[activeSession.value.activePhase].checkpoints
})

const codeValue = computed({
  get() {
    return activeSession.value?.code ?? ''
  },
  set(value: string) {
    updateCode(value)
  },
})

const savedLabel = computed(() => {
  if (!lastSavedAt.value) return 'Not saved yet'
  return `saved ${new Date(lastSavedAt.value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
})

function ensureSession() {
  if (!routeProblem.value) return
  if (
    !activeSession.value ||
    activeSession.value.problemId !== routeProblem.value.id ||
    activeSession.value.mode !== targetMode.value
  ) {
    startSession(routeProblem.value.id, targetMode.value)
  }
}

onMounted(() => {
  ensureSession()
})

watch([routeProblem, targetMode], () => {
  ensureSession()
})

function isChecked(item: string): boolean {
  return activePhaseChecklist.value.includes(item)
}

function toggleChecklist(item: string) {
  if (!activeSession.value) return
  toggleCheckpoint(activeSession.value.activePhase, item)
}

function onCodeKeydown(event: KeyboardEvent) {
  if (event.key !== 'Tab') return
  event.preventDefault()
  const element = codeArea.value
  if (!element) return
  const start = element.selectionStart
  const end = element.selectionEnd
  const current = codeValue.value
  codeValue.value = `${current.slice(0, start)}    ${current.slice(end)}`
  requestAnimationFrame(() => {
    element.selectionStart = element.selectionEnd = start + 4
  })
}

async function handleSend() {
  const text = chatInput.value.trim()
  if (!text) return
  chatInput.value = ''
  await sendMessage(text)
}

function handlePhaseSwitch(phaseId: LLDPhaseId) {
  setActivePhase(phaseId)
}

function handleSubmit() {
  submitSession()
}

function handleRestart() {
  restartSession(targetMode.value)
}
</script>

<template>
  <div v-if="routeProblem && activeSession && currentProblem" class="container lld-session-page">
    <section class="session-header animate-in">
      <div>
        <router-link :to="{ name: 'lld-framework', params: { id: currentProblem.id } }" class="crumb mono">
          ← framework
        </router-link>
        <p class="terminal-prompt">lld.session / {{ currentProblem.id }}</p>
        <h1>{{ currentProblem.title }}</h1>
        <p class="session-description">{{ currentProblem.description }}</p>
      </div>

      <div class="header-actions">
        <div class="timer-card card">
          <span class="meta-label mono">time.remaining</span>
          <strong>{{ timeRemainingLabel }}</strong>
          <span class="timer-mode">{{ activeSession.mode === 'guided' ? 'Guided coaching' : 'Interview coaching' }}</span>
        </div>
        <div class="timer-card card compact-card">
          <span class="meta-label mono">phase.progress</span>
          <strong>{{ phaseProgress }}%</strong>
          <span class="timer-mode">{{ phaseTitle }}</span>
        </div>
        <button class="btn" @click="togglePause">
          {{ activeSession.paused ? 'Resume' : 'Pause' }}
        </button>
        <button class="btn btn-primary" @click="handleSubmit">Submit Interview</button>
      </div>
    </section>

    <section class="phase-nav animate-in stagger-2">
      <button
        v-for="phase in frameworkPhases"
        :key="phase.id"
        class="phase-nav-btn"
        :class="{ active: activeSession.activePhase === phase.id }"
        @click="handlePhaseSwitch(phase.id)"
      >
        <span class="mono phase-nav-time">{{ phase.timebox }}</span>
        <strong>{{ phase.title }}</strong>
        <small>{{ phase.deliverable }}</small>
      </button>
    </section>

    <section v-if="activeSession.report" class="report-strip animate-in stagger-3">
      <article class="card report-card score-card">
        <span class="meta-label mono">debrief.score</span>
        <strong>{{ activeSession.report.overallScore }}/100</strong>
        <p>{{ activeSession.report.summary }}</p>
      </article>
      <article class="card report-card">
        <span class="meta-label mono">strengths</span>
        <ul>
          <li v-for="item in activeSession.report.strengths" :key="item">{{ item }}</li>
        </ul>
      </article>
      <article class="card report-card">
        <span class="meta-label mono">improvements</span>
        <ul>
          <li v-for="item in activeSession.report.improvements" :key="item">{{ item }}</li>
        </ul>
      </article>
      <article class="card report-card">
        <span class="meta-label mono">phase.scores</span>
        <div class="phase-score-grid">
          <div v-for="phase in frameworkPhases" :key="phase.id" class="phase-score">
            <span>{{ phase.title }}</span>
            <strong>{{ activeSession.report.phaseScores[phase.id] }}</strong>
          </div>
        </div>
        <button class="btn" @click="handleRestart">Restart Session</button>
      </article>
    </section>

    <section class="workspace-grid animate-in stagger-4">
      <aside class="left-rail">
        <article class="card focus-card">
          <div class="section-head">
            <span class="section-label terminal-prompt">current.phase</span>
            <span class="badge badge-source">{{ phaseTimebox }}</span>
          </div>
          <h2>{{ phaseTitle }}</h2>
          <p>{{ phaseFocus }}</p>
          <div class="rail-block">
            <strong>Deliverable</strong>
            <p>{{ phaseDeliverable }}</p>
          </div>
          <div class="rail-block">
            <strong>Coach prompt</strong>
            <p>{{ phaseCoachPrompt }}</p>
          </div>
        </article>

        <article class="card problem-card">
          <div class="section-head">
            <span class="section-label terminal-prompt">problem.brief</span>
          </div>
          <p class="problem-summary">{{ currentProblem.description }}</p>
          <div class="rail-block">
            <strong>Must have</strong>
            <ul>
              <li v-for="item in currentProblem.framework.requirements.must_have" :key="item">{{ item }}</li>
            </ul>
          </div>
          <div class="rail-block">
            <strong>Patterns</strong>
            <ul>
              <li v-for="pattern in currentProblem.framework.design_patterns" :key="pattern.name + pattern.applied_to">
                {{ pattern.name }} · {{ pattern.applied_to }}
              </li>
            </ul>
          </div>
        </article>
      </aside>

      <div class="main-rail">
        <article class="card notes-card">
          <div class="section-head">
            <span class="section-label terminal-prompt">phase.workspace</span>
            <span class="badge badge-source">{{ activeSession.mode }}</span>
          </div>
          <textarea v-model="phaseNotes" class="phase-textarea" spellcheck="false"></textarea>

          <template v-if="activeSession.mode === 'guided'">
            <div class="guided-grid">
              <div class="prompt-box">
                <h3>Hints</h3>
                <ul>
                  <li v-for="hint in phaseHints" :key="hint">{{ hint }}</li>
                </ul>
              </div>
              <div class="prompt-box">
                <h3>Checkpoints</h3>
                <label v-for="item in checkpointItems" :key="item" class="checkpoint-row">
                  <input type="checkbox" :checked="isChecked(item)" @change="toggleChecklist(item)" />
                  <span>{{ item }}</span>
                </label>
              </div>
            </div>
          </template>
          <template v-else>
            <div class="prompt-box minimal-box">
              <h3>Interview pressure note</h3>
              <p>
                Guardrails are intentionally reduced. Use the phase title to keep your structure,
                but drive the answer yourself before asking for help.
              </p>
            </div>
          </template>
        </article>

        <article class="card editor-card">
          <div class="section-head editor-head">
            <div>
              <span class="section-label terminal-prompt">code.workspace</span>
              <h2>Java workspace</h2>
            </div>
            <div class="editor-actions">
              <span class="mono save-label">{{ savedLabel }}</span>
              <button class="btn" @click="flushCodeSave">Save Code</button>
            </div>
          </div>
          <textarea
            ref="codeArea"
            v-model="codeValue"
            class="code-editor"
            spellcheck="false"
            @keydown="onCodeKeydown"
          ></textarea>
        </article>
      </div>

      <aside class="right-rail">
        <article class="card digest-card">
          <div class="section-head">
            <span class="section-label terminal-prompt">smart.context</span>
          </div>
          <template v-if="contextDigest">
            <div class="digest-row">
              <span class="meta-label mono">active phase</span>
              <strong>{{ contextDigest.activePhaseTitle }}</strong>
            </div>
            <div class="digest-row">
              <span class="meta-label mono">filled phases</span>
              <strong>{{ contextDigest.filledPhases.join(', ') || 'none yet' }}</strong>
            </div>
            <div class="digest-row">
              <span class="meta-label mono">code types</span>
              <strong>{{ contextDigest.codeTypes.join(', ') || 'not named yet' }}</strong>
            </div>
            <div class="digest-row">
              <span class="meta-label mono">code lines</span>
              <strong>{{ contextDigest.codeLines }}</strong>
            </div>
            <div class="digest-summary">
              <span class="meta-label mono">note summary</span>
              <p>{{ contextDigest.noteSummary }}</p>
            </div>
          </template>
        </article>

        <article class="card chat-card">
          <div class="section-head">
            <span class="section-label terminal-prompt">ai.interviewer</span>
            <span class="badge" :class="activeSession.mode === 'guided' ? 'badge-easy' : 'badge-medium'">
              {{ activeSession.mode === 'guided' ? 'Helpful' : 'Pressure' }}
            </span>
          </div>
          <div class="chat-thread">
            <div
              v-for="(message, index) in activeSession.chat"
              :key="`${message.ts}-${index}`"
              class="chat-bubble"
              :class="message.role"
            >
              <span class="chat-role mono">{{ message.role === 'assistant' ? 'coach' : 'you' }}</span>
              <p>{{ message.content }}</p>
            </div>
            <div v-if="isResponding" class="chat-bubble assistant typing-state">
              <span class="chat-role mono">coach</span>
              <p>thinking through your latest design state...</p>
            </div>
          </div>
          <div class="chat-input-row">
            <textarea
              v-model="chatInput"
              class="chat-input"
              placeholder="Ask for a requirement nudge, modeling check, design review, or implementation critique..."
              @keydown.enter.exact.prevent="handleSend"
            ></textarea>
            <button class="btn btn-primary" @click="handleSend">Send</button>
          </div>
        </article>
      </aside>
    </section>
  </div>

  <div v-else class="container not-found">
    <div class="card">
      <p class="terminal-prompt">lld.session.not_found</p>
      <button class="btn" @click="router.push('/system-design/lld')">Back to catalog</button>
    </div>
  </div>
</template>

<style scoped>
.lld-session-page {
  display: grid;
  gap: var(--space-lg);
}

.session-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-lg);
  align-items: start;
}

.crumb {
  display: inline-block;
  margin-bottom: var(--space-md);
  color: var(--text-muted);
}

.session-header h1 {
  font-size: clamp(2.1rem, 3vw, 3rem);
  margin-bottom: 6px;
}

.session-description {
  color: var(--text-secondary);
  max-width: 66ch;
}

.header-actions {
  display: flex;
  gap: var(--space-sm);
  align-items: stretch;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.timer-card {
  min-width: 150px;
  display: grid;
  gap: 6px;
}

.compact-card {
  min-width: 130px;
}

.meta-label {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.timer-card strong {
  font-size: 1.8rem;
  font-family: var(--font-display);
  line-height: 1;
}

.timer-mode {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.phase-nav {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--space-sm);
}

.phase-nav-btn {
  display: grid;
  gap: 6px;
  padding: var(--space-md);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  background: var(--bg-card);
  color: var(--text-secondary);
  text-align: left;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.phase-nav-btn:hover,
.phase-nav-btn.active {
  border-color: color-mix(in srgb, var(--accent-cyan) 28%, transparent);
  background: color-mix(in srgb, var(--bg-card-hover) 82%, transparent);
  color: var(--text-primary);
  box-shadow: var(--glow-cyan);
}

.phase-nav-time {
  color: var(--accent-cyan);
  font-size: 0.72rem;
}

.phase-nav-btn small {
  color: var(--text-muted);
}

.report-strip {
  display: grid;
  grid-template-columns: 1.1fr 1fr 1fr 1fr;
  gap: var(--space-md);
}

.report-card {
  display: grid;
  gap: var(--space-sm);
}

.report-card ul {
  padding-left: 1rem;
  display: grid;
  gap: 8px;
  color: var(--text-secondary);
}

.score-card strong {
  font-size: 2.4rem;
  font-family: var(--font-display);
  line-height: 1;
}

.score-card p {
  color: var(--text-secondary);
}

.phase-score-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-sm);
}

.phase-score {
  padding: 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
  background: color-mix(in srgb, var(--bg-secondary) 70%, transparent);
}

.phase-score span {
  display: block;
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.workspace-grid {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr) 340px;
  gap: var(--space-lg);
  align-items: start;
}

.left-rail,
.main-rail,
.right-rail {
  display: grid;
  gap: var(--space-lg);
}

.focus-card,
.problem-card,
.notes-card,
.editor-card,
.digest-card,
.chat-card {
  display: grid;
  gap: var(--space-md);
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-md);
}

.section-label {
  color: var(--text-muted);
}

.rail-block {
  display: grid;
  gap: 6px;
}

.focus-card p,
.problem-summary,
.rail-block p,
.rail-block ul,
.digest-summary p {
  color: var(--text-secondary);
}

.rail-block ul {
  padding-left: 1rem;
  display: grid;
  gap: 8px;
}

.phase-textarea,
.code-editor,
.chat-input {
  width: 100%;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--bg-input);
  color: var(--text-primary);
  font-family: var(--font-mono);
  resize: vertical;
}

.phase-textarea {
  min-height: 250px;
  padding: 16px;
  line-height: 1.6;
}

.guided-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-md);
}

.prompt-box {
  padding: var(--space-md);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  background: color-mix(in srgb, var(--bg-secondary) 70%, transparent);
}

.prompt-box h3 {
  margin-bottom: var(--space-sm);
  font-size: var(--text-base);
}

.prompt-box ul {
  padding-left: 1rem;
  display: grid;
  gap: 8px;
  color: var(--text-secondary);
}

.checkpoint-row {
  display: flex;
  align-items: flex-start;
  gap: var(--space-sm);
  color: var(--text-secondary);
  margin-bottom: 10px;
}

.minimal-box p {
  color: var(--text-secondary);
}

.editor-head {
  align-items: end;
}

.editor-head h2 {
  margin-top: 4px;
}

.editor-actions {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.save-label {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.code-editor {
  min-height: 440px;
  padding: 18px;
  line-height: 1.65;
}

.digest-row {
  display: flex;
  justify-content: space-between;
  gap: var(--space-md);
  align-items: start;
}

.digest-row strong {
  text-align: right;
}

.digest-summary {
  padding-top: var(--space-sm);
  border-top: 1px solid var(--border-subtle);
}

.chat-thread {
  display: grid;
  gap: var(--space-sm);
  max-height: 560px;
  overflow-y: auto;
  padding-right: 4px;
}

.chat-bubble {
  display: grid;
  gap: 6px;
  padding: var(--space-md);
  border-radius: var(--radius-md);
}

.chat-bubble.assistant {
  background: color-mix(in srgb, var(--accent-cyan) 8%, var(--bg-card));
  border: 1px solid color-mix(in srgb, var(--accent-cyan) 20%, transparent);
}

.chat-bubble.user {
  background: color-mix(in srgb, var(--accent-purple) 8%, var(--bg-card));
  border: 1px solid color-mix(in srgb, var(--accent-purple) 20%, transparent);
}

.chat-role {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.chat-bubble p {
  white-space: pre-wrap;
  color: var(--text-primary);
}

.typing-state p {
  color: var(--text-secondary);
}

.chat-input-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-sm);
  align-items: end;
}

.chat-input {
  min-height: 92px;
  padding: 14px;
  line-height: 1.6;
}

.not-found {
  min-height: 50vh;
  display: grid;
  place-items: center;
}

@media (max-width: 1320px) {
  .workspace-grid {
    grid-template-columns: 1fr;
  }

  .left-rail,
  .main-rail,
  .right-rail {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1180px) {
  .session-header,
  .report-strip,
  .guided-grid,
  .chat-input-row,
  .phase-nav {
    grid-template-columns: 1fr;
  }

  .header-actions {
    justify-content: start;
  }
}
</style>
