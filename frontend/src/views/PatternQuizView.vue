<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue'
import { usePatterns } from '../composables/usePatterns'
import { useProgress } from '../composables/useProgress'
import type { Problem } from '../types'

const { getAllProblems, patterns, loading } = usePatterns()
const { isSolved } = useProgress()

const filterPattern = ref<string>('all')
const showAnswer = ref(false)
const currentProblem = ref<Problem | null>(null)
const userGuess = ref('')
const score = ref({ correct: 0, total: 0 })
const history = ref<Array<{ problem: Problem; guess: string; correct: boolean }>>([])
const showFullDescription = ref(false)
const showHint = ref(false)
const QUIZ_DESCRIPTION_PREVIEW_CHARS = 360

function extractDescription(problem: Problem | null): string {
  if (!problem) return ''

  if (problem.description_text?.trim()) {
    return problem.description_text.replace(/\s+/g, ' ').trim()
  }

  const html = problem.description_html ?? ''
  return html
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

const fullDescription = computed(() => extractDescription(currentProblem.value))
const hasExpandableDescription = computed(() => fullDescription.value.length > QUIZ_DESCRIPTION_PREVIEW_CHARS)
const descriptionPreview = computed(() => {
  if (!fullDescription.value) return ''
  if (showFullDescription.value || !hasExpandableDescription.value) return fullDescription.value
  return `${fullDescription.value.slice(0, QUIZ_DESCRIPTION_PREVIEW_CHARS).trimEnd()}...`
})

function pickRandom() {
  let pool = getAllProblems()
  if (filterPattern.value !== 'all') {
    pool = pool.filter(p => p.pattern_id === filterPattern.value)
  }
  if (pool.length === 0) return
  const idx = Math.floor(Math.random() * pool.length)
  const selected = pool[idx]
  if (!selected) return
  currentProblem.value = selected
  showAnswer.value = false
  userGuess.value = ''
  showFullDescription.value = false
  showHint.value = false
}

function reveal() {
  if (!currentProblem.value) return
  showAnswer.value = true
  score.value.total++

  const guessNorm = userGuess.value.toLowerCase().trim()
  const patternNorm = currentProblem.value.pattern_name.toLowerCase()
  const patternId = currentProblem.value.pattern_id.toLowerCase()
  const patternFirstToken = patternNorm.split(' ')[0] ?? ''
  const patternIdFirstToken = patternId.split('-')[0] ?? ''

  // Fuzzy match: check if guess contains key words of the pattern
  const isCorrect =
    patternNorm.includes(guessNorm) ||
    patternId.includes(guessNorm.replace(/\s+/g, '-')) ||
    guessNorm.includes(patternFirstToken) ||
    guessNorm.includes(patternIdFirstToken)

  if (isCorrect && guessNorm.length > 1) {
    score.value.correct++
  }

  history.value.unshift({
    problem: currentProblem.value,
    guess: userGuess.value || '(skipped)',
    correct: isCorrect && guessNorm.length > 1,
  })
}

function nextProblem() {
  pickRandom()
}

// Start with first problem
function start() {
  score.value = { correct: 0, total: 0 }
  history.value = []
  showHint.value = false
  pickRandom()
}

function getDiffClass(diff: string | null): string {
  if (!diff) return ''
  return `badge-${diff.toLowerCase()}`
}

function toggleDescription() {
  showFullDescription.value = !showFullDescription.value
}

function toggleHint() {
  showHint.value = !showHint.value
}

// Auto-pick first problem when data loads
watchEffect(() => {
  if (!loading.value && !currentProblem.value) {
    pickRandom()
  }
})
</script>

<template>
  <div class="container quiz-view" v-if="!loading">
    <header class="qz-header animate-in">
      <div>
        <span class="terminal-prompt">pattern_quiz.start()</span>
        <h1 class="qz-title">Pattern Identification</h1>
        <p class="qz-desc">Given a problem, can you identify the pattern before looking?</p>
      </div>
      <div class="qz-score" v-if="score.total > 0">
        <span class="score-num" style="color: var(--accent-green)">{{ score.correct }}</span>
        <span class="score-sep">/</span>
        <span class="score-num">{{ score.total }}</span>
        <span class="score-label">correct</span>
      </div>
    </header>

    <!-- Filter -->
    <div class="qz-controls animate-in stagger-1">
      <select v-model="filterPattern" class="filter-select" @change="pickRandom()">
        <option value="all">All Patterns</option>
        <option v-for="p in patterns" :key="p.pattern_id" :value="p.pattern_id">
          {{ p.name }}
        </option>
      </select>
      <button class="btn" @click="start">↻ Reset Score</button>
    </div>

    <!-- Problem Card -->
    <div class="quiz-card card animate-in stagger-2" v-if="currentProblem">
      <div class="qz-problem-header">
        <span class="qz-num mono">#{{ currentProblem.number }}</span>
        <span class="badge" :class="getDiffClass(currentProblem.difficulty)">
          {{ currentProblem.difficulty }}
        </span>
        <span class="badge" v-if="isSolved(currentProblem.slug)" style="color: var(--accent-green)">
          ✓ Previously solved
        </span>
      </div>

      <h2 class="qz-problem-title">{{ currentProblem.title }}</h2>

      <section v-if="descriptionPreview" class="qz-statement">
        <h3 class="qz-statement-heading">Problem Statement</h3>
        <p class="qz-statement-text">{{ descriptionPreview }}</p>
        <button v-if="hasExpandableDescription" class="btn btn-ghost statement-toggle" @click="toggleDescription">
          {{ showFullDescription ? 'Show less' : 'Show more' }}
        </button>
      </section>

      <!-- Pattern hint (hidden) -->
      <div class="qz-hint-area" v-if="currentProblem.pattern_hint && !showAnswer">
        <button class="hint-toggle btn btn-ghost" @click="toggleHint">
          {{ showHint ? '💡 Hide hint' : '💡 Show hint' }}
        </button>
        <p class="hint-text" v-if="showHint">{{ currentProblem.pattern_hint }}</p>
      </div>

      <!-- Tags clue -->
      <div class="qz-tags" v-if="showHint && !showAnswer && currentProblem.topic_tags?.length">
        <span class="tag" v-for="tag in currentProblem.topic_tags" :key="tag">{{ tag }}</span>
      </div>

      <!-- Guess input -->
      <div class="guess-area" v-if="!showAnswer">
        <label class="guess-label">What pattern is this?</label>
        <div class="guess-row">
          <input
            v-model="userGuess"
            class="guess-input"
            type="text"
            placeholder="Type your guess... (e.g. Sliding Window)"
            @keyup.enter="reveal"
            autofocus
          />
          <button class="btn btn-primary" @click="reveal">
            Reveal →
          </button>
        </div>
      </div>

      <!-- Answer revealed -->
      <div class="answer-area animate-in" v-if="showAnswer">
        <div class="answer-header">
          <span class="answer-label">The pattern is:</span>
          <span class="answer-pattern">{{ currentProblem.pattern_name }}</span>
        </div>

        <div class="answer-insight" v-if="currentProblem.pattern_hint">
          <span class="insight-icon">🔍</span>
          <span>{{ currentProblem.pattern_hint }}</span>
        </div>

        <div class="answer-insight" v-if="currentProblem.key_insight" style="border-color: rgba(34,211,167,0.15)">
          <span class="insight-icon">💡</span>
          <span>{{ currentProblem.key_insight }}</span>
        </div>

        <div class="answer-actions">
          <router-link :to="`/problem/${currentProblem.slug}`" class="btn">
            View Details
          </router-link>
          <a :href="currentProblem.leetcode_url" target="_blank" class="btn">
            LeetCode ↗
          </a>
          <div style="flex:1"></div>
          <button class="btn btn-primary" @click="nextProblem" autofocus>
            Next Problem →
          </button>
        </div>
      </div>
    </div>

    <!-- History -->
    <div v-if="history.length > 0" class="history-section animate-in stagger-3">
      <h3 class="history-heading terminal-prompt">session_history</h3>
      <div class="history-list">
        <div
          v-for="(h, idx) in history.slice(0, 10)"
          :key="idx"
          class="history-row"
          :class="{ correct: h.correct }"
        >
          <span class="hist-status">{{ h.correct ? '✓' : '✗' }}</span>
          <span class="hist-title">{{ h.problem.title }}</span>
          <span class="hist-guess mono">{{ h.guess }}</span>
          <span class="hist-answer mono">→ {{ h.problem.pattern_name }}</span>
        </div>
      </div>
    </div>
  </div>

  <div class="container loading-state" v-else>
    <div class="terminal-prompt">loading quiz...</div>
  </div>
</template>

<style scoped>
.qz-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: var(--space-xl);
  flex-wrap: wrap;
  gap: var(--space-md);
}

.qz-title {
  font-size: var(--text-2xl);
  font-weight: 800;
}

.qz-desc {
  color: var(--text-secondary);
  font-size: var(--text-sm);
  margin-top: 4px;
}

.qz-score {
  display: flex;
  align-items: baseline;
  gap: 4px;
  font-family: var(--font-mono);
  padding: var(--space-sm) var(--space-md);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-card);
}

.score-num {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--text-primary);
}

.score-sep {
  color: var(--text-muted);
}

.score-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-left: 4px;
}

.qz-controls {
  display: flex;
  gap: var(--space-sm);
  margin-bottom: var(--space-xl);
}

.filter-select {
  padding: 6px 12px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}

/* ── Quiz Card ─────────────────────── */
.quiz-card {
  margin-bottom: var(--space-xl);
  padding: var(--space-xl);
}

.qz-problem-header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: var(--space-sm);
}

.qz-num {
  color: var(--text-muted);
  font-size: var(--text-sm);
}

.qz-problem-title {
  font-size: var(--text-xl);
  font-weight: 800;
  margin-bottom: var(--space-md);
}

.qz-statement {
  margin-bottom: var(--space-lg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  padding: var(--space-md);
}

.qz-statement-heading {
  font-size: var(--text-sm);
  font-family: var(--font-mono);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: var(--space-xs);
}

.qz-statement-text {
  color: var(--text-secondary);
  line-height: 1.7;
  font-size: var(--text-sm);
  overflow-wrap: anywhere;
  word-break: break-word;
}

.statement-toggle {
  margin-top: var(--space-sm);
}

.qz-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs);
  margin-bottom: var(--space-lg);
}

.qz-hint-area {
  margin-bottom: var(--space-lg);
}

.hint-text {
  margin-top: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  background: rgba(251, 191, 36, 0.06);
  border: 1px solid rgba(251, 191, 36, 0.15);
  border-radius: var(--radius-sm);
  color: var(--accent-yellow);
  font-size: var(--text-sm);
}

/* ── Guess ──────────────────────────── */
.guess-label {
  display: block;
  font-family: var(--font-display);
  font-size: var(--text-base);
  font-weight: 600;
  margin-bottom: var(--space-sm);
}

.guess-row {
  display: flex;
  gap: var(--space-sm);
}

.guess-input {
  flex: 1;
  padding: var(--space-sm) var(--space-md);
  border: 2px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: var(--text-base);
  transition: border-color var(--transition-fast);
}

.guess-input:focus {
  outline: none;
  border-color: var(--accent-cyan);
  box-shadow: var(--glow-cyan);
}

/* ── Answer ─────────────────────────── */
.answer-header {
  display: flex;
  align-items: baseline;
  gap: var(--space-sm);
  margin-bottom: var(--space-md);
}

.answer-label {
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

.answer-pattern {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: 800;
  color: var(--accent-cyan);
}

.answer-insight {
  display: flex;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  border-left: 3px solid rgba(56, 189, 248, 0.3);
  margin-bottom: var(--space-sm);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.6;
}

.insight-icon {
  flex-shrink: 0;
}

.answer-actions {
  display: flex;
  gap: var(--space-sm);
  margin-top: var(--space-lg);
  flex-wrap: wrap;
}

/* ── History ────────────────────────── */
.history-section {
  margin-top: var(--space-md);
}

.history-heading {
  margin-bottom: var(--space-md);
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.history-row {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  background: var(--bg-card);
}

.hist-status {
  font-weight: 700;
  color: var(--accent-red);
}

.history-row.correct .hist-status {
  color: var(--accent-green);
}

.hist-title {
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.hist-guess {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.hist-answer {
  color: var(--accent-cyan);
  font-size: var(--text-xs);
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
}

@media (max-width: 768px) {
  .guess-row {
    flex-direction: column;
  }

  .hist-guess, .hist-answer {
    display: none;
  }
}
</style>
