<script setup lang="ts">
import { computed, ref, watch, watchEffect } from 'vue'
import { useRoute } from 'vue-router'
import { usePatterns } from '../composables/usePatterns'
import { useProgress } from '../composables/useProgress'
import { useSmartRandom } from '../composables/useSmartRandom'
import ReflectionModal from '../components/ReflectionModal.vue'
import AIChatPanel from '../components/AIChatPanel.vue'
import CodeHighlight from '../components/CodeHighlight.vue'

const route = useRoute()
const slug = computed(() => route.params.slug as string)

const { problems, loading, getProblemsForPattern } = usePatterns()
const { state, isSolved, markSolved, unmarkSolved, getConfidence, getNote, addNote, getReflection } = useProgress()
const { navigateSmartRandom } = useSmartRandom()

const problem = computed(() => problems.value[slug.value])

const solved = computed(() => isSolved(slug.value))
const confidence = computed(() => getConfidence(slug.value))

const noteText = ref('')
const showNotes = ref(false)
const showReflection = ref(false)
const showSolutionBreakdown = ref(false)
const revealedStepCount = ref(0)
const interviewRoute = computed(() => ({
  path: '/mock-interview',
  query: {
    slug: slug.value,
    autostart: '1',
    single: '1',
  },
}))

// Load existing note and keep it synced
watchEffect(() => {
  if (slug.value) {
    noteText.value = state.notes[slug.value] ?? ''
  }
})

function toggleSolved() {
  if (solved.value) {
    unmarkSolved(slug.value)
  } else {
    // Open reflection modal instead of directly marking
    showReflection.value = true
  }
}

function setConfidence(level: 1 | 2 | 3) {
  markSolved(slug.value, level)
}

function saveNote() {
  addNote(slug.value, noteText.value)
}

function getDiffClass(diff: string | null): string {
  if (!diff) return ''
  return `badge-${diff.toLowerCase()}`
}

function frequencyLabel(tier: string | null | undefined): string {
  const value = String(tier ?? 'low').toLowerCase()
  if (value === 'very_high') return 'Very High Frequency'
  if (value === 'high') return 'High Frequency'
  if (value === 'medium') return 'Medium Frequency'
  return 'Low Frequency'
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

const timeComplexityVariants = computed(() => splitComplexityVariants(problem.value?.time_complexity))
const spaceComplexityVariants = computed(() => splitComplexityVariants(problem.value?.space_complexity))
const relatedProblems = computed(() => {
  if (!problem.value) return []
  return getProblemsForPattern(problem.value.pattern_id)
    .filter((item) => item.slug !== slug.value)
    .slice(0, 5)
})

const followUpProblems = computed(() => {
  if (!problem.value?.follow_ups?.length) return []
  const items = []
  for (const followSlug of problem.value.follow_ups) {
    const item = problems.value[followSlug]
    if (item && item.slug !== slug.value) {
      items.push(item)
    }
  }
  return items
})

const problemChatChips = computed(() => {
  const patternName = problem.value?.pattern_name
  return [
    'Walk me through the approach',
    'Show me the optimal solution',
    'What are the edge cases?',
    patternName
      ? `How does this connect to ${patternName}?`
      : 'How does this connect to the pattern?',
  ]
})

const solutionBreakdown = computed(() => problem.value?.solution_breakdown)
const revealedSteps = computed(() => {
  const steps = solutionBreakdown.value?.steps ?? []
  return steps.slice(0, revealedStepCount.value)
})
const allBreakdownStepsRevealed = computed(() => {
  const total = solutionBreakdown.value?.steps?.length ?? 0
  return total > 0 && revealedStepCount.value >= total
})

watch(slug, () => {
  showSolutionBreakdown.value = false
  revealedStepCount.value = 0
})

function revealSolutionBreakdown() {
  if (!solutionBreakdown.value) return
  showSolutionBreakdown.value = true
  if (revealedStepCount.value === 0) {
    revealedStepCount.value = 1
  }
}

function revealNextStep() {
  const total = solutionBreakdown.value?.steps?.length ?? 0
  if (revealedStepCount.value < total) {
    revealedStepCount.value += 1
  }
}
</script>

<template>
  <div class="container problem-view" v-if="!loading && problem">
    <!-- ═══ Header ═══ -->
    <header class="prob-header animate-in">
      <nav class="breadcrumbs mono">
        <router-link to="/">Dashboard</router-link>
        <span>/</span>
        <router-link :to="`/pattern/${problem.pattern_id}`">{{ problem.pattern_name }}</router-link>
        <span>/</span>
        <span class="crumb-current">{{ problem.title }}</span>
      </nav>

      <router-link :to="`/pattern/${problem.pattern_id}`" class="back-link">
        <span>←</span> {{ problem.pattern_name }}
      </router-link>

      <div class="prob-title-row">
        <div class="prob-number-wrap">
          <span class="prob-number mono">#{{ problem.number }}</span>
        </div>
        <div>
          <h1 class="prob-title">{{ problem.title }}</h1>
          <div class="prob-badges">
            <span class="badge" :class="getDiffClass(problem.difficulty)">
              {{ problem.difficulty || 'Unknown' }}
            </span>
            <span class="badge" v-if="problem.acceptance_rate">
              {{ problem.acceptance_rate }}% AC
            </span>
            <span class="badge badge-source" v-if="problem.in_both">NeetCode + Striver</span>
            <span class="badge badge-source" v-else-if="problem.in_neetcode">NeetCode</span>
            <span class="badge badge-source" v-else-if="problem.in_striver">Striver</span>
            <span class="badge badge-source" v-if="problem.frequency_tier">
              {{ frequencyLabel(problem.frequency_tier) }}
            </span>
            <span class="badge badge-source" v-for="company in (problem.companies ?? []).slice(0, 5)" :key="`company-${company}`">
              🏢 {{ company }}
            </span>
          </div>
        </div>
      </div>

      <div class="prob-actions">
        <button class="btn" :class="{ 'btn-primary': solved }" @click="toggleSolved">
          {{ solved ? '✓ Solved' : '◉ Mark Solved' }}
        </button>
        <a :href="problem.leetcode_url" target="_blank" rel="noopener" class="btn">
          Open on LeetCode ↗
        </a>
        <router-link :to="interviewRoute" class="btn" target="_blank" rel="noopener">
          Solve in Interview Mode
        </router-link>
        <button class="btn btn-ghost" @click="showNotes = !showNotes">
          {{ showNotes ? 'Hide Notes' : '✎ Notes' }}
        </button>
        <button class="btn btn-ghost" @click="navigateSmartRandom(slug)" title="Smart pick based on your progress, confidence, and momentum">
          ⚡ Next Problem
        </button>
      </div>

      <!-- Reflection Modal -->
      <ReflectionModal
        v-if="showReflection && problem"
        :slug="slug"
        :pattern-name="problem.pattern_name"
        :problem-title="problem.title"
        @close="showReflection = false"
      />

      <!-- Confidence selector -->
      <div class="confidence-row" v-if="solved">
        <span class="conf-label terminal-prompt">confidence_level =</span>
        <button
          v-for="level in [1, 2, 3] as const"
          :key="level"
          class="conf-btn"
          :class="{ active: confidence === level }"
          @click="setConfidence(level)"
        >
          {{ level === 1 ? '😟 Shaky' : level === 2 ? '😐 Okay' : '😎 Solid' }}
        </button>
      </div>
    </header>

    <!-- ═══ Previous Reflection ═══ -->
    <section v-if="getReflection(slug)" class="reflection-section animate-in" style="margin-bottom: var(--space-md)">
      <div class="card card-flat">
        <h3 class="section-heading">🪞 Your Reflection</h3>
        <div class="reflection-grid">
          <div class="reflection-item">
            <span class="refl-label">🎯 Pattern identified</span>
            <span class="refl-val">{{ getReflection(slug)!.pattern }}</span>
          </div>
          <div class="reflection-item">
            <span class="refl-label">🔍 What signaled it</span>
            <span class="refl-val">{{ getReflection(slug)!.signal }}</span>
          </div>
          <div class="reflection-item">
            <span class="refl-label">🔧 Template deviation</span>
            <span class="refl-val">{{ getReflection(slug)!.deviation }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ Notes ═══ -->
    <section v-if="showNotes" class="notes-section animate-in" style="margin-bottom: var(--space-xl)">
      <div class="card card-flat">
        <h3 class="section-heading">📝 Your Notes</h3>
        <textarea
          v-model="noteText"
          @blur="saveNote"
          class="note-textarea"
          placeholder="Write your approach, key observations, or things to remember..."
          rows="4"
        ></textarea>
      </div>
    </section>

    <section
      class="solution-breakdown-section animate-in"
      style="margin-bottom: var(--space-xl)"
      v-if="solutionBreakdown"
    >
      <div class="card card-flat">
        <div class="solution-breakdown-head">
          <div>
            <h3 class="section-heading" style="margin-bottom: var(--space-xs)">📖 Solution Breakdown</h3>
            <p class="solution-breakdown-sub">
              Progressive reveal: intuition → approach steps → pseudo-code → edge cases.
            </p>
          </div>

          <button class="btn btn-primary" v-if="!showSolutionBreakdown" @click="revealSolutionBreakdown">
            Reveal Solution
          </button>
        </div>

        <div v-if="showSolutionBreakdown" class="solution-breakdown-body">
          <article class="solution-callout">
            <span class="solution-callout-label">Intuition</span>
            <p class="solution-callout-text">{{ solutionBreakdown.intuition }}</p>
          </article>

          <article class="solution-callout">
            <span class="solution-callout-label">Pattern Connection</span>
            <p class="solution-callout-text">{{ solutionBreakdown.pattern_connection }}</p>
          </article>

          <ol class="solution-step-list" v-if="revealedSteps.length">
            <li
              class="solution-step-item"
              v-for="(step, index) in revealedSteps"
              :key="`breakdown-step-${index}-${step.title}`"
            >
              <span class="solution-step-index mono">Step {{ index + 1 }}</span>
              <h4 class="solution-step-title">{{ step.title }}</h4>
              <p class="solution-step-detail">{{ step.detail }}</p>
            </li>
          </ol>

          <button
            class="btn"
            v-if="!allBreakdownStepsRevealed"
            @click="revealNextStep"
          >
            Reveal Next Step
          </button>

          <div v-if="allBreakdownStepsRevealed" class="solution-extra">
            <div class="solution-code-wrap" v-if="solutionBreakdown.java_pseudocode">
              <span class="terminal-prompt">java_pseudo_code</span>
              <CodeHighlight :code="solutionBreakdown.java_pseudocode" language="java" />
            </div>

            <div class="solution-checklists">
              <article class="solution-list-card" v-if="solutionBreakdown.edge_cases?.length">
                <h4 class="section-heading" style="margin-bottom: var(--space-sm)">Edge Cases Checklist</h4>
                <ul class="solution-mini-list">
                  <li v-for="edge in solutionBreakdown.edge_cases" :key="`edge-${edge}`">{{ edge }}</li>
                </ul>
              </article>

              <article class="solution-list-card" v-if="solutionBreakdown.alternatives?.length">
                <h4 class="section-heading" style="margin-bottom: var(--space-sm)">Alternative Approaches</h4>
                <ul class="solution-mini-list">
                  <li v-for="alt in solutionBreakdown.alternatives" :key="`alt-${alt.approach}`">
                    <strong>{{ alt.approach }}:</strong> {{ alt.tradeoff }}
                  </li>
                </ul>
              </article>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ Insights Grid ═══ -->
    <div class="insights-grid animate-in stagger-1">
      <div class="card card-flat insight-card insight-signal" v-if="problem.pattern_hint">
        <div class="insight-label">
          <span class="insight-icon">🔍</span> Pattern Signal
        </div>
        <p class="insight-text">{{ problem.pattern_hint }}</p>
      </div>

      <div class="card card-flat insight-card insight-key" v-if="problem.key_insight">
        <div class="insight-label">
          <span class="insight-icon">💡</span> Key Insight
        </div>
        <p class="insight-text highlight">{{ problem.key_insight }}</p>
      </div>

      <div class="card card-flat insight-card insight-deviation" v-if="problem.template_deviation">
        <div class="insight-label">
          <span class="insight-icon">🔧</span> Template Deviation
        </div>
        <p class="insight-text">{{ problem.template_deviation }}</p>
      </div>

      <div class="card card-flat insight-card insight-warning" v-if="problem.common_mistake">
        <div class="insight-label">
          <span class="insight-icon">⚠️</span> Common Mistake
        </div>
        <p class="insight-text warning">{{ problem.common_mistake }}</p>
      </div>
    </div>

    <!-- ═══ Complexity & Tags ═══ -->
    <div class="meta-row animate-in stagger-2">
      <div class="card card-flat meta-card" v-if="problem.time_complexity || problem.space_complexity">
        <h3 class="section-heading">⏱ Complexity</h3>
        <div class="complexity-grid">
          <section class="complexity-block" v-if="timeComplexityVariants.length">
            <span class="comp-label">Time Complexity</span>
            <p class="comp-desc">How runtime grows with input size.</p>
            <ul class="comp-list">
              <li v-for="item in timeComplexityVariants" :key="`time-${item}`" class="comp-value mono">{{ item }}</li>
            </ul>
          </section>

          <section class="complexity-block" v-if="spaceComplexityVariants.length">
            <span class="comp-label">Space Complexity</span>
            <p class="comp-desc">How extra memory scales for the approach.</p>
            <ul class="comp-list">
              <li v-for="item in spaceComplexityVariants" :key="`space-${item}`" class="comp-value mono">{{ item }}</li>
            </ul>
          </section>
        </div>
      </div>

      <div class="meta-side">
        <div class="card card-flat meta-card" v-if="problem.companies?.length || problem.follow_ups?.length">
          <h3 class="section-heading">🏢 Interview Signals</h3>

          <div class="company-wrap" v-if="problem.companies?.length">
            <span v-for="company in problem.companies" :key="`company-chip-${company}`" class="tag">
              {{ company }}
            </span>
          </div>

          <div class="followups-wrap" v-if="followUpProblems.length">
            <span class="terminal-prompt followups-label">suggested_follow_ups</span>
            <div class="related-list">
              <router-link
                v-for="item in followUpProblems"
                :key="`follow-${item.slug}`"
                :to="`/problem/${item.slug}`"
                class="related-item"
              >
                <span class="related-title">{{ item.title }}</span>
                <span class="badge" :class="getDiffClass(item.difficulty)">
                  {{ item.difficulty || 'Unknown' }}
                </span>
              </router-link>
            </div>
          </div>
        </div>

        <div class="card card-flat meta-card" v-if="problem.topic_tags?.length">
          <h3 class="section-heading">🏷 Topic Tags</h3>
          <div class="tags-wrap">
            <span v-for="tag in problem.topic_tags" :key="tag" class="tag">{{ tag }}</span>
          </div>
        </div>

        <div class="card card-flat meta-card related-card" v-if="relatedProblems.length">
          <h3 class="section-heading">🔗 Related Problems</h3>
          <div class="related-list">
            <router-link
              v-for="item in relatedProblems"
              :key="item.slug"
              :to="`/problem/${item.slug}`"
              class="related-item"
            >
              <span class="related-title">{{ item.title }}</span>
              <span class="badge" :class="getDiffClass(item.difficulty)">
                {{ item.difficulty || 'Unknown' }}
              </span>
            </router-link>
          </div>
        </div>
      </div>
    </div>

    <AIChatPanel
      :key="`problem-ai-${slug}`"
      context-type="problem"
      :context-id="slug"
      :context-label="problem.title"
      :quick-chips="problemChatChips"
    />
  </div>

  <div class="container loading-state" v-else-if="loading">
    <div class="terminal-prompt">loading problem...</div>
  </div>

  <div class="container" v-else>
    <p class="terminal-prompt" style="padding: var(--space-2xl)">problem not found</p>
  </div>
</template>

<style scoped>
.prob-header {
  margin-bottom: var(--space-xl);
}

.breadcrumbs {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--text-xs);
  margin-bottom: var(--space-sm);
  color: var(--text-muted);
}

.breadcrumbs a {
  color: var(--text-secondary);
}

.breadcrumbs a:hover {
  color: var(--accent-cyan);
}

.crumb-current {
  color: var(--accent-cyan);
  max-width: 320px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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

.prob-title-row {
  display: flex;
  gap: var(--space-lg);
  align-items: flex-start;
  margin-bottom: var(--space-md);
}

.prob-number-wrap {
  padding-top: 4px;
}

.prob-number {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--accent-cyan);
  opacity: 0.6;
}

.prob-title {
  font-size: var(--text-2xl);
  font-weight: 800;
  margin-bottom: var(--space-sm);
}

.prob-badges {
  display: flex;
  gap: var(--space-xs);
  flex-wrap: wrap;
}

.prob-actions {
  display: flex;
  gap: var(--space-sm);
  margin-bottom: var(--space-md);
  flex-wrap: wrap;
}

.confidence-row {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
}

.conf-label {
  font-size: var(--text-sm);
}

.conf-btn {
  padding: 4px 12px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.conf-btn:hover {
  border-color: var(--accent-cyan);
  color: var(--text-primary);
}

.conf-btn.active {
  border-color: var(--accent-green);
  background: rgba(34, 211, 167, 0.1);
  color: var(--accent-green);
}

/* ── Notes ──────────────────────────── */
.section-heading {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: var(--text-base);
  font-weight: 700;
  margin-bottom: var(--space-md);
}

.note-textarea {
  width: 100%;
  padding: var(--space-md);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: 1.6;
  resize: vertical;
  transition: border-color var(--transition-fast);
}

.note-textarea:focus {
  outline: none;
  border-color: var(--accent-cyan);
  box-shadow: var(--glow-cyan);
}

.note-textarea::placeholder {
  color: var(--text-muted);
}

/* ── Solution Breakdown ─────────────── */
.solution-breakdown-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-md);
  margin-bottom: var(--space-md);
}

.solution-breakdown-sub {
  margin: 0;
  color: var(--text-muted);
  font-size: var(--text-sm);
}

.solution-breakdown-body {
  display: grid;
  gap: var(--space-md);
}

.solution-callout {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  padding: var(--space-sm) var(--space-md);
}

.solution-callout-label {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 6px;
}

.solution-callout-text {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.7;
}

.solution-step-list {
  list-style: none;
  display: grid;
  gap: var(--space-sm);
  padding: 0;
  margin: 0;
}

.solution-step-item {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  padding: var(--space-sm) var(--space-md);
}

.solution-step-index {
  font-size: var(--text-xs);
  color: var(--accent-cyan);
}

.solution-step-title {
  margin: 4px 0 6px;
  font-size: var(--text-base);
}

.solution-step-detail {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.7;
}

.solution-extra {
  display: grid;
  gap: var(--space-md);
}

.solution-code-wrap {
  display: grid;
  gap: var(--space-sm);
}

.solution-checklists {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-md);
}

.solution-list-card {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  padding: var(--space-sm) var(--space-md);
}

.solution-mini-list {
  display: grid;
  gap: 6px;
  margin: 0;
  padding-left: 18px;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  line-height: 1.6;
}

/* ── Insights Grid ──────────────────── */
.insights-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-md);
  margin-bottom: var(--space-xl);
}

.insight-card {
  padding: var(--space-lg);
}

.insight-signal {
  background: linear-gradient(160deg, rgba(56, 189, 248, 0.08), rgba(56, 189, 248, 0.02));
}

.insight-key {
  background: linear-gradient(160deg, rgba(34, 211, 167, 0.08), rgba(34, 211, 167, 0.02));
}

.insight-deviation {
  background: linear-gradient(160deg, rgba(167, 139, 250, 0.08), rgba(167, 139, 250, 0.02));
}

.insight-warning {
  background: linear-gradient(160deg, rgba(251, 146, 60, 0.08), rgba(251, 146, 60, 0.02));
}

.insight-label {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: var(--space-sm);
}

.insight-icon {
  font-size: var(--text-base);
}

.insight-text {
  color: var(--text-secondary);
  font-size: var(--text-sm);
  line-height: 1.7;
}

.insight-text.highlight {
  color: var(--accent-green);
  font-weight: 500;
}

.insight-text.warning {
  color: var(--accent-orange);
}

/* ── Meta Row ───────────────────────── */
.meta-row {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--space-md);
}

.meta-side {
  display: grid;
  gap: var(--space-md);
}

.complexity-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-lg);
}

.complexity-block {
  padding: var(--space-sm) var(--space-md);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
}

.comp-label {
  display: block;
  font-size: var(--text-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
}

.comp-desc {
  margin-bottom: var(--space-sm);
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.comp-list {
  list-style: none;
  display: grid;
  gap: 8px;
}

.comp-value {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--accent-cyan);
  line-height: 1.6;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.tags-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs);
}

.company-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs);
}

.followups-wrap {
  margin-top: var(--space-md);
}

.followups-label {
  display: inline-block;
  margin-bottom: var(--space-sm);
  font-size: var(--text-xs);
}

.related-list {
  display: grid;
  gap: 6px;
}

.related-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  padding: 8px 10px;
  color: inherit;
}

.related-item:hover {
  border-color: var(--accent-cyan);
}

.related-title {
  color: var(--text-primary);
  font-size: var(--text-sm);
}

/* ── Reflection Grid ────────────────── */
.reflection-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-sm);
}

.reflection-item {
  padding: var(--space-sm) var(--space-md);
  background: var(--bg-elevated);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
}

.refl-label {
  display: block;
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-bottom: 4px;
}

.refl-val {
  display: block;
  font-size: var(--text-sm);
  color: var(--text-primary);
  line-height: 1.5;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
}

@media (max-width: 768px) {
  .insights-grid {
    grid-template-columns: 1fr;
  }

  .meta-row {
    grid-template-columns: 1fr;
  }

  .complexity-grid {
    grid-template-columns: 1fr;
  }

  .prob-title-row {
    flex-direction: column;
    gap: var(--space-sm);
  }

  .solution-breakdown-head {
    flex-direction: column;
    align-items: stretch;
  }

  .solution-checklists {
    grid-template-columns: 1fr;
  }

  .breadcrumbs {
    flex-wrap: wrap;
  }
}
</style>
