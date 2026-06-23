import { http } from '@/api/http'

const BASE = '/telegram/profile'

export const profilesApi = {
  create(data) {
    return http.post(BASE, data).then((r) => r.data)
  },
  patch(id, data) {
    return http.patch(`${BASE}/${id}`, data).then((r) => r.data)
  },
}
