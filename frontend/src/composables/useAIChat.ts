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

type ContextType = 'pattern' | 'problem'

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

export function useAIChat(contextType: ContextType, contextId: string) {
  const messages = ref<AIChatMessage[]>(loadChatHistory(contextType, contextId))
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Persist chat history on changes
  watch(
    messages,
    (newMessages) => {
      saveChatHistory(contextType, contextId, newMessages)
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
        contextType === 'pattern' ? '/api/ai/pattern-chat' : '/api/ai/problem-chat'

      const bodyKey = contextType === 'pattern' ? 'pattern_id' : 'problem_slug'

      const body = {
        [bodyKey]: contextId,
        messages: messages.value.map((m) => ({
          role: m.role,
          content: m.content,
        })),
      }

      const response = await fetch(getApiUrl(endpoint), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!response.ok) {
        throw new Error(`AI chat API failed with status ${response.status}`)
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

      // Add error as assistant message so user can see what happened
      messages.value.push({
        role: 'assistant',
        content: `⚠️ ${errorMessage}. Please check that the backend server is running and try again.`,
        timestamp: new Date().toISOString(),
      })
    } finally {
      isLoading.value = false
    }
  }

  function clearChat() {
    messages.value = []
    const key = `${STORAGE_PREFIX}${contextType}-${contextId}`
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
