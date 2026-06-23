<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const username = ref('')
const password = ref('')

async function submit() {
  const ok = await auth.login(username.value, password.value)
  if (ok) {
    // Возвращаем на исходный маршрут, если был redirect; иначе на корень.
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    router.replace(redirect)
  }
}
</script>

<template>
  <div class="login">
    <form class="login__card" @submit.prevent="submit">
      <h1 class="login__title">Leadorub Admin</h1>

      <BaseInput v-model="username" label="Логин" placeholder="username" />
      <BaseInput v-model="password" label="Пароль" type="password" placeholder="••••••••" />

      <p v-if="auth.error" class="login__error">{{ auth.error }}</p>

      <BaseButton type="submit" :disabled="auth.loading || !username || !password">
        {{ auth.loading ? 'Входим…' : 'Войти' }}
      </BaseButton>
    </form>
  </div>
</template>

<style scoped>
.login {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4);
}
.login__card {
  width: 100%;
  max-width: 360px;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}
.login__title {
  margin: 0 0 var(--space-2);
  font-size: 20px;
  text-align: center;
}
.login__error {
  margin: 0;
  color: var(--color-danger);
  font-size: 14px;
}
</style>
