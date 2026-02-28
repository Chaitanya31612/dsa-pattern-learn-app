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
