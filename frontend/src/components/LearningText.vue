<script setup lang="ts">
import { computed } from 'vue'
import { readingBeats } from '../lib/reading'
const props=defineProps<{text:string}>()
const beats=computed(()=>props.text.split(/\n\s*\n/).flatMap(p=>readingBeats(p)))
</script>
<template><div class="learning-text"><p v-for="(beat,i) in beats" :key="i">{{ beat.text }}</p></div></template>
<style scoped>.learning-text{max-width:68ch;line-height:1.8;overflow-wrap:anywhere}.learning-text p{margin:0 0 1em}.learning-text p:last-child{margin-bottom:0}</style>
