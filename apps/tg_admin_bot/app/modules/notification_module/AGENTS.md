# Notification Module Client Guide For AI Agents

## Purpose

`app.modules.notification_module` is the Telegram-side delivery consumer.
It subscribes to RabbitMQ queue `telegram_notifications` to receive, validate, and physically send messages via the `aiogram.Bot` instance.

This module is dependency-driven:
- It relies on `app.modules.rmq_module` to register consumers and listen to queues.
- It relies on `app.core.settings` to get the bot credentials and configuration.

## Message Contract

Incoming event payload validation is enforced using the `TelegramNotification` and `TelegramButton` Pydantic models.

### `TelegramNotification`
- `chat_id` (int | str): Target Telegram chat identifier.
- `message` (str): Text message to be sent.
- `inline_buttons` (bool | None): Flag for inline keyboard layout.
- `reply_buttons` (bool | None): Flag for reply keyboard layout.
- `buttons` (list[list[TelegramButton]] | None): Keyboard grid.

### `TelegramButton`
- `text` (str): Button text.
- `requests_contect` (bool | None): Specifically spelled field request contact (as per requirements).
- `request_location` (bool | None): Flag to request user location.
- `web_app` (str | None): Target URL for Web App.

Note: There is a compatibility validator mapping `request_contact` input to `requests_contect` if provided.

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
