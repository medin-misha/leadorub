# support_module

Режим поддержки: пользователь общается с администратором от имени бота. Вход — командой
`/support`; каждое текстовое сообщение пересылается в backend через RabbitMQ.

## Поток
- `/support` → состояние FSM `SupportStates.active` + интро с инлайн-кнопкой
  «Завершить диалог».
- Любой текст в состоянии `active` → публикация в очередь `telegram_support_in`, затем
  реакция 👀 на сообщение — строго ПОСЛЕ успешной публикации.
- Фото/документ в `active` (до 10 МБ) → бот скачивает файл из Telegram и POST-ит на backend
  (`/api/chat/inbound-media`), затем 👀 после успешной загрузки. Бинарь идёт по HTTP, не
  через RMQ.
- `/stop`, инлайн-кнопка или `/start` → выход из режима поддержки.

Направление «админ → пользователь» здесь НЕ обрабатывается: backend публикует уведомление
в `telegram_notifications`, а доставляет его существующий `notification_module` (текст или файл).

## Структура
- `states.py` — `SupportStates.active`.
- `keyboards.py` — `support_exit_keyboard()` + `EXIT_CALLBACK = "support:stop"`.
- `services/uploader.py` — `upload_inbound_media(...)` (multipart POST + `X-Service-Token`).
- `handlers.py` — роутер режима поддержки. `MAX_MEDIA_BYTES = 10 МБ`.

## Порядок регистрации хендлеров — ВАЖНО
aiogram резолвит хендлеры по порядку регистрации внутри роутера. Порядок строго такой:
1. `/support` (`@login_required`).
2. `/stop` + `StateFilter(active)`.
3. callback `support:stop` + `StateFilter(active)`.
4. `StateFilter(active) & F.text` — публикация + реакция.
5. `StateFilter(active) & F.photo` / `& F.document` — `_forward_media`: проверка размера →
   `bot.download` → `upload_inbound_media` → реакция.
6. fallback `StateFilter(active)` (прочие типы) — «только текст/фото/документ». Последним.

Роутер подключается ПОСЛЕ `system` в `app/bot/registry.py`, поэтому `/start` имеет
приоритет и выходит из режима (`start_command` вызывает `state.clear()`). Catch-all
ограничен `StateFilter(active)`, чтобы вне режима бот работал как обычно.

## Контракт очереди (должен совпадать с backend `chat_module`)
- очередь/routing key `telegram_support_in`, exchange `app.events` (`direct`),
  event `telegram.support_message`.
- payload: `{telegram_id, text, tg_message_id}`.
- 👀 = «принято в очередь» (доставлено брокеру), а не «админ прочитал». При ошибке
  публикации реакции нет — вместо неё ответ «не доставлено».

## Хранилище состояния
`Dispatcher()` использует дефолтный `MemoryStorage` (один polling-процесс, короткоживущее
состояние). Redis нужен только для нескольких реплик или переживания рестартов — это
правка одной строки в `app/bot/dispatcher.py` плюс настройка/зависимость.

См. сквозной дизайн: `docs/specs/2026-06-23-support-chat-design.md`.
