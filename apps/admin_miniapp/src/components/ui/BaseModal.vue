<script setup>
defineProps({ title: { type: String, default: '' } })
defineEmits(['close'])
</script>

<template>
  <div class="modal__overlay" @click.self="$emit('close')">
    <div class="modal" role="dialog">
      <header class="modal__header">
        <h3 class="modal__title">{{ title }}</h3>
        <button class="modal__close" @click="$emit('close')">×</button>
      </header>
      <div class="modal__body"><slot /></div>
      <footer class="modal__footer"><slot name="footer" /></footer>
    </div>
  </div>
</template>

<style scoped>
.modal__overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4);
  z-index: 50;
}
.modal {
  background: var(--color-surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  width: 100%;
  max-width: 560px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}
.modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border);
}
.modal__title {
  margin: 0;
  font-size: 16px;
}
.modal__close {
  border: none;
  background: none;
  font-size: 22px;
  cursor: pointer;
  color: var(--color-text-muted);
}
.modal__body {
  padding: var(--space-4);
  overflow-y: auto;
}
.modal__footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--color-border);
}
</style>
