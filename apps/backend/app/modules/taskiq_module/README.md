# Taskiq Module

`taskiq_module` — встроенная инфраструктура отложенных задач шаблона `fastapi_template`.

Модуль решает одну задачу: дать любому фича-модулю возможность **выполнять** и **откладывать**
фоновые задачи, не возясь с настройкой брокера и планировщика. Достаточно положить рядом с
модулем файл `tasks.py` — инфраструктуру трогать не нужно.

Ключевые свойства:

- единый общий broker для объявления задач (`@taskiq_broker.task`);
- автодискавери всех `app/modules/*/tasks.py` — новые задачи подхватываются автоматически;
- обобщённый API планирования для **любой** задачи (по дате, через интервал, по cron);
- строгий UTC: любое время запуска приводится к UTC через `astimezone` в одной точке
  (`ensure_utc`), наивные даты отклоняются;
- Redis result backend — результат `enqueue_task(...)` можно дождаться.

Это намеренно только инфраструктурный слой. Конкретные бизнес-задачи живут в `tasks.py`
фича-модулей, а не здесь.

## Архитектура

Работают три процесса (в продакшене — разные):

| Процесс       | Назначение                              | Запуск                                                            |
|---------------|-----------------------------------------|------------------------------------------------------------------|
| **API**       | объявляет и планирует задачи            | `uv run uvicorn main:app` (зовёт `startup_taskiq_runtime()`)      |
| **worker**    | исполняет задачи                        | `uv run taskiq worker app.modules.taskiq_module.broker:broker`    |
| **scheduler** | опрашивает Redis и шлёт задачи в worker | `uv run taskiq scheduler app.modules.taskiq_module.scheduler:scheduler` |

Компоненты:

- `AioPikaBroker` (RabbitMQ) — транспорт исполнения задач (`broker.py`);
- `RedisScheduleSource` — хранилище расписаний (`services/source.py`);
- `RedisAsyncResultBackend` — хранилище результатов (подключается в `broker.py`);
- `TaskiqScheduler` — собирается из брокера и источника расписаний (`scheduler.py`).

## Конфигурация

Переменные окружения (см. `.env.example`):

| Переменная                        | По умолчанию | Назначение                                              |
|-----------------------------------|--------------|---------------------------------------------------------|
| `taskiq_enabled`                  | `false`      | Включает модуль целиком                                  |
| `amqp_url`                        | —            | URL RabbitMQ (общий с rmq_module)                       |
| `redis_url`                       | —            | URL Redis (schedule source + result backend)            |
| `taskiq_schedule_prefix`          | `schedule`   | Префикс ключей расписаний в Redis                       |
| `taskiq_debug_endpoints_enabled`  | `false`      | Включает debug-роутер (только вместе с `debug=true`)     |

Настройки проецируются в `config.py` (`taskiq_settings`). Подмодули читают конфигурацию
оттуда, а не из `.env` напрямую.

## Что экспортирует модуль

```python
from app.modules.taskiq_module import taskiq_broker          # объявление задач
from app.modules.taskiq_module import (                       # планирование/запуск
    schedule_task_at, schedule_task_after, schedule_task_cron,
    cancel_scheduled_task, list_scheduled_tasks, enqueue_task, ensure_utc,
)
from app.modules.taskiq_module import (                       # жизненный цикл
    startup_taskiq_runtime, shutdown_taskiq_runtime,
)
```

## Как добавить задачи в свой модуль

1. Создайте `app/modules/<feature>/tasks.py`:

   ```python
   from app.modules.taskiq_module import taskiq_broker

   @taskiq_broker.task
   async def send_telegram_notification(chat_id: int, text: str) -> None:
       ...  # отправка уведомления
   ```

   Дискавери импортирует файл сам — править `taskiq_module` не нужно.

2. Планируйте задачу из любого сервиса или эндпоинта:

   ```python
   from datetime import datetime, timezone, timedelta
   from app.modules.taskiq_module import schedule_task_at, schedule_task_after
   from app.modules.notification_module.tasks import send_telegram_notification

   # на конкретный момент (дата обязана быть aware — приведётся к UTC)
   when = datetime(2026, 6, 2, 18, 0, tzinfo=timezone.utc)
   schedule_id = await schedule_task_at(send_telegram_notification, when, chat_id=1, text="hi")

   # через интервал от текущего момента
   schedule_id = await schedule_task_after(
       send_telegram_notification, timedelta(minutes=30), chat_id=1, text="через 30 мин"
   )
   ```

## API планирования

| Функция                                              | Назначение                                              |
|------------------------------------------------------|---------------------------------------------------------|
| `schedule_task_at(task, when, *a, **kw) -> str`      | Отложить на момент `when` (aware → UTC)                 |
| `schedule_task_after(task, delay, *a, **kw) -> str`  | Отложить на `delay` (`timedelta`) от `now(UTC)`         |
| `schedule_task_cron(task, cron, *a, **kw) -> str`    | Повторяющийся запуск по cron (в UTC)                    |
| `cancel_scheduled_task(schedule_id) -> None`         | Отменить расписание по `schedule_id`                    |
| `list_scheduled_tasks() -> list[ScheduledTask]`      | Список активных расписаний                               |
| `enqueue_task(task, *a, **kw) -> AsyncTaskiqTask`    | Запустить немедленно; результат — `await .wait_result()`|
| `ensure_utc(when) -> datetime`                       | Проверить aware-дату и привести к UTC через `astimezone`|

Если планирование недоступно (модуль выключен или нет `redis_url`), функции бросают
`TaskiqConfigurationError` с понятным сообщением.

## Debug-эндпоинты

Доступны только при `debug=true` **и** `taskiq_debug_endpoints_enabled=true`. Демонстрируют
планирование на встроенной задаче `send_reminder`:

- `POST /api/taskiq/schedule` — запланировать напоминание на дату (`{ "when": ..., "message": ... }`);
- `POST /api/taskiq/schedule/after` — на `delay_seconds` от текущего момента;
- `GET /api/taskiq/schedules` — список активных расписаний;
- `DELETE /api/taskiq/schedules/{schedule_id}` — отменить расписание.

## Локальная проверка end-to-end

Нужны запущенные RabbitMQ и Redis (из `.env`).

```bash
# терминал A — worker
uv run taskiq worker app.modules.taskiq_module.broker:broker
# терминал B — scheduler
uv run taskiq scheduler app.modules.taskiq_module.scheduler:scheduler
# терминал C — API (с включённым debug-роутером)
uv run uvicorn main:app
```

Затем `POST /api/taskiq/schedule/after` с телом `{"delay_seconds": 60, "message": "test"}` —
примерно через минуту worker напечатает строку `REMINDER: test`.
