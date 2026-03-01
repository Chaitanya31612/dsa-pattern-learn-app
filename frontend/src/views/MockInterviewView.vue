<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { usePatterns } from '../composables/usePatterns'
import { useMockInterview } from '../composables/useMockInterview'

const {
  activeSession,
  currentProblem,
  currentProblemState,
  canStartSession,
  featureFlags,
  timeRemainingLabel,
  defaultConfig,
  startSession,
  updateCode,
  addThought,
  sendMessage,
  requestHint,
  submitAndContinue,
  endInterviewEarly,
  restartInterview,
  togglePause,
  resumeIfNeeded,
} = useMockInterview()

const { problems, loading } = usePatterns()

const setupConfig = ref({
  totalQuestions: defaultConfig.totalQuestions,
  totalTimeMinutes: defaultConfig.totalTimeMinutes,
  language: defaultConfig.language,
  allowPause: defaultConfig.allowPause,
})

const setupError = ref('')
const thoughtInput = ref('')
const chatInput = ref('')

const sessionStatusLabel = computed(() => {
  if (!activeSession.value) return 'idle'
  if (activeSession.value.status === 'completed') return 'completed'
  if (activeSession.value.status === 'abandoned') return 'ended early'
  return 'in progress'
})

const currentQuestionLabel = computed(() => {
  if (!activeSession.value) return '0 / 0'
  return `${activeSession.value.currentIndex + 1} / ${activeSession.value.questionSlugs.length}`
})

const clarificationLog = computed(() => {
  return (
    currentProblemState.value?.chat.filter(
      message => message.role === 'user' && /\?|clarify|constraint|assume|edge/i.test(message.content),
    ) ?? []
  )
})

const chatMessages = computed(() => currentProblemState.value?.chat ?? [])
const canSubmit = computed(() => Boolean(activeSession.value && currentProblemState.value))

function startInterview() {
  setupError.value = ''
  const result = startSession({
    totalQuestions: setupConfig.value.totalQuestions,
    totalTimeMinutes: setupConfig.value.totalTimeMinutes,
    language: 'java',
    allowPause: setupConfig.value.allowPause,
  })

  if (!result.ok) {
    setupError.value = result.error
    return
  }

  thoughtInput.value = ''
  chatInput.value = ''
}

function submitThought() {
  if (!thoughtInput.value.trim()) return
  addThought(thoughtInput.value)
  thoughtInput.value = ''
}

function sendChat() {
  if (!chatInput.value.trim()) return
  sendMessage(chatInput.value)
  chatInput.value = ''
}

function submitProblemAndContinue() {
  submitAndContinue()
  thoughtInput.value = ''
  chatInput.value = ''
}

function getDifficultyClass(diff: string | null | undefined): string {
  if (!diff) return ''
  return `badge-${diff.toLowerCase()}`
}

function onVisibilityChange() {
  if (!document.hidden) {
    resumeIfNeeded()
  }
}

onMounted(() => {
  resumeIfNeeded()
  document.addEventListener('visibilitychange', onVisibilityChange)
})

onUnmounted(() => {
  document.removeEventListener('visibilitychange', onVisibilityChange)
})
</script>

<template>
  <div class="container mock-view" v-if="!loading">
    <header class="mv-header animate-in">
      <span class="terminal-prompt">mock.interview(mode='realistic-v1')</span>
      <div class="title-row">
        <h1 class="mv-title">Mock Interview</h1>
        <span class="status-pill" :class="`status-${activeSession?.status ?? 'idle'}`">
          {{ sessionStatusLabel }}
        </span>
      </div>
      <p class="mv-subtitle">
        3-question interview simulation with timed pressure, Java-first coding, and offline interviewer chat.
      </p>
    </header>

    <section v-if="!activeSession" class="setup-pane card card-flat animate-in stagger-1">
      <h2 class="section-heading">Session Setup</h2>
      <div class="setup-grid">
        <label class="field">
          <span class="field-label">Questions</span>
          <input v-model.number="setupConfig.totalQuestions" class="field-input" type="number" min="3" max="3" />
        </label>
        <label class="field">
          <span class="field-label">Total Time (minutes)</span>
          <input v-model.number="setupConfig.totalTimeMinutes" class="field-input" type="number" min="15" max="120" step="5" />
        </label>
        <label class="field">
          <span class="field-label">Language</span>
          <input class="field-input" :value="setupConfig.language.toUpperCase()" type="text" disabled />
        </label>
        <label class="field field-toggle">
          <span class="field-label">Pause Allowed</span>
          <input v-model="setupConfig.allowPause" type="checkbox" />
        </label>
      </div>

      <div class="policy-box">
        <h3 class="policy-title">V1 Policy</h3>
        <ul class="policy-list">
          <li>Difficulty mix: Medium-focused with at most one Easy.</li>
          <li>Hard questions excluded in V1 for realistic timing.</li>
          <li>Offline interviewer is active by default.</li>
          <li>State persists across refresh.</li>
        </ul>
      </div>

      <div class="flag-row">
        <span class="tag">AI Mode: {{ featureFlags.aiEnabled ? 'On' : 'Off' }}</span>
        <span class="tag">RAG Mode: {{ featureFlags.ragEnabled ? 'On' : 'Off' }}</span>
      </div>

      <p v-if="setupError" class="setup-error">{{ setupError }}</p>

      <div class="setup-actions">
        <button class="btn btn-primary" :disabled="!canStartSession" @click="startInterview">
          Start Interview
        </button>
      </div>
    </section>

    <section v-else-if="activeSession.status === 'active'" class="workspace animate-in stagger-1">
      <div class="workspace-top card card-flat">
        <div class="meta-block">
          <span class="meta-label">Question</span>
          <span class="meta-value mono">{{ currentQuestionLabel }}</span>
        </div>
        <div class="meta-block">
          <span class="meta-label">Timer</span>
          <span class="meta-value mono timer">{{ timeRemainingLabel }}</span>
        </div>
        <div class="meta-block">
          <span class="meta-label">Difficulty</span>
          <span class="badge" :class="getDifficultyClass(currentProblem?.difficulty)">
            {{ currentProblem?.difficulty ?? 'Unknown' }}
          </span>
        </div>
        <div class="workspace-actions">
          <button class="btn" @click="requestHint">Need Hint</button>
          <button class="btn" @click="togglePause" :disabled="!activeSession.config.allowPause">
            {{ activeSession.paused ? 'Resume' : 'Pause' }}
          </button>
          <button class="btn btn-primary" :disabled="!canSubmit" @click="submitProblemAndContinue">
            {{ activeSession.currentIndex === activeSession.questionSlugs.length - 1 ? 'Submit Interview' : 'Submit + Next' }}
          </button>
          <button class="btn btn-ghost" style="color: var(--accent-red)" @click="endInterviewEarly">
            End Early
          </button>
        </div>
      </div>

      <div class="workspace-grid">
        <article class="panel card problem-panel">
          <header class="panel-head">
            <h2 class="panel-title">Problem Brief</h2>
            <a
              v-if="currentProblem"
              :href="currentProblem.leetcode_url"
              target="_blank"
              rel="noopener noreferrer"
              class="btn"
            >
              Open LeetCode ↗
            </a>
          </header>

          <div v-if="currentProblem" class="brief-block">
            <h3 class="problem-title">{{ currentProblem.title }}</h3>
            <p class="brief-text">
              Use this as a real interview prompt. In V1, full statement text is external;
              open the LeetCode tab and continue discussion here.
            </p>
            <div class="tag-wrap">
              <span class="tag">Pattern: {{ currentProblem.pattern_name }}</span>
              <span class="tag" v-if="currentProblem.acceptance_rate">AC {{ currentProblem.acceptance_rate }}%</span>
              <span v-for="tag in currentProblem.topic_tags" :key="tag" class="tag">{{ tag }}</span>
            </div>
          </div>

          <div class="thought-box">
            <h3 class="panel-subtitle">Approach Notes</h3>
            <textarea
              v-model="thoughtInput"
              class="thought-input"
              rows="3"
              placeholder="Write your high-level plan, assumptions, and edge cases..."
            ></textarea>
            <button class="btn" @click="submitThought">Add Note</button>

            <ul v-if="currentProblemState?.thoughts.length" class="thought-list">
              <li v-for="(thought, idx) in currentProblemState.thoughts" :key="`${thought}-${idx}`">
                {{ thought }}
              </li>
            </ul>
            <p v-else class="empty-text">No notes yet.</p>
          </div>

          <div class="clarification-box">
            <h3 class="panel-subtitle">Clarifications Log</h3>
            <ul v-if="clarificationLog.length" class="clarification-list">
              <li v-for="item in clarificationLog.slice(-8)" :key="item.ts">{{ item.content }}</li>
            </ul>
            <p v-else class="empty-text">Ask about constraints or assumptions; they appear here.</p>
          </div>
        </article>

        <article class="panel card editor-panel">
          <header class="panel-head">
            <h2 class="panel-title">Java Workspace</h2>
            <div class="editor-actions">
              <button class="btn" disabled>Run code (coming next)</button>
            </div>
          </header>

          <textarea
            :value="currentProblemState?.code ?? ''"
            class="code-editor"
            spellcheck="false"
            @input="updateCode(($event.target as HTMLTextAreaElement).value)"
          ></textarea>

          <div class="editor-footer">
            <span class="mono">Hints used: {{ currentProblemState?.hintCount ?? 0 }}</span>
            <span class="mono">Submitted: {{ currentProblemState?.submittedAt ? 'Yes' : 'No' }}</span>
          </div>
        </article>

        <article class="panel card chat-panel">
          <header class="panel-head">
            <h2 class="panel-title">Interviewer Chat</h2>
            <span class="tag">Offline interviewer</span>
          </header>

          <div class="chat-thread">
            <div
              v-for="message in chatMessages"
              :key="`${message.ts}-${message.role}`"
              class="chat-msg"
              :class="`chat-${message.role}`"
            >
              <span class="chat-role mono">{{ message.role === 'assistant' ? 'Interviewer' : 'You' }}</span>
              <p>{{ message.content }}</p>
            </div>
          </div>

          <div class="chat-input-row">
            <textarea
              v-model="chatInput"
              class="chat-input"
              rows="3"
              placeholder="Ask for clarifications or explain your approach..."
            ></textarea>
            <button class="btn" @click="sendChat">Send</button>
          </div>
        </article>
      </div>
    </section>

    <section v-else class="report-pane animate-in stagger-1">
      <div class="card score-hero">
        <span class="terminal-prompt">interview.report()</span>
        <h2 class="score-title">Final Score: {{ activeSession.result?.totalScore ?? 0 }}/100</h2>
        <p class="score-subtitle">
          Session {{ activeSession.status === 'abandoned' ? 'ended early' : 'completed' }} ·
          {{ activeSession.questionSlugs.length }} questions
        </p>
      </div>

      <div class="report-grid">
        <article class="card report-card">
          <h3 class="panel-subtitle">Per Problem</h3>
          <div class="problem-results">
            <div
              v-for="slug in activeSession.questionSlugs"
              :key="slug"
              class="result-item"
            >
              <div class="result-head">
                <strong>{{ problems[slug]?.title ?? slug }}</strong>
                <span class="badge">{{ activeSession.result?.perProblem[slug]?.score ?? 0 }}/100</span>
              </div>
              <ul class="reason-list">
                <li v-for="reason in activeSession.result?.perProblem[slug]?.reasoning ?? []" :key="reason">
                  {{ reason }}
                </li>
              </ul>
            </div>
          </div>
        </article>

        <article class="card report-card">
          <h3 class="panel-subtitle">Strengths</h3>
          <ul class="reason-list">
            <li v-for="item in activeSession.result?.strengths ?? []" :key="item">{{ item }}</li>
          </ul>

          <h3 class="panel-subtitle" style="margin-top: var(--space-lg)">Weaknesses</h3>
          <ul class="reason-list">
            <li v-for="item in activeSession.result?.weaknesses ?? []" :key="item">{{ item }}</li>
          </ul>
        </article>

        <article class="card report-card">
          <h3 class="panel-subtitle">Next Steps</h3>
          <ul class="reason-list">
            <li v-for="item in activeSession.result?.nextSteps ?? []" :key="item">{{ item }}</li>
          </ul>

          <h3 class="panel-subtitle" style="margin-top: var(--space-lg)">Recommended Problems</h3>
          <ul class="reason-list">
            <li v-for="slug in activeSession.result?.recommendedProblems ?? []" :key="slug">
              <router-link :to="`/problem/${slug}`">{{ problems[slug]?.title ?? slug }}</router-link>
            </li>
          </ul>
        </article>
      </div>

      <div class="report-actions">
        <button class="btn btn-primary" @click="restartInterview">Start New Interview</button>
      </div>
    </section>
  </div>

  <div class="container loading-state" v-else>
    <div class="terminal-prompt">loading interview engine...</div>
  </div>
</template>

<style scoped>
.mv-header {
  margin-bottom: var(--space-xl);
}

.title-row {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  flex-wrap: wrap;
}

.mv-title {
  font-size: var(--text-3xl);
  font-weight: 800;
}

.mv-subtitle {
  color: var(--text-secondary);
  margin-top: var(--space-sm);
}

.status-pill {
  border-radius: 999px;
  padding: 4px 10px;
  border: 1px solid var(--border-default);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.status-idle {
  color: var(--text-secondary);
}

.status-active {
  color: var(--accent-cyan);
}

.status-completed {
  color: var(--accent-green);
}

.status-abandoned {
  color: var(--accent-orange);
}

.section-heading,
.panel-title,
.panel-subtitle {
  font-size: var(--text-base);
  font-weight: 700;
}

.setup-pane {
  max-width: 880px;
}

.setup-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-md);
  margin-top: var(--space-md);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.field-input {
  border: 1px solid var(--border-default);
  background: var(--bg-input);
  color: var(--text-primary);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  font-family: var(--font-mono);
}

.field-toggle {
  justify-content: flex-end;
}

.policy-box {
  margin-top: var(--space-lg);
  border: 1px solid var(--border-subtle);
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
  padding: var(--space-md);
}

.policy-title {
  font-size: var(--text-sm);
  margin-bottom: var(--space-sm);
}

.policy-list {
  padding-left: var(--space-md);
  color: var(--text-secondary);
  font-size: var(--text-sm);
  display: grid;
  gap: 6px;
}

.flag-row {
  display: flex;
  gap: var(--space-sm);
  margin-top: var(--space-md);
}

.setup-error {
  margin-top: var(--space-sm);
  color: var(--accent-red);
  font-size: var(--text-sm);
}

.setup-actions {
  margin-top: var(--space-lg);
}

.workspace {
  display: grid;
  gap: var(--space-md);
}

.workspace-top {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  flex-wrap: wrap;
  position: sticky;
  top: 64px;
  z-index: 20;
  background: var(--bg-secondary);
}

.meta-block {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.meta-label {
  color: var(--text-muted);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.meta-value {
  font-size: var(--text-lg);
  font-weight: 700;
}

.timer {
  color: var(--accent-orange);
}

.workspace-actions {
  margin-left: auto;
  display: flex;
  gap: var(--space-sm);
  flex-wrap: wrap;
}

.workspace-grid {
  display: grid;
  grid-template-columns: 1.1fr 1fr 0.95fr;
  gap: var(--space-md);
}

.panel {
  min-height: 520px;
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
}

.problem-title {
  font-size: var(--text-lg);
}

.brief-text {
  color: var(--text-secondary);
  margin-top: var(--space-xs);
  margin-bottom: var(--space-sm);
}

.tag-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs);
}

.thought-box,
.clarification-box {
  padding-top: var(--space-sm);
  border-top: 1px solid var(--border-subtle);
}

.thought-input,
.chat-input {
  width: 100%;
  border: 1px solid var(--border-default);
  background: var(--bg-input);
  color: var(--text-primary);
  border-radius: var(--radius-sm);
  padding: var(--space-sm);
  font-family: var(--font-body);
  resize: vertical;
  margin: var(--space-sm) 0;
}

.thought-list,
.clarification-list,
.reason-list {
  padding-left: var(--space-md);
  display: grid;
  gap: 6px;
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

.empty-text {
  color: var(--text-muted);
  font-size: var(--text-sm);
}

.code-editor {
  flex: 1;
  width: 100%;
  min-height: 380px;
  resize: vertical;
  background: var(--bg-code);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  border-radius: var(--radius-sm);
  padding: var(--space-md);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: 1.6;
}

.editor-footer {
  display: flex;
  justify-content: space-between;
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.chat-thread {
  flex: 1;
  overflow: auto;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: var(--space-sm);
  display: grid;
  gap: var(--space-sm);
  background: var(--bg-input);
}

.chat-msg {
  border-radius: var(--radius-sm);
  padding: var(--space-sm);
  font-size: var(--text-sm);
}

.chat-role {
  font-size: var(--text-xs);
  color: var(--text-muted);
  display: block;
  margin-bottom: 4px;
}

.chat-user {
  background: rgba(56, 189, 248, 0.08);
  border: 1px solid rgba(56, 189, 248, 0.18);
}

.chat-assistant {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
}

.chat-input-row {
  display: grid;
  gap: var(--space-sm);
}

.report-pane {
  display: grid;
  gap: var(--space-md);
}

.score-hero {
  display: grid;
  gap: var(--space-sm);
}

.score-title {
  font-size: var(--text-2xl);
}

.score-subtitle {
  color: var(--text-secondary);
}

.report-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-md);
}

.report-card {
  min-height: 280px;
}

.problem-results {
  display: grid;
  gap: var(--space-md);
}

.result-item {
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: var(--space-sm);
}

.result-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: var(--space-xs);
}

.report-actions {
  display: flex;
  justify-content: flex-start;
}

@media (max-width: 1200px) {
  .workspace-grid,
  .report-grid {
    grid-template-columns: 1fr;
  }

  .panel {
    min-height: auto;
  }
}

@media (max-width: 768px) {
  .workspace-top {
    top: 56px;
    padding-bottom: var(--space-sm);
  }

  .workspace-actions {
    margin-left: 0;
    width: 100%;
  }

  .workspace-actions .btn {
    flex: 1;
    justify-content: center;
  }

  .mv-title {
    font-size: var(--text-2xl);
  }
}
</style>
