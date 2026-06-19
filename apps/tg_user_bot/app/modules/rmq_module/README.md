# RMQ Module

`app/modules/rmq_module` — это общий RabbitMQ transport-layer модуль для
`telegram_template`.

Он нужен для общей инфраструктуры:

- подключения к RabbitMQ;
- публикации сообщений через стабильный API;
- регистрации consumer'ов очередей из Telegram-модулей;
- ручного запуска и остановки listener'ов через общий runtime;
- хранения topology-логики в одном месте.

Этот модуль намеренно не содержит Telegram-бизнес-логику и не встраивается в
бизнес-модули. При этом он теперь встроен в общий lifecycle бота как
постоянная системная инфраструктура.

Важно: в текущем состоянии `telegram_template` рядом с этим модулем уже
подключён демонстрационный `test_rmq_module`. Он регистрирует один consumer и
добавляет Telegram-команду `/rmqping` для ручной проверки publish-flow.

## Что Экспортирует Модуль

Предпочтительно импортировать публичные экспорты:

```python
from app.modules.rmq_module import RMQMessage, register_consumer, rmq_publisher
from app.modules.rmq_module import rmq_runtime
```

Публичные экспорты:

- `RMQMessage`
- `RMQRuntimeHealth`
- `RMQRegistrationRead`
- `ExchangeSpec`
- `QueueSpec`
- `ConsumerRegistration`
- `RMQPublisher`
- `RMQConsumerRegistry`
- `register_consumer(...)`
- `rmq_publisher`
- `rmq_registry`
- `rmq_runtime`
- `startup_rmq_runtime(...)`
- `shutdown_rmq_runtime()`
- `router`
- `RMQConfigurationError`

## Конфигурация

Настройка подключения:

```env
AMQP_URL=amqp://guest:guest@localhost:5672/
```

`AMQP_URL` теперь необязателен на уровне загрузки приложения. Он требуется
только тогда, когда RMQ реально используется:

- если какой-то модуль вызывает `rmq_publisher.publish(...)`, отсутствие
  `AMQP_URL` приведёт к `RMQConfigurationError`;
- если в registry есть consumer registrations, бот упадёт на startup, потому
  что lifecycle попытается поднять `rmq_runtime`;
- если registrations нет и publisher не используется, бот стартует без
  RabbitMQ-конфигурации.

В текущем шаблоне это означает следующее:

- если `test_rmq_module` остаётся подключённым, registration уже существует по
  умолчанию;
- при `RABBITMQ_CONSUMER_ENABLED=true` lifecycle попытается поднять RMQ runtime
  на старте;
- если вы хотите оставить `rmq_module` подключённым, но не стартовать RMQ в
  локальной среде, либо отключите `test_rmq_module` в `app/bot/registry.py`,
  либо установите `RABBITMQ_CONSUMER_ENABLED=false`.

Дополнительные runtime-настройки:

```env
RABBITMQ_DEFAULT_EXCHANGE=app.events
RABBITMQ_DEFAULT_EXCHANGE_TYPE=direct
RABBITMQ_DEFAULT_QUEUE=app.events.default
RABBITMQ_DEFAULT_ROUTING_KEY=app.events.default
RABBITMQ_PREFETCH_COUNT=10
RABBITMQ_CONSUMER_ENABLED=true
RABBITMQ_PUBLISH_TIMEOUT=5
RABBITMQ_RECONNECT_INTERVAL=5
```

Эти значения читаются через общий `app/core/config.py`, так что вся
process-level конфигурация остаётся централизованной.

## Как Публиковать Сообщения

Используй общий publisher вместо прямой работы с `aio-pika`:

```python
from app.modules.rmq_module import rmq_publisher


await rmq_publisher.publish(
    event="telegram.user.created",
    payload={"telegram_id": 123456},
    routing_key="telegram.user.created",
)
```

Publisher автоматически собирает transport-envelope:

- `event`
- `payload`
- `message_id`
- `timestamp`
- `source`
- `correlation_id`

Если нужен auto-declare очереди перед публикацией, передай `queue_name`.

## Как Регистрировать Consumer

Регистрируй consumer'ы во время импорта модуля или в явном startup wiring:

```python
from app.modules.rmq_module import RMQMessage, register_consumer


async def handle_user_created(message: RMQMessage) -> None:
    telegram_id = message.payload["telegram_id"]
    print(telegram_id)


register_consumer(
    queue_name="telegram.user.created",
    exchange_name="app.events",
    routing_key="telegram.user.created",
    handler=handle_user_created,
)
```

После регистрации consumer попадёт в общий registry, но не начнёт слушать
очередь сам по себе, пока не будет запущен runtime.

## Как Работает Интеграция С Lifecycle

`rmq_module` подключён в `app/bot/lifecycle.py` как постоянный системный
инфраструктурный модуль. Lifecycle вызывает `startup_rmq_runtime()` и
`shutdown_rmq_runtime()` напрямую — управлять ими вручную не нужно.

Сам runtime стартует только если одновременно выполняются оба условия:

- `RABBITMQ_CONSUMER_ENABLED=true`
- в registry есть хотя бы один зарегистрированный consumer

Если consumer-регистраций нет, startup RMQ просто пропускается.

С учётом встроенного `test_rmq_module` в fresh template второе условие уже
выполнено, пока вы явно не отключите demo-регистрацию.

## Что Делает Runtime

- устанавливает общее соединение с RabbitMQ;
- поднимает по одной listener-task на каждую регистрацию;
- валидирует входящие сообщения как `RMQMessage`;
- вызывает зарегистрированный async handler;
- делает `ack` на success;
- делает `reject(requeue=False)` на invalid envelope или handler error.

## Роутер Модуля

Модуль экспортирует `router`, чтобы не ломать каноническую структуру
`telegram_template`, но в V1 в нём нет пользовательских команд.

Сейчас этот router уже подключён в `app/bot/registry.py`, но в V1 остаётся
пустым и не добавляет пользовательских команд.

Пользовательская RMQ-команда в шаблоне сейчас живёт не здесь, а в
`app/modules/test_rmq_module`.

## Текущие Ограничения V1

Эта версия пока не предоставляет:

- DLQ orchestration;
- retry/backoff-политику;
- request-response RPC flows;
- idempotency guarantees.

Добавляй это только тогда, когда появится реальный сценарий и отдельное
разрешение на изменения outside of `rmq_module`.
