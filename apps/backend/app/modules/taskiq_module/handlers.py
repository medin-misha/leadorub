from datetime import timedelta

from fastapi import APIRouter, status

from .schemas import (
    ScheduleAfterRequest,
    ScheduleAtRequest,
    ScheduledTaskRead,
    ScheduleResponse,
)
from .services import (
    cancel_scheduled_task,
    list_scheduled_tasks,
    schedule_task_after,
    schedule_task_at,
)
from .tasks import send_reminder

# Debug-роутер для ручной проверки отложенных задач. Подключается в
# app/api/router.py только когда debug и debug_endpoints_enabled включены.
router = APIRouter(prefix="/taskiq", tags=["taskiq"])


@router.post("/schedule", response_model=ScheduleResponse)
async def schedule_reminder(data: ScheduleAtRequest) -> ScheduleResponse:
    schedule_id = await schedule_task_at(send_reminder, data.when, message=data.message)
    return ScheduleResponse(schedule_id=schedule_id)


@router.post("/schedule/after", response_model=ScheduleResponse)
async def schedule_reminder_after(data: ScheduleAfterRequest) -> ScheduleResponse:
    schedule_id = await schedule_task_after(
        send_reminder, timedelta(seconds=data.delay_seconds), message=data.message
    )
    return ScheduleResponse(schedule_id=schedule_id)


@router.get("/schedules", response_model=list[ScheduledTaskRead])
async def get_schedules() -> list[ScheduledTaskRead]:
    tasks = await list_scheduled_tasks()
    return [ScheduledTaskRead.model_validate(task) for task in tasks]


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(schedule_id: str) -> None:
    await cancel_scheduled_task(schedule_id)
