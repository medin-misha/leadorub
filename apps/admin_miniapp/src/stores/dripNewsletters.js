import { defineStore } from 'pinia'
import { extractError } from '@/api/http'
import { dripNewslettersApi } from '@/api/dripNewsletters'
import { CALLBACK_DATA_MAX_BYTES } from '@/constants'
import { isButtonValid } from '@/utils/newsletterValidation'
import { isTriggerValid } from '@/utils/dripValidation'

// Стор вкладки «Автоворонка». Поля формы сообщения (text/file/keyboard) и
// getters/actions вокруг них намеренно повторяют контракт stores/newsletter.js:
// это позволяет переиспользовать MessageComposer/KeyboardEditor через prop store.
export const useDripNewslettersStore = defineStore('dripNewsletters', {
  state: () => ({
    // Список правил.
    rules: [],
    loading: false,
    listError: null,
    // Триггер создаваемого правила.
    title: '',
    triggerState: '',
    daysOffset: 1,
    sendTime: '10:00',
    // Контент сообщения — контракт MessageComposer/KeyboardEditor.
    text: '',
    file: null,
    keyboard: { type: 'inline', buttons: [] },
    sending: false,
    error: null,
    result: null, // созданное правило после успеха
  }),

  getters: {
    // Кнопка отправки формы активна, когда есть контент И валиден триггер.
    canSend: (state) => {
      const hasContent = state.text.trim().length > 0 || state.file !== null
      return hasContent && isTriggerValid(state)
    },

    keyboardLabel: (state) => {
      const n = state.keyboard.buttons.length
      return n ? `${n} (${state.keyboard.type})` : null
    },

    keyboardValid: (state) =>
      state.keyboard.buttons.every((b) => isButtonValid(b, state.keyboard.type)),

    keyboardError: (state) => {
      const { buttons, type } = state.keyboard
      for (let i = 0; i < buttons.length; i++) {
        const btn = buttons[i]
        if (isButtonValid(btn, type)) continue
        const n = i + 1
        if (!btn.text.trim()) return `Кнопка ${n}: укажите текст`
        const url = btn.url.trim()
        const cb = btn.callback_data.trim()
        const hasUrl = url.length > 0
        const hasCb = cb.length > 0
        if (hasUrl === hasCb) return `Кнопка ${n}: укажите ссылку или callback_data`
        if (hasUrl) return `Кнопка ${n}: некорректная ссылка (нужен https://домен.ru или tg://…)`
        return `Кнопка ${n}: callback_data длиннее ${CALLBACK_DATA_MAX_BYTES} байт`
      }
      return null
    },

    canAddButton: (state) => {
      const { buttons, type } = state.keyboard
      if (buttons.length === 0) return true
      return isButtonValid(buttons[buttons.length - 1], type)
    },
  },

  actions: {
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

    async fetchRules() {
      this.loading = true
      this.listError = null
      try {
        // Правил единицы — пагинация в v1 не нужна, берём с запасом.
        this.rules = await dripNewslettersApi.list({ page: 1, limit: 100 })
      } catch (err) {
        this.listError = extractError(err)
      } finally {
        this.loading = false
      }
    },

    async create() {
      if (this.sending) return
      this.error = null
      if (!this.canSend) {
        this.error = 'Заполните триггер и добавьте текст или вложение'
        return
      }
      if (!this.keyboardValid) {
        this.error = this.keyboardError || 'Проверьте кнопки'
        return
      }

      const hasButtons = this.keyboard.buttons.length > 0
      const body = {
        title: this.title.trim() || null,
        trigger_state: this.triggerState.trim(),
        days_offset: Number(this.daysOffset),
        send_time: this.sendTime,
        text: this.text.trim() ? this.text : null,
        // use_buttons и buttons включаются только вместе (контракт бэкенда).
        use_buttons: hasButtons ? this.keyboard.type.toUpperCase() : null,
        buttons: hasButtons
          ? this.keyboard.buttons.map((b) => {
              if (this.keyboard.type === 'reply') return { text: b.text.trim() }
              const btn = { text: b.text.trim() }
              if (b.url.trim()) btn.url = b.url.trim()
              else if (b.callback_data.trim()) btn.callback_data = b.callback_data.trim()
              return btn
            })
          : null,
      }

      const form = new FormData()
      form.append('payload', JSON.stringify(body))
      if (this.file) form.append('file', this.file)

      this.sending = true
      try {
        this.result = await dripNewslettersApi.create(form)
        this.rules.unshift(this.result)
        // Чистим контент и триггер, кроме состояния — обычно правил несколько
        // на одно состояние, так удобнее заводить серию.
        this.title = ''
        this.text = ''
        this.file = null
        this.keyboard = { type: 'inline', buttons: [] }
      } catch (err) {
        this.error = extractError(err)
      } finally {
        this.sending = false
      }
    },

    async toggleActive(rule) {
      try {
        const updated = await dripNewslettersApi.patch(rule.id, {
          is_active: !rule.is_active,
        })
        const idx = this.rules.findIndex((r) => r.id === rule.id)
        // PATCH-ответ не считает sent_count — сохраняем прежнее значение.
        if (idx !== -1) {
          this.rules[idx] = { ...updated, sent_count: this.rules[idx].sent_count }
        }
      } catch (err) {
        this.listError = extractError(err)
      }
    },

    async removeRule(id) {
      try {
        await dripNewslettersApi.remove(id)
        this.rules = this.rules.filter((r) => r.id !== id)
      } catch (err) {
        this.listError = extractError(err)
      }
    },
  },
})
