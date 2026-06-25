<script setup>
import { ref, watch, nextTick } from 'vue'
import MessageBubble from './MessageBubble.vue'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

const scroller = ref(null)

// Автоскролл вниз при появлении новых сообщений. flush:'post' — после рендера DOM.
watch(
  () => props.messages.length,
  async () => {
    await nextTick()
    if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
  },
  { flush: 'post' },
)
</script>

<template>
  <div ref="scroller" class="thread">
    <p v-if="loading && !messages.length" class="thread__empty">Загрузка…</p>
    <p v-else-if="!messages.length" class="thread__empty">Сообщений пока нет</p>
    <MessageBubble v-for="m in messages" :key="m.id" :message="m" />
  </div>
</template>

<style scoped>
.thread {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  overflow-y: auto;
}
.thread__empty {
  margin: auto;
  color: var(--color-text-muted);
}
</style>
