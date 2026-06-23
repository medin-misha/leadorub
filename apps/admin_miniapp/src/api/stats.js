import { http } from '@/api/http'

const BASE = '/telegram/stats'

export const statsApi = {
  create(data) {
    return http.post(BASE, data).then((r) => r.data)
  },
  patch(id, data) {
    return http.patch(`${BASE}/${id}`, data).then((r) => r.data)
  },
}
