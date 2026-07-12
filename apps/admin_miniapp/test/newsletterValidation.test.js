import assert from 'node:assert/strict'
import test from 'node:test'

import {
  callbackDataBytes,
  isButtonValid,
  isValidButtonUrl,
} from '../src/utils/newsletterValidation.js'

test('принимает поддерживаемые Telegram URL и отклоняет локальные хосты', () => {
  assert.equal(isValidButtonUrl('https://example.com/path'), true)
  assert.equal(isValidButtonUrl('tg://resolve?domain=example'), true)
  assert.equal(isValidButtonUrl('http://localhost/path'), false)
  assert.equal(isValidButtonUrl('javascript:alert(1)'), false)
})

test('считает лимит callback_data в UTF-8 байтах', () => {
  assert.equal(callbackDataBytes('я'.repeat(32)), 64)
  assert.equal(isButtonValid({ text: 'OK', url: '', callback_data: 'я'.repeat(32) }, 'inline'), true)
  assert.equal(isButtonValid({ text: 'OK', url: '', callback_data: 'я'.repeat(33) }, 'inline'), false)
})

test('inline-кнопка требует ровно одно действие', () => {
  assert.equal(isButtonValid({ text: 'OK', url: '', callback_data: '' }, 'inline'), false)
  assert.equal(
    isButtonValid({ text: 'OK', url: 'https://example.com', callback_data: 'action' }, 'inline'),
    false,
  )
})
