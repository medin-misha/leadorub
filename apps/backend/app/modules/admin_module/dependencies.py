"""
FastAPI-зависимости авторизации backend.

Три гейта:
- `get_current_admin` / `require_admin` — доступ только для админа по Bearer-JWT;
- `require_service` — доступ только для server-to-server вызовов по X-Service-Token;
- `require_admin_or_service` — для эндпоинтов, которые дёргают и админка, и бот.

Токен админа проверяется с обращением к БД (`is_active`) — это позволяет мгновенно
отзывать доступ у удалённого/выключенного администратора.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import database
from app.core.security import decode_access_token

from .models import Admin

# auto_error=False — отсутствие/битый заголовок отдаём как credentials=None,
# чтобы самим контролировать тело и заголовки ответа 401.
_bearer_scheme = HTTPBearer(auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(database.get_session)]
BearerDep = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)]
ServiceTokenDep = Annotated[str | None, Header(alias="X-Service-Token")]


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def _admin_from_credentials(
    session: AsyncSession, credentials: HTTPAuthorizationCredentials | None
) -> Admin | None:
    """Достаёт активного админа из Bearer-JWT либо возвращает None."""

    if credentials is None:
        return None
    payload = decode_access_token(credentials.credentials)
    if not payload:
        return None
    sub = payload.get("sub")
    if sub is None:
        return None
    try:
        admin_id = int(sub)
    except (TypeError, ValueError):
        return None
    admin = await session.get(Admin, admin_id)
    if admin is None or not admin.is_active:
        return None
    return admin


async def get_current_admin(
    session: SessionDep,
    credentials: BearerDep = None,
) -> Admin:
    """Возвращает текущего администратора по Bearer-JWT или бросает 401."""

    admin = await _admin_from_credentials(session, credentials)
    if admin is None:
        raise _unauthorized()
    return admin


# Алиас для использования в `dependencies=[Depends(require_admin)]`, когда
# сам объект админа в обработчике не нужен — только факт авторизации.
require_admin = get_current_admin


def _service_token_valid(token: str | None) -> bool:
    """Проверяет X-Service-Token против настроенного секрета.

    Если service_token не сконфигурирован — любой запрос невалиден (fail-closed).
    """

    return bool(settings.service_token) and token == settings.service_token


async def require_service(x_service_token: ServiceTokenDep = None) -> None:
    """Гейт для server-to-server вызовов (юзер-бот → backend)."""

    if not _service_token_valid(x_service_token):
        raise _unauthorized()


async def require_admin_or_service(
    session: SessionDep,
    credentials: BearerDep = None,
    x_service_token: ServiceTokenDep = None,
) -> None:
    """Пропускает, если запрос пришёл либо от админа (JWT), либо от бота (токен)."""

    if _service_token_valid(x_service_token):
        return
    if await _admin_from_credentials(session, credentials) is not None:
        return
    raise _unauthorized()
