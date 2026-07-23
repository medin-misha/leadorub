// Валидация полей триггера капельной рассылки. Вынесена из стора в чистый
// модуль, чтобы покрыть node --test (как newsletterValidation.js).

const TIME_RE = /^([01]\d|2[0-3]):[0-5]\d$/

export function isTriggerStateValid(value) {
  return typeof value === 'string' && value.trim().length > 0 && value.trim().length <= 255
}

export function isDaysOffsetValid(value) {
  // Number('') === 0 — пустой input не должен считаться нулём дней.
  if (typeof value === 'string' && value.trim() === '') return false
  const n = Number(value)
  return Number.isInteger(n) && n >= 0 && n <= 365
}

// <input type="time"> даёт "HH:MM"; строка руками — проверяем формат сами.
export function isSendTimeValid(value) {
  return typeof value === 'string' && TIME_RE.test(value)
}

export function isTriggerValid({ triggerState, daysOffset, sendTime }) {
  return (
    isTriggerStateValid(triggerState) &&
    isDaysOffsetValid(daysOffset) &&
    isSendTimeValid(sendTime)
  )
}
