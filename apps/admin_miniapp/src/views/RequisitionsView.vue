<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useRequisitionsStore } from '@/stores/requisitions'
import Pagination from '@/components/ui/Pagination.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseModal from '@/components/ui/BaseModal.vue'

const store = useRequisitionsStore()
const router = useRouter()

const selectedReq = ref(null)
const adminComment = ref('')
const processingError = ref(null)

onMounted(() => {
  store.fetchRequisitions()
})

const statusOptions = [
  { value: '', label: 'Все статусы' },
  { value: 'pending', label: 'Ожидают' },
  { value: 'in_progress', label: 'В обработке' },
  { value: 'approved', label: 'Одобрены' },
  { value: 'rejected', label: 'Отклонены' },
]

const productOptions = [
  { value: '', label: 'Все продукты' },
  { value: 'consultation', label: 'Консультация' },
  { value: 'community', label: 'В сообщество' },
]

function handleSearch(val) {
  store.setSearch(val)
}

function handleStatusFilter(val) {
  store.setStatus(val)
}

function handleTypeFilter(val) {
  store.setType(val)
}

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('ru-RU')
}

function getProductLabel(type) {
  const map = {
    consultation: 'Консультация 📅',
    community: 'В сообщество 👥',
  }
  return map[type] || type
}

function getStatusLabel(status) {
  const map = {
    pending: 'Ожидает',
    in_progress: 'В обработке',
    approved: 'Одобрена',
    rejected: 'Отклонена',
  }
  return map[status] || status
}

function openDetails(requisition) {
  selectedReq.ref
  selectedReq.value = requisition
  adminComment.value = requisition.admin_comment || ''
  processingError.value = null
}

function closeDetails() {
  selectedReq.value = null
  adminComment.value = ''
  processingError.value = null
}

async function changeStatus(newStatus) {
  if (!selectedReq.value) return
  processingError.value = null
  try {
    const updated = await store.updateStatus(selectedReq.value.id, {
      status: newStatus,
      admin_comment: adminComment.value || null,
    })
    selectedReq.value = updated // Обновляем модалку
    closeDetails()
  } catch (err) {
    processingError.value = 'Не удалось обновить статус заявки.'
  }
}

function openUserChat(telegramUser) {
  if (!telegramUser) return
  router.push({ name: 'chat', query: { userId: telegramUser.id } })
}

// Преобразует payload-ключи в читаемые русские названия
function translateKey(key) {
  const map = {
    name: 'Имя',
    phone: 'Телефон',
    description: 'Описание проблемы',
    experience: 'Соцсети/Опыт',
    motivation: 'Мотивация',
  }
  return map[key] || key
}
</script>

<template>
  <div class="requisitions">
    <!-- Фильтры -->
    <div class="requisitions__filters">
      <BaseInput
        :model-value="store.search"
        placeholder="Поиск по заявкам..."
        class="filter-search"
        @update:model-value="handleSearch"
      />
      <BaseSelect
        :model-value="store.status"
        :options="statusOptions"
        class="filter-select"
        @update:model-value="handleStatusFilter"
      />
      <BaseSelect
        :model-value="store.type"
        :options="productOptions"
        class="filter-select"
        @update:model-value="handleTypeFilter"
      />
    </div>

    <p v-if="store.error" class="requisitions__error">{{ store.error }}</p>

    <!-- Таблица -->
    <div class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Пользователь</th>
            <th>Продукт</th>
            <th>Создана</th>
            <th>Статус</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in store.items" :key="r.id" class="table__row">
            <td>{{ r.id }}</td>
            <td>
              <div class="user-info">
                <span class="user-info__name">
                  {{ [r.telegram_user?.first_name, r.telegram_user?.last_name].filter(Boolean).join(' ') || '—' }}
                </span>
                <span v-if="r.telegram_user?.username" class="user-info__username">
                  @{{ r.telegram_user.username }}
                </span>
              </div>
            </td>
            <td>{{ getProductLabel(r.type) }}</td>
            <td>{{ fmtDate(r.created_at) }}</td>
            <td>
              <span :class="['badge', `badge--${r.status}`]">
                {{ getStatusLabel(r.status) }}
              </span>
            </td>
            <td class="table__actions">
              <BaseButton variant="primary" @click="openDetails(r)">Обработать</BaseButton>
              <BaseButton
                v-if="r.telegram_user"
                variant="ghost"
                @click="openUserChat(r.telegram_user)"
              >
                Чат
              </BaseButton>
            </td>
          </tr>
          <tr v-if="!store.loading && !store.items.length">
            <td colspan="6" class="table__empty">Нет заявок</td>
          </tr>
          <tr v-if="store.loading">
            <td colspan="6" class="table__empty">Загрузка…</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Пагинация -->
    <div class="requisitions__footer">
      <Pagination
        :page="store.page"
        :has-next="store.hasNext"
        :limit="store.limit"
        @update:page="store.setPage"
        @update:limit="store.setLimit"
      />
    </div>

    <!-- Модалка деталей -->
    <BaseModal
      v-if="selectedReq"
      :title="`Заявка #${selectedReq.id} — ${getProductLabel(selectedReq.type)}`"
      @close="closeDetails"
    >
      <div class="details">
        <!-- Информация о пользователе -->
        <section class="details__section">
          <h4>Отправитель</h4>
          <div class="sender-card" v-if="selectedReq.telegram_user">
            <div class="sender-card__info">
              <strong>
                {{ [selectedReq.telegram_user.first_name, selectedReq.telegram_user.last_name].filter(Boolean).join(' ') }}
              </strong>
              <span v-if="selectedReq.telegram_user.username" class="sender-card__username">
                @{{ selectedReq.telegram_user.username }}
              </span>
              <span class="sender-card__id">ID: {{ selectedReq.telegram_user.telegram_id }}</span>
            </div>
            <BaseButton variant="ghost" @click="openUserChat(selectedReq.telegram_user)">
              Открыть чат
            </BaseButton>
          </div>
          <span v-else>Данные пользователя недоступны</span>
        </section>

        <!-- Содержимое заявки (payload) -->
        <section class="details__section">
          <h4>Данные формы</h4>
          <div class="payload-list">
            <div
              v-for="(val, key) in selectedReq.payload"
              :key="key"
              class="payload-item"
            >
              <span class="payload-item__key">{{ translateKey(key) }}:</span>
              <span class="payload-item__val">{{ val }}</span>
            </div>
          </div>
        </section>

        <!-- История обработки -->
        <section class="details__section">
          <h4>Текущий статус</h4>
          <div class="status-summary">
            <span :class="['badge', `badge--${selectedReq.status}`]">
              {{ getStatusLabel(selectedReq.status) }}
            </span>
            <div v-if="selectedReq.admin_comment" class="admin-comment-box">
              <strong>Комментарий администратора:</strong>
              <p>{{ selectedReq.admin_comment }}</p>
            </div>
          </div>
        </section>

        <!-- Форма обработки (только для незавершенных) -->
        <section
          v-if="selectedReq.status === 'pending' || selectedReq.status === 'in_progress'"
          class="details__section details__action-form"
        >
          <h4>Решение администратора</h4>
          <div class="comment-field">
            <label for="admin-comment">Комментарий к решению (увидит пользователь):</label>
            <textarea
              id="admin-comment"
              v-model="adminComment"
              placeholder="Введите комментарий (необязательно)..."
              class="textarea-input"
              maxlength="1024"
            ></textarea>
          </div>

          <p v-if="processingError" class="details__error">{{ processingError }}</p>

          <div class="action-buttons">
            <BaseButton variant="danger" @click="changeStatus('rejected')">Отклонить ❌</BaseButton>
            <BaseButton variant="ghost" @click="changeStatus('in_progress')" v-if="selectedReq.status === 'pending'">
              В обработку ⚙️
            </BaseButton>
            <BaseButton variant="primary" @click="changeStatus('approved')">Одобрить ✔️</BaseButton>
          </div>
        </section>
      </div>
    </BaseModal>
  </div>
</template>

<style scoped>
.requisitions {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.requisitions__filters {
  display: flex;
  gap: var(--space-3);
  align-items: flex-end;
}
.filter-search {
  flex-grow: 1;
}
.filter-select {
  width: 200px;
}
.requisitions__error {
  color: var(--color-danger);
  margin: 0;
}
.requisitions__footer {
  display: flex;
  justify-content: flex-end;
}

/* Таблица */
.table-wrap {
  overflow-x: auto;
  background: var(--color-surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}
.table {
  width: 100%;
  border-collapse: collapse;
}
.table th,
.table td {
  padding: var(--space-3);
  text-align: left;
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}
.table th {
  font-size: 13px;
  color: var(--color-text-muted);
}
.table__row {
  transition: background-color 0.15s ease;
}
.table__row:hover {
  background-color: var(--color-bg);
}
.user-info {
  display: flex;
  flex-direction: column;
}
.user-info__name {
  font-weight: 500;
}
.user-info__username {
  font-size: 12px;
  color: var(--color-text-muted);
}

.table__actions {
  display: flex;
  gap: var(--space-2);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s ease-in-out;
}
.table__row:hover .table__actions {
  opacity: 1;
  pointer-events: auto;
}
.table__empty {
  text-align: center;
  color: var(--color-text-muted);
  padding: var(--space-5);
}

/* Статусные бейджи */
.badge {
  display: inline-block;
  padding: var(--space-1) var(--space-2);
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
}
.badge--pending {
  background-color: #fef3c7;
  color: #d97706;
}
.badge--in_progress {
  background-color: #dbeafe;
  color: #2563eb;
}
.badge--approved {
  background-color: #d1fae5;
  color: #059669;
}
.badge--rejected {
  background-color: #fee2e2;
  color: #dc2626;
}

/* Детали заявки в модалке */
.details {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.details__section {
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--space-3);
}
.details__section:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
.details__section h4 {
  margin: 0 0 var(--space-2) 0;
  font-size: 14px;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.sender-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--color-bg);
  padding: var(--space-3);
  border-radius: var(--radius);
}
.sender-card__info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.sender-card__username {
  font-size: 13px;
  color: var(--color-primary);
}
.sender-card__id {
  font-size: 12px;
  color: var(--color-text-muted);
}

.payload-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.payload-item {
  display: flex;
  flex-direction: column;
  background: var(--color-bg);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius);
}
.payload-item__key {
  font-size: 12px;
  color: var(--color-text-muted);
}
.payload-item__val {
  font-weight: 500;
  white-space: pre-wrap;
}

.admin-comment-box {
  margin-top: var(--space-2);
  padding: var(--space-3);
  background: #f9fafb;
  border-left: 4px solid var(--color-border);
  border-radius: 0 var(--radius) var(--radius) 0;
}
.admin-comment-box p {
  margin: var(--space-1) 0 0 0;
  white-space: pre-wrap;
}

/* Форма действий */
.details__action-form {
  background: #fafafa;
  padding: var(--space-3);
  border-radius: var(--radius);
  border: 1px solid var(--color-border);
}
.comment-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  margin-bottom: var(--space-3);
}
.comment-field label {
  font-size: 13px;
  color: var(--color-text-muted);
}
.textarea-input {
  width: 100%;
  height: 80px;
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font: inherit;
  resize: vertical;
  background: var(--color-surface);
}
.textarea-input:focus {
  outline: none;
  border-color: var(--color-primary);
}
.action-buttons {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
.details__error {
  color: var(--color-danger);
  font-size: 13px;
  margin: 0 0 var(--space-2) 0;
}
</style>
