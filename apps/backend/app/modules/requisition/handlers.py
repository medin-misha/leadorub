from typing import Annotated

from fastapi import APIRouter, Depends, Query, status, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import database
from app.modules.admin_module.dependencies import require_admin, require_service
from app.modules.system import CRUD

from .models import Requisition
from .schemas import RequisitionCreate, RequisitionRead, RequisitionStatusUpdate
from .services import (
    create_requisition as create_requisition_service,
    list_requisitions as list_requisitions_service,
    update_requisition_status as update_requisition_status_service,
)

router = APIRouter(prefix="/requisitions", tags=["requisitions"])

SessionDep = Annotated[AsyncSession, Depends(database.get_session)]


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


from pydantic import BaseModel, Field

class RequisitionPublicCreate(BaseModel):
    telegram_id: int = Field(..., description="ID пользователя в Telegram")
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
    x_telegram_init_data: Annotated[str | None, Header()] = None,
) -> Requisition:
    """Создание заявки напрямую из клиентского Mini App с проверкой Telegram initData."""
    from app.core.config import settings
    from app.modules.telegram_module.utils import validate_telegram_init_data

    # В режиме debug при отсутствии initData разрешаем тестовую запись
    is_valid = False
    if settings.debug and not x_telegram_init_data:
        is_valid = True
    else:
        # Валидируем initData с помощью токена бота
        is_valid = validate_telegram_init_data(
            init_data=x_telegram_init_data,
            bot_token=settings.user_bot or "",
        )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидные данные авторизации Telegram (initData).",
        )

    requisition_data = RequisitionCreate(
        telegram_id=data.telegram_id,
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
