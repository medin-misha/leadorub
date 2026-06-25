from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class TelegramButton(BaseModel):
    text: str
    url: str | None = Field(default=None, description="URL for inline button")
    callback_data: str | None = Field(
        default=None, description="Callback data for inline button"
    )
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
            # Совместимость: корректное написание request_contact мапим в исторический typo
            if "request_contact" in data and "requests_contect" not in data:
                data["requests_contect"] = data["request_contact"]
        return data


class TelegramNotification(BaseModel):
    # Рассылка приходит ОДНИМ сообщением со списком получателей — бот сам перебирает.
    chat_ids: list[int | str]
    message: str | None = None  # текст или подпись к файлу
    use_buttons: Literal["INLINE", "REPLY"] | None = None
    buttons: list[TelegramButton] | None = None  # плоский список
    file_id: int | None = None  # id модели File бэкенда (не Telegram file_id)
    # Идемпотентность рассылки: общий id всех чанков одной рассылки. None =
    # дедуп выключен (старое сообщение / degrade на стороне бота).
    broadcast_id: str | None = None
    # Диагностика чанкования (для логов).
    chunk_index: int | None = None
    chunk_total: int | None = None
