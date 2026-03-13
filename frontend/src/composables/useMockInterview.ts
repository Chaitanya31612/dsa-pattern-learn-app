import { computed, ref } from 'vue'
import type {
  InterviewProblemState,
  MockInterviewConfig,
  MockInterviewFeatureFlags,
  MockInterviewProblemResult,
  MockInterviewResult,
  MockInterviewSession,
  Problem,
} from '../types'
import { usePatterns } from './usePatterns'
import { useProgress } from './useProgress'

/**
 * Mock Interview Composable (V2)
 * ==============================
 *
 * This composable owns interview runtime state:
 * - session creation / persistence
 * - question selection policy (3 questions, medium-focused)
 * - timer lifecycle
 * - chat + hint flow (AI first, offline fallback)
 * - final scoring report
 *
 * Example workflow:
 * 1) startSession() -> creates question slugs + per-problem state
 * 2) sendMessage("Need hint") -> calls backend API, falls back offline if needed
 * 3) submitAndContinue() -> marks current problem and advances
 * 4) after last problem -> finalizeSession("completed")
 */

const SESSION_STORAGE_KEY = 'dsa-mock-interview-sessions'
const RECENT_STORAGE_KEY = 'dsa-mock-interview-recent-slugs'
const FLAGS_STORAGE_KEY = 'dsa-mock-interview-flags'
const MAX_RECENT_SLUGS = 40
/**
 * Storage ownership note:
 * - This composable is the only writer for all mock-interview storage keys.
 * - The view reads/writes through composable APIs only.
 * This centralization keeps schema migrations and debugging predictable.
 */

// Starter code shown when each problem opens.
// Example output in editor:
// class Solution {
//     public int solve(int[] nums) { ... }
// }
const DEFAULT_JAVA_TEMPLATE = `class Solution {
    public int solve(int[] nums) {
        // TODO: implement
        return 0;
    }
}`

const DEFAULT_CONFIG: MockInterviewConfig = {
  totalQuestions: 3,
  totalTimeMinutes: 45,
  language: 'java',
  allowPause: false,
}

const DEFAULT_FLAGS: MockInterviewFeatureFlags = {
  aiEnabled: true,
  ragEnabled: false,
}

const activeSession = ref<MockInterviewSession | null>(loadSession())
const featureFlags = ref<MockInterviewFeatureFlags>(loadFlags())

let timerHandle: number | null = null
type StartSessionOptions = Partial<MockInterviewConfig> & { preferredSlug?: string }

/**
 * AI debrief payload contracts returned by backend in debrief mode.
 *
 * These are intentionally local (not global app types) because they are
 * transport-layer contracts for one API endpoint, not persisted domain models.
 */
type AIDebriefPerProblemPayload = {
  score?: number
  reasoning?: string[]
}

type AIDebriefReportPayload = {
  total_score?: number
  per_problem?: Record<string, AIDebriefPerProblemPayload>
  strengths?: string[]
  weaknesses?: string[]
  next_steps?: string[]
  recommended_problems?: string[]
}

type DebriefRecommendationCandidate = {
  slug: string
  title: string
  difficulty: string | null
  pattern_name: string
}

const isReportGenerating = ref(false)

/**
 * Restore session from localStorage.
 * If data shape is invalid (old schema/corrupt), we fail safely with null.
 */
function loadSession(): MockInterviewSession | null {
  try {
    const raw = localStorage.getItem(SESSION_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as MockInterviewSession
    if (!parsed || typeof parsed !== 'object') return null
    if (!Array.isArray(parsed.questionSlugs)) return null
    if (!parsed.problems || typeof parsed.problems !== 'object') return null
    if (!parsed.lastTickAt) parsed.lastTickAt = new Date().toISOString()
    if (typeof parsed.paused !== 'boolean') parsed.paused = false
    return parsed
  } catch {
    return null
  }
}

function saveSession(session: MockInterviewSession | null) {
  if (!session) {
    localStorage.removeItem(SESSION_STORAGE_KEY)
    return
  }
  localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session))
}

function loadFlags(): MockInterviewFeatureFlags {
  /**
   * Feature flags are persisted so local dev/prototyping survives refresh.
   * Current runtime behavior:
   * - aiEnabled: gates backend calls in sendMessage() and enhanceReportWithAI()
   * - ragEnabled: reserved switch, currently surfaced in UI for future extension
   */
  try {
    const raw = localStorage.getItem(FLAGS_STORAGE_KEY)
    if (!raw) return DEFAULT_FLAGS
    const parsed = JSON.parse(raw)
    return {
      aiEnabled: Boolean(parsed?.aiEnabled),
      ragEnabled: Boolean(parsed?.ragEnabled),
    }
  } catch {
    return DEFAULT_FLAGS
  }
}

function saveFlags(flags: MockInterviewFeatureFlags) {
  localStorage.setItem(FLAGS_STORAGE_KEY, JSON.stringify(flags))
}

function loadRecentSlugs(): string[] {
  // This list is used by buildSelectionWeight() to avoid repeatedly serving
  // the same interview problems across consecutive sessions.
  try {
    const raw = localStorage.getItem(RECENT_STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter((value): value is string => typeof value === 'string')
  } catch {
    return []
  }
}

function saveRecentSlugs(slugs: string[]) {
  localStorage.setItem(RECENT_STORAGE_KEY, JSON.stringify(slugs.slice(0, MAX_RECENT_SLUGS)))
}

function appendRecentSlugs(slugs: string[]) {
  // New session slugs are prepended so recency penalties are strongest for
  // the latest interviews.
  const current = loadRecentSlugs()
  const deduped = [...slugs, ...current.filter(s => !slugs.includes(s))]
  saveRecentSlugs(deduped)
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function toWords(text: string): number {
  // Shared lexical metric used by computeProblemResult() to score clarity
  // of the candidate's written approach notes.
  return text
    .split(/\s+/)
    .map(t => t.trim())
    .filter(Boolean).length
}

const CODE_BOILERPLATE_LINE_PATTERNS = [
  /^class\s+Solution\b/,
  /^public\s+\w+\s+solve\(int\[\]\s+nums\)\s*\{?$/,
  /^\/\/\s*TODO/i,
  /^return\s+0;?$/,
  /^[{}]+$/,
]

function countMeaningfulCodeLines(code: string): number {
  return code
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean)
    .filter(line => !CODE_BOILERPLATE_LINE_PATTERNS.some(pattern => pattern.test(line))).length
}

function weightedPick<T>(items: T[], getWeight: (item: T) => number): T | null {
  /**
   * Roulette-wheel weighted sampling.
   * Example:
   * - A weight 100
   * - B weight 20
   * - C weight 5
   * A is picked most often, but B/C still occasionally appear for diversity.
   */
  const weighted = items
    .map(item => ({ item, weight: getWeight(item) }))
    .filter(entry => entry.weight > 0)

  if (weighted.length === 0) return null

  const total = weighted.reduce((sum, entry) => sum + entry.weight, 0)
  let random = Math.random() * total

  for (const entry of weighted) {
    random -= entry.weight
    if (random <= 0) {
      return entry.item
    }
  }

  return weighted[weighted.length - 1]?.item ?? null
}

function parseIsoTime(iso: string | undefined): number {
  if (!iso) return 0
  const parsed = new Date(iso).getTime()
  return Number.isFinite(parsed) ? parsed : 0
}

function isHintRequest(message: string): boolean {
  return /hint|stuck|nudge|help/i.test(message)
}

function buildOfflineReply(problem: Problem | undefined, userMessage: string, currentHintCount: number): string {
  /**
   * Deterministic fallback interviewer used when:
   * - AI endpoint is unavailable
   * - AI mode is explicitly off
   *
   * Hint ladder examples:
   * - level 1: framing question
   * - level 2: pattern/data-structure nudge
   * - level 3+: high-level step guidance
   */
  const message = userMessage.trim().toLowerCase()

  if (isHintRequest(message)) {
    const nextHintLevel = Math.max(currentHintCount, 1)

    if (nextHintLevel <= 1) {
      return `Start by clarifying the core input-output contract for ${problem?.title ?? 'this problem'}. What data must you preserve at each step?`
    }

    if (nextHintLevel === 2) {
      return `You can likely model this with ${problem?.pattern_name ?? 'a fitting pattern'}. Sketch the data structure first and list operations needed per element.`
    }

    return 'Try a two-phase approach: first collect the state you need, then make one deterministic pass to build the answer. Keep each operation O(1) where possible.'
  }

  if (/complex|time|space|big[- ]?o|o\(/i.test(message)) {
    return 'State your current algorithm in one line, then derive time and space by counting loops, nested operations, and auxiliary structures.'
  }

  if (/clarify|constraint|assume|edge/i.test(message)) {
    return 'Good question. List assumptions explicitly: empty input, duplicates, ordering guarantees, and bounds. Then adapt your approach around those cases.'
  }

  if (/correct|right|approach|direction/i.test(message)) {
    return 'Your direction sounds reasonable. Continue by proving the invariant that stays true after each iteration.'
  }

  return `Walk me through your plan for ${problem?.title ?? 'this problem'} in 3 steps: data structure choice, traversal strategy, and edge-case handling.`
}

function formatSeconds(totalSec: number): string {
  const minutes = Math.floor(totalSec / 60)
  const seconds = totalSec % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

function getApiBaseUrl(): string {
  const base = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ?? ''
  return base.endsWith('/') ? base.slice(0, -1) : base
}

function getApiUrl(path: string): string {
  const base = getApiBaseUrl()
  return base ? `${base}${path}` : path
}

async function fetchInterviewerReply(payload: {
  sessionId: string
  problemSlug: string
  hintLevel: number
  mode: 'interview' | 'debrief'
  messages: Array<{ role: 'user' | 'assistant'; content: string; ts: string }>
  problem: Problem | undefined
  debriefContext?: {
    session_status: 'completed' | 'abandoned'
    total_questions: number
    total_time_minutes: number
    remaining_time_sec: number
    language: 'java'
    total_score_heuristic: number
    attempts: Array<{
      slug: string
      title: string
      difficulty: string | null
      pattern_name: string
      description_text: string
      stored_note: string
      thoughts: string[]
      code: string
      chat: Array<{ role: 'user' | 'assistant'; content: string; ts: string }>
      hint_count: number
      submitted: boolean
      heuristic_score: number
      heuristic_reasoning: string[]
    }>
    candidate_recommendations: DebriefRecommendationCandidate[]
  }
}): Promise<{ reply: string; intent?: string; debrief?: AIDebriefReportPayload }> {
  /**
   * Frontend -> Backend API contract.
   *
   * We include both short metadata and problem statement context when available.
   * Example:
   * - title: "Two Sum"
   * - pattern_name: "Arrays & Hashing"
   * - description_text: "Given an array of integers nums..."
   */
  // Backend JSON contract mirrors `backend/app.py` pydantic models.
  // We keep field names in snake_case to avoid backend-side remapping.
  const body = {
    session_id: payload.sessionId,
    problem_slug: payload.problemSlug,
    hint_level: payload.hintLevel,
    mode: payload.mode,
    messages: payload.messages,
    problem: payload.problem
      ? {
          title: payload.problem.title,
          difficulty: payload.problem.difficulty,
          pattern_name: payload.problem.pattern_name,
          pattern_hint: payload.problem.pattern_hint,
          key_insight: payload.problem.key_insight,
          description_html: payload.problem.description_html,
          description_text: payload.problem.description_text,
          topic_tags: payload.problem.topic_tags,
        }
      : null,
    debrief_context: payload.debriefContext ?? null,
  }

  const response = await fetch(getApiUrl('/api/mock-interview/respond'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    throw new Error(`Mock interview API failed with status ${response.status}`)
  }

  const data = await response.json()
  return {
    reply: String(data.reply ?? ''),
    intent: typeof data.intent === 'string' ? data.intent : undefined,
    debrief: data.debrief && typeof data.debrief === 'object' ? (data.debrief as AIDebriefReportPayload) : undefined,
  }
}

function normalizeTextList(values: unknown, fallback: string[], minItems: number, maxItems: number): string[] {
  /**
   * Normalize AI-produced list fields safely.
   *
   * Example:
   * - AI returns [" item 1 ", "", 42]
   * - Output becomes ["item 1"] and then falls back if empty.
   */
  if (!Array.isArray(values)) {
    return fallback
  }

  const cleaned = values
    .filter((value): value is string => typeof value === 'string')
    .map(value => value.trim())
    .filter(Boolean)
    .slice(0, maxItems)

  if (cleaned.length >= minItems) return cleaned
  return fallback
}

function normalizeAIDebriefResult(
  aiDebrief: AIDebriefReportPayload | undefined,
  session: MockInterviewSession,
  fallback: MockInterviewResult,
  knownProblems: Record<string, Problem>,
): MockInterviewResult {
  /**
   * Merge AI debrief over deterministic fallback.
   *
   * Why merge instead of replace:
   * - AI output may be partial or malformed for one field.
   * - We keep the session report stable by preserving fallback data.
   */
  if (!aiDebrief) return fallback

  const merged: MockInterviewResult = {
    ...fallback,
    perProblem: { ...fallback.perProblem },
  }

  const aiTotalScore = Number(aiDebrief.total_score)
  if (Number.isFinite(aiTotalScore)) {
    merged.totalScore = clamp(Math.round(aiTotalScore), 0, 100)
  }

  merged.strengths = normalizeTextList(aiDebrief.strengths, fallback.strengths, 1, 6)
  merged.weaknesses = normalizeTextList(aiDebrief.weaknesses, fallback.weaknesses, 1, 7)
  merged.nextSteps = normalizeTextList(aiDebrief.next_steps, fallback.nextSteps, 2, 7)

  const recommended = Array.isArray(aiDebrief.recommended_problems)
    ? aiDebrief.recommended_problems
        .filter((slug): slug is string => typeof slug === 'string')
        .map(slug => slug.trim())
        .filter(slug => Boolean(slug) && Boolean(knownProblems[slug]) && !session.questionSlugs.includes(slug))
        .slice(0, 5)
    : []
  if (recommended.length > 0) {
    merged.recommendedProblems = recommended
  }

  const aiPerProblem = aiDebrief.per_problem ?? {}
  for (const slug of session.questionSlugs) {
    const fallbackProblem = merged.perProblem[slug]
    if (!fallbackProblem) continue

    const aiEntry = aiPerProblem[slug]
    if (!aiEntry) continue

    const aiScore = Number(aiEntry.score)
    const nextScore = Number.isFinite(aiScore) ? clamp(Math.round(aiScore), 0, 100) : fallbackProblem.score
    const nextReasoning = normalizeTextList(aiEntry.reasoning, fallbackProblem.reasoning, 1, 7)

    merged.perProblem[slug] = {
      ...fallbackProblem,
      score: nextScore,
      reasoning: nextReasoning,
    }
  }

  return merged
}

export function useMockInterview() {
  const { getAllProblems, problems } = usePatterns()
  const { isSolved, getConfidence, state } = useProgress()
  const isInterviewerResponding = ref(false)

  function getCurrentSlug(session = activeSession.value): string | null {
    // Helper is used by both computed selectors and command handlers to ensure
    // "current question" logic is consistently index-driven.
    if (!session) return null
    return session.questionSlugs[session.currentIndex] ?? null
  }

  const currentProblem = computed(() => {
    const slug = getCurrentSlug()
    if (!slug) return null
    return problems.value[slug] ?? null
  })

  const canStartSession = computed(() => getAllProblems().length > 0)

  const timeRemainingLabel = computed(() => {
    const remaining = activeSession.value?.timeRemainingSec ?? 0
    return formatSeconds(Math.max(remaining, 0))
  })

  function persist() {
    // Single write gateway for active session persistence.
    // Any state mutation that should survive refresh should call this.
    saveSession(activeSession.value)
  }

  function buildSelectionWeight(problem: Problem, selected: Problem[], recentSlugs: string[]): number {
    /**
     * Scoring model for candidate problems.
     *
     * Examples:
     * - Unsolved medium from unseen pattern -> high chance
     * - Recently solved with confidence=3 -> much lower priority
     * - Same pattern already selected in this session -> diversity penalty
     */
    const confidence = getConfidence(problem.slug)
    const solved = isSolved(problem.slug)
    let weight = 35

    // Learning-priority weighting:
    // unsolved and low-confidence solved problems should appear most often.
    if (!solved) {
      weight += 75
    } else if (confidence === 1) {
      weight += 45
    } else if (confidence === 2) {
      weight += 24
    } else {
      weight += 8
    }

    // Mediums are emphasized because they are closest to common interview bars.
    if (problem.difficulty === 'Medium') weight += 18
    if (problem.in_both) weight += 8

    // Recency decay from solved history prevents immediate repetition of just-practiced problems.
    const solvedAt = state.solved[problem.slug]?.date
    if (solvedAt) {
      const ageDays = (Date.now() - parseIsoTime(solvedAt)) / (1000 * 60 * 60 * 24)
      if (ageDays < 3) weight -= 40
      else if (ageDays < 7) weight -= 22
      else if (ageDays < 14) weight -= 8
    }

    // Cross-session memory: avoid repeatedly re-serving recent interview slugs.
    const recencyIndex = recentSlugs.indexOf(problem.slug)
    if (recencyIndex !== -1) {
      weight -= Math.max(30 - recencyIndex * 2, 8)
    }

    // Intra-session diversity: penalize duplicate pattern families.
    if (selected.some(p => p.pattern_id === problem.pattern_id)) {
      weight -= 22
    }

    // Small jitter avoids deterministic ties and keeps sessions varied.
    weight += Math.random() * 10

    return Math.max(1, weight)
  }

  function selectQuestions(totalQuestions: number, preferredSlug?: string): string[] {
    /**
     * Session policy:
     * - Allowed difficulties: Easy + Medium
     * - Easy count: 0 or 1
     * - Remaining: Medium
     */
    // Default policy pool (explicitly excludes hard unless user picked one manually).
    const all = getAllProblems().filter(problem => problem.difficulty === 'Easy' || problem.difficulty === 'Medium')
    const allProblems = getAllProblems()
    const recentSlugs = loadRecentSlugs()

    const easyPool = all.filter(problem => problem.difficulty === 'Easy')
    const mediumPool = all.filter(problem => problem.difficulty === 'Medium')

    const selected: Problem[] = []
    const preferredProblem = preferredSlug ? allProblems.find(problem => problem.slug === preferredSlug) : undefined
    if (preferredProblem) {
      selected.push(preferredProblem)
    }

    // Easy target applies across whole session.
    // If preferred problem is Easy, we lock easy target to 1.
    let easyTarget = easyPool.length > 0 && Math.random() < 0.45 ? 1 : 0
    if (preferredProblem?.difficulty === 'Easy') easyTarget = 1

    if (easyTarget === 1 && selected.length === 0) {
      const easyPick = weightedPick(easyPool, problem => buildSelectionWeight(problem, selected, recentSlugs))
      if (easyPick) selected.push(easyPick)
    }

    while (selected.length < totalQuestions) {
      const selectedEasy = selected.filter(problem => problem.difficulty === 'Easy').length
      const remainingSlots = totalQuestions - selected.length
      const mustPickEasyNow = easyTarget > selectedEasy && remainingSlots <= (easyTarget - selectedEasy)
      const needMedium = !mustPickEasyNow
      const pool = needMedium
        ? mediumPool.filter(problem => !selected.some(sel => sel.slug === problem.slug))
        : easyPool.filter(problem => !selected.some(sel => sel.slug === problem.slug))

      const fallbackPool = all.filter(problem => !selected.some(sel => sel.slug === problem.slug))
      const source = pool.length > 0 ? pool : fallbackPool
      if (source.length === 0) break

      const pick = weightedPick(source, problem => buildSelectionWeight(problem, selected, recentSlugs))
      if (!pick) break
      selected.push(pick)
    }

    return selected.slice(0, totalQuestions).map(problem => problem.slug)
  }

  function startTimer() {
    // Timer is driven by wall-clock deltas, not naive "minus 1 every second".
    // This handles tab throttling/background pauses more accurately.
    if (timerHandle) {
      window.clearInterval(timerHandle)
      timerHandle = null
    }

    timerHandle = window.setInterval(() => {
      const session = activeSession.value
      if (!session || session.status !== 'active' || session.paused) return

      const now = Date.now()
      const elapsed = Math.floor((now - parseIsoTime(session.lastTickAt)) / 1000)
      if (elapsed <= 0) return

      session.timeRemainingSec = Math.max(0, session.timeRemainingSec - elapsed)
      session.lastTickAt = new Date(now).toISOString()

      // Time expiry routes through the same finalization pipeline as manual submit,
      // ensuring report generation/persistence stays consistent.
      if (session.timeRemainingSec <= 0) {
        finalizeSession('completed')
        return
      }

      persist()
    }, 1000)
  }

  function stopTimer() {
    if (!timerHandle) return
    window.clearInterval(timerHandle)
    timerHandle = null
  }

  function refreshElapsedTime() {
    // Called on visibility changes and resume flows to reconcile wall-clock drift.
    const session = activeSession.value
    if (!session || session.status !== 'active' || session.paused) return

    const now = Date.now()
    const elapsed = Math.floor((now - parseIsoTime(session.lastTickAt)) / 1000)
    if (elapsed <= 0) return

    session.timeRemainingSec = Math.max(0, session.timeRemainingSec - elapsed)
    session.lastTickAt = new Date(now).toISOString()

    if (session.timeRemainingSec <= 0) {
      finalizeSession('completed')
      return
    }

    persist()
  }

  function ensureProblemStarted(slug: string) {
    const session = activeSession.value
    if (!session) return

    const stateForProblem = session.problems[slug]
    if (!stateForProblem) return

    // We intentionally set startedAt lazily when problem is first entered,
    // not at session creation time.
    if (!stateForProblem.startedAt) {
      stateForProblem.startedAt = new Date().toISOString()
      persist()
    }
  }

  function startSession(options?: StartSessionOptions) {
    if (!canStartSession.value) {
      return { ok: false as const, error: 'Problem database not loaded yet.' }
    }

    // Default interview is 3 questions.
    // Special case: deep-link flow ("Solve in Interview Mode") can request 1 focused question.
    const requestedTotal = options?.totalQuestions
    const totalQuestions = options?.preferredSlug && requestedTotal === 1 ? 1 : 3
    const config: MockInterviewConfig = {
      ...DEFAULT_CONFIG,
      ...options,
      totalQuestions,
      totalTimeMinutes: options?.totalTimeMinutes ?? DEFAULT_CONFIG.totalTimeMinutes,
      language: 'java',
    }

    const questionSlugs = selectQuestions(config.totalQuestions, options?.preferredSlug)
    if (questionSlugs.length < config.totalQuestions) {
      return { ok: false as const, error: 'Not enough eligible Easy/Medium problems to start a session.' }
    }

    const problemsState = Object.fromEntries(
      questionSlugs.map((slug): [string, InterviewProblemState] => {
        return [
          slug,
          {
            slug,
            startedAt: null,
            submittedAt: null,
            code: DEFAULT_JAVA_TEMPLATE,
            thoughts: [],
            chat: [
              {
                role: 'assistant',
                content: 'Interview starts now. Explain your initial approach before writing code.',
                ts: new Date().toISOString(),
              },
            ],
            hintCount: 0,
          },
        ]
      }),
    )

    activeSession.value = {
      id: `mi_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`,
      status: 'active',
      createdAt: new Date().toISOString(),
      config,
      questionSlugs,
      currentIndex: 0,
      timeRemainingSec: config.totalTimeMinutes * 60,
      lastTickAt: new Date().toISOString(),
      paused: false,
      problems: problemsState,
    }

    appendRecentSlugs(questionSlugs)

    const firstSlug = questionSlugs[0]
    if (firstSlug) ensureProblemStarted(firstSlug)

    persist()
    startTimer()

    return { ok: true as const }
  }

  function getCurrentProblemState() {
    const session = activeSession.value
    const slug = getCurrentSlug(session)
    if (!session || !slug) return null
    return session.problems[slug] ?? null
  }

  function updateCode(code: string) {
    const stateForProblem = getCurrentProblemState()
    if (!stateForProblem) return
    stateForProblem.code = code
    persist()
  }

  function addThought(thought: string) {
    const trimmed = thought.trim()
    if (!trimmed) return

    const stateForProblem = getCurrentProblemState()
    if (!stateForProblem) return

    stateForProblem.thoughts.unshift(trimmed)
    persist()
  }
  async function sendMessage(message: string) {
    /**
     * Chat send path:
     * 1) append user message locally
     * 2) compute hint count
     * 3) call AI endpoint when enabled
     * 4) fallback to deterministic offline reply on failure
     * 5) append assistant message + persist
     */
    const trimmed = message.trim()
    if (!trimmed) return

    const session = activeSession.value
    const slug = getCurrentSlug(session)
    if (!session || !slug) return

    const problemState = session.problems[slug]
    if (!problemState) return

    // Append user message first so even failed API calls keep an accurate transcript.
    problemState.chat.push({
      role: 'user',
      content: trimmed,
      ts: new Date().toISOString(),
    })

    const currentProblemMeta = problems.value[slug]
    const hintRequested = isHintRequest(trimmed)

    if (hintRequested) {
      problemState.hintCount += 1
    }

    let assistantReply = ''

    if (featureFlags.value.aiEnabled) {
      isInterviewerResponding.value = true
      try {
        const aiResponse = await fetchInterviewerReply({
          sessionId: session.id,
          problemSlug: slug,
          hintLevel: problemState.hintCount,
          mode: 'interview',
          messages: problemState.chat,
          problem: currentProblemMeta,
        })
        assistantReply = aiResponse.reply.trim()
      } catch {
        // Hard fallback guarantees chat continuity even on backend/provider failures.
        assistantReply = buildOfflineReply(currentProblemMeta, trimmed, problemState.hintCount)
      } finally {
        isInterviewerResponding.value = false
      }
    } else {
      assistantReply = buildOfflineReply(currentProblemMeta, trimmed, problemState.hintCount)
    }

    if (!assistantReply) {
      assistantReply = buildOfflineReply(currentProblemMeta, trimmed, problemState.hintCount)
    }

    problemState.chat.push({
      role: 'assistant',
      content: assistantReply,
      ts: new Date().toISOString(),
    })

    persist()
  }

  async function requestHint() {
    await sendMessage('Need a hint, I am stuck.')
  }

  function submitCurrentProblem() {
    const stateForProblem = getCurrentProblemState()
    if (!stateForProblem) return false

    if (!stateForProblem.startedAt) {
      stateForProblem.startedAt = new Date().toISOString()
    }
    if (!stateForProblem.submittedAt) {
      stateForProblem.submittedAt = new Date().toISOString()
    }

    persist()
    return true
  }

  function moveToNextProblem() {
    const session = activeSession.value
    if (!session) return false

    if (session.currentIndex >= session.questionSlugs.length - 1) {
      return false
    }

    session.currentIndex += 1
    session.lastTickAt = new Date().toISOString()

    const slug = getCurrentSlug(session)
    if (slug) ensureProblemStarted(slug)

    persist()
    return true
  }

  function computeProblemResult(problem: Problem | undefined, stateForProblem: InterviewProblemState): MockInterviewProblemResult {
    /**
     * Heuristic V1/V2 scoring model (deterministic).
     *
     * Example signal mapping:
     * - More structured thoughts + submission => higher understanding/approach
     * - Mentions of edge cases/test/dry run => higher correctness confidence
     * - Excessive hints => penalties on autonomy-oriented criteria
     */
    const userMessages = stateForProblem.chat.filter(message => message.role === 'user')
    const joinedThoughts = stateForProblem.thoughts.join(' ')
    const allUserMessages = userMessages.map(message => message.content).join(' ')

    const thoughtWords = toWords(joinedThoughts)
    const meaningfulThoughtCount = stateForProblem.thoughts.filter(thought => toWords(thought) >= 4).length
    const meaningfulUserMessageCount = userMessages.filter(message => {
      const content = message.content.trim()
      if (content.length < 12) return false
      if (isHintRequest(content) && toWords(content) <= 5) return false
      return true
    }).length

    const meaningfulCodeLines = countMeaningfulCodeLines(stateForProblem.code)
    const submitted = Boolean(stateForProblem.submittedAt)

    const hasMeaningfulCode = meaningfulCodeLines > 0
    const hasMeaningfulNotes = meaningfulThoughtCount > 0
    const hasMeaningfulChat = meaningfulUserMessageCount > 0

    if (!hasMeaningfulCode && !hasMeaningfulNotes && !hasMeaningfulChat && !submitted) {
      return {
        score: 0,
        rubric: {
          problemUnderstanding: 0,
          approachQuality: 0,
          correctnessConfidence: 0,
          complexityReasoning: 0,
          communicationQuality: 0,
        },
        reasoning: [
          'No meaningful implementation, notes, or discussion evidence was provided.',
          'Score is near zero for empty attempts by design.',
          'Write at least a rough approach and initial code draft before ending.',
          'Discuss assumptions, edge cases, and Big-O to improve future interview scores.',
        ],
      }
    }

    const mentionsComplexity = /o\(|complexity|time|space/i.test(`${joinedThoughts} ${allUserMessages}`)
    const mentionsValidation = /edge|test|dry run|validate|check/i.test(`${joinedThoughts} ${allUserMessages} ${stateForProblem.code}`)
    const patternToken = problem?.pattern_name.toLowerCase().split(/\s+/).find(Boolean) ?? ''
    const mentionsPattern =
      patternToken.length > 2 &&
      `${joinedThoughts.toLowerCase()} ${allUserMessages.toLowerCase()}`.includes(patternToken)

    const understanding = clamp(
      Math.round(
        (submitted ? 1 : 0) +
          meaningfulThoughtCount * 3 +
          thoughtWords / 18 +
          meaningfulUserMessageCount * 2 +
          (mentionsPattern ? 1 : 0) -
          stateForProblem.hintCount * 1.2,
      ),
      0,
      20,
    )

    const approach = clamp(
      Math.round(
        (submitted ? 2 : 0) +
          meaningfulCodeLines * 2.8 +
          meaningfulThoughtCount * 1.2 +
          (mentionsPattern ? 1 : 0) -
          stateForProblem.hintCount * 2.4,
      ),
      0,
      25,
    )

    const correctness = clamp(
      Math.round(
        (submitted ? 2 : 0) +
          meaningfulCodeLines * 2.2 +
          (mentionsValidation ? 5 : 0) -
          stateForProblem.hintCount * 1.8,
      ),
      0,
      25,
    )

    const complexity = clamp(
      Math.round(
        (mentionsComplexity ? 6 : 0) +
          Math.min(meaningfulUserMessageCount, 3) +
          (submitted && hasMeaningfulCode ? 2 : 0) -
          stateForProblem.hintCount * 0.8,
      ),
      0,
      15,
    )

    const communication = clamp(
      Math.round(
        meaningfulThoughtCount * 2.2 +
          meaningfulUserMessageCount * 2.4 -
          stateForProblem.hintCount * 1.2,
      ),
      0,
      15,
    )

    const rawTotal = understanding + approach + correctness + complexity + communication
    const evidenceSignals = [hasMeaningfulCode, hasMeaningfulNotes, hasMeaningfulChat, submitted].filter(Boolean).length

    let maxScoreCap = 100
    if (evidenceSignals <= 1) maxScoreCap = 18
    else if (evidenceSignals === 2) maxScoreCap = 38
    if (!hasMeaningfulCode && !submitted) maxScoreCap = Math.min(maxScoreCap, 12)
    if (submitted && !hasMeaningfulCode) maxScoreCap = Math.min(maxScoreCap, 22)

    const total = clamp(Math.min(rawTotal, maxScoreCap), 0, 100)
    const reasoning: string[] = []

    if (hasMeaningfulCode) reasoning.push('Implementation evidence was present in your code draft.')
    else reasoning.push('No meaningful code implementation was provided.')

    if (hasMeaningfulNotes) reasoning.push('You documented approach notes, which improved clarity.')
    else reasoning.push('Add approach notes before coding to improve structure and score.')

    if (hasMeaningfulChat) reasoning.push('Interview communication included substantive technical discussion.')
    else reasoning.push('Use chat to explain assumptions and tradeoffs, not only hint requests.')

    if (mentionsValidation) reasoning.push('Validation signals were present (tests/edge-case checks).')
    else reasoning.push('Run and explain at least one dry-run or edge-case check.')

    if (!submitted) reasoning.push('Solution was not submitted; completion heavily affects final score.')
    if (stateForProblem.hintCount >= 3) reasoning.push('Frequent hints lowered autonomy-oriented rubric categories.')

    return {
      score: total,
      rubric: {
        problemUnderstanding: understanding,
        approachQuality: approach,
        correctnessConfidence: correctness,
        complexityReasoning: complexity,
        communicationQuality: communication,
      },
      reasoning,
    }
  }

  function selectRecommendedProblems(session: MockInterviewSession, weakPatternIds: string[]): string[] {
    /**
     * Post-interview recommendation ranking.
     *
     * Primary goal:
     * - reinforce weakest pattern families seen in this interview.
     * Secondary goals:
     * - prioritize unsolved/low-confidence medium problems.
     */
    const sessionSet = new Set(session.questionSlugs)
    const all = getAllProblems().filter(problem => !sessionSet.has(problem.slug))

    const scored = all
      .map(problem => {
        const confidence = getConfidence(problem.slug)
        const solved = isSolved(problem.slug)

        let score = 0
        if (weakPatternIds.includes(problem.pattern_id)) score += 50
        if (!solved) score += 35
        if (confidence === 1) score += 25
        if (confidence === 2) score += 10
        if (problem.difficulty === 'Medium') score += 15
        if (problem.in_both) score += 6

        return { slug: problem.slug, score }
      })
      .sort((a, b) => b.score - a.score)

    return scored.slice(0, 5).map(entry => entry.slug)
  }

  function buildHeuristicSessionResult(session: MockInterviewSession): {
    result: MockInterviewResult
    weakPatternIds: string[]
  } {
    /**
     * Deterministic baseline report.
     *
     * Important:
     * - This is always computed first so report rendering never blocks on network.
     * - AI debrief (if enabled) is applied later as an overlay for personalization.
     */
    const resultsByProblem: Record<string, MockInterviewProblemResult> = {}

    const criterionTotals = {
      understanding: 0,
      approach: 0,
      correctness: 0,
      complexity: 0,
      communication: 0,
    }

    const patternLoss: Record<string, { id: string; name: string; total: number; count: number }> = {}

    for (const slug of session.questionSlugs) {
      const problemState = session.problems[slug]
      if (!problemState) continue

      const problem = problems.value[slug]
      const result = computeProblemResult(problem, problemState)
      resultsByProblem[slug] = result

      criterionTotals.understanding += result.rubric.problemUnderstanding
      criterionTotals.approach += result.rubric.approachQuality
      criterionTotals.correctness += result.rubric.correctnessConfidence
      criterionTotals.complexity += result.rubric.complexityReasoning
      criterionTotals.communication += result.rubric.communicationQuality

      if (problem) {
        if (!patternLoss[problem.pattern_id]) {
          patternLoss[problem.pattern_id] = {
            id: problem.pattern_id,
            name: problem.pattern_name,
            total: 0,
            count: 0,
          }
        }
        const bucket = patternLoss[problem.pattern_id]
        if (!bucket) continue
        bucket.total += 100 - result.score
        bucket.count += 1
      }
    }

    const scores = Object.values(resultsByProblem).map(result => result.score)
    const avgScore = scores.length > 0 ? scores.reduce((sum, score) => sum + score, 0) / scores.length : 0

    const allSubmitted = session.questionSlugs.every(slug => Boolean(session.problems[slug]?.submittedAt))
    const spread = scores.length > 1 ? Math.max(...scores) - Math.min(...scores) : 0
    const consistencyBonus = allSubmitted && avgScore >= 55 ? (spread <= 15 ? 5 : spread <= 25 ? 3 : 0) : 0

    const totalScore = clamp(Math.round(avgScore + consistencyBonus), 0, 100)

    const denom = Math.max(session.questionSlugs.length, 1)
    const avgUnderstanding = criterionTotals.understanding / denom
    const avgApproach = criterionTotals.approach / denom
    const avgCorrectness = criterionTotals.correctness / denom
    const avgComplexity = criterionTotals.complexity / denom
    const avgCommunication = criterionTotals.communication / denom

    const strengths: string[] = []
    if (avgUnderstanding >= 14) strengths.push('You framed problems well before implementation.')
    if (avgApproach >= 16) strengths.push('Your algorithm direction was generally interview-ready.')
    if (avgCorrectness >= 16) strengths.push('You showed good correctness discipline and validation.')
    if (avgComplexity >= 10) strengths.push('You communicated time/space tradeoffs effectively.')
    if (avgCommunication >= 10) strengths.push('Your thought process was clear and collaborative.')

    if (strengths.length === 0) {
      strengths.push('A session baseline was established; next step is adding stronger code and reasoning evidence.')
    }

    const weaknesses: string[] = []
    if (avgUnderstanding < 12) weaknesses.push('State assumptions and edge cases earlier.')
    if (avgApproach < 14) weaknesses.push('Spend more time on approach outline before coding.')
    if (avgCorrectness < 14) weaknesses.push('Add dry runs and adversarial test checks before submit.')
    if (avgComplexity < 9) weaknesses.push('Explicitly articulate Big-O for time and space.')
    if (avgCommunication < 9) weaknesses.push('Narrate decisions in concise interviewer-friendly checkpoints.')
    if (totalScore <= 10) weaknesses.push('Very limited implementation evidence was captured in this session.')

    const weakPatterns = Object.values(patternLoss)
      .sort((a, b) => b.total / b.count - a.total / a.count)
      .slice(0, 2)

    weakPatterns.forEach(pattern => {
      weaknesses.push(`Pattern gap: ${pattern.name} needs more reps under timed pressure.`)
    })

    const nextSteps: string[] = [
      'Re-solve each interview question in 20 minutes without hints, then compare decisions.',
      'Write one-line invariants before coding to reduce logic drift.',
      'End each solution with a quick complexity + edge-case checklist out loud.',
    ]

    if (weakPatterns[0]) {
      nextSteps.push(`Prioritize ${weakPatterns[0].name} for your next focused practice block.`)
    }

    const weakPatternIds = weakPatterns.map(pattern => pattern.id)
    const recommendedProblems = selectRecommendedProblems(session, weakPatternIds)

    return {
      result: {
        totalScore,
        perProblem: resultsByProblem,
        strengths,
        weaknesses,
        nextSteps,
        recommendedProblems,
      },
      weakPatternIds,
    }
  }

  async function enhanceReportWithAI(
    sessionId: string,
    status: 'completed' | 'abandoned',
    fallbackResult: MockInterviewResult,
    weakPatternIds: string[],
  ) {
    /**
     * Generate personalized final report with AI based on:
     * - code typed in editor
     * - approach notes (thoughts) + stored notes
     * - user/interviewer transcript
     *
     * If anything fails, fallback result remains unchanged.
     */
    const session = activeSession.value
    if (!session || session.id !== sessionId) return
    if (!featureFlags.value.aiEnabled) return

    isReportGenerating.value = true
    try {
      // Attempt payload mirrors backend DebriefProblemAttemptPayload.
      const attempts = session.questionSlugs.map(slug => {
        const problemState = session.problems[slug]
        const problem = problems.value[slug]
        const fallbackProblem = fallbackResult.perProblem[slug]
        return {
          slug,
          title: problem?.title ?? slug,
          difficulty: problem?.difficulty ?? null,
          pattern_name: problem?.pattern_name ?? 'Unknown',
          description_text: problem?.description_text ?? '',
          stored_note: state.notes[slug] ?? '',
          thoughts: [...(problemState?.thoughts ?? [])],
          code: problemState?.code ?? '',
          chat: [...(problemState?.chat ?? [])].slice(-16),
          hint_count: problemState?.hintCount ?? 0,
          submitted: Boolean(problemState?.submittedAt),
          heuristic_score: fallbackProblem?.score ?? 0,
          heuristic_reasoning: [...(fallbackProblem?.reasoning ?? [])],
        }
      })

      // We send a superset candidate list and let backend/LLM select final
      // recommendations while staying grounded in known slugs.
      const recommendationCandidates: DebriefRecommendationCandidate[] = selectRecommendedProblems(session, weakPatternIds)
        .slice(0, 12)
        .map(slug => {
          const problem = problems.value[slug]
          return {
            slug,
            title: problem?.title ?? slug,
            difficulty: problem?.difficulty ?? null,
            pattern_name: problem?.pattern_name ?? 'Unknown',
          }
        })

      // Debrief endpoint still requires `problem_slug`; use best-available slug.
      const activeProblemSlug = session.questionSlugs[session.currentIndex] ?? session.questionSlugs[0] ?? 'session-summary'
      const response = await fetchInterviewerReply({
        sessionId: session.id,
        problemSlug: activeProblemSlug,
        hintLevel: attempts.reduce((sum, attempt) => sum + attempt.hint_count, 0),
        mode: 'debrief',
        messages: attempts.flatMap(attempt => attempt.chat).slice(-20),
        problem: problems.value[activeProblemSlug],
        debriefContext: {
          session_status: status,
          total_questions: session.questionSlugs.length,
          total_time_minutes: session.config.totalTimeMinutes,
          remaining_time_sec: session.timeRemainingSec,
          language: 'java',
          total_score_heuristic: fallbackResult.totalScore,
          attempts,
          candidate_recommendations: recommendationCandidates,
        },
      })

      const latest = activeSession.value
      if (!latest || latest.id !== sessionId) return
      if (!latest.result) return

      const mergedResult = normalizeAIDebriefResult(response.debrief, latest, latest.result, problems.value)
      latest.result = mergedResult
      activeSession.value = { ...latest }
      persist()
    } catch {
      // Silent fallback: keep deterministic report when AI debrief fails.
    } finally {
      const latest = activeSession.value
      if (latest && latest.id === sessionId) {
        isReportGenerating.value = false
      }
    }
  }

  function finalizeSession(status: 'completed' | 'abandoned') {
    /**
     * Finalization is now two-phase:
     * 1) compute deterministic report immediately for instant UX
     * 2) asynchronously overlay AI-personalized debrief if available
     */
    const session = activeSession.value
    if (!session) return

    const { result: fallbackResult, weakPatternIds } = buildHeuristicSessionResult(session)

    session.status = status
    session.paused = false
    session.lastTickAt = new Date().toISOString()
    session.result = fallbackResult

    activeSession.value = { ...session }
    persist()
    stopTimer()

    // Fire-and-forget AI overlay keeps report rendering instant.
    void enhanceReportWithAI(session.id, status, fallbackResult, weakPatternIds)
  }

  function submitAndContinue() {
    const session = activeSession.value
    if (!session || session.status !== 'active') return

    submitCurrentProblem()

    if (session.currentIndex >= session.questionSlugs.length - 1) {
      finalizeSession('completed')
      return
    }

    moveToNextProblem()
  }

  function endInterviewEarly() {
    finalizeSession('abandoned')
  }

  function restartInterview() {
    stopTimer()
    isReportGenerating.value = false
    activeSession.value = null
    saveSession(null)
  }

  function resumeIfNeeded() {
    // Called from view mount + tab visibility restore.
    // Guarantees timer and elapsed time are reconciled before user continues.
    if (!activeSession.value) return

    refreshElapsedTime()

    if (activeSession.value.status === 'active') {
      activeSession.value.lastTickAt = new Date().toISOString()
      persist()
      startTimer()
    } else {
      stopTimer()
    }
  }

  function togglePause() {
    const session = activeSession.value
    if (!session || !session.config.allowPause || session.status !== 'active') return

    if (session.paused) {
      session.paused = false
      session.lastTickAt = new Date().toISOString()
      startTimer()
    } else {
      refreshElapsedTime()
      session.paused = true
      stopTimer()
    }

    persist()
  }

  function updateFeatureFlags(next: Partial<MockInterviewFeatureFlags>) {
    // Feature flags are intentionally runtime mutable for experimentation.
    // Any new flag should default safely in loadFlags()/DEFAULT_FLAGS.
    featureFlags.value = {
      ...featureFlags.value,
      ...next,
    }
    saveFlags(featureFlags.value)
  }

  const currentProblemState = computed(() => getCurrentProblemState())

  if (activeSession.value?.status === 'active') {
    resumeIfNeeded()
  }

  return {
    activeSession,
    currentProblem,
    currentProblemState,
    canStartSession,
    featureFlags,
    isInterviewerResponding,
    isReportGenerating,
    timeRemainingLabel,
    defaultConfig: DEFAULT_CONFIG,
    startSession,
    updateCode,
    addThought,
    sendMessage,
    requestHint,
    submitCurrentProblem,
    submitAndContinue,
    moveToNextProblem,
    endInterviewEarly,
    restartInterview,
    togglePause,
    updateFeatureFlags,
    resumeIfNeeded,
  }
}
