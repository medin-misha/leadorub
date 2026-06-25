<script setup>
import { ref } from 'vue'
import { MESSAGE_MAX_LENGTH } from '@/constants'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseFileInput from '@/components/ui/BaseFileInput.vue'

const props = defineProps({
  sending: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['send'])

const text = ref('')
const file = ref(null)

function submit() {
  const body = text.value.trim()
  // Отправляем при наличии текста ИЛИ файла.
  if ((!body && !file.value) || props.sending || props.disabled) return
  emit('send', { text: body, file: file.value })
  text.value = ''
  file.value = null
}

// Enter — отправить, Shift+Enter — перенос строки.
function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    submit()
  }
}
</script>

<template>
  <form class="composer" @submit.prevent="submit">
    <BaseFileInput v-model="file" />
    <div class="composer__row">
      <textarea
        v-model="text"
        class="composer__input"
        rows="2"
        :maxlength="MESSAGE_MAX_LENGTH"
        placeholder="Ваш ответ…"
        :disabled="disabled"
        @keydown="onKeydown"
      />
      <BaseButton type="submit" :disabled="sending || disabled || (!text.trim() && !file)">
        Отправить
      </BaseButton>
    </div>
    <span
      class="composer__counter"
      :class="{ 'composer__counter--max': text.length >= MESSAGE_MAX_LENGTH }"
    >
      {{ text.length }} / {{ MESSAGE_MAX_LENGTH }}
    </span>
  </form>
</template>

<style scoped>
.composer {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  border-top: 1px solid var(--color-border);
}
.composer__row {
  display: flex;
  gap: var(--space-2);
  align-items: flex-end;
}
.composer__input {
  flex: 1;
  resize: vertical;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font: inherit;
}
.composer__input:focus {
  outline: none;
  border-color: var(--color-primary);
}
.composer__counter {
  align-self: flex-end;
  font-size: 12px;
  color: var(--color-text-muted);
}
.composer__counter--max {
  color: var(--color-danger);
}
</style>
