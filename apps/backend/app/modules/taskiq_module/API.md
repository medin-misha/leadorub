# Taskiq Module

All endpoints of this module are available **only in debug mode**: the `taskiq` router is mounted in
`app/api/router.py` only when both `debug=true` and
`taskiq_debug_endpoints_enabled=true` are enabled. They demonstrate scheduling on the built-in task
`send_reminder` and are not intended for production.

## POST /api/taskiq/schedule

> Schedule a reminder for a specific date. The date must be timezone-aware and is converted to UTC. Available only in debug (taskiq debug flag).

request

```json
{
  "when": "2026-06-02T18:00:00+00:00",
  "message": "Текст напоминания"
}
```

response

```json
{
  "schedule_id": "b7c1e0f2-3a4d-4c9e-8f21-0a1b2c3d4e5f"
}
```

## POST /api/taskiq/schedule/after

> Schedule a reminder after an interval from the current moment (in seconds, `delay_seconds > 0`). The countdown starts from `now(UTC)`. Available only in debug (taskiq debug flag).

request

```json
{
  "delay_seconds": 60,
  "message": "Текст напоминания"
}
```

response

```json
{
  "schedule_id": "b7c1e0f2-3a4d-4c9e-8f21-0a1b2c3d4e5f"
}
```

## GET /api/taskiq/schedules

> Return the list of all active schedules from the schedule source. There is no request body. Available only in debug (taskiq debug flag).

request

```json
{}
```

response

```json
[
  {
    "schedule_id": "b7c1e0f2-3a4d-4c9e-8f21-0a1b2c3d4e5f",
    "task_name": "send_reminder",
    "time": "2026-06-02T18:00:00+00:00",
    "cron": null,
    "args": [],
    "kwargs": { "message": "Текст напоминания" }
  }
]
```

## DELETE /api/taskiq/schedules/{schedule_id}

> Cancel a previously scheduled task by its `schedule_id`. There is no request or response body: on success it returns `204 No Content`. Available only in debug (taskiq debug flag).

Path parameter:

- `schedule_id` (string) — the schedule identifier obtained at creation time (`ScheduleResponse.schedule_id`) or from `GET /api/taskiq/schedules`.

request

```json
{}
```

response

```
204 No Content
```
