"""
Бизнес-логика администраторов: аутентификация, bootstrap при старте и
управление учётками (создание/изменение/удаление) с защитой от self-lockout.
"""

from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import database
from app.core.security import hash_password, verify_password
from app.modules.system import CRUD

from ..models import Admin
from ..schemas import AdminCreate, AdminPatch

logger = logging.getLogger(__name__)


async def get_admin_by_username(session: AsyncSession, username: str) -> Admin | None:
    """Возвращает админа по username или None."""

    result = await session.execute(select(Admin).where(Admin.username == username))
    return result.scalars().first()


async def authenticate(
    session: AsyncSession, username: str, password: str
) -> Admin | None:
    """Проверяет логин/пароль. Возвращает активного админа или None.

    Никогда не различает «нет такого username» и «неверный пароль» —
    наружу отдаём единый отрицательный результат, чтобы не помогать перебору.
    """

    admin = await get_admin_by_username(session, username)
    if admin is None or not admin.is_active:
        return None
    if not verify_password(password, admin.hashed_password):
        return None
    return admin


async def create_admin(session: AsyncSession, data: AdminCreate) -> Admin:
    """Создаёт нового администратора. 400, если username уже занят."""

    if await get_admin_by_username(session, data.username) is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin with this username already exists.",
        )

    admin = Admin(
        username=data.username,
        hashed_password=hash_password(data.password),
        is_active=True,
    )
    session.add(admin)
    await session.flush()
    await session.refresh(admin)
    return admin


async def list_admins(
    session: AsyncSession, page: int = 1, limit: int = 50
) -> list[Admin]:
    """Список администраторов (с пагинацией через общий CRUD)."""

    return await CRUD.get(model=Admin, session=session, page=page, limit=limit)


async def update_admin(
    session: AsyncSession,
    admin_id: int,
    data: AdminPatch,
    current_admin: Admin,
) -> Admin:
    """Обновляет пароль и/или активность.

    Запрещаем деактивировать самого себя: иначе админ мгновенно потеряет доступ
    (is_active проверяется на каждом запросе) и может закрыть систему.
    """

    admin: Admin = await CRUD._get_by_id(model=Admin, session=session, id=admin_id)

    if data.is_active is False and admin.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account.",
        )

    if data.password is not None:
        admin.hashed_password = hash_password(data.password)
    if data.is_active is not None:
        admin.is_active = data.is_active

    await session.flush()
    await session.refresh(admin)
    return admin


async def delete_admin(
    session: AsyncSession, admin_id: int, current_admin: Admin
) -> str:
    """Удаляет администратора.

    Запрещаем удалять самого себя — это гарантирует, что в системе всегда
    останется хотя бы один администратор (текущий).
    """

    if admin_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account.",
        )

    return await CRUD.delete(model=Admin, session=session, id=admin_id)


async def bootstrap_admin() -> None:
    """Создаёт первого администратора из .env при старте, если его ещё нет.

    Идемпотентно: если админ с таким username уже существует — ничего не делаем,
    чтобы не затирать сменённый пароль. Вызывается из lifespan после миграций.
    """

    if not settings.admin_username or not settings.admin_password:
        logger.info("Bootstrap admin skipped: admin_username/admin_password not set.")
        return

    async with database.sessionmaker() as session:
        existing = await get_admin_by_username(session, settings.admin_username)
        if existing is not None:
            logger.info("Bootstrap admin '%s' already exists.", settings.admin_username)
            return

        session.add(
            Admin(
                username=settings.admin_username,
                hashed_password=hash_password(settings.admin_password),
                is_active=True,
            )
        )
        await session.commit()
        logger.info("Bootstrap admin '%s' created.", settings.admin_username)
