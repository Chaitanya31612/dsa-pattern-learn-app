<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { usePatterns } from '../composables/usePatterns'
import { useProgress } from '../composables/useProgress'
import CodeHighlight from '../components/CodeHighlight.vue'

const route = useRoute()
const patternId = computed(() => route.params.id as string)

const { getPattern, getProblemsForPattern, loading } = usePatterns()
const { isSolved, markSolved, unmarkSolved, patternCompletion } = useProgress()

const pattern = computed(() => getPattern(patternId.value))
const problems = computed(() => getProblemsForPattern(patternId.value))

const activeTab = ref<'overview' | 'template' | 'problems'>('overview')
const codeLang = ref<'python' | 'javascript' | 'java'>('python')

const completion = computed(() => {
  if (!pattern.value) return 0
  return patternCompletion(pattern.value.problem_slugs)
})

const templateCode = computed(() => {
  if (!pattern.value) return ''
  const map: Record<string, string> = {
    python: pattern.value.template_code_python,
    javascript: pattern.value.template_code_javascript,
    java: pattern.value.template_code_java,
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
          <span class="badge">{{ pattern.time_complexity }}</span>
          <span class="badge">{{ pattern.space_complexity }}</span>
        </div>
      </div>

      <div class="pv-progress">
        <div class="progress-bar" style="height: 6px">
          <div class="progress-fill" :style="{ width: completion + '%' }"></div>
        </div>
        <span class="mono" style="font-size: var(--text-xs); color: var(--text-muted)">
          {{ completion }}% complete
        </span>
      </div>
    </header>

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
          v-for="lang in (['python', 'javascript', 'java'] as const)"
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
          class="problem-row"
          :class="{ solved: isSolved(problem.slug) }"
        >
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
      </div>
    </div>
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

.pv-progress {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.pv-progress .progress-bar {
  flex: 1;
  max-width: 300px;
}

/* ── Grid ──────────────────────────── */
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
  gap: 2px;
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

  .problem-ac {
    display: none;
  }
}
</style>
