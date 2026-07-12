<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'

const tg = window.Telegram?.WebApp || null

const goals = [
  {
    id: 'fat_loss',
    icon: '🔥',
    title: 'Сжечь жир',
    description: 'Снизить вес, убрать живот и выстроить питание без срывов.'
  },
  {
    id: 'muscle_gain',
    icon: '💪',
    title: 'Набрать мышцы',
    description: 'Получить систему тренировок и питания для роста массы.'
  },
  {
    id: 'strength',
    icon: '⚡',
    title: 'Стать сильнее',
    description: 'Повысить силовые показатели и общую выносливость.'
  }
]

const experienceOptions = [
  { value: 'none', label: 'Не тренировался' },
  { value: 'under_year', label: 'До года' },
  { value: 'one_to_three', label: '1–3 года' },
  { value: 'over_three', label: 'Более 3 лет' }
]

const step = ref(1)
const selectedGoal = ref('')
const form = reactive({
  age: '',
  height: '',
  weight: '',
  experience: '',
  name: '',
  obstacles: '',
  limitations: ''
})
const errors = reactive({})
const isSubmitting = ref(false)
const submitSuccess = ref(false)
const submitError = ref('')

const currentGoal = computed(() => goals.find((goal) => goal.id === selectedGoal.value))
const currentExperience = computed(
  () => experienceOptions.find((option) => option.value === form.experience)?.label || 'Не указан'
)

function selectGoal(goalId) {
  selectedGoal.value = goalId
  delete errors.goal
}

function clearErrors() {
  Object.keys(errors).forEach((key) => delete errors[key])
}

function validateStep() {
  clearErrors()

  if (step.value === 1 && !selectedGoal.value) {
    errors.goal = 'Выбери главную цель'
  }

  if (step.value === 2) {
    const age = Number(form.age)
    const height = Number(form.height)
    const weight = Number(form.weight)

    if (!form.age || age < 14 || age > 100) errors.age = 'Укажи возраст от 14 до 100 лет'
    if (!form.height || height < 100 || height > 250) errors.height = 'Укажи рост от 100 до 250 см'
    if (!form.weight || weight < 30 || weight > 350) errors.weight = 'Укажи вес от 30 до 350 кг'
    if (!form.experience) errors.experience = 'Выбери опыт тренировок'
  }

  if (step.value === 3) {
    if (!form.name.trim()) errors.name = 'Укажи, как к тебе обращаться'
  }

  return Object.keys(errors).length === 0
}

function nextStep() {
  if (!validateStep()) return
  step.value += 1
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function previousStep() {
  if (step.value <= 1 || isSubmitting.value) return
  step.value -= 1
  clearErrors()
  submitError.value = ''
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function buildDescription() {
  return [
    `Цель: ${currentGoal.value?.title || 'Не указана'}`,
    `Возраст: ${form.age} лет`,
    `Рост: ${form.height} см`,
    `Вес: ${form.weight} кг`,
    `Опыт: ${currentExperience.value}`,
    `Что мешает: ${form.obstacles.trim() || 'Не указано'}`,
    `Травмы и ограничения: ${form.limitations.trim() || 'Нет'}`
  ].join('\n')
}

async function submitForm() {
  if (!validateStep() || isSubmitting.value) return

  const initData = tg?.initData
  if (!initData) {
    submitError.value = 'Открой MiniApp через кнопку в Telegram-боте.'
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
    tg?.BackButton?.hide()
  } catch (error) {
    console.error('Consultation request failed', error)
    submitError.value = 'Не удалось отправить заявку. Проверь связь и попробуй ещё раз.'
  } finally {
    isSubmitting.value = false
  }
}

function closeMiniApp() {
  tg?.close()
}

watch(step, (currentStep) => {
  if (!tg?.BackButton) return
  if (currentStep > 1 && !submitSuccess.value) tg.BackButton.show()
  else tg.BackButton.hide()
})

onMounted(() => {
  tg?.ready()
  tg?.expand()
  tg?.setHeaderColor?.('#090b0e')
  tg?.setBackgroundColor?.('#090b0e')
  tg?.BackButton?.onClick(previousStep)
})

onBeforeUnmount(() => tg?.BackButton?.offClick(previousStep))
</script>

<template>
  <div class="app-shell">
    <div class="grid-glow" aria-hidden="true"></div>

    <header class="brand-header">
      <div class="brand-mark"><span>TOЧKA</span><span>СБОРКИ<span class="brand-cursor">_</span></span></div>
      <div class="coach-badge"><span class="coach-dot"></span>Эрнест · 30+ лет практики</div>
    </header>

    <main class="consultation-card">
      <div v-if="submitSuccess" class="success-screen">
        <div class="success-code">STATUS / ACCEPTED</div>
        <div class="success-icon">✓</div>
        <h1>Заявка принята</h1>
        <p>Эрнест изучит твои данные и свяжется с тобой, чтобы согласовать консультацию.</p>

        <div class="summary-card">
          <div><span>Цель</span><strong>{{ currentGoal?.title }}</strong></div>
          <div><span>Параметры</span><strong>{{ form.height }} см / {{ form.weight }} кг</strong></div>
          <div><span>Опыт</span><strong>{{ currentExperience }}</strong></div>
        </div>

        <button class="primary-button" type="button" @click="closeMiniApp">Вернуться в Telegram</button>
      </div>

      <template v-else>
        <div class="progress-head">
          <span>0{{ step }} / 03</span>
          <span>{{ step === 1 ? 'ЦЕЛЬ' : step === 2 ? 'ПАРАМЕТРЫ' : 'КОНТАКТ' }}</span>
        </div>
        <div class="progress-track"><span :style="{ width: `${step * 33.333}%` }"></span></div>

        <section v-if="step === 1" class="step-panel">
          <p class="eyebrow">Персональная стратегия</p>
          <h1>С чего начнём твою трансформацию?</h1>
          <p class="lead">Выбери главную цель. На консультации мы разберём текущую форму и составим план.</p>

          <div class="goal-list">
            <button
              v-for="goal in goals"
              :key="goal.id"
              type="button"
              class="goal-card"
              :class="{ selected: selectedGoal === goal.id }"
              @click="selectGoal(goal.id)"
            >
              <span class="goal-icon">{{ goal.icon }}</span>
              <span class="goal-copy"><strong>{{ goal.title }}</strong><small>{{ goal.description }}</small></span>
              <span class="goal-arrow">→</span>
            </button>
          </div>
          <p v-if="errors.goal" class="field-error">{{ errors.goal }}</p>
          <button class="primary-button" type="button" @click="nextStep">Продолжить <span>→</span></button>
        </section>

        <section v-else-if="step === 2" class="step-panel">
          <p class="eyebrow">Исходные данные</p>
          <h1>Фиксируем точку старта</h1>
          <p class="lead">Эти параметры помогут заранее оценить твою ситуацию.</p>

          <div class="metrics-grid">
            <label class="field"><span>Возраст</span><div class="unit-input"><input v-model="form.age" inputmode="numeric" type="number" min="14" max="100" placeholder="30"><b>лет</b></div><small v-if="errors.age">{{ errors.age }}</small></label>
            <label class="field"><span>Рост</span><div class="unit-input"><input v-model="form.height" inputmode="numeric" type="number" min="100" max="250" placeholder="180"><b>см</b></div><small v-if="errors.height">{{ errors.height }}</small></label>
            <label class="field"><span>Вес</span><div class="unit-input"><input v-model="form.weight" inputmode="decimal" type="number" min="30" max="350" step="0.1" placeholder="85"><b>кг</b></div><small v-if="errors.weight">{{ errors.weight }}</small></label>
          </div>

          <fieldset class="experience-field">
            <legend>Опыт тренировок</legend>
            <div class="choice-grid">
              <button v-for="option in experienceOptions" :key="option.value" type="button" :class="{ selected: form.experience === option.value }" @click="form.experience = option.value; delete errors.experience">{{ option.label }}</button>
            </div>
            <small v-if="errors.experience" class="field-error">{{ errors.experience }}</small>
          </fieldset>

          <div class="button-row"><button class="secondary-button" type="button" @click="previousStep">←</button><button class="primary-button" type="button" @click="nextStep">Продолжить <span>→</span></button></div>
        </section>

        <section v-else class="step-panel">
          <p class="eyebrow">Последний шаг</p>
          <h1>Оставь контакты</h1>
          <p class="lead">Кратко опиши ситуацию — Эрнест изучит её до звонка.</p>

          <label class="field full"><span>Твоё имя *</span><input v-model="form.name" type="text" autocomplete="name" placeholder="Как к тебе обращаться?" :class="{ invalid: errors.name }"><small v-if="errors.name">{{ errors.name }}</small></label>
          <label class="field full"><span>Что сейчас мешает получить результат?</span><textarea v-model="form.obstacles" rows="3" placeholder="Например: не хватает системы, срываюсь в питании..."></textarea></label>
          <label class="field full"><span>Травмы или ограничения</span><textarea v-model="form.limitations" rows="2" placeholder="Если нет — оставь поле пустым"></textarea></label>

          <div v-if="submitError" class="error-banner">{{ submitError }}</div>
          <p class="privacy-note">Отправляя заявку, ты соглашаешься на обработку указанных данных.</p>
          <div class="button-row"><button class="secondary-button" type="button" :disabled="isSubmitting" @click="previousStep">←</button><button class="primary-button" type="button" :disabled="isSubmitting" @click="submitForm">{{ isSubmitting ? 'Отправка...' : 'Отправить заявку' }} <span v-if="!isSubmitting">→</span></button></div>
        </section>
      </template>
    </main>
  </div>
</template>
