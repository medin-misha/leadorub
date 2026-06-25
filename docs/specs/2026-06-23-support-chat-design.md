# Support chat — bot ↔ admin panel (design)

Date: 2026-06-23
Status: approved

## Goal

Two-way support chat between a bot user and an administrator, driven from the admin
panel's **Chat** tab. A user types `/support`, the bot enters a support mode and forwards
every text message to the backend; the admin sees conversations in the panel and replies
on behalf of the bot. The Chat tab existed only as a placeholder; this fills it in.

Three services change:
- **backend** (`apps/backend`) — new `chat_module`: stores history + registers the
  backend's **first** RMQ consumer.
- **tg_user_bot** (`apps/tg_user_bot`) — new `support_module`: FSM support mode +
  publish + 👀 reaction.
- **admin_miniapp** (`apps/admin_miniapp`) — real Chat tab (two-pane, polling).

## Decisions (from brainstorming)

- **Storage = PostgreSQL, not MongoDB.** History is a flat message log; a `chat_message`
  table fits the existing SQLAlchemy/Alembic stack. No new infrastructure.
- **User → backend = RabbitMQ.** The bot publishes to a new queue `telegram_support_in`;
  the backend registers its first consumer and writes `direction='user'`.
- **Admin → user = the existing `telegram_notifications` queue.** No new bot code: the
  backend publishes a `{chat_ids:[telegram_id], message}` notification and the existing
  `notification_module` delivers it. The backend also stores `direction='admin'`.
- **Real-time = polling.** No WebSocket/SSE infra exists; the open thread polls every
  ~4 s, the conversation list every ~10 s.
- **👀 reaction = "queued".** The bot reacts on the user's message strictly AFTER a
  successful `rmq_publisher.publish` (delivered to the broker, not yet persisted).
- **Support mode = aiogram FSM, MemoryStorage.** Single polling process; state is
  short-lived. Redis is a documented upgrade path, not in scope.
- **Media = photos & documents, ≤10 MB.** Binary travels over HTTP, not RMQ: the bot
  downloads the file from Telegram and POSTs it to the backend, which stores it in S3
  (`file_module`) and references it from `chat_message.file_id`. Other types (video,
  voice, stickers) are out of scope for now.

## Data model (PostgreSQL)

Table `chat_message` (`chat_module`):

| column | type | notes |
|---|---|---|
| `id` | int PK | |
| `telegram_user_id` | int FK → `telegramuser.id` (CASCADE) | |
| `direction` | str(8) | `'user'` \| `'admin'` |
| `text` | text \| null | null when the message is media-only (caption optional) |
| `tg_message_id` | bigint \| null | Telegram message id of the user's message |
| `file_id` | int \| null FK → `file.id` (SET NULL) | optional attachment (backend File) |
| `is_read` | bool, default false | meaningful for `direction='user'` |
| `created_at` / `updated_at` | timestamptz | from `TimestampMixin` |

A message carries text and/or an attachment. Attachments reuse the existing `file_module`
(S3/MinIO + `File` model); `file_id` is the backend `File.id`.

Index `ix_chat_message_user_created (telegram_user_id, created_at)` backs both the thread
read and the conversation aggregate. A conversation = all rows for one `telegram_user_id`.

## RMQ contracts (single source of truth)

**Inbound (user → backend)** — NEW queue:
- queue `telegram_support_in`, exchange `app.events` (`direct`), routing key `telegram_support_in`.
- `event = "telegram.support_message"`. `payload`:
```json
{ "telegram_id": 555, "text": "help me", "tg_message_id": 42 }
```
Backend consumer (`chat_module.services.consumer_handler.handle_support_message`):
resolves `telegram_id → telegramuser.id`, inserts `direction='user', is_read=false`.
Unknown `telegram_id` → log + ack (dropped, no requeue). Other errors → reject(requeue=false).

**Inbound media (user → backend)** — HTTP, NOT RMQ (binary):
- `POST /api/chat/inbound-media` (`require_service`), `multipart/form-data`: `file`,
  `telegram_id`, optional `tg_message_id`, optional `caption`.
- The bot downloads the photo/document from Telegram (≤10 MB) and POSTs it; the backend
  uploads to S3 (`file_module`) and inserts `chat_message(direction='user', file_id, text=caption)`.
- 👀 is set after the upload returns 200.

**Outbound (admin → user)** — REUSES the newsletter/notification queue:
- queue `telegram_notifications`, exchange `app.events` (`direct`), routing key `telegram_notifications`.
- `event = "telegram.notification"`. `payload = {"chat_ids": [telegram_id], "message": text, "file_id"?: int}`.
- Delivered by the bot's existing `notification_module` — `_broadcast_text` for text,
  `_broadcast_file` (downloads `GET /api/files/{id}`, sends photo/document) when `file_id` is set.

## Backend — `apps/backend/app/modules/chat_module`

- **Model** `models/chat_message.py` — `ChatMessage`, explicit `__tablename__="chat_message"`.
- **Schemas** `schemas/chat.py` — `SupportMessageRMQ` (consumer input), `ChatMessageCreate`
  (internal CRUD), `ChatMessageRead` (incl. `file_id`/`file_name`), `ConversationRead`.
- **Services** `services/chat_service.py`:
  - `_store_file` — upload to S3 + create `File` (purge S3 on DB failure); shared helper.
  - `store_inbound_message` — resolve user, insert text `direction='user'`.
  - `store_inbound_media` — resolve user, `_store_file`, insert `direction='user'` with `file_id`.
  - `list_conversations` — one query: aggregate `max(created_at)` + `count(*) FILTER (user & !is_read)`,
    join `TelegramUser`, two correlated scalar subqueries for last text/direction, order by recency.
  - `get_messages` — initial load = last N (desc + reverse); polling = `id > after_id` asc.
  - `send_admin_reply(text=, file=)` — optional `_store_file`, create `direction='admin'`
    (flush) THEN publish (`file_id` added to the payload when present); publish failure
    propagates so `get_session` rolls back the un-delivered row.
  - `mark_read` — set `is_read=true` for user messages.
- **Consumer** `services/consumer_handler.py` — the backend's first consumer. Opens a DB
  session via `database.sessionmaker()` directly (NOT `Depends`/`get_session`, unavailable
  outside a request) and manages commit/rollback itself.
- **Endpoints** `handlers.py`, prefix `/api/chat`:
  - `GET /chat/conversations?search=&page=&limit=` (`require_admin`)
  - `GET /chat/conversations/{telegram_user_id}/messages?after_id=&limit=` (`require_admin`)
  - `POST /chat/conversations/{telegram_user_id}/reply` — multipart `text?` + `file?` (`require_admin`)
  - `POST /chat/conversations/{telegram_user_id}/read` (`require_admin`)
  - `POST /chat/inbound-media` — multipart `file` + `telegram_id` + `tg_message_id?` +
    `caption?` (`require_service`; called by the bot)
- Wiring: `ChatMessage` registered in `app/modules/__init__.py` (Alembic discovery +
  consumer registration side-effect); router in `app/api/router.py`. Migration
  `c1a2b3d4e5f6_add_chat_message`.

## Bot — `apps/tg_user_bot/app/modules/support_module`

- `states.py` — `SupportStates.active`.
- `keyboards.py` — inline "Завершить диалог" (`callback_data="support:stop"`).
- `services/uploader.py` — `upload_inbound_media(...)` POSTs a downloaded file to
  `POST /api/chat/inbound-media` (`X-Service-Token`, 60 s timeout).
- `handlers.py` — registration order matters (aiogram resolves in order within a router):
  1. `/support` (`@login_required`) → set `active` + intro/keyboard.
  2. `/stop` + `StateFilter(active)` → clear.
  3. callback `support:stop` + `active` → clear.
  4. `StateFilter(active) & F.text` → publish then `message.react([👀])`.
  5. `StateFilter(active) & F.photo` / `& F.document` → `_forward_media`: size-check (≤10 MB)
     → `bot.download` → `upload_inbound_media` → `message.react([👀])`.
  6. fallback `StateFilter(active)` (other types) → "only text/photo/document".
- `/start` (system router, registered first → priority) calls `state.clear()` so it also
  exits support mode.
- Wiring: `support_router` in `app/bot/registry.py` (after system/notification).
  Storage: `MemoryStorage` (default `Dispatcher()`).

## Frontend — `apps/admin_miniapp`

- `api/chat.js` — `listConversations`, `getMessages`, `reply`, `markRead`.
- `stores/chat.js` — Pinia store: conversations/messages/activeUid/search + polling
  lifecycle (`startListPolling`/`startThreadPolling`/`stopAllPolling`), `_inFlight` guard,
  incremental `after_id` fetch with id dedupe.
- `views/ChatView.vue` — two panes; `onMounted` starts polling, `onUnmounted` stops it
  (and on conversation switch the previous thread interval is stopped first — no leaks).
- `components/chat/` — `ConversationList` (unread badge, preview), `ChatThread`
  (auto-scroll), `MessageBubble` (admin right / user left), `ChatComposer` (text + file via
  `BaseFileInput`, Enter to send), `MediaAttachment` (fetches the file as a blob via
  `GET /files/{id}` and shows an image preview or a download link).

## Error handling

- Bot: publish failure → no 👀, "не доставлено" reply. 👀 only after a confirmed publish.
- Backend consumer: unknown user → drop+ack; other error → reject(requeue=false) (no poison loop).
- Admin reply: row created before publish; publish failure rolls the row back (atomic).
- ⚠️ The backend consumer needs `rabbitmq_consumer_enabled=true` + `amqp_url` set.

## Testing

- Backend (`tests/test_chat_service.py`, `test_chat_consumer.py`): inbound store path,
  reply creates admin row + publishes, publish failure propagates, consumer commit /
  unknown-user-ack / other-error-raise.
- Bot (`tests/test_support_handlers.py`): catch-all publishes correct payload then reacts
  (order asserted), publish failure skips reaction, `/stop` + callback clear state,
  `/support` sets `active`.
- Frontend: no test framework (out of scope) — verified via `npm run build`.

## Out of scope (YAGNI)

Video / voice / stickers in the support thread (only photos & documents); WebSocket/SSE
real-time; Redis FSM persistence; per-admin assignment / roles; conversation archiving;
typing indicators.
