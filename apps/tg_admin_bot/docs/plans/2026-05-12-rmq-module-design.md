# Telegram RMQ Module Design

## Goal

Add a reusable RabbitMQ infrastructure module to `telegram_template`.

The module must:

- publish messages through a shared API;
- register queue consumers through a shared registry;
- run consumer listeners through an explicit runtime object;
- stay transport-focused and not contain Telegram business flows;
- integrate into shared `app/core` settings and `app/bot` lifecycle while
  keeping RabbitMQ configuration lazy.

## Scope

### Included In V1

- shared RabbitMQ client built on `aio-pika`;
- standard transport envelope;
- reusable publisher API;
- consumer registry;
- runtime start and stop API;
- exchange, queue, and binding declaration support;
- lifecycle integration into the bot startup and shutdown flow;
- module-local README in Russian;
- module-local AGENTS guide in English.

### Not Included In V1

- Telegram commands for RMQ debugging;
- DLQ, retry orchestration, or RPC semantics;
- business payload validation beyond the shared envelope.

## Architecture

The module lives in `app/modules/rmq_module/` and contains:

- `config.py`
  Module-local projection from shared core settings plus configuration error
  helpers.
- `handlers.py`
  Empty router placeholder for future module-level Telegram commands.
- `runtime.py`
  Manual startup and shutdown helpers for external wiring.
- `schemas/`
  Transport envelope and introspection DTOs.
- `services/client.py`
  Connection, channel, topology, publish, and consume primitives.
- `services/publisher.py`
  Stable high-level publish API.
- `services/registry.py`
  Consumer registration storage and helper.
- `services/consumer.py`
  Listener loop and dispatch to registered handlers.
- `services/runtime.py`
  Process-level runtime orchestration.
- `services/topology.py`
  Exchange and queue specifications.

## Runtime Flow

1. A feature module imports `rmq_publisher` and calls `publish(...)`.
2. A feature module imports `register_consumer(...)` and registers an async handler.
3. Bot lifecycle calls `await startup_rmq_runtime()` on startup.
4. Runtime starts only when consumer registrations exist and consumers are enabled.
5. Incoming messages are validated into `RMQMessage`.
6. Successful handlers `ack`; invalid payloads or handler failures `reject(requeue=False)`.
7. Bot lifecycle calls `await shutdown_rmq_runtime()` on shutdown.

## Constraints

- `README.md` must stay in Russian.
- `AGENTS.md` must stay in English.
- `AMQP_URL` must be required only when publisher or registered consumers
  actually use RabbitMQ.
- Public imports should come from `app.modules.rmq_module.__init__`.
