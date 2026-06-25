from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import database
from app.modules.admin_module.dependencies import require_admin, require_service
from app.modules.telegram_module.utils.limits import MESSAGE_MAX_LENGTH

from .schemas import ChatMessageRead, ConversationRead
from .services import (
    SupportUserNotFound,
    get_messages as get_messages_service,
    list_conversations as list_conversations_service,
    mark_read as mark_read_service,
    send_admin_reply as send_admin_reply_service,
    store_inbound_media as store_inbound_media_service,
)

router = APIRouter(prefix="/chat", tags=["chat"])

SessionDep = Annotated[AsyncSession, Depends(database.get_session)]


# Эндпоинты для админки — под Bearer JWT.
@router.get(
    "/conversations",
    response_model=list[ConversationRead],
    dependencies=[Depends(require_admin)],
)
async def list_conversations(
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    search: str | None = None,
) -> list[ConversationRead]:
    """Список диалогов поддержки с непрочитанными и превью последнего сообщения."""
    return await list_conversations_service(
        session, search=search, page=page, limit=limit
    )


@router.get(
    "/conversations/{telegram_user_id}/messages",
    response_model=list[ChatMessageRead],
    dependencies=[Depends(require_admin)],
)
async def list_messages(
    telegram_user_id: int,
    session: SessionDep,
    after_id: Annotated[int | None, Query(ge=0)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[ChatMessageRead]:
    """Тред одного диалога. `after_id` — для инкрементального polling новых сообщений."""
    return await get_messages_service(
        session, telegram_user_id, after_id=after_id, limit=limit
    )


@router.post(
    "/conversations/{telegram_user_id}/reply",
    response_model=ChatMessageRead,
    dependencies=[Depends(require_admin)],
)
async def reply(
    telegram_user_id: int,
    session: SessionDep,
    text: Annotated[str | None, Form()] = None,
    file: UploadFile | None = None,
) -> ChatMessageRead:
    """Ответ администратора (multipart): текст и/или вложение.

    Сохраняет сообщение, заливает файл (если есть) и отправляет всё пользователю.
    """
    cleaned = text.strip() if text else None
    if not cleaned and file is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reply must contain text or a file",
        )
    # Лимит Telegram (см. telegram_module/utils/limits.py): текст-подпись > 1024
    # уронил бы отправку у бота молча — отдаём явный 400.
    if cleaned and len(cleaned) > MESSAGE_MAX_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Text must not exceed {MESSAGE_MAX_LENGTH} characters",
        )
    return await send_admin_reply_service(
        session, telegram_user_id, text=cleaned, file=file
    )


@router.post(
    "/conversations/{telegram_user_id}/read",
    dependencies=[Depends(require_admin)],
)
async def read(
    telegram_user_id: int,
    session: SessionDep,
) -> dict[str, int | str]:
    """Помечает все сообщения пользователя в диалоге прочитанными."""
    updated = await mark_read_service(session, telegram_user_id)
    return {"status": "ok", "updated": updated}


# Эндпоинт для бота (server-to-server) — под X-Service-Token.
@router.post(
    "/inbound-media",
    response_model=ChatMessageRead,
    dependencies=[Depends(require_service)],
)
async def inbound_media(
    session: SessionDep,
    file: UploadFile,
    telegram_id: Annotated[int, Form()],
    tg_message_id: Annotated[int | None, Form()] = None,
    caption: Annotated[str | None, Form()] = None,
) -> ChatMessageRead:
    """Приём медиа от пользователя: бот скачал файл из Telegram и шлёт его сюда.

    Бинарь идёт по HTTP (не через RMQ). Заливаем в S3, создаём File и строку
    chat_message(direction='user', file_id).
    """
    try:
        return await store_inbound_media_service(
            session,
            telegram_id=telegram_id,
            file=file,
            caption=caption.strip() if caption else None,
            tg_message_id=tg_message_id,
        )
    except SupportUserNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TelegramUser with telegram_id={telegram_id} not found.",
        )
