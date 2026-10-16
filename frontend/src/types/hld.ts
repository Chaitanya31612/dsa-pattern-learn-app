export const HLD_PHASES = [
  { id: 'contract', title: 'Contract', prompt: 'Who uses it? What must it do? What is out of scope? State speed, freshness, and the rule that must never break.', time: '0–6 min' },
  { id: 'size', title: 'Size', prompt: 'How many requests each second? What is the peak? How much data, and for how long? Which number changes your design?' , time: '6–10 min' },
  { id: 'model', title: 'Model', prompt: 'What can clients ask? What data do you store and look up? Which store owns the answer? Which changes must commit together?', time: '10–16 min' },
  { id: 'flow', title: 'Flow', prompt: 'Follow one write and one read through the boxes. When is it safe to reply success? What runs in the background?', time: '16–26 min' },
  { id: 'stress', title: 'Stress', prompt: 'Try two users at once, a crash, a retry, one popular item, or old data. Show exactly what happens in the hardest case.', time: '26–37 min' },
  { id: 'operate', title: 'Operate', prompt: 'How will you notice trouble, recover, and check access? What costs most? How will you release and undo a change?', time: '37–42 min' },
  { id: 'explain', title: 'Explain', prompt: 'Why this choice? What other option could work? Name a downside, the next limit, and what you would test.', time: '42–45 min' },
] as const
export type HLDPhase = typeof HLD_PHASES[number]['id']
export const HLD_DIMENSIONS = ['requirements', 'scale', 'data_interfaces', 'flows', 'correctness', 'failure_operations', 'tradeoffs', 'communication'] as const
export type HLDDimension = typeof HLD_DIMENSIONS[number]
export const DIMENSION_LABELS: Record<HLDDimension, string> = {
  requirements: 'Requirements', scale: 'Scale', data_interfaces: 'Data & interfaces', flows: 'End-to-end flows',
  correctness: 'Correctness', failure_operations: 'Failure & operations', tradeoffs: 'Trade-offs & evolution', communication: 'Communication & adaptation',
}
export interface HLDSection { id: string; title: string; content: string; quick?: { title: string; explanation: string; example: string; tip: string } }
export interface HLDQuestion { id: string; prompt: string; options: string[]; correctIndex: number; explanation: string }
export interface HLDExercise { id: string; title: string; kind: 'design' | 'transfer' | 'repair'; prompt: string; solution: string; minutes: number }
export interface HLDModule {
  id: string; number: number; track: 'volume-1' | 'volume-2'; chapter?: number; lab?: 'geo' | 'queue' | 'reservation' | 'retry' | null; title: string; hours: number; prerequisites: string; book: string; outcome: string
  sections: HLDSection[]; examples: HLDSection[]; exercises: HLDExercise[]; questions: HLDQuestion[]; recallPrompt: string
  visuals: { id: string; title: string; caption: string; placement: 'overview' | 'recap'; code: string }[]
}
export interface HLDCourse { schemaVersion: 1; contentVersion: string; title: string; tracks: { id: 'volume-1' | 'volume-2'; title: string; description: string }[]; modules: HLDModule[]; materials: Record<string, string> }
export interface HLDReview {
  scope?: 'design' | 'repair';
  source: 'ai' | 'self'; dimensions: { id: HLDDimension; score: number; evidence: string; feedback: string }[]
  summary: string; strengths: string[]; gaps: string[]; next_exercise: string; critical_issue: boolean; total: number; passed: boolean
}
export interface HLDDraft {
  phases: Record<HLDPhase, string>; diagram: string; assisted: boolean
  timer: { remaining: number; runningSince: number | null }
}
export interface HLDAttempt {
  id: string; exerciseId: string; createdAt: number; phases: Record<HLDPhase, string>; diagram: string
  assisted: boolean; review?: HLDReview
}
export interface HLDQuizAttempt { createdAt: number; choices: Record<string, number>; score: number; total: number }
export interface HLDModuleProgress {
  completedSections: string[]; notes: string; drafts: Record<string, HLDDraft>; attempts: HLDAttempt[]; quizAttempts: HLDQuizAttempt[]; quizDraft?: Record<string, number>
}
export interface HLDCard {
  id: string; moduleId: string; kind: 'recall' | 'quiz' | 'decision'; question: string; answer: string
  dueAt: number; step: number; lapses: number; lastReviewed: number | null; lastResponse: string; lastRating?: 'again' | 'hard' | 'good'
}
export interface HLDProgress { schemaVersion: 1; modules: Record<string, HLDModuleProgress>; cards: Record<string, HLDCard> }
