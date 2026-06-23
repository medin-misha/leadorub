import { createRouter, createWebHistory } from 'vue-router'
import { tabs } from '@/tabs'
import { useAuthStore } from '@/stores/auth'

// Роуты строятся из реестра вкладок: /{key} → lazy-компонент вкладки.
// Все вкладки требуют авторизации; /login — публичный.
const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true },
  },
  { path: '/', redirect: `/${tabs[0].key}` },
  ...tabs.map((tab) => ({
    path: `/${tab.key}`,
    name: tab.key,
    component: tab.component,
  })),
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Гейт: на защищённый маршрут без токена — редирект на /login (с возвратным redirect).
router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.public) {
    // Залогиненного со страницы логина уводим внутрь.
    if (to.name === 'login' && auth.isAuthenticated) return { path: '/' }
    return true
  }
  if (!auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router
