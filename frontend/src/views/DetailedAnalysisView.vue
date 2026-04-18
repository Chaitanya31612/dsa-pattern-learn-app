<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useMockInterview } from '../composables/useMockInterview'
import CodeHighlight from '../components/CodeHighlight.vue'
import AIChatPanel from '../components/AIChatPanel.vue'
import { usePatterns } from '../composables/usePatterns'
import { marked } from 'marked'

const route = useRoute()
const slug = computed(() => typeof route.params.slug === 'string' ? route.params.slug : '')

const { activeSession } = useMockInterview()
const problemState = computed(() => {
  if (!slug.value || !activeSession.value) return null
  return activeSession.value.problems[slug.value] ?? null
})

const { problems } = usePatterns()
const globalProblem = computed(() => problems.value[slug.value])

const problemChatChips = computed(() => {
  return [
    'Can you explain the space complexity more?',
    'What are other ways to optimize this?',
    'How do I implement your suggested improvements?',
  ]
})

const isAnalyzing = ref(true)
const analysisResult = ref<{
  timeComplexity: string
  spaceComplexity: string
  improvements: string[]
  strengths: string[]
  interview_walkthrough?: string
} | null>(null)
const errorMsg = ref('')

const activeStep = ref(0)
const steps = [
  { id: 'complexity', title: 'Execution Profile', icon: '⚡' },
  { id: 'strengths', title: 'What Went Well', icon: '✨' },
  { id: 'improvements', title: 'Areas for Growth', icon: '🎯' },
  { id: 'walkthrough', title: 'Ideal Walkthrough', icon: '🎬' }
]

const parseComplexity = (text: string) => {
  if (!text) return { bigO: 'O(?)', desc: 'No data provided.' }
  const match = text.match(/^(O\([^)]+\))(.*)/i)
  if (match) {
    let desc = match[2]?.trim() || ''
    if (desc.startsWith(',')) desc = desc.slice(1).trim()
    if (desc.startsWith('-')) desc = desc.slice(1).trim()
    if (desc.toLowerCase().startsWith('because')) desc = desc.substring(7).trim()
    if (desc.length > 0) desc = desc.charAt(0).toUpperCase() + desc.slice(1)
    return { bigO: match[1], desc: desc || 'Determined by loop and recursion depths.' }
  }
  return { bigO: 'O(•)', desc: text }
}

const timeInfo = computed(() => parseComplexity(analysisResult.value?.timeComplexity || ''))
const spaceInfo = computed(() => parseComplexity(analysisResult.value?.spaceComplexity || ''))

async function fetchAnalysis() {
  if (!problemState.value) {
    errorMsg.value = 'No session data found for this problem.'
    isAnalyzing.value = false
    return
  }

  isAnalyzing.value = true
  try {
    const response = await fetch('/api/analyze-code', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        problem_slug: slug.value,
        code: problemState.value.code,
        notes: problemState.value.thoughts,
        chat: problemState.value.chat,
      }),
    }).catch(() => null)

    if (!response || !response.ok) {
      analysisResult.value = {
        timeComplexity: "O(1) - Demo Mode",
        spaceComplexity: "O(1) - Demo Mode",
        improvements: ["This is a frontend-only deployment for demonstration purposes.", "To get actual AI-driven code analysis and recommendations, please run the project locally with the backend server and API keys setup.", "Backend components are disabled in this preview."],
        strengths: ["You've successfully run the frontend interface!", "The UI components are rendering perfectly."],
        interview_walkthrough: "This is a **frontend-only deployment** for demonstration purposes.\n\nTo see the real power of this application and get a detailed AI-driven interview walkthrough:\n1. Clone the repository\n2. Set up the Python backend\n3. Provide your API keys in `.env`\n4. Run both frontend and backend locally.\n\nEnjoy exploring the UI!"
      }
      return
    }
    
    const data = await response.json()
    analysisResult.value = data
  } catch (err: any) {
    errorMsg.value = err.message || 'Failed to fetch analysis.'
  } finally {
    isAnalyzing.value = false
  }
}

function nextStep() {
  if (activeStep.value < steps.length - 1) activeStep.value++
}

function prevStep() {
  if (activeStep.value > 0) activeStep.value--
}

const formattedWalkthrough = computed(() => {
  if (!analysisResult.value?.interview_walkthrough) return ''
  // Replace the literal string "\n" with actual double newlines for paragraph spacing
  const cleanedText = analysisResult.value.interview_walkthrough.replace(/\\n/g, '\n\n')
  return marked.parse(cleanedText, { async: false, breaks: true, gfm: true })
})

onMounted(() => {
  fetchAnalysis()
})
</script>

<template>
  <div class="container container-large detailed-analysis">
    <header class="da-header animate-in">
      <router-link to="/mock-interview" class="back-link">
        <span>←</span> Back to Interview
      </router-link>
      <div class="da-title-wrap">
        <h1 class="da-title">Feedback Report</h1>
        <div class="da-badge mono">target_slug = "{{ slug }}"</div>
      </div>
    </header>

    <div v-if="!problemState" class="card error-card">
      <p>Could not find interview session data for this problem.</p>
    </div>
    
    <div v-else class="da-layout animate-in stagger-1">
      <aside class="da-sidebar">
        <div class="source-card lux-card">
          <div class="lux-card-header">
            <div class="mac-dots"><span></span><span></span><span></span></div>
            <span class="lux-label mono">submission.java</span>
            <span class="lux-tag">Read Only</span>
          </div>
          <div class="source-body custom-scroll">
            <CodeHighlight :code="problemState.code" language="java" />
          </div>
        </div>
        
        <div class="notes-card lux-card" v-if="problemState.thoughts?.length">
          <div class="lux-card-header blurred-header">
            <div class="mac-dots"><span></span><span></span><span></span></div>
            <span class="lux-label mono">candidate_notes.txt</span>
          </div>
          <div class="notes-body custom-scroll">
            <ul class="notes-list">
              <li v-for="(note, i) in problemState.thoughts" :key="i">{{ note }}</li>
            </ul>
          </div>
        </div>
      </aside>

      <main class="da-main">
        <div class="evaluation-view cyber-panel">
          
          <div v-if="isAnalyzing" class="eval-loading">
            <div class="scanning-grid"></div>
            <div class="scanning-beam"></div>
            <div class="eval-loading-inner">
              <div class="spinner"></div>
              <div class="eval-loading-text terminal-prompt">Interrogating logic structure...</div>
            </div>
          </div>
          
          <div v-else-if="errorMsg" class="eval-error">
            <div class="error-content">
              <span class="error-icon">⚠</span>
              <p>{{ errorMsg }}</p>
              <button class="btn btn-primary mt-sm" @click="fetchAnalysis">Retry Connection</button>
            </div>
          </div>
          
          <div v-else-if="analysisResult" class="eval-carousel">
            <header class="carousel-header">
              <h2 class="carousel-title" v-if="steps[activeStep]">
                <div class="step-icon-glowing">{{ steps[activeStep]?.icon }}</div>
                <span>{{ steps[activeStep]?.title }}</span>
              </h2>
              <div class="step-indicator">
                <button 
                  v-for="(step, idx) in steps" 
                  :key="step.id" 
                  class="step-line"
                  :class="{ active: activeStep === idx, completed: activeStep > idx }"
                  @click="activeStep = idx"
                  :title="step.title"
                ></button>
              </div>
            </header>

            <div class="carousel-viewport custom-scroll">
              <Transition name="slide-fade" mode="out-in">
                
                <div v-if="activeStep === 0" class="slide-content showcase-content" key="slide-0">
                  <div class="complexity-wrapper">
                    <div class="comp-card time-card">
                      <div class="comp-bg-glow time-glow"></div>
                      <div class="comp-card-inner">
                        <span class="comp-metric-name"><i class="icon">⏱</i> Time</span>
                        <strong class="comp-metric-big mono">{{ timeInfo.bigO }}</strong>
                        <div class="comp-divider"></div>
                        <p class="comp-metric-desc">{{ timeInfo.desc }}</p>
                      </div>
                    </div>
                    
                    <div class="comp-card space-card">
                      <div class="comp-bg-glow space-glow"></div>
                      <div class="comp-card-inner">
                        <span class="comp-metric-name"><i class="icon">💾</i> Space</span>
                        <strong class="comp-metric-big mono">{{ spaceInfo.bigO }}</strong>
                        <div class="comp-divider"></div>
                        <p class="comp-metric-desc">{{ spaceInfo.desc }}</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div v-else-if="activeStep === 1" class="slide-content" key="slide-1">
                  <div v-if="!analysisResult.strengths?.length" class="empty-state">
                    <span class="terminal-prompt">No distinct strengths identified.</span>
                  </div>
                  <ul v-else class="feature-list success-list">
                    <li v-for="(item, i) in analysisResult.strengths" :key="`str-${i}`" class="feature-item">
                      <div class="feature-icon check-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                      </div>
                      <div class="feature-text">{{ item }}</div>
                    </li>
                  </ul>
                </div>

                <div v-else-if="activeStep === 2" class="slide-content" key="slide-2">
                  <div v-if="!analysisResult.improvements?.length" class="empty-state">
                    <span class="terminal-prompt">Code is rock solid. Zero improvements suggested.</span>
                  </div>
                  <ul v-else class="feature-list warning-list">
                    <li v-for="(item, i) in analysisResult.improvements" :key="`imp-${i}`" class="feature-item">
                      <div class="feature-icon alert-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                      </div>
                      <div class="feature-text">{{ item }}</div>
                    </li>
                  </ul>
                </div>

                <div v-else-if="activeStep === 3" class="slide-content walk-content" key="slide-3">
                  <div class="walkthrough-timeline">
                    <p class="walkthrough-intro"><span class="highlight-text">Perfect Interview Loop:</span> The ideal narrative timeline to secure the offer.</p>
                    <div class="timeline-nodes">
                      <div class="timeline-node">
                        <div class="node-bullet"></div>
                        <div class="node-content markdown-body" v-html="formattedWalkthrough"></div>
                      </div>
                    </div>
                  </div>
                </div>
              </Transition>
            </div>

            <footer class="carousel-footer">
              <button class="nav-btn prev-btn" :class="{ disabled: activeStep === 0 }" @click="prevStep">
                <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
                Back
              </button>
              
              <div class="progress-capsule mono">
                <span class="current">{{ activeStep + 1 }}</span>
                <span class="separator">/</span>
                <span class="total">{{ steps.length }}</span>
              </div>
              
              <button class="nav-btn next-btn" :class="{ disabled: activeStep === steps.length - 1 }" @click="nextStep">
                Next
                <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
              </button>
            </footer>
          </div>
        </div>
      </main>
    </div>
    
    <AIChatPanel
      :key="`analysis-ai-${slug}`"
      context-type="problem"
      :context-id="slug"
      :context-label="globalProblem?.title || slug"
      :quick-chips="problemChatChips"
    />
  </div>
</template>

<style scoped>
/* ── Layout & Typography ── */
.detailed-analysis {
  max-width: 1536px;
  display: flex;
  flex-direction: column;
  height: 100vh;
  min-height: 900px;
  padding: var(--space-xl) var(--space-xl) var(--space-3xl);
  overflow-y: auto;
  overflow-x: hidden;
  background: var(--bg-default);
}

.da-header {
  flex-shrink: 0;
  margin-bottom: var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-weight: 700;
  transition: all var(--transition-fast);
}

.back-link:hover {
  color: var(--accent-cyan);
  transform: translateX(-4px);
}

.da-title-wrap {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.da-title {
  font-size: var(--text-3xl);
  font-weight: 900;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, #fff, var(--text-secondary));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.da-badge {
  background: rgba(56, 189, 248, 0.1);
  color: var(--accent-cyan);
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  border: 1px solid rgba(56, 189, 248, 0.3);
  box-shadow: 0 0 10px rgba(56,189,248,0.1);
}

.da-layout {
  display: grid;
  grid-template-columns: minmax(400px, 1.1fr) minmax(500px, 1.4fr);
  gap: var(--space-2xl);
  flex: 1;
  min-height: 0;
}

@media (max-width: 1024px) {
  .da-layout {
    grid-template-columns: 1fr;
    overflow-y: auto;
  }
  .detailed-analysis {
    height: auto;
    overflow: visible;
  }
}

/* ── Left Column: Cyber Cards ── */
.da-sidebar {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
  min-height: 0;
}

.lux-card {
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 40px rgba(0,0,0,0.3), inset 0 1px 1px rgba(255,255,255,0.05);
}

.source-card { flex: 2; min-height: 0; }
.notes-card { flex: 1; min-height: 200px; }

.lux-card-header {
  background: rgba(0,0,0,0.2);
  border-bottom: 1px solid var(--border-subtle);
  padding: 12px var(--space-md);
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.mac-dots {
  display: flex;
  gap: 6px;
  margin-right: 8px;
}

.mac-dots span {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #4a4a4a;
}
.mac-dots span:nth-child(1) { background: #ff5f56; }
.mac-dots span:nth-child(2) { background: #ffbd2e; }
.mac-dots span:nth-child(3) { background: #27c93f; }

.lux-label {
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-weight: 600;
  flex: 1;
}

.lux-tag {
  font-size: 9px;
  text-transform: uppercase;
  color: var(--accent-purple);
  background: rgba(168, 85, 247, 0.1);
  padding: 2px 8px;
  border-radius: 99px;
  border: 1px solid rgba(168, 85, 247, 0.2);
  letter-spacing: 0.1em;
}

.source-body {
  flex: 1;
  background: #0d1117;
  padding: 0;
}

.notes-body {
  flex: 1;
  padding: var(--space-md);
  background: rgba(0,0,0,0.1);
}

.notes-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  color: var(--text-primary);
  font-size: var(--text-sm);
  line-height: 1.6;
}

.notes-list li {
  position: relative;
  padding-left: 20px;
  border-left: 2px solid var(--border-subtle);
  padding-bottom: var(--space-sm);
}

.notes-list li::before {
  content: '';
  position: absolute;
  left: -5px;
  top: 6px;
  width: 8px;
  height: 8px;
  background: var(--text-muted);
  border-radius: 50%;
}

/* ── Custom Scrollbar ── */
.custom-scroll {
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--border-default) transparent;
}
.custom-scroll::-webkit-scrollbar { width: 6px; }
.custom-scroll::-webkit-scrollbar-track { background: transparent; }
.custom-scroll::-webkit-scrollbar-thumb { background: var(--border-default); border-radius: 10px; }

/* ── Right Column: AI Panel ── */
.da-main {
  display: flex;
  flex-direction: column;
  min-height: 0;
  position: relative;
}

.cyber-panel {
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: var(--radius-xl);
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 30px 60px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.1);
  position: relative;
}

/* ── Carousel Header ── */
.eval-carousel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.carousel-header {
  padding: var(--space-xl) var(--space-2xl) var(--space-lg);
  border-bottom: 1px solid rgba(255,255,255,0.05);
  background: linear-gradient(180deg, rgba(255,255,255,0.03) 0%, transparent 100%);
}

.carousel-title {
  font-size: var(--text-2xl);
  font-weight: 800;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
}

.step-icon-glowing {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  font-size: var(--text-xl);
  box-shadow: 0 4px 12px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.1);
  position: relative;
}

.step-indicator {
  display: flex;
  gap: 8px;
  width: 100%;
}

.step-line {
  flex: 1;
  height: 4px;
  background: var(--bg-input);
  border-radius: 2px;
  border: none;
  cursor: pointer;
  transition: all var(--transition-base);
  position: relative;
  overflow: hidden;
}

.step-line::after {
  content: '';
  position: absolute;
  top: 0; left: 0; bottom: 0;
  width: 0%;
  background: var(--accent-cyan);
  transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.step-line.completed::after { width: 100%; }
.step-line.active::after { width: 50%; background: var(--text-primary); animation: pulse-width 2s infinite alternate; }
.step-line:hover { background: var(--border-default); transform: scaleY(1.5); }

@keyframes pulse-width {
  0% { width: 30%; }
  100% { width: 70%; }
}

/* ── Carousel Viewport ── */
.carousel-viewport {
  flex: 1;
  position: relative;
  padding: var(--space-2xl);
  overflow-y: auto;
}

.slide-content {
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
}

/* Transitions */
.slide-fade-enter-active, .slide-fade-leave-active {
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
.slide-fade-enter-from { opacity: 0; transform: translateX(30px) scale(0.98); }
.slide-fade-leave-to { opacity: 0; transform: translateX(-30px) scale(0.98); }

/* ── Slide 0: Complexity ── */
.complexity-wrapper {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-xl);
}

.comp-card {
  position: relative;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  padding: var(--space-2xl);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0,0,0,0.2);
  transition: transform var(--transition-slow);
}

.comp-card:hover { transform: translateY(-4px); }

.comp-bg-glow {
  position: absolute;
  top: -50px;
  right: -50px;
  width: 150px;
  height: 150px;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.15;
  z-index: 0;
}

.time-glow { background: var(--accent-orange); }
.space-glow { background: var(--accent-cyan); }

.comp-card-inner {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.comp-metric-name {
  color: var(--text-secondary);
  font-size: var(--text-sm);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: var(--space-lg);
}

.comp-metric-big {
  font-size: 5rem;
  line-height: 1.1;
  font-weight: 800;
  color: var(--text-primary);
  margin-bottom: var(--space-xl);
  text-shadow: 0 4px 20px rgba(255,255,255,0.1);
  letter-spacing: -3px;
}

.comp-divider {
  height: 1px;
  background: linear-gradient(90deg, var(--border-subtle) 0%, transparent 100%);
  margin-bottom: var(--space-md);
}

.comp-metric-desc {
  color: var(--text-secondary);
  font-size: var(--text-base);
  line-height: 1.6;
}

/* ── Slide 1 & 2: Feature Lists ── */
.feature-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.feature-item {
  display: flex;
  gap: var(--space-lg);
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.05);
  padding: var(--space-lg);
  border-radius: var(--radius-lg);
  align-items: flex-start;
  transition: all var(--transition-base);
}

.feature-item:hover {
  background: rgba(255,255,255,0.04);
  transform: translateX(4px);
}

.feature-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  padding: 6px;
}

.check-icon {
  background: rgba(34, 197, 94, 0.15);
  color: var(--accent-green);
  box-shadow: 0 0 15px rgba(34, 197, 94, 0.2);
}

.alert-icon {
  background: rgba(244, 63, 94, 0.15);
  color: var(--accent-red);
  box-shadow: 0 0 15px rgba(244, 63, 94, 0.2);
}

.feature-text {
  color: var(--text-primary);
  font-size: var(--text-lg);
  line-height: 1.5;
  font-weight: 500;
}

.empty-state {
  text-align: center;
  padding: var(--space-3xl) var(--space-xl);
  color: var(--text-muted);
}

/* ── Slide 3: Walkthrough ── */
.walkthrough-timeline {
  display: flex;
  flex-direction: column;
  gap: var(--space-xl);
  position: relative;
}

.walkthrough-intro {
  font-size: var(--text-lg);
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: var(--space-lg);
}

.highlight-text {
  color: var(--accent-purple);
  font-weight: 700;
}

.timeline-nodes {
  display: flex;
  flex-direction: column;
  gap: var(--space-xl);
  padding-left: 20px;
  position: relative;
}

.timeline-nodes::before {
  content: '';
  position: absolute;
  left: 3px;
  top: 10px;
  bottom: 0;
  width: 2px;
  background: linear-gradient(180deg, var(--accent-cyan) 0%, rgba(56, 189, 248, 0) 100%);
}

.timeline-node {
  position: relative;
  display: flex;
  gap: var(--space-lg);
}

.node-bullet {
  width: 10px;
  height: 10px;
  background: var(--bg-card);
  border: 2px solid var(--accent-cyan);
  border-radius: 50%;
  position: absolute;
  left: -21px;
  top: 6px;
  z-index: 2;
  box-shadow: 0 0 10px var(--accent-cyan);
}

.node-content p {
  color: var(--text-primary);
  font-size: var(--text-lg);
  line-height: 1.7;
  background: rgba(255,255,255,0.02);
  padding: var(--space-md) var(--space-lg);
  border-radius: var(--radius-sm);
  border: 1px solid rgba(255,255,255,0.03);
}

/* ── Carousel Footer ── */
.carousel-footer {
  padding: var(--space-lg) var(--space-2xl);
  border-top: 1px solid rgba(255,255,255,0.05);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(0,0,0,0.2);
}

.nav-btn {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
  padding: 12px 24px;
  border-radius: var(--radius-full);
  font-weight: 600;
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all var(--transition-base);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.nav-btn:hover:not(.disabled) {
  color: var(--bg-default);
  background: var(--text-primary);
  border-color: var(--text-primary);
}

.nav-btn.next-btn:hover:not(.disabled) {
  background: var(--accent-cyan);
  color: #000;
  border-color: var(--accent-cyan);
  box-shadow: 0 0 20px rgba(56, 189, 248, 0.4);
}

.nav-btn.disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.progress-capsule {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  background: rgba(255,255,255,0.05);
  padding: 8px 20px;
  border-radius: var(--radius-full);
  font-size: var(--text-sm);
}

.progress-capsule .current { color: var(--text-primary); font-weight: 700; }
.progress-capsule .separator { color: var(--text-muted); }
.progress-capsule .total { color: var(--text-secondary); }

/* ── Loading and Error States ── */
.eval-loading, .eval-error {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.scanning-grid {
  position: absolute;
  inset: 0;
  background-size: 40px 40px;
  background-image: 
    linear-gradient(to right, rgba(255,255,255,0.02) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(255,255,255,0.02) 1px, transparent 1px);
}

.eval-loading-inner {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-lg);
  background: rgba(0,0,0,0.4);
  padding: var(--space-2xl);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(56, 189, 248, 0.2);
  backdrop-filter: blur(10px);
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(56, 189, 248, 0.1);
  border-top-color: var(--accent-cyan);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.error-content {
  text-align: center;
  color: var(--accent-red);
  background: rgba(244, 63, 94, 0.05);
  padding: var(--space-2xl);
  border: 1px solid rgba(244, 63, 94, 0.2);
  border-radius: var(--radius-lg);
}

.error-icon {
  font-size: 3rem;
  display: block;
  margin-bottom: var(--space-md);
}

.mt-sm { margin-top: var(--space-md); }
</style>
