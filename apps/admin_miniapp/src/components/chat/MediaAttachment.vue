<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { chatApi } from '@/api/chat'

const props = defineProps({
  fileId: { type: Number, required: true },
  fileName: { type: String, default: '' },
})

const url = ref('')
const loading = ref(true)
const failed = ref(false)

// Картинку показываем превью; остальное — ссылкой на скачивание.
// SVG намеренно исключён: его можно открыть как top-level документ и исполнить
// встроенный <script> в origin'е панели (Stored XSS) — пусть качается, а не рендерится.
const isImage = /\.(png|jpe?g|gif|webp|bmp)$/i.test(props.fileName || '')

onMounted(async () => {
  try {
    // Файл закрыт авторизацией — тянем blob через axios (он добавит Bearer).
    url.value = await chatApi.fileObjectUrl(props.fileId)
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => {
  if (url.value) URL.revokeObjectURL(url.value)
})
</script>

<template>
  <div class="attach">
    <span v-if="loading" class="attach__muted">Загрузка вложения…</span>
    <span v-else-if="failed" class="attach__muted">Не удалось загрузить вложение</span>
    <a v-else-if="isImage" :href="url" target="_blank" rel="noopener">
      <img :src="url" :alt="fileName" class="attach__img" />
    </a>
    <a v-else :href="url" :download="fileName || 'file'" class="attach__file">
      📎 {{ fileName || 'Файл' }}
    </a>
  </div>
</template>

<style scoped>
.attach {
  margin-bottom: var(--space-1);
}
.attach__muted {
  font-size: 12px;
  opacity: 0.7;
}
.attach__img {
  max-width: 220px;
  max-height: 220px;
  border-radius: var(--radius);
  display: block;
}
.attach__file {
  color: inherit;
  text-decoration: underline;
  word-break: break-all;
}
</style>
