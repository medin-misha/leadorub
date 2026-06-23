import { http } from '@/api/http'

const BASE = '/auth'

export const authApi = {
  // Логин по username/password → { access_token, token_type }.
  login(username, password) {
    return http.post(`${BASE}/login`, { username, password }).then((r) => r.data)
  },
  // Текущий админ по токену.
  me() {
    return http.get(`${BASE}/me`).then((r) => r.data)
  },
  // Управление администраторами.
  listAdmins({ page = 1, limit = 50 } = {}) {
    return http.get(`${BASE}/admins`, { params: { page, limit } }).then((r) => r.data)
  },
  createAdmin(payload) {
    return http.post(`${BASE}/admins`, payload).then((r) => r.data)
  },
  updateAdmin(id, patch) {
    return http.patch(`${BASE}/admins/${id}`, patch).then((r) => r.data)
  },
  removeAdmin(id) {
    return http.delete(`${BASE}/admins/${id}`).then((r) => r.data)
  },
}
