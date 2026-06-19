from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class RMQMessage(BaseModel):
    event: str = Field(min_length=1)
    payload: dict[str, Any]
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = Field(min_length=1)
    correlation_id: str | None = None
