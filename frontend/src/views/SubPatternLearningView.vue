<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { usePatterns } from '../composables/usePatterns'
import { useProgress } from '../composables/useProgress'
import CodeHighlight from '../components/CodeHighlight.vue'
import AIChatPanel from '../components/AIChatPanel.vue'

const route = useRoute()
const patternSlug = computed(() => route.params.patternSlug as string)
const subPatternSlug = computed(() => route.params.subPatternSlug as string)

const { getPattern, getProblemsForPattern, loading } = usePatterns()
const { isSolved, markSolved, unmarkSolved, patternCompletion } = useProgress()

const parentPattern = computed(() => getPattern(patternSlug.value))
const subPattern = computed(() => {
  if (!parentPattern.value) return null
  return parentPattern.value.sub_patterns?.find(sp => sp.sub_pattern_id === subPatternSlug.value) || null
})

const problems = computed(() => {
  if (!subPattern.value) return []
  const allPatternProblems = getProblemsForPattern(patternSlug.value)
  return allPatternProblems.filter(p => p.sub_pattern_id === subPatternSlug.value)
})

const activeTab = ref<'overview' | 'template' | 'problems'>('overview')
const hoveredProblemSlug = ref<string | null>(null)

const completion = computed(() => {
  if (!subPattern.value || !subPattern.value.problem_slugs) return 0
  return patternCompletion(subPattern.value.problem_slugs)
})

const ringCircumference = 2 * Math.PI * 18
const ringOffset = computed(() => ringCircumference - ((completion.value / 100) * ringCircumference))

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

const patternChatChips = computed(() => {
  return [
    'Explain this strictly in terms of Java',
    'When should I NOT use this sub-pattern?',
    'Show me a visual trace of this sub-pattern',
    'Generate a conceptual quiz about this sub-pattern'
  ]
})
</script>

<template>
  <div class="container pattern-view" v-if="!loading && subPattern && parentPattern">
    <!-- ═══ Header ═══ -->
    <header class="pv-header animate-in">
      <router-link :to="`/pattern/${patternSlug}`" class="back-link">
        <span>←</span> Back to {{ parentPattern.name }}
      </router-link>

      <div class="pv-title-row">
        <h1 class="pv-title">{{ subPattern.name }}</h1>
        <div class="pv-meta">
          <span class="badge">{{ problems.length }} problems</span>
        </div>
      </div>

      <div class="pv-progress">
        <div class="pv-ring">
          <svg viewBox="0 0 44 44" aria-label="Completion progress">
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

    <!-- ═══ Tabs ═══ -->
    <div class="tab-bar animate-in stagger-1" style="margin-bottom: var(--space-xl)">
      <button class="tab-btn" :class="{ active: activeTab === 'overview' }" @click="activeTab = 'overview'">
        Core Concept
      </button>
      <button class="tab-btn" :class="{ active: activeTab === 'template' }" @click="activeTab = 'template'">
        Java Template
      </button>
      <button class="tab-btn" :class="{ active: activeTab === 'problems' }" @click="activeTab = 'problems'">
        Focused Practice
      </button>
    </div>

    <!-- ═══ Overview Tab ═══ -->
    <div v-if="activeTab === 'overview'" class="animate-in">
      <div class="pv-grid">
        <section class="card card-flat">
          <h3 class="section-heading">
            <span class="heading-icon">💡</span> Mental Model
          </h3>
          <p class="mental-model-text">{{ subPattern.mental_model || subPattern.description }}</p>
        </section>

        <section class="card card-flat">
          <h3 class="section-heading">
            <span class="heading-icon">🎯</span> Trigger Phrases
          </h3>
          <div class="trigger-list">
            <span v-for="phrase in subPattern.trigger_phrases" :key="phrase" class="trigger-chip">
              "{{ phrase }}"
            </span>
          </div>
        </section>
      </div>

      <section class="card card-flat" style="margin-top: var(--space-md)" v-if="subPattern.explanation">
        <h3 class="section-heading">
          <span class="heading-icon">📖</span> Deep Dive Explanation
        </h3>
        <div class="explanation-text" v-html="subPattern.explanation.replace(/\n/g, '<br/>')"></div>
      </section>
    </div>

    <!-- ═══ Template Tab ═══ -->
    <div v-if="activeTab === 'template'" class="animate-in">
      <div class="lang-switcher">
        <button class="btn btn-ghost active">Java</button>
      </div>
      <CodeHighlight :code="subPattern.template_code_java || '// No template generated yet'" language="java" />
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
      :key="`subp-ai-${subPatternSlug}`"
      context-type="sub-pattern"
      :context-id="subPatternSlug"
      :context-label="subPattern.name"
      :quick-chips="patternChatChips"
    />
  </div>

  <div class="container loading-state" v-else-if="loading">
    <div class="terminal-prompt">loading sub-pattern...</div>
  </div>

  <div class="container" v-else>
    <p class="terminal-prompt" style="padding: var(--space-2xl)">sub-pattern not found</p>
  </div>
</template>

<style scoped>
/* Reuse the exact same gorgeous styles from PatternView.vue */
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

.pv-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-md);
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

@media (max-width: 768px) {
  .pv-grid {
    grid-template-columns: 1fr;
  }
  .problem-ac {
    display: none;
  }
}
</style>
