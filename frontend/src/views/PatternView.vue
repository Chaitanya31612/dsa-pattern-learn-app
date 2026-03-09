<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { usePatterns } from '../composables/usePatterns'
import { useProgress } from '../composables/useProgress'
import CodeHighlight from '../components/CodeHighlight.vue'
import AIChatPanel from '../components/AIChatPanel.vue'

const route = useRoute()
const patternId = computed(() => route.params.id as string)

const { getPattern, getProblemsForPattern, loading } = usePatterns()
const { isSolved, markSolved, unmarkSolved, patternCompletion } = useProgress()

const pattern = computed(() => getPattern(patternId.value))
const problems = computed(() => getProblemsForPattern(patternId.value))

const activeTab = ref<'overview' | 'template' | 'problems'>('overview')
const codeLang = ref<'python' | 'javascript' | 'java'>('java')
const hoveredProblemSlug = ref<string | null>(null)

const completion = computed(() => {
  if (!pattern.value) return 0
  return patternCompletion(pattern.value.problem_slugs)
})

const ringCircumference = 2 * Math.PI * 18
const ringOffset = computed(() => ringCircumference - ((completion.value / 100) * ringCircumference))

const templateCode = computed(() => {
  if (!pattern.value) return ''
  const map: Record<string, string> = {
    java: pattern.value.template_code_java,
    python: pattern.value.template_code_python,
    javascript: pattern.value.template_code_javascript,
  }
  return map[codeLang.value] || ''
})

function toggleSolved(slug: string) {
  if (isSolved(slug)) {
    unmarkSolved(slug)
  } else {
    markSolved(slug, 2)
  }
}

function getDiffClass(diff: string | null): string {
  if (!diff) return ''
  return `badge-${diff.toLowerCase()}`
}

function normalizeComplexityText(value: string | null | undefined): string {
  if (!value) return ''
  return value.replace(/\s+/g, ' ').trim()
}

function splitComplexityVariants(value: string | null | undefined): string[] {
  const normalized = normalizeComplexityText(value)
  if (!normalized) return []

  let segments = normalized
    .split(/\s*;\s*/g)
    .flatMap(part => part.split(/\s*,\s*or\s+/gi))
    .map(part => part.trim())
    .filter(Boolean)

  if (segments.length === 1) {
    const oCount = (normalized.match(/O\(/g) ?? []).length
    if (oCount > 1 && /\s+or\s+/i.test(normalized)) {
      segments = normalized
        .split(/\s+or\s+/gi)
        .map(part => part.trim())
        .filter(Boolean)
    }
  }

  return Array.from(new Set(segments))
}

const timeComplexityVariants = computed(() => splitComplexityVariants(pattern.value?.time_complexity))
const spaceComplexityVariants = computed(() => splitComplexityVariants(pattern.value?.space_complexity))

const difficultyBreakdown = computed(() => {
  const counts = {
    Easy: 0,
    Medium: 0,
    Hard: 0,
  }

  for (const problem of problems.value) {
    if (problem.difficulty === 'Easy') counts.Easy += 1
    if (problem.difficulty === 'Medium') counts.Medium += 1
    if (problem.difficulty === 'Hard') counts.Hard += 1
  }

  const total = problems.value.length || 1
  return [
    { label: 'Easy', count: counts.Easy, pct: Math.round((counts.Easy / total) * 100), color: 'var(--diff-easy)' },
    { label: 'Medium', count: counts.Medium, pct: Math.round((counts.Medium / total) * 100), color: 'var(--diff-medium)' },
    { label: 'Hard', count: counts.Hard, pct: Math.round((counts.Hard / total) * 100), color: 'var(--diff-hard)' },
  ]
})

const topCompanies = computed(() => {
  return pattern.value?.top_companies?.filter(item => item.count > 0) ?? []
})

const subPatternSections = computed(() => {
  if (!pattern.value?.sub_patterns?.length) return []

  const bySlug = new Map(problems.value.map(problem => [problem.slug, problem]))

  return pattern.value.sub_patterns
    .filter(subPattern => {
      const count = subPattern.problem_count ?? subPattern.problem_slugs?.length ?? 0
      return count > 0
    })
    .map(subPattern => ({
      ...subPattern,
      problems: (subPattern.problem_slugs ?? [])
        .map(slug => bySlug.get(slug))
        .filter((problem): problem is (typeof problems.value)[number] => Boolean(problem)),
    }))
})

const patternChatChips = computed(() => {
  const relatedPattern = pattern.value?.related_patterns?.[0]
  return [
    'Explain this pattern simply',
    'When should I NOT use this?',
    'Show me a visual example',
    relatedPattern ? `Compare with ${relatedPattern}` : 'Compare with a related pattern',
  ]
})
</script>

<template>
  <div class="container pattern-view" v-if="!loading && pattern">
    <!-- ═══ Header ═══ -->
    <header class="pv-header animate-in">
      <router-link to="/" class="back-link">
        <span>←</span> Patterns
      </router-link>

      <div class="pv-title-row">
        <h1 class="pv-title">{{ pattern.name }}</h1>
        <div class="pv-meta">
          <span class="badge">{{ pattern.problem_count }} problems</span>
        </div>
      </div>

      <div class="pv-progress">
        <div class="pv-ring">
          <svg viewBox="0 0 44 44" aria-label="Pattern completion progress">
            <circle class="pv-ring-bg" cx="22" cy="22" r="18" />
            <circle
              class="pv-ring-fill"
              cx="22"
              cy="22"
              r="18"
              :stroke-dasharray="ringCircumference"
              :stroke-dashoffset="ringOffset"
            />
          </svg>
          <span class="pv-ring-label mono">{{ completion }}%</span>
        </div>

        <div class="pv-progress-bar-wrap">
          <div class="progress-bar" style="height: 6px">
            <div class="progress-fill" :style="{ width: completion + '%' }"></div>
          </div>
          <span class="mono pv-progress-label">{{ completion }}% complete</span>
        </div>
      </div>
    </header>

    <section
      class="card card-flat complexity-overview animate-in"
      v-if="timeComplexityVariants.length || spaceComplexityVariants.length"
    >
      <h3 class="section-heading">
        <span class="heading-icon">⏱</span> Complexity At a Glance
      </h3>
      <div class="complexity-grid">
        <article class="complexity-card" v-if="timeComplexityVariants.length">
          <span class="complexity-label">Time Complexity</span>
          <p class="complexity-help">Expected runtime characteristics for common approaches in this pattern.</p>
          <ul class="complexity-list">
            <li v-for="item in timeComplexityVariants" :key="`pattern-time-${item}`" class="complexity-value mono">{{ item }}</li>
          </ul>
        </article>

        <article class="complexity-card" v-if="spaceComplexityVariants.length">
          <span class="complexity-label">Space Complexity</span>
          <p class="complexity-help">Typical auxiliary memory usage while applying the pattern.</p>
          <ul class="complexity-list">
            <li v-for="item in spaceComplexityVariants" :key="`pattern-space-${item}`" class="complexity-value mono">{{ item }}</li>
          </ul>
        </article>
      </div>
    </section>

    <section class="card card-flat difficulty-overview animate-in" v-if="problems.length">
      <h3 class="section-heading">
        <span class="heading-icon">📊</span> Difficulty Distribution
      </h3>
      <div class="diff-mini-grid">
        <article v-for="item in difficultyBreakdown" :key="item.label" class="diff-mini-card">
          <div class="diff-mini-head">
            <span class="mono">{{ item.label }}</span>
            <span class="mono">{{ item.count }}</span>
          </div>
          <div class="diff-mini-bar">
            <span class="diff-mini-fill" :style="{ width: `${item.pct}%`, background: item.color }"></span>
          </div>
          <span class="diff-mini-pct mono">{{ item.pct }}%</span>
        </article>
      </div>
    </section>

    <section class="card card-flat company-overview animate-in" v-if="topCompanies.length">
      <h3 class="section-heading">
        <span class="heading-icon">🏢</span> Top Companies
      </h3>
      <div class="company-mini-grid">
        <article class="company-mini-card" v-for="item in topCompanies" :key="item.company">
          <strong class="company-mini-name">{{ item.company }}</strong>
          <span class="company-mini-count mono">{{ item.count }} problems</span>
        </article>
      </div>
    </section>

    <section class="card card-flat subpattern-overview animate-in" v-if="subPatternSections.length">
      <h3 class="section-heading">
        <span class="heading-icon">🧩</span> Sub-Patterns
      </h3>
      <div class="subpattern-grid">
        <details
          v-for="subPattern in subPatternSections"
          :key="subPattern.sub_pattern_id"
          class="subpattern-card"
        >
          <summary class="subpattern-summary">
            <div class="subpattern-summary-main">
              <strong class="subpattern-name">{{ subPattern.name }}</strong>
              <p class="subpattern-description">{{ subPattern.description }}</p>
            </div>
            <span class="badge">{{ subPattern.problem_count }} problems</span>
          </summary>

          <div class="subpattern-body">
            <div class="trigger-list" v-if="subPattern.trigger_phrases.length">
              <span v-for="phrase in subPattern.trigger_phrases" :key="`${subPattern.sub_pattern_id}-${phrase}`" class="trigger-chip">
                {{ phrase }}
              </span>
            </div>

            <div class="subpattern-problem-links" v-if="subPattern.problems.length">
              <router-link
                v-for="problem in subPattern.problems.slice(0, 6)"
                :key="problem.slug"
                :to="`/problem/${problem.slug}`"
                class="subpattern-problem-link"
              >
                {{ problem.title }}
              </router-link>
            </div>
          </div>
        </details>
      </div>
    </section>

    <!-- ═══ Tabs ═══ -->
    <div class="tab-bar animate-in stagger-1" style="margin-bottom: var(--space-xl)">
      <button class="tab-btn" :class="{ active: activeTab === 'overview' }" @click="activeTab = 'overview'">
        Overview
      </button>
      <button class="tab-btn" :class="{ active: activeTab === 'template' }" @click="activeTab = 'template'">
        Template
      </button>
      <button class="tab-btn" :class="{ active: activeTab === 'problems' }" @click="activeTab = 'problems'">
        Problems
      </button>
    </div>

    <!-- ═══ Overview Tab ═══ -->
    <div v-if="activeTab === 'overview'" class="animate-in">
      <div class="pv-grid">
        <section class="card card-flat">
          <h3 class="section-heading">
            <span class="heading-icon">💡</span> Mental Model
          </h3>
          <p class="mental-model-text">{{ pattern.mental_model }}</p>
        </section>

        <section class="card card-flat">
          <h3 class="section-heading">
            <span class="heading-icon">🎯</span> Trigger Phrases
          </h3>
          <div class="trigger-list">
            <span v-for="phrase in pattern.trigger_phrases" :key="phrase" class="trigger-chip">
              "{{ phrase }}"
            </span>
          </div>
        </section>
      </div>

      <section class="card card-flat" style="margin-top: var(--space-md)">
        <h3 class="section-heading">
          <span class="heading-icon">📖</span> Explanation
        </h3>
        <div class="explanation-text" v-html="pattern.explanation.replace(/\n/g, '<br/>')"></div>
      </section>

      <div class="pv-grid" style="margin-top: var(--space-md)">
        <section class="card card-flat">
          <h3 class="section-heading">
            <span class="heading-icon">✅</span> When to Use
          </h3>
          <ul class="use-list">
            <li v-for="item in pattern.when_to_use" :key="item">{{ item }}</li>
          </ul>
        </section>

        <section class="card card-flat">
          <h3 class="section-heading">
            <span class="heading-icon">⚠️</span> Common Mistakes
          </h3>
          <ul class="mistake-list">
            <li v-for="item in pattern.common_mistakes" :key="item">{{ item }}</li>
          </ul>
        </section>
      </div>

      <section class="card card-flat" style="margin-top: var(--space-md)" v-if="pattern.sample_walkthrough?.approach">
        <h3 class="section-heading">
          <span class="heading-icon">🚶</span> Walkthrough: {{ pattern.sample_walkthrough.problem }}
        </h3>
        <div class="walkthrough-text" v-html="pattern.sample_walkthrough.approach.replace(/\n/g, '<br/>')"></div>
      </section>

      <section class="card card-flat" style="margin-top: var(--space-md)" v-if="pattern.related_patterns.length">
        <h3 class="section-heading">
          <span class="heading-icon">🔗</span> Related Patterns
        </h3>
        <div class="related-list">
          <router-link
            v-for="rp in pattern.related_patterns"
            :key="rp"
            :to="`/pattern/${rp}`"
            class="badge badge-source"
          >
            {{ rp }}
          </router-link>
        </div>
      </section>
    </div>

    <!-- ═══ Template Tab ═══ -->
    <div v-if="activeTab === 'template'" class="animate-in">
      <div class="lang-switcher">
        <button
          v-for="lang in (['java', 'python', 'javascript'] as const)"
          :key="lang"
          class="btn btn-ghost"
          :class="{ active: codeLang === lang }"
          @click="codeLang = lang"
        >
          {{ lang }}
        </button>
      </div>

      <CodeHighlight :code="templateCode" :language="codeLang" />
    </div>

    <!-- ═══ Problems Tab ═══ -->
    <div v-if="activeTab === 'problems'" class="animate-in">
      <div class="problem-list">
        <div
          v-for="problem in problems"
          :key="problem.slug"
          class="problem-item"
          @mouseenter="hoveredProblemSlug = problem.slug"
          @mouseleave="hoveredProblemSlug = null"
        >
          <div class="problem-row" :class="{ solved: isSolved(problem.slug) }">
            <button
              class="solve-check"
              :class="{ checked: isSolved(problem.slug) }"
              @click.prevent="toggleSolved(problem.slug)"
              :title="isSolved(problem.slug) ? 'Unmark' : 'Mark solved'"
            >
              {{ isSolved(problem.slug) ? '✓' : '' }}
            </button>

            <router-link :to="`/problem/${problem.slug}`" class="problem-info">
              <span class="problem-num mono">#{{ problem.number }}</span>
              <span class="problem-title">{{ problem.title }}</span>
            </router-link>

            <span class="badge" :class="getDiffClass(problem.difficulty)">
              {{ problem.difficulty || '?' }}
            </span>

            <span class="problem-ac mono" v-if="problem.acceptance_rate">
              {{ problem.acceptance_rate }}%
            </span>

            <a
              :href="problem.leetcode_url"
              target="_blank"
              rel="noopener"
              class="lc-link"
              title="Open on LeetCode"
            >↗</a>
          </div>

          <Transition name="preview-fade">
            <div v-if="hoveredProblemSlug === problem.slug" class="problem-preview">
              <p class="problem-preview-line" v-if="problem.pattern_hint">
                <span class="problem-preview-label">Signal:</span> {{ problem.pattern_hint }}
              </p>
              <p class="problem-preview-line" v-if="problem.key_insight">
                <span class="problem-preview-label">Insight:</span> {{ problem.key_insight }}
              </p>
            </div>
          </Transition>
        </div>
      </div>
    </div>

    <AIChatPanel
      :key="`pattern-ai-${patternId}`"
      context-type="pattern"
      :context-id="patternId"
      :context-label="pattern.name"
      :quick-chips="patternChatChips"
    />
  </div>

  <div class="container loading-state" v-else-if="loading">
    <div class="terminal-prompt">loading pattern...</div>
  </div>

  <div class="container" v-else>
    <p class="terminal-prompt" style="padding: var(--space-2xl)">pattern not found</p>
  </div>
</template>

<style scoped>
.pv-header {
  margin-bottom: var(--space-xl);
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--text-muted);
  margin-bottom: var(--space-md);
  transition: color var(--transition-fast);
}

.back-link:hover {
  color: var(--accent-cyan);
}

.pv-title-row {
  display: flex;
  align-items: center;
  gap: var(--space-lg);
  flex-wrap: wrap;
  margin-bottom: var(--space-md);
}

.pv-title {
  font-size: var(--text-2xl);
  font-weight: 800;
}

.pv-meta {
  display: flex;
  gap: var(--space-xs);
}

.complexity-overview {
  margin-bottom: var(--space-xl);
}

.pv-progress {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.pv-ring {
  position: relative;
  width: 58px;
  height: 58px;
  flex-shrink: 0;
}

.pv-ring svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.pv-ring-bg {
  fill: none;
  stroke: var(--bg-input);
  stroke-width: 4;
}

.pv-ring-fill {
  fill: none;
  stroke: var(--accent-cyan);
  stroke-width: 4;
  stroke-linecap: round;
  transition: stroke-dashoffset var(--transition-slow);
}

.pv-ring-label {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent-cyan);
  font-size: 11px;
  font-weight: 700;
}

.pv-progress-bar-wrap {
  flex: 1;
  max-width: 300px;
}

.pv-progress-label {
  display: block;
  margin-top: 6px;
  color: var(--text-muted);
  font-size: var(--text-xs);
}

/* ── Grid ──────────────────────────── */
.pv-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-md);
}

.complexity-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-md);
}

.complexity-card {
  padding: var(--space-md);
  border: 1px solid var(--border-subtle);
  background: var(--bg-elevated);
  border-radius: var(--radius-sm);
}

.difficulty-overview {
  margin-bottom: var(--space-xl);
}

.company-overview {
  margin-bottom: var(--space-xl);
}

.company-mini-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--space-sm);
}

.company-mini-card {
  border: 1px solid var(--border-subtle);
  background: var(--bg-elevated);
  border-radius: var(--radius-sm);
  padding: var(--space-sm);
  display: grid;
  gap: 4px;
}

.company-mini-name {
  color: var(--text-primary);
  font-size: var(--text-sm);
}

.company-mini-count {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.subpattern-overview {
  margin-bottom: var(--space-xl);
}

.subpattern-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-sm);
}

.subpattern-card {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  overflow: hidden;
}

.subpattern-summary {
  list-style: none;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  cursor: pointer;
}

.subpattern-summary::-webkit-details-marker {
  display: none;
}

.subpattern-summary-main {
  min-width: 0;
}

.subpattern-name {
  display: block;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.subpattern-description {
  color: var(--text-muted);
  font-size: var(--text-xs);
  line-height: 1.5;
}

.subpattern-body {
  border-top: 1px solid var(--border-subtle);
  padding: var(--space-sm) var(--space-md) var(--space-md);
  display: grid;
  gap: var(--space-sm);
}

.subpattern-problem-links {
  display: grid;
  gap: 6px;
}

.subpattern-problem-link {
  color: var(--text-secondary);
  font-size: var(--text-sm);
  line-height: 1.4;
}

.subpattern-problem-link:hover {
  color: var(--accent-cyan);
}

.diff-mini-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-sm);
}

.diff-mini-card {
  border: 1px solid var(--border-subtle);
  background: var(--bg-elevated);
  border-radius: var(--radius-sm);
  padding: var(--space-sm);
}

.diff-mini-head {
  display: flex;
  justify-content: space-between;
  color: var(--text-secondary);
  font-size: var(--text-xs);
  margin-bottom: 6px;
}

.diff-mini-bar {
  height: 8px;
  border-radius: 999px;
  background: var(--bg-input);
  overflow: hidden;
}

.diff-mini-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  transition: width var(--transition-slow);
}

.diff-mini-pct {
  display: block;
  margin-top: 6px;
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.complexity-label {
  display: block;
  color: var(--text-muted);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
}

.complexity-help {
  color: var(--text-muted);
  font-size: var(--text-xs);
  margin-bottom: var(--space-sm);
}

.complexity-list {
  list-style: none;
  display: grid;
  gap: 8px;
}

.complexity-value {
  color: var(--accent-cyan);
  font-size: var(--text-sm);
  line-height: 1.6;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.section-heading {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: var(--text-base);
  font-weight: 700;
  margin-bottom: var(--space-md);
  color: var(--text-primary);
}

.heading-icon {
  font-size: var(--text-lg);
}

.mental-model-text {
  font-size: var(--text-lg);
  color: var(--accent-cyan);
  font-style: italic;
  line-height: 1.6;
  font-family: var(--font-display);
}

.trigger-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
}

.trigger-chip {
  display: inline-block;
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  background: rgba(56, 189, 248, 0.08);
  border: 1px solid rgba(56, 189, 248, 0.15);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--accent-cyan);
}

.explanation-text {
  color: var(--text-secondary);
  line-height: 1.8;
  font-size: var(--text-base);
}

.use-list, .mistake-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.use-list li::before {
  content: '→ ';
  color: var(--accent-green);
  font-family: var(--font-mono);
}

.mistake-list li::before {
  content: '✗ ';
  color: var(--accent-red);
  font-family: var(--font-mono);
}

.use-list li, .mistake-list li {
  color: var(--text-secondary);
  font-size: var(--text-sm);
  line-height: 1.6;
}

.walkthrough-text {
  color: var(--text-secondary);
  line-height: 1.8;
  font-size: var(--text-sm);
}

.related-list {
  display: flex;
  gap: var(--space-sm);
  flex-wrap: wrap;
}

/* ── Template Tab ──────────────────── */
.lang-switcher {
  display: flex;
  gap: 4px;
  margin-bottom: var(--space-md);
}

.lang-switcher .btn {
  text-transform: capitalize;
}

.lang-switcher .btn.active {
  color: var(--accent-cyan);
  border-color: var(--accent-cyan);
  background: rgba(56, 189, 248, 0.08);
}

.code-block pre {
  white-space: pre-wrap;
  word-break: break-word;
}

/* ── Problem List ──────────────────── */
.problem-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.problem-item {
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.problem-row {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-sm);
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  transition: all var(--transition-fast);
}

.problem-row:hover {
  background: var(--bg-card-hover);
  border-color: var(--border-default);
}

.problem-row.solved {
  opacity: 0.6;
}

.problem-row.solved .problem-title {
  text-decoration: line-through;
  text-decoration-color: var(--text-muted);
}

.solve-check {
  width: 22px;
  height: 22px;
  border-radius: 4px;
  border: 2px solid var(--border-default);
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--accent-green);
  transition: all var(--transition-fast);
  flex-shrink: 0;
}

.solve-check:hover {
  border-color: var(--accent-cyan);
}

.solve-check.checked {
  border-color: var(--accent-green);
  background: rgba(34, 211, 167, 0.15);
}

.problem-info {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex: 1;
  min-width: 0;
  text-decoration: none;
}

.problem-num {
  color: var(--text-muted);
  font-size: var(--text-xs);
  flex-shrink: 0;
  width: 48px;
}

.problem-title {
  color: var(--text-primary);
  font-size: var(--text-sm);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.problem-ac {
  color: var(--text-muted);
  font-size: var(--text-xs);
  flex-shrink: 0;
}

.lc-link {
  color: var(--text-muted);
  font-size: var(--text-sm);
  flex-shrink: 0;
  transition: color var(--transition-fast);
}

.lc-link:hover {
  color: var(--accent-cyan);
}

.problem-preview {
  border: 1px solid var(--border-subtle);
  border-top: none;
  background: linear-gradient(180deg, rgba(56, 189, 248, 0.06), rgba(56, 189, 248, 0.02));
  padding: var(--space-sm) var(--space-md);
}

.problem-preview-line {
  color: var(--text-secondary);
  font-size: var(--text-xs);
  line-height: 1.6;
}

.problem-preview-line + .problem-preview-line {
  margin-top: 4px;
}

.problem-preview-label {
  color: var(--accent-cyan);
  font-family: var(--font-mono);
}

.preview-fade-enter-active,
.preview-fade-leave-active {
  transition: all var(--transition-fast);
}

.preview-fade-enter-from,
.preview-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
}

@media (max-width: 768px) {
  .pv-grid {
    grid-template-columns: 1fr;
  }

  .complexity-grid {
    grid-template-columns: 1fr;
  }

  .diff-mini-grid {
    grid-template-columns: 1fr;
  }

  .company-mini-grid {
    grid-template-columns: 1fr;
  }

  .subpattern-grid {
    grid-template-columns: 1fr;
  }

  .problem-ac {
    display: none;
  }
}
</style>
