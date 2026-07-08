<script setup>
defineProps({
  conversations: { type: Array, default: () => [] },
  activeUid: { type: [Number, null], default: null },
})
defineEmits(['select'])

// Заголовок диалога: имя → @username → "ID <telegram_id>".
function title(c) {
  const name = [c.first_name, c.last_name].filter(Boolean).join(' ')
  if (name) return name
  if (c.username) return '@' + c.username
  return 'ID ' + c.telegram_id
}

// Превью последнего сообщения; ответы администратора помечаем «Вы: ».
// Пустой текст означает сообщение-вложение (текста нет → был файл).
function preview(c) {
  if (!c.last_direction && !c.last_text) {
    return 'Начать диалог'
  }
  const prefix = c.last_direction === 'admin' ? 'Вы: ' : ''
  return prefix + (c.last_text || '📎 Вложение')
}

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
  <ul class="conv-list">
    <li
      v-for="c in conversations"
      :key="c.telegram_user_id"
      :class="[
        'conv',
        { 'conv--active': c.telegram_user_id === activeUid },
      ]"
      @click="$emit('select', c.telegram_user_id)"
    >
      <div class="conv__row">
        <span class="conv__title">{{ title(c) }}</span>
        <span class="conv__time">{{ formatTime(c.last_at) }}</span>
      </div>
      <div class="conv__row">
        <span class="conv__preview">{{ preview(c) }}</span>
        <span v-if="c.unread_count > 0" class="conv__badge">{{ c.unread_count }}</span>
      </div>
    </li>
    <li v-if="!conversations.length" class="conv-list__empty">Диалогов пока нет</li>
  </ul>
</template>

<style scoped>
.conv-list {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  flex: 1;
}
.conv {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--color-border);
  cursor: pointer;
}
.conv:hover {
  background: var(--color-bg);
}
.conv--active {
  background: var(--color-bg);
}
.conv__row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2);
}
.conv__title {
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.conv__time {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--color-text-muted);
}
.conv__preview {
  font-size: 13px;
  color: var(--color-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.conv__badge {
  flex-shrink: 0;
  min-width: 18px;
  padding: 0 6px;
  border-radius: 9px;
  background: var(--color-primary);
  color: #fff;
  font-size: 12px;
  line-height: 18px;
  text-align: center;
}
.conv-list__empty {
  padding: var(--space-4);
  color: var(--color-text-muted);
  text-align: center;
}
</style>
