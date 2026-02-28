import { usePatterns } from './usePatterns'
import { useProgress } from './useProgress'
import { useRouter } from 'vue-router'
import type { Problem } from '../types'

/**
 * Smart Random Problem Selector
 *
 * Goals:
 * 1) Keep recommendations relevant to your current learning state.
 * 2) Avoid repetitive picks (duplicate feeling) across consecutive smart-random clicks.
 * 3) Stay probabilistic, not deterministic, so sessions still feel random.
 *
 * How it works (pipeline):
 * - Step A: compute a learning weight for each candidate.
 * - Step B: remove the current problem + most recent smart-random pick to prevent instant repeats.
 * - Step C: prefer "unseen recently" candidates first (freshness window).
 * - Step D: if pool is exhausted, keep all candidates but apply a recency penalty instead.
 * - Step E: weighted random draw over the final pool.
 *
 * Learning weight factors (higher = more likely):
 * - Unsolved bonus: unsolved problems get a large base weight.
 * - Confidence resurfacing: confidence-1 and confidence-2 problems can return; confidence-3 is skipped.
 * - Difficulty ladder: Easy -> Medium -> Hard preference based on pattern progress.
 * - Pattern momentum: recently active patterns get boosted.
 * - Stale-pattern nudge: untouched patterns get a small boost.
 * - Bridge bonus: in_both problems get a bonus.
 *
 * Duplicate handling:
 * - Persists recent smart-random picks in localStorage (`dsa-smart-random-history`).
 * - Blocks immediate back-to-back repeats.
 * - Avoids recently picked slugs while alternatives exist.
 * - Falls back gracefully with recency penalties when the candidate pool is small.
 *
 * ---------------------------------------------------------------------------
 * Worked scoring examples (simplified, before random jitter):
 *
 * Example A: Fresh learner, unsolved Easy in a new pattern
 * - solved? no => +100
 * - pattern progress < 0.3 and difficulty Easy => +30
 * - solvedInPattern === 0 => +15
 * - in_both? yes => +10
 * - momentum? none yet => +0
 * Total base = 155 (then +0..15 jitter)
 *
 * Example B: Solved problem with confidence=1, medium phase pattern
 * - solved? yes, confidence=1 => +40
 * - pattern progress 0.45 and difficulty Medium => +25
 * - recent pattern activity in last 24h => +20
 * - in_both? no => +0
 * Total base = 85 (then +0..15 jitter)
 *
 * Example C: Solved problem with confidence=3
 * - confidence=3 => weight 0 (excluded from candidate pool)
 *
 * Benefit summary from these examples:
 * - A gets highest probability: pushes forward unsolved, right-difficulty work.
 * - B still resurfaces for reinforcement: weak memories are revisited.
 * - C is skipped: prevents wasting picks on already-solid problems.
 *
 * ---------------------------------------------------------------------------
 * Duplicate-control examples:
 *
 * Example D: Immediate repeat protection
 * - Last smart-random pick was `two-sum`.
 * - Next click excludes `two-sum` (if at least one other candidate exists).
 * - Result: no back-to-back duplicate.
 *
 * Example E: Recent-window freshness
 * - Recent history: [A, B, C, D], and there are other valid candidates.
 * - Pool first prefers candidates not in recent history.
 * - Result: better topic rotation and less "same few questions" feeling.
 *
 * Example F: Small pool fallback
 * - Only recently seen candidates remain.
 * - They are reintroduced with recency penalty multiplier (0.2 to 1.0).
 * - Result: selector never gets stuck, but still biases away from repeats.
 */

const SMART_RANDOM_HISTORY_KEY = 'dsa-smart-random-history'
const MAX_HISTORY = 40
const RECENT_WINDOW = 12

export function useSmartRandom() {
  const { getAllProblems, patterns } = usePatterns()
  const { isSolved, getConfidence, state } = useProgress()
  const router = useRouter()

  function loadHistory(): string[] {
    try {
      const raw = localStorage.getItem(SMART_RANDOM_HISTORY_KEY)
      if (!raw) return []
      const parsed = JSON.parse(raw)
      return Array.isArray(parsed) ? parsed.filter(v => typeof v === 'string') : []
    } catch {
      return []
    }
  }

  function saveHistory(history: string[]) {
    localStorage.setItem(SMART_RANDOM_HISTORY_KEY, JSON.stringify(history.slice(0, MAX_HISTORY)))
  }

  function recordPick(slug: string) {
    const next = [slug, ...loadHistory().filter(s => s !== slug)]
    saveHistory(next)
  }

  function getRecencyMultiplier(slug: string, history: string[], recentWindowSize: number): number {
    if (recentWindowSize <= 0) return 1
    const idx = history.indexOf(slug)
    if (idx === -1) return 1
    const closeness = (recentWindowSize - Math.min(idx, recentWindowSize)) / recentWindowSize
    // Most recent gets strongest penalty, older entries are penalized less.
    // Example: recentWindowSize=10
    // - idx=0  => closeness=1.0 => multiplier=max(0.2, 1-0.8)=0.2
    // - idx=5  => closeness=0.5 => multiplier=max(0.2, 1-0.4)=0.6
    // - idx=10 => closeness=0.0 => multiplier=1.0
    return Math.max(0.2, 1 - closeness * 0.8)
  }

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
    // If two problems have very similar score, jitter avoids deterministic loops.
    // Example: 120 vs 121 can occasionally flip, improving session variety.
    weight += Math.random() * 15

    return weight
  }

  function pickSmartProblem(excludeSlug?: string): Problem | null {
    const history = loadHistory()
    const lastPickedSlug = history[0]

    let all = getAllProblems().filter(p => p.slug !== excludeSlug)
    if (all.length === 0) return null

    // Hard guard: avoid immediate repeats from Smart Random history.
    // Example: if previous pick is "valid-anagram", next selection excludes it
    // whenever at least one alternate candidate is available.
    if (lastPickedSlug && all.length > 1) {
      all = all.filter(p => p.slug !== lastPickedSlug)
    }

    // Calculate weights
    const weighted = all.map(p => ({ problem: p, weight: getSmartWeight(p) }))
      .filter(w => w.weight > 0)

    if (weighted.length === 0) return null

    const recentWindowSize = Math.min(RECENT_WINDOW, Math.max(weighted.length - 1, 0))
    const recentSet = new Set(history.slice(0, recentWindowSize))
    const unseenRecently = weighted.filter(w => !recentSet.has(w.problem.slug))

    // Prefer fresh candidates first; if exhausted, keep all with recency penalties.
    // This keeps diversity high in large pools and remains functional in small pools.
    const pool = unseenRecently.length > 0
      ? unseenRecently
      : weighted.map(w => ({
          problem: w.problem,
          weight: w.weight * getRecencyMultiplier(w.problem.slug, history, recentWindowSize),
        })).filter(w => w.weight > 0)

    if (pool.length === 0) return null

    // Performs a weighted random selection from the candidate pool
    // -------------- CONCEPT --------------
    //   - Roulette wheel selection picks an item based on weights proportional to their probabilities.
    // - Example with weights [2, 3, 5]: total weight = 10.
    // - Generate random number r from 0 (inclusive) to total weight (exclusive), e.g., r = 4.7.
    // - Iterate subtracting each weight from r:
    //     - r - 2 = 2.7 (still > 0), move to next weight
    //     - r - 3 = -0.3 (now ≤ 0), select this item (second item).
    // - This sampling is fair, giving each item a chance proportional to its weight.
    // - Edge case fallback: if not selected by loop, return last item to handle floating-point or rounding issues.
    // - In JS, Math.random() returns [0,1), scaled by total weights for r, ensuring coverage across intervals.

    // ------------------ Example ------------------
    // Suppose:
    //   - A: weight 50
    //   - B: weight 30
    //   - C: weight 20
    //   totalWeight = 100, so:

    //   - A should be picked ~50%
    //   - B ~30%
    //   - C ~20%
    //   If Math.random() gives 0.62, then:
    //   - random = 0.62 * 100 = 62
    //   - Subtract A(50) → 12 (still > 0)
    //   - Subtract B(30) → -18 (<= 0) → pick B

    //   If random had been 18, A would be picked.
    //   If random had been 95, A then B then C, so C is picked.

    //   So bigger weight = bigger interval on [0, totalWeight) = higher chance.

    // ------------ Need for this ------------
    // - If you always pick highest weight, recommendations become deterministic and repetitive.
    // - Weighted random gives bias, not absolute rule: high-weight items appear more often, low-weight items still appear sometimes.
    // - That balance improves learning: strong prioritization + enough variety/exploration.

    // Why allowing low-weight picks helps:

    // - Prevents “same top 3 problems forever”.
    // - Avoids starvation of medium/low items.
    // - Keeps sessions fresh and can surface useful edge cases.
    // - Probabilities still favor important items strongly.

    // Example:

    // - Weights: A=100, B=20, C=5 (total 125)
    // - Probabilities:
    //     - A ≈ 80%
    //     - B ≈ 16%
    //     - C ≈ 4%
    //       So low-weight C can be picked, but rarely.

    const totalWeight = pool.reduce((sum, w) => sum + w.weight, 0)
    let random = Math.random() * totalWeight

    for (const w of pool) {
      random -= w.weight
      if (random <= 0) {
        recordPick(w.problem.slug)
        return w.problem
      }
    }

    // - This is a safety net in case floating-point/edge behavior makes the loop miss a return.
    // - In normal math, loop should pick something; fallback ensures function still returns a valid problem instead of failing.
    const fallback = pool[pool.length - 1]?.problem ?? null
    if (fallback) recordPick(fallback.slug)
    return fallback
  }

  function navigateSmartRandom(excludeSlug?: string) {
    const pick = pickSmartProblem(excludeSlug)
    if (pick) router.push(`/problem/${pick.slug}`)
  }

  return { pickSmartProblem, navigateSmartRandom, getSmartWeight }
}
