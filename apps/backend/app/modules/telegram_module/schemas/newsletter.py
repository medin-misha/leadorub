from typing import Literal

from pydantic import BaseModel, Field, model_validator


class NewsletterFilters(BaseModel):
    """Фильтр аудитории — та же семантика, что у GET /telegram/users."""

    search: str | None = None
    field: str | None = None


class NewsletterButton(BaseModel):
    """Кнопка рассылки. url/callback_data — только для INLINE."""

    text: str
    url: str | None = None
    callback_data: str | None = None


class NewsletterRequest(BaseModel):
    filters: NewsletterFilters = Field(default_factory=NewsletterFilters)
    text: str | None = None
    use_buttons: Literal["INLINE", "REPLY"] | None = None
    buttons: list[NewsletterButton] | None = None

    @model_validator(mode="after")
    def _validate_buttons(self) -> "NewsletterRequest":
        # buttons и use_buttons включаются только вместе
        if self.buttons and not self.use_buttons:
            raise ValueError("use_buttons must be set when buttons are provided")
        if self.use_buttons and not self.buttons:
            raise ValueError("buttons must be provided when use_buttons is set")
        # для INLINE у каждой кнопки ровно одно из url / callback_data
        if self.use_buttons == "INLINE" and self.buttons:
            for btn in self.buttons:
                has_url = bool(btn.url)
                has_cb = bool(btn.callback_data)
                if has_url == has_cb:  # оба или ни одного
                    raise ValueError(
                        "each INLINE button needs exactly one of url / callback_data"
                    )
        return self


class NewsletterResult(BaseModel):
    status: str
    recipients: int
    # Общий id всех чанков рассылки — для трассировки/дедупа на стороне бота.
    broadcast_id: str | None = None
