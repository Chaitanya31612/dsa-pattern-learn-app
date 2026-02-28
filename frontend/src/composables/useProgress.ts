import { reactive, computed, watch } from 'vue'
import type { Progress } from '../types'

const STORAGE_KEY = 'dsa-pattern-progress'

function loadFromStorage(): Progress {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch (e) {
    console.warn('Failed to load progress from localStorage:', e)
  }
  return { solved: {}, notes: {}, reflections: {} }
}

const state = reactive<Progress>(loadFromStorage())

// Auto-persist on changes
watch(() => state, () => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
}, { deep: true })

export function useProgress() {
  function markSolved(slug: string, confidence: 1 | 2 | 3) {
    state.solved[slug] = {
      date: new Date().toISOString(),
      confidence,
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
    getDueForReview,
    totalSolved,
    patternCompletion,
    exportProgress,
    importProgress,
  }
}
