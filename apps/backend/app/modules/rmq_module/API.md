# RMQ Module

## GET /api/rmq/health

> Returns a snapshot of the RMQ runtime state: whether the module is enabled, whether `amqp_url` is configured, whether the listener runtime is running, whether there is a connection to the broker, along with counters of registrations and active listeners. Always available, no authorization required.

request

```json
{ "no request body" }
```

response

```json
{
  "enabled": true,
  "configured": true,
  "started": true,
  "connected": true,
  "consumer_enabled": true,
  "registration_count": 1,
  "listener_count": 1,
  "default_exchange": "app.events",
  "default_queue": "app.events.default"
}
```

## GET /api/rmq/registrations

> Returns the list of registered consumers (queue topology and bindings declared via `register_consumer`). Always available, no authorization required.

request

```json
{ "no request body" }
```

response

```json
[
  {
    "queue_name": "telegram_support_in",
    "exchange_name": "app.events",
    "routing_key": "telegram_support_in",
    "exchange_type": "direct",
    "handler_name": "handle_support_message",
    "auto_declare": true
  }
]
```

## POST /api/rmq/publish

> Publishes an arbitrary message directly to the broker (bypassing the outbox). Intended for transport debugging. Available only in debug mode: `debug=true` and `rabbitmq_debug_endpoints_enabled=true`; otherwise returns `404 Not Found`. No authorization required.

request

```json
{
  "event": "debug.ping",
  "payload": { "message": "hello" },
  "exchange_name": "app.events",
  "queue_name": "app.events.default",
  "routing_key": "app.events.default",
  "source": "debug-endpoint",
  "correlation_id": null,
  "exchange_type": "direct"
}
```

Required fields: `event` (non-empty string), `payload` (object). The remaining fields are optional (`null`/absent → defaults are taken from the configuration: `routing_key` falls back to `queue_name`, then to `default_routing_key`).

response

```json
{
  "message": {
    "event": "debug.ping",
    "payload": { "message": "hello" },
    "message_id": "0f8fad5b-d9cb-469f-a165-70867728950e",
    "timestamp": "2026-07-24T10:15:30.000000+00:00",
    "source": "debug-endpoint",
    "correlation_id": null
  },
  "exchange_name": "app.events",
  "queue_name": "app.events.default",
  "routing_key": "app.events.default",
  "source": "debug-endpoint",
  "exchange_type": "direct"
}
```

## POST /api/rmq/consume

> Fetches and acknowledges (ack) a single message from the queue for transport debugging. If necessary, declares the topology (exchange/queue/binding) before reading. Available only in debug mode: `debug=true` and `rabbitmq_debug_endpoints_enabled=true`; otherwise returns `404 Not Found`. No authorization required.

request

```json
{
  "queue_name": "app.events.default",
  "exchange_name": "app.events",
  "routing_key": "app.events.default",
  "exchange_type": "direct"
}
```

All fields are optional. If `queue_name` is absent, `default_queue` is used, and `routing_key` falls back to the queue name.

response

```json
{
  "status": "consumed",
  "queue_name": "app.events.default",
  "message": {
    "event": "debug.ping",
    "payload": { "message": "hello" },
    "message_id": "0f8fad5b-d9cb-469f-a165-70867728950e",
    "timestamp": "2026-07-24T10:15:30.000000+00:00",
    "source": "debug-endpoint",
    "correlation_id": null
  },
  "raw_body": null
}
```

Possible `status` values: `consumed` (message received; `message` is populated, `raw_body` = `null`), `empty` (queue is empty; `message` and `raw_body` = `null`). If the message body could not be parsed into `RMQMessage`, `message` = `null` and the raw body is returned in `raw_body`.
