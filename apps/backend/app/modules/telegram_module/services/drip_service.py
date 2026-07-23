import logging

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.file_module.models import File
from app.modules.file_module.schemas import FileCreate
from app.modules.file_module.services import s3_client
from app.modules.file_module.utils import sanitize_filename
from app.modules.system import CRUD
from app.modules.system.services.errors import DBErrorHandler

from ..models import DripNewsletter, DripNewsletterSend
from ..schemas import DripNewsletterCreate
from ..utils.limits import MESSAGE_MAX_LENGTH

logger = logging.getLogger(__name__)


async def create_drip_newsletter(
    data: DripNewsletterCreate,
    file: UploadFile | None,
    session: AsyncSession,
) -> DripNewsletter:
    """Создаёт правило капельной рассылки.

    Контент-гейты те же, что у обычной рассылки (send_newsletter): пустое
    сообщение и текст длиннее лимита Telegram отклоняем сразу, а не в момент
    доставки. Файл грузится в S3 с компенсацией: упала запись в БД — объект
    удаляется, чтобы не копить сирот в бакете.
    """
    if not (data.text and data.text.strip()) and file is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Drip newsletter must contain text or a file",
        )

    if data.text and len(data.text) > MESSAGE_MAX_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Text must not exceed {MESSAGE_MAX_LENGTH} characters",
        )

    file_id: int | None = None
    link: str | None = None
    if file is not None:
        filename = sanitize_filename(file.filename)
        link = await s3_client.create(
            file_obj=file.file,
            filename=filename,
            content_type=file.content_type or "application/octet-stream",
        )
        try:
            record = await CRUD.create(
                data=FileCreate(link=link, name=filename, note=None),
                model=File,
                session=session,
            )
        except Exception:
            await s3_client.delete(link)
            raise
        file_id = record.id

    try:
        rule = DripNewsletter(
            title=data.title,
            trigger_state=data.trigger_state,
            days_offset=data.days_offset,
            send_time=data.send_time,
            text=data.text,
            use_buttons=data.use_buttons,
            buttons=(
                [btn.model_dump(exclude_none=True) for btn in data.buttons]
                if data.buttons
                else None
            ),
            file_id=file_id,
        )
        session.add(rule)
        await session.flush()
        await session.refresh(rule)
    except HTTPException:
        raise
    except Exception as err:
        # Транзакция откатится вместе со строкой File — подчищаем и S3-объект.
        if link is not None:
            await s3_client.delete(link)
        DBErrorHandler.handle(err=err, model=DripNewsletter, action="creating")
    return rule


async def list_drip_newsletters(
    session: AsyncSession,
    page: int,
    limit: int,
) -> list[DripNewsletter]:
    """Список правил с количеством уже отправленных (sent_count) одним запросом."""
    stmt = (
        select(DripNewsletter, func.count(DripNewsletterSend.id))
        .outerjoin(
            DripNewsletterSend,
            DripNewsletterSend.drip_newsletter_id == DripNewsletter.id,
        )
        .group_by(DripNewsletter.id)
        .order_by(DripNewsletter.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    try:
        rows = (await session.execute(stmt)).all()
    except Exception as err:
        DBErrorHandler.handle(err=err, model=DripNewsletter, action="reading")
    rules: list[DripNewsletter] = []
    for rule, sent_count in rows:
        # Транзиентный атрибут для DripNewsletterRead (from_attributes).
        rule.sent_count = sent_count
        rules.append(rule)
    return rules


async def delete_drip_newsletter(
    id: int,
    session: AsyncSession,
) -> str | None:
    """Удаляет правило и его лог (CASCADE) + строку File.

    Возвращает S3-link удалённого файла (или None) — сам объект хранилища
    удаляет handler в background task ПОСЛЕ коммита, как в file_module:
    упавший S3-delete не должен откатывать уже принятое решение об удалении.
    """
    rule = await CRUD.get(model=DripNewsletter, session=session, id=id)
    link: str | None = None
    try:
        if rule.file_id is not None:
            file_record = await session.get(File, rule.file_id)
            if file_record is not None:
                link = file_record.link
                await session.delete(file_record)
        await session.delete(rule)
        await session.flush()
    except HTTPException:
        raise
    except Exception as err:
        DBErrorHandler.handle(err=err, model=DripNewsletter, action="deleting")
    return link
