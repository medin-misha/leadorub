# Support Module Guide For AI Agents

## Purpose

Support mode: the user chats with an administrator on behalf of the bot. The user
enters with `/support`; every text message is forwarded to the backend over
RabbitMQ, and photos/documents are uploaded over HTTP.

The admin → user direction is NOT handled here: the backend publishes to
`telegram_notifications` and `notification_module` delivers it. Message and upload
contracts are in [interface contracts](API.md).

## Flow

- `/support` → FSM state `SupportStates.active` + intro with an inline "Завершить
  диалог" button. Not `StateFilter`-gated, so it can be entered from any state.
- text in `active` → publish to `telegram_support_in`, then set the 👀 reaction —
  strictly AFTER a successful publish.
- photo/document in `active` (≤ 10 MB) → download from Telegram, POST to the
  backend, then 👀 after the upload succeeds. Binary goes over HTTP, not RMQ.
- `/stop`, the inline button, or `/start` → leave support mode.

## Layout

- `states.py` — `SupportStates` with a single state `active`.
- `keyboards.py` — `support_exit_keyboard()` + `EXIT_CALLBACK = "support:stop"`.
- `services/uploader.py` — `upload_inbound_media(...)` (multipart POST +
  `X-Service-Token`).
- `handlers.py` — the support router; `MAX_MEDIA_BYTES = 10 MB` lives here.

## Handler Registration Order — IMPORTANT

aiogram resolves handlers in registration order within a router. Inside the
support router they MUST stay in this order:

1. `/support` (`@login_required`).
2. `/stop` + `StateFilter(active)`.
3. callback `support:stop` + `StateFilter(active)`.
4. `StateFilter(active) & F.text` — publish + react.
5. `StateFilter(active) & F.photo` / `& F.document` — `_forward_media`:
   size-check → `bot.download` → `upload_inbound_media` → react.
6. fallback `StateFilter(active)` (other types) — "only text/photo/document".
   MUST be last.

The router is included AFTER `system` in `app/bot/registry.py`, so `/start` keeps
priority and exits support mode (`start_command` calls `state.clear()`). The
catch-all is gated by `StateFilter(active)` so the bot behaves normally outside
support mode.

## Rules For Agents

- The 👀 reaction goes strictly after a confirmed `rmq_publisher.publish`; on
  publish failure send a "не доставлено" reply instead of a reaction. Never
  import `aio-pika` directly.
- Keep the queue/event constants and the media endpoint in sync with the backend
  `chat_module` and with [API.md](API.md).
- Media = photos & documents only (≤ 10 MB), uploaded over HTTP. Size is checked
  twice — by metadata before download and by actual bytes after. Adding
  video/voice means new `F.<type>` handlers above the fallback; the binary
  upload path is already type-agnostic.
- `Dispatcher()` uses the default `MemoryStorage` (single polling process,
  short-lived state). Redis would only be needed for multiple replicas / restart
  persistence — a one-line change in `app/bot/dispatcher.py` plus a setting.
