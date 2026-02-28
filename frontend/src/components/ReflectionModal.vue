<script setup lang="ts">
import { ref, computed } from 'vue'
import { useProgress } from '../composables/useProgress'

const props = defineProps<{
  slug: string
  patternName: string
  problemTitle: string
}>()

const emit = defineEmits<{
  close: []
}>()

const { addReflection, markSolved } = useProgress()

const step = ref(1)
const answers = ref({
  pattern: props.patternName,
  signal: '',
  deviation: '',
})
const confidence = ref<1 | 2 | 3>(2)

const canAdvance = computed(() => {
  if (step.value === 1) return answers.value.pattern.trim().length > 0
  if (step.value === 2) return answers.value.signal.trim().length > 0
  if (step.value === 3) return answers.value.deviation.trim().length > 0
  return true
})

function next() {
  if (step.value < 4) {
    step.value++
  }
}

function back() {
  if (step.value > 1) {
    step.value--
  }
}

function submit() {
  markSolved(props.slug, confidence.value)
  addReflection(props.slug, {
    pattern: answers.value.pattern,
    signal: answers.value.signal,
    deviation: answers.value.deviation,
  })
  emit('close')
}

const steps = [
  { num: 1, label: 'Pattern', icon: '🎯' },
  { num: 2, label: 'Signal', icon: '🔍' },
  { num: 3, label: 'Deviation', icon: '🔧' },
  { num: 4, label: 'Confidence', icon: '📊' },
]
</script>

<template>
  <Teleport to="body">
    <div class="modal-overlay" @click.self="emit('close')">
      <div class="modal-container">
        <!-- Header -->
        <div class="modal-header">
          <div>
            <span class="modal-label terminal-prompt">reflect()</span>
            <h2 class="modal-title">{{ problemTitle }}</h2>
          </div>
          <button class="btn btn-ghost" @click="emit('close')">✕</button>
        </div>

        <!-- Progress dots -->
        <div class="step-dots">
          <div
            v-for="s in steps"
            :key="s.num"
            class="step-dot"
            :class="{ active: step === s.num, done: step > s.num }"
          >
            <span class="step-icon">{{ step > s.num ? '✓' : s.icon }}</span>
            <span class="step-label">{{ s.label }}</span>
          </div>
        </div>

        <!-- Step 1: What pattern? -->
        <div v-if="step === 1" class="step-content animate-in">
          <label class="step-question">What pattern is this?</label>
          <p class="step-hint">Identify the core algorithmic pattern used to solve this problem.</p>
          <input
            v-model="answers.pattern"
            class="step-input"
            type="text"
            placeholder="e.g. Sliding Window, Two Pointers, BFS..."
            autofocus
            @keyup.enter="canAdvance && next()"
          />
        </div>

        <!-- Step 2: What signal? -->
        <div v-if="step === 2" class="step-content animate-in">
          <label class="step-question">What in the problem told you that?</label>
          <p class="step-hint">What words, constraints, or structure in the problem statement signaled this pattern?</p>
          <textarea
            v-model="answers.signal"
            class="step-textarea"
            placeholder='e.g. "longest substring" + constraint on characters → Sliding Window'
            rows="3"
            autofocus
          ></textarea>
        </div>

        <!-- Step 3: Template deviation? -->
        <div v-if="step === 3" class="step-content animate-in">
          <label class="step-question">What's the template deviation?</label>
          <p class="step-hint">How did this specific problem differ from the standard pattern template?</p>
          <textarea
            v-model="answers.deviation"
            class="step-textarea"
            placeholder="e.g. Variable window size instead of fixed, needed a hashmap for counting..."
            rows="3"
            autofocus
          ></textarea>
        </div>

        <!-- Step 4: Confidence -->
        <div v-if="step === 4" class="step-content animate-in">
          <label class="step-question">How confident are you?</label>
          <p class="step-hint">This sets your spaced repetition review interval.</p>
          <div class="confidence-options">
            <button
              v-for="opt in [
                { val: 1 as const, emoji: '😟', label: 'Shaky', desc: 'Review tomorrow', color: 'var(--accent-red)' },
                { val: 2 as const, emoji: '😐', label: 'Okay', desc: 'Review in 3 days', color: 'var(--accent-yellow)' },
                { val: 3 as const, emoji: '😎', label: 'Solid', desc: 'Review in 7 days', color: 'var(--accent-green)' },
              ]"
              :key="opt.val"
              class="conf-option"
              :class="{ selected: confidence === opt.val }"
              :style="{ '--opt-color': opt.color }"
              @click="confidence = opt.val"
            >
              <span class="conf-emoji">{{ opt.emoji }}</span>
              <span class="conf-label">{{ opt.label }}</span>
              <span class="conf-desc">{{ opt.desc }}</span>
            </button>
          </div>
        </div>

        <!-- Footer -->
        <div class="modal-footer">
          <button v-if="step > 1" class="btn" @click="back">← Back</button>
          <div style="flex:1"></div>
          <button
            v-if="step < 4"
            class="btn btn-primary"
            :disabled="!canAdvance"
            @click="next"
          >
            Next →
          </button>
          <button
            v-else
            class="btn btn-primary"
            @click="submit"
          >
            ✓ Save & Mark Solved
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  animation: fade-in 0.2s ease;
}

.modal-container {
  background: var(--bg-card);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  width: 520px;
  max-width: 95vw;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: var(--shadow-lg), var(--glow-cyan);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: var(--space-lg) var(--space-lg) var(--space-md);
}

.modal-label {
  font-size: var(--text-xs);
  display: block;
  margin-bottom: 4px;
}

.modal-title {
  font-size: var(--text-lg);
  font-weight: 700;
}

/* ── Step Dots ──────────────────── */
.step-dots {
  display: flex;
  gap: var(--space-md);
  padding: 0 var(--space-lg);
  margin-bottom: var(--space-lg);
}

.step-dot {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  color: var(--text-muted);
  border: 1px solid transparent;
  transition: all var(--transition-fast);
}

.step-dot.active {
  color: var(--accent-cyan);
  border-color: var(--border-default);
  background: rgba(56, 189, 248, 0.05);
}

.step-dot.done {
  color: var(--accent-green);
}

.step-icon {
  font-size: var(--text-base);
}

.step-label {
  display: none;
}

@media (min-width: 480px) {
  .step-label {
    display: inline;
  }
}

/* ── Step Content ───────────────── */
.step-content {
  padding: 0 var(--space-lg) var(--space-lg);
}

.step-question {
  display: block;
  font-family: var(--font-display);
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.step-hint {
  font-size: var(--text-sm);
  color: var(--text-muted);
  margin-bottom: var(--space-md);
}

.step-input,
.step-textarea {
  width: 100%;
  padding: var(--space-sm) var(--space-md);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: 1.6;
  transition: border-color var(--transition-fast);
}

.step-input:focus,
.step-textarea:focus {
  outline: none;
  border-color: var(--accent-cyan);
  box-shadow: var(--glow-cyan);
}

.step-input::placeholder,
.step-textarea::placeholder {
  color: var(--text-muted);
}

.step-textarea {
  resize: vertical;
}

/* ── Confidence Options ─────────── */
.confidence-options {
  display: flex;
  gap: var(--space-sm);
}

.conf-option {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: var(--space-md);
  border: 2px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--bg-elevated);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.conf-option:hover {
  border-color: var(--opt-color);
}

.conf-option.selected {
  border-color: var(--opt-color);
  background: color-mix(in srgb, var(--opt-color) 8%, transparent);
  box-shadow: 0 0 12px color-mix(in srgb, var(--opt-color) 15%, transparent);
}

.conf-emoji {
  font-size: 28px;
}

.conf-label {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.conf-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

/* ── Footer ─────────────────────── */
.modal-footer {
  display: flex;
  align-items: center;
  padding: var(--space-md) var(--space-lg);
  border-top: 1px solid var(--border-subtle);
}

.modal-footer .btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
