# RMQ Module Guide For AI Agents

## Purpose

`app.modules.rmq_module` is the shared RabbitMQ transport layer for the FastAPI application.

It exists to:

- centralize connection and channel management;
- provide a stable publish API for business modules;
- provide a registry-based consume API for business modules;
- keep queue topology logic in one place;
- keep FastAPI startup and shutdown integration predictable.

This module is built-in transport infrastructure, not business logic.
It remains a dedicated first-party module in `app/modules/` and should not be collapsed into `system`.

## Hard Rules

- Do not let feature modules import `aio-pika` directly when `rmq_module` can provide the needed capability.
- Keep connection and channel logic inside `services/client.py`.
- Keep listener lifecycle logic inside `services/runtime.py` and `services/consumer.py`.
- Keep queue, exchange, and binding descriptions reusable through shared topology structures.
- Keep the public message envelope backward-compatible.
- Do not add ad hoc retry or DLQ behavior in feature modules.
- Keep app-level startup/shutdown wiring in `app/lifecycle.py`, not in feature modules.

## Ownership Boundaries

This module owns:

- RabbitMQ connection management;
- message publishing;
- consumer registration;
- topology declaration;
- RMQ-specific config projection;
- debug HTTP endpoints for RabbitMQ transport checks.

This module does not own:

- Telegram workflows;
- business-level orchestration;
- idempotency semantics for specific features;
- domain payload validation beyond the shared transport envelope.
- generic DB or CRUD infrastructure from `system`.

## Preferred Imports

Feature modules should prefer:

```python
from app.modules.rmq_module import rmq_publisher, register_consumer, RMQMessage
```

Prefer public exports from `__init__.py` instead of importing internals unless you are changing this module itself.

## Editing Guidance

- Put new transport behavior in `services/`.
- Keep `handlers.py` thin and focused on HTTP transport only.
- Keep module-local settings projection in `config.py`; do not read `.env` directly in submodules.
- If a change affects startup or shutdown, update `app/lifecycle.py` and `runtime.py` wrappers together.
- If a change adds new settings, update both `app/core/config.py` and `.env.example`.
- If a change affects developer usage, update `README.md`.
- Do not wire example/test routers into `app/api/router.py` by default.

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

## Runtime Expectations

- `services/runtime.py` owns the long-lived listener runtime object.
- `runtime.py` at the module root owns startup/shutdown wrappers and configuration gating.
- `startup_rmq_runtime()` should be safe to call from app startup even when RMQ is disabled or no consumers are registered.
- Missing `amqp_url` should fail with `RMQConfigurationError`, not with an opaque low-level client exception.

## Message Contract

The shared envelope currently contains:

- `event`
- `payload`
- `message_id`
- `timestamp`
- `source`
- `correlation_id`

If you need additional transport metadata, add it deliberately and keep compatibility in mind.
