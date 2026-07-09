import { http } from '@/api/http'

const BASE = '/requisitions'

export const requisitionsApi = {
  list({ page = 1, limit = 10, search = null, status = null, type = null } = {}) {
    const params = { page, limit }
    if (search) params.search = search
    if (status) params.status = status
    if (type) params.type = type
    return http.get(BASE, { params }).then((r) => r.data)
  },
  get(id) {
    return http.get(`${BASE}/${id}`).then((r) => r.data)
  },
  updateStatus(id, { status, admin_comment = null }) {
    return http.patch(`${BASE}/${id}/status`, { status, admin_comment }).then((r) => r.data)
  },
}
