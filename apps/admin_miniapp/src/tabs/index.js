// ⭐ Реестр вкладок — единственный источник правды.
// Добавить вкладку = добавить сюда объект + создать view-компонент.
export const tabs = [
  { key: 'users', label: 'Users', component: () => import('@/views/UsersView.vue') },
  { key: 'newsletter', label: 'Newsletter', component: () => import('@/views/NewsletterView.vue') },
  { key: 'admin', label: 'Admin', component: () => import('@/views/AdminView.vue') },
  { key: 'chat', label: 'Chat', component: () => import('@/views/ChatView.vue') },
]
