import { defineStore } from 'pinia'
import { extractError } from '@/api/http'

// Заглушка отправки: бэкенда ещё нет. Имитируем сетевую задержку и успех.
// TODO: удалить mockSend и звать newsletterApi.send(form) из @/api/newsletter,
// когда появится POST /telegram/newsletter.
function mockSend(_form) {
  return new Promise((resolve) => setTimeout(() => resolve({ status: 'ok' }), 800))
}

export const useNewsletterStore = defineStore('newsletter', {
  state: () => ({
    audience: { mode: 'all', search: '', field: '' }, // mode: 'all' | 'filter'
    text: '',
    file: null, // File | null
    sending: false,
    error: null,
    result: null, // { status } после успешной отправки
  }),

  getters: {
    // Слать можно, если есть текст ИЛИ вложение. Пустую рассылку запрещаем.
    canSend: (state) => state.text.trim().length > 0 || state.file !== null,
    // Человекочитаемое описание аудитории для диалога подтверждения.
    audienceLabel: (state) => {
      if (state.audience.mode === 'all') return 'Все пользователи'
      const where = state.audience.field || 'везде'
      const q = state.audience.search || '—'
      return `Фильтр: ${where} ⊇ "${q}"`
    },
  },

  actions: {
    setAudience({ mode, search, field }) {
      this.audience = {
        mode: mode ?? this.audience.mode,
        search: search ?? '',
        field: field ?? '',
      }
    },
    setText(value) {
      this.text = value
    },
    setFile(file) {
      this.file = file
    },

    async send() {
      this.error = null
      if (!this.canSend) {
        this.error = 'Добавьте текст или вложение'
        return
      }
      // FormData — потому что есть бинарный файл (multipart).
      const form = new FormData()
      form.append('text', this.text)
      if (this.file) form.append('file', this.file)
      form.append('mode', this.audience.mode)
      if (this.audience.mode === 'filter') {
        form.append('search', this.audience.search)
        form.append('field', this.audience.field)
      }

      this.sending = true
      try {
        // TODO: заменить mockSend(form) на newsletterApi.send(form), когда будет бэкенд.
        this.result = await mockSend(form)
        // После успеха чистим сообщение, аудиторию оставляем.
        this.text = ''
        this.file = null
      } catch (err) {
        this.error = extractError(err)
      } finally {
        this.sending = false
      }
    },

    reset() {
      this.text = ''
      this.file = null
      this.error = null
      this.result = null
    },
  },
})
