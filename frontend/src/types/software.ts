import type { HLDCard, HLDQuestion } from './hld'
export type SoftwareTrack = 'spring' | 'ruby' | 'git' | 'frontend' | 'ux' | 'cloud' | 'ops' | 'events'
export interface SoftwareLab {
  id: string; title: string; version: string; journalPath: string; guide: string
  files: { path: string; language: string; content: string }[]
}
export interface SoftwareModule {
  level: 'beginner' | 'intermediate'; sequence: number; tags: string[]
  useCase?: string; benefits?: string; drawbacks?: string; lab?: string | null
  id: string; track: SoftwareTrack; number: number; title: string; outcome: string; hours: number; cue: string; version: string; book: string; prerequisite: string | null; journalPath: string
  sections: { id: string; title: string; content: string }[]
  exercises: { id: string; title: string; kind: string; prompt: string; solution: string; minutes: number }[]
  questions: HLDQuestion[]
  visuals: { title: string; code: string; placement: string }[]
  trace: { title: string; detail: string }[]
  reading: { title: string; path: string; content: string }[]
  sources: { title: string; url: string }[]
  recallPrompt: string
}
export interface SoftwareCourse {
  schemaVersion: 1; contentVersion: string; title: string; guide: string; versions: string
  tracks: { id: SoftwareTrack; title: string; description: string; version: string; hours: number }[]
  labs: Record<string, SoftwareLab>
  modules: SoftwareModule[]
}
export const WORK_FIELDS = [
  { id: 'predict', title: 'Predict', prompt: 'What will happen? Follow a concrete input through the steps.' },
  { id: 'change', title: 'Change', prompt: 'Write your repair, code, diagram, or proposed steps.' },
  { id: 'verify', title: 'Verify', prompt: 'What did you run or inspect? Expected and actual result? If not run, say so.' },
  { id: 'explain', title: 'Explain', prompt: 'Why does it work? Give one failing case and a limitation.' },
] as const
export type WorkField = typeof WORK_FIELDS[number]['id']
export interface SoftwareDraft { phases: Record<WorkField, string>; diagram: string; assisted: boolean }
export interface SoftwareReport {
  source: 'ai' | 'self'; summary: string; next_exercise: string
  dimensions: { id: WorkField; score: number; evidence: string; feedback: string }[]
}
export interface SoftwareAttempt extends SoftwareDraft { id: string; exerciseId: string; createdAt: number; report?: SoftwareReport }
export interface SoftwareModuleProgress {
  completed: string[]; drafts: Record<string, SoftwareDraft>; attempts: SoftwareAttempt[]
  quizDraft: Record<string, number>; quizzes: { createdAt: number; choices: Record<string, number>; score: number; total: number }[]
  quizSubmitted: boolean; notes: string
}
export interface SoftwareProgress { schemaVersion: 1; modules: Record<string, SoftwareModuleProgress>; cards: Record<string, HLDCard> }
