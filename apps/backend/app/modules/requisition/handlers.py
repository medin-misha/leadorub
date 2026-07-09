from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
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
