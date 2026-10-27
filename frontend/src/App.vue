<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useTheme } from './composables/useTheme'
import { useProgress } from './composables/useProgress'
import { usePatterns } from './composables/usePatterns'

const { theme, toggleTheme } = useTheme()
const { totalSolved } = useProgress()
const { meta, error: catalogError, retry: retryCatalog } = usePatterns()
const route = useRoute()
const headerNav = ref<HTMLElement | null>(null)
function revealCurrentLink() {
  if (!window.matchMedia('(max-width: 1439px)').matches || !headerNav.value) return
  const path=route.path
  const target=headerNav.value.querySelector<HTMLElement>(path.startsWith('/hld/') || path === '/system-design/hld' ? '.hld-direct-link' : 'a.active')
  if(target)headerNav.value.scrollLeft=Math.max(0,target.offsetLeft-headerNav.value.offsetLeft-12)
}
watch(()=>route.path,async()=>{await nextTick();revealCurrentLink()},{immediate:true})
onMounted(()=>window.addEventListener('resize',revealCurrentLink))
onUnmounted(()=>window.removeEventListener('resize',revealCurrentLink))



</script>

<template>
  <div class="app-layout">
    <!-- ═══ Header ═══ -->
    <header class="app-header">
      <div class="container header-inner">
        <router-link to="/" class="logo-link">
          <div class="logo">
            <span class="logo-bracket">{</span>
            <span class="logo-text">DSA</span>
            <span class="logo-dot">.</span>
            <span class="logo-accent">lab</span>
            <span class="logo-bracket">}</span>
          </div>
          <span class="logo-sub terminal-prompt">pattern_mastery</span>
        </router-link>

        <nav ref="headerNav" class="header-nav" aria-label="Main navigation">
          <router-link to="/" class="nav-link" active-class="active">
            <span class="nav-icon">◈</span> Dashboard
          </router-link>
          <router-link to="/problems" class="nav-link" active-class="active">
            <span class="nav-icon">▤</span> Problems
          </router-link>
          <router-link to="/custom" class="nav-link" active-class="active">
            <span class="nav-icon">⚡</span> Custom
          </router-link>
          <router-link to="/review" class="nav-link" active-class="active">
            <span class="nav-icon">↻</span> Review
          </router-link>
          <router-link to="/mock-interview" class="nav-link" active-class="active">
            <span class="nav-icon">⧗</span> Interview
          </router-link>
          <router-link to="/system-design/lld" class="nav-link" :class="{ active: route.path.startsWith('/lld/') || route.path.startsWith('/system-design/lld') }">LLD</router-link>
          <router-link to="/system-design/hld" class="nav-link hld-direct-link" :class="{ active: route.path.startsWith('/hld/') || route.path.startsWith('/system-design/hld') }">HLD</router-link>
          <router-link to="/ai" class="nav-link" :class="{ active: route.path === '/ai' || route.path.startsWith('/ai/') }" active-class="active">AI Learnings</router-link>
          <router-link to="/software" class="nav-link" :class="{ active: route.path.startsWith('/software') }">Software Learnings</router-link>
          <router-link to="/quiz" class="nav-link" active-class="active">
            <span class="nav-icon">?</span> Quiz
          </router-link>
        </nav>

        <div class="header-right">
          <!-- Teleport target for page-specific header badges (like Problem difficulty) -->
          <div id="header-extra"></div>

          <div class="stat-chip">
            <span class="stat-value">{{ totalSolved }}</span>
            <span class="stat-label">/{{ meta.total_problems }}</span>
          </div>
          <router-link to="/settings" class="btn btn-ghost theme-toggle" title="Settings">
            ⚙
          </router-link>
          <button class="btn btn-ghost theme-toggle" @click="toggleTheme" :title="`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`">
            {{ theme === 'dark' ? '☀' : '◑' }}
          </button>
        </div>
      </div>
    </header>

    <!-- ═══ Main Content ═══ -->
    <main class="app-main">
      <div v-if="catalogError" class="container catalog-load-error" role="alert"><p>The DSA catalog could not load. Check your connection, then retry.</p><button class="btn" @click="retryCatalog">Retry DSA catalog</button></div>
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" :key="String(route.name)" />
        </transition>
      </router-view>
    </main>

    <!-- ═══ Footer ═══ -->
    <footer class="app-footer">
      <div class="container footer-inner">
        <span class="terminal-prompt">system.status = "ready"</span>
        <span class="footer-meta">{{ meta.total_patterns }} patterns · {{ meta.total_problems }} problems</span>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.catalog-load-error { padding:20px; margin-bottom:20px; border:1px solid var(--accent-red); border-radius:8px; }
.app-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* ── Header ──────────────────────────────────── */
.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-subtle);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.header-inner {
  display: flex;
  align-items: center;
  gap: 20px;
  min-height: 64px;
  height: auto;
  max-width: 1600px;
}

.logo-link {
  display: flex;
  align-items: baseline;
  flex: 0 0 auto;
  white-space: nowrap;
  gap: var(--space-sm);
  text-decoration: none;
}

.logo {
  font-family: var(--font-mono);
  font-size: var(--text-lg);
  font-weight: 700;
  letter-spacing: -0.02em;
}

.logo-bracket {
  color: var(--text-muted);
}

.logo-text {
  color: var(--text-primary);
}

.logo-dot {
  color: var(--accent-cyan);
}

.logo-accent {
  color: var(--accent-cyan);
}

.logo-sub {
  font-size: var(--text-xs);
  display: none;
}

.header-nav {
  display: flex;
  gap: 2px;
  margin-left: auto;
  min-width: 0;
  align-items: center;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  min-height: 40px;
  flex: 0 0 auto;
  white-space: nowrap;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.nav-link:hover {
  color: var(--text-primary);
  background: var(--bg-card);
}

.nav-link.active {
  color: var(--accent-cyan);
  background: var(--bg-card);
}

.nav-icon {
  font-size: 11px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex: 0 0 auto;
}

.stat-chip {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
}

.stat-value {
  color: var(--accent-green);
  font-weight: 700;
}

.stat-label {
  color: var(--text-muted);
}

.theme-toggle {
  font-size: var(--text-lg);
  padding: 4px 8px;
}

/* ── Main ────────────────────────────────────── */
.app-main {
  flex: 1;
  padding: var(--space-xl) 0;
}

/* ── Footer ──────────────────────────────────── */
.app-footer {
  border-top: 1px solid var(--border-subtle);
  padding: var(--space-md) 0;
}

.footer-inner {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.footer-meta {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
}

/* ── Page Transition ─────────────────────────── */
.page-enter-active,
.page-leave-active {
  transition: opacity 0.2s var(--ease-out), transform 0.2s var(--ease-out);
}

.page-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* ── Responsive ──────────────────────────────── */
@media (max-width: 1439px) {
  .header-inner { display: grid; grid-template-columns: minmax(0, 1fr) auto; height: auto; padding-top: 10px; padding-bottom: 6px; gap: 8px; }
  .header-nav { grid-column: 1 / -1; grid-row: 2; margin-left: 0; width: 100%; min-width: 0; overflow-x: auto; padding-bottom: 4px; }
  .nav-link { white-space: nowrap; flex-shrink: 0; }
  .header-right { grid-column: 2; grid-row: 1; }
}
@media (max-width: 768px) {
  .header-inner {
    gap: var(--space-md);
  }

  .logo-sub {
    display: none;
  }

  .nav-link { min-height:44px; }

  .nav-link span:not(.nav-icon) {
    display: none;
  }
}
</style>
