import { http } from '@/api/http'

const BASE = '/telegram/newsletter'

export const newsletterApi = {
  // multipart/form-data — axios сам выставит Content-Type с boundary по FormData.
  // ВНИМАНИЕ: бэкенд этого эндпоинта ещё нет. Модуль готов, но из стора пока не вызывается.
  send(formData) {
    return http.post(BASE, formData).then((r) => r.data)
  },
}
