import { CALLBACK_DATA_MAX_BYTES } from '../constants.js'

const URL_SCHEMES = ['http:', 'https:', 'tg:']
const IPV4_RE = /^(\d{1,3}\.){3}\d{1,3}$/

function isValidHttpHost(hostname) {
  if (!hostname) return false
  if (IPV4_RE.test(hostname)) return true
  const labels = hostname.split('.')
  return labels.length >= 2 && labels.every(Boolean) && labels.at(-1).length >= 2
}

export function isValidButtonUrl(value) {
  try {
    const parsed = new URL(value)
    if (!URL_SCHEMES.includes(parsed.protocol)) return false
    return parsed.protocol === 'tg:' || isValidHttpHost(parsed.hostname)
  } catch {
    return false
  }
}

export function callbackDataBytes(value) {
  return new TextEncoder().encode(value).length
}

export function isButtonValid(button, type) {
  if (!button.text.trim()) return false
  if (type === 'reply') return true
  const hasUrl = button.url.trim().length > 0
  const hasCallback = button.callback_data.trim().length > 0
  if (hasUrl === hasCallback) return false
  return hasUrl
    ? isValidButtonUrl(button.url.trim())
    : callbackDataBytes(button.callback_data.trim()) <= CALLBACK_DATA_MAX_BYTES
}
