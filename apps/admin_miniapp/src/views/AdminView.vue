<script setup>
import { computed, onMounted, ref } from 'vue'
import { authApi } from '@/api/auth'
import { extractError } from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import Pagination from '@/components/ui/Pagination.vue'

const auth = useAuthStore()

const items = ref([])
const page = ref(1)
const limit = ref(20)
const loading = ref(false)
const error = ref(null)
const hasNext = computed(() => items.value.length === limit.value)

// id текущего админа — чтобы запретить действия над самим собой в UI.
const selfId = computed(() => auth.admin?.id ?? null)

async function fetchAdmins() {
  loading.value = true
  error.value = null
  try {
    items.value = await authApi.listAdmins({ page: page.value, limit: limit.value })
  } catch (err) {
    error.value = extractError(err)
    items.value = []
  } finally {
    loading.value = false
  }
}

function setPage(next) {
  page.value = Math.max(1, next)
  fetchAdmins()
}
function setLimit(next) {
  limit.value = Math.max(1, next)
  page.value = 1
  fetchAdmins()
}

// --- Создание администратора ---
const createOpen = ref(false)
const createForm = ref({ username: '', password: '' })
const createError = ref(null)
const createBusy = ref(false)

function openCreate() {
  createForm.value = { username: '', password: '' }
  createError.value = null
  createOpen.value = true
}
async function submitCreate() {
  createBusy.value = true
  createError.value = null
  try {
    await authApi.createAdmin({ ...createForm.value })
    createOpen.value = false
    await fetchAdmins()
  } catch (err) {
    createError.value = extractError(err)
  } finally {
    createBusy.value = false
  }
}

// --- Смена пароля ---
const passwordOpen = ref(false)
const passwordTarget = ref(null)
const newPassword = ref('')
const passwordError = ref(null)
const passwordBusy = ref(false)

function openPassword(admin) {
  passwordTarget.value = admin
  newPassword.value = ''
  passwordError.value = null
  passwordOpen.value = true
}
async function submitPassword() {
  passwordBusy.value = true
  passwordError.value = null
  try {
    await authApi.updateAdmin(passwordTarget.value.id, { password: newPassword.value })
    passwordOpen.value = false
    await fetchAdmins()
  } catch (err) {
    passwordError.value = extractError(err)
  } finally {
    passwordBusy.value = false
  }
}

// --- Активность ---
async function toggleActive(admin) {
  error.value = null
  try {
    await authApi.updateAdmin(admin.id, { is_active: !admin.is_active })
    await fetchAdmins()
  } catch (err) {
    error.value = extractError(err)
  }
}

// --- Удаление ---
const deleteTarget = ref(null)
const deleteBusy = ref(false)

async function confirmDelete() {
  deleteBusy.value = true
  error.value = null
  try {
    await authApi.removeAdmin(deleteTarget.value.id)
    deleteTarget.value = null
    await fetchAdmins()
  } catch (err) {
    error.value = extractError(err)
  } finally {
    deleteBusy.value = false
  }
}

onMounted(fetchAdmins)
</script>

<template>
  <section class="admins">
    <header class="admins__bar">
      <h2 class="admins__title">Администраторы</h2>
      <BaseButton @click="openCreate">+ Создать админа</BaseButton>
    </header>

    <p v-if="error" class="admins__error">{{ error }}</p>

    <table class="admins__table">
      <thead>
        <tr>
          <th>ID</th>
          <th>Логин</th>
          <th>Статус</th>
          <th>Действия</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="admin in items" :key="admin.id">
          <td>{{ admin.id }}</td>
          <td>
            {{ admin.username }}
            <span v-if="admin.id === selfId" class="admins__self">(вы)</span>
          </td>
          <td>
            <span :class="['badge', admin.is_active ? 'badge--on' : 'badge--off']">
              {{ admin.is_active ? 'активен' : 'выключен' }}
            </span>
          </td>
          <td class="admins__actions">
            <BaseButton variant="ghost" @click="openPassword(admin)">Пароль</BaseButton>
            <BaseButton
              variant="ghost"
              :disabled="admin.id === selfId"
              @click="toggleActive(admin)"
            >
              {{ admin.is_active ? 'Выключить' : 'Включить' }}
            </BaseButton>
            <BaseButton
              variant="danger"
              :disabled="admin.id === selfId"
              @click="deleteTarget = admin"
            >
              Удалить
            </BaseButton>
          </td>
        </tr>
        <tr v-if="!loading && !items.length">
          <td colspan="4" class="admins__empty">Администраторов нет</td>
        </tr>
      </tbody>
    </table>

    <Pagination
      :page="page"
      :has-next="hasNext"
      :limit="limit"
      @update:page="setPage"
      @update:limit="setLimit"
    />

    <!-- Создание -->
    <BaseModal v-if="createOpen" title="Новый администратор" @close="createOpen = false">
      <div class="form">
        <BaseInput v-model="createForm.username" label="Логин" placeholder="username" />
        <BaseInput
          v-model="createForm.password"
          label="Пароль"
          type="password"
          placeholder="мин. 6 символов"
        />
        <p v-if="createError" class="admins__error">{{ createError }}</p>
      </div>
      <template #footer>
        <BaseButton variant="ghost" @click="createOpen = false">Отмена</BaseButton>
        <BaseButton
          :disabled="createBusy || !createForm.username || createForm.password.length < 6"
          @click="submitCreate"
        >
          Создать
        </BaseButton>
      </template>
    </BaseModal>

    <!-- Смена пароля -->
    <BaseModal v-if="passwordOpen" title="Смена пароля" @close="passwordOpen = false">
      <div class="form">
        <p class="admins__hint">Новый пароль для «{{ passwordTarget?.username }}»</p>
        <BaseInput
          v-model="newPassword"
          label="Пароль"
          type="password"
          placeholder="мин. 6 символов"
        />
        <p v-if="passwordError" class="admins__error">{{ passwordError }}</p>
      </div>
      <template #footer>
        <BaseButton variant="ghost" @click="passwordOpen = false">Отмена</BaseButton>
        <BaseButton :disabled="passwordBusy || newPassword.length < 6" @click="submitPassword">
          Сохранить
        </BaseButton>
      </template>
    </BaseModal>

    <!-- Удаление -->
    <BaseModal v-if="deleteTarget" title="Удалить администратора?" @close="deleteTarget = null">
      <p>Администратор «{{ deleteTarget.username }}» будет удалён без возможности восстановления.</p>
      <template #footer>
        <BaseButton variant="ghost" @click="deleteTarget = null">Отмена</BaseButton>
        <BaseButton variant="danger" :disabled="deleteBusy" @click="confirmDelete">
          Удалить
        </BaseButton>
      </template>
    </BaseModal>
  </section>
</template>

<style scoped>
.admins {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.admins__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.admins__title {
  margin: 0;
  font-size: 18px;
}
.admins__error {
  margin: 0;
  color: var(--color-danger);
  font-size: 14px;
}
.admins__table {
  width: 100%;
  border-collapse: collapse;
}
.admins__table th,
.admins__table td {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--color-border);
  text-align: left;
}
.admins__actions {
  display: flex;
  gap: var(--space-2);
}
.admins__self {
  color: var(--color-text-muted);
  font-size: 13px;
}
.admins__empty {
  text-align: center;
  color: var(--color-text-muted);
}
.admins__hint {
  margin: 0 0 var(--space-2);
  color: var(--color-text-muted);
  font-size: 14px;
}
.form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.badge {
  padding: 2px 8px;
  border-radius: var(--radius);
  font-size: 13px;
}
.badge--on {
  background: rgba(34, 197, 94, 0.15);
  color: #15803d;
}
.badge--off {
  background: rgba(148, 163, 184, 0.2);
  color: var(--color-text-muted);
}
</style>
