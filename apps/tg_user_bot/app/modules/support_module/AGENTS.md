# support_module

Support mode: the user chats with an administrator on behalf of the bot. The user enters
with `/support`; every text message is forwarded to the backend over RabbitMQ.

## Flow
- `/support` → FSM state `SupportStates.active` + intro message with an inline
  "Завершить диалог" button.
- Any text in `active` → publish to queue `telegram_support_in`, then set the 👀 reaction
  on the message — strictly AFTER a successful publish.
- A photo/document in `active` (≤10 MB) → download from Telegram, POST to the backend
  (`/api/chat/inbound-media`), then set 👀 after the upload succeeds. Binary goes over HTTP,
  not RMQ.
- `/stop`, the inline button, or `/start` → leave support mode.

The admin → user direction is NOT handled here: the backend publishes a notification to
`telegram_notifications` and the existing `notification_module` delivers it (text or file).

## Layout
- `states.py` — `SupportStates.active`.
- `keyboards.py` — `support_exit_keyboard()` + `EXIT_CALLBACK = "support:stop"`.
- `services/uploader.py` — `upload_inbound_media(...)` (multipart POST + `X-Service-Token`).
- `handlers.py` — the support router. `MAX_MEDIA_BYTES = 10 MB`.

## Handler registration order — IMPORTANT
aiogram resolves handlers in registration order within a router. Inside the support
router they MUST be declared in this order:
1. `/support` (`@login_required`).
2. `/stop` + `StateFilter(active)`.
3. callback `support:stop` + `StateFilter(active)`.
4. `StateFilter(active) & F.text` — publish + react.
5. `StateFilter(active) & F.photo` / `& F.document` — `_forward_media`: size-check →
   `bot.download` → `upload_inbound_media` → react.
6. fallback `StateFilter(active)` (other types) — "only text/photo/document". MUST be last.

The router is included AFTER `system` in `app/bot/registry.py`, so `/start` keeps priority
and exits support mode (`start_command` calls `state.clear()`). The catch-all is gated by
`StateFilter(active)` so the bot behaves normally outside support mode.

## RMQ contract (must match backend `chat_module`)
- queue/routing key `telegram_support_in`, exchange `app.events` (`direct`),
  event `telegram.support_message`.
- payload: `{telegram_id, text, tg_message_id}`.
- 👀 = "queued" (delivered to the broker), NOT "admin has read it". Published via
  `rmq_publisher`; on publish failure → no reaction, a "не доставлено" reply instead.

## Storage
`Dispatcher()` uses the default `MemoryStorage` (single polling process, short-lived
state). Redis is only needed for multiple replicas / restart persistence — that would be a
one-line change in `app/bot/dispatcher.py` plus a `redis_url` setting and dependency.

## Rules for agents
- Reaction strictly after a confirmed `rmq_publisher.publish`; never import `aio-pika`
  directly.
- Keep the queue/event constants in sync with the backend and the spec
  (`docs/specs/2026-06-23-support-chat-design.md`).
- Media = photos & documents only (≤10 MB), uploaded over HTTP. Adding video/voice means
  new `F.<type>` handlers above the fallback; everything else (binary upload, storage) is
  already type-agnostic on the backend.
