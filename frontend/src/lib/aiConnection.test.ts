import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { aiHeaders, aiURL, hostedAIKey, saveHostedAIKey } from './aiConnection'

beforeEach(() => {
  const values = new Map<string, string>()
  vi.stubGlobal('sessionStorage', {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    removeItem: (key: string) => values.delete(key),
  })
})
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs() })

describe('Hosted AI connection', () => {
  it('adds a personal key only when explicitly saved and removes it on clear', () => {
    expect(aiHeaders()).toEqual({ 'Content-Type': 'application/json' })
    saveHostedAIKey('  personal-access-key  ')
    expect(hostedAIKey()).toBe('personal-access-key')
    expect(aiHeaders().Authorization).toBe('Bearer personal-access-key')
    saveHostedAIKey('')
    expect(aiHeaders().Authorization).toBeUndefined()
  })
  it('uses the configured hosted URL for DSA analysis too', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://worker.example/')
    expect(aiURL('/api/analyze-code')).toBe('https://worker.example/api/analyze-code')
    vi.stubEnv('VITE_API_BASE_URL', '')
    expect(aiURL('/api/analyze-code')).toBe('/api/analyze-code')
  })
  it('keeps requests usable when session storage is unavailable', () => {
    vi.stubGlobal('sessionStorage', { getItem() { throw new Error('blocked') } })
    expect(hostedAIKey()).toBe('')
    expect(aiHeaders().Authorization).toBeUndefined()
  })
})
