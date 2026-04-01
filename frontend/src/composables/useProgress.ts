import { reactive, computed, watch } from 'vue'
import type { Progress } from '../types'

const STORAGE_KEY = 'dsa-pattern-progress'

function loadFromStorage(): Progress {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (!parsed.code) parsed.code = {}
      if (!parsed.notes) parsed.notes = {}
      if (!parsed.reflections) parsed.reflections = {}
      if (!parsed.solved) parsed.solved = {}
      return parsed
    }
  } catch (e) {
    console.warn('Failed to load progress from localStorage:', e)
  }
  return { solved: {}, notes: {}, code: {}, reflections: {} }
}

const state = reactive<Progress>(loadFromStorage())

// Debounce helper — coalesces rapid bursts (e.g. typing) into one write.
let _persistTimer: ReturnType<typeof setTimeout> | null = null
function schedulePersist() {
  if (_persistTimer !== null) clearTimeout(_persistTimer)
  _persistTimer = setTimeout(() => {
    _persistTimer = null
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
    } catch (e) {
      console.warn('Failed to persist progress to localStorage:', e)
    }
  }, 600)
}

// Auto-persist on changes — debounced so rapid typing doesn't hammer JSON.stringify
watch(() => state, () => {
  schedulePersist()
}, { deep: true })

// Sync state across multiple tabs
if (typeof window !== 'undefined') {
  window.addEventListener('storage', (event) => {
    if (event.key === STORAGE_KEY && event.newValue) {
      try {
        const newData = JSON.parse(event.newValue)
        Object.assign(state, newData)
      } catch (e) {
        console.warn('Failed to sync state from storage event:', e)
      }
    }
  })
}

export function useProgress() {
  function markSolved(slug: string, confidence: 1 | 2 | 3, score?: number, reasoning?: string[]) {
    const existing = state.solved[slug]
    state.solved[slug] = {
      date: new Date().toISOString(),
      confidence,
      score: score ?? existing?.score,
      reasoning: reasoning ?? existing?.reasoning,
    }
  }

  function unmarkSolved(slug: string) {
    delete state.solved[slug]
  }

  function isSolved(slug: string): boolean {
    return slug in state.solved
  }

  function getConfidence(slug: string): 1 | 2 | 3 | null {
    return state.solved[slug]?.confidence ?? null
  }

  function addNote(slug: string, note: string) {
    state.notes[slug] = note
  }

  function getNote(slug: string): string {
    return state.notes[slug] ?? ''
  }

  function addReflection(slug: string, reflection: { pattern: string; signal: string; deviation: string }) {
    state.reflections[slug] = reflection
  }

  function getReflection(slug: string) {
    return state.reflections[slug] ?? null
  }

  function addCode(slug: string, code: string) {
    state.code[slug] = code
  }

  function getCode(slug: string): string {
    return state.code[slug] ?? ''
  }

  /** Get problems due for spaced repetition review */
  function getDueForReview(): string[] {
    const now = Date.now()
    const due: string[] = []

    for (const [slug, info] of Object.entries(state.solved)) {
      const solvedAt = new Date(info.date).getTime()
      const daysSince = (now - solvedAt) / (1000 * 60 * 60 * 24)

      // Spaced repetition intervals based on confidence
      const interval = info.confidence === 1 ? 1 : info.confidence === 2 ? 3 : 7
      if (daysSince >= interval) {
        due.push(slug)
      }
    }

    return due
  }

  const totalSolved = computed(() => Object.keys(state.solved).length)

  function patternCompletion(slugs: string[]): number {
    if (slugs.length === 0) return 0
    const solved = slugs.filter(s => isSolved(s)).length
    return Math.round((solved / slugs.length) * 100)
  }

  function exportProgress(): string {
    return JSON.stringify(state, null, 2)
  }

  function importProgress(json: string) {
    try {
      const imported = JSON.parse(json)
      Object.assign(state, imported)
    } catch (e) {
      console.error('Failed to import progress:', e)
    }
  }

  return {
    state,
    markSolved,
    unmarkSolved,
    isSolved,
    getConfidence,
    addNote,
    getNote,
    addReflection,
    getReflection,
    addCode,
    getCode,
    getDueForReview,
    totalSolved,
    patternCompletion,
    exportProgress,
    importProgress,
  }
}
