<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { useTheme } from '../composables/useTheme'
const { theme } = useTheme()
const props = defineProps<{ content: string }>()
const root = ref<HTMLElement | null>(null)
const diagramError = ref(false)
const html = computed(() => DOMPurify.sanitize(marked.parse(props.content, { async: false }) as string))
let generation = 0
watch([html, theme], async () => {
  const current = ++generation
  diagramError.value = false
  await nextTick()
  if (root.value) root.value.innerHTML = html.value
  const blocks = Array.from(root.value?.querySelectorAll('code.language-mermaid') ?? [])
  if (!blocks.length) return
  try {
    const { default: mermaid } = await import('mermaid')
    mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', htmlLabels: false, flowchart: { htmlLabels: false }, theme: document.documentElement.dataset.theme === 'light' ? 'default' : 'dark' })
    for (const [i, block] of blocks.entries()) {
      const id = `hld-diagram-${crypto.randomUUID().replace(/-/g, '')}-${i}`
      try {
        const result = await mermaid.render(id, block.textContent ?? '')
        if (current !== generation) return
        if (block.parentElement) block.parentElement.innerHTML = DOMPurify.sanitize(result.svg, { USE_PROFILES: { svg: true } })
      } catch {
        document.getElementById(`d${id}`)?.remove()
        if (current === generation) diagramError.value = true
      }
    }
  } catch { if (current === generation) diagramError.value = true }

}, { immediate: true, flush: 'post' })
</script>

<template><div ref="root" class="hld-markdown" v-html="html"></div><p v-if="diagramError" class="hld-muted" role="status">Diagram preview could not render. Your readable source is kept above; check its syntax and try again.</p></template>

<style scoped>
.hld-markdown { color: var(--text-primary); line-height: 1.8; overflow-wrap: anywhere; }
.hld-markdown :deep(p), .hld-markdown :deep(ul), .hld-markdown :deep(ol) { margin-bottom: 16px; }
.hld-markdown :deep(h1), .hld-markdown :deep(h2), .hld-markdown :deep(h3) { margin: 22px 0 12px; line-height: 1.3; }
.hld-markdown :deep(ul), .hld-markdown :deep(ol) { padding-left: 24px; }
.hld-markdown :deep(li) { margin-bottom: 6px; }
.hld-markdown :deep(pre) { overflow-x: auto; background: var(--bg-code); border: 1px solid var(--border-default); padding: 16px; border-radius: 10px; white-space: pre; }
.hld-markdown :deep(code) { font-family: var(--font-mono); font-size: .88em; }
.hld-markdown :deep(a) { color: var(--accent-cyan); text-decoration: underline; }
.hld-markdown :deep(svg) { width: 100%; max-height: 480px; }
.hld-markdown :deep(blockquote) { border-left: 3px solid var(--accent-cyan); padding-left: 16px; }
</style>
