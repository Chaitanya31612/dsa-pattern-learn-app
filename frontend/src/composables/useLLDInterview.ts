import { computed, ref } from 'vue'
import type {
  LLDCatalogProblem,
  LLDInterviewMode,
  LLDInterviewReport,
  LLDInterviewSession,
  LLDPhaseId,
  LLDPhaseWorkspace,
} from '../types'
import { LLD_FRAMEWORK_PHASES, LLD_PROBLEMS as HARDCODED_PROBLEMS } from '../data/lldProblems'

const STORAGE_KEY = 'dsa-lld-interview-session-v1'
const NOTE_TEMPLATES: Record<LLDPhaseId, string> = {
  clarify: 'Must-haves:\n- \n\nNice-to-have:\n- \n\nAssumptions:\n- \n\nOut of scope:\n- ',
  model: 'Core entities:\n- \n\nRelationships:\n- \n\nInvariants:\n- ',
  design: 'Interfaces / enums:\n- \n\nPatterns and why:\n- \n\nTrade-offs:\n- ',
  implement: 'Implementation plan:\n1. \n2. \n3. \n\nDemo path:\n- ',
  review: 'Edge cases:\n- \n\nFuture scope:\n- \n\nWhat I would improve next:\n- ',
}

const activeSession = ref<LLDInterviewSession | null>(loadSession())
const isResponding = ref(false)
const lastSavedAt = ref<string | null>(activeSession.value?.savedCodeAt ?? null)

let timerHandle: number | null = null
let codeSaveHandle: number | null = null

function loadSession(): LLDInterviewSession | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as LLDInterviewSession
    if (!parsed || typeof parsed !== 'object' || !parsed.problemId) return null
    for (const phase of LLD_FRAMEWORK_PHASES) {
      if (!parsed.phaseWork?.[phase.id]) {
        parsed.phaseWork[phase.id] = { notes: NOTE_TEMPLATES[phase.id], checkpoints: [] }
      }
    }
    // Backward-compat: older sessions may not have hintCount
    if (typeof parsed.hintCount !== 'number') parsed.hintCount = 0
    return parsed
  } catch {
    return null
  }
}

function saveSession(session: LLDInterviewSession | null) {
  if (!session) {
    localStorage.removeItem(STORAGE_KEY)
    return
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
}

// Module-level merged problem cache (populated by useLLDProblems async load).
// We import JSON cache ref from useLLDProblems at runtime to avoid circular deps.
let _mergedProblemsCache: LLDCatalogProblem[] = HARDCODED_PROBLEMS

/** Called by composable to register the merged catalog once JSON is ready. */
export function registerMergedProblems(problems: LLDCatalogProblem[]) {
  _mergedProblemsCache = problems
}

function getApiBaseUrl(): string {
  const base = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ?? ''
  return base.endsWith('/') ? base.slice(0, -1) : base
}

function getApiUrl(path: string): string {
  const base = getApiBaseUrl()
  return base ? `${base}${path}` : path
}

function getProblem(problemId: string): LLDCatalogProblem | undefined {
  return _mergedProblemsCache.find(p => p.id === problemId)
}

function createPhaseWork(): Record<LLDPhaseId, LLDPhaseWorkspace> {
  return LLD_FRAMEWORK_PHASES.reduce<Record<LLDPhaseId, LLDPhaseWorkspace>>((acc, phase) => {
    acc[phase.id] = {
      notes: NOTE_TEMPLATES[phase.id],
      checkpoints: [],
    }
    return acc
  }, {} as Record<LLDPhaseId, LLDPhaseWorkspace>)
}

function meaningfulCodeLines(code: string): number {
  return code
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean)
    .filter(line => !line.startsWith('//'))
    .length
}

function extractCodeTypes(code: string): string[] {
  const found = new Set<string>()
  const matches = code.matchAll(/\b(?:class|interface|enum|record)\s+([A-Z][A-Za-z0-9_]*)/g)
  for (const match of matches) {
    if (match[1]) found.add(match[1])
  }
  return [...found]
}

function summarizeText(value: string, max = 180): string {
  const trimmed = value.replace(/\s+/g, ' ').trim()
  if (!trimmed) return 'No substantial notes yet.'
  return trimmed.length <= max ? trimmed : `${trimmed.slice(0, max - 1)}…`
}

function buildContextDigest(problem: LLDCatalogProblem, session: LLDInterviewSession) {
  const activePhase = LLD_FRAMEWORK_PHASES.find(phase => phase.id === session.activePhase)
  const phaseNotes = session.phaseWork[session.activePhase]?.notes ?? ''
  const filledPhases = LLD_FRAMEWORK_PHASES.filter(phase => {
    const notes = session.phaseWork[phase.id]?.notes ?? ''
    return notes.replace(/[^a-zA-Z0-9]/g, '').length > 18
  }).map(phase => phase.title)
  const codeTypes = extractCodeTypes(session.code)
  const referencedEntities = problem.framework.entities.classes
    .map(entity => entity.name)
    .filter(name => phaseNotes.includes(name) || session.code.includes(name))

  return {
    activePhaseTitle: activePhase?.title ?? 'Clarify',
    noteSummary: summarizeText(phaseNotes),
    filledPhases,
    codeTypes,
    referencedEntities,
    codeLines: meaningfulCodeLines(session.code),
  }
}

function markdownList(items: string[]): string {
  return items.map(item => `- ${item}`).join('\n')
}

function nextActionForPhase(problem: LLDCatalogProblem, phaseId: LLDPhaseId): string {
  const phase = LLD_FRAMEWORK_PHASES.find(item => item.id === phaseId)
  const guidedHint = problem.guided.phase_hints[phaseId]?.[0] ?? 'Keep the answer crisp and extensible.'
  return `${phase?.title ?? 'Current'} focus: ${guidedHint}`
}

function buildAssistantReply(problem: LLDCatalogProblem, session: LLDInterviewSession, userMessage: string): string {
  const digest = buildContextDigest(problem, session)
  const message = userMessage.toLowerCase()
  const mode = session.mode
  const contextLine = digest.codeTypes.length
    ? `Current design context: I can already see ${digest.codeTypes.slice(0, 4).join(', ')} in your workspace.`
    : `Current design context: you have not committed concrete types yet, so stay high-signal and name the main abstractions next.`
  const entityLine = digest.referencedEntities.length
    ? `Entities already present in your notes/code: ${digest.referencedEntities.slice(0, 5).join(', ')}.`
    : `Your notes have not anchored the core entities clearly yet.`

  if (message.includes('requirement') || message.includes('clarify') || session.activePhase === 'clarify') {
    if (mode === 'interview' && !message.includes('stuck') && !message.includes('help')) {
      return [
        `You are in ${digest.activePhaseTitle}. Lead with scope control before naming classes.`,
        contextLine,
        'Answer these first:',
        markdownList(problem.framework.requirements.clarifying_questions.slice(0, 3)),
        'Then bucket the problem into must-have, nice-to-have, and out-of-scope items.',
      ].join('\n\n')
    }

    return [
      `Use this clarify structure for ${problem.title}:`,
      markdownList(problem.framework.requirements.clarifying_questions.slice(0, 4)),
      'Must-haves to lock in:',
      markdownList(problem.framework.requirements.must_have),
      'Out of scope to say explicitly:',
      markdownList(problem.framework.requirements.out_of_scope),
    ].join('\n\n')
  }

  if (message.includes('uml') || message.includes('class') || message.includes('entity') || message.includes('model')) {
    return [
      `Modeling pass for ${problem.title}:`,
      contextLine,
      entityLine,
      'Core entities to anchor:',
      markdownList(problem.framework.entities.classes.map(entity => `${entity.name}: ${entity.responsibility}`)),
      'Relationships to say out loud:',
      markdownList(problem.framework.entities.relationships),
    ].join('\n\n')
  }

  if (message.includes('pattern') || message.includes('interface') || message.includes('contract') || message.includes('design')) {
    const patterns = problem.framework.design_patterns.map(pattern => `${pattern.name} -> ${pattern.applied_to}: ${pattern.why}`)
    return [
      `Contract phase guidance for ${problem.title}:`,
      contextLine,
      'Patterns worth introducing only if they buy extensibility:',
      markdownList(patterns),
      `Say this: ${problem.framework.key_phrases[0]}`,
    ].join('\n\n')
  }

  if (message.includes('code') || message.includes('implement') || message.includes('starter') || session.activePhase === 'implement') {
    const directness = mode === 'guided'
      ? ['Implementation order:', markdownList(problem.framework.implementation_order), 'Checkpoints:', markdownList(problem.guided.checkpoints.slice(0, 3))]
      : ['Implementation pressure test:', nextActionForPhase(problem, session.activePhase), 'Do not code everything. Prioritize the runnable happy path and one extension seam.']

    return [
      `Implementation coaching for ${problem.title}:`,
      contextLine,
      `Current note summary: ${digest.noteSummary}`,
      ...directness,
    ].join('\n\n')
  }

  if (message.includes('edge') || message.includes('review') || message.includes('extend') || message.includes('future')) {
    return [
      `Review pass for ${problem.title}:`,
      'Gotchas to call out:',
      markdownList(problem.framework.gotchas),
      `Follow-up drill: ${problem.framework.extensibility_test}`,
      `Use this line: ${problem.framework.key_phrases[problem.framework.key_phrases.length - 1]}`,
    ].join('\n\n')
  }

  if (message.includes('next')) {
    return [
      `Next move in ${digest.activePhaseTitle}:`,
      nextActionForPhase(problem, session.activePhase),
      `Your strongest accumulated context so far: ${digest.noteSummary}`,
      `Phases with usable notes: ${digest.filledPhases.join(', ') || 'none yet'}.`,
    ].join('\n\n')
  }

  if (mode === 'interview') {
    return [
      `Interviewer stance: I will not hand you the whole design, but I will keep you on track.`,
      contextLine,
      entityLine,
      `Right now I want a stronger answer in ${digest.activePhaseTitle}. ${nextActionForPhase(problem, session.activePhase)}`,
      'If you are stuck, ask for a narrower nudge such as entity modeling, interface seams, or edge-case review.',
    ].join('\n\n')
  }

  return [
    `Guided coaching for ${problem.title}:`,
    contextLine,
    entityLine,
    `Current phase: ${digest.activePhaseTitle}.`,
    `Recommended next action: ${nextActionForPhase(problem, session.activePhase)}`,
    'Helpful checkpoints:',
    markdownList(problem.guided.checkpoints.slice(0, 4)),
  ].join('\n\n')
}

function scorePhase(problem: LLDCatalogProblem, session: LLDInterviewSession, phaseId: LLDPhaseId): number {
  const notes = session.phaseWork[phaseId]?.notes ?? ''
  const noteSignal = Math.min(45, Math.round(notes.replace(/\s+/g, '').length / 8))
  const codeSignal = phaseId === 'implement' ? Math.min(35, meaningfulCodeLines(session.code) * 2) : 0
  const keywordPool = [
    ...problem.framework.key_phrases,
    ...problem.framework.entities.classes.map(entity => entity.name),
    ...problem.framework.design_patterns.map(pattern => pattern.name),
  ]
  const keywordHits = keywordPool.reduce((count, keyword) => {
    return notes.toLowerCase().includes(keyword.toLowerCase()) || session.code.toLowerCase().includes(keyword.toLowerCase())
      ? count + 1
      : count
  }, 0)
  const keywordSignal = Math.min(20, keywordHits * 4)
  const checkpointSignal = session.phaseWork[phaseId]?.checkpoints.length ? 10 : 0
  const phaseBase = phaseId === 'implement' ? 20 : 30
  return Math.min(100, phaseBase + noteSignal + codeSignal + keywordSignal + checkpointSignal)
}

function buildReport(problem: LLDCatalogProblem, session: LLDInterviewSession): LLDInterviewReport {
  const phaseScores = LLD_FRAMEWORK_PHASES.reduce<Record<LLDPhaseId, number>>((acc, phase) => {
    acc[phase.id] = scorePhase(problem, session, phase.id)
    return acc
  }, {} as Record<LLDPhaseId, number>)

  const overallScore = Math.round(
    LLD_FRAMEWORK_PHASES.reduce((sum, phase) => sum + phaseScores[phase.id], 0) / LLD_FRAMEWORK_PHASES.length,
  )

  const strengths: string[] = []
  const improvements: string[] = []

  if (phaseScores.clarify >= 70) strengths.push('You scoped the problem before coding and captured assumptions instead of guessing silently.')
  else improvements.push('Open with sharper requirement bucketing: must-have, nice-to-have, and out-of-scope should be explicit.')

  if (phaseScores.model >= 70) strengths.push('Your entity model is recognizable and interview-friendly, which reduces refactor pressure during coding.')
  else improvements.push('Your class model needs stronger ownership boundaries. Name the aggregates and relationships earlier.')

  if (phaseScores.design >= 70) strengths.push('You identified at least one meaningful abstraction seam instead of hardcoding policy into manager classes.')
  else improvements.push('Introduce interfaces or state/policy seams before implementation so extensibility is visible.')

  if (phaseScores.implement >= 70) strengths.push('The implementation shows a runnable core path instead of unfinished abstractions only.')
  else improvements.push('Code the happy path earlier. A short runnable skeleton beats a broad but shallow design.')

  if (phaseScores.review >= 70) strengths.push('You closed the loop with edge cases and follow-up readiness, which is where seniority usually shows.')
  else improvements.push('Reserve the final minutes for edge cases, concurrency notes, and one follow-up requirement.')

  const summary = session.mode === 'guided'
    ? 'Guided mode favored structure and framework discipline. The next gain is to make your notes terser and your implementation path more decisive.'
    : 'Interview mode shows how well your framework survives with less scaffolding. Keep compressing your spoken structure so design decisions land faster.'

  return {
    overallScore,
    phaseScores,
    strengths,
    improvements,
    summary,
  }
}

function startTimer() {
  if (timerHandle || !activeSession.value || activeSession.value.status !== 'active') return
  timerHandle = window.setInterval(() => {
    const session = activeSession.value
    if (!session || session.status !== 'active' || session.paused) return
    const now = Date.now()
    const last = new Date(session.lastTickAt).getTime()
    const delta = Number.isFinite(last) ? Math.max(0, Math.floor((now - last) / 1000)) : 1
    if (delta <= 0) return

    session.timeRemainingSec = Math.max(0, session.timeRemainingSec - delta)
    session.lastTickAt = new Date(now).toISOString()
    session.updatedAt = session.lastTickAt

    if (session.timeRemainingSec === 0) {
      const problem = getProblem(session.problemId)
      if (problem) {
        session.report = buildReport(problem, session)
      }
      session.status = 'completed'
      stopTimer()
    }

    saveSession(session)
  }, 1000)
}

function stopTimer() {
  if (!timerHandle) return
  window.clearInterval(timerHandle)
  timerHandle = null
}

function scheduleCodeSave() {
  if (codeSaveHandle) window.clearTimeout(codeSaveHandle)
  codeSaveHandle = window.setTimeout(() => {
    flushCodeSave()
  }, 450)
}

function flushCodeSave() {
  if (!activeSession.value) return
  const now = new Date().toISOString()
  activeSession.value.savedCodeAt = now
  activeSession.value.updatedAt = now
  lastSavedAt.value = now
  saveSession(activeSession.value)
}

function maybeResumeSession() {
  const session = activeSession.value
  if (!session || session.status !== 'active') return
  if (!session.paused) {
    const now = Date.now()
    const last = new Date(session.lastTickAt).getTime()
    const delta = Number.isFinite(last) ? Math.max(0, Math.floor((now - last) / 1000)) : 0
    if (delta > 0) {
      session.timeRemainingSec = Math.max(0, session.timeRemainingSec - delta)
      session.lastTickAt = new Date(now).toISOString()
      if (session.timeRemainingSec === 0) {
        const problem = getProblem(session.problemId)
        if (problem) session.report = buildReport(problem, session)
        session.status = 'completed'
      }
      saveSession(session)
    }
  }

  if (session.status === 'active') startTimer()
}

export function useLLDInterview() {
  maybeResumeSession()

  const currentProblem = computed(() => {
    if (!activeSession.value) return null
    return getProblem(activeSession.value.problemId) ?? null
  })

  const timeRemainingLabel = computed(() => {
    const totalSeconds = activeSession.value?.timeRemainingSec ?? 0
    const mins = Math.floor(totalSeconds / 60)
    const secs = totalSeconds % 60
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  })

  const phaseProgress = computed(() => {
    if (!activeSession.value) return 0
    const completed = LLD_FRAMEWORK_PHASES.filter(phase => {
      const notes = activeSession.value?.phaseWork[phase.id]?.notes ?? ''
      return notes.replace(/[^a-zA-Z0-9]/g, '').length > 18
    }).length
    return Math.round((completed / LLD_FRAMEWORK_PHASES.length) * 100)
  })

  const contextDigest = computed(() => {
    if (!activeSession.value || !currentProblem.value) return null
    return buildContextDigest(currentProblem.value, activeSession.value)
  })

  function startSession(problemId: string, mode: LLDInterviewMode) {
    const problem = getProblem(problemId)
    if (!problem) return

    const createdAt = new Date().toISOString()
    activeSession.value = {
      id: `lld_${problemId}_${Date.now()}`,
      problemId,
      mode,
      status: 'active',
      createdAt,
      updatedAt: createdAt,
      activePhase: 'clarify',
      paused: false,
      timeRemainingSec: problem.duration[mode] * 60,
      lastTickAt: createdAt,
      phaseWork: createPhaseWork(),
      code: mode === 'guided' ? problem.guided.starter_code : '',
      savedCodeAt: createdAt,
      hintCount: 0,
      chat: [
        {
          role: 'assistant',
          content: `${problem.interview.opening_prompt}\n\nMode: ${mode === 'guided' ? 'Guided coaching. I will give structure, hints, and guardrails.' : 'Interview coaching. I will stay helpful, but I will push you to drive the structure.'}`,
          ts: createdAt,
        },
      ],
    }
    lastSavedAt.value = createdAt
    saveSession(activeSession.value)
    stopTimer()
    startTimer()
  }

  function setActivePhase(phaseId: LLDPhaseId) {
    if (!activeSession.value) return
    activeSession.value.activePhase = phaseId
    activeSession.value.updatedAt = new Date().toISOString()
    saveSession(activeSession.value)
  }

  function updatePhaseNotes(phaseId: LLDPhaseId, notes: string) {
    if (!activeSession.value) return
    activeSession.value.phaseWork[phaseId].notes = notes
    activeSession.value.updatedAt = new Date().toISOString()
    saveSession(activeSession.value)
  }

  function toggleCheckpoint(phaseId: LLDPhaseId, item: string) {
    if (!activeSession.value) return
    const checklist = activeSession.value.phaseWork[phaseId].checkpoints
    const index = checklist.indexOf(item)
    if (index >= 0) checklist.splice(index, 1)
    else checklist.push(item)
    activeSession.value.updatedAt = new Date().toISOString()
    saveSession(activeSession.value)
  }

  function updateCode(code: string) {
    if (!activeSession.value) return
    activeSession.value.code = code
    activeSession.value.updatedAt = new Date().toISOString()
    saveSession(activeSession.value)
    scheduleCodeSave()
  }

  function togglePause() {
    if (!activeSession.value || activeSession.value.status !== 'active') return
    const now = new Date().toISOString()
    if (!activeSession.value.paused) {
      const last = new Date(activeSession.value.lastTickAt).getTime()
      const delta = Math.max(0, Math.floor((Date.now() - last) / 1000))
      activeSession.value.timeRemainingSec = Math.max(0, activeSession.value.timeRemainingSec - delta)
    }
    activeSession.value.paused = !activeSession.value.paused
    activeSession.value.lastTickAt = now
    activeSession.value.updatedAt = now
    saveSession(activeSession.value)
  }

  async function sendMessage(content: string) {
    if (!activeSession.value || !currentProblem.value) return
    const trimmed = content.trim()
    if (!trimmed || isResponding.value) return

    const now = new Date().toISOString()
    activeSession.value.chat.push({ role: 'user', content: trimmed, ts: now })
    activeSession.value.updatedAt = now
    saveSession(activeSession.value)

    isResponding.value = true

    const problem = currentProblem.value
    const session = activeSession.value

    try {
      // Build compact digest payload — only changed fields + last 8 chat turns.
      const digest = buildContextDigest(problem, session)
      const recentChat = session.chat.slice(-8).map(m => ({ role: m.role, content: m.content }))

      const payload = {
        problem_id: session.problemId,
        mode: session.mode,
        active_phase: session.activePhase,
        hint_count: session.hintCount ?? 0,
        context_digest: {
          active_phase_title: digest.activePhaseTitle,
          note_summary: digest.noteSummary,
          filled_phases: digest.filledPhases,
          code_types: digest.codeTypes,
          referenced_entities: digest.referencedEntities,
          code_lines: digest.codeLines,
        },
        messages: recentChat,
        problem_meta: {
          title: problem.title,
          difficulty: problem.difficulty,
          tags: problem.tags,
          must_have: problem.framework?.requirements?.must_have ?? [],
          entities: problem.framework?.entities?.classes?.map(c => `${c.name}: ${c.responsibility}`) ?? [],
          design_patterns: problem.framework?.design_patterns?.map(p => `${p.name}: ${p.why}`) ?? [],
          key_phrases: problem.framework?.key_phrases ?? [],
          gotchas: problem.framework?.gotchas ?? [],
          extensibility_test: problem.framework?.extensibility_test ?? '',
        },
      }

      const response = await fetch(getApiUrl('/api/lld-interview/respond'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }).catch(() => null)

      if (response && response.ok) {
        const data = await response.json()
        const reply = String(data.reply ?? '')
        if (reply) {
          session.chat.push({ role: 'assistant', content: reply, ts: new Date().toISOString() })
          session.updatedAt = new Date().toISOString()
          saveSession(session)
          isResponding.value = false
          return
        }
      }
    } catch {
      // Fall through to heuristic fallback
    }

    // Heuristic demo-mode fallback — runs when backend is unavailable.
    await new Promise(resolve => window.setTimeout(resolve, 260))
    const reply = buildAssistantReply(problem, session, trimmed)
    session.chat.push({ role: 'assistant', content: reply, ts: new Date().toISOString() })
    session.updatedAt = new Date().toISOString()
    saveSession(session)
    isResponding.value = false
  }

  function submitSession() {
    if (!activeSession.value || !currentProblem.value) return
    activeSession.value.status = 'completed'
    activeSession.value.paused = true
    activeSession.value.report = buildReport(currentProblem.value, activeSession.value)
    activeSession.value.updatedAt = new Date().toISOString()
    saveSession(activeSession.value)
    stopTimer()
  }

  function restartSession(mode?: LLDInterviewMode) {
    if (!activeSession.value) return
    startSession(activeSession.value.problemId, mode ?? activeSession.value.mode)
  }

  return {
    activeSession,
    currentProblem,
    isResponding,
    lastSavedAt,
    frameworkPhases: LLD_FRAMEWORK_PHASES,
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
  }
}
