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

const SESSION_STORAGE_KEY = 'dsa-mock-interview-sessions'
const RECENT_STORAGE_KEY = 'dsa-mock-interview-recent-slugs'
const FLAGS_STORAGE_KEY = 'dsa-mock-interview-flags'
const MAX_RECENT_SLUGS = 40

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
  aiEnabled: false,
  ragEnabled: false,
}

const activeSession = ref<MockInterviewSession | null>(loadSession())
const featureFlags = ref<MockInterviewFeatureFlags>(loadFlags())

let timerHandle: number | null = null

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
  const current = loadRecentSlugs()
  const deduped = [...slugs, ...current.filter(s => !slugs.includes(s))]
  saveRecentSlugs(deduped)
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function toWords(text: string): number {
  return text
    .split(/\s+/)
    .map(t => t.trim())
    .filter(Boolean).length
}

function weightedPick<T>(items: T[], getWeight: (item: T) => number): T | null {
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

export function useMockInterview() {
  const { getAllProblems, problems } = usePatterns()
  const { isSolved, getConfidence, state } = useProgress()

  function getCurrentSlug(session = activeSession.value): string | null {
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
    saveSession(activeSession.value)
  }

  function buildSelectionWeight(problem: Problem, selected: Problem[], recentSlugs: string[]): number {
    const confidence = getConfidence(problem.slug)
    const solved = isSolved(problem.slug)
    let weight = 35

    if (!solved) {
      weight += 75
    } else if (confidence === 1) {
      weight += 45
    } else if (confidence === 2) {
      weight += 24
    } else {
      weight += 8
    }

    if (problem.difficulty === 'Medium') weight += 18
    if (problem.in_both) weight += 8

    const solvedAt = state.solved[problem.slug]?.date
    if (solvedAt) {
      const ageDays = (Date.now() - parseIsoTime(solvedAt)) / (1000 * 60 * 60 * 24)
      if (ageDays < 3) weight -= 40
      else if (ageDays < 7) weight -= 22
      else if (ageDays < 14) weight -= 8
    }

    const recencyIndex = recentSlugs.indexOf(problem.slug)
    if (recencyIndex !== -1) {
      weight -= Math.max(30 - recencyIndex * 2, 8)
    }

    if (selected.some(p => p.pattern_id === problem.pattern_id)) {
      weight -= 22
    }

    weight += Math.random() * 10

    return Math.max(1, weight)
  }

  function selectQuestions(totalQuestions: number): string[] {
    const all = getAllProblems().filter(problem => problem.difficulty === 'Easy' || problem.difficulty === 'Medium')
    const recentSlugs = loadRecentSlugs()

    const easyPool = all.filter(problem => problem.difficulty === 'Easy')
    const mediumPool = all.filter(problem => problem.difficulty === 'Medium')

    const selected: Problem[] = []
    const easyTarget = easyPool.length > 0 && Math.random() < 0.45 ? 1 : 0

    if (easyTarget === 1) {
      const easyPick = weightedPick(easyPool, problem => buildSelectionWeight(problem, selected, recentSlugs))
      if (easyPick) selected.push(easyPick)
    }

    while (selected.length < totalQuestions) {
      const needMedium = selected.filter(problem => problem.difficulty === 'Medium').length < totalQuestions - easyTarget
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

    if (!stateForProblem.startedAt) {
      stateForProblem.startedAt = new Date().toISOString()
      persist()
    }
  }

  function startSession(partialConfig?: Partial<MockInterviewConfig>) {
    if (!canStartSession.value) {
      return { ok: false as const, error: 'Problem database not loaded yet.' }
    }

    const totalQuestions = 3
    const config: MockInterviewConfig = {
      ...DEFAULT_CONFIG,
      ...partialConfig,
      totalQuestions,
      totalTimeMinutes: partialConfig?.totalTimeMinutes ?? DEFAULT_CONFIG.totalTimeMinutes,
      language: 'java',
    }

    const questionSlugs = selectQuestions(config.totalQuestions)
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

  function sendMessage(message: string) {
    const trimmed = message.trim()
    if (!trimmed) return

    const session = activeSession.value
    const slug = getCurrentSlug(session)
    if (!session || !slug) return

    const problemState = session.problems[slug]
    if (!problemState) return

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

    const assistantReply = buildOfflineReply(currentProblemMeta, trimmed, problemState.hintCount)

    problemState.chat.push({
      role: 'assistant',
      content: assistantReply,
      ts: new Date().toISOString(),
    })

    persist()
  }

  function requestHint() {
    sendMessage('Need a hint, I am stuck.')
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
    const joinedThoughts = stateForProblem.thoughts.join(' ')
    const allUserMessages = stateForProblem.chat
      .filter(message => message.role === 'user')
      .map(message => message.content)
      .join(' ')

    const thoughtWords = toWords(joinedThoughts)
    const codeLines = stateForProblem.code.split('\n').map(line => line.trim()).filter(Boolean).length
    const userMessageCount = stateForProblem.chat.filter(message => message.role === 'user').length

    const mentionsComplexity = /o\(|complexity|time|space/i.test(`${joinedThoughts} ${allUserMessages}`)
    const mentionsValidation = /edge|test|dry run|validate|check/i.test(`${joinedThoughts} ${allUserMessages} ${stateForProblem.code}`)
    const patternToken = problem?.pattern_name.toLowerCase().split(/\s+/).find(Boolean) ?? ''
    const mentionsPattern = patternToken.length > 2 && joinedThoughts.toLowerCase().includes(patternToken)

    const understanding = clamp(
      Math.round((stateForProblem.submittedAt ? 6 : 2) + thoughtWords / 14 + userMessageCount * 1.4 + (mentionsPattern ? 2 : 0)),
      0,
      20,
    )

    const approach = clamp(
      Math.round((stateForProblem.submittedAt ? 8 : 3) + codeLines * 1.1 + (mentionsPattern ? 3 : 0) - stateForProblem.hintCount * 1.8),
      0,
      25,
    )

    const correctness = clamp(
      Math.round((stateForProblem.submittedAt ? 10 : 2) + codeLines * 0.9 + (mentionsValidation ? 8 : 0) - stateForProblem.hintCount),
      0,
      25,
    )

    const complexity = clamp(
      Math.round((mentionsComplexity ? 9 : 3) + (stateForProblem.submittedAt ? 3 : 0) + Math.min(userMessageCount, 3)),
      0,
      15,
    )

    const communication = clamp(
      Math.round(4 + stateForProblem.thoughts.length * 2 + userMessageCount * 1.5 - stateForProblem.hintCount * 0.8),
      0,
      15,
    )

    const total = understanding + approach + correctness + complexity + communication

    const reasoning: string[] = []

    if (understanding >= 14) reasoning.push('Problem understanding was clear and structured.')
    else reasoning.push('Problem framing needs more explicit assumptions and constraints.')

    if (approach >= 17) reasoning.push('Approach quality was solid with workable implementation detail.')
    else reasoning.push('Approach can be tightened before coding to reduce rework.')

    if (correctness >= 16) reasoning.push('Solution confidence improved through validation signals.')
    else reasoning.push('Correctness confidence is limited; add explicit dry-run or edge-case checks.')

    if (complexity >= 10) reasoning.push('Complexity reasoning was communicated in interview-friendly form.')
    else reasoning.push('Complexity explanation was thin or missing; state time/space tradeoffs clearly.')

    if (stateForProblem.hintCount >= 3) {
      reasoning.push('Frequent hints were needed; aim to hold the line longer before requesting nudges.')
    }

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

  function finalizeSession(status: 'completed' | 'abandoned') {
    const session = activeSession.value
    if (!session) return

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
    const consistencyBonus = allSubmitted ? (spread <= 15 ? 5 : spread <= 25 ? 3 : 0) : 0

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
      strengths.push('You stayed engaged across all prompts and produced working drafts.')
    }

    const weaknesses: string[] = []
    if (avgUnderstanding < 12) weaknesses.push('State assumptions and edge cases earlier.')
    if (avgApproach < 14) weaknesses.push('Spend more time on approach outline before coding.')
    if (avgCorrectness < 14) weaknesses.push('Add dry runs and adversarial test checks before submit.')
    if (avgComplexity < 9) weaknesses.push('Explicitly articulate Big-O for time and space.')
    if (avgCommunication < 9) weaknesses.push('Narrate decisions in concise interviewer-friendly checkpoints.')

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

    const recommendedProblems = selectRecommendedProblems(session, weakPatterns.map(pattern => pattern.id))

    const result: MockInterviewResult = {
      totalScore,
      perProblem: resultsByProblem,
      strengths,
      weaknesses,
      nextSteps,
      recommendedProblems,
    }

    session.status = status
    session.paused = false
    session.lastTickAt = new Date().toISOString()
    session.result = result

    activeSession.value = { ...session }
    persist()
    stopTimer()
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
    activeSession.value = null
    saveSession(null)
  }

  function resumeIfNeeded() {
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
