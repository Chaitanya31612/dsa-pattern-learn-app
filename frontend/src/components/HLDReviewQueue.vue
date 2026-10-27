<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useHLD } from '../composables/useHLD'
import HLDMarkdown from './HLDMarkdown.vue'
import { scheduleReview } from '../lib/hldLearning'
const props = defineProps<{ moduleId?: string }>()
const { course, state, dueCards, now, reviewCard } = useHLD()
const cards = computed(() => dueCards.value.filter(c => !props.moduleId || c.moduleId === props.moduleId))
const nextDue = computed(() => Object.values(state.cards).filter(c => (!props.moduleId || c.moduleId === props.moduleId) && c.dueAt > now.value).sort((a,b) => a.dueAt - b.dueAt)[0]?.dueAt)
const card = computed(() => cards.value[0])
const response = ref('')
const revealed = ref(false)
const error = ref('')
const completed = ref(0)
watch(() => card.value?.id, () => { response.value = ''; revealed.value = false; error.value = '' })
const title = computed(() => course.value?.modules.find(m => m.id === card.value?.moduleId)?.title)
const nextGood = computed(() => card.value ? new Date(scheduleReview(card.value, 'good', now.value).dueAt).toLocaleDateString() : '')
function rate(rating: 'again' | 'hard' | 'good') {
  if (!card.value || !revealed.value) return
  try { reviewCard(card.value.id, rating, response.value); completed.value++ }
  catch (err) { error.value = err instanceof Error ? err.message : 'Could not save recall.' }
}
</script>
<template>
  <section class="hld-review">
    <div class="hld-row"><h2>Recall before you reread</h2><span class="hld-muted">{{ cards.length }} due · {{ completed }} reviewed this session</span></div>
    <template v-if="card">
      <div class="hld-row"><span class="hld-eyebrow">{{ card.kind }} · {{ title }}</span><router-link :to="`/hld/${card.moduleId}`">Open lesson</router-link></div>
      <HLDMarkdown :content="card.question" />
      <label class="hld-label" for="hld-recall-response">Your explanation, without notes</label>
      <textarea id="hld-recall-response" v-model="response" class="hld-input" rows="5" placeholder="Name the mechanism, its assumptions, a failure case, and the trade-off."></textarea>
      <button v-if="!revealed" class="btn btn-primary" :disabled="!response.trim()" @click="revealed = true">Compare after recalling</button>
      <div v-else class="hld-feedback">
        <HLDMarkdown :content="card.answer" />
        <p class="hld-muted">Rate your recall honestly. This schedules review; it is not a design assessment.</p>
        <div class="hld-row">
          <button class="btn" @click="rate('again')">Again · 10 minutes</button>
          <button class="btn" @click="rate('hard')">Partial · tomorrow</button>
          <button class="btn btn-primary" @click="rate('good')">Retrieved · {{ nextGood }}</button>
        </div>
      </div>
      <p v-if="error" role="alert">{{ error }}</p>
    </template>
    <div v-else class="hld-empty">
      <h3>{{ completed ? 'Review session complete' : 'No HLD reviews due here' }}</h3>
      <p>Lesson completion, submitted designs, and quizzes add recall cards. Missed questions return immediately; later reviews spread out as you retrieve them.</p>
      <p v-if="nextDue">Next scheduled HLD review: {{ new Date(nextDue).toLocaleString() }}</p>
    </div>
  </section>
</template>
