# chat_module

Чат поддержки между пользователями бота и администраторами. Хранит историю переписки и
содержит **первый RMQ-consumer в backend**.

## Зачем модуль
- Таблица `chat_message` — плоский лог сообщений. Один диалог = все строки с одним
  `telegram_user_id`, отсортированные по `created_at`/`id`.
- Входящий текст (пользователь → backend): слушаем очередь `telegram_support_in` и пишем
  `direction='user'`.
- Входящее медиа (пользователь → backend): принимаем `POST /inbound-media` (бот скачал файл
  из Telegram), заливаем в S3 (`file_module`) и пишем `direction='user'` с `file_id`.
- Исходящее (админ → пользователь): пишем `direction='admin'` (с опциональным `file_id`) И
  публикуем уведомление в очередь `telegram_notifications` (доставляет `notification_module`
  бота — он сам скачает файл по `file_id` и отправит фото/документ).
- Чтение для админки: список диалогов (с непрочитанными), тред, отметка прочитанным.

## Структура
- `models/chat_message.py` — `ChatMessage(Base, TimestampMixin)`. Имя таблицы задано явно
  (`chat_message`), т.к. конвенция `Base` дала бы `chatmessage`. Композитный индекс
  `ix_chat_message_user_created (telegram_user_id, created_at)`.
- `schemas/chat.py` — `SupportMessageRMQ` (вход consumer'а), `ChatMessageCreate`
  (внутренняя), `ChatMessageRead`, `ConversationRead`, `ReplyRequest`.
- `services/chat_service.py` — бизнес-логика, исключение `SupportUserNotFound`.
- `services/consumer_handler.py` — `handle_support_message` + `register_consumer`.
- `handlers.py` — роутер `prefix="/chat"`, всё под `require_admin`.

## Контракты очередей
- Входящая: `telegram_support_in` / exchange `app.events` (`direct`) / routing key
  `telegram_support_in`. Payload — `{telegram_id, text, tg_message_id?}`.
- Исходящая: переиспользуем `telegram_notifications`, payload
  `{chat_ids:[telegram_id], message}`. Константы должны совпадать с ботом и newsletter.

## Сессия БД в consumer — ВАЖНО
Consumer работает вне FastAPI-запроса, поэтому `Depends(database.get_session)` недоступен.
`handle_support_message` открывает сессию через `database.sessionmaker()` напрямую и сам
делает commit/rollback. Это единственное санкционированное место в обход правила «только
Depends». Политика ошибок:
- `SupportUserNotFound` → rollback + лог + return (сообщение ack-ается, без requeue-петли);
- любое другое исключение → rollback + raise → consumer делает `reject(requeue=False)`.

Регистрация — side-effect импорта: `chat_module/__init__.py` импортирует
`services.consumer_handler`, а `app/modules/__init__.py` импортирует `chat_module`.
Consumer стартует только при `rabbitmq_consumer_enabled=true` и заданном `amqp_url`.

## Эндпоинты (`/api/chat`)
- `GET /conversations?search=&page=&limit=` (`require_admin`) — список диалогов (по
  свежести; непрочитанные через `count(*) FILTER (direction='user' AND NOT is_read)`).
- `GET /conversations/{telegram_user_id}/messages?after_id=&limit=` (`require_admin`) —
  тред. Без `after_id` — последние N (в хронологии); с `after_id` — только `id > after_id`
  (polling). `ChatMessageRead` содержит `file_id`/`file_name` для вложений.
- `POST /conversations/{telegram_user_id}/reply` (`require_admin`) — multipart: `text?` +
  `file?` (нужно текст ИЛИ файл). Сначала (заливаем файл и) пишем строку, затем публикуем;
  если публикация падает — строка откатывается (атомарно).
- `POST /conversations/{telegram_user_id}/read` (`require_admin`) — пометить прочитанным.
- `POST /inbound-media` (`require_service`) — multipart: `file`, `telegram_id`,
  `tg_message_id?`, `caption?`. Дёргает бот при фото/документе от пользователя; заливаем в
  S3 и пишем `direction='user'` с `file_id`. Бинарь идёт по HTTP (не через RMQ).

См. сквозной дизайн: `docs/specs/2026-06-23-support-chat-design.md`.
