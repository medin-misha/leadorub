<script setup>
import { useNewsletterStore } from '@/stores/newsletter'
import BaseInput from '@/components/ui/BaseInput.vue'
import { CALLBACK_DATA_MAX_BYTES } from '@/constants'

const store = useNewsletterStore()

// Исчезающие поля inline-кнопки:
// url показываем, пока callback_data пуст; callback_data — пока пуст url.
// Оба пусты → видны оба; как только в одном появился текст — второе скрыто.
function showUrl(btn) {
  return !btn.callback_data.trim()
}
function showCb(btn) {
  return !btn.url.trim()
}
</script>

<template>
  <div class="kb">
    <span class="kb__label">Кнопки</span>

    <!-- Переключатель типа клавиатуры -->
    <div class="kb__seg" role="group" aria-label="Тип клавиатуры">
      <button
        type="button"
        :class="['kb__seg-btn', { 'kb__seg-btn--active': store.keyboard.type === 'inline' }]"
        @click="store.setKeyboardType('inline')"
      >
        Inline
      </button>
      <button
        type="button"
        :class="['kb__seg-btn', { 'kb__seg-btn--active': store.keyboard.type === 'reply' }]"
        @click="store.setKeyboardType('reply')"
      >
        Reply
      </button>
    </div>

    <!-- Список кнопок: одна кнопка = одна карточка-строка -->
    <div
      v-for="(btn, i) in store.keyboard.buttons"
      :key="i"
      class="kb__item"
    >
      <div class="kb__item-head">
        <BaseInput
          class="kb__grow"
          :model-value="btn.text"
          placeholder="Текст кнопки"
          @update:model-value="store.updateButton(i, { text: $event })"
        />
        <button type="button" class="kb__remove" title="Удалить" @click="store.removeButton(i)">
          ×
        </button>
      </div>

      <!-- Доп. поля только для inline -->
      <template v-if="store.keyboard.type === 'inline'">
        <BaseInput
          v-if="showUrl(btn)"
          :model-value="btn.url"
          placeholder="URL (https://…)"
          @update:model-value="store.updateButton(i, { url: $event })"
        />
        <BaseInput
          v-if="showCb(btn)"
          :model-value="btn.callback_data"
          :maxlength="CALLBACK_DATA_MAX_BYTES"
          placeholder="callback_data (до 64 байт)"
          @update:model-value="store.updateButton(i, { callback_data: $event })"
        />
      </template>
    </div>

    <p v-if="store.keyboardError" class="kb__error">{{ store.keyboardError }}</p>

    <button
      type="button"
      class="kb__add"
      :disabled="!store.canAddButton"
      @click="store.addButton()"
    >
      + Добавить кнопку
    </button>
  </div>
</template>

<style scoped>
.kb {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.kb__label {
  font-size: 13px;
  color: var(--color-text-muted);
}
.kb__seg {
  display: inline-flex;
  align-self: flex-start;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  overflow: hidden;
}
.kb__seg-btn {
  padding: var(--space-2) var(--space-4);
  border: none;
  background: var(--color-surface);
  font: inherit;
  color: var(--color-text);
  cursor: pointer;
}
.kb__seg-btn--active {
  background: var(--color-primary);
  color: #fff;
}
.kb__item {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  background: var(--color-bg);
}
.kb__item-head {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
}
.kb__grow {
  flex: 1;
}
.kb__remove {
  border: none;
  background: none;
  font-size: 22px;
  line-height: 1;
  padding: var(--space-1) var(--space-2);
  color: var(--color-text-muted);
  cursor: pointer;
}
.kb__remove:hover {
  color: var(--color-danger);
}
.kb__error {
  margin: 0;
  font-size: 13px;
  color: var(--color-danger);
}
.kb__add {
  align-self: flex-start;
  padding: var(--space-2) var(--space-4);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius);
  background: var(--color-surface);
  font: inherit;
  color: var(--color-text);
  cursor: pointer;
}
.kb__add:hover:not(:disabled) {
  border-color: var(--color-primary);
}
.kb__add:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
