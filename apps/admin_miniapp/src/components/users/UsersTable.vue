<script setup>
import BaseButton from '@/components/ui/BaseButton.vue'

defineProps({
  items: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})
defineEmits(['edit', 'delete'])

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('ru-RU')
}
</script>

<template>
  <div class="table-wrap">
    <table class="table">
      <thead>
        <tr>
          <th>ID</th>
          <th>telegram_id</th>
          <th>username</th>
          <th>Имя</th>
          <th>Язык</th>
          <th>Бот заблокирован</th>
          <th>Создан</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="u in items" :key="u.id">
          <td>{{ u.id }}</td>
          <td>{{ u.telegram_id }}</td>
          <td>{{ u.username || '—' }}</td>
          <td>{{ [u.first_name, u.last_name].filter(Boolean).join(' ') || '—' }}</td>
          <td>{{ u.language_code || '—' }}</td>
          <td>{{ u.is_blocket_bot ? 'да' : 'нет' }}</td>
          <td>{{ fmtDate(u.created_at) }}</td>
          <td class="table__actions">
            <BaseButton variant="ghost" @click="$emit('edit', u)">Изменить</BaseButton>
            <BaseButton variant="danger" @click="$emit('delete', u)">Удалить</BaseButton>
          </td>
        </tr>
        <tr v-if="!loading && !items.length">
          <td colspan="8" class="table__empty">Ничего не найдено</td>
        </tr>
        <tr v-if="loading">
          <td colspan="8" class="table__empty">Загрузка…</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.table-wrap {
  overflow-x: auto;
  background: var(--color-surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}
.table {
  width: 100%;
  border-collapse: collapse;
}
.table th,
.table td {
  padding: var(--space-3);
  text-align: left;
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}
.table th {
  font-size: 13px;
  color: var(--color-text-muted);
}
.table__actions {
  display: flex;
  gap: var(--space-2);
}
.table__empty {
  text-align: center;
  color: var(--color-text-muted);
  padding: var(--space-5);
}
</style>
