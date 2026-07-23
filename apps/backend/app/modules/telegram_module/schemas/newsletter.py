import re
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, model_validator

# Лимит Telegram на callback_data inline-кнопки — 64 БАЙТА (UTF-8), не символа.
# Зеркалит CALLBACK_DATA_MAX_BYTES во фронте: при превышении Telegram отклоняет
# отправку, и рассылка не доставляется.
CALLBACK_DATA_MAX_BYTES = 64

# Telegram принимает в URL inline-кнопки только http(s) и deep-link tg://.
_URL_SCHEMES = {"http", "https", "tg"}
# IPv4 (1.2.3.4) — «TLD» числовой, разрешаем отдельным правилом.
_IPV4_RE = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")


def _is_valid_http_host(host: str) -> bool:
    """Хост http(s)-ссылки должен быть «настоящим» доменом: с точкой и TLD из ≥2
    символов, либо IPv4. urlsplit, как и new URL() во фронте, пропускает одно-словные
    хосты (asdasd, localhost) — а Telegram их отклоняет («Wrong HTTP URL»)."""
    if not host:
        return False
    if _IPV4_RE.match(host):
        return True
    labels = host.split(".")
    if len(labels) < 2:  # нужен хотя бы один TLD
        return False
    if any(
        not label for label in labels
    ):  # пустая метка → ведущая/висячая/двойная точка
        return False
    return len(labels[-1]) >= 2


def _is_valid_button_url(value: str) -> bool:
    """Валиден ли URL inline-кнопки: схема http(s)/tg, для http(s) — реальный домен.
    Зеркало фронтовой проверки (stores/newsletter.js) — второй барьер для запросов
    в обход админ-панели."""
    parts = urlsplit(value.strip())
    if parts.scheme not in _URL_SCHEMES:
        return False
    if parts.scheme == "tg":  # deep-link внутрь Telegram, домен не нужен
        return True
    return _is_valid_http_host(parts.hostname or "")


class NewsletterFilters(BaseModel):
    """Фильтр аудитории — та же семантика, что у GET /telegram/users."""

    search: str | None = None
    field: str | None = None


class NewsletterButton(BaseModel):
    """Кнопка рассылки. url/callback_data — только для INLINE."""

    text: str
    url: str | None = None
    callback_data: str | None = None


class NewsletterContent(BaseModel):
    """Контент сообщения рассылки (текст + кнопки) без аудитории.

    Общая база для обычной рассылки (NewsletterRequest) и капельной
    (DripNewsletterCreate): валидация кнопок должна быть одинаковой везде,
    где контент в итоге уезжает в build_newsletter_payload.
    """

    text: str | None = None
    use_buttons: Literal["INLINE", "REPLY"] | None = None
    buttons: list[NewsletterButton] | None = None

    @model_validator(mode="after")
    def _validate_buttons(self) -> "NewsletterContent":
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
                # url — валидная ссылка, иначе Telegram вернёт «Wrong HTTP URL»
                if has_url and not _is_valid_button_url(btn.url):
                    raise ValueError(f"invalid inline button url: {btn.url!r}")
                # callback_data — не длиннее лимита Telegram (64 байта UTF-8)
                if has_cb:
                    cb_bytes = len(btn.callback_data.encode("utf-8"))
                    if cb_bytes > CALLBACK_DATA_MAX_BYTES:
                        raise ValueError(
                            f"callback_data must be at most "
                            f"{CALLBACK_DATA_MAX_BYTES} bytes"
                        )
        return self


class NewsletterRequest(NewsletterContent):
    filters: NewsletterFilters = Field(default_factory=NewsletterFilters)


class NewsletterResult(BaseModel):
    status: str
    recipients: int
    # Общий id всех чанков рассылки — для трассировки/дедупа на стороне бота.
    broadcast_id: str | None = None
