<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import DOMPurify from 'dompurify'
import { useTheme } from '../composables/useTheme'
const { theme } = useTheme()
const props = defineProps<{ title: string; caption?: string; code: string }>()
const svg = ref('')
const problem = ref('')
const zoom = ref(1)
const naturalWidth = ref(0)
const dialog = ref<HTMLDialogElement | null>(null)
let generation = 0
async function render() {
  const version = ++generation
  const renderId = `hld-${crypto.randomUUID().replace(/-/g, '')}`
  try {
    const { default: mermaid } = await import('mermaid')
    const style = getComputedStyle(document.documentElement)
    mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', htmlLabels: false, theme: 'base', flowchart: { htmlLabels: false },
      themeVariables: { primaryColor: style.getPropertyValue('--bg-elevated').trim(), primaryTextColor: style.getPropertyValue('--text-primary').trim(),
        primaryBorderColor: style.getPropertyValue('--accent-cyan').trim(), lineColor: style.getPropertyValue('--text-secondary').trim(),
        secondaryColor: style.getPropertyValue('--bg-card').trim(), tertiaryColor: style.getPropertyValue('--bg-secondary').trim(),
        background: style.getPropertyValue('--bg-card').trim(), textColor: style.getPropertyValue('--text-primary').trim(), fontFamily: 'sans-serif' } })
    const result = await mermaid.render(renderId, props.code)
    if (version !== generation) return
    svg.value = DOMPurify.sanitize(result.svg, { USE_PROFILES: { svg: true } }); problem.value = ''
    const parsed = new DOMParser().parseFromString(svg.value, 'image/svg+xml')
    naturalWidth.value = Number(parsed.documentElement.getAttribute('viewBox')?.split(/\s+/)[2]) || 0
  } catch { document.getElementById(`d${renderId}`)?.remove(); if (version === generation) problem.value = 'Diagram could not render. The readable source is available below.' }
}
watch([() => props.code, theme], render, { immediate: true, flush: 'post' })
async function expand() { await nextTick(); dialog.value?.showModal() }
</script>
<template>
  <figure class="hld-diagram">
      <figcaption class="hld-row"><div><strong>{{ title }}</strong><p v-if="caption" class="hld-muted">{{ caption }}</p></div>
      <div class="hld-row"><button class="btn btn-ghost" :disabled="zoom <= .6" aria-label="Zoom diagram out" @click="zoom = Math.max(.6, zoom - .2)">−</button><span class="hld-muted">{{ Math.round(zoom * 100) }}%</span><button class="btn btn-ghost" :disabled="zoom >= 2.4" aria-label="Zoom diagram in" @click="zoom = Math.min(2.4, zoom + .2)">+</button><button class="btn" @click="expand">Expand diagram</button></div>
      </figcaption>
    <p v-if="problem" role="status">{{ problem }}</p><p v-else-if="!svg" role="status">Rendering diagram…</p>
    <p class="hld-muted">Zoom or expand to read the details. Wide diagrams can scroll sideways.</p>
    <div class="diagram-viewport"><div class="diagram-svg" :style="{ width: `${zoom * 100}%`, minWidth: `${zoom > 1 ? Math.max(260, naturalWidth * .8 * zoom) : 260}px`, maxWidth: `${Math.max(260, naturalWidth * 1.2) * zoom}px` }" role="img" :aria-label="title" v-html="svg"></div></div>
    <details><summary>Diagram source</summary><pre>{{ code }}</pre></details>
    <dialog ref="dialog" class="diagram-dialog" :aria-label="title"><div class="hld-row"><h2>{{ title }}</h2><button class="btn" @click="dialog?.close()">Close diagram</button></div><div class="diagram-svg" role="img" :aria-label="title" v-html="svg"></div></dialog>
  </figure>
</template>
<style scoped>
.hld-diagram { margin:20px 0; padding:18px; background:var(--bg-secondary); border:1px solid var(--border-default); border-radius:10px; }
.hld-diagram figcaption { display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap; }.hld-diagram figcaption p { margin:8px 0; }
.diagram-viewport { overflow:auto; margin-top:16px; }.diagram-svg { min-width:260px; }.diagram-svg :deep(svg) { width:100%; height:auto; max-width:none !important; }
.hld-diagram pre { overflow:auto; font:var(--text-sm) var(--font-mono); white-space:pre; }
.diagram-dialog { max-width:95vw; width:1200px; max-height:92vh; padding:24px; border:1px solid var(--border-default); border-radius:12px; background:var(--bg-card); color:var(--text-primary); overflow:auto; }
.diagram-dialog::backdrop { background:rgba(0,0,0,.7); }
</style>
