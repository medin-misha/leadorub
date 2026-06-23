<script setup>
import { ref, watch } from 'vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'

const emit = defineEmits(['search'])

// '' = полнотекстовый поиск; иначе точное поле модели TelegramUser.
const fieldOptions = [
  { value: '', label: 'Везде' },
  { value: 'telegram_id', label: 'telegram_id' },
  { value: 'username', label: 'username' },
  { value: 'first_name', label: 'first_name' },
  { value: 'last_name', label: 'last_name' },
  { value: 'language_code', label: 'language_code' },
]

const search = ref('')
const field = ref('')
let timer = null

// Debounce: не дёргаем backend на каждый символ.
watch([search, field], () => {
  clearTimeout(timer)
  timer = setTimeout(() => {
    emit('search', { search: search.value.trim(), field: field.value })
  }, 300)
})
</script>

<template>
  <div class="searchbar">
    <BaseInput v-model="search" placeholder="Поиск пользователей…" class="searchbar__input" />
    <BaseSelect v-model="field" :options="fieldOptions" />
  </div>
</template>

<style scoped>
.searchbar {
  display: flex;
  gap: var(--space-2);
  align-items: flex-end;
}
.searchbar__input {
  flex: 1;
}
</style>
