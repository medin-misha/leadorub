<script setup>
import MediaAttachment from './MediaAttachment.vue'

defineProps({
  message: { type: Object, required: true },
})

// Короткое время для пузыря сообщения.
function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <div
    :class="[
      'bubble',
      message.direction === 'admin' ? 'bubble--admin' : 'bubble--user',
    ]"
  >
    <MediaAttachment
      v-if="message.file_id"
      :file-id="message.file_id"
      :file-name="message.file_name"
    />
    <p v-if="message.text" class="bubble__text">{{ message.text }}</p>
    <span class="bubble__time">{{ formatTime(message.created_at) }}</span>
  </div>
</template>

<style scoped>
.bubble {
  max-width: 75%;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius);
  white-space: pre-wrap;
  word-break: break-word;
}
/* Сообщение пользователя — слева, ответ администратора — справа. */
.bubble--user {
  align-self: flex-start;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}
.bubble--admin {
  align-self: flex-end;
  background: var(--color-primary);
  color: #fff;
}
.bubble__text {
  margin: 0;
}
.bubble__time {
  display: block;
  margin-top: var(--space-1);
  font-size: 11px;
  opacity: 0.7;
  text-align: right;
}
</style>
