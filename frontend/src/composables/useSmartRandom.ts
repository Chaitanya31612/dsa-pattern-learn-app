import { usePatterns } from './usePatterns'
import { useProgress } from './useProgress'
import { useRouter } from 'vue-router'
import type { Problem } from '../types'

/**
 * Smart Random Problem Selector
 *
 * Scoring factors (higher = more likely to be picked):
 * 1. Unsolved bonus        — unsolved problems get a large base weight
 * 2. Pattern momentum      — problems in patterns where you've been solving get a boost
 * 3. Difficulty ladder     — prefers Easy→Medium→Hard progression per pattern
 * 4. Low confidence review — solved but shaky (confidence 1) problems resurface
 * 5. Stale patterns        — patterns you haven't touched get a slight boost
 * 6. Bridge bonus          — in_both problems get a small bonus (high-value overlap)
 */

export function useSmartRandom() {
  const { getAllProblems, patterns } = usePatterns()
  const { isSolved, getConfidence, state } = useProgress()
  const router = useRouter()

  function getSmartWeight(p: Problem): number {
    let weight = 0
    const solved = isSolved(p.slug)
    const confidence = getConfidence(p.slug)

    // ── 1. Base: unsolved gets large weight ──
    if (!solved) {
      weight += 100
    } else {
      // Low confidence solved problems still surface
      if (confidence === 1) weight += 40
      else if (confidence === 2) weight += 10
      else return 0 // confidence 3 = solid, skip
    }

    // ── 2. Difficulty ladder ──
    // Count solved in this pattern to determine where user is
    const patternSlugs = patterns.value.find(pt => pt.pattern_id === p.pattern_id)?.problem_slugs ?? []
    const solvedInPattern = patternSlugs.filter(s => isSolved(s)).length
    const totalInPattern = patternSlugs.length
    const patternProgress = totalInPattern > 0 ? solvedInPattern / totalInPattern : 0

    // Prefer Easy early, Medium mid, Hard late
    const diffOrder: Record<string, number> = { Easy: 0, Medium: 1, Hard: 2 }
    const diffLevel = diffOrder[p.difficulty ?? 'Medium'] ?? 1

    if (patternProgress < 0.3 && diffLevel === 0) weight += 30      // Early: prefer Easy
    else if (patternProgress < 0.7 && diffLevel === 1) weight += 25  // Mid: prefer Medium
    else if (patternProgress >= 0.7 && diffLevel === 2) weight += 20 // Late: prefer Hard

    // ── 3. Pattern momentum ──
    // Check how recently user solved something in this pattern
    const recentSolves = patternSlugs
      .filter(s => isSolved(s))
      .map(s => state.solved[s]?.date ? new Date(state.solved[s].date).getTime() : 0)

    if (recentSolves.length > 0) {
      const lastSolve = Math.max(...recentSolves)
      const hoursSince = (Date.now() - lastSolve) / (1000 * 60 * 60)
      // Recent activity (within 24h) = momentum boost
      if (hoursSince < 24) weight += 20
      else if (hoursSince < 72) weight += 10
    }

    // ── 4. Stale pattern boost ──
    // If no progress in this pattern at all, give a nudge
    if (solvedInPattern === 0 && !solved) {
      weight += 15
    }

    // ── 5. Bridge bonus ──
    if (p.in_both) weight += 10

    // ── 6. Small random jitter to avoid always picking the same one ──
    weight += Math.random() * 15

    return weight
  }

  function pickSmartProblem(excludeSlug?: string): Problem | null {
    const all = getAllProblems().filter(p => p.slug !== excludeSlug)
    if (all.length === 0) return null

    // Calculate weights
    const weighted = all.map(p => ({ problem: p, weight: getSmartWeight(p) }))
      .filter(w => w.weight > 0)

    if (weighted.length === 0) return null

    // Weighted random selection
    const totalWeight = weighted.reduce((sum, w) => sum + w.weight, 0)
    let random = Math.random() * totalWeight

    for (const w of weighted) {
      random -= w.weight
      if (random <= 0) return w.problem
    }

    return weighted[weighted.length - 1]?.problem ?? null
  }

  function navigateSmartRandom(excludeSlug?: string) {
    const pick = pickSmartProblem(excludeSlug)
    if (pick) router.push(`/problem/${pick.slug}`)
  }

  return { pickSmartProblem, navigateSmartRandom, getSmartWeight }
}
