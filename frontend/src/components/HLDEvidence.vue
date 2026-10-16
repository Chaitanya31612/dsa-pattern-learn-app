<script setup lang="ts">
import { computed } from 'vue'
import { moduleEvidence } from '../lib/hldLearning'
import { useHLD } from '../composables/useHLD'
import type { HLDModule } from '../types/hld'
const props = defineProps<{ module: HLDModule }>()
const { state } = useHLD()
const evidence = computed(() => moduleEvidence(props.module, state.modules[props.module.id], Object.values(state.cards)))
const labels = { lesson: 'Explored every lesson step', design: 'Tried every main design round', transfer: 'Tried a changed requirement', repair: 'Tried the repair exercise', quiz: 'Latest quiz at least 75%', independent: 'Unaided design work met the review threshold, provisionally', delayed: 'Recalled a design explanation at least 7 days after first submission' }
</script>
<template>
  <details class="hld-evidence"><summary>Your learning evidence · {{ evidence.count }}/{{ evidence.total }}</summary>
    <ul><li v-for="(label, key) in labels" :key="key"><span :class="{ 'hld-memory-tip': evidence[key] }">{{ evidence[key] ? '✓' : '○' }} {{ label }}</span></li></ul>
    <p class="hld-muted">Review threshold: 18/24, at least 2/3 in every area, no critical correctness gap, and no help during the attempt. Feedback and self-rated recall remain provisional. These checks guide practice; modules stay open.</p>
  </details>
</template>
