<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLLDProblems } from '../composables/useLLDProblems'
import { useLLDInterview } from '../composables/useLLDInterview'

const route = useRoute()
const router = useRouter()
const { getProblem, frameworkPhases, coachingStrategy } = useLLDProblems()
const { startSession } = useLLDInterview()

const problem = computed(() => getProblem(String(route.params.id ?? '')))

function handleStart(mode: 'guided' | 'interview') {
  if (!problem.value) return
  startSession(problem.value.id, mode)
  router.push({ name: 'lld-session', params: { id: problem.value.id }, query: { mode } })
}
</script>

<template>
  <div v-if="problem" class="container lld-framework-page">
    <section class="framework-hero animate-in">
      <div>
        <router-link to="/system-design/lld" class="crumb mono">← system-design / lld</router-link>
        <p class="terminal-prompt hero-kicker">problem.{{ String(problem.number).padStart(2, '0') }}</p>
        <h1>{{ problem.title }}</h1>
        <p class="hero-description">{{ problem.description }}</p>
      </div>

      <div class="hero-meta card">
        <div class="meta-row">
          <span class="meta-label mono">difficulty</span>
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
        <div class="meta-row">
          <span class="meta-label mono">guided / interview</span>
          <strong>{{ problem.duration.guided }} / {{ problem.duration.interview }} min</strong>
        </div>
        <div class="tag-row">
          <span v-for="tag in problem.tags" :key="tag" class="tag-chip mono">{{ tag }}</span>
        </div>
      </div>
    </section>

    <section class="framework-layout animate-in stagger-2">
      <aside class="framework-side">
        <article class="card sticky-card">
          <div class="section-head">
            <span class="section-label terminal-prompt">repeatable SOP</span>
          </div>
          <div class="phase-stack">
            <div v-for="phase in frameworkPhases" :key="phase.id" class="phase-card">
              <div class="phase-card-top">
                <strong>{{ phase.title }}</strong>
                <span class="mono">{{ phase.timebox }}</span>
              </div>
              <p>{{ phase.focus }}</p>
              <small>{{ phase.coachingPrompt }}</small>
            </div>
          </div>
        </article>

        <article class="card strategy-card">
          <div class="section-head">
            <span class="section-label terminal-prompt">mastery loop</span>
          </div>
          <ol class="strategy-list">
            <li v-for="item in coachingStrategy" :key="item">{{ item }}</li>
          </ol>
        </article>
      </aside>

      <div class="framework-main">
        <article class="card detail-card">
          <div class="section-head">
            <span class="section-label terminal-prompt">requirements</span>
          </div>
          <div class="detail-grid three-col">
            <div>
              <h3>Must Have</h3>
              <ul>
                <li v-for="item in problem.framework.requirements.must_have" :key="item">{{ item }}</li>
              </ul>
            </div>
            <div>
              <h3>Nice to Have</h3>
              <ul>
                <li v-for="item in problem.framework.requirements.nice_to_have" :key="item">{{ item }}</li>
              </ul>
            </div>
            <div>
              <h3>Out of Scope</h3>
              <ul>
                <li v-for="item in problem.framework.requirements.out_of_scope" :key="item">{{ item }}</li>
              </ul>
            </div>
          </div>
          <div class="prompt-box">
            <h3>Clarifying questions to ask first</h3>
            <ul>
              <li v-for="item in problem.framework.requirements.clarifying_questions" :key="item">{{ item }}</li>
            </ul>
          </div>
        </article>

        <article class="card detail-card">
          <div class="section-head">
            <span class="section-label terminal-prompt">model + contracts</span>
          </div>
          <div class="entity-grid">
            <div v-for="entity in problem.framework.entities.classes" :key="entity.name" class="entity-card">
              <h3>{{ entity.name }}</h3>
              <p>{{ entity.responsibility }}</p>
              <div>
                <strong>Fields</strong>
                <ul>
                  <li v-for="field in entity.fields" :key="field">{{ field }}</li>
                </ul>
              </div>
              <div>
                <strong>Methods</strong>
                <ul>
                  <li v-for="method in entity.methods" :key="method">{{ method }}</li>
                </ul>
              </div>
            </div>
          </div>
          <div class="detail-grid two-col lower-grid">
            <div class="prompt-box">
              <h3>Relationships</h3>
              <ul>
                <li v-for="item in problem.framework.entities.relationships" :key="item">{{ item }}</li>
              </ul>
            </div>
            <div class="prompt-box">
              <h3>Design patterns worth using</h3>
              <ul>
                <li v-for="pattern in problem.framework.design_patterns" :key="pattern.name + pattern.applied_to">
                  <strong>{{ pattern.name }}</strong> · {{ pattern.applied_to }}<br />
                  <span>{{ pattern.why }}</span>
                </li>
              </ul>
            </div>
          </div>
          <div class="uml-block code-block">
            <span class="code-lang">uml</span>
            <pre>{{ problem.framework.uml_ascii }}</pre>
          </div>
        </article>

        <article class="card detail-card">
          <div class="section-head">
            <span class="section-label terminal-prompt">implementation + review</span>
          </div>
          <div class="detail-grid two-col">
            <div class="prompt-box">
              <h3>Implementation order</h3>
              <ol>
                <li v-for="item in problem.framework.implementation_order" :key="item">{{ item }}</li>
              </ol>
            </div>
            <div class="prompt-box">
              <h3>Key phrases to say out loud</h3>
              <ul>
                <li v-for="item in problem.framework.key_phrases" :key="item">{{ item }}</li>
              </ul>
            </div>
          </div>
          <div class="detail-grid two-col lower-grid">
            <div class="prompt-box danger-box">
              <h3>Common interview mistakes</h3>
              <ul>
                <li v-for="item in problem.framework.gotchas" :key="item">{{ item }}</li>
              </ul>
            </div>
            <div class="prompt-box success-box">
              <h3>Extensibility follow-up</h3>
              <p>{{ problem.framework.extensibility_test }}</p>
            </div>
          </div>
        </article>

        <article class="card launch-card">
          <div>
            <span class="section-label terminal-prompt">start.session</span>
            <h2>Choose the pressure level</h2>
            <p>
              Guided mode keeps the framework visible and lets the AI coach hand you structure.
              Interview mode removes most guardrails and pushes you to drive the round yourself.
            </p>
          </div>
          <div class="launch-actions">
            <button class="btn btn-primary launch-btn" @click="handleStart('guided')">
              Guided Mode · {{ problem.duration.guided }} min
            </button>
            <button class="btn launch-btn" @click="handleStart('interview')">
              Interview Mode · {{ problem.duration.interview }} min
            </button>
          </div>
        </article>
      </div>
    </section>
  </div>

  <div v-else class="container not-found">
    <div class="card">
      <p class="terminal-prompt">lld.problem.not_found</p>
      <router-link to="/system-design/lld" class="btn">Back to LLD catalog</router-link>
    </div>
  </div>
</template>

<style scoped>
.lld-framework-page {
  display: grid;
  gap: var(--space-xl);
}

.framework-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(260px, 0.8fr);
  gap: var(--space-lg);
  align-items: start;
}

.crumb {
  display: inline-block;
  margin-bottom: var(--space-md);
  color: var(--text-muted);
}

.hero-kicker {
  margin-bottom: var(--space-sm);
}

.framework-hero h1 {
  font-size: clamp(2.4rem, 3vw, 3.2rem);
  margin-bottom: var(--space-sm);
}

.hero-description {
  color: var(--text-secondary);
  max-width: 66ch;
}

.hero-meta {
  display: grid;
  gap: var(--space-md);
}

.meta-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-md);
}

.meta-label {
  color: var(--text-muted);
  font-size: var(--text-xs);
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

.framework-layout {
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: var(--space-lg);
  align-items: start;
}

.framework-side {
  display: grid;
  gap: var(--space-lg);
}

.sticky-card {
  position: sticky;
  top: 84px;
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

.phase-stack {
  display: grid;
  gap: var(--space-sm);
}

.phase-card {
  padding: var(--space-md);
  border-radius: var(--radius-md);
  border: 1px solid color-mix(in srgb, var(--accent-cyan) 16%, transparent);
  background: color-mix(in srgb, var(--bg-secondary) 70%, transparent);
}

.phase-card-top {
  display: flex;
  justify-content: space-between;
  gap: var(--space-md);
  margin-bottom: 6px;
}

.phase-card p,
.phase-card small,
.strategy-list {
  color: var(--text-secondary);
}

.strategy-list {
  display: grid;
  gap: var(--space-md);
  padding-left: 1.15rem;
}

.framework-main {
  display: grid;
  gap: var(--space-lg);
}

.detail-card {
  display: grid;
  gap: var(--space-lg);
}

.detail-grid {
  display: grid;
  gap: var(--space-lg);
}

.detail-grid.two-col {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.detail-grid.three-col {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.detail-card h3 {
  margin-bottom: var(--space-sm);
  font-size: var(--text-lg);
}

.detail-card ul,
.detail-card ol {
  padding-left: 1.1rem;
  color: var(--text-secondary);
  display: grid;
  gap: 8px;
}

.entity-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-md);
}

.entity-card,
.prompt-box {
  padding: var(--space-md);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  background: color-mix(in srgb, var(--bg-secondary) 72%, transparent);
}

.entity-card p,
.prompt-box p,
.prompt-box span {
  color: var(--text-secondary);
}

.entity-card div + div {
  margin-top: var(--space-sm);
}

.lower-grid {
  margin-top: calc(-1 * var(--space-sm));
}

.uml-block pre {
  white-space: pre-wrap;
}

.danger-box {
  border-color: color-mix(in srgb, var(--accent-red) 20%, transparent);
}

.success-box {
  border-color: color-mix(in srgb, var(--accent-green) 20%, transparent);
}

.launch-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-lg);
  align-items: center;
}

.launch-card p {
  color: var(--text-secondary);
  margin-top: 6px;
  max-width: 60ch;
}

.launch-actions {
  display: grid;
  gap: var(--space-sm);
}

.launch-btn {
  justify-content: center;
  min-width: 250px;
}

.not-found {
  min-height: 50vh;
  display: grid;
  place-items: center;
}

@media (max-width: 1200px) {
  .framework-hero,
  .framework-layout,
  .detail-grid.three-col,
  .detail-grid.two-col,
  .entity-grid,
  .launch-card {
    grid-template-columns: 1fr;
  }

  .sticky-card {
    position: static;
  }
}
</style>
