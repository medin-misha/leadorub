from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Form,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

import logging

from app.core.database import database
from app.core.config import settings
from app.modules.file_module.services import s3_client
from app.modules.file_module.utils import validate_upload_size
from app.modules.admin_module.dependencies import (
    require_admin,
    require_admin_or_service,
    require_service,
)
from app.modules.system import CRUD

from .models import DripNewsletter, TelegramUser, UserProfile, UserStats
from .schemas import (
    DripNewsletterCreate,
    DripNewsletterPatch,
    DripNewsletterRead,
    NewsletterRequest,
    NewsletterResult,
    TelegramUserLogin,
    TelegramUserPatch,
    TelegramUserRead,
    TelegramUserRegister,
    UserStateUpdate,
    UserProfileCreate,
    UserProfilePatch,
    UserProfileRead,
    UserStatsCreate,
    UserStatsPatch,
    UserStatsRead,
)
from .services import (
    bulk_create_telegram_users as bulk_create_telegram_users_service,
    create_drip_newsletter as create_drip_newsletter_service,
    create_telegram_user as create_telegram_user_service,
    delete_drip_newsletter as delete_drip_newsletter_service,
    list_drip_newsletters as list_drip_newsletters_service,
    login_telegram_user as login_telegram_user_service,
    send_newsletter as send_newsletter_service,
    set_user_state as set_user_state_service,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])

SessionDep = Annotated[AsyncSession, Depends(database.get_session)]


async def _delete_s3_object(link: str) -> None:
    try:
        await s3_client.delete(link=link)
    except Exception:
        logger.warning("S3 delete failed for link %s after DB record was removed", link)


# Состояние диалога: бот выставляет позицию пользователя в воронке
# (именованные состояния в user_stats.state) по telegram_id.
@router.put(
    "/state",
    response_model=UserStatsRead,
    dependencies=[Depends(require_service)],
)
async def set_user_state(
    data: UserStateUpdate,
    session: SessionDep,
) -> UserStats:
    return await set_user_state_service(
        telegram_id=data.telegram_id,
        state=data.state,
        session=session,
    )


# TelegramUser
@router.post(
    "/login",
    response_model=TelegramUserRead,
    dependencies=[Depends(require_service)],
)
async def login_telegram_user(
    data: TelegramUserLogin,
    session: SessionDep,
) -> TelegramUser:
    return await login_telegram_user_service(
        telegram_id=data.telegram_id,
        session=session,
    )


@router.post(
    "/users",
    response_model=TelegramUserRead,
    dependencies=[Depends(require_admin_or_service)],
)
async def create_telegram_user(
    data: TelegramUserRegister,
    response: Response,
    session: SessionDep,
) -> TelegramUser:
    telegram_user, created = await create_telegram_user_service(
        data=data, session=session
    )
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return telegram_user


@router.post(
    "/users/bulk",
    response_model=list[TelegramUserRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def bulk_create_telegram_users(
    data: list[TelegramUserRegister],
    session: SessionDep,
) -> list[TelegramUser]:
    return await bulk_create_telegram_users_service(data=data, session=session)


@router.get(
    "/users/{id}",
    response_model=TelegramUserRead,
    dependencies=[Depends(require_admin)],
)
async def get_telegram_user(
    id: int,
    session: SessionDep,
) -> TelegramUser:
    return await CRUD.get(model=TelegramUser, session=session, id=id)


@router.get(
    "/users",
    response_model=list[TelegramUserRead],
    dependencies=[Depends(require_admin)],
)
async def list_telegram_users(
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1)] = 10,
    search: str | None = None,
    field: str | None = None,
) -> list[TelegramUser]:
    return await CRUD.get(
        model=TelegramUser,
        session=session,
        page=page,
        limit=limit,
        search=search,
        field=field,
    )


@router.post(
    "/newsletter",
    response_model=NewsletterResult,
    dependencies=[Depends(require_admin)],
)
async def send_newsletter(
    session: SessionDep,
    payload: Annotated[str, Form()],
    file: UploadFile | None = None,
) -> dict:
    """Запускает рассылку: парсит JSON payload (multipart) и делегирует в сервис.

    payload — JSON тела рассылки (filters/text/use_buttons/buttons);
    file — опциональное вложение (multipart). Логика — в services.
    """
    request = NewsletterRequest.model_validate_json(payload)
    if file is not None:
        await validate_upload_size(
            file, max_size_bytes=settings.newsletter_upload_max_size_bytes
        )
    return await send_newsletter_service(request=request, file=file, session=session)


# Капельные рассылки: правило «состояние → через N дней в HH:MM отправить
# сообщение». Доставку выполняет cron-sweep (services/drip_sweep.py).
@router.post(
    "/drip-newsletters",
    response_model=DripNewsletterRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_drip_newsletter(
    session: SessionDep,
    payload: Annotated[str, Form()],
    file: UploadFile | None = None,
) -> DripNewsletter:
    """Создаёт правило: multipart как у /newsletter — JSON payload + файл."""
    data = DripNewsletterCreate.model_validate_json(payload)
    if file is not None:
        await validate_upload_size(
            file, max_size_bytes=settings.newsletter_upload_max_size_bytes
        )
    return await create_drip_newsletter_service(data=data, file=file, session=session)


@router.get(
    "/drip-newsletters",
    response_model=list[DripNewsletterRead],
    dependencies=[Depends(require_admin)],
)
async def list_drip_newsletters(
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1)] = 10,
) -> list[DripNewsletter]:
    return await list_drip_newsletters_service(session=session, page=page, limit=limit)


@router.patch(
    "/drip-newsletters/{id}",
    response_model=DripNewsletterRead,
    dependencies=[Depends(require_admin)],
)
async def patch_drip_newsletter(
    id: int,
    data: DripNewsletterPatch,
    session: SessionDep,
) -> DripNewsletter:
    return await CRUD.patch(new_data=data, model=DripNewsletter, session=session, id=id)


@router.delete("/drip-newsletters/{id}", dependencies=[Depends(require_admin)])
async def delete_drip_newsletter(
    id: int,
    session: SessionDep,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    link = await delete_drip_newsletter_service(id=id, session=session)
    # S3 — best-effort после коммита, как в file_module: упавший delete не
    # должен откатывать удаление правила.
    if link is not None:
        background_tasks.add_task(_delete_s3_object, link)
    return {"status": "ok"}


@router.patch(
    "/users/{id}",
    response_model=TelegramUserRead,
    dependencies=[Depends(require_admin)],
)
async def patch_telegram_user(
    id: int,
    data: TelegramUserPatch,
    session: SessionDep,
) -> TelegramUser:
    return await CRUD.patch(new_data=data, model=TelegramUser, session=session, id=id)


@router.delete("/users/{id}", dependencies=[Depends(require_admin)])
async def delete_telegram_user(
    id: int,
    session: SessionDep,
) -> dict[str, str]:
    result = await CRUD.delete(model=TelegramUser, session=session, id=id)
    return {"status": result}


# UserProfile
@router.post(
    "/profile",
    response_model=UserProfileRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_user_profile(
    data: UserProfileCreate,
    session: SessionDep,
) -> UserProfile:
    return await CRUD.create(data=data, model=UserProfile, session=session)


@router.get(
    "/profile/{id}",
    response_model=UserProfileRead,
    dependencies=[Depends(require_admin)],
)
async def get_user_profile(
    id: int,
    session: SessionDep,
) -> UserProfile:
    return await CRUD.get(model=UserProfile, session=session, id=id)


@router.get(
    "/profile",
    response_model=list[UserProfileRead],
    dependencies=[Depends(require_admin)],
)
async def list_user_profiles(
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1)] = 10,
    search: str | None = None,
    field: str | None = None,
) -> list[UserProfile]:
    return await CRUD.get(
        model=UserProfile,
        session=session,
        page=page,
        limit=limit,
        search=search,
        field=field,
    )


@router.patch(
    "/profile/{id}",
    response_model=UserProfileRead,
    dependencies=[Depends(require_admin)],
)
async def patch_user_profile(
    id: int,
    data: UserProfilePatch,
    session: SessionDep,
) -> UserProfile:
    return await CRUD.patch(new_data=data, model=UserProfile, session=session, id=id)


@router.delete("/profile/{id}", dependencies=[Depends(require_admin)])
async def delete_user_profile(
    id: int,
    session: SessionDep,
) -> dict[str, str]:
    result = await CRUD.delete(model=UserProfile, session=session, id=id)
    return {"status": result}


# UserStats
@router.post(
    "/stats",
    response_model=UserStatsRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_user_stats(
    data: UserStatsCreate,
    session: SessionDep,
) -> UserStats:
    return await CRUD.create(data=data, model=UserStats, session=session)


@router.get(
    "/stats/{id}",
    response_model=UserStatsRead,
    dependencies=[Depends(require_admin)],
)
async def get_user_stats(
    id: int,
    session: SessionDep,
) -> UserStats:
    return await CRUD.get(model=UserStats, session=session, id=id)


@router.get(
    "/stats",
    response_model=list[UserStatsRead],
    dependencies=[Depends(require_admin)],
)
async def list_user_stats(
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1)] = 10,
    search: str | None = None,
    field: str | None = None,
) -> list[UserStats]:
    return await CRUD.get(
        model=UserStats,
        session=session,
        page=page,
        limit=limit,
        search=search,
        field=field,
    )


@router.patch(
    "/stats/{id}",
    response_model=UserStatsRead,
    dependencies=[Depends(require_admin)],
)
async def patch_user_stats(
    id: int,
    data: UserStatsPatch,
    session: SessionDep,
) -> UserStats:
    return await CRUD.patch(new_data=data, model=UserStats, session=session, id=id)


@router.delete("/stats/{id}", dependencies=[Depends(require_admin)])
async def delete_user_stats(
    id: int,
    session: SessionDep,
) -> dict[str, str]:
    result = await CRUD.delete(model=UserStats, session=session, id=id)
    return {"status": result}
