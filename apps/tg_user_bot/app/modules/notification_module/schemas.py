from typing import Any
from pydantic import BaseModel, Field, model_validator


class TelegramButton(BaseModel):
    text: str
    requests_contect: bool | None = Field(
        default=None, description="Request contact button (user-specified spelling)"
    )
    request_location: bool | None = Field(
        default=None, description="Request location button"
    )
    web_app: str | None = Field(default=None, description="Web App URL")

    @model_validator(mode="before")
    @classmethod
    def handle_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Fallback mappings for robust field parsing
            if "request_contact" in data and "requests_contect" not in data:
                data["requests_contect"] = data["request_contact"]
        return data


class TelegramNotification(BaseModel):
    chat_id: int | str
    message: str
    inline_buttons: bool | None = Field(default=None)
    reply_buttons: bool | None = Field(default=None)
    buttons: list[list[TelegramButton]] | None = Field(default=None)
