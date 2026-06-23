import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.system import CRUD
from app.modules.system.services.errors import DBErrorHandler

from ..models import TelegramUser, UserProfile, UserStats
from ..schemas import (
    TelegramUserRegister,
    UserProfileCreate,
    UserProfileRegister,
    UserStatsCreate,
    UserStatsRegister,
)


logger = logging.getLogger(__name__)


async def create_telegram_user(
    data: TelegramUserRegister,
    session: AsyncSession,
) -> tuple[TelegramUser, bool]:
    """
    Атомарно регистрирует пользователя: создаёт TelegramUser + UserProfile + UserStats.

    Все три вставки выполняются в рамках одной транзакции сессии (коммит происходит
    на уровне `database.get_session`). Если падает создание профиля или статистики,
    `DBErrorHandler` поднимает HTTPException, и вся транзакция откатывается — частично
    созданного пользователя не остаётся.

    Идемпотентность обеспечивается `CRUD.get_or_create` по `telegram_id`: если
    пользователь уже существует, связанные модели не пересоздаются и возвращается
    `created=False`.
    """
    # 1. Идентичность Telegram. get_or_create защищает от гонок по unique telegram_id.
    telegram_user, created = await CRUD.get_or_create(
        data=data.telegram_user,
        model=TelegramUser,
        session=session,
        lookup_fields=("telegram_id",),
    )

    # Пользователь уже зарегистрирован: профиль и статистика созданы ранее.
    if not created:
        return telegram_user, False

    # 2. Профиль. При отсутствии входных данных создаётся пустым.
    profile_data = data.profile or UserProfileRegister()
    await CRUD.create(
        data=UserProfileCreate(
            telegram_user_id=telegram_user.id,
            **profile_data.model_dump(),
        ),
        model=UserProfile,
        session=session,
    )

    # 3. Статистика. last_seen_at = момент регистрации.
    stats_data = data.stats or UserStatsRegister()
    await CRUD.create(
        data=UserStatsCreate(
            telegram_user_id=telegram_user.id,
            last_seen_at=datetime.now(timezone.utc),
            **stats_data.model_dump(),
        ),
        model=UserStats,
        session=session,
    )

    # Связи заданы через FK, на родителе ещё не загружены — подгружаем для ответа.
    await session.refresh(telegram_user, attribute_names=["user_profile", "user_stats"])
    return telegram_user, True


async def bulk_create_telegram_users(
    data: list[TelegramUserRegister],
    session: AsyncSession,
) -> list[TelegramUser]:
    """
    Массовая регистрация: для каждого элемента создаёт TelegramUser + UserProfile + UserStats.

    В отличие от `create_telegram_user`, не выполняет проверку идемпотентности —
    дубликат `telegram_id` приведёт к IntegrityError (400). Вся партия пишется в
    одной транзакции, поэтому при сбое любого элемента откатывается целиком.
    """
    if not data:
        return []

    # 1. Идентичности. bulk_create делает flush и заполняет id у каждой записи.
    telegram_users = await CRUD.bulk_create(
        data=[item.telegram_user for item in data],
        model=TelegramUser,
        session=session,
    )

    now = datetime.now(timezone.utc)

    # 2. Профили.
    profiles = [
        UserProfileCreate(
            telegram_user_id=telegram_user.id,
            **(item.profile or UserProfileRegister()).model_dump(),
        )
        for item, telegram_user in zip(data, telegram_users)
    ]
    await CRUD.bulk_create(data=profiles, model=UserProfile, session=session)

    # 3. Статистика.
    stats = [
        UserStatsCreate(
            telegram_user_id=telegram_user.id,
            last_seen_at=now,
            **(item.stats or UserStatsRegister()).model_dump(),
        )
        for item, telegram_user in zip(data, telegram_users)
    ]
    await CRUD.bulk_create(data=stats, model=UserStats, session=session)

    for telegram_user in telegram_users:
        await session.refresh(
            telegram_user, attribute_names=["user_profile", "user_stats"]
        )
    return telegram_users


async def login_telegram_user(
    telegram_id: int,
    session: AsyncSession,
) -> TelegramUser:
    """
    Логин пользователя по telegram_id с обновлением `last_seen_at` в UserStats.

    Это событие записи, а не чистое чтение: помимо поиска пользователя обновляется
    время последнего захода в связанной модели UserStats.
    """
    try:
        result = await session.execute(
            select(TelegramUser).where(TelegramUser.telegram_id == telegram_id)
        )
        telegram_user = result.scalars().first()

        if telegram_user is None:
            raise HTTPException(
                status_code=404,
                detail=f"TelegramUser with telegram_id={telegram_id} not found.",
            )

        # last_seen_at переехал в UserStats; selectin уже загрузил связь.
        if telegram_user.user_stats is not None:
            telegram_user.user_stats.last_seen_at = datetime.now(timezone.utc)
            await session.flush()
            await session.refresh(telegram_user, attribute_names=["user_stats"])
    except HTTPException:
        raise
    except Exception as err:
        DBErrorHandler.handle(err=err, model=TelegramUser, action="logging in")
    else:
        return telegram_user
