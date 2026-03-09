<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { useAIChat } from '../composables/useAIChat'
import hljs from 'highlight.js/lib/core'
import java from 'highlight.js/lib/languages/java'
import python from 'highlight.js/lib/languages/python'
import javascript from 'highlight.js/lib/languages/javascript'

hljs.registerLanguage('java', java)
hljs.registerLanguage('python', python)
hljs.registerLanguage('javascript', javascript)

const props = defineProps<{
  contextType: 'pattern' | 'problem'
  contextId: string
  contextLabel: string
  quickChips?: string[]
}>()

const defaultPatternChips = [
  'Explain this pattern simply',
  'Show me the template code',
  'When should I NOT use this?',
  'Compare with a related pattern',
]

const defaultProblemChips = [
  'Walk me through the approach',
  'Show the optimal solution',
  'What are the edge cases?',
  'Explain the time complexity',
]

const chips = computed(() => {
  if (props.quickChips?.length) return props.quickChips
  return props.contextType === 'pattern' ? defaultPatternChips : defaultProblemChips
})

const isOpen = ref(false)
const isExpanded = ref(false)
const inputText = ref('')
const threadRef = ref<HTMLElement | null>(null)

const { messages, isLoading, sendMessage, clearChat } = useAIChat(
  props.contextType,
  props.contextId,
)

function toggle() {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    nextTick(() => scrollToBottom())
  }
}

function toggleExpanded() {
  isExpanded.value = !isExpanded.value
  nextTick(() => scrollToBottom())
}

function scrollToBottom() {
  if (!threadRef.value) return
  threadRef.value.scrollTop = threadRef.value.scrollHeight
}

watch(
  () => messages.value.length,
  async () => {
    await nextTick()
    scrollToBottom()
  },
)

async function handleSend() {
  const text = inputText.value.trim()
  if (!text) return
  inputText.value = ''
  await sendMessage(text)
}

async function handleChipClick(chip: string) {
  await sendMessage(chip)
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSend()
  }
}

function handleClear() {
  clearChat()
}

/**
 * Render message content with basic markdown support.
 * Handles: code blocks (```), inline code (`), bold (**), line breaks.
 */
function renderMarkdown(content: string): string {
  let html = content

  // Escape HTML entities first
  html = html
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // Fenced code blocks: ```lang\n...\n```
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_match, lang, code) => {
    const language = lang || 'java'
    let highlighted = code.trim()
    try {
      if (hljs.getLanguage(language)) {
        highlighted = hljs.highlight(code.trim(), { language }).value
      }
    } catch {
      // keep raw
    }
    return `<div class="ai-code-block"><span class="ai-code-lang">${language}</span><pre><code class="hljs">${highlighted}</code></pre></div>`
  })

  // Inline code: `code`
  html = html.replace(/`([^`]+)`/g, '<code class="ai-inline-code">$1</code>')

  // Bold: **text**
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')

  // Line breaks
  html = html.replace(/\n/g, '<br/>')

  return html
}
</script>

<template>
  <!-- Floating chat trigger button -->
  <button
    class="ai-chat-trigger"
    :class="{ open: isOpen }"
    @click="toggle"
    :title="isOpen ? 'Close AI Chat' : 'Ask AI'"
  >
    <span class="trigger-icon">{{ isOpen ? '✕' : '🤖' }}</span>
    <span class="trigger-label" v-if="!isOpen">Ask AI</span>
  </button>

  <!-- Chat panel -->
  <Transition name="chat-slide">
    <div v-if="isOpen" class="ai-chat-panel" :class="{ expanded: isExpanded }">
      <!-- Header -->
      <header class="ai-chat-header">
        <div class="ai-chat-header-info">
          <span class="ai-chat-avatar">🤖</span>
          <div>
            <h3 class="ai-chat-title">AI Tutor</h3>
            <span class="ai-chat-ctx mono">{{ contextLabel }}</span>
          </div>
        </div>
        <div class="ai-chat-header-actions">
          <button
            class="btn-icon"
            @click="toggleExpanded"
            :title="isExpanded ? 'Exit full screen' : 'Expand to full screen'"
          >
            {{ isExpanded ? '🗕' : '⛶' }}
          </button>
          <button class="btn-icon" @click="handleClear" title="Clear chat">🗑</button>
        </div>
      </header>

      <!-- Message thread -->
      <div class="ai-chat-thread" ref="threadRef">
        <!-- Empty state -->
        <div v-if="messages.length === 0" class="ai-chat-empty">
          <span class="ai-chat-empty-icon">💡</span>
          <p class="ai-chat-empty-text">
            Ask me anything about
            <strong>{{ contextLabel }}</strong>.
            I can explain concepts, show code, walk through solutions, and more.
          </p>

          <!-- Quick suggestion chips -->
          <div class="ai-chip-grid">
            <button
              v-for="chip in chips"
              :key="chip"
              class="ai-chip"
              @click="handleChipClick(chip)"
              :disabled="isLoading"
            >
              {{ chip }}
            </button>
          </div>
        </div>

        <!-- Messages -->
        <div
          v-for="(msg, idx) in messages"
          :key="`${msg.timestamp}-${idx}`"
          class="ai-msg"
          :class="`ai-msg-${msg.role}`"
        >
          <span class="ai-msg-avatar">{{ msg.role === 'assistant' ? '🤖' : '👤' }}</span>
          <div class="ai-msg-body">
            <span class="ai-msg-role mono">
              {{ msg.role === 'assistant' ? 'AI Tutor' : 'You' }}
            </span>
            <div class="ai-msg-content" v-html="renderMarkdown(msg.content)"></div>
          </div>
        </div>

        <!-- Typing indicator -->
        <div v-if="isLoading" class="ai-msg ai-msg-assistant">
          <span class="ai-msg-avatar">🤖</span>
          <div class="ai-msg-body">
            <span class="ai-msg-role mono">AI Tutor</span>
            <div class="ai-typing">
              <span class="ai-typing-dot"></span>
              <span class="ai-typing-dot"></span>
              <span class="ai-typing-dot"></span>
            </div>
          </div>
        </div>
      </div>

      <!-- Quick chips when chat has messages -->
      <div v-if="messages.length > 0 && !isLoading" class="ai-chip-row">
        <button
          v-for="chip in chips.slice(0, 3)"
          :key="chip"
          class="ai-chip ai-chip-sm"
          @click="handleChipClick(chip)"
          :disabled="isLoading"
        >
          {{ chip }}
        </button>
      </div>

      <!-- Input area -->
      <div class="ai-chat-input-area">
        <textarea
          v-model="inputText"
          class="ai-chat-input"
          rows="2"
          :placeholder="contextType === 'pattern'
            ? 'Ask about this pattern, its variations, techniques...'
            : 'Ask about the approach, solution, edge cases...'"
          :disabled="isLoading"
          @keydown="handleKeydown"
        ></textarea>
        <button
          class="btn btn-primary ai-send-btn"
          :disabled="isLoading || !inputText.trim()"
          @click="handleSend"
        >
          {{ isLoading ? '...' : '↑' }}
        </button>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
/* ── Trigger Button ──────────────────────── */
.ai-chat-trigger {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 1000;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border: 1px solid var(--accent-cyan);
  border-radius: 999px;
  background: var(--bg-card);
  color: var(--accent-cyan);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--glow-cyan), var(--shadow-lg);
  transition: all var(--transition-base);
}

.ai-chat-trigger:hover {
  background: var(--bg-card-hover);
  transform: translateY(-2px);
  box-shadow: var(--glow-cyan), var(--shadow-lg), 0 0 40px rgba(56, 189, 248, 0.2);
}

.ai-chat-trigger.open {
  padding: 12px 16px;
  border-radius: 50%;
  background: var(--bg-elevated);
}

.trigger-icon {
  font-size: 18px;
  line-height: 1;
}

/* ── Chat Panel ──────────────────────────── */
.ai-chat-panel {
  position: fixed;
  bottom: 80px;
  right: 24px;
  z-index: 999;
  width: min(560px, calc(100vw - 32px));
  max-height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg), var(--glow-cyan);
  overflow: hidden;
}

.ai-chat-panel.expanded {
  top: 16px;
  right: 16px;
  bottom: 16px;
  left: 16px;
  width: auto;
  max-height: none;
}

/* ── Header ──────────────────────────────── */
.ai-chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: linear-gradient(135deg, rgba(56, 189, 248, 0.08), rgba(34, 211, 167, 0.05));
  border-bottom: 1px solid var(--border-subtle);
}

.ai-chat-header-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ai-chat-avatar {
  font-size: 24px;
  line-height: 1;
}

.ai-chat-title {
  font-size: var(--text-sm);
  font-weight: 700;
  font-family: var(--font-display);
  color: var(--text-primary);
}

.ai-chat-ctx {
  font-size: var(--text-xs);
  color: var(--accent-cyan);
}

.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  transition: background var(--transition-fast);
}

.btn-icon:hover {
  background: var(--bg-elevated);
}

/* ── Thread ──────────────────────────────── */
.ai-chat-thread {
  flex: 1;
  min-height: 300px;
  max-height: 420px;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ai-chat-panel.expanded .ai-chat-thread {
  max-height: none;
}

/* ── Empty State ─────────────────────────── */
.ai-chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 24px 16px;
  gap: 12px;
}

.ai-chat-empty-icon {
  font-size: 32px;
}

.ai-chat-empty-text {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.6;
  max-width: 280px;
}

.ai-chip-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  width: 100%;
  margin-top: 8px;
}

.ai-chip {
  padding: 8px 12px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  color: var(--text-secondary);
  font-family: var(--font-body);
  font-size: var(--text-xs);
  cursor: pointer;
  transition: all var(--transition-fast);
  text-align: left;
  line-height: 1.4;
}

.ai-chip:hover:not(:disabled) {
  border-color: var(--accent-cyan);
  color: var(--accent-cyan);
  background: rgba(56, 189, 248, 0.06);
}

.ai-chip:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ai-chip-row {
  display: flex;
  gap: 4px;
  padding: 6px 12px;
  overflow-x: auto;
  border-top: 1px solid var(--border-subtle);
}

.ai-chip-sm {
  white-space: nowrap;
  padding: 4px 10px;
  font-size: 10px;
}

/* ── Messages ────────────────────────────── */
.ai-msg {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.ai-msg-avatar {
  font-size: 18px;
  line-height: 1;
  flex-shrink: 0;
  margin-top: 2px;
}

.ai-msg-body {
  flex: 1;
  min-width: 0;
}

.ai-msg-role {
  font-size: 10px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  display: block;
  margin-bottom: 3px;
}

.ai-msg-content {
  font-size: var(--text-sm);
  line-height: 1.7;
  color: var(--text-primary);
  word-break: break-word;
}

.ai-msg-user .ai-msg-content {
  color: var(--text-secondary);
}

.ai-msg-assistant {
  padding: 10px;
  background: var(--bg-elevated);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
}

/* ── Typing Indicator ────────────────────── */
.ai-typing {
  display: flex;
  gap: 5px;
  padding: 4px 0;
}

.ai-typing-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent-cyan);
  opacity: 0.4;
  animation: typing-bounce 1.4s infinite ease-in-out;
}

.ai-typing-dot:nth-child(2) {
  animation-delay: 0.16s;
}

.ai-typing-dot:nth-child(3) {
  animation-delay: 0.32s;
}

@keyframes typing-bounce {
  0%, 80%, 100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  40% {
    transform: translateY(-6px);
    opacity: 1;
  }
}

/* ── Code blocks in messages ─────────────── */
.ai-msg-content :deep(.ai-code-block) {
  margin: 8px 0;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-code);
  overflow-x: auto;
  position: relative;
}

.ai-msg-content :deep(.ai-code-lang) {
  position: absolute;
  top: 4px;
  right: 8px;
  font-size: 10px;
  font-family: var(--font-mono);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.ai-msg-content :deep(.ai-code-block pre) {
  padding: 12px;
  margin: 0;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.6;
  overflow-x: auto;
}

.ai-msg-content :deep(.ai-inline-code) {
  font-family: var(--font-mono);
  font-size: 0.88em;
  padding: 1px 5px;
  border-radius: 3px;
  background: var(--bg-code);
  color: var(--accent-cyan);
  border: 1px solid var(--border-subtle);
}

.ai-msg-content :deep(strong) {
  color: var(--accent-cyan);
  font-weight: 600;
}

/* ── Input Area ──────────────────────────── */
.ai-chat-input-area {
  display: flex;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid var(--border-subtle);
  background: var(--bg-secondary);
  align-items: flex-end;
}

.ai-chat-input {
  flex: 1;
  border: 1px solid var(--border-default);
  background: var(--bg-input);
  color: var(--text-primary);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  font-family: var(--font-body);
  font-size: var(--text-sm);
  resize: none;
  line-height: 1.5;
  transition: border-color var(--transition-fast);
}

.ai-chat-input:focus {
  outline: none;
  border-color: var(--accent-cyan);
}

.ai-send-btn {
  padding: 8px 14px;
  min-width: 40px;
  font-size: 16px;
  font-weight: 700;
}

/* ── Slide Animation ─────────────────────── */
.chat-slide-enter-active {
  animation: chat-pop-in 0.3s var(--ease-spring) forwards;
}

.chat-slide-leave-active {
  animation: chat-pop-out 0.2s var(--ease-out) forwards;
}

@keyframes chat-pop-in {
  from {
    opacity: 0;
    transform: translateY(20px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes chat-pop-out {
  from {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
  to {
    opacity: 0;
    transform: translateY(20px) scale(0.95);
  }
}

/* ── Responsive ──────────────────────────── */
@media (max-width: 480px) {
  .ai-chat-panel {
    width: calc(100vw - 16px);
    right: 8px;
    bottom: 72px;
    max-height: calc(100vh - 100px);
  }

  .ai-chat-trigger {
    bottom: 16px;
    right: 16px;
    padding: 10px 16px;
  }

  .trigger-label {
    display: none;
  }
}
</style>
