<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { usePatterns } from '../composables/usePatterns'
import { useProgress } from '../composables/useProgress'

const { patterns, problems, meta, loading, getAllProblems } = usePatterns()
const { state, totalSolved, patternCompletion, getDueForReview } = useProgress()

const overallPercent = computed(() => {
  if (!meta.value.total_problems) return 0
  return Math.round((totalSolved.value / meta.value.total_problems) * 100)
})

const dueCount = computed(() => getDueForReview().length)
const animatedSolved = ref(0)
const animatedPercent = ref(0)
const animatedDueCount = ref(0)

const sortBy = ref<'order' | 'progress' | 'count'>('order')

const sortedPatterns = computed(() => {
  const list = [...patterns.value]
  if (sortBy.value === 'progress') {
    list.sort((a, b) => patternCompletion(b.problem_slugs) - patternCompletion(a.problem_slugs))
  } else if (sortBy.value === 'count') {
    list.sort((a, b) => b.problem_count - a.problem_count)
  }
  return list
})

const dailyChallenge = computed(() => {
  const all = getAllProblems()
  if (!all.length) return null

  const today = new Date().toISOString().slice(0, 10)
  let hash = 0
  for (const ch of today) {
    hash = ((hash << 5) - hash) + ch.charCodeAt(0)
    hash |= 0
  }

  const index = Math.abs(hash) % all.length
  return all[index] ?? null
})

const recentActivity = computed(() => {
  return Object.entries(state.solved)
    .map(([slug, info]) => {
      const problem = problems.value[slug]
      if (!problem) return null
      return {
        slug,
        title: problem.title,
        patternName: problem.pattern_name,
        confidence: info.confidence,
        date: info.date,
      }
    })
    .filter((item): item is {
      slug: string
      title: string
      patternName: string
      confidence: 1 | 2 | 3
      date: string
    } => item !== null)
    .sort((a, b) => +new Date(b.date) - +new Date(a.date))
    .slice(0, 5)
})

function animateNumber(target: number, output: { value: number }, duration = 650) {
  const startValue = output.value
  const delta = target - startValue
  const startTime = performance.now()

  const frame = (now: number) => {
    const progress = Math.min((now - startTime) / duration, 1)
    output.value = Math.round(startValue + delta * progress)
    if (progress < 1) requestAnimationFrame(frame)
  }

  requestAnimationFrame(frame)
}

watch(totalSolved, (value) => animateNumber(value, animatedSolved), { immediate: true })
watch(overallPercent, (value) => animateNumber(value, animatedPercent), { immediate: true })
watch(dueCount, (value) => animateNumber(value, animatedDueCount), { immediate: true })

function confidenceLabel(level: 1 | 2 | 3): string {
  if (level === 3) return 'Solid'
  if (level === 2) return 'Okay'
  return 'Shaky'
}

function formatActivityDate(value: string): string {
  return new Date(value).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  })
}

function getPatternAccent(index: number): string {
  const accents = [
    'var(--accent-cyan)',
    'var(--accent-green)',
    'var(--accent-orange)',
    'var(--accent-purple)',
    'var(--accent-pink)',
    'var(--accent-yellow)',
    'var(--accent-red)',
  ]
  return accents[index % accents.length] ?? 'var(--accent-cyan)'
}
</script>

<template>
  <div class="container dashboard" v-if="!loading">
    <!-- ═══ Hero Stats ═══ -->
    <section class="hero animate-in">
      <div class="hero-content">
        <h1 class="hero-title">
          <span class="hero-greeting terminal-prompt">./grind --mode=patterns</span>
          Pattern Mastery
        </h1>
        <p class="hero-desc">
          Master DSA through pattern recognition. {{ meta.total_problems }} problems across
          {{ meta.total_patterns }} patterns.
        </p>
      </div>

      <div class="hero-stats">
        <div class="stat-card">
          <div class="stat-ring" :style="{ '--pct': animatedPercent }">
            <svg viewBox="0 0 36 36">
              <path class="ring-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              <path class="ring-fill" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                :stroke-dasharray="`${animatedPercent}, 100`" />
            </svg>
            <span class="ring-label">{{ animatedPercent }}%</span>
          </div>
          <div class="stat-info">
            <span class="stat-number">{{ animatedSolved }}</span>
            <span class="stat-text">solved</span>
          </div>
        </div>

        <div class="stat-card stat-difficulty">
          <div class="diff-row">
            <span class="diff-dot" style="background: var(--diff-easy)"></span>
            <span class="diff-label">Easy</span>
            <span class="diff-count mono">{{ meta.difficulty_distribution.Easy || 0 }}</span>
          </div>
          <div class="diff-row">
            <span class="diff-dot" style="background: var(--diff-medium)"></span>
            <span class="diff-label">Medium</span>
            <span class="diff-count mono">{{ meta.difficulty_distribution.Medium || 0 }}</span>
          </div>
          <div class="diff-row">
            <span class="diff-dot" style="background: var(--diff-hard)"></span>
            <span class="diff-label">Hard</span>
            <span class="diff-count mono">{{ meta.difficulty_distribution.Hard || 0 }}</span>
          </div>
        </div>

        <router-link to="/review" class="stat-card stat-card-link" v-if="dueCount > 0">
          <div class="stat-info">
            <span class="stat-number" style="color: var(--accent-orange)">{{ animatedDueCount }}</span>
            <span class="stat-text">due for review →</span>
          </div>
        </router-link>
      </div>
    </section>

    <!-- <section class="utility-hub card card-flat animate-in stagger-1">
      <div class="utility-column utility-recent">
        <h3 class="utility-title">Recent Activity</h3>
        <ul class="activity-list" v-if="recentActivity.length">
          <li v-for="item in recentActivity" :key="item.slug" class="activity-item">
            <router-link :to="`/problem/${item.slug}`" class="activity-link">
              <span class="activity-title">{{ item.title }}</span>
              <span class="activity-meta">
                {{ item.patternName }} · {{ confidenceLabel(item.confidence) }} · {{ formatActivityDate(item.date) }}
              </span>
            </router-link>
          </li>
        </ul>
        <p v-else class="activity-empty">No solved problems yet. Start with a daily challenge.</p>
      </div>

      <div class="utility-column utility-actions">
        <h3 class="utility-title">Quick Actions</h3>
        <div class="quick-actions-stack">
          <router-link class="quick-action" :to="dailyChallenge ? `/problem/${dailyChallenge.slug}` : '/problems'">
            <span class="quick-icon">🎯</span>
            <div>
              <span class="quick-name">Daily Challenge</span>
              <span class="quick-meta">
                {{ dailyChallenge ? dailyChallenge.title : 'Pick a random problem' }}
              </span>
            </div>
          </router-link>

          <router-link class="quick-action" to="/mock-interview">
            <span class="quick-icon">🧠</span>
            <div>
              <span class="quick-name">Start Interview</span>
              <span class="quick-meta">Practice under timed pressure</span>
            </div>
          </router-link>

          <router-link class="quick-action" to="/quiz">
            <span class="quick-icon">🧩</span>
            <div>
              <span class="quick-name">Pattern Quiz</span>
              <span class="quick-meta">Sharpen recognition speed</span>
            </div>
          </router-link>
        </div>
      </div>
    </section> -->

    <!-- ═══ Sort bar ═══ -->
    <section class="sort-bar animate-in stagger-2">
      <span class="section-label terminal-prompt">patterns.sort_by</span>
      <div class="tab-bar">
        <button class="tab-btn" :class="{ active: sortBy === 'order' }" @click="sortBy = 'order'">
          Learning Order
        </button>
        <button class="tab-btn" :class="{ active: sortBy === 'progress' }" @click="sortBy = 'progress'">
          Progress
        </button>
        <button class="tab-btn" :class="{ active: sortBy === 'count' }" @click="sortBy = 'count'">
          Problem Count
        </button>
      </div>
    </section>

    <!-- ═══ Pattern Grid ═══ -->
    <section class="pattern-grid">
      <router-link
        v-for="(pattern, idx) in sortedPatterns"
        :key="pattern.pattern_id"
        :to="`/pattern/${pattern.pattern_id}`"
        class="pattern-card card animate-in"
        :class="`stagger-${Math.min(idx % 7 + 1, 6)}`"
        :style="{ '--card-accent': getPatternAccent(idx) }"
      >
        <div class="pattern-header">
          <span class="pattern-idx mono">{{ String(idx + 1).padStart(2, '0') }}</span>
          <span class="pattern-problems mono">{{ pattern.problem_count }} problems</span>
        </div>

        <h3 class="pattern-name">{{ pattern.name }}</h3>

        <p class="pattern-model">{{ pattern.mental_model }}</p>

        <div class="pattern-footer">
          <div class="progress-bar">
            <div
              class="progress-fill"
              :style="{
                width: patternCompletion(pattern.problem_slugs) + '%',
                background: `linear-gradient(90deg, ${getPatternAccent(idx)}, ${getPatternAccent(idx)}88)`
              }"
            ></div>
          </div>
          <span class="pattern-pct mono">{{ patternCompletion(pattern.problem_slugs) }}%</span>
        </div>

        <div class="pattern-glow" :style="{ background: getPatternAccent(idx) }"></div>
      </router-link>
    </section>
  </div>

  <div class="container loading-state" v-else>
    <div class="terminal-prompt">loading database...</div>
  </div>
</template>

<style scoped>
/* ── Hero ─────────────────────────────────────── */
.hero {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: var(--space-2xl);
  margin-bottom: var(--space-2xl);
  align-items: center;
}

.hero-greeting {
  display: block;
  font-size: var(--text-sm);
  margin-bottom: var(--space-sm);
}

.hero-title {
  font-size: var(--text-3xl);
  font-weight: 800;
  background: linear-gradient(135deg, var(--text-primary), var(--accent-cyan));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-desc {
  color: var(--text-secondary);
  margin-top: var(--space-sm);
  font-size: var(--text-base);
  max-width: 420px;
}

.hero-stats {
  display: flex;
  gap: var(--space-md);
  align-items: stretch;
}

.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-md) var(--space-lg);
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.stat-ring {
  width: 56px;
  height: 56px;
  position: relative;
}

.stat-ring svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.ring-bg {
  fill: none;
  stroke: var(--bg-input);
  stroke-width: 2.5;
}

.ring-fill {
  fill: none;
  stroke: var(--accent-cyan);
  stroke-width: 2.5;
  stroke-linecap: round;
  transition: stroke-dasharray var(--transition-slow);
}

.ring-label {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 700;
  color: var(--accent-cyan);
}

.stat-number {
  display: block;
  font-family: var(--font-mono);
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--accent-green);
}

.stat-text {
  font-size: var(--text-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-difficulty {
  flex-direction: column;
  gap: var(--space-xs);
  padding: var(--space-sm) var(--space-lg);
}

.diff-row {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: var(--text-sm);
}

.diff-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.diff-label {
  color: var(--text-secondary);
  min-width: 55px;
}

.diff-count {
  color: var(--text-primary);
  font-weight: 600;
  font-size: var(--text-xs);
}

/* ── Utility Hub ───────────────────────────────────── */
.utility-hub {
  display: grid;
  grid-template-columns: 1.45fr 0.95fr;
  gap: var(--space-md);
  margin-bottom: var(--space-xl);
  padding: var(--space-md);
}

.utility-column {
  min-width: 0;
}

.utility-recent {
  padding-right: var(--space-sm);
}

.utility-actions {
  border-left: 1px solid var(--border-subtle);
  padding-left: var(--space-md);
}

.utility-title {
  font-size: var(--text-base);
  margin-bottom: var(--space-sm);
}

.quick-actions-stack {
  display: grid;
  gap: var(--space-sm);
}

.quick-action {
  display: flex;
  gap: var(--space-sm);
  align-items: flex-start;
  padding: var(--space-sm) var(--space-md);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  transition: all var(--transition-fast);
  color: inherit;
}

.quick-action:hover {
  border-color: var(--accent-cyan);
  transform: translateY(-1px);
}

.quick-icon {
  font-size: var(--text-lg);
  line-height: 1;
}

.quick-name {
  display: block;
  font-weight: 600;
  color: var(--text-primary);
  font-size: var(--text-sm);
}

.quick-meta {
  display: block;
  color: var(--text-muted);
  font-size: var(--text-xs);
  margin-top: 2px;
  line-height: 1.4;
}

.activity-list {
  list-style: none;
  display: grid;
  gap: 6px;
}

.activity-item {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
}

.activity-link {
  display: block;
  padding: 10px var(--space-sm);
  color: inherit;
}

.activity-link:hover .activity-title {
  color: var(--accent-cyan);
}

.activity-title {
  display: block;
  font-size: var(--text-sm);
  color: var(--text-primary);
  font-weight: 600;
  transition: color var(--transition-fast);
}

.activity-meta {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.activity-empty {
  color: var(--text-muted);
  font-size: var(--text-sm);
}

/* ── Sort Bar ─────────────────────────────────── */
.sort-bar {
  display: flex;
  align-items: center;
  gap: var(--space-lg);
  margin-bottom: var(--space-xl);
}

.section-label {
  white-space: nowrap;
}

/* ── Pattern Grid ─────────────────────────────── */
.pattern-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--space-md);
}

.pattern-card {
  text-decoration: none;
  color: inherit;
  cursor: pointer;
  position: relative;
}

.pattern-card:hover {
  border-color: var(--card-accent, var(--accent-cyan));
}

.pattern-card:hover .pattern-glow {
  opacity: 0.06;
}

.pattern-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-sm);
}

.pattern-idx {
  color: var(--card-accent, var(--accent-cyan));
  font-size: var(--text-xs);
  font-weight: 700;
  opacity: 0.7;
}

.pattern-problems {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.pattern-name {
  font-size: var(--text-lg);
  font-weight: 700;
  margin-bottom: var(--space-sm);
  color: var(--text-primary);
}

.pattern-model {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: var(--space-md);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.pattern-footer {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.pattern-footer .progress-bar {
  flex: 1;
}

.pattern-pct {
  color: var(--text-muted);
  font-size: var(--text-xs);
  font-weight: 600;
  min-width: 32px;
  text-align: right;
}

.pattern-glow {
  position: absolute;
  bottom: -20px;
  right: -20px;
  width: 100px;
  height: 100px;
  border-radius: 50%;
  filter: blur(40px);
  opacity: 0;
  transition: opacity var(--transition-base);
  pointer-events: none;
}

/* ── Bridge Problems ──────────────────────────── */
.bridge-section {
  margin-top: var(--space-2xl);
}

.bridge-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--space-sm);
}

.bridge-card {
  text-decoration: none;
  color: inherit;
  padding: var(--space-md);
  position: relative;
  transition: all var(--transition-fast);
  border-left: 3px solid var(--accent-purple);
}

.bridge-card:hover {
  border-color: var(--accent-cyan);
}

.bridge-solved {
  opacity: 0.5;
}

.bridge-top {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: 6px;
}

.bridge-num {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.bridge-title {
  display: block;
  font-weight: 600;
  font-size: var(--text-sm);
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.bridge-pattern {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.bridge-check {
  position: absolute;
  top: var(--space-sm);
  right: var(--space-sm);
  color: var(--accent-green);
  font-size: var(--text-sm);
  font-weight: 700;
}

/* ── Loading ──────────────────────────────────── */
.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  font-size: var(--text-lg);
}

/* ── Responsive ───────────────────────────────── */
@media (max-width: 768px) {
  .hero {
    grid-template-columns: 1fr;
    gap: var(--space-lg);
  }

  .hero-stats {
    flex-wrap: wrap;
  }

  .sort-bar {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-sm);
  }

  .utility-hub {
    grid-template-columns: 1fr;
  }

  .utility-actions {
    border-left: none;
    border-top: 1px solid var(--border-subtle);
    padding-left: 0;
    padding-top: var(--space-sm);
  }

  .quick-actions-stack {
    grid-template-columns: 1fr;
  }

  .pattern-grid {
    grid-template-columns: 1fr;
  }

  .bridge-grid {
    grid-template-columns: 1fr;
  }
}
</style>
