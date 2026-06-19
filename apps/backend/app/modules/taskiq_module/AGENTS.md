# Taskiq Module Guide For AI Agents

## Purpose

`app.modules.taskiq_module` is the shared deferred-task infrastructure for the FastAPI
application. It exists to let any feature module enqueue and schedule background tasks
without owning broker/scheduler plumbing.

It provides:

- a single shared broker that feature modules use to declare tasks (`@taskiq_broker.task`);
- auto-discovery of every `app/modules/*/tasks.py` so new task modules need zero infra changes;
- a generic scheduling API that works for **any** task (by time, by delay, by cron);
- a strict UTC guard (`ensure_utc`) — every scheduled run is normalized to UTC via `astimezone`;
- a Redis result backend so `enqueue_task(...)` results can be awaited.

This module is built-in infrastructure, not business logic. It stays a dedicated first-party
module in `app/modules/` and must not be collapsed into `system`.

## Transport Architecture

Three cooperating runtimes (separate OS processes in production):

- **API process** — declares/schedules tasks; runs `startup_taskiq_runtime()` in the lifespan.
- **Worker process** — executes tasks: `taskiq worker app.modules.taskiq_module.broker:broker`.
- **Scheduler process** — polls Redis and dispatches due tasks:
  `taskiq scheduler app.modules.taskiq_module.scheduler:scheduler`.

Components:

- `AioPikaBroker` (RabbitMQ) — task execution transport (`broker.py`).
- `RedisScheduleSource` — persistent schedule storage (`services/source.py`).
- `RedisAsyncResultBackend` — task result storage (attached in `broker.py`).
- `TaskiqScheduler` — built from broker + schedule source (`scheduler.py`).

## Hard Rules

- Feature modules must never instantiate their own broker; declare tasks via `taskiq_broker`.
- All scheduling must go through `services/scheduling.py`; never call `schedule_by_time`
  directly from feature code, so the UTC guard is always applied.
- `ensure_utc` is the single normalization point. Naive datetimes must be rejected, not guessed.
- Keep app-level startup/shutdown wiring in `app/lifecycle.py`, not in feature modules.
- Read configuration from `config.py` (`taskiq_settings`), never from `.env` in submodules.
- Do not wire the debug router into `app/api/router.py` unconditionally — it is gated by
  `debug` + `taskiq_debug_endpoints_enabled`.

## Ownership Boundaries

This module owns:

- broker / result backend / schedule source / scheduler construction;
- task auto-discovery;
- generic scheduling, cancellation, listing and immediate enqueue helpers;
- UTC normalization of scheduled times;
- taskiq-specific config projection;
- debug HTTP endpoints for manual schedule checks.

This module does not own:

- concrete business tasks (those live in each feature module's `tasks.py`);
- Telegram/notification workflows or payload semantics;
- generic DB/CRUD infrastructure from `system`.

## Preferred Imports

Feature modules should prefer the public exports:

```python
from app.modules.taskiq_module import taskiq_broker        # declare tasks
from app.modules.taskiq_module import (                     # schedule / enqueue
    schedule_task_at, schedule_task_after, schedule_task_cron,
    cancel_scheduled_task, list_scheduled_tasks, enqueue_task, ensure_utc,
)
```

## How A Feature Module Adds Tasks

Create `app/modules/<feature>/tasks.py`:

```python
from app.modules.taskiq_module import taskiq_broker

@taskiq_broker.task
async def send_telegram_notification(chat_id: int, text: str) -> None:
    ...
```

Discovery imports it automatically — no edits to this module are required. Then schedule it:

```python
from app.modules.taskiq_module import schedule_task_at
from app.modules.<feature>.tasks import send_telegram_notification

schedule_id = await schedule_task_at(send_telegram_notification, when, chat_id=1, text="hi")
```

## Scheduling Contract

- `schedule_task_at(task, when, *a, **kw) -> str` — `when` must be tz-aware; normalized to UTC.
- `schedule_task_after(task, delay: timedelta, *a, **kw) -> str` — relative to `now(UTC)`.
- `schedule_task_cron(task, cron: str, *a, **kw) -> str` — recurring (cron is UTC).
- `cancel_scheduled_task(schedule_id)` / `list_scheduled_tasks()` — manage existing schedules.
- `enqueue_task(task, *a, **kw) -> AsyncTaskiqTask` — run now; await `.wait_result()` if needed.

If scheduling is unavailable (taskiq disabled or no `redis_url`), helpers raise
`TaskiqConfigurationError` with a clear message instead of a low-level `AttributeError`.

## Runtime Expectations

- `startup_taskiq_runtime()` is a no-op when `taskiq_enabled=false` and is safe to always call.
- In the API process it discovers tasks and starts broker + schedule source.
- Worker discovery happens via the `TaskiqEvents.WORKER_STARTUP` hook in `broker.py`.
- Scheduler discovery happens at import time in `scheduler.py`.
- The `broker.is_worker_process` guard prevents double startup inside the worker.

## Editing Guidance

- Put new scheduling behavior in `services/scheduling.py`.
- Keep `handlers.py` thin: HTTP transport only, delegating to services.
- Keep config projection in `config.py`; if a setting is added, update both
  `app/core/config.py` and `.env.example`.
- If a change affects startup/shutdown, update `runtime.py` and `app/lifecycle.py` together.
- If a change affects developer usage, update `README.md`.
