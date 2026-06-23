import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from '@/router'
import App from '@/App.vue'
import { setUnauthorizedHandler } from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import '@/styles/tokens.css'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(router)

// Сессия и 401: при протухшем/невалидном токене сбрасываем стор и уводим на /login.
const auth = useAuthStore(pinia)
setUnauthorizedHandler(() => {
  auth.logout()
  if (router.currentRoute.value.name !== 'login') {
    router.push({ name: 'login' })
  }
})

// Если токен уже есть — подтягиваем профиль (заодно валидируем токен: при 401 сработает хендлер).
if (auth.isAuthenticated) {
  auth.fetchMe().catch(() => {})
}

app.mount('#app')
