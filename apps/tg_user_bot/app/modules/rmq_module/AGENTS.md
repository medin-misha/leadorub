# RMQ Module Guide For AI Agents

## Purpose

`app.modules.rmq_module` is the shared RabbitMQ transport layer for
`telegram_template`.

It exists to:

- centralize RabbitMQ connection and channel management;
- provide a stable publish API for Telegram feature modules;
- provide a registry-based consume API for Telegram feature modules;
- keep queue topology logic in one place;
- stay integrated with shared `app/core` settings and `app/bot` lifecycle
  without leaking transport details into feature modules.

This module is transport infrastructure, not business logic.

## Hard Rules

- Do not let feature modules import `aio-pika` directly when `rmq_module` can
  provide the needed capability.
- Keep connection and channel logic inside `services/client.py`.
- Keep listener lifecycle logic inside `services/runtime.py` and
  `services/consumer.py`.
- Keep queue, exchange, and binding descriptions reusable through shared
  topology structures.
- Keep the public message envelope backward-compatible.
- Treat changes in `app/core` or `app/bot` as cross-cutting integration work
  and keep them minimal and deliberate.

## Ownership Boundaries

This module owns:

- RabbitMQ connection management;
- message publishing;
- consumer registration;
- topology declaration;
- manual runtime startup and shutdown helpers.
- startup policy for consumer runtime activation.

This module does not own:

- Telegram business workflows;
- aiogram router registration in the bot runtime;
- idempotency semantics for specific features;
- domain payload validation beyond the shared transport envelope.

## Preferred Imports

Feature modules should prefer:

```python
from app.modules.rmq_module import RMQMessage, register_consumer, rmq_publisher
```

Prefer public exports from `__init__.py` instead of importing internals unless
you are changing this module itself.

## Editing Guidance

- Put transport behavior in `services/`.
- Keep `handlers.py` thin and free from business commands.
- If a change adds new settings, update both `app/core/config.py` and the
  module README.
- If a change affects developer usage, update the Russian `README.md`.
- Keep runtime startup lazy: no RMQ URL should be required unless publisher or
  registered consumers actually use RabbitMQ.

## Consumer Contract

Registered consumer handlers should accept one `RMQMessage` and return `None`.

Expected shape:

```python
async def handler(message: RMQMessage) -> None:
    ...
```

If the handler raises:

- the message is rejected without requeue in V1;
- the failure is logged by the runtime.

Do not silently swallow handler failures inside the runtime.

## Message Contract

The shared envelope currently contains:

- `event`
- `payload`
- `message_id`
- `timestamp`
- `source`
- `correlation_id`

If you need additional transport metadata, add it deliberately and keep
compatibility in mind.
