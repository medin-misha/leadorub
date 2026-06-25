# Notification Module Client Guide For AI Agents

## Purpose

`app.modules.notification_module` is the Telegram-side delivery consumer.
It subscribes to RabbitMQ queue `admin_telegram_notifications` to receive, validate, and physically send messages via the `aiogram.Bot` instance.

> NOTE: The admin bot uses its own queue/routing key `admin_telegram_notifications` (NOT the shared `telegram_notifications` that `tg_user_bot` consumes). Since exchange `app.events` is a `direct` exchange, sharing a routing key would fan a copy of every user broadcast into this queue. The dedicated key isolates admin-bound notifications from user-bound ones.

This module is dependency-driven:
- It relies on `app.modules.rmq_module` to register consumers and listen to queues.
- It relies on `app.core.settings` to get the bot credentials and configuration.

## Incoming RMQ message (broadcast)

`TelegramNotification` payload:
- `chat_ids: list[int|str]` — the consumer loops and sends to each (single message per broadcast, not per recipient).
- `message: str|None` — text, or caption when a file is attached.
- `use_buttons: "INLINE"|"REPLY"|None` — single key (replaces the old `inline_buttons`/`reply_buttons` flags).
- `buttons: list[TelegramButton]|None` — FLAT list (one button per row). INLINE buttons use `url`/`callback_data`; REPLY buttons use `requests_contect`/`request_location`/`web_app`.
- `file_id: int|None` — backend `File.id`. Resolved via `GET /api/files/{id}` (download bytes once, reuse the returned Telegram file_id; `image/*` → `send_photo`, else `send_document`).

Sender: `services/sender.py` (`build_markup`, `is_photo`, `send_notification`). File resolver: `services/backend_files.py` — sends the `X-Service-Token` header (`SERVICE_TOKEN`) because backend gates `GET /api/files/{id}` with `require_admin_or_service`; without it the download is `401`. Consumer wiring lives in `consumer_handler.py` (queue/routing key `admin_telegram_notifications`).

## How Consumer Registration works

By importing the router `from app.modules.notification_module.handlers import router` in `app/bot/registry.py`, the import chain is resolved.
Inside `handlers.py`, `services/consumer_handler.py` is imported, causing:
```python
register_consumer(
    queue_name="admin_telegram_notifications",
    exchange_name="app.events",
    routing_key="admin_telegram_notifications",
    handler=handle_telegram_notification,
)
```
to execute at module-level. This registers the callback with the RMQ registry, and it will be run when the RMQ client initializes during startup hook inside `app/bot/lifecycle.py`.
