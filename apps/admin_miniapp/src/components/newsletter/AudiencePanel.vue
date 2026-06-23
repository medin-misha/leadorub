<script setup>
import { ref, watch } from 'vue'
import { useNewsletterStore } from '@/stores/newsletter'
import UserSearchBar from '@/components/users/UserSearchBar.vue'

const store = useNewsletterStore()

// Локальное состояние панели, инициализируем из стора.
const mode = ref(store.audience.mode) // 'all' | 'filter'
const search = ref(store.audience.search)
const field = ref(store.audience.field)

// Любое изменение режима/фильтра синхронизируем в стор.
watch([mode, search, field], () => {
  store.setAudience({ mode: mode.value, search: search.value, field: field.value })
})

// При выходе из режима «по фильтру» сбрасываем локальный фильтр,
// чтобы при повторном входе он совпадал с (пустым) UserSearchBar.
watch(mode, (m) => {
  if (m === 'all') {
    search.value = ''
    field.value = ''
  }
})

// UserSearchBar уже дебаунсит и отдаёт { search, field }.
function onSearch({ search: s, field: f }) {
  search.value = s
  field.value = f
}
</script>

<template>
  <aside class="audience">
    <h3 class="audience__title">Аудитория</h3>

    <label class="audience__radio">
      <input v-model="mode" type="radio" value="all" />
      <span>Отправить всем</span>
    </label>

    <label class="audience__radio">
      <input v-model="mode" type="radio" value="filter" />
      <span>По фильтру</span>
    </label>

    <div v-if="mode === 'filter'" class="audience__filter">
      <UserSearchBar @search="onSearch" />
    </div>
  </aside>
</template>

<style scoped>
.audience {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  background: var(--color-surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: var(--space-4);
}
.audience__title {
  margin: 0;
  font-size: 16px;
}
.audience__radio {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
}
.audience__filter {
  margin-top: var(--space-2);
}
</style>
