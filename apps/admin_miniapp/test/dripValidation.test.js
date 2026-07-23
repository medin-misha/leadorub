import assert from 'node:assert/strict'
import test from 'node:test'

import {
  isDaysOffsetValid,
  isSendTimeValid,
  isTriggerStateValid,
  isTriggerValid,
} from '../src/utils/dripValidation.js'

test('состояние-триггер — непустая строка до 255 символов', () => {
  assert.equal(isTriggerStateValid('persona_start'), true)
  assert.equal(isTriggerStateValid('  '), false)
  assert.equal(isTriggerStateValid(''), false)
  assert.equal(isTriggerStateValid('x'.repeat(256)), false)
})

test('дни — целое от 0 до 365 (принимает строку из input type=number)', () => {
  assert.equal(isDaysOffsetValid(0), true)
  assert.equal(isDaysOffsetValid('7'), true)
  assert.equal(isDaysOffsetValid(-1), false)
  assert.equal(isDaysOffsetValid(366), false)
  assert.equal(isDaysOffsetValid(1.5), false)
  assert.equal(isDaysOffsetValid(''), false)
})

test('время отправки — строго HH:MM', () => {
  assert.equal(isSendTimeValid('10:00'), true)
  assert.equal(isSendTimeValid('23:59'), true)
  assert.equal(isSendTimeValid('24:00'), false)
  assert.equal(isSendTimeValid('9:00'), false)
  assert.equal(isSendTimeValid(''), false)
})

test('isTriggerValid объединяет все три проверки', () => {
  const valid = { triggerState: 'persona_start', daysOffset: 1, sendTime: '10:00' }
  assert.equal(isTriggerValid(valid), true)
  assert.equal(isTriggerValid({ ...valid, triggerState: '' }), false)
  assert.equal(isTriggerValid({ ...valid, daysOffset: -1 }), false)
  assert.equal(isTriggerValid({ ...valid, sendTime: 'later' }), false)
})
