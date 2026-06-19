# RMQ Module

`rmq_module` — встроенный RabbitMQ transport-модуль `fastapi_template`.

Он живёт в собственной директории внутри `app/modules/`, но не считается внешним или подключаемым плагином. Это first-party часть шаблона со своим package boundary, своим lifecycle-контрактом и своей документацией.

Модуль владеет общей инфраструктурой для:

- подключения к RabbitMQ;
- публикации сообщений через стабильный API;
- регистрации consumer'ов очередей из бизнес-модулей;
- запуска фоновых listeners при старте FastAPI;
- предоставления RMQ health/registration endpoints;
- предоставления debug publish/consume endpoints только при включенном глобальном отладочном режиме (`debug=true`) и наличии явного флага (`rabbitmq_debug_endpoints_enabled=true`).

Этот модуль намеренно остаётся только transport-layer. Бизнес-сценарии должны жить в feature-модулях, а не здесь.

## Роль В Архитектуре

Важно различать:

- `app/core/` — process-level общие примитивы;
- `app/modules/system/` — generic shared infrastructure;
- `app/modules/rmq_module/` — built-in transport subsystem со своим API.

RabbitMQ не перенесён в `system`, потому что это не generic CRUD/DB-примитив, а отдельная интеграционная подсистема со своей конфигурацией, runtime-логикой и transport-контрактом.

## Что Экспортирует Модуль

Предпочтительно импортировать публичные экспорты:

```python
from app.modules.rmq_module import RMQMessage, register_consumer, rmq_publisher
from app.modules.rmq_module import startup_rmq_runtime, shutdown_rmq_runtime
```

Публичные экспорты:

- `RMQMessage`
- `RMQPublishRequest`
- `RMQPublishResponse`
- `RMQConsumeRequest`
- `RMQConsumeResponse`
- `RMQPublisher`
- `RMQConsumerRegistry`
- `ConsumerRegistration`
- `ExchangeSpec`
- `QueueSpec`
- `RMQModuleSettings`
- `RMQConfigurationError`
- `register_consumer(...)`
- `rmq_publisher`
- `rmq_registry`
- `rmq_runtime`
- `rmq_settings`
- `startup_rmq_runtime()`
- `shutdown_rmq_runtime()`
- `router`

## Конфигурация

Все env-настройки по-прежнему загружаются централизованно через `app/core/config.py`, но сам модуль использует свою проекцию настроек из [config.py](/home/misha/code/module_service/fastapi_template/app/modules/rmq_module/config.py:1).

Основные настройки:

```env
rabbitmq_enabled=true
amqp_url=amqp://guest:guest@localhost:5672/
rabbitmq_default_exchange=app.events
rabbitmq_default_exchange_type=direct
rabbitmq_default_queue=app.events.default
rabbitmq_default_routing_key=app.events.default
rabbitmq_prefetch_count=10
rabbitmq_consumer_enabled=true
rabbitmq_publish_timeout=5
rabbitmq_reconnect_interval=5
rabbitmq_debug_endpoints_enabled=false
```

Поведение конфигурации:

- если `rabbitmq_enabled=false`, built-in модуль считается выключенным;
- если `rabbitmq_enabled=true`, но `amqp_url` не задан, publish/consume использовать нельзя;
- если consumer-регистраций нет, lifecycle не стартует RMQ runtime на startup;
- `POST /api/rmq/publish` и `POST /api/rmq/consume` доступны только в том случае, если глобальный режим отладки `debug` равен `true` **и** отладочные ручки дополнительно включены флагом `rabbitmq_debug_endpoints_enabled=true`. В иных случаях данные эндпоинты возвращают ошибку `404 Not Found`.

## Lifecycle

Process-level wiring больше не живёт в `main.py`. Оно вынесено в [app/lifecycle.py](/home/misha/code/module_service/fastapi_template/app/lifecycle.py:1).

FastAPI startup/shutdown использует thin wrappers:

- `startup_rmq_runtime()`
- `shutdown_rmq_runtime()`

Startup ведёт себя так:

1. если модуль выключен, runtime пропускается;
2. если consumer-регистраций нет, runtime пропускается;
3. если consumers выключены флагом, runtime пропускается;
4. если registrations есть, но `amqp_url` нет, выбрасывается `RMQConfigurationError`;
5. иначе запускаются listener-task'и.

Это делает RMQ встроенной частью приложения, но не принуждает каждую инсталляцию шаблона иметь живой RabbitMQ.

## Публикация Из Бизнес-Модуля

Используй общий publisher вместо прямой работы с `aio-pika`:

```python
from app.modules.rmq_module import rmq_publisher


await rmq_publisher.publish(
    event="telegram.user.created",
    payload={"telegram_id": 123456},
    routing_key="telegram.user.created",
)
```

Publisher автоматически оборачивает данные в стандартный envelope:

- `event`
- `payload`
- `message_id`
- `timestamp`
- `source`
- `correlation_id`

Если модуль не настроен, publisher поднимет `RMQConfigurationError` вместо неочевидного низкоуровневого сбоя клиента.

## Регистрация Consumer'а

Регистрируй consumer'ы через публичный API:

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

После регистрации listener будет автоматически запущен через lifecycle приложения, если consumers включены и конфигурация валидна.

Для production-кода лучше, чтобы consumer wiring было явным на уровне модуля, а не спрятанным в тестовом роутере.

## HTTP Endpoints

Всегда доступны:

- `GET /api/rmq/health`
- `GET /api/rmq/registrations`

Только в отладочном режиме (когда `debug=true` и `rabbitmq_debug_endpoints_enabled=true` в конфигурации):

- `POST /api/rmq/publish`
- `POST /api/rmq/consume`

Пример payload для debug publish:

```json
{
  "event": "debug.ping",
  "payload": {
    "message": "hello"
  },
  "routing_key": "app.events.default"
}
```

Пример payload для debug consume:

```json
{
  "queue_name": "app.events.default"
}
```

## Примерный Тестовый Модуль

`app/modules/test_rmq_module/` можно использовать как пример wiring для локальной отладки, но он не должен быть постоянно подключён в production API router по умолчанию.

## Текущие Ограничения V1

Эта версия пока не предоставляет:

- DLQ orchestration;
- настраиваемую retry/backoff-политику;
- request-response RPC flows;
- idempotency guarantees.

Добавляй это только тогда, когда появится реальный продуктовый сценарий, который этого требует.
