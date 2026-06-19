from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScheduleAtRequest(BaseModel):
    when: datetime = Field(description="Timezone-aware дата; приводится к UTC")
    message: str


class ScheduleAfterRequest(BaseModel):
    delay_seconds: int = Field(
        gt=0, description="Через сколько секунд от now() запустить"
    )
    message: str


class ScheduleResponse(BaseModel):
    schedule_id: str


class ScheduledTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    schedule_id: str
    task_name: str
    time: datetime | None = None
    cron: str | None = None
    args: list[Any] = []
    kwargs: dict[str, Any] = {}
