<script setup>
import { ref } from 'vue'
import { useUsersStore } from '@/stores/users'
import { extractError } from '@/api/http'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

const props = defineProps({ user: { type: Object, required: true } })
const emit = defineEmits(['close', 'confirm'])
const store = useUsersStore()

const busy = ref(false)
const error = ref(null)

async function confirm() {
  busy.value = true
  error.value = null
  try {
    await store.deleteUser(props.user.id)
    emit('confirm')
  } catch (err) {
    error.value = extractError(err)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <BaseModal title="Удаление пользователя" @close="emit('close')">
    <p>
      Удалить пользователя <b>#{{ user.id }}</b>
      (telegram_id {{ user.telegram_id }})? Действие необратимо — профиль и
      статистика будут удалены каскадно.
    </p>
    <p v-if="error" class="del__error">{{ error }}</p>

    <template #footer>
      <BaseButton variant="ghost" @click="emit('close')">Отмена</BaseButton>
      <BaseButton variant="danger" :disabled="busy" @click="confirm">
        {{ busy ? 'Удаление…' : 'Удалить' }}
      </BaseButton>
    </template>
  </BaseModal>
</template>

<style scoped>
.del__error {
  color: var(--color-danger);
}
</style>
