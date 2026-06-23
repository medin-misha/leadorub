from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import database
from app.core.security import create_access_token

from .dependencies import get_current_admin, require_admin
from .models import Admin
from .schemas import AdminCreate, AdminPatch, AdminRead, LoginRequest, TokenResponse
from .services import (
    authenticate,
    create_admin as create_admin_service,
    delete_admin as delete_admin_service,
    list_admins as list_admins_service,
    update_admin as update_admin_service,
)

router = APIRouter(prefix="/auth", tags=["auth"])

SessionDep = Annotated[AsyncSession, Depends(database.get_session)]
CurrentAdminDep = Annotated[Admin, Depends(get_current_admin)]


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, session: SessionDep) -> TokenResponse:
    """Логин по username/password. Выдаёт access-JWT либо общий 401."""

    admin = await authenticate(session, username=data.username, password=data.password)
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(subject=admin.id))


@router.get("/me", response_model=AdminRead)
async def get_me(admin: CurrentAdminDep) -> Admin:
    """Возвращает текущего администратора по токену."""

    return admin


@router.get(
    "/admins",
    response_model=list[AdminRead],
    dependencies=[Depends(require_admin)],
)
async def list_admins(
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1)] = 50,
) -> list[Admin]:
    return await list_admins_service(session=session, page=page, limit=limit)


@router.post(
    "/admins",
    response_model=AdminRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_admin(data: AdminCreate, session: SessionDep) -> Admin:
    return await create_admin_service(session=session, data=data)


@router.patch("/admins/{id}", response_model=AdminRead)
async def patch_admin(
    id: int,
    data: AdminPatch,
    session: SessionDep,
    current_admin: CurrentAdminDep,
) -> Admin:
    return await update_admin_service(
        session=session, admin_id=id, data=data, current_admin=current_admin
    )


@router.delete("/admins/{id}")
async def delete_admin(
    id: int,
    session: SessionDep,
    current_admin: CurrentAdminDep,
) -> dict[str, str]:
    result = await delete_admin_service(
        session=session, admin_id=id, current_admin=current_admin
    )
    return {"status": result}
