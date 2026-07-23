import { http } from '@/api/http'

const BASE = '/telegram/drip-newsletters'

export const dripNewslettersApi = {
  // Список правил. Ответ: DripNewsletterRead[] (с sent_count).
  list(params) {
    return http.get(BASE, { params }).then((r) => r.data)
  },
  // multipart: поле `payload` (JSON DripNewsletterCreate) + опциональный `file`.
  create(formData) {
    return http.post(BASE, formData).then((r) => r.data)
  },
  // Правка только title / is_active (контент правила в v1 не редактируется).
  patch(id, body) {
    return http.patch(`${BASE}/${id}`, body).then((r) => r.data)
  },
  remove(id) {
    return http.delete(`${BASE}/${id}`).then((r) => r.data)
  },
}
