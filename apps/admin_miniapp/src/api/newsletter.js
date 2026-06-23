import { http } from '@/api/http'

const BASE = '/telegram/newsletter'

export const newsletterApi = {
  // multipart/form-data — axios сам выставит Content-Type с boundary по FormData.
  // Тело: поле `payload` (JSON NewsletterRequest) + опциональный `file`.
  // Ответ: { status, recipients }.
  send(formData) {
    return http.post(BASE, formData).then((r) => r.data)
  },
}
