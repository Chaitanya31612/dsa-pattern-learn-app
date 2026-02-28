<script setup lang="ts">
import { computed, ref } from 'vue'
import { usePatterns } from '../composables/usePatterns'
import { useProgress } from '../composables/useProgress'
import type { Problem } from '../types'

const { getAllProblems, patterns, loading } = usePatterns()
const { isSolved, markSolved, unmarkSolved } = useProgress()

const search = ref('')
const filterDiff = ref<string>('all')
const filterPattern = ref<string>('all')
const filterStatus = ref<string>('all')
const sortBy = ref<'score' | 'number' | 'difficulty' | 'acceptance'>('score')

const filteredProblems = computed(() => {
  let list = getAllProblems()

  // Search
  if (search.value) {
    const q = search.value.toLowerCase()
    list = list.filter(p =>
      p.title.toLowerCase().includes(q) ||
      p.slug.includes(q) ||
      String(p.number).includes(q)
    )
  }

  // Difficulty filter
  if (filterDiff.value !== 'all') {
    list = list.filter(p => p.difficulty === filterDiff.value)
  }

  // Pattern filter
  if (filterPattern.value !== 'all') {
    list = list.filter(p => p.pattern_id === filterPattern.value)
  }

  // Status filter
  if (filterStatus.value === 'solved') {
    list = list.filter(p => isSolved(p.slug))
  } else if (filterStatus.value === 'unsolved') {
    list = list.filter(p => !isSolved(p.slug))
  }

  // Sort
  list.sort((a, b) => {
    if (sortBy.value === 'number') return (a.number ?? 0) - (b.number ?? 0)
    if (sortBy.value === 'difficulty') {
      const ord: Record<string, number> = { Easy: 0, Medium: 1, Hard: 2 }
      return (ord[a.difficulty ?? ''] ?? 3) - (ord[b.difficulty ?? ''] ?? 3)
    }
    if (sortBy.value === 'acceptance') return (b.acceptance_rate ?? 0) - (a.acceptance_rate ?? 0)
    return b.score - a.score
  })

  return list
})

function toggleSolved(slug: string) {
  isSolved(slug) ? unmarkSolved(slug) : markSolved(slug, 2)
}

function getDiffClass(diff: string | null): string {
  if (!diff) return ''
  return `badge-${diff.toLowerCase()}`
}
</script>

<template>
  <div class="container all-problems" v-if="!loading">
    <header class="ap-header animate-in">
      <h1 class="ap-title">All Problems</h1>
      <span class="ap-count mono">{{ filteredProblems.length }} results</span>
    </header>

    <!-- ═══ Filters ═══ -->
    <div class="filters animate-in stagger-1">
      <div class="search-wrap">
        <span class="search-icon">⌕</span>
        <input
          v-model="search"
          class="search-input"
          type="text"
          placeholder="Search by name, number, or slug..."
        />
      </div>

      <div class="filter-row">
        <select v-model="filterDiff" class="filter-select">
          <option value="all">All Difficulties</option>
          <option value="Easy">Easy</option>
          <option value="Medium">Medium</option>
          <option value="Hard">Hard</option>
        </select>

        <select v-model="filterPattern" class="filter-select">
          <option value="all">All Patterns</option>
          <option v-for="p in patterns" :key="p.pattern_id" :value="p.pattern_id">
            {{ p.name }}
          </option>
        </select>

        <select v-model="filterStatus" class="filter-select">
          <option value="all">All Status</option>
          <option value="solved">Solved</option>
          <option value="unsolved">Unsolved</option>
        </select>

        <div class="tab-bar" style="flex-shrink: 0">
          <button class="tab-btn" :class="{ active: sortBy === 'score' }" @click="sortBy = 'score'">Score</button>
          <button class="tab-btn" :class="{ active: sortBy === 'number' }" @click="sortBy = 'number'">#</button>
          <button class="tab-btn" :class="{ active: sortBy === 'difficulty' }" @click="sortBy = 'difficulty'">Diff</button>
          <button class="tab-btn" :class="{ active: sortBy === 'acceptance' }" @click="sortBy = 'acceptance'">AC%</button>
        </div>
      </div>
    </div>

    <!-- ═══ Problem Table ═══ -->
    <div class="problem-table animate-in stagger-2">
      <div class="table-header">
        <span class="col-check"></span>
        <span class="col-num">#</span>
        <span class="col-title">Title</span>
        <span class="col-pattern">Pattern</span>
        <span class="col-diff">Diff</span>
        <span class="col-ac">AC%</span>
        <span class="col-link"></span>
      </div>

      <div
        v-for="problem in filteredProblems"
        :key="problem.slug"
        class="table-row"
        :class="{ solved: isSolved(problem.slug) }"
      >
        <button
          class="solve-check col-check"
          :class="{ checked: isSolved(problem.slug) }"
          @click="toggleSolved(problem.slug)"
        >
          {{ isSolved(problem.slug) ? '✓' : '' }}
        </button>

        <span class="col-num mono">{{ problem.number }}</span>

        <router-link :to="`/problem/${problem.slug}`" class="col-title problem-link">
          {{ problem.title }}
        </router-link>

        <router-link
          :to="`/pattern/${problem.pattern_id}`"
          class="col-pattern pattern-tag"
        >
          {{ problem.pattern_name }}
        </router-link>

        <span class="col-diff">
          <span class="badge" :class="getDiffClass(problem.difficulty)" style="font-size: 0.65rem">
            {{ problem.difficulty || '?' }}
          </span>
        </span>

        <span class="col-ac mono">{{ problem.acceptance_rate ? problem.acceptance_rate + '%' : '—' }}</span>

        <a :href="problem.leetcode_url" target="_blank" rel="noopener" class="col-link lc-link">↗</a>
      </div>

      <div v-if="filteredProblems.length === 0" class="empty-state">
        <span class="terminal-prompt">no problems match your filters</span>
      </div>
    </div>
  </div>

  <div class="container loading-state" v-else>
    <div class="terminal-prompt">loading problems...</div>
  </div>
</template>

<style scoped>
.ap-header {
  display: flex;
  align-items: baseline;
  gap: var(--space-md);
  margin-bottom: var(--space-xl);
}

.ap-title {
  font-size: var(--text-2xl);
  font-weight: 800;
}

.ap-count {
  color: var(--text-muted);
  font-size: var(--text-sm);
}

/* ── Filters ──────────────────────────── */
.filters {
  margin-bottom: var(--space-xl);
}

.search-wrap {
  position: relative;
  margin-bottom: var(--space-md);
}

.search-icon {
  position: absolute;
  left: var(--space-md);
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  font-size: var(--text-lg);
}

.search-input {
  width: 100%;
  padding: var(--space-sm) var(--space-md) var(--space-sm) 40px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  transition: border-color var(--transition-fast);
}

.search-input:focus {
  outline: none;
  border-color: var(--accent-cyan);
  box-shadow: var(--glow-cyan);
}

.search-input::placeholder {
  color: var(--text-muted);
}

.filter-row {
  display: flex;
  gap: var(--space-sm);
  flex-wrap: wrap;
  align-items: center;
}

.filter-select {
  padding: 6px 12px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  cursor: pointer;
  transition: border-color var(--transition-fast);
}

.filter-select:focus {
  outline: none;
  border-color: var(--accent-cyan);
}

/* ── Table ─────────────────────────────── */
.table-header {
  display: grid;
  grid-template-columns: 30px 50px 1fr 150px 70px 60px 30px;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--border-default);
  margin-bottom: 2px;
}

.table-row {
  display: grid;
  grid-template-columns: 30px 50px 1fr 150px 70px 60px 30px;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  align-items: center;
  border-radius: var(--radius-sm);
  transition: background var(--transition-fast);
}

.table-row:hover {
  background: var(--bg-card-hover);
}

.table-row.solved {
  opacity: 0.5;
}

.solve-check {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  border: 2px solid var(--border-default);
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: var(--accent-green);
  transition: all var(--transition-fast);
}

.solve-check:hover {
  border-color: var(--accent-cyan);
}

.solve-check.checked {
  border-color: var(--accent-green);
  background: rgba(34, 211, 167, 0.15);
}

.col-num {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.problem-link {
  color: var(--text-primary);
  font-size: var(--text-sm);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-decoration: none;
}

.problem-link:hover {
  color: var(--accent-cyan);
}

.pattern-tag {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-secondary);
  text-decoration: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pattern-tag:hover {
  color: var(--accent-cyan);
}

.col-ac {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.lc-link {
  color: var(--text-muted);
  font-size: var(--text-sm);
  text-decoration: none;
  transition: color var(--transition-fast);
}

.lc-link:hover {
  color: var(--accent-cyan);
}

.empty-state {
  padding: var(--space-2xl);
  text-align: center;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
}

@media (max-width: 768px) {
  .table-header {
    display: none;
  }

  .table-row {
    grid-template-columns: 30px 40px 1fr auto 30px;
  }

  .col-pattern, .col-ac {
    display: none;
  }
}
</style>
