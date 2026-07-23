from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field

from .newsletter import NewsletterButton, NewsletterContent


class DripNewsletterCreate(NewsletterContent):
    """Создание правила капельной рассылки.

    Наследует контент и валидацию кнопок от NewsletterContent; добавляет
    триггер: состояние, задержку в днях и время отправки (в drip_timezone).
    """

    title: str | None = Field(default=None, max_length=255)
    trigger_state: str = Field(min_length=1, max_length=255)
    days_offset: int = Field(ge=0, le=365)
    # pydantic парсит "HH:MM" / "HH:MM:SS" в datetime.time.
    send_time: time


class DripNewsletterPatch(BaseModel):
    """Правка правила: только название и вкл/выкл.

    Контент в v1 не редактируется — правило пересоздают. Так лог отправок
    остаётся честным: он привязан к id правила и не может относиться
    к «другому» контенту.
    """

    title: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class DripNewsletterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str | None = None
    trigger_state: str
    days_offset: int
    send_time: time
    text: str | None = None
    use_buttons: str | None = None
    buttons: list[NewsletterButton] | None = None
    file_id: int | None = None
    is_active: bool
    # Сколько пользователей уже получили это правило (из лога отправок).
    sent_count: int = 0
    created_at: datetime
    updated_at: datetime
