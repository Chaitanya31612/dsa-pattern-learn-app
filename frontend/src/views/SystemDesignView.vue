<script setup lang="ts">
import { computed, ref } from 'vue'
import { useLLDProblems } from '../composables/useLLDProblems'

const { problems, meta, frameworkPhases, coachingStrategy } = useLLDProblems()

const activeTab = ref<'lld' | 'hld'>('lld')
const difficultyFilter = ref<'All' | 'Easy' | 'Medium' | 'Hard'>('All')
const tagFilter = ref('All')
const search = ref('')

const filteredProblems = computed(() => {
  const query = search.value.trim().toLowerCase()
  return problems.value.filter((problem) => {
    const matchesDifficulty = difficultyFilter.value === 'All' || problem.difficulty === difficultyFilter.value
    const matchesTag = tagFilter.value === 'All' || problem.tags.includes(tagFilter.value)
    const haystack = `${problem.title} ${problem.description} ${problem.tags.join(' ')} ${problem.category}`.toLowerCase()
    const matchesSearch = !query || haystack.includes(query)
    return matchesDifficulty && matchesTag && matchesSearch
  })
})

const hardCount = computed(() => problems.value.filter(problem => problem.difficulty === 'Hard').length)
const avgGuided = computed(() => {
  if (!problems.value.length) return 0
  return Math.round(problems.value.reduce((sum, problem) => sum + problem.duration.guided, 0) / problems.value.length)
})
</script>

<template>
  <div class="container system-design-page">
    <section class="design-hero animate-in">
      <div class="hero-copy">
        <p class="terminal-prompt hero-kicker">./grind --mode=system-design</p>
        <h1 class="hero-title">System Design Track</h1>
        <p class="hero-description">
          Build one repeatable LLD interview operating system, then plug new problems into it.
          The goal here is not just solving Parking Lot or Splitwise once. It is reducing every
          future machine round to the same five moves: clarify, model, design, implement, review.
        </p>
        <div class="hero-actions">
          <button class="btn btn-primary" @click="activeTab = 'lld'">Open LLD Track</button>
          <span class="hero-note mono">HLD reserved for the next iteration.</span>
        </div>
      </div>

      <div class="hero-aside">
        <div class="stat-panel">
          <span class="stat-label mono">catalog.problems</span>
          <strong class="stat-value">{{ meta.totalProblems }}</strong>
          <span class="stat-help">All LLD prompts from `project-markdowns/LLD/code`.</span>
        </div>
        <div class="stat-panel accent-cyan">
          <span class="stat-label mono">avg.session</span>
          <strong class="stat-value">{{ avgGuided }} min</strong>
          <span class="stat-help">Guided mode keeps 50 min. Interview mode trims to 45 min.</span>
        </div>
        <div class="stat-panel accent-red">
          <span class="stat-label mono">hard.rounds</span>
          <strong class="stat-value">{{ hardCount }}</strong>
          <span class="stat-help">Harder controller, scheduler, and matching problems for pressure practice.</span>
        </div>
      </div>
    </section>

    <section class="track-switch animate-in stagger-2">
      <div class="tab-bar track-tabs">
        <button class="tab-btn" :class="{ active: activeTab === 'lld' }" @click="activeTab = 'lld'">
          LLD Track
        </button>
        <button class="tab-btn" :class="{ active: activeTab === 'hld' }" @click="activeTab = 'hld'">
          HLD Soon
        </button>
      </div>
    </section>

    <template v-if="activeTab === 'lld'">
      <section class="framework-strip animate-in stagger-3">
        <article class="framework-card card card-glass">
          <div class="section-head">
            <span class="section-label terminal-prompt">lld.framework</span>
            <span class="badge badge-source">machine-coding SOP</span>
          </div>
          <h2>What to rehearse until it becomes automatic</h2>
          <div class="phase-grid">
            <div v-for="phase in frameworkPhases" :key="phase.id" class="phase-pill">
              <span class="phase-index mono">{{ phase.timebox }}</span>
              <strong>{{ phase.title }}</strong>
              <p>{{ phase.focus }}</p>
            </div>
          </div>
        </article>

        <article class="strategy-card card">
          <div class="section-head">
            <span class="section-label terminal-prompt">coach.strategy</span>
          </div>
          <ol class="strategy-list">
            <li v-for="item in coachingStrategy" :key="item">{{ item }}</li>
          </ol>
        </article>
      </section>

      <section class="filters animate-in stagger-4">
        <div class="filter-group search-group">
          <label class="mono" for="lld-search">Search</label>
          <input id="lld-search" v-model="search" class="filter-input" type="text" placeholder="parking, scheduler, state, strategy..." />
        </div>
        <div class="filter-group">
          <label class="mono" for="lld-difficulty">Difficulty</label>
          <select id="lld-difficulty" v-model="difficultyFilter" class="filter-input">
            <option value="All">All</option>
            <option value="Easy">Easy</option>
            <option value="Medium">Medium</option>
            <option value="Hard">Hard</option>
          </select>
        </div>
        <div class="filter-group">
          <label class="mono" for="lld-tag">Focus Tag</label>
          <select id="lld-tag" v-model="tagFilter" class="filter-input">
            <option value="All">All</option>
            <option v-for="tag in meta.tags" :key="tag" :value="tag">{{ tag }}</option>
          </select>
        </div>
        <div class="filter-summary mono">
          showing {{ filteredProblems.length }} / {{ meta.totalProblems }}
        </div>
      </section>

      <section class="problem-grid">
        <router-link
          v-for="problem in filteredProblems"
          :key="problem.id"
          :to="{ name: 'lld-framework', params: { id: problem.id } }"
          class="problem-card card animate-in"
        >
          <div class="problem-card-top">
            <span class="problem-number mono">{{ String(problem.number).padStart(2, '0') }}</span>
            <span
              class="badge"
              :class="{
                'badge-easy': problem.difficulty === 'Easy',
                'badge-medium': problem.difficulty === 'Medium',
                'badge-hard': problem.difficulty === 'Hard',
              }"
            >
              {{ problem.difficulty }}
            </span>
          </div>

          <div class="problem-card-body">
            <h3>{{ problem.title }}</h3>
            <p>{{ problem.description }}</p>
          </div>

          <div class="tag-row">
            <span v-for="tag in problem.tags" :key="tag" class="tag-chip mono">{{ tag }}</span>
          </div>

          <div class="problem-card-bottom">
            <div>
              <span class="meta-label mono">track</span>
              <strong>{{ problem.category }}</strong>
            </div>
            <div>
              <span class="meta-label mono">guided/interview</span>
              <strong>{{ problem.duration.guided }} / {{ problem.duration.interview }} min</strong>
            </div>
          </div>
        </router-link>
      </section>
    </template>

    <section v-else class="hld-placeholder card animate-in">
      <p class="terminal-prompt">system_design.next()</p>
      <h2>HLD track is intentionally not live yet.</h2>
      <p>
        The current build focuses on LLD machine rounds and the interview execution framework.
        HLD can be layered later without changing the top-nav structure.
      </p>
    </section>
  </div>
</template>

<style scoped>
.system-design-page {
  display: grid;
  gap: var(--space-xl);
}

.design-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(320px, 0.9fr);
  gap: var(--space-xl);
  align-items: stretch;
}

.hero-copy,
.hero-aside {
  position: relative;
}

.hero-copy {
  padding: var(--space-xl);
  border-radius: var(--radius-xl);
  border: 1px solid color-mix(in srgb, var(--accent-cyan) 18%, transparent);
  background:
    radial-gradient(circle at top left, color-mix(in srgb, var(--accent-cyan) 16%, transparent), transparent 32%),
    linear-gradient(145deg, color-mix(in srgb, var(--bg-card) 92%, transparent), var(--bg-secondary));
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

.hero-copy::after {
  content: '';
  position: absolute;
  inset: auto -10% -35% auto;
  width: 320px;
  height: 320px;
  border-radius: 50%;
  background: radial-gradient(circle, color-mix(in srgb, var(--accent-green) 18%, transparent), transparent 68%);
  pointer-events: none;
}

.hero-kicker {
  margin-bottom: var(--space-md);
}

.hero-title {
  font-size: clamp(2.6rem, 4vw, 4rem);
  line-height: 0.95;
  margin-bottom: var(--space-md);
  max-width: 11ch;
}

.hero-description {
  max-width: 64ch;
  color: var(--text-secondary);
  font-size: 1.02rem;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  margin-top: var(--space-xl);
  flex-wrap: wrap;
}

.hero-note {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.hero-aside {
  display: grid;
  gap: var(--space-md);
}

.stat-panel {
  display: grid;
  gap: var(--space-xs);
  padding: var(--space-lg);
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-card);
}

.stat-panel.accent-cyan {
  border-color: color-mix(in srgb, var(--accent-cyan) 25%, transparent);
}

.stat-panel.accent-red {
  border-color: color-mix(in srgb, var(--accent-red) 24%, transparent);
}

.stat-label {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.stat-value {
  font-family: var(--font-display);
  font-size: 2rem;
  line-height: 1;
}

.stat-help {
  color: var(--text-secondary);
  font-size: 0.95rem;
}

.track-switch {
  display: flex;
}

.track-tabs {
  width: min(360px, 100%);
}

.framework-strip {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(280px, 0.7fr);
  gap: var(--space-lg);
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-md);
  margin-bottom: var(--space-md);
}

.section-label {
  color: var(--text-muted);
}

.framework-card h2,
.strategy-card h2 {
  margin-bottom: var(--space-lg);
}

.phase-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--space-sm);
}

.phase-pill {
  padding: var(--space-md);
  border-radius: var(--radius-md);
  border: 1px solid color-mix(in srgb, var(--accent-cyan) 18%, transparent);
  background: color-mix(in srgb, var(--bg-card) 82%, transparent);
}

.phase-index {
  display: block;
  color: var(--accent-cyan);
  font-size: 0.72rem;
  margin-bottom: var(--space-sm);
}

.phase-pill strong {
  display: block;
  margin-bottom: 6px;
}

.phase-pill p {
  color: var(--text-secondary);
  font-size: 0.92rem;
}

.strategy-list {
  display: grid;
  gap: var(--space-md);
  padding-left: 1.15rem;
  color: var(--text-secondary);
}

.filters {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) repeat(2, minmax(180px, 220px)) auto;
  gap: var(--space-md);
  align-items: end;
}

.filter-group {
  display: grid;
  gap: 6px;
}

.filter-group label {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.filter-input {
  width: 100%;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-default);
  background: var(--bg-card);
  color: var(--text-primary);
  font-family: var(--font-body);
}

.filter-input:focus {
  outline: none;
  border-color: var(--accent-cyan);
  box-shadow: var(--glow-cyan);
}

.filter-summary {
  justify-self: end;
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.problem-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-lg);
}

.problem-card {
  display: grid;
  gap: var(--space-md);
  min-height: 270px;
}

.problem-card-top,
.problem-card-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-md);
}

.problem-number {
  color: var(--accent-cyan);
  font-size: var(--text-sm);
}

.problem-card-body h3 {
  font-size: var(--text-xl);
  margin-bottom: 10px;
  color: var(--text-primary);
}

.problem-card-body p {
  color: var(--text-secondary);
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
}

.tag-chip {
  padding: 5px 10px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--accent-purple) 10%, var(--bg-card));
  border: 1px solid color-mix(in srgb, var(--accent-purple) 18%, transparent);
  color: var(--text-secondary);
  font-size: 0.72rem;
}

.meta-label {
  display: block;
  color: var(--text-muted);
  font-size: 0.72rem;
  margin-bottom: 4px;
}

.problem-card-bottom strong {
  color: var(--text-primary);
  font-size: 0.96rem;
}

.hld-placeholder {
  display: grid;
  gap: var(--space-sm);
  min-height: 220px;
  place-content: center;
}

.hld-placeholder p:last-child {
  color: var(--text-secondary);
  max-width: 60ch;
}

@media (max-width: 1200px) {
  .design-hero,
  .framework-strip,
  .filters,
  .problem-grid {
    grid-template-columns: 1fr;
  }

  .phase-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .filter-summary {
    justify-self: start;
  }
}

@media (max-width: 760px) {
  .hero-copy {
    padding: var(--space-lg);
  }

  .hero-title {
    font-size: 2.5rem;
  }

  .phase-grid {
    grid-template-columns: 1fr;
  }
}
</style>
