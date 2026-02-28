<script setup lang="ts">
import { useTheme } from './composables/useTheme'
import { useProgress } from './composables/useProgress'
import { usePatterns } from './composables/usePatterns'
import { useRouter } from 'vue-router'

const { theme, toggleTheme } = useTheme()
const { totalSolved } = useProgress()
const { meta } = usePatterns()
const router = useRouter()
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

        <nav class="header-nav">
          <router-link to="/" class="nav-link" active-class="active">
            <span class="nav-icon">◈</span> Dashboard
          </router-link>
          <router-link to="/problems" class="nav-link" active-class="active">
            <span class="nav-icon">▤</span> Problems
          </router-link>
          <router-link to="/review" class="nav-link" active-class="active">
            <span class="nav-icon">↻</span> Review
          </router-link>
          <router-link to="/quiz" class="nav-link" active-class="active">
            <span class="nav-icon">?</span> Quiz
          </router-link>
        </nav>

        <div class="header-right">
          <div class="stat-chip">
            <span class="stat-value">{{ totalSolved }}</span>
            <span class="stat-label">/{{ meta.total_problems }}</span>
          </div>
          <button class="btn btn-ghost theme-toggle" @click="toggleTheme" :title="`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`">
            {{ theme === 'dark' ? '☀' : '◑' }}
          </button>
        </div>
      </div>
    </header>

    <!-- ═══ Main Content ═══ -->
    <main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
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
  gap: var(--space-xl);
  height: 56px;
}

.logo-link {
  display: flex;
  align-items: baseline;
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
  opacity: 0.5;
}

.header-nav {
  display: flex;
  gap: 2px;
  margin-left: auto;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
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
@media (max-width: 768px) {
  .header-inner {
    gap: var(--space-md);
  }

  .logo-sub {
    display: none;
  }

  .nav-link span:not(.nav-icon) {
    display: none;
  }
}
</style>
