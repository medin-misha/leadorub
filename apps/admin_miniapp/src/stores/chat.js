import { defineStore } from 'pinia'
import { chatApi } from '@/api/chat'
import { extractError } from '@/api/http'

// Интервалы polling. Список диалогов опрашиваем реже, открытый тред — чаще.
const LIST_POLL_MS = 10000
const THREAD_POLL_MS = 4000

export const useChatStore = defineStore('chat', {
  state: () => ({
    conversations: [],
    activeUid: null,
    messages: [],
    search: '',
    loadingList: false,
    loadingThread: false,
    sending: false,
    error: null,
    // Хэндлы setInterval и guard от наложения запросов (нереактивные по смыслу).
    _listTimer: null,
    _threadTimer: null,
    _inFlight: false,
  }),

  getters: {
    activeConversation(state) {
      return (
        state.conversations.find(
          (c) => c.telegram_user_id === state.activeUid,
        ) || null
      )
    },
    // id последнего сообщения треда — точка отсчёта для инкрементального polling.
    lastMessageId(state) {
      return state.messages.length
        ? state.messages[state.messages.length - 1].id
        : null
    },
  },

  actions: {
    async fetchConversations() {
      this.loadingList = true
      try {
        this.conversations = await chatApi.listConversations({
          search: this.search || null,
        })
      } catch (err) {
        this.error = extractError(err)
      } finally {
        this.loadingList = false
      }
    },

    async setSearch(value) {
      this.search = value ?? ''
      await this.fetchConversations()
    },

    async openConversation(uid) {
      if (this.activeUid === uid) return
      // Переключаем диалог: гасим polling предыдущего треда, чтобы интервалы
      // не накапливались.
      this.stopThreadPolling()
      this.activeUid = uid
      this.messages = []
      this.loadingThread = true
      try {
        this.messages = await chatApi.getMessages(uid, { limit: 50 })
        await this.markRead(uid)
      } catch (err) {
        this.error = extractError(err)
      } finally {
        this.loadingThread = false
      }
      this.startThreadPolling()
    },

    closeConversation() {
      this.stopThreadPolling()
      this.activeUid = null
      this.messages = []
    },

    async fetchMessages({ incremental = false } = {}) {
      if (this.activeUid == null) return
      if (this._inFlight) return // не допускаем наложения опросов
      this._inFlight = true
      const uid = this.activeUid
      try {
        if (incremental) {
          const fresh = await chatApi.getMessages(uid, {
            after_id: this.lastMessageId ?? 0,
            limit: 100,
          })
          if (uid !== this.activeUid) return // диалог переключили за время запроса
          if (fresh.length) {
            const known = new Set(this.messages.map((m) => m.id))
            const toAdd = fresh.filter((m) => !known.has(m.id))
            if (toAdd.length) this.messages.push(...toAdd)
            // Новые сообщения пользователя в открытом треде сразу читаем.
            if (toAdd.some((m) => m.direction === 'user')) {
              await this.markRead(uid)
            }
          }
        } else {
          const data = await chatApi.getMessages(uid, { limit: 50 })
          if (uid === this.activeUid) this.messages = data
        }
      } catch (err) {
        this.error = extractError(err)
      } finally {
        this._inFlight = false
      }
    },

    async sendReply(text, file = null) {
      const uid = this.activeUid
      const body = (text ?? '').trim()
      // Нужен текст ИЛИ вложение.
      if (uid == null || (!body && !file)) return
      this.sending = true
      this.error = null
      try {
        const msg = await chatApi.reply(uid, { text: body || null, file })
        if (uid === this.activeUid) this.messages.push(msg)
        // Обновляем превью/порядок диалога в списке.
        await this.fetchConversations()
      } catch (err) {
        this.error = extractError(err)
      } finally {
        this.sending = false
      }
    },

    async markRead(uid) {
      try {
        await chatApi.markRead(uid)
        const conv = this.conversations.find((c) => c.telegram_user_id === uid)
        if (conv) conv.unread_count = 0
      } catch {
        // Пометка прочитанным не критична — молча игнорируем сбой.
      }
    },

    startListPolling() {
      this.stopListPolling()
      this._listTimer = setInterval(() => this.fetchConversations(), LIST_POLL_MS)
    },
    stopListPolling() {
      if (this._listTimer) {
        clearInterval(this._listTimer)
        this._listTimer = null
      }
    },
    startThreadPolling() {
      this.stopThreadPolling()
      this._threadTimer = setInterval(
        () => this.fetchMessages({ incremental: true }),
        THREAD_POLL_MS,
      )
    },
    stopThreadPolling() {
      if (this._threadTimer) {
        clearInterval(this._threadTimer)
        this._threadTimer = null
      }
    },
    stopAllPolling() {
      this.stopListPolling()
      this.stopThreadPolling()
    },
  },
})
