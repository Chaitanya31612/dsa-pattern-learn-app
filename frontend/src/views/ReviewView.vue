<script setup lang="ts">
import { computed, ref } from 'vue'
import { usePatterns } from '../composables/usePatterns'
import { useProgress } from '../composables/useProgress'

const { problems, patterns, loading } = usePatterns()
const { getDueForReview, isSolved, getConfidence, getReflection, markSolved, state } = useProgress()

const dueSlugs = computed(() => getDueForReview())
const dueProblems = computed(() =>
  dueSlugs.value
    .map(slug => problems.value[slug])
    .filter(Boolean)
    .sort((a, b) => {
      // Show lowest confidence first
      const confA = getConfidence(a.slug) ?? 0
      const confB = getConfidence(b.slug) ?? 0
      return confA - confB
    })
)

const expandedSlug = ref<string | null>(null)

function toggleExpand(slug: string) {
  expandedSlug.value = expandedSlug.value === slug ? null : slug
}

function reviewDone(slug: string, newConf: 1 | 2 | 3) {
  markSolved(slug, newConf)
}

function getDiffClass(diff: string | null): string {
  if (!diff) return ''
  return `badge-${diff.toLowerCase()}`
}

function getConfLabel(conf: number | null): string {
  if (conf === 1) return '😟 Shaky'
  if (conf === 2) return '😐 Okay'
  if (conf === 3) return '😎 Solid'
  return '?'
}

function daysSinceSolved(slug: string): number {
  const info = state.solved[slug]
  if (!info) return 0
  return Math.floor((Date.now() - new Date(info.date).getTime()) / (1000 * 60 * 60 * 24))
}

// Stats
const totalSolved = computed(() => Object.keys(state.solved).length)
const avgConfidence = computed(() => {
  const vals = Object.values(state.solved).map(s => s.confidence)
  if (vals.length === 0) return 0
  return (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1)
})
</script>

<template>
  <div class="container review-view" v-if="!loading">
    <header class="rv-header animate-in">
      <div>
        <span class="terminal-prompt">review_queue.status()</span>
        <h1 class="rv-title">Spaced Repetition</h1>
      </div>
      <div class="rv-stats">
        <div class="stat-pill">
          <span class="stat-num" style="color: var(--accent-orange)">{{ dueProblems.length }}</span>
          <span class="stat-txt">due today</span>
        </div>
        <div class="stat-pill">
          <span class="stat-num" style="color: var(--accent-green)">{{ totalSolved }}</span>
          <span class="stat-txt">total solved</span>
        </div>
        <div class="stat-pill">
          <span class="stat-num" style="color: var(--accent-cyan)">{{ avgConfidence }}</span>
          <span class="stat-txt">avg confidence</span>
        </div>
      </div>
    </header>

    <!-- Empty State -->
    <div v-if="dueProblems.length === 0" class="empty-state animate-in stagger-1">
      <div class="empty-card card card-flat">
        <div class="empty-icon">✅</div>
        <h3>All caught up!</h3>
        <p v-if="totalSolved === 0" class="empty-desc">
          Start solving problems and mark them with a confidence level.
          <br/>They'll appear here when due for review.
        </p>
        <p v-else class="empty-desc">
          No problems due for review right now. Keep solving!
          <br/>Your next review will appear based on your confidence ratings.
        </p>
        <router-link to="/" class="btn btn-primary" style="margin-top: var(--space-md)">
          ← Back to Dashboard
        </router-link>
      </div>
    </div>

    <!-- Due Problems -->
    <div v-else class="due-list">
      <div class="due-info animate-in stagger-1">
        <p class="terminal-prompt">Review these problems to strengthen your pattern recognition.</p>
        <p style="font-size: var(--text-sm); color: var(--text-muted); margin-top: 4px">
          Update your confidence after re-attempting each problem.
        </p>
      </div>

      <div
        v-for="(problem, idx) in dueProblems"
        :key="problem.slug"
        class="due-card card animate-in"
        :class="[`stagger-${Math.min(idx + 2, 6)}`, { expanded: expandedSlug === problem.slug }]"
      >
        <div class="due-main" @click="toggleExpand(problem.slug)">
          <div class="due-left">
            <span class="due-num mono">#{{ problem.number }}</span>
            <div class="due-info-block">
              <span class="due-title">{{ problem.title }}</span>
              <div class="due-meta">
                <span class="badge" :class="getDiffClass(problem.difficulty)">
                  {{ problem.difficulty }}
                </span>
                <router-link :to="`/pattern/${problem.pattern_id}`" class="due-pattern">
                  {{ problem.pattern_name }}
                </router-link>
                <span class="due-days mono">{{ daysSinceSolved(problem.slug) }}d ago</span>
                <span class="due-conf">{{ getConfLabel(getConfidence(problem.slug)) }}</span>
              </div>
            </div>
          </div>
          <span class="expand-icon">{{ expandedSlug === problem.slug ? '▾' : '▸' }}</span>
        </div>

        <!-- Expanded Content -->
        <div v-if="expandedSlug === problem.slug" class="due-expanded animate-in">
          <!-- Previous reflection -->
          <div class="reflection-recall" v-if="getReflection(problem.slug)">
            <h4 class="recall-heading">Your Previous Reflection</h4>
            <div class="recall-grid">
              <div class="recall-item">
                <span class="recall-label">🎯 Pattern</span>
                <span class="recall-val">{{ getReflection(problem.slug)!.pattern }}</span>
              </div>
              <div class="recall-item">
                <span class="recall-label">🔍 Signal</span>
                <span class="recall-val">{{ getReflection(problem.slug)!.signal }}</span>
              </div>
              <div class="recall-item">
                <span class="recall-label">🔧 Deviation</span>
                <span class="recall-val">{{ getReflection(problem.slug)!.deviation }}</span>
              </div>
            </div>
          </div>

          <!-- Insights -->
          <div class="insight-row" v-if="problem.key_insight">
            <span class="insight-label">💡 Key Insight</span>
            <span class="insight-val">{{ problem.key_insight }}</span>
          </div>

          <!-- Actions -->
          <div class="due-actions">
            <a :href="problem.leetcode_url" target="_blank" class="btn">
              Open on LeetCode ↗
            </a>
            <router-link :to="`/problem/${problem.slug}`" class="btn">
              View Details
            </router-link>
            <div style="flex:1"></div>
            <span class="conf-update-label mono">Update confidence:</span>
            <button class="conf-mini" :class="{ active: getConfidence(problem.slug) === 1 }" @click.stop="reviewDone(problem.slug, 1)">😟</button>
            <button class="conf-mini" :class="{ active: getConfidence(problem.slug) === 2 }" @click.stop="reviewDone(problem.slug, 2)">😐</button>
            <button class="conf-mini" :class="{ active: getConfidence(problem.slug) === 3 }" @click.stop="reviewDone(problem.slug, 3)">😎</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="container loading-state" v-else>
    <div class="terminal-prompt">loading review queue...</div>
  </div>
</template>

<style scoped>
.rv-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: var(--space-xl);
  flex-wrap: wrap;
  gap: var(--space-md);
}

.rv-title {
  font-size: var(--text-2xl);
  font-weight: 800;
}

.rv-stats {
  display: flex;
  gap: var(--space-sm);
}

.stat-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}

.stat-num {
  font-weight: 700;
}

.stat-txt {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

/* ── Empty State ──────────────────── */
.empty-state {
  display: flex;
  justify-content: center;
  padding: var(--space-3xl) 0;
}

.empty-card {
  text-align: center;
  max-width: 400px;
  padding: var(--space-2xl);
}

.empty-icon {
  font-size: 48px;
  margin-bottom: var(--space-md);
}

.empty-card h3 {
  font-size: var(--text-xl);
  margin-bottom: var(--space-sm);
}

.empty-desc {
  color: var(--text-secondary);
  font-size: var(--text-sm);
  line-height: 1.7;
}

/* ── Due List ─────────────────────── */
.due-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.due-info {
  margin-bottom: var(--space-md);
}

.due-card {
  padding: 0;
  cursor: pointer;
}

.due-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-md) var(--space-lg);
}

.due-left {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  min-width: 0;
}

.due-num {
  color: var(--text-muted);
  font-size: var(--text-sm);
  flex-shrink: 0;
  width: 48px;
}

.due-title {
  display: block;
  font-weight: 600;
  font-size: var(--text-base);
  margin-bottom: 4px;
}

.due-meta {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
}

.due-pattern {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.due-days {
  font-size: var(--text-xs);
  color: var(--accent-orange);
}

.due-conf {
  font-size: var(--text-xs);
}

.expand-icon {
  color: var(--text-muted);
  font-size: var(--text-sm);
  flex-shrink: 0;
}

/* ── Expanded ─────────────────────── */
.due-expanded {
  padding: 0 var(--space-lg) var(--space-lg);
  border-top: 1px solid var(--border-subtle);
  padding-top: var(--space-md);
}

.reflection-recall {
  margin-bottom: var(--space-md);
}

.recall-heading {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: var(--space-sm);
}

.recall-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-sm);
}

.recall-item {
  padding: var(--space-sm);
  background: var(--bg-elevated);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
}

.recall-label {
  display: block;
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-bottom: 2px;
}

.recall-val {
  font-size: var(--text-sm);
  color: var(--text-primary);
  line-height: 1.5;
}

.insight-row {
  display: flex;
  gap: var(--space-sm);
  margin-bottom: var(--space-md);
  padding: var(--space-sm);
  background: rgba(34, 211, 167, 0.05);
  border-radius: var(--radius-sm);
  border: 1px solid rgba(34, 211, 167, 0.1);
}

.insight-label {
  flex-shrink: 0;
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.insight-val {
  font-size: var(--text-sm);
  color: var(--accent-green);
}

.due-actions {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
}

.conf-update-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.conf-mini {
  width: 32px;
  height: 32px;
  border: 2px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.conf-mini:hover {
  border-color: var(--accent-cyan);
  transform: scale(1.1);
}

.conf-mini.active {
  border-color: var(--accent-green);
  background: rgba(34, 211, 167, 0.1);
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
}

@media (max-width: 768px) {
  .rv-stats {
    flex-wrap: wrap;
  }

  .recall-grid {
    grid-template-columns: 1fr;
  }
}
</style>
