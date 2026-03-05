/* TypeScript interfaces for the DSA Pattern Learning Platform */

export interface Pattern {
  pattern_id: string
  name: string
  explanation: string
  mental_model: string
  template_code_python: string
  template_code_javascript: string
  template_code_java: string
  trigger_phrases: string[]
  when_to_use: string[]
  common_mistakes: string[]
  time_complexity: string
  space_complexity: string
  related_patterns: string[]
  sample_walkthrough: {
    problem: string
    problem_number: number
    approach: string
  }
  problem_count: number
  problem_slugs: string[]
}

export interface Problem {
  number: number | null
  title: string
  slug: string
  leetcode_url: string
  // Raw LeetCode prompt HTML from the pipeline source.
  // Example: "<p>Given an array of integers...</p>"
  description_html?: string
  // Plain-text prompt derived from description_html (tags removed).
  // Example: "Given an array of integers nums and an integer target..."
  description_text?: string
  difficulty: 'Easy' | 'Medium' | 'Hard' | null
  acceptance_rate: number | null
  topic_tags: string[]
  pattern_id: string
  pattern_name: string
  in_neetcode: boolean
  in_striver: boolean
  in_both: boolean
  score: number
  pattern_hint: string
  key_insight: string
  template_deviation: string
  common_mistake: string
  time_complexity: string
  space_complexity: string
}

export interface Progress {
  solved: Record<string, {
    date: string
    confidence: 1 | 2 | 3
  }>
  notes: Record<string, string>
  reflections: Record<string, {
    pattern: string
    signal: string
    deviation: string
  }>
}

export interface Database {
  patterns: Pattern[]
  problems: Record<string, Problem>
  pattern_order: string[]
  meta: {
    total_problems: number
    total_patterns: number
    difficulty_distribution: Record<string, number>
  }
}

export interface MockInterviewConfig {
  // Session shape selected in MockInterviewView setup panel and locked into
  // MockInterviewSession at startSession().
  totalQuestions: number
  totalTimeMinutes: number
  language: 'java'
  allowPause: boolean
}

export interface MockInterviewChatMessage {
  role: 'user' | 'assistant'
  content: string
  ts: string
}

export interface InterviewProblemState {
  // Runtime state for one problem inside a mock interview session.
  // Stored under MockInterviewSession.problems[slug].
  slug: string
  startedAt: string | null
  submittedAt: string | null
  code: string
  thoughts: string[]
  chat: MockInterviewChatMessage[]
  hintCount: number
}

export interface MockInterviewProblemResult {
  // Deterministic heuristic scoring output per problem.
  // May be overlaid by AI debrief values while keeping same shape.
  score: number
  rubric: {
    problemUnderstanding: number
    approachQuality: number
    correctnessConfidence: number
    complexityReasoning: number
    communicationQuality: number
  }
  reasoning: string[]
}

export interface MockInterviewResult {
  // Final report shown in MockInterviewView report pane.
  // Built in two phases: deterministic first, optional AI overlay second.
  totalScore: number
  perProblem: Record<string, MockInterviewProblemResult>
  strengths: string[]
  weaknesses: string[]
  nextSteps: string[]
  recommendedProblems: string[]
}

export interface MockInterviewSession {
  // Persisted interview session model used by useMockInterview composable.
  // Backward-compatible edits are preferred since this lives in localStorage.
  id: string
  status: 'active' | 'completed' | 'abandoned'
  createdAt: string
  config: MockInterviewConfig
  questionSlugs: string[]
  currentIndex: number
  timeRemainingSec: number
  lastTickAt: string
  paused: boolean
  problems: Record<string, InterviewProblemState>
  result?: MockInterviewResult
}

export interface MockInterviewFeatureFlags {
  // Runtime switches for interview behavior.
  // aiEnabled currently gates backend chat/debrief calls.
  aiEnabled: boolean
  ragEnabled: boolean
}
