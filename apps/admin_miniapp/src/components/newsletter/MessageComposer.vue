<script setup>
import { computed } from 'vue'
import { useNewsletterStore } from '@/stores/newsletter'
import { MESSAGE_MAX_LENGTH } from '@/constants'
import BaseFileInput from '@/components/ui/BaseFileInput.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import KeyboardEditor from '@/components/newsletter/KeyboardEditor.vue'

const emit = defineEmits(['submit']) // просим вьюху открыть диалог подтверждения

// Компонент переиспользуется вкладкой капельных рассылок: она передаёт свой
// стор с тем же контрактом полей (text/file/keyboard, canSend, keyboardValid…).
// Без пропса — прежнее поведение (стор обычной рассылки).
const props = defineProps({
  store: { type: Object, default: null },
  submitLabel: { type: String, default: 'Разослать' },
})

const store = props.store ?? useNewsletterStore()

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
      :maxlength="MESSAGE_MAX_LENGTH"
      placeholder="Текст рассылки…"
    />
    <span
      class="composer__counter"
      :class="{ 'composer__counter--max': text.length >= MESSAGE_MAX_LENGTH }"
    >
      {{ text.length }} / {{ MESSAGE_MAX_LENGTH }}
    </span>

    <BaseFileInput v-model="file" label="Вложение" />

    <KeyboardEditor :store="store" />

    <div class="composer__actions">
      <BaseButton
        :disabled="!store.canSend || !store.keyboardValid || store.sending"
        @click="emit('submit')"
      >
        {{ submitLabel }}
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
.composer__counter {
  margin-top: calc(-1 * var(--space-2));
  align-self: flex-end;
  font-size: 12px;
  color: var(--color-text-muted);
}
.composer__counter--max {
  color: var(--color-danger);
}
.composer__actions {
  display: flex;
  justify-content: flex-end;
}
</style>
