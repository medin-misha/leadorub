from ..schemas.newsletter import NewsletterContent


def build_newsletter_payload(
    chat_ids: list,
    request: NewsletterContent,
    file_id: int | None,
    broadcast_id: str,
    chunk_index: int,
    chunk_total: int,
) -> dict:
    """Собирает payload RMQ-сообщения для бота из запроса рассылки.

    chat_ids — получатели ОДНОГО чанка (не вся аудитория); broadcast_id — общий
    id всех чанков рассылки (для идемпотентности на стороне бота); chunk_index/
    chunk_total — диагностика для логов. use_buttons — единый ключ; buttons —
    плоский список; file_id — id модели File бэкенда (или None).
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
        "broadcast_id": broadcast_id,
        "chunk_index": chunk_index,
        "chunk_total": chunk_total,
    }
