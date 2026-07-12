from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import database
from app.modules.admin_module.dependencies import require_admin, require_service
from app.modules.admin_module.services.login_rate_limit import (
    LoginRateLimiter,
    get_client_ip,
)
from app.modules.system import CRUD
from app.modules.telegram_module.utils import parse_telegram_init_data

from .models import Requisition
from .schemas import RequisitionCreate, RequisitionRead, RequisitionStatusUpdate
from .services import (
    create_requisition as create_requisition_service,
    list_requisitions as list_requisitions_service,
    update_requisition_status as update_requisition_status_service,
)

router = APIRouter(prefix="/requisitions", tags=["requisitions"])

SessionDep = Annotated[AsyncSession, Depends(database.get_session)]

public_requisition_rate_limiter = LoginRateLimiter(
    attempts=settings.public_requisition_rate_limit_attempts,
    ip_attempts=settings.public_requisition_rate_limit_ip_attempts,
    window_seconds=settings.public_requisition_rate_limit_window_seconds,
)


@router.post(
    "",
    response_model=RequisitionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_service)],
)
async def create_requisition(
    data: RequisitionCreate,
    session: SessionDep,
) -> Requisition:
    """Создание новой заявки от имени пользователя (вызывается Telegram-ботом).

    Доступно только по X-Service-Token.
    """
    return await create_requisition_service(data=data, session=session)


class RequisitionPublicCreate(BaseModel):
    type: str = Field("consultation", description="Тип заявки")
    name: str = Field(..., description="Имя клиента")
    phone: str = Field(..., description="Телефон клиента")
    description: str | None = Field(None, description="Описание проблемы")


@router.post(
    "/public",
    response_model=RequisitionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_public_requisition(
    data: RequisitionPublicCreate,
    session: SessionDep,
    request: Request,
    telegram_init_data: Annotated[str, Header(alias="X-Telegram-Init-Data")],
) -> Requisition:
    """Создание заявки из Client Mini App с проверкой подписи Telegram."""
    if not settings.user_bot:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram WebApp authentication is not configured",
        )

    init_data = parse_telegram_init_data(
        telegram_init_data,
        settings.user_bot,
        max_age_seconds=settings.telegram_init_data_max_age_seconds,
    )
    telegram_id = init_data.get("user", {}).get("id") if init_data else None
    if (
        not isinstance(telegram_id, int)
        or isinstance(telegram_id, bool)
        or telegram_id <= 0
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Telegram initData",
        )

    client_ip = get_client_ip(
        request, settings.admin_login_trusted_proxy_cidrs
    )
    retry_after = await public_requisition_rate_limiter.acquire(
        client_ip=client_ip,
        username=str(telegram_id),
    )
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requisitions. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    requisition_data = RequisitionCreate(
        telegram_id=telegram_id,
        type=data.type,
        payload={
            "name": data.name,
            "phone": data.phone,
            "description": data.description or "",
            "source": "miniapp",
        },
    )
    return await create_requisition_service(data=requisition_data, session=session)


@router.get(
    "",
    response_model=list[RequisitionRead],
    dependencies=[Depends(require_admin)],
)
async def list_requisitions(
    session: SessionDep,
    status_filter: str | None = Query(
        default=None, alias="status", description="Фильтр по статусу заявки"
    ),
    type_filter: str | None = Query(
        default=None, alias="type", description="Фильтр по типу продукта"
    ),
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1)] = 10,
    search: str | None = None,
) -> list[Requisition]:
    """Получение списка заявок с пагинацией и фильтрами.

    Доступно только для администраторов.
    """
    return await list_requisitions_service(
        session=session,
        status_filter=status_filter,
        type_filter=type_filter,
        page=page,
        limit=limit,
        search=search,
    )


@router.get(
    "/{id}",
    response_model=RequisitionRead,
    dependencies=[Depends(require_admin)],
)
async def get_requisition(
    id: int,
    session: SessionDep,
) -> Requisition:
    """Получение детальной информации о конкретной заявке.

    Доступно только для администраторов.
    """
    return await CRUD.get(model=Requisition, session=session, id=id)


@router.patch(
    "/{id}/status",
    response_model=RequisitionRead,
    dependencies=[Depends(require_admin)],
)
async def update_requisition_status(
    id: int,
    data: RequisitionStatusUpdate,
    session: SessionDep,
) -> Requisition:
    """Обновление статуса заявки администратором (одобрение, отклонение).

    Доступно только для администраторов.
    """
    return await update_requisition_status_service(
        requisition_id=id, data=data, session=session
    )
