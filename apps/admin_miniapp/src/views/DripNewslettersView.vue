<script setup>
import { computed, onMounted, ref } from 'vue'
import { useDripNewslettersStore } from '@/stores/dripNewsletters'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import MessageComposer from '@/components/newsletter/MessageComposer.vue'

const store = useDripNewslettersStore()

// Известные состояния воронки — подсказки datalist; можно ввести любое своё.
const KNOWN_STATES = ['persona_start', 'business_start']

const createdNotice = ref(false)

const title = computed({
  get: () => store.title,
  set: (v) => (store.title = v),
})
const triggerState = computed({
  get: () => store.triggerState,
  set: (v) => (store.triggerState = v),
})
const daysOffset = computed({
  get: () => store.daysOffset,
  set: (v) => (store.daysOffset = v),
})
const sendTime = computed({
  get: () => store.sendTime,
  set: (v) => (store.sendTime = v),
})

async function onSubmit() {
  await store.create()
  if (!store.error) {
    createdNotice.value = true
    setTimeout(() => (createdNotice.value = false), 4000)
  }
}

function onDelete(rule) {
  const label = rule.title || `#${rule.id}`
  // Удаление стирает и лог отправок: пересозданное правило может отправить
  // сообщение тем же людям повторно — предупреждаем.
  if (window.confirm(`Удалить правило «${label}»? Лог отправок тоже удалится.`)) {
    store.removeRule(rule.id)
  }
}

function scheduleLabel(rule) {
  const time = rule.send_time?.slice(0, 5) ?? rule.send_time
  if (rule.days_offset === 0) return `в день входа в ${time}`
  return `через ${rule.days_offset} дн. в ${time}`
}

onMounted(() => store.fetchRules())
</script>

<template>
  <div class="drip">
    <p v-if="createdNotice" class="drip__notice">Правило создано ✓</p>
    <p v-if="store.error" class="drip__error">{{ store.error }}</p>

    <div class="drip__cols">
      <!-- Форма создания: триггер + сообщение -->
      <section class="drip__form">
        <div class="drip__trigger">
          <h3 class="drip__title">Триггер</h3>
          <BaseInput v-model="title" label="Название (для списка)" placeholder="Догрев после /start" />
          <label class="drip__field">
            <span class="drip__label">Состояние-триггер</span>
            <input
              v-model="triggerState"
              class="drip__input"
              list="drip-known-states"
              placeholder="persona_start"
            />
            <datalist id="drip-known-states">
              <option v-for="s in KNOWN_STATES" :key="s" :value="s" />
            </datalist>
          </label>
          <BaseInput
            v-model="daysOffset"
            type="number"
            label="Через сколько дней"
            placeholder="1"
          />
          <BaseInput v-model="sendTime" type="time" label="Время отправки" />
          <p class="drip__hint">
            Сообщение придёт через указанное число дней после входа в состояние —
            только тем, кто в нём ещё остаётся, и один раз на пользователя.
          </p>
        </div>

        <MessageComposer :store="store" submit-label="Создать правило" @submit="onSubmit" />
      </section>

      <!-- Список правил -->
      <section class="drip__list">
        <h3 class="drip__title">Правила</h3>
        <p v-if="store.listError" class="drip__error">{{ store.listError }}</p>
        <p v-if="store.loading" class="drip__muted">Загрузка…</p>
        <p v-else-if="!store.rules.length" class="drip__muted">Правил пока нет</p>

        <article v-for="rule in store.rules" :key="rule.id" class="drip__card">
          <div class="drip__card-main">
            <b>{{ rule.title || `Правило #${rule.id}` }}</b>
            <span class="drip__muted">
              {{ rule.trigger_state }} → {{ scheduleLabel(rule) }}
            </span>
            <span class="drip__muted">Отправлено: {{ rule.sent_count }}</span>
          </div>
          <div class="drip__card-actions">
            <span
              class="drip__badge"
              :class="rule.is_active ? 'drip__badge--on' : 'drip__badge--off'"
            >
              {{ rule.is_active ? 'активно' : 'выключено' }}
            </span>
            <BaseButton variant="ghost" @click="store.toggleActive(rule)">
              {{ rule.is_active ? 'Выключить' : 'Включить' }}
            </BaseButton>
            <BaseButton variant="ghost" @click="onDelete(rule)">Удалить</BaseButton>
          </div>
        </article>
      </section>
    </div>
  </div>
</template>

<style scoped>
.drip {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.drip__cols {
  display: flex;
  gap: var(--space-4);
  align-items: flex-start;
  flex-wrap: wrap;
}
.drip__form {
  flex: 1 1 420px;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.drip__list {
  flex: 1 1 380px;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.drip__trigger {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  background: var(--color-surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: var(--space-4);
}
.drip__title {
  margin: 0;
  font-size: 16px;
}
.drip__field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.drip__label {
  font-size: 13px;
  color: var(--color-text-muted);
}
.drip__input {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font: inherit;
}
.drip__input:focus {
  outline: none;
  border-color: var(--color-primary);
}
.drip__hint {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-muted);
}
.drip__card {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  align-items: center;
  flex-wrap: wrap;
  background: var(--color-surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: var(--space-3) var(--space-4);
}
.drip__card-main {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.drip__card-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.drip__badge {
  font-size: 12px;
  padding: 2px var(--space-2);
  border-radius: 999px;
}
.drip__badge--on {
  background: var(--color-success-bg);
  color: var(--color-success);
}
.drip__badge--off {
  background: var(--color-bg);
  color: var(--color-text-muted);
}
.drip__notice {
  margin: 0;
  padding: var(--space-3);
  border-radius: var(--radius);
  background: var(--color-success-bg);
  color: var(--color-success);
}
.drip__error {
  margin: 0;
  color: var(--color-danger);
}
.drip__muted {
  color: var(--color-text-muted);
  font-size: 13px;
  margin: 0;
}
</style>
