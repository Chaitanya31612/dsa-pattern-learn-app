import { computed, ref } from 'vue'
import { LLD_COACHING_STRATEGY, LLD_FRAMEWORK_PHASES, LLD_PROBLEMS as HARDCODED_PROBLEMS } from '../data/lldProblems'
import type { LLDCatalogProblem } from '../types'

/**
 * useLLDProblems
 * --------------
 * Loads LLD problem catalog from lld-db.json first (public/lld-db.json).
 * Falls back to the hardcoded lldProblems.ts data for any problem ID that
 * is not found in the JSON file, so we never lose data during deep-dive migration.
 *
 * Loading strategy:
 * 1. Fetch /lld-db.json on first call (cached in module-level ref).
 * 2. Merge: for each hardcoded problem, check if JSON has a richer version.
 * 3. JSON wins if it has the full framework block; otherwise hardcoded wins.
 */

type LLDDatabase = {
  version: string
  problems: LLDCatalogProblem[]
}

// Module-level cache so the fetch only happens once per app lifetime.
const jsonProblemsCache = ref<LLDCatalogProblem[] | null>(null)
const jsonLoadError = ref<string | null>(null)
const jsonLoading = ref(false)
let jsonLoadPromise: Promise<void> | null = null

function hasFullFramework(problem: LLDCatalogProblem): boolean {
  // A problem from lld-db.json is considered "deep-dive ready" only when it has
  // the full framework block with requirements, entities, and design patterns.
  return (
    Array.isArray(problem.framework?.requirements?.must_have) &&
    problem.framework.requirements.must_have.length > 0 &&
    Array.isArray(problem.framework?.entities?.classes) &&
    problem.framework.entities.classes.length > 0
  )
}

async function loadJsonProblems(): Promise<void> {
  if (jsonProblemsCache.value !== null) return

  jsonLoading.value = true
  try {
    const response = await fetch('/lld-db.json')
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data: LLDDatabase = await response.json()
    if (!Array.isArray(data.problems)) throw new Error('Invalid lld-db.json shape')
    jsonProblemsCache.value = data.problems
  } catch (err) {
    jsonLoadError.value = err instanceof Error ? err.message : 'Failed to load lld-db.json'
    jsonProblemsCache.value = []
  } finally {
    jsonLoading.value = false
  }
}

function getMergedProblems(): LLDCatalogProblem[] {
  const jsonById = new Map<string, LLDCatalogProblem>()
  for (const p of jsonProblemsCache.value ?? []) {
    jsonById.set(p.id, p)
  }

  // Build the merged list: JSON wins for deep-dive problems, hardcoded for the rest.
  const merged: LLDCatalogProblem[] = []
  const seenIds = new Set<string>()

  for (const hardcoded of HARDCODED_PROBLEMS) {
    const jsonVersion = jsonById.get(hardcoded.id)
    if (jsonVersion && hasFullFramework(jsonVersion)) {
      // Deep-dive JSON version exists — merge: JSON provides deep fields, hardcoded
      // provides anything the JSON stub lacks (e.g. guided.phase_hints, checkpoints).
      merged.push({
        ...hardcoded,
        ...jsonVersion,
        // Guided block: prefer JSON if it has phase_hints, else keep hardcoded.
        guided: jsonVersion.guided?.phase_hints ? jsonVersion.guided : hardcoded.guided,
        // Interview block: JSON wins if it has probing_questions, otherwise hardcoded.
        interview: jsonVersion.interview?.probing_questions
          ? jsonVersion.interview
          : { ...hardcoded.interview, ...jsonVersion.interview },
        // deep_dive is JSON-only.
        deep_dive: jsonVersion.deep_dive,
      })
    } else {
      merged.push(hardcoded)
    }
    seenIds.add(hardcoded.id)
  }

  // Any JSON-only problems (not yet in lldProblems.ts) get appended.
  for (const jsonProblem of jsonProblemsCache.value ?? []) {
    if (!seenIds.has(jsonProblem.id) && hasFullFramework(jsonProblem)) {
      merged.push(jsonProblem)
    }
  }

  return merged
}

export function useLLDProblems() {
  // Trigger JSON load once.
  if (!jsonLoadPromise) {
    jsonLoadPromise = loadJsonProblems()
  }

  const problems = computed<LLDCatalogProblem[]>(() => {
    if (jsonProblemsCache.value === null) {
      // JSON not yet loaded — return hardcoded until ready.
      return HARDCODED_PROBLEMS
    }
    return getMergedProblems()
  })

  const loading = computed(() => jsonLoading.value)

  const meta = computed(() => {
    const difficulty = problems.value.reduce<Record<string, number>>((acc, p) => {
      acc[p.difficulty] = (acc[p.difficulty] ?? 0) + 1
      return acc
    }, {})
    return {
      totalProblems: problems.value.length,
      categories: [...new Set(problems.value.map(p => p.category))],
      difficulty,
      tags: [...new Set(problems.value.flatMap(p => p.tags))].sort(),
    }
  })

  function getProblem(id: string): LLDCatalogProblem | undefined {
    return problems.value.find(p => p.id === id)
  }

  /** Whether a given problem has the full deep-dive content from lld-db.json */
  function hasDeepDive(id: string): boolean {
    const p = getProblem(id)
    return Boolean(p?.deep_dive)
  }

  return {
    problems,
    loading,
    meta,
    frameworkPhases: computed(() => LLD_FRAMEWORK_PHASES),
    coachingStrategy: computed(() => LLD_COACHING_STRATEGY),
    getProblem,
    hasDeepDive,
  }
}
