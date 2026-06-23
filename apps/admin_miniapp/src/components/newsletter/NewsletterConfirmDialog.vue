<script setup>
import { useNewsletterStore } from '@/stores/newsletter'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

const emit = defineEmits(['close', 'sent'])

const store = useNewsletterStore()

async function confirm() {
  await store.send()
  // send() при ошибке выставит store.error и не очистит сообщение — тогда не закрываем.
  if (!store.error) emit('sent')
}
</script>

<template>
  <BaseModal title="Подтверждение рассылки" @close="emit('close')">
    <div class="confirm">
      <p class="confirm__row"><b>Аудитория:</b> {{ store.audienceLabel }}</p>
      <p class="confirm__row">
        <b>Текст:</b>
        <span v-if="store.text">{{ store.text }}</span>
        <span v-else class="confirm__muted">— без текста —</span>
      </p>
      <p class="confirm__row">
        <b>Вложение:</b>
        <span v-if="store.file">{{ store.file.name }}</span>
        <span v-else class="confirm__muted">— нет —</span>
      </p>
      <p v-if="store.error" class="confirm__error">{{ store.error }}</p>
    </div>

    <template #footer>
      <BaseButton variant="ghost" :disabled="store.sending" @click="emit('close')">
        Отмена
      </BaseButton>
      <BaseButton :disabled="store.sending" @click="confirm">
        {{ store.sending ? 'Отправка…' : 'Разослать' }}
      </BaseButton>
    </template>
  </BaseModal>
</template>

<style scoped>
.confirm {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.confirm__row {
  margin: 0;
  word-break: break-word;
}
.confirm__muted {
  color: var(--color-text-muted);
}
.confirm__error {
  margin: 0;
  color: var(--color-danger);
}
</style>
