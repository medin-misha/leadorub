# RMQ Module Guide For AI Agents

## Purpose

`app.modules.rmq_module` is the shared RabbitMQ transport layer for the Telegram
user bot.

It exists to:

- centralize RabbitMQ connection and channel management;
- provide a stable publish API for Telegram feature modules;
- provide a registry-based consume API for Telegram feature modules;
- keep queue topology logic in one place;
- stay integrated with `app/core` settings and `app/bot` lifecycle without
  leaking transport details into feature modules.

This module is transport infrastructure, not business logic.

## Hard Rules

- Do not let feature modules import `aio-pika` directly when `rmq_module` can
  provide the needed capability.
- Keep connection and channel logic inside `services/client.py`.
- Keep listener lifecycle logic inside `services/runtime.py` and
  `services/consumer.py`.
- Keep queue, exchange, and binding descriptions reusable through the shared
  topology structures in `services/topology.py`.
- Keep the public message envelope (`RMQMessage`) backward-compatible.
- Treat changes in `app/core` or `app/bot` as cross-cutting integration work and
  keep them minimal and deliberate.

## Ownership Boundaries

This module owns:

- RabbitMQ connection management;
- message publishing;
- consumer registration;
- topology declaration;
- runtime startup and shutdown helpers and the startup-activation policy.

This module does not own:

- Telegram business workflows;
- idempotency semantics for specific features (that lives with the feature, e.g.
  `notification_module`);
- domain payload validation beyond the shared transport envelope.

## Preferred Imports

```python
from app.modules.rmq_module import RMQMessage, register_consumer, rmq_publisher
```

Public exports (`__all__`): `RMQMessage`, `RetryableRMQError`,
`RMQConfigurationError`, `register_consumer`, `rmq_publisher`, `rmq_registry`,
`rmq_runtime`, `startup_rmq_runtime`, `shutdown_rmq_runtime`, `router`,
`ConsumerRegistration`, `ExchangeSpec`, `QueueSpec`, `RMQConsumerRegistry`,
`RMQPublisher`, `RMQRegistrationRead`, `RMQRuntimeHealth`. Prefer these over
internal paths unless you are changing this module itself.

## Editing Guidance

- Put transport behavior in `services/`.
- The module exports `router` (`Router(name="rmq")`) to preserve the canonical
  module shape, but it is empty in V1 — no Telegram commands. It is still
  included in `app/bot/registry.py`; keep it free of business commands.
- If a change adds new settings, update `app/core/config.py` and the bot `.env`.
- Keep runtime startup lazy: no `AMQP_URL` is required unless the publisher runs
  or consumers are registered.

## Consumer Contract

Registered handlers accept one `RMQMessage` and return `None`:

```python
async def handler(message: RMQMessage) -> None:
    ...
```

On handler outcome, the runtime:

- `ack`s on success;
- `reject(requeue=True)` when the handler raises the public `RetryableRMQError`
  (known-transient failure);
- `reject(requeue=False)` on an invalid envelope or any other exception.

Do not silently swallow handler failures inside the runtime.

## Runtime Activation

`startup_rmq_runtime()` is wired directly in `app/bot/lifecycle.py`; do not manage
it manually. The runtime starts only when BOTH hold:

- `RABBITMQ_CONSUMER_ENABLED=true`, AND
- at least one consumer is registered.

Otherwise startup is skipped and no broker connection is opened. In the current
bot the registered consumers are `notification_module` (`telegram_notifications`)
and, on the publish side, `support_module` publishes to `telegram_support_in`.

## Message Envelope

`RMQMessage` currently carries:

- `event` (non-empty `str`)
- `payload` (`dict`)
- `message_id` (`uuid4`, auto)
- `timestamp` (UTC, auto)
- `source` (non-empty `str`)
- `correlation_id` (`str | None`)

Add transport metadata deliberately and keep compatibility in mind. HTTP debug
endpoints exist on the backend `rmq_module`, not here; see [interface
contracts](API.md) for the Python publish/consume API.

## V1 Limitations

Not provided yet: DLQ orchestration, retry/backoff policy, RPC flows,
transport-level idempotency guarantees. Add these only with a real scenario and
explicit permission to change code outside `rmq_module`.
