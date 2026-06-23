<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import TabBar from '@/components/layout/TabBar.vue'

const auth = useAuthStore()
const router = useRouter()

function logout() {
  auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="app">
    <header class="app__header">
      <span class="app__brand">Leadorub Admin</span>
      <div v-if="auth.isAuthenticated" class="app__user">
        <span v-if="auth.admin" class="app__username">{{ auth.admin.username }}</span>
        <button class="app__logout" @click="logout">Выйти</button>
      </div>
    </header>
    <TabBar v-if="auth.isAuthenticated" />
    <main class="app__main">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.app__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  font-weight: 700;
}
.app__user {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-weight: 400;
}
.app__username {
  color: var(--color-text-muted);
  font-size: 14px;
}
.app__logout {
  padding: var(--space-1) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  background: var(--color-surface);
  cursor: pointer;
  font: inherit;
}
.app__logout:hover {
  background: var(--color-bg);
}
.app__main {
  flex: 1;
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  padding: var(--space-4);
}
</style>
