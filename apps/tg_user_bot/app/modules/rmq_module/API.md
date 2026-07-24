# RMQ Module — Interface Contracts

This module exposes no HTTP and no Telegram commands. Its contract is the Python
publish/consume API used by feature modules, plus the shared message envelope and
topology defaults.

## Publish

```python
from app.modules.rmq_module import rmq_publisher

await rmq_publisher.publish(
    event="telegram.user.created",
    payload={"telegram_id": 123456},
    queue_name="telegram.user.created",   # optional: auto-declares before publish
    routing_key="telegram.user.created",
)
```

The publisher wraps the payload into the transport envelope automatically.
Missing `AMQP_URL` raises `RMQConfigurationError`.

## Register A Consumer

```python
from app.modules.rmq_module import RMQMessage, register_consumer


async def handle_user_created(message: RMQMessage) -> None:
    telegram_id = message.payload["telegram_id"]
    ...


register_consumer(
    queue_name="telegram.user.created",
    exchange_name="app.events",
    routing_key="telegram.user.created",
    handler=handle_user_created,
)
```

Registration adds the consumer to the registry but does not start listening until
the runtime starts (see CLAUDE.md → Runtime Activation). Register at import time
so the router import chain in `app/bot/registry.py` wires it up.

## Message Envelope (`RMQMessage`)

```json
{
  "event": "telegram.user.created",
  "payload": { "telegram_id": 123456 },
  "message_id": "0f8fad5b-d9cb-469f-a165-70867728950e",
  "timestamp": "2026-07-24T10:15:30.000000+00:00",
  "source": "telegram-bot",
  "correlation_id": null
}
```

- `event` — non-empty string.
- `payload` — object.
- `message_id` — UUID, auto-generated.
- `timestamp` — UTC, auto-generated.
- `source` — non-empty string.
- `correlation_id` — string or `null`.

## Topology Defaults

`ExchangeSpec(name, exchange_type="direct", durable=True, auto_delete=False)` and
`QueueSpec(name, durable=True, auto_delete=False, routing_key=None)`. Defaults
come from settings: exchange `app.events` (`direct`), queue/routing key
`app.events.default`.

## Consumer Outcome Semantics

| Handler outcome | Broker action |
| --- | --- |
| returns `None` | `ack` |
| raises `RetryableRMQError` | `reject(requeue=True)` |
| invalid envelope / other exception | `reject(requeue=False)` |
