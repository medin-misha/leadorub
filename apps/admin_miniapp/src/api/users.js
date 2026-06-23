import { http } from '@/api/http'

const BASE = '/telegram/users'

export const usersApi = {
  list({ page = 1, limit = 10, search = null, field = null } = {}) {
    const params = { page, limit }
    if (search) params.search = search
    if (field) params.field = field
    return http.get(BASE, { params }).then((r) => r.data)
  },
  get(id) {
    return http.get(`${BASE}/${id}`).then((r) => r.data)
  },
  create(payload) {
    return http.post(BASE, payload).then((r) => r.data)
  },
  update(id, patch) {
    return http.patch(`${BASE}/${id}`, patch).then((r) => r.data)
  },
  remove(id) {
    return http.delete(`${BASE}/${id}`).then((r) => r.data)
  },
}
