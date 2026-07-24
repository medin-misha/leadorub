# Notification Module Guide For AI Agents

## Purpose

`app.modules.notification_module` is the Telegram-side delivery consumer. It
subscribes to the RabbitMQ queue `telegram_notifications` to receive, validate,
and physically send messages (single notifications and newsletter broadcasts) via
an `aiogram.Bot` instance.

This module is dependency-driven:

- it relies on `rmq_module` to register the consumer and receive messages;
- it relies on `app.core.settings` for bot credentials and configuration.

The admin → user direction ends here: `support_module` and the admin chat publish
to this queue on the backend side; delivery is this module's job. The full
inbound message contract is in [interface contracts](API.md).

## Layout

- `handlers.py` — `Router(name="notification")` plus a side-effect import of the
  consumer handler. No update handling; the router exists only to trigger
  registration through the import chain.
- `schemas.py` — `TelegramNotification`, `TelegramButton`.
- `services/consumer_handler.py` — RMQ registration + `handle_telegram_notification`.
- `services/sender.py` — the send path (`build_markup`, `is_photo`, `escape_html`,
  `_send_with_retry`, `send_notification`, `_broadcast_text`, `_broadcast_file`).
- `services/backend_files.py` — attachment resolver (`fetch_file`).
- `services/idempotency.py` — the Redis dedup store (`idempotency_store`).

## Consumer Registration

Importing the router in `app/bot/registry.py` pulls in `consumer_handler.py`,
which runs `register_consumer(queue_name="telegram_notifications",
exchange_name="app.events", routing_key="telegram_notifications",
handler=handle_telegram_notification)` at module level. The consumer starts when
the RMQ runtime starts during `app/bot/lifecycle.py`.

## Send Error Handling (`_send_with_retry`)

Every send goes through `_send_with_retry(make_request, chat_id)`, which returns a
`DeliveryResult` with one of three statuses. `make_request` is a coroutine
factory — re-called each attempt, since an already-awaited coroutine cannot be
reused.

- `TelegramRetryAfter` (429, flood control): sleep EXACTLY `exc.retry_after` and
  retry, up to `MAX_FLOOD_RETRIES` (5). This is the only case that retries
  in-process. Ignoring 429 and hammering on gets the WHOLE bot temporarily
  banned, not one recipient — so it is mandatory.
- `TelegramForbiddenError` (403, user blocked the bot / chat deleted): log at
  info (expected, no stack trace), no retry → `PERMANENT_FAILURE`.
- any other exception: `logger.exception`, no in-process retry →
  `RETRYABLE_FAILURE`.

A `RETRYABLE_FAILURE` releases the recipient's Redis claim and adds it to the
retry set; after the loop finishes the remaining recipients, the module raises
`NotificationDeliveryError(RetryableRMQError)` so the transport rejects the chunk
with `requeue=True`. On redelivery, completed recipients are skipped (`sent`
marker) and only released recipients are retried. In `_broadcast_file` the
returned `Message` is also how the reusable Telegram `file_id` is captured — only
on a successful send.

## HTML Escaping (plain-text safety)

The bot sends with `parse_mode=HTML` (`DefaultBotProperties`). Admin-authored text
(newsletter + chat replies, both routed here) is treated as PLAIN text:
`escape_html` (stdlib `html.escape(..., quote=False)`) escapes `<`, `>`, `&` in
`message` right before it becomes `text=` / `caption=`. Without this, stray
`<`/`>`/`&` make Telegram reject the message with `can't parse entities`; the
error is swallowed in the send loop, so the recipient silently gets nothing.
Button labels are NOT escaped — Telegram does not HTML-parse them. Escaping is
intentionally done in the bot, not the backend: it is parse_mode-specific.

## Idempotency (newsletter dedup)

The backend splits a broadcast into chunks (one RMQ message per chunk) sharing one
`broadcast_id`. The sender uses a two-phase per-recipient marker keyed
`newsletter:{broadcast_id}:{chat_id}`:

- **processing** — `claim()` does `SET NX EX 900` with a unique token
  (`PROCESSING_TTL_SECONDS = 900`, 15 min);
- **sent** — on success or permanent 403, a Lua CAS atomically flips the token to
  `sent` with the long TTL `newsletter_idempotency_ttl_seconds` (default `172800`
  = 48 h);
- **release** — on a temporary failure, a Lua CAS deletes only the owning
  worker's `processing` token, then the chunk is requeued.

Both loops claim before sending; in `_broadcast_file` the claim runs BEFORE
building media so a skipped recipient does not consume the byte upload. Degrade
(send without dedup, warn) when `broadcast_id` is `None` (old message during a
rolling deploy) OR Redis is unavailable. Delivery is prioritized over dedup. The
store connects/closes in `app/bot/lifecycle.py`.

## Rules For Agents

- Never import `aio-pika` directly; the transport is `rmq_module`.
- Keep the inbound contract in sync with the backend chat/newsletter publishers
  and with [API.md](API.md).
- Attachments only via `GET /api/files/{id}` with `X-Service-Token` (backend
  gates it with `require_admin_or_service`; without the token the download is
  `401`).
- Adding a media type means a new branch in the sender; keep dedup and error
  handling type-agnostic.
