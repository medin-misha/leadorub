from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FileCreate(BaseModel):
    link: str
    name: str
    note: str | None = None


class FileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    link: str
    name: str
    note: str | None = None
    created_at: datetime
    updated_at: datetime
