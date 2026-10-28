import { aiHeaders } from '../lib/aiConnection'
import { ref, watch } from 'vue'

/**
 * Learning-Mode AI Chat Composable
 * =================================
 *
 * Handles context-aware AI chat for Pattern and Problem views.
 * Unlike the interview chat (sanitized, no solutions), this is
 * LEARNING MODE — full explanations, code, and examples are encouraged.
 *
 * Usage:
 *   const { messages, sendMessage, isLoading, clearChat } = useAIChat('pattern', 'sliding-window')
 *   await sendMessage('Explain this pattern simply')
 */

export interface AIChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

type ContextType = 'pattern' | 'problem' | 'sub-pattern' | 'hld' | 'software' | 'ai-course'
export interface HLDChatContext {
  mode: 'learn' | 'practice' | 'review'
  exercise_id?: string
  file_path?: string
  section_id?: string
  example_id?: string
  attempt?: { phases: Record<string, string>; diagram: string; assisted: boolean }
}

const STORAGE_PREFIX = 'dsa-ai-chat-'

function getApiBaseUrl(): string {
  const base = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ?? ''
  return base.endsWith('/') ? base.slice(0, -1) : base
}

function getApiUrl(path: string): string {
  const base = getApiBaseUrl()
  return base ? `${base}${path}` : path
}

function loadChatHistory(contextType: ContextType, contextId: string): AIChatMessage[] {
  try {
    const key = `${STORAGE_PREFIX}${contextType}-${contextId}`
    const raw = sessionStorage.getItem(key)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function saveChatHistory(contextType: ContextType, contextId: string, messages: AIChatMessage[]) {
  const key = `${STORAGE_PREFIX}${contextType}-${contextId}`
  // Keep only last 30 messages to avoid sessionStorage bloat
  sessionStorage.setItem(key, JSON.stringify(messages.slice(-30)))
}

export function useAIChat(contextType: ContextType, contextId: string, getHLDContext?: () => HLDChatContext | undefined) {
  const initialContext = getHLDContext?.()
  const learning = ['hld', 'software', 'ai-course'].includes(contextType)
  const historyId = learning ? `${contextId}-${initialContext?.mode}-${initialContext?.exercise_id ?? 'lesson'}` : contextId
  const messages = ref<AIChatMessage[]>(loadChatHistory(contextType, historyId))
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Persist chat history on changes
  watch(
    messages,
    (newMessages) => {
      try { saveChatHistory(contextType, historyId, newMessages) } catch { /* Chat remains usable without session storage. */ }
    },
    { deep: true },
  )

  async function sendMessage(content: string): Promise<void> {
    const trimmed = content.trim()
    if (!trimmed || isLoading.value) return

    error.value = null

    // Add user message immediately
    messages.value.push({
      role: 'user',
      content: trimmed,
      timestamp: new Date().toISOString(),
    })

    isLoading.value = true

    try {
      const endpoint =
        contextType === 'ai-course' ? '/api/ai/ai-course-chat' : contextType === 'software' ? '/api/ai/software-chat' : contextType === 'hld' ? '/api/ai/hld-chat' : contextType === 'pattern' || contextType === 'sub-pattern' ? '/api/ai/pattern-chat' : '/api/ai/problem-chat'

      const bodyKey = learning ? 'module_id' : (contextType === 'pattern' || contextType === 'sub-pattern') ? 'pattern_id' : 'problem_slug'

      // Implement a sliding window character limit to prevent 422 payload errors.
      // We iterate backwards to keep the most recent context.
      const MAX_CHARS = 12000
      let charCount = 0
      const payloadMessages = []

      for (let i = messages.value.length - 1; i >= 0; i--) {
        const m = messages.value[i]
        if (!m) continue
        const len = Math.min(m.content.length, 6000)
        if (charCount + len > MAX_CHARS && payloadMessages.length > 0) {
          break
        }
        payloadMessages.unshift({
          role: m.role,
          content: m.content.slice(0, 6000),
        })
        charCount += len
        if (payloadMessages.length >= 30) break
      }

      const body = {
        [bodyKey]: contextId,
        messages: payloadMessages,
        ...(learning ? getHLDContext?.() : {}),
      }

      const response = await fetch(getApiUrl(endpoint), {
        method: 'POST',
        headers: aiHeaders(),
        body: JSON.stringify(body),
      }).catch(() => null);

      if (response?.status === 401) {
        error.value = 'Enter your hosted AI access key in Settings, then retry.'
        return
      }
      if (!response || !response.ok) {
        if (learning) {
          const data = await response?.json().catch(() => null)
          throw new Error(typeof data?.detail === 'string' ? data.detail : 'AI coach is unavailable. Your design is saved. Check the backend/provider or continue with self-review.')
        }
        messages.value.push({
          role: 'assistant',
          content: '🔒 **Demo Mode**: This is a frontend-only deployment for demonstration purposes. For full AI features, please run the project locally with the backend server and your API keys configured.',
          timestamp: new Date().toISOString(),
        });
        return;
      }

      const data = await response.json()
      const reply = String(data.reply ?? 'No response received.')

      messages.value.push({
        role: 'assistant',
        content: reply,
        timestamp: new Date().toISOString(),
      })
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to get AI response'
      error.value = errorMessage
      if (learning) return

      messages.value.push({
        role: 'assistant',
        content: '🔒 **Demo Mode**: This is a frontend-only deployment. The backend server could not be reached. Run locally with backend server and API keys setup for full features.',
        timestamp: new Date().toISOString(),
      })
    } finally {
      isLoading.value = false
    }
  }

  function clearChat() {
    messages.value = []
    const key = `${STORAGE_PREFIX}${contextType}-${historyId}`
    sessionStorage.removeItem(key)
  }

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearChat,
  }
}
