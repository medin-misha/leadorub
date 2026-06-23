# Notification Module Client Guide For AI Agents

## Purpose

`app.modules.notification_module` is the Telegram-side delivery consumer.
It subscribes to RabbitMQ queue `telegram_notifications` to receive, validate, and physically send messages via the `aiogram.Bot` instance.

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

Sender: `services/sender.py` (`build_markup`, `is_photo`, `send_notification`). File resolver: `services/backend_files.py`. Consumer wiring (`consumer_handler.py`, queue `telegram_notifications`) is unchanged.

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
