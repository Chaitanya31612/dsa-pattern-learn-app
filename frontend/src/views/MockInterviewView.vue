<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePatterns } from '../composables/usePatterns'
import { useMockInterview } from '../composables/useMockInterview'
import CodeHighlight from '../components/CodeHighlight.vue'

/**
 * MockInterviewView
 * -----------------
 * UI-only orchestration layer.
 *
 * This view deliberately keeps business logic inside `useMockInterview`.
 * Here we focus on:
 * - wiring composable state/actions into controls
 * - handling local UI inputs (chat textbox, thought textbox)
 * - editor typing UX enhancements (Tab indentation)
 *
 * Example user flow:
 * - click "Need Hint" -> `requestHintMessage()` -> composable handles AI call
 * - type code and press Tab -> inserts 4 spaces instead of focus change
 */

const {
  activeSession,
  currentProblem,
  currentProblemState,
  canStartSession,
  featureFlags,
  isInterviewerResponding,
  isReportGenerating,
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
  updateFeatureFlags,
  resumeIfNeeded,
} = useMockInterview()

const { problems, loading } = usePatterns()
const route = useRoute()
const router = useRouter()

const setupConfig = ref({
  totalQuestions: defaultConfig.totalQuestions,
  totalTimeMinutes: defaultConfig.totalTimeMinutes,
  language: defaultConfig.language,
  allowPause: defaultConfig.allowPause,
})
// `setupConfig` is UI-local draft state.
// The source-of-truth session config lives inside useMockInterview().startSession().

const setupError = ref('')
const thoughtInput = ref('')
const chatInput = ref('')
const showSyntaxHighlight = ref(false)
const lastHandledAutoStartKey = ref('')

type InterviewLayoutPrefs = {
  editorRatio: number
  expanded: boolean
}

const INTERVIEW_LAYOUT_STORAGE_KEY = 'dsa-mock-interview-layout'
const DEFAULT_EDITOR_RATIO = 0.6
const MIN_EDITOR_RATIO = 0.44
const MAX_EDITOR_RATIO = 0.78
const SPLIT_BREAKPOINT = 1200

const viewportWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1400)
const workspaceRightRef = ref<HTMLElement | null>(null)
const chatThreadRef = ref<HTMLElement | null>(null)
const editorRatio = ref(DEFAULT_EDITOR_RATIO)
const isEditorExpanded = ref(false)
const isDraggingDivider = ref(false)

let dragStartX = 0
let dragStartRatio = DEFAULT_EDITOR_RATIO

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

function loadInterviewLayout(): InterviewLayoutPrefs {
  try {
    const raw = localStorage.getItem(INTERVIEW_LAYOUT_STORAGE_KEY)
    if (!raw) return { editorRatio: DEFAULT_EDITOR_RATIO, expanded: false }
    const parsed = JSON.parse(raw)
    const ratio = Number(parsed?.editorRatio)
    return {
      editorRatio: Number.isFinite(ratio) ? clamp(ratio, MIN_EDITOR_RATIO, MAX_EDITOR_RATIO) : DEFAULT_EDITOR_RATIO,
      expanded: Boolean(parsed?.expanded),
    }
  } catch {
    return { editorRatio: DEFAULT_EDITOR_RATIO, expanded: false }
  }
}

function saveInterviewLayout() {
  localStorage.setItem(
    INTERVIEW_LAYOUT_STORAGE_KEY,
    JSON.stringify({
      editorRatio: editorRatio.value,
      expanded: isEditorExpanded.value,
    }),
  )
}

const isSplitLayoutAvailable = computed(() => viewportWidth.value > SPLIT_BREAKPOINT)

const workspaceRightStyle = computed(() => {
  if (!isSplitLayoutAvailable.value) return {}
  if (isEditorExpanded.value) {
    return { gridTemplateColumns: 'minmax(520px, 1fr) 0px minmax(0px, 0fr)' }
  }

  const ratio = clamp(editorRatio.value, MIN_EDITOR_RATIO, MAX_EDITOR_RATIO)
  const chatRatio = 1 - ratio
  return {
    gridTemplateColumns: `minmax(420px, ${ratio.toFixed(3)}fr) 10px minmax(320px, ${chatRatio.toFixed(3)}fr)`,
  }
})

function updateViewportWidth() {
  viewportWidth.value = window.innerWidth
}

function toggleEditorExpand() {
  if (!isSplitLayoutAvailable.value) return
  isEditorExpanded.value = !isEditorExpanded.value
}

function resetEditorLayout() {
  editorRatio.value = DEFAULT_EDITOR_RATIO
  isEditorExpanded.value = false
}

function stopDividerDrag() {
  if (!isDraggingDivider.value) return
  isDraggingDivider.value = false
  document.removeEventListener('pointermove', onDividerPointerMove)
  document.removeEventListener('pointerup', stopDividerDrag)
  document.body.style.userSelect = ''
  document.body.style.cursor = ''
}

function onDividerPointerMove(event: PointerEvent) {
  if (!isDraggingDivider.value || !workspaceRightRef.value) return

  const paneWidth = workspaceRightRef.value.clientWidth
  if (!paneWidth) return

  const deltaX = event.clientX - dragStartX
  const ratioDelta = deltaX / paneWidth
  editorRatio.value = clamp(dragStartRatio + ratioDelta, MIN_EDITOR_RATIO, MAX_EDITOR_RATIO)
}

function onDividerPointerDown(event: PointerEvent) {
  if (!isSplitLayoutAvailable.value || isEditorExpanded.value) return
  event.preventDefault()

  isDraggingDivider.value = true
  dragStartX = event.clientX
  dragStartRatio = editorRatio.value

  document.body.style.userSelect = 'none'
  document.body.style.cursor = 'col-resize'
  document.addEventListener('pointermove', onDividerPointerMove)
  document.addEventListener('pointerup', stopDividerDrag)
}

function scrollChatToBottom() {
  if (!chatThreadRef.value) return
  chatThreadRef.value.scrollTop = chatThreadRef.value.scrollHeight
}

// Human-friendly labels for the header status chip.
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

const selectedProblemSlug = computed(() => {
  return typeof route.query.slug === 'string' ? route.query.slug : ''
})

const selectedProblemTitle = computed(() => {
  const slug = selectedProblemSlug.value
  if (!slug) return ''
  return problems.value[slug]?.title ?? slug
})

const shouldAutoStart = computed(() => {
  // Deep-link flag from ProblemView:
  // /mock-interview?slug=<slug>&autostart=1[&single=1]
  const value = route.query.autostart
  return value === '1' || value === 'true'
})
const shouldSingleQuestionMode = computed(() => {
  // Used for "Solve in Interview Mode" flow where user wants focused
  // practice on one chosen problem.
  const value = route.query.single
  return value === '1' || value === 'true'
})
const autoStartKey = computed(() => {
  if (!shouldAutoStart.value || !selectedProblemSlug.value) return ''
  return `${selectedProblemSlug.value}|${String(route.query.autostart ?? '')}|${String(route.query.single ?? '')}`
})

function sanitizeDescriptionHtml(rawHtml: string): string {
  /**
   * Lightweight sanitization for LeetCode prompt snippets.
   * We remove scripts/styles/images/event handlers to avoid noisy/broken rendering.
   */
  return rawHtml
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<style[\s\S]*?<\/style>/gi, '')
    .replace(/<img[^>]*>/gi, '')
    .replace(/\son\w+="[^"]*"/gi, '')
    .replace(/\son\w+='[^']*'/gi, '')
}

// Rich prompt preview shown in Problem Brief.
const problemDescriptionPreview = computed(() => {
  const html = currentProblem.value?.description_html ?? ''
  if (html) return sanitizeDescriptionHtml(html)

  const text = currentProblem.value?.description_text ?? ''
  if (!text) return ''
  return `<p>${text.replace(/\n+/g, '<br/>')}</p>`
})

// Clarification log filters user turns that look like assumptions/questions.
// Example captured message: "Can I assume input is sorted?"
const clarificationLog = computed(() => {
  return (
    currentProblemState.value?.chat.filter(
      message => message.role === 'user' && /\?|clarify|constraint|assume|edge/i.test(message.content),
    ) ?? []
  )
})

const chatMessages = computed(() => currentProblemState.value?.chat ?? [])
const canSubmit = computed(() => Boolean(activeSession.value && currentProblemState.value))

watch(
  () => chatMessages.value.length,
  async () => {
    await nextTick()
    scrollChatToBottom()
  },
)

watch(
  () => isInterviewerResponding.value,
  async (responding, wasResponding) => {
    if (wasResponding && !responding) {
      await nextTick()
      scrollChatToBottom()
    }
  },
)

watch(
  () => [editorRatio.value, isEditorExpanded.value] as const,
  () => {
    saveInterviewLayout()
  },
)

watch(
  () => isSplitLayoutAvailable.value,
  available => {
    if (!available) {
      stopDividerDrag()
      isEditorExpanded.value = false
    }
  },
)

function startInterview() {
  // Start always uses Java in current V2.
  // The composable defaults to 3 questions, but allows 1 question for
  // deep-link "Solve in Interview Mode" flow (slug + single query flag).
  setupError.value = ''
  const result = startSession({
    totalQuestions: selectedProblemSlug.value && shouldSingleQuestionMode.value ? 1 : setupConfig.value.totalQuestions,
    totalTimeMinutes: setupConfig.value.totalTimeMinutes,
    language: 'java',
    allowPause: setupConfig.value.allowPause,
    preferredSlug: selectedProblemSlug.value || undefined,
  })

  if (!result.ok) {
    setupError.value = result.error
    return
  }

  thoughtInput.value = ''
  chatInput.value = ''

  // Query cleanup prevents accidental re-trigger on refresh/back navigation.
  if (selectedProblemSlug.value || shouldAutoStart.value) {
    router.replace({ path: route.path, query: {} })
  }
}

function submitThought() {
  if (!thoughtInput.value.trim()) return
  addThought(thoughtInput.value)
  thoughtInput.value = ''
}

async function sendChat() {
  // Chat submission is intentionally async because composable may call backend.
  // UI disable states are driven by `isInterviewerResponding`.
  if (!chatInput.value.trim()) return
  await sendMessage(chatInput.value)
  chatInput.value = ''
}

function submitProblemAndContinue() {
  // Local fields are reset after each submit to keep next question workspace clean.
  submitAndContinue()
  thoughtInput.value = ''
  chatInput.value = ''
}

async function requestHintMessage() {
  await requestHint()
}

function handleEditorKeydown(event: KeyboardEvent) {
  /**
   * Developer-friendly typing behavior for textarea-based editor.
   *
   * Before:
   * - Pressing Tab moved focus to next input (browser default form behavior).
   * After:
   * - Pressing Tab inserts 4 spaces at cursor.
   *
   * Example:
   *   if (x > 0) {|}
   * becomes
   *   if (x > 0) {    |}
   */
  if (event.key !== 'Tab') return
  event.preventDefault()

  const target = event.target as HTMLTextAreaElement
  const start = target.selectionStart
  const end = target.selectionEnd
  const value = target.value
  const indentation = '    '

  const next = `${value.slice(0, start)}${indentation}${value.slice(end)}`
  target.value = next
  updateCode(next)

  requestAnimationFrame(() => {
    target.selectionStart = start + indentation.length
    target.selectionEnd = start + indentation.length
  })
}

function toggleSyntaxHighlight() {
  // Toggle between:
  // - editable code textarea
  // - read-only highlighted syntax view
  showSyntaxHighlight.value = !showSyntaxHighlight.value
}

function getDifficultyClass(diff: string | null | undefined): string {
  if (!diff) return ''
  return `badge-${diff.toLowerCase()}`
}

function onVisibilityChange() {
  // Re-sync timer after tab/background transitions.
  if (!document.hidden) {
    resumeIfNeeded()
  }
}

onMounted(() => {
  // Current product direction: AI interviewer should be on by default in V2.
  // This can still be toggled internally via composable feature flags if needed.
  const layoutPrefs = loadInterviewLayout()
  editorRatio.value = layoutPrefs.editorRatio
  isEditorExpanded.value = layoutPrefs.expanded
  updateViewportWidth()

  updateFeatureFlags({ aiEnabled: true })
  resumeIfNeeded()
  scrollChatToBottom()
  window.addEventListener('resize', updateViewportWidth)
  document.addEventListener('visibilitychange', onVisibilityChange)
})

onUnmounted(() => {
  stopDividerDrag()
  window.removeEventListener('resize', updateViewportWidth)
  document.removeEventListener('visibilitychange', onVisibilityChange)
})

watch(
  () => [loading.value, autoStartKey.value] as const,
  () => {
    if (!autoStartKey.value) {
      // Reset latch when no autostart query is present.
      // This allows triggering autostart again later for the same slug.
      lastHandledAutoStartKey.value = ''
      return
    }
    if (loading.value) return

    if (lastHandledAutoStartKey.value === autoStartKey.value) return
    lastHandledAutoStartKey.value = autoStartKey.value

    if (activeSession.value) {
      // Explicit behavior requested:
      // when URL contains slug+autostart, end/reset current interview session
      // and start a new one anchored to that slug.
      restartInterview()
    }

    // Start after reset so we never mix two sessions' question sets.
    startInterview()
  },
  { immediate: true },
)
</script>

<template>
  <div class="container mock-view" v-if="!loading">
    <!-- Header summarizes mode and current session state -->
    <header class="mv-header animate-in">
      <span class="terminal-prompt">mock.interview(mode='v2-ai')</span>
      <div class="title-row">
        <h1 class="mv-title">Mock Interview</h1>
        <span class="status-pill" :class="`status-${activeSession?.status ?? 'idle'}`">
          {{ sessionStatusLabel }}
        </span>
      </div>
      <p class="mv-subtitle">
        3-question interview simulation with timed pressure, Java-first coding, and Groq-powered interviewer chat.
      </p>
    </header>

    <!-- Setup screen appears when there is no active session in local storage -->
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
          <li>AI interviewer (Groq smart) is enabled, with offline fallback on failure.</li>
          <li>State persists across refresh.</li>
        </ul>
      </div>

      <div class="flag-row">
        <span class="tag">AI Mode: {{ featureFlags.aiEnabled ? 'On' : 'Off' }}</span>
        <span class="tag">RAG Mode: {{ featureFlags.ragEnabled ? 'On' : 'Off' }}</span>
        <span class="tag" v-if="selectedProblemSlug">
          Selected: {{ selectedProblemTitle }}
        </span>
      </div>

      <p v-if="setupError" class="setup-error">{{ setupError }}</p>

      <div class="setup-actions">
        <button class="btn btn-primary" :disabled="!canStartSession" @click="startInterview">
          Start Interview
        </button>
      </div>
    </section>

    <!-- Active interview workspace -->
    <section v-else-if="activeSession.status === 'active'" class="workspace animate-in stagger-1">
      <!-- Sticky top bar: progress + timer + critical actions -->
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
          <button class="btn" :disabled="isInterviewerResponding" @click="requestHintMessage">
            {{ isInterviewerResponding ? 'Thinking...' : 'Need Hint' }}
          </button>
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
        <!-- Left panel: problem context + user notes -->
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
            <div class="brief-description">
              <div class="brief-rich" v-if="problemDescriptionPreview" v-html="problemDescriptionPreview"></div>
              <p class="brief-text" v-else>
                Prompt preview unavailable in local db. Open LeetCode for full statement.
              </p>
            </div>
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

        <div class="workspace-right" ref="workspaceRightRef" :style="workspaceRightStyle">
          <!-- Middle panel: code editor -->
          <article class="panel card editor-panel">
            <header class="panel-head">
              <h2 class="panel-title">Java Workspace</h2>
              <div class="editor-actions">
                <button class="btn" @click="toggleSyntaxHighlight">
                  {{ showSyntaxHighlight ? 'Code Editor' : 'Syntax Highlight' }}
                </button>
                <button class="btn" @click="toggleEditorExpand" :disabled="!isSplitLayoutAvailable">
                  {{ isEditorExpanded ? 'Restore Layout' : 'Expand Editor' }}
                </button>
                <button class="btn btn-ghost" @click="resetEditorLayout" :disabled="!isSplitLayoutAvailable">
                  Reset Layout
                </button>
              </div>
            </header>

            <div v-if="showSyntaxHighlight" class="code-highlight-wrap">
              <CodeHighlight :code="currentProblemState?.code ?? ''" language="java" />
            </div>
            <textarea
              v-else
              :value="currentProblemState?.code ?? ''"
              class="code-editor"
              spellcheck="false"
              @input="updateCode(($event.target as HTMLTextAreaElement).value)"
              @keydown="handleEditorKeydown"
            ></textarea>

            <div class="editor-footer">
              <span class="mono">Hints used: {{ currentProblemState?.hintCount ?? 0 }}</span>
              <span class="mono">Submitted: {{ currentProblemState?.submittedAt ? 'Yes' : 'No' }}</span>
            </div>
          </article>

          <div
            v-if="isSplitLayoutAvailable && !isEditorExpanded"
            class="splitter"
            :class="{ dragging: isDraggingDivider }"
            @pointerdown="onDividerPointerDown"
            title="Drag to resize editor and chat"
          ></div>

          <!-- Right panel: interviewer chat -->
          <article v-if="!isEditorExpanded || !isSplitLayoutAvailable" class="panel card chat-panel">
            <header class="panel-head">
              <h2 class="panel-title">Interviewer Chat</h2>
              <span class="tag">{{ featureFlags.aiEnabled ? 'AI interviewer · Groq smart' : 'Offline interviewer' }}</span>
            </header>

            <div class="chat-thread" ref="chatThreadRef">
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
                :disabled="isInterviewerResponding"
              ></textarea>
              <button class="btn" :disabled="isInterviewerResponding" @click="sendChat">
                {{ isInterviewerResponding ? 'Thinking...' : 'Send' }}
              </button>
            </div>
          </article>
        </div>
      </div>
    </section>

    <!-- Final report view after completion/early end -->
    <section v-else class="report-pane animate-in stagger-1">
      <div class="card score-hero">
        <span class="terminal-prompt">interview.report()</span>
        <h2 class="score-title">Final Score: {{ activeSession.result?.totalScore ?? 0 }}/100</h2>
        <p class="score-subtitle">
          Session {{ activeSession.status === 'abandoned' ? 'ended early' : 'completed' }} ·
          {{ activeSession.questionSlugs.length }} questions
        </p>
        <p v-if="isReportGenerating" class="score-subtitle report-refreshing">
          Personalizing feedback from your code, notes, and interviewer chat...
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
  grid-template-columns: minmax(320px, 1.1fr) minmax(0, 2fr);
  gap: var(--space-md);
}

.workspace-right {
  display: grid;
  grid-template-columns: minmax(420px, 0.6fr) 10px minmax(320px, 0.4fr);
  gap: var(--space-sm);
  align-items: stretch;
  min-width: 0;
}

.panel {
  min-height: 520px;
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  min-width: 0;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
}

.editor-actions {
  display: flex;
  gap: var(--space-xs);
  flex-wrap: wrap;
}

.problem-title {
  font-size: var(--text-lg);
}

.brief-text {
  color: var(--text-secondary);
  margin-top: var(--space-xs);
  margin-bottom: var(--space-sm);
}

.brief-description {
  min-height: 220px;
  height: 320px;
  max-height: 560px;
  overflow: auto;
  resize: vertical;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  padding: var(--space-sm) var(--space-md);
  padding-right: 2px;
  margin-bottom: var(--space-sm);
}

.brief-rich :deep(p) {
  color: var(--text-secondary);
  margin-bottom: var(--space-sm);
  line-height: 1.7;
}

.brief-rich :deep(li) {
  color: var(--text-secondary);
  margin-left: var(--space-md);
  margin-bottom: 4px;
}

.brief-rich :deep(strong) {
  color: var(--text-primary);
}

.brief-rich :deep(code) {
  color: var(--accent-cyan);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}

.brief-rich :deep(.example),
.brief-rich :deep(.example-block) {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: var(--space-sm);
  margin-bottom: var(--space-sm);
  background: var(--bg-card);
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
  min-height: 620px;
  resize: none;
  background: var(--bg-code);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  border-radius: var(--radius-sm);
  padding: var(--space-md);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: 1.7;
}

.code-highlight-wrap {
  min-height: 620px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  overflow: auto;
  background: var(--bg-code);
}

.code-highlight-wrap :deep(.code-block) {
  min-height: 620px;
  border: none;
  border-radius: 0;
  box-shadow: none;
}

.splitter {
  width: 10px;
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(56, 189, 248, 0.1), rgba(56, 189, 248, 0.3), rgba(56, 189, 248, 0.1));
  border: 1px solid rgba(56, 189, 248, 0.2);
  cursor: col-resize;
  touch-action: none;
  transition: opacity var(--transition-fast), border-color var(--transition-fast);
}

.splitter:hover {
  border-color: var(--accent-cyan);
}

.splitter.dragging {
  border-color: var(--accent-cyan);
  box-shadow: var(--glow-cyan);
}

.editor-footer {
  display: flex;
  justify-content: space-between;
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.chat-thread {
  flex: 1;
  min-height: 0;
  height: 420px;
  max-height: 420px;
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

.report-refreshing {
  color: var(--accent-cyan);
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

  .workspace-right {
    grid-template-columns: 1fr;
    gap: var(--space-md);
  }

  .splitter {
    display: none;
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
