<script setup>
import { onMounted, reactive, ref } from 'vue'

const tg = window.Telegram?.WebApp || null

const form = reactive({
  name: '',
  sources: '',
  comment: ''
})
const errors = reactive({})
const isSubmitting = ref(false)
const submitSuccess = ref(false)
const submitError = ref('')

function clearErrors() {
  Object.keys(errors).forEach((key) => delete errors[key])
}

function validateForm() {
  clearErrors()

  if (!form.name.trim()) errors.name = 'Укажите, как к вам обращаться'
  if (!form.sources.trim()) errors.sources = 'Укажите хотя бы один источник — ссылку, домен или название площадки'

  return Object.keys(errors).length === 0
}

// Контракт backend не меняем: источники и комментарий упаковываем в description.
function buildDescription() {
  return [
    `Источники: ${form.sources.trim()}`,
    `Комментарий: ${form.comment.trim() || 'Не указан'}`
  ].join('\n')
}

async function submitForm() {
  if (!validateForm() || isSubmitting.value) return

  const initData = tg?.initData
  if (!initData) {
    submitError.value = 'Откройте MiniApp через кнопку в Telegram-боте.'
    return
  }

  isSubmitting.value = true
  submitError.value = ''

  try {
    const response = await fetch('/api/requisitions/public', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Telegram-Init-Data': initData
      },
      body: JSON.stringify({
        type: 'consultation',
        name: form.name.trim(),
        // Backend пока требует этот ключ, хотя Mini App больше не собирает телефон.
        phone: '',
        description: buildDescription()
      })
    })

    if (!response.ok) throw new Error(`Request failed with status ${response.status}`)

    submitSuccess.value = true
  } catch (error) {
    console.error('Removal request failed', error)
    submitError.value = 'Не удалось отправить заявку. Проверьте связь и попробуйте ещё раз.'
  } finally {
    isSubmitting.value = false
  }
}

function closeMiniApp() {
  tg?.close()
}

onMounted(() => {
  tg?.ready()
  tg?.expand()
  tg?.setHeaderColor?.('#150823')
  tg?.setBackgroundColor?.('#150823')
})
</script>

<template>
  <div class="app-shell">
    <div class="retro-bg" aria-hidden="true">
      <div class="scanlines"></div>
      <div class="glitch-bar glitch-bar--1"></div>
      <div class="glitch-bar glitch-bar--2"></div>
      <div class="glitch-bar glitch-bar--3"></div>
      <div class="glitch-bar glitch-bar--4"></div>
    </div>

    <header class="brand-header">
      <div class="brand-mark glitch-text" data-text="DMCA GUARDIAN_">DMCA GUARDIAN_</div>
      <div class="brand-badge"><span class="brand-dot"></span>Удаление слитых данных</div>
    </header>

    <main class="request-card">
      <div v-if="submitSuccess" class="success-screen">
        <div class="success-code">STATUS / ACCEPTED</div>
        <div class="success-icon">✓</div>
        <h1>Заявка принята</h1>
        <p>Менеджер изучит указанные источники и свяжется с вами в Telegram, чтобы согласовать удаление.</p>

        <div class="summary-card">
          <div><span>Имя</span><strong>{{ form.name }}</strong></div>
          <div><span>Источники</span><strong>{{ form.sources }}</strong></div>
          <div v-if="form.comment.trim()"><span>Комментарий</span><strong>{{ form.comment }}</strong></div>
        </div>

        <button class="primary-button" type="button" @click="closeMiniApp">Вернуться в Telegram</button>
      </div>

      <template v-else>
        <div class="card-head">
          <span>REQUEST / 48H</span>
          <span>БЕСПЛАТНЫЙ РАЗБОР</span>
        </div>

        <section class="step-panel">
          <p class="eyebrow">Заявка на удаление</p>
          <h1>Где утекли ваши данные?</h1>
          <p class="lead">
            Перечислите площадки, где появился слитый контент, — менеджер проверит их до созвона
            и предложит план удаления.
          </p>

          <label class="field full">
            <span>Ваше имя *</span>
            <input
              v-model="form.name"
              type="text"
              autocomplete="name"
              placeholder="Как к вам обращаться?"
              :class="{ invalid: errors.name }"
            >
            <small v-if="errors.name">{{ errors.name }}</small>
          </label>

          <label class="field full">
            <span>Источники *</span>
            <textarea
              v-model="form.sources"
              rows="4"
              placeholder="Ссылки, домены или названия площадок — сайты, Telegram-каналы, форумы. Каждый источник с новой строки."
              :class="{ invalid: errors.sources }"
            ></textarea>
            <small v-if="errors.sources">{{ errors.sources }}</small>
          </label>

          <label class="field full">
            <span>Комментарий</span>
            <textarea
              v-model="form.comment"
              rows="3"
              placeholder="Что именно утекло, как давно, что уже пробовали — любые детали, которые помогут."
            ></textarea>
          </label>

          <div v-if="submitError" class="error-banner">{{ submitError }}</div>
          <p class="privacy-note">Отправляя заявку, вы соглашаетесь на обработку указанных данных.</p>
          <button class="primary-button" type="button" :disabled="isSubmitting" @click="submitForm">
            {{ isSubmitting ? 'Отправка...' : 'Отправить заявку' }} <span v-if="!isSubmitting">→</span>
          </button>
        </section>
      </template>
    </main>
  </div>
</template>
