<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { HLDModule, HLDSection } from '../types/hld'
import HLDMarkdown from './HLDMarkdown.vue'
import HLDDiagram from './HLDDiagram.vue'
const props = defineProps<{ example: HLDSection; visuals: HLDModule['visuals'] }>()
const steps = computed(() => {
  const matches = [...props.example.content.matchAll(/^### (.+)$/gm)]
  if (!matches.length) return [{ title:'Explanation', content:props.example.content }]
  return matches.map((m,i) => ({ title:m[1]!, content:props.example.content.slice(m.index! + m[0].length, matches[i+1]?.index ?? props.example.content.length).trim() }))
})
const index = ref(0)
const predictions = ref<Record<number,string>>({})
const revealed = ref<Record<number,boolean>>({0:true})
watch(() => props.example.content, () => { index.value=0; predictions.value={}; revealed.value={0:true} })
const current = computed(() => steps.value[index.value]!)
</script>
<template>
  <article class="hld-content-pane">
    <h2>{{ example.title }}</h2><p class="hld-muted">One decision at a time. First read the contract. For the next steps, predict before comparing. These teaching notes are not graded.</p>
    <nav class="hld-phase-tabs" aria-label="Worked example steps"><button v-for="(step,i) in steps" :key="i" :class="{selected:index===i}" :aria-pressed="index===i" @click="index=i">{{ step.title }}</button></nav>
    <h3 class="hld-worked-heading">{{ index+1 }}/{{ steps.length }} · {{ current.title }}</h3>
    <template v-if="!revealed[index]"><label class="hld-label">What would you decide here, and why?<textarea v-model="predictions[index]" class="hld-input" rows="3" placeholder="My choice is… because the requirement says…"></textarea></label><button class="btn btn-primary" :disabled="!predictions[index]?.trim()" @click="revealed[index]=true">Compare with the worked explanation</button></template>
    <template v-else><HLDMarkdown :content="current.content" /><HLDDiagram v-if="current.title.includes('Flow') && visuals[0]" :title="visuals[0].title" :caption="visuals[0].caption" :code="visuals[0].code" /></template>
    <div class="hld-row"><button class="btn" :disabled="index===0" @click="index--">Previous decision</button><button class="btn" :disabled="index===steps.length-1 || !revealed[index]" @click="index++">Next decision →</button></div>
  </article>
</template>
<style scoped>.hld-worked-heading { margin:24px 0 16px; }</style>
