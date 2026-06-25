import { http } from '@/api/http'

const BASE = '/chat'

// HTTP-слой вкладки Chat. Сырые запросы — здесь, не в сторе/компонентах.
export const chatApi = {
  // Список диалогов: пользователь + превью последнего сообщения + непрочитанные.
  listConversations({ search = null, page = 1, limit = 50 } = {}) {
    const params = { page, limit }
    if (search) params.search = search
    return http.get(`${BASE}/conversations`, { params }).then((r) => r.data)
  },
  // Сообщения одного диалога. after_id — для инкрементального polling новых.
  getMessages(uid, { after_id = null, limit = 50 } = {}) {
    const params = { limit }
    if (after_id != null) params.after_id = after_id
    return http
      .get(`${BASE}/conversations/${uid}/messages`, { params })
      .then((r) => r.data)
  },
  // Ответ администратора (multipart): текст и/или вложение. Уйдёт пользователю через бота.
  reply(uid, { text = null, file = null } = {}) {
    const form = new FormData()
    if (text) form.append('text', text)
    if (file) form.append('file', file)
    return http
      .post(`${BASE}/conversations/${uid}/reply`, form)
      .then((r) => r.data)
  },
  // Пометить все сообщения пользователя в диалоге прочитанными.
  markRead(uid) {
    return http.post(`${BASE}/conversations/${uid}/read`).then((r) => r.data)
  },
  // Скачивает вложение как blob и отдаёт object URL (auth-заголовок добавит interceptor).
  fileObjectUrl(fileId) {
    return http
      .get(`/files/${fileId}`, { responseType: 'blob' })
      .then((r) => URL.createObjectURL(r.data))
  },
}
