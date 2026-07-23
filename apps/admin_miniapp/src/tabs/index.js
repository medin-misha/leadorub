// ⭐ Реестр вкладок — единственный источник правды.
// Добавить вкладку = добавить сюда объект + создать view-компонент.
export const tabs = [
  { key: 'users', label: 'Пользователи', component: () => import('@/views/UsersView.vue') },
  { key: 'requisitions', label: 'Заявки', component: () => import('@/views/RequisitionsView.vue') },
  { key: 'newsletter', label: 'Рассылка', component: () => import('@/views/NewsletterView.vue') },
  { key: 'drip', label: 'Автоворонка', component: () => import('@/views/DripNewslettersView.vue') },
  { key: 'admin', label: 'Админы', component: () => import('@/views/AdminView.vue') },
  { key: 'chat', label: 'Чат', component: () => import('@/views/ChatView.vue') },
]
