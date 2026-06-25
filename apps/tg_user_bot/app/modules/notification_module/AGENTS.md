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

Sender: `services/sender.py` (`build_markup`, `is_photo`, `send_notification`). File resolver: `services/backend_files.py` — sends the `X-Service-Token` header (`SERVICE_TOKEN`) because backend gates `GET /api/files/{id}` with `require_admin_or_service`; without it the download is `401`. Consumer wiring (`consumer_handler.py`, queue `telegram_notifications`) is unchanged.

## Idempotency (newsletter dedup)

The backend splits a broadcast into chunks (one RMQ message per chunk) that share one `broadcast_id`; each chunk is acked separately. To make chunk redelivery safe (RabbitMQ `consumer_timeout`, bot crash mid-chunk), the sender claims every recipient before sending: `idempotency_store.claim(broadcast_id, chat_id)` runs `SET newsletter:{broadcast_id}:{chat_id} 1 NX EX <ttl>` in Redis. `True` (key set — we are first) → send; `False` (key already existed) → skip. The marker is NOT deleted — it outlives the broadcast; TTL cleans it up.

- Both loops (`_broadcast_text`, `_broadcast_file`) claim before sending. In `_broadcast_file` the claim runs BEFORE building media, so a skipped recipient does not consume the byte-upload that captures the reusable Telegram file_id.
- Degrade → claim returns `True` (send without dedup) when `broadcast_id` is `None` (old message during rolling deploy) OR Redis is unavailable/errors. Delivery is prioritized over dedup; a warning is logged.
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
