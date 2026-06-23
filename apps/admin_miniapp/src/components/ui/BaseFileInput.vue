<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'

const props = defineProps({
  modelValue: { type: Object, default: null }, // File | null (File — это объект)
  label: { type: String, default: '' },
  accept: { type: String, default: '' }, // '' = любой тип
})
const emit = defineEmits(['update:modelValue'])

const inputRef = ref(null)
const previewUrl = ref('') // object URL для превью изображения

// При смене файла пересоздаём object URL (для картинок — показываем превью),
// старый обязательно освобождаем, иначе утечёт память.
watch(
  () => props.modelValue,
  (file) => {
    if (previewUrl.value) {
      URL.revokeObjectURL(previewUrl.value)
      previewUrl.value = ''
    }
    if (file && file.type.startsWith('image/')) {
      previewUrl.value = URL.createObjectURL(file)
    }
  }
)

onBeforeUnmount(() => {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
})

function onChange(e) {
  const file = e.target.files?.[0] ?? null
  emit('update:modelValue', file)
}

function pick() {
  inputRef.value?.click()
}

function clear() {
  emit('update:modelValue', null)
  // сбрасываем native input, чтобы можно было выбрать тот же файл повторно
  if (inputRef.value) inputRef.value.value = ''
}

// Человекочитаемый размер файла.
function fmtSize(bytes) {
  if (bytes < 1024) return `${bytes} Б`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`
  return `${(bytes / 1024 / 1024).toFixed(1)} МБ`
}
</script>

<template>
  <div class="file">
    <span v-if="label" class="file__label">{{ label }}</span>

    <!-- native input скрыт, открываем его кликом по кнопке -->
    <input
      ref="inputRef"
      type="file"
      class="file__native"
      :accept="accept"
      @change="onChange"
    />

    <div v-if="!modelValue">
      <button type="button" class="file__btn" @click="pick">📎 Прикрепить файл</button>
    </div>

    <div v-else class="file__selected">
      <img v-if="previewUrl" :src="previewUrl" alt="" class="file__thumb" />
      <div class="file__meta">
        <span class="file__name">{{ modelValue.name }}</span>
        <span class="file__size">{{ fmtSize(modelValue.size) }}</span>
      </div>
      <button type="button" class="file__remove" title="Убрать" @click="clear">×</button>
    </div>
  </div>
</template>

<style scoped>
.file {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.file__label {
  font-size: 13px;
  color: var(--color-text-muted);
}
.file__native {
  display: none;
}
.file__btn {
  padding: var(--space-2) var(--space-4);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius);
  background: var(--color-surface);
  font: inherit;
  color: var(--color-text);
  cursor: pointer;
}
.file__btn:hover {
  border-color: var(--color-primary);
}
.file__selected {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  background: var(--color-surface);
}
.file__thumb {
  width: 40px;
  height: 40px;
  object-fit: cover;
  border-radius: var(--radius);
}
.file__meta {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}
.file__name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.file__size {
  font-size: 12px;
  color: var(--color-text-muted);
}
.file__remove {
  border: none;
  background: none;
  font-size: 20px;
  line-height: 1;
  color: var(--color-text-muted);
  cursor: pointer;
}
</style>
