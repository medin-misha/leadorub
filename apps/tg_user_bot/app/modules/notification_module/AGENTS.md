# Notification Module Client Guide For AI Agents

## Purpose

`app.modules.notification_module` is the Telegram-side delivery consumer.
It subscribes to RabbitMQ queue `telegram_notifications` to receive, validate, and physically send messages via the `aiogram.Bot` instance.

This module is dependency-driven:
- It relies on `app.modules.rmq_module` to register consumers and listen to queues.
- It relies on `app.core.settings` to get the bot credentials and configuration.

## Incoming RMQ message (broadcast)

`TelegramNotification` payload:
- `chat_ids: list[int|str]` — recipients of ONE chunk; the consumer loops and sends to each (the backend now publishes one message **per chunk**, not one per recipient).
- `message: str|None` — text, or caption when a file is attached.
- `use_buttons: "INLINE"|"REPLY"|None` — single key (replaces the old `inline_buttons`/`reply_buttons` flags).
- `buttons: list[TelegramButton]|None` — FLAT list (one button per row). INLINE buttons use `url`/`callback_data`; REPLY buttons use `requests_contect`/`request_location`/`web_app`.
- `file_id: int|None` — backend `File.id`. Resolved via `GET /api/files/{id}` (download bytes once, reuse the returned Telegram file_id; `image/*` → `send_photo`, else `send_document`).
- `broadcast_id: str|None` — shared id of all chunks of one broadcast; the dedup key (`IdempotencyStore.claim`, Redis `SET NX`). `None` = dedup off (old message during rolling deploy / degrade).
- `chunk_index: int|None`, `chunk_total: int|None` — chunking diagnostics for logs.

Sender: `services/sender.py` (`build_markup`, `is_photo`, `escape_html`, `_send_with_retry`, `send_notification`). File resolver: `services/backend_files.py` — sends the `X-Service-Token` header (`SERVICE_TOKEN`) because backend gates `GET /api/files/{id}` with `require_admin_or_service`; without it the download is `401`. Consumer wiring (`consumer_handler.py`, queue `telegram_notifications`) is unchanged.

## Send error handling (`_send_with_retry`)

Every send (`send_message` / `send_photo` / `send_document`) goes through
`_send_with_retry(make_request, chat_id)`, which dispatches on the aiogram error type
per recipient. `make_request` is a coroutine factory (re-called each attempt — an
already-awaited coroutine cannot be reused). It returns the `Message` on success or
`None` when the recipient could not be reached.

- `TelegramRetryAfter` (429, flood control): sleep EXACTLY `exc.retry_after` and retry,
  up to `MAX_FLOOD_RETRIES` (default 5). Ignoring 429 and hammering on gets the WHOLE
  bot temporarily banned, not just one recipient — so this is mandatory, not optional.
- `TelegramForbiddenError` (403, user blocked the bot / chat deleted): log at info (no
  stack trace — it is expected), no retry, move to the next recipient.
- Any other exception: `logger.exception` (stack trace) and skip the recipient so one
  bad address never aborts the whole broadcast.

In `_broadcast_file` the returned `Message` is also how the reusable Telegram `file_id`
is captured — only when the send actually succeeds (`message is not None`).

TODO (cross-service, not yet wired): on 403 the user should be marked `is_blocket_bot`
in the backend so future broadcasts skip them. There is no service-auth channel for
that today — the `PATCH /telegram/users/{id}` endpoint is `require_admin` and is keyed
by internal `id`, while the bot only holds `telegram_id`.

## HTML escaping (plain-text safety)

The bot sends with `parse_mode=HTML` (`DefaultBotProperties`). Admin-authored text
(newsletter + chat replies, both routed through this queue) is treated as **plain
text**: `escape_html` (`services/sender.py`, stdlib `html.escape(..., quote=False)`)
escapes `<`, `>`, `&` in `message` right before it becomes `text=` / `caption=`.
Without this, stray `<`/`>`/`&` ("M&M's", `1 < 2`, an unclosed tag) make Telegram
reject the message with `can't parse entities`; the error is swallowed by the
`except` in the send loop, so the recipient silently gets nothing. Button labels are
NOT escaped — Telegram does not HTML-parse them. Escaping is intentionally NOT done
in the backend: it is parse_mode-specific, so it lives next to the bot that owns the
parse mode. Known minor limitation: the backend's 1024 length check sees the RAW
text, so a caption packed with special chars could still overflow once escaped.

## Idempotency (newsletter dedup)

The backend splits a broadcast into chunks (one RMQ message per chunk) that share one `broadcast_id`. The sender uses a two-phase per-recipient marker: `claim` creates a unique short-lived `processing` value with `SET NX`; success and permanent 403 failures atomically become long-lived `sent`; temporary failures atomically release only the owning worker's claim and raise `RetryableRMQError`, so the transport rejects with `requeue=True`. On redelivery, completed recipients are skipped and only released recipients are retried.

- Both loops (`_broadcast_text`, `_broadcast_file`) claim before sending. In `_broadcast_file` the claim runs BEFORE building media, so a skipped recipient does not consume the byte-upload that captures the reusable Telegram file_id.
- Degrade → claim returns an untracked claim (send without dedup) when `broadcast_id` is `None` (old message during rolling deploy) OR Redis is unavailable/errors. Delivery is prioritized over dedup; a warning is logged.
- Store: `services/idempotency.py` (`idempotency_store` singleton), connected/closed in `app/bot/lifecycle.py`. Config (`app/core/config.py`): `redis_host`/`redis_port`/`redis_db`/`redis_password` (mirror of the backend, single `redis_password` secret from `infra/.env`) + `redis_url` property; marker TTL `newsletter_idempotency_ttl_seconds` (default `172800` = 48h, ENV).

## How Consumer Registration works

By importing the router `from app.modules.notification_module.handlers import router` in `app/bot/registry.py`, the import chain is resolved.
Inside `handlers.py`, `services/consumer_handler.py` is imported, causing:
```python
register_consumer(
    queue_name="telegram_notifications",
    exchange_name="app.events",
    routing_key="telegram_notifications",
    handler=handle_telegram_notification,
)
```
to execute at module-level. This registers the callback with the RMQ registry, and it will be run when the RMQ client initializes during startup hook inside `app/bot/lifecycle.py`.
