import axios from 'axios'

// Один origin: в dev проксирует Vite, в проде — Caddy. Поэтому baseURL = /api.
export const http = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

// Ключ JWT в localStorage (тот же, что использует auth-стор).
export const TOKEN_KEY = 'admin_token'

// Обработчик 401: регистрируется в рантайме (main.js), чтобы http.js не импортировал
// стор/роутер и не создавал циклов импорта.
let onUnauthorized = null
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn
}

// Запрос: подкладываем Bearer-токен из localStorage, если он есть.
http.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Ответ: на 401 (протух/нет токена) сбрасываем сессию через зарегистрированный хендлер.
http.interceptors.response.use(
  (response) => response,
  (err) => {
    if (err?.response?.status === 401 && onUnauthorized) onUnauthorized()
    return Promise.reject(err)
  },
)

// Достаём человекочитаемое сообщение из ответа backend (DBErrorHandler шлёт detail).
export function extractError(err) {
  return err?.response?.data?.detail || err?.message || 'Неизвестная ошибка'
}
