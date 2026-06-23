<script setup>
import { reactive, ref } from 'vue'
import { useUsersStore } from '@/stores/users'
import { extractError } from '@/api/http'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

const props = defineProps({ user: { type: Object, required: true } })
const emit = defineEmits(['close', 'saved'])
const store = useUsersStore()

const saving = ref(false)
const error = ref(null)

// Локальные копии, чтобы не мутировать строку таблицы напрямую.
const form = reactive({
  username: props.user.username ?? '',
  first_name: props.user.first_name ?? '',
  last_name: props.user.last_name ?? '',
  language_code: props.user.language_code ?? '',
  is_blocket_bot: !!props.user.is_blocket_bot,
})

const profile = reactive({
  phone: props.user.user_profile?.phone ?? '',
  email: props.user.user_profile?.email ?? '',
  timezone: props.user.user_profile?.timezone ?? '',
  full_name: props.user.user_profile?.full_name ?? '',
  note: props.user.user_profile?.note ?? '',
})

const stats = reactive({
  source: props.user.user_stats?.source ?? '',
  state: props.user.user_stats?.state ?? '',
})

// Пустые строки → null, чтобы не писать "" в nullable-поля.
function nullify(obj) {
  const out = {}
  for (const [k, v] of Object.entries(obj)) out[k] = v === '' ? null : v
  return out
}

async function save() {
  saving.value = true
  error.value = null
  try {
    // 1) Основные поля пользователя
    await store.updateUser(props.user.id, {
      username: form.username || null,
      first_name: form.first_name || null,
      last_name: form.last_name || null,
      language_code: form.language_code || null,
      is_blocket_bot: form.is_blocket_bot,
    })

    // 2) Профиль: PATCH если есть, иначе POST с telegram_user_id
    const profilePayload = nullify(profile)
    if (props.user.user_profile?.id) {
      await store.updateProfile(props.user.user_profile.id, profilePayload)
    } else {
      await store.createProfile({ telegram_user_id: props.user.id, ...profilePayload })
    }

    // 3) Статистика: PATCH если есть, иначе POST
    const statsPayload = nullify(stats)
    if (props.user.user_stats?.id) {
      await store.updateStats(props.user.user_stats.id, statsPayload)
    } else {
      await store.createStats({ telegram_user_id: props.user.id, ...statsPayload })
    }

    await store.fetchUsers()
    emit('saved')
  } catch (err) {
    error.value = extractError(err)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <BaseModal :title="`Пользователь #${user.id}`" @close="emit('close')">
    <div class="form">
      <p class="form__readonly">telegram_id: <b>{{ user.telegram_id }}</b></p>

      <BaseInput v-model="form.username" label="username" />
      <BaseInput v-model="form.first_name" label="Имя" />
      <BaseInput v-model="form.last_name" label="Фамилия" />
      <BaseInput v-model="form.language_code" label="Язык (language_code)" />
      <label class="form__check">
        <input type="checkbox" v-model="form.is_blocket_bot" />
        <span>Бот заблокирован пользователем</span>
      </label>

      <details class="form__section">
        <summary>Профиль</summary>
        <div class="form__group">
          <BaseInput v-model="profile.full_name" label="ФИО" />
          <BaseInput v-model="profile.phone" label="Телефон" />
          <BaseInput v-model="profile.email" label="Email" />
          <BaseInput v-model="profile.timezone" label="Таймзона" />
          <BaseInput v-model="profile.note" label="Заметка" />
        </div>
      </details>

      <details class="form__section">
        <summary>Статистика</summary>
        <div class="form__group">
          <BaseInput v-model="stats.source" label="Источник (source)" />
          <BaseInput v-model="stats.state" label="Состояние (state)" />
        </div>
      </details>

      <p v-if="error" class="form__error">{{ error }}</p>
    </div>

    <template #footer>
      <BaseButton variant="ghost" @click="emit('close')">Отмена</BaseButton>
      <BaseButton :disabled="saving" @click="save">{{ saving ? 'Сохранение…' : 'Сохранить' }}</BaseButton>
    </template>
  </BaseModal>
</template>

<style scoped>
.form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.form__readonly {
  margin: 0;
  color: var(--color-text-muted);
}
.form__check {
  display: flex;
  gap: var(--space-2);
  align-items: center;
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
