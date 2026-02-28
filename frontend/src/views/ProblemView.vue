<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { usePatterns } from '../composables/usePatterns'
import { useProgress } from '../composables/useProgress'
import ReflectionModal from '../components/ReflectionModal.vue'

const route = useRoute()
const slug = computed(() => route.params.slug as string)

const { problems, loading } = usePatterns()
const { isSolved, markSolved, unmarkSolved, getConfidence, getNote, addNote, getReflection } = useProgress()

const problem = computed(() => problems.value[slug.value])

const solved = computed(() => isSolved(slug.value))
const confidence = computed(() => getConfidence(slug.value))

const noteText = ref('')
const showNotes = ref(false)
const showReflection = ref(false)

// Load existing note
import { watchEffect } from 'vue'
watchEffect(() => {
  if (slug.value) {
    noteText.value = getNote(slug.value)
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
</script>

<template>
  <div class="container problem-view" v-if="!loading && problem">
    <!-- ═══ Header ═══ -->
    <header class="prob-header animate-in">
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
        <button class="btn btn-ghost" @click="showNotes = !showNotes">
          {{ showNotes ? 'Hide Notes' : '✎ Notes' }}
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

    <!-- ═══ Insights Grid ═══ -->
    <div class="insights-grid animate-in stagger-1">
      <div class="card card-flat insight-card" v-if="problem.pattern_hint">
        <div class="insight-label">
          <span class="insight-icon">🔍</span> Pattern Signal
        </div>
        <p class="insight-text">{{ problem.pattern_hint }}</p>
      </div>

      <div class="card card-flat insight-card" v-if="problem.key_insight">
        <div class="insight-label">
          <span class="insight-icon">💡</span> Key Insight
        </div>
        <p class="insight-text highlight">{{ problem.key_insight }}</p>
      </div>

      <div class="card card-flat insight-card" v-if="problem.template_deviation">
        <div class="insight-label">
          <span class="insight-icon">🔧</span> Template Deviation
        </div>
        <p class="insight-text">{{ problem.template_deviation }}</p>
      </div>

      <div class="card card-flat insight-card" v-if="problem.common_mistake">
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
          <div v-if="problem.time_complexity">
            <span class="comp-label">Time</span>
            <span class="comp-value mono">{{ problem.time_complexity }}</span>
          </div>
          <div v-if="problem.space_complexity">
            <span class="comp-label">Space</span>
            <span class="comp-value mono">{{ problem.space_complexity }}</span>
          </div>
        </div>
      </div>

      <div class="card card-flat meta-card" v-if="problem.topic_tags?.length">
        <h3 class="section-heading">🏷 Topic Tags</h3>
        <div class="tags-wrap">
          <span v-for="tag in problem.topic_tags" :key="tag" class="tag">{{ tag }}</span>
        </div>
      </div>
    </div>
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

.complexity-grid {
  display: flex;
  gap: var(--space-xl);
}

.comp-label {
  display: block;
  font-size: var(--text-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 2px;
}

.comp-value {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--accent-cyan);
}

.tags-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs);
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

  .prob-title-row {
    flex-direction: column;
    gap: var(--space-sm);
  }
}
</style>
