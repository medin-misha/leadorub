# chat_module

Support chat between bot users and administrators. Stores the message history and is the
**first RMQ consumer in the backend**.

## Responsibility
- `chat_message` table — flat message log; one conversation = all rows for a
  `telegram_user_id` ordered by `created_at`/`id`.
- Inbound text (user → backend): consume the `telegram_support_in` queue and persist
  `direction='user'`.
- Inbound media (user → backend): receive `POST /inbound-media` (HTTP, the bot downloaded
  the file), upload to S3 (`file_module`) and persist `direction='user'` with `file_id`.
- Outbound (admin → user): persist `direction='admin'` (with optional `file_id`) and enqueue
  an outbox notification in the same DB transaction. The outbox runtime later publishes to
  `telegram_notifications` after commit.
- Read APIs for the admin panel: conversation list (with unread counts), thread, mark-read.

## Layout
- `models/chat_message.py` — `ChatMessage(Base, TimestampMixin)`. Explicit
  `__tablename__ = "chat_message"` (the `Base` convention would yield `chatmessage`).
  Composite index `ix_chat_message_user_created (telegram_user_id, created_at)`.
- `schemas/chat.py` — `SupportMessageRMQ` (consumer input), `ChatMessageCreate` (internal
  CRUD), `ChatMessageRead`, `ConversationRead`, `ReplyRequest`.
- `services/chat_service.py` — business logic (see below). `SupportUserNotFound`.
- `services/consumer_handler.py` — `handle_support_message` + `register_consumer(...)`.
- `handlers.py` — `APIRouter(prefix="/chat")`, all gated by `require_admin`.

## RMQ contracts
- Inbound queue `telegram_support_in` / exchange `app.events` (`direct`) / routing key
  `telegram_support_in`. Payload = `SupportMessageRMQ` = `{telegram_id, text, tg_message_id?}`.
- Outbound reuses `telegram_notifications` (event `telegram.notification`), payload
  `{chat_ids:[telegram_id], message:text}` — must stay aligned with the bot's
  `notification_module` and `telegram_module` newsletter constants.

## Consumer DB session — IMPORTANT (exception to the template rule)
The consumer runs OUTSIDE a FastAPI request, so `Depends(database.get_session)` is
unavailable. `handle_support_message` opens a session via `database.sessionmaker()`
directly and manages commit/rollback itself. This is the ONE sanctioned place that
bypasses the "always use Depends" rule. Error policy:
- `SupportUserNotFound` → rollback + log + return (message is acked, no requeue loop).
- any other exception → rollback + raise → `RMQConsumerService` does `reject(requeue=False)`.

Registration happens as an import side-effect: `chat_module/__init__.py` imports
`services.consumer_handler`, and `app/modules/__init__.py` imports `chat_module`. The
consumer only starts if `rabbitmq_consumer_enabled=true` and `amqp_url` is set.

## Endpoints (prefix `/api/chat`)
Router `prefix="/chat"`. Admin endpoints (conversation list, thread, reply, mark-read) are
gated by `require_admin`; the bot's media intake `POST /inbound-media` is gated by
`require_service` (`X-Service-Token`). Inbound media binary goes over HTTP here (not RMQ);
inbound text still arrives via the `telegram_support_in` queue.

Full request/response contracts (paths, params, fields, types) live in a dedicated file.
See [API contracts](API.md).

## Rules for agents
- Keep handlers thin; logic in `services/`. Never import `aio-pika` directly — use
  `enqueue_outbox_message` for transactional events or public RMQ module exports.
- Keep the inbound/outbound queue+event constants in sync with the bot and the spec
  (`docs/specs/2026-06-23-support-chat-design.md`).
- After API/model changes, run `uv run alembic revision --autogenerate` and update this
  file.
