// A personal hosted-backend access key, never a Groq/Gemini provider key.
const KEY = 'patternfirst-hosted-ai-access'

export function hostedAIKey(): string {
  try { return sessionStorage.getItem(KEY) ?? '' } catch { return '' }
}

export function saveHostedAIKey(value: string): void {
  if (value.trim()) sessionStorage.setItem(KEY, value.trim())
  else sessionStorage.removeItem(KEY)
}

export function aiHeaders(): Record<string, string> {
  const key = hostedAIKey()
  return { 'Content-Type': 'application/json', ...(key ? { Authorization: `Bearer ${key}` } : {}) }
}

export function aiURL(path: string): string {
  const base = (import.meta.env.VITE_API_BASE_URL ?? '').trim().replace(/\/$/, '')
  return `${base}${path}`
}
