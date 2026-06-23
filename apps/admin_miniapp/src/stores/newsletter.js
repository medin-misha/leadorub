import { defineStore } from 'pinia'
import { extractError } from '@/api/http'

// Заглушка отправки: бэкенда ещё нет. Имитируем сетевую задержку и успех.
// TODO: удалить mockSend и звать newsletterApi.send(form) из @/api/newsletter,
// когда появится POST /telegram/newsletter.
function mockSend(_form) {
  return new Promise((resolve) => setTimeout(() => resolve({ status: 'ok' }), 800))
}

// Валидность одной кнопки в зависимости от типа клавиатуры.
// reply: достаточно текста. inline: текст + РОВНО одно из url / callback_data.
function isButtonValid(btn, type) {
  if (!btn.text.trim()) return false
  if (type === 'reply') return true
  const hasUrl = btn.url.trim().length > 0
  const hasCb = btn.callback_data.trim().length > 0
  return hasUrl !== hasCb // XOR — ровно одно поле заполнено
}

export const useNewsletterStore = defineStore('newsletter', {
  state: () => ({
    audience: { mode: 'all', search: '', field: '' }, // mode: 'all' | 'filter'
    text: '',
    file: null, // File | null
    // Клавиатура сообщения. type: 'inline' | 'reply'.
    // Кнопка: { text, url, callback_data }. Для reply используется только text.
    keyboard: { type: 'inline', buttons: [] },
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

    // Сводка для диалога подтверждения: «3 (inline)» либо null (кнопок нет).
    keyboardLabel: (state) => {
      const n = state.keyboard.buttons.length
      return n ? `${n} (${state.keyboard.type})` : null
    },

    // Все кнопки валидны (пустой список тоже валиден — клавиатуры просто нет).
    keyboardValid: (state) =>
      state.keyboard.buttons.every((b) => isButtonValid(b, state.keyboard.type)),

    // Текст первой ошибки для показа под списком, либо null.
    keyboardError: (state) => {
      const { buttons, type } = state.keyboard
      for (let i = 0; i < buttons.length; i++) {
        if (isButtonValid(buttons[i], type)) continue
        if (!buttons[i].text.trim()) return `Кнопка ${i + 1}: укажите текст`
        return `Кнопка ${i + 1}: укажите ссылку или callback_data`
      }
      return null
    },

    // Добавлять новую кнопку можно, только если последняя уже валидна
    // (или список пуст). Не даёт накопить хвост из пустых кнопок.
    canAddButton: (state) => {
      const { buttons, type } = state.keyboard
      if (buttons.length === 0) return true
      return isButtonValid(buttons[buttons.length - 1], type)
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

    setKeyboardType(type) {
      this.keyboard.type = type
    },
    addButton() {
      this.keyboard.buttons.push({ text: '', url: '', callback_data: '' })
    },
    updateButton(index, patch) {
      const btn = this.keyboard.buttons[index]
      if (btn) Object.assign(btn, patch)
    },
    removeButton(index) {
      this.keyboard.buttons.splice(index, 1)
    },

    async send() {
      if (this.sending) return // защита от двойного клика / повторного входа
      this.error = null
      if (!this.canSend) {
        this.error = 'Добавьте текст или вложение'
        return
      }
      // Защита на случай вызова в обход заблокированной кнопки.
      if (!this.keyboardValid) {
        this.error = this.keyboardError || 'Проверьте кнопки'
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
      // Клавиатуру кладём одним JSON-полем, только если есть валидные кнопки.
      // У inline-кнопки оставляем лишь заполненный ключ (url ИЛИ callback_data).
      if (this.keyboard.buttons.length > 0) {
        const payload = {
          type: this.keyboard.type,
          buttons: this.keyboard.buttons.map((b) => {
            if (this.keyboard.type === 'reply') return { text: b.text.trim() }
            const btn = { text: b.text.trim() }
            if (b.url.trim()) btn.url = b.url.trim()
            else if (b.callback_data.trim()) btn.callback_data = b.callback_data.trim()
            return btn
          }),
        }
        form.append('keyboard', JSON.stringify(payload))
      }

      this.sending = true
      try {
        // TODO: заменить mockSend(form) на newsletterApi.send(form), когда будет бэкенд.
        this.result = await mockSend(form)
        // После успеха чистим сообщение и кнопки, аудиторию оставляем.
        this.text = ''
        this.file = null
        this.keyboard = { type: 'inline', buttons: [] }
      } catch (err) {
        this.error = extractError(err)
      } finally {
        this.sending = false
      }
    },

    reset() {
      this.text = ''
      this.file = null
      this.keyboard = { type: 'inline', buttons: [] }
      this.error = null
      this.result = null
    },
  },
})
