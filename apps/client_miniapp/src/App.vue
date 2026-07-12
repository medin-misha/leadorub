<script setup>
import { ref, onMounted } from 'vue'

// Инициализация Telegram WebApp
const tg = window.Telegram?.WebApp || null

const types = [
  {
    id: 'individual',
    title: '🧠 Индивидуальная консультация',
    duration: '50 мин',
    desc: 'Глубокий разбор личного запроса: самооценка, тревожность, поиск ориентиров.'
  },
  {
    id: 'family',
    title: '👥 Семейная сессия',
    duration: '90 мин',
    desc: 'Работа в паре: учимся слышать друг друга и конструктивно решать конфликты.'
  },
  {
    id: 'express',
    title: '⚡ Экспресс-сессия',
    duration: '30 мин',
    desc: 'Быстрый фокус на конкретной проблеме и поиск решения здесь и сейчас.'
  }
]

const selectedType = ref('individual')
const name = ref('')
const phone = ref('')
const description = ref('')

const errors = ref({
  name: '',
  phone: ''
})

const isSubmitting = ref(false)
const submitSuccess = ref(false)
const submitError = ref('')

onMounted(() => {
  if (tg) {
    tg.ready()
    tg.expand()
    // Настраиваем цвета шапки Telegram WebApp под наш дизайн
    if (tg.setHeaderColor) {
      tg.setHeaderColor('#131822')
    }
  }
})

function selectType(id) {
  selectedType.value = id
}

function validate() {
  let isValid = true
  errors.value.name = ''
  errors.value.phone = ''

  if (!name.value.trim()) {
    errors.value.name = 'Пожалуйста, введите ваше имя'
    isValid = false
  }

  const phoneClean = phone.value.replace(/\D/g, '')
  if (!phone.value.trim()) {
    errors.value.phone = 'Пожалуйста, введите номер телефона'
    isValid = false
  } else if (phoneClean.length < 7) {
    errors.value.phone = 'Некорректный формат телефона'
    isValid = false
  }

  return isValid
}

async function submitForm() {
  if (!validate()) return

  const initData = tg?.initData
  if (!initData) {
    submitError.value = 'Открой MiniApp через кнопку в Telegram-боте.'
    return
  }

  isSubmitting.value = true
  submitError.value = ''

  const selectedTitle = types.find(t => t.id === selectedType.value)?.title || selectedType.value
  
  const payload = {
    type: 'consultation',
    name: name.value.trim(),
    phone: phone.value.trim(),
    description: `Формат: ${selectedTitle}. Запрос: ${description.value.trim()}`
  }

  try {
    const response = await fetch('/api/requisitions/public', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Telegram-Init-Data': initData
      },
      body: JSON.stringify(payload)
    })

    if (!response.ok) {
      throw new Error('Ошибка сервера при отправке')
    }

    submitSuccess.value = true
    
    // Закрываем приложение через 2.5 секунды
    if (tg) {
      setTimeout(() => {
        tg.close()
      }, 2500)
    }
  } catch (err) {
    console.error(err)
    submitError.value = 'Произошла ошибка при отправке заявки. Пожалуйста, попробуйте позже.'
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="container">
    <header class="header">
      <div class="header__subtitle">Ваш психолог</div>
      <h1 class="header__title">Запись на сессию</h1>
    </header>

    <main class="form-card">
      <div v-if="submitSuccess" class="success-screen">
        <div class="success-icon">✓</div>
        <h2 class="success-title">Заявка отправлена!</h2>
        <p class="success-desc">Спасибо за доверие. Я свяжусь с вами в ближайшее время для подтверждения записи.</p>
      </div>
      
      <template v-else>
        <div class="form-group">
          <label class="section-title">Выберите формат встречи</label>
          <div class="type-grid">
            <div
              v-for="item in types"
              :key="item.id"
              class="type-card"
              :class="{ active: selectedType === item.id }"
              @click="selectType(item.id)"
            >
              <div class="type-card__header">
                <span class="type-card__title">{{ item.title }}</span>
              </div>
              <p class="type-card__desc">{{ item.desc }}</p>
            </div>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label" for="name">Ваше имя *</label>
          <input
            id="name"
            v-model="name"
            type="text"
            class="form-input"
            :class="{ invalid: errors.name }"
            placeholder="Как к вам обращаться?"
            autocomplete="name"
            :disabled="isSubmitting"
          />
          <span v-if="errors.name" class="error-text">{{ errors.name }}</span>
        </div>

        <div class="form-group">
          <label class="form-label" for="phone">Номер телефона *</label>
          <input
            id="phone"
            v-model="phone"
            type="tel"
            class="form-input"
            :class="{ invalid: errors.phone }"
            placeholder="+7 (___) ___-__-__"
            autocomplete="tel"
            :disabled="isSubmitting"
          />
          <span v-if="errors.phone" class="error-text">{{ errors.phone }}</span>
        </div>

        <div class="form-group">
          <label class="form-label" for="desc">С каким вопросом обращаетесь? (необязательно)</label>
          <textarea
            id="desc"
            v-model="description"
            class="form-textarea"
            placeholder="Кратко опишите вашу цель или проблему, которую хотите обсудить..."
            rows="3"
            :disabled="isSubmitting"
          ></textarea>
        </div>

        <div v-if="submitError" class="error-banner">
          {{ submitError }}
        </div>

        <button class="submit-btn" :disabled="isSubmitting" @click="submitForm">
          {{ isSubmitting ? 'Отправка...' : 'Подтвердить запись' }}
        </button>
      </template>
    </main>
  </div>
</template>
