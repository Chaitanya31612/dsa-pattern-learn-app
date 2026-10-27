<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { spaceReadingParagraphs,readingTerms } from '../lib/reading'
import { useTheme } from '../composables/useTheme'
const { theme } = useTheme()
const props = defineProps<{ content: string }>()
const root = ref<HTMLElement | null>(null)
const diagramError = ref(false)
const terms = computed(()=>readingTerms(props.content))
const html = computed(() => DOMPurify.sanitize(marked.parse(props.content, { async: false }) as string))
let generation = 0
watch([html, theme], async () => {
  const current = ++generation
  diagramError.value = false
  await nextTick()
  if (root.value) { root.value.innerHTML = html.value; spaceReadingParagraphs(root.value) }
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

<template><div class="learning-reading"><aside v-if="terms.length" class="reading-terms" aria-label="Terms in plain words"><p>In plain words</p><dl><template v-for="[term,meaning] in terms" :key="term"><dt>{{ term }}</dt><dd>{{ meaning }}</dd></template></dl></aside><div ref="root" class="hld-markdown" v-html="html"></div><p v-if="diagramError" class="hld-muted" role="status">Diagram preview could not render. Your readable source is kept above; check its syntax and try again.</p></div></template>

<style scoped>
.hld-markdown { font-size:.98rem; color: var(--text-primary); line-height: 1.85; overflow-wrap: anywhere; }
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

<style scoped>
.reading-terms{margin:0 0 22px;padding:14px 18px;background:var(--bg-secondary);border-left:3px solid var(--accent-cyan);border-radius:0 8px 8px 0;max-width:68ch}.reading-terms>p{font-size:.75rem;text-transform:uppercase;letter-spacing:.06em;color:var(--accent-cyan);margin:0 0 10px}.reading-terms dl{margin:0;display:grid;grid-template-columns:fit-content(12em) 1fr;gap:8px 16px;font-size:.9rem;line-height:1.7}.reading-terms dt{font-weight:600;text-transform:capitalize}.reading-terms dd{margin:0;color:var(--text-secondary)}.hld-markdown :deep(p){max-width:68ch;margin:0 0 1.2em}.hld-markdown :deep(.reading-group){margin:0 0 26px}.hld-markdown :deep(.reading-beat){margin-bottom:12px}.hld-markdown :deep(li){margin:10px 0;max-width:72ch;line-height:1.8}.hld-markdown :deep(blockquote){padding:16px 20px;background:var(--bg-secondary);margin:22px 0;border-radius:0 8px 8px 0}.hld-markdown :deep(blockquote p:last-child){margin-bottom:0}.hld-markdown :deep(table){display:block;overflow:auto;max-width:100%;border-collapse:collapse;margin:24px 0}.hld-markdown :deep(th),.hld-markdown :deep(td){padding:12px 16px;border:1px solid var(--border-default);text-align:left}.hld-markdown :deep(pre){margin:22px 0;font-size:.9rem;line-height:1.7}.hld-markdown :deep(h2),.hld-markdown :deep(h3){max-width:60ch;margin-top:30px}@media(max-width:550px){.reading-terms dl{grid-template-columns:1fr;gap:4px}.reading-terms dd{margin-bottom:10px}.hld-markdown{font-size:.96rem}.hld-markdown :deep(blockquote){padding:14px}}
</style>
