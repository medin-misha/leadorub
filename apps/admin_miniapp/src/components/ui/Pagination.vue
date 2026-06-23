<script setup>
defineProps({
  page: { type: Number, required: true },
  hasNext: { type: Boolean, default: false },
  limit: { type: Number, default: 10 },
  limitOptions: { type: Array, default: () => [10, 20, 50] },
})
defineEmits(['update:page', 'update:limit'])
</script>

<template>
  <div class="pager">
    <button class="pager__btn" :disabled="page <= 1" @click="$emit('update:page', page - 1)">←</button>
    <span class="pager__page">Стр. {{ page }}</span>
    <button class="pager__btn" :disabled="!hasNext" @click="$emit('update:page', page + 1)">→</button>
    <select
      class="pager__limit"
      :value="limit"
      @change="$emit('update:limit', Number($event.target.value))"
    >
      <option v-for="opt in limitOptions" :key="opt" :value="opt">{{ opt }} / стр.</option>
    </select>
  </div>
</template>

<style scoped>
.pager {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.pager__btn {
  padding: var(--space-1) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  background: var(--color-surface);
  cursor: pointer;
}
.pager__btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.pager__page {
  color: var(--color-text-muted);
  font-size: 14px;
}
.pager__limit {
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
}
</style>
