import { defineStore } from 'pinia'
import { extractError } from '@/api/http'
import { newsletterApi } from '@/api/newsletter'
import { CALLBACK_DATA_MAX_BYTES } from '@/constants'

// Telegram принимает в inline-URL-кнопке только http(s) и deep-link tg://
// (Bot API, InlineKeyboardButton.url — «HTTP or tg:// URL»).
const URL_SCHEMES = ['http:', 'https:', 'tg:']

// IPv4 вида 1.2.3.4 — у него «TLD» числовой, поэтому разрешаем отдельным правилом.
const IPV4_RE = /^(\d{1,3}\.){3}\d{1,3}$/

// Похож ли хост http(s)-ссылки на «настоящий» домен. Важно: new URL() пропускает
// одно-словные хосты («asdasd», «localhost») — синтаксически они валидны, но
// Telegram их отклоняет («Bad Request: ... URL is invalid: Wrong HTTP URL»):
// ему нужен домен с точкой и непустым TLD. Эту проверку URL-конструктор не делает.
function isValidHttpHost(hostname) {
  if (!hostname) return false
  if (IPV4_RE.test(hostname)) return true
  const labels = hostname.split('.')
  // Нужно ≥2 меток, ни одной пустой (нет ведущей/висячей/двойной точки),
  // и TLD из ≥2 символов (.com, .ru, .io …).
  if (labels.length < 2) return false
  if (labels.some((label) => label.length === 0)) return false
  return labels[labels.length - 1].length >= 2
}

// Валиден ли URL inline-кнопки. Парсим конструктором URL (он отсекает мусор без
// схемы и с пробелами), проверяем схему, а для http(s) — ещё и «настоящий» хост.
function isValidButtonUrl(value) {
  let parsed
  try {
    parsed = new URL(value)
  } catch {
    return false
  }
  if (!URL_SCHEMES.includes(parsed.protocol)) return false
  // tg:// — deep-link внутрь Telegram, домен ему не нужен.
  if (parsed.protocol === 'tg:') return true
  return isValidHttpHost(parsed.hostname)
}

// Длина строки в БАЙТАХ UTF-8: лимит Telegram на callback_data — 64 байта, а не
// символа, поэтому считаем именно байты (TextEncoder есть во всех целевых браузерах).
function callbackDataBytes(value) {
  return new TextEncoder().encode(value).length
}

// Валидность одной кнопки в зависимости от типа клавиатуры.
// reply: достаточно текста. inline: текст + РОВНО одно из url / callback_data,
// причём url — валидная ссылка, а callback_data — не длиннее лимита Telegram.
function isButtonValid(btn, type) {
  if (!btn.text.trim()) return false
  if (type === 'reply') return true
  const url = btn.url.trim()
  const cb = btn.callback_data.trim()
  const hasUrl = url.length > 0
  const hasCb = cb.length > 0
  if (hasUrl === hasCb) return false // XOR — ровно одно поле заполнено
  if (hasUrl) return isValidButtonUrl(url)
  return callbackDataBytes(cb) <= CALLBACK_DATA_MAX_BYTES
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
        const btn = buttons[i]
        if (isButtonValid(btn, type)) continue
        const n = i + 1
        if (!btn.text.trim()) return `Кнопка ${n}: укажите текст`
        // Дальше — только inline (reply с текстом уже валиден).
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
      // Тело рассылки — одним JSON-полем `payload` (бэкенд парсит его как
      // NewsletterRequest), бинарный файл — отдельным multipart-полем `file`.
      const hasButtons = this.keyboard.buttons.length > 0
      const body = {
        // mode='all' → пустой фильтр (бэкенд возьмёт всех); 'filter' → search/field.
        filters:
          this.audience.mode === 'filter'
            ? {
                search: this.audience.search.trim() || null,
                field: this.audience.field || null,
              }
            : { search: null, field: null },
        text: this.text.trim() ? this.text : null,
        // use_buttons и buttons включаются только вместе (требование бэкенда).
        use_buttons: hasButtons ? this.keyboard.type.toUpperCase() : null,
        buttons: hasButtons
          ? this.keyboard.buttons.map((b) => {
              if (this.keyboard.type === 'reply') return { text: b.text.trim() }
              const btn = { text: b.text.trim() }
              // У inline-кнопки оставляем лишь заполненный ключ (url ИЛИ callback_data).
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
        this.result = await newsletterApi.send(form)
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
