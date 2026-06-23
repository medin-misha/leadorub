<script setup>
import { computed } from 'vue'
import { useNewsletterStore } from '@/stores/newsletter'
import BaseFileInput from '@/components/ui/BaseFileInput.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import KeyboardEditor from '@/components/newsletter/KeyboardEditor.vue'

const emit = defineEmits(['submit']) // просим вьюху открыть диалог подтверждения

const store = useNewsletterStore()

// v-model к стору через computed get/set.
const text = computed({
  get: () => store.text,
  set: (v) => store.setText(v),
})
const file = computed({
  get: () => store.file,
  set: (v) => store.setFile(v),
})
</script>

<template>
  <section class="composer">
    <h3 class="composer__title">Сообщение</h3>

    <textarea
      v-model="text"
      class="composer__text"
      rows="8"
      placeholder="Текст рассылки…"
    />

    <BaseFileInput v-model="file" label="Вложение" />

    <KeyboardEditor />

    <div class="composer__actions">
      <BaseButton
        :disabled="!store.canSend || !store.keyboardValid || store.sending"
        @click="emit('submit')"
      >
        Разослать
      </BaseButton>
    </div>
  </section>
</template>

<style scoped>
.composer {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  background: var(--color-surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: var(--space-4);
}
.composer__title {
  margin: 0;
  font-size: 16px;
}
.composer__text {
  width: 100%;
  resize: vertical;
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font: inherit;
}
.composer__text:focus {
  outline: none;
  border-color: var(--color-primary);
}
.composer__actions {
  display: flex;
  justify-content: flex-end;
}
</style>
