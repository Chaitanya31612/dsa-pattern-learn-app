import { ref, computed } from 'vue'
import type { Database, Pattern, Problem } from '../types'

const db = ref<Database | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
let loaded = false

async function loadDb() {
  if (loaded) return
  loading.value = true
  try {
    const resp = await fetch('/db.json')
    if (!resp.ok) throw new Error(`Failed to load db.json: ${resp.status}`)
    db.value = await resp.json()
    loaded = true
  } catch (e: any) {
    error.value = e.message
    console.error('Failed to load database:', e)
  } finally {
    loading.value = false
  }
}

export function usePatterns() {
  if (!loaded) loadDb()

  const patterns = computed<Pattern[]>(() => db.value?.patterns ?? [])

  const problems = computed<Record<string, Problem>>(() => db.value?.problems ?? {})

  const patternOrder = computed<string[]>(() => db.value?.pattern_order ?? [])

  function getPattern(id: string): Pattern | undefined {
    return patterns.value.find(p => p.pattern_id === id)
  }

  function getProblemsForPattern(patternId: string): Problem[] {
    const pattern = getPattern(patternId)
    if (!pattern) return []
    return pattern.problem_slugs
      .map(slug => problems.value[slug])
      .filter(Boolean)
  }

  function getAllProblems(): Problem[] {
    return Object.values(problems.value)
  }

  const meta = computed(() => db.value?.meta ?? {
    total_problems: 0,
    total_patterns: 0,
    difficulty_distribution: {},
  })

  return {
    patterns,
    problems,
    patternOrder,
    loading,
    error,
    meta,
    getPattern,
    getProblemsForPattern,
    getAllProblems,
  }
}
