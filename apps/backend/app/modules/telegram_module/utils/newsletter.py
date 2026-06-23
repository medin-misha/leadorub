from ..schemas.newsletter import NewsletterRequest


def build_newsletter_payload(
    chat_ids: list, request: NewsletterRequest, file_id: int | None
) -> dict:
    """Собирает payload RMQ-сообщения для бота из запроса рассылки.

    Контракт (см. docs/specs/2026-06-23-newsletter-broadcast-design.md):
    chat_ids — все получатели одним сообщением; use_buttons — единый ключ;
    buttons — плоский список; file_id — id модели File бэкенда (или None).
    """
    return {
        "chat_ids": chat_ids,
        "message": request.text,
        "use_buttons": request.use_buttons,
        "buttons": (
            [btn.model_dump(exclude_none=True) for btn in request.buttons]
            if request.buttons
            else None
        ),
        "file_id": file_id,
    }
