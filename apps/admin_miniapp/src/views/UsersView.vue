<script setup>
import { onMounted, ref } from 'vue'
import { useUsersStore } from '@/stores/users'
import UserSearchBar from '@/components/users/UserSearchBar.vue'
import UsersTable from '@/components/users/UsersTable.vue'
import UserEditDialog from '@/components/users/UserEditDialog.vue'
import UserDeleteConfirm from '@/components/users/UserDeleteConfirm.vue'
import UserCreateDialog from '@/components/users/UserCreateDialog.vue'
import Pagination from '@/components/ui/Pagination.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

const store = useUsersStore()

const editing = ref(null)
const deleting = ref(null)
const creating = ref(false)

onMounted(() => store.fetchUsers())

function onSearch({ search, field }) {
  store.setSearch({ search, field })
}
</script>

<template>
  <div class="users">
    <div class="users__toolbar">
      <UserSearchBar @search="onSearch" />
      <BaseButton @click="creating = true">+ Пользователь</BaseButton>
    </div>

    <p v-if="store.error" class="users__error">{{ store.error }}</p>

    <UsersTable
      :items="store.items"
      :loading="store.loading"
      @edit="editing = $event"
      @delete="deleting = $event"
    />

    <div class="users__footer">
      <Pagination
        :page="store.page"
        :has-next="store.hasNext"
        :limit="store.limit"
        @update:page="store.setPage($event)"
        @update:limit="store.setLimit($event)"
      />
    </div>

    <UserEditDialog
      v-if="editing"
      :user="editing"
      @close="editing = null"
      @saved="editing = null"
    />
    <UserDeleteConfirm
      v-if="deleting"
      :user="deleting"
      @close="deleting = null"
      @confirm="deleting = null"
    />
    <UserCreateDialog
      v-if="creating"
      @close="creating = false"
      @created="creating = false"
    />
  </div>
</template>

<style scoped>
.users {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.users__toolbar {
  display: flex;
  gap: var(--space-3);
  align-items: flex-end;
}
.users__error {
  color: var(--color-danger);
  margin: 0;
}
.users__footer {
  display: flex;
  justify-content: flex-end;
}
</style>
