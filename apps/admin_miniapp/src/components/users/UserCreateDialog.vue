<script setup>
import { reactive, ref } from 'vue'
import { useUsersStore } from '@/stores/users'
import { extractError } from '@/api/http'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

const emit = defineEmits(['close', 'created'])
const store = useUsersStore()

const saving = ref(false)
const error = ref(null)

const form = reactive({
  telegram_id: '',
  username: '',
  first_name: '',
  last_name: '',
  language_code: '',
})
const profile = reactive({ full_name: '', phone: '', email: '' })
const stats = reactive({ source: '' })

async function save() {
  if (!form.telegram_id) {
    error.value = 'telegram_id обязателен'
    return
  }
  saving.value = true
  error.value = null
  try {
    // Композитный POST /telegram/users: telegram_user + опц. profile/stats.
    const payload = {
      telegram_user: {
        telegram_id: Number(form.telegram_id),
        username: form.username || null,
        first_name: form.first_name || null,
        last_name: form.last_name || null,
        language_code: form.language_code || null,
      },
      profile: {
        full_name: profile.full_name || null,
        phone: profile.phone || null,
        email: profile.email || null,
      },
      stats: { source: stats.source || null },
    }
    await store.createUser(payload)
    emit('created')
  } catch (err) {
    error.value = extractError(err)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <BaseModal title="Новый пользователь" @close="emit('close')">
    <div class="form">
      <BaseInput v-model="form.telegram_id" type="number" label="telegram_id *" />
      <BaseInput v-model="form.username" label="username" />
      <BaseInput v-model="form.first_name" label="Имя" />
      <BaseInput v-model="form.last_name" label="Фамилия" />
      <BaseInput v-model="form.language_code" label="Язык" />

      <details class="form__section">
        <summary>Профиль</summary>
        <div class="form__group">
          <BaseInput v-model="profile.full_name" label="ФИО" />
          <BaseInput v-model="profile.phone" label="Телефон" />
          <BaseInput v-model="profile.email" label="Email" />
        </div>
      </details>

      <details class="form__section">
        <summary>Статистика</summary>
        <div class="form__group">
          <BaseInput v-model="stats.source" label="Источник" />
        </div>
      </details>

      <p v-if="error" class="form__error">{{ error }}</p>
    </div>

    <template #footer>
      <BaseButton variant="ghost" @click="emit('close')">Отмена</BaseButton>
      <BaseButton :disabled="saving" @click="save">{{ saving ? 'Создание…' : 'Создать' }}</BaseButton>
    </template>
  </BaseModal>
</template>

<style scoped>
.form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.form__section > summary {
  cursor: pointer;
  font-weight: 500;
  padding: var(--space-2) 0;
}
.form__group {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding-top: var(--space-2);
}
.form__error {
  color: var(--color-danger);
  margin: 0;
}
</style>
