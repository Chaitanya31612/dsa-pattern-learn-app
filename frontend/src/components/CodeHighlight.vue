<script setup lang="ts">
import { computed } from 'vue'
import hljs from 'highlight.js/lib/core'
import python from 'highlight.js/lib/languages/python'
import javascript from 'highlight.js/lib/languages/javascript'
import java from 'highlight.js/lib/languages/java'

hljs.registerLanguage('python', python)
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('java', java)

const props = defineProps<{
  code: string
  language: string
}>()

const highlightedHtml = computed(() => {
  if (!props.code) return ''
  const lang = props.language === 'javascript' ? 'javascript' : props.language === 'java' ? 'java' : 'python'
  return hljs.highlight(props.code, { language: lang }).value
})
</script>

<template>
  <div class="code-block">
    <span class="code-lang">{{ language }}</span>
    <pre><code :class="`hljs language-${language}`" v-html="highlightedHtml"></code></pre>
  </div>
</template>

<style>
/* highlight.js theme — custom dark matching our design system */
.hljs {
  background: transparent !important;
  color: var(--text-primary);
}
.hljs-keyword,
.hljs-selector-tag,
.hljs-built_in { color: var(--accent-purple, #c084fc); }
.hljs-string,
.hljs-attr { color: var(--accent-green, #22d3a7); }
.hljs-number,
.hljs-literal { color: var(--accent-orange, #fb923c); }
.hljs-comment,
.hljs-doctag { color: var(--text-muted); font-style: italic; }
.hljs-function .hljs-title,
.hljs-title.function_,
.hljs-title { color: var(--accent-cyan, #38bdf8); }
.hljs-type,
.hljs-class .hljs-title { color: var(--accent-yellow, #fbbf24); }
.hljs-params { color: var(--text-secondary); }
.hljs-variable,
.hljs-template-variable { color: var(--accent-pink, #f472b6); }
.hljs-meta { color: var(--text-muted); }
.hljs-punctuation { color: var(--text-muted); }
</style>
