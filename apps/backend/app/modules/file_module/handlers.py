import logging
import mimetypes
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, UploadFile, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import database
from app.core.config import settings
from app.modules.admin_module.dependencies import (
    require_admin,
    require_admin_or_service,
)
from app.modules.system import CRUD

from .models import File
from .schemas import FileCreate, FileRead
from .services import s3_client
from .utils import sanitize_filename, validate_upload_size

router = APIRouter(prefix="/files", tags=["Files"])
logger = logging.getLogger(__name__)

SessionDep = Annotated[AsyncSession, Depends(database.get_session)]

# MIME-типы, которые браузер способен выполнить как активный top-level документ
# (исполнить встроенный <script>). Если отдать такой файл с его «настоящим» MIME,
# открытие ссылки в новой вкладке исполнит скрипт в origin'е админ-панели —
# Stored XSS (например, evil.svg, присланный внешним пользователем в чат).
# Поэтому подобные типы принудительно понижаем до application/octet-stream,
# чтобы браузер скачивал файл, а не рендерил его.
DANGEROUS_INLINE_MIME_TYPES: frozenset[str] = frozenset(
    {
        "image/svg+xml",
        "text/html",
        "application/xhtml+xml",
        "text/xml",
        "application/xml",
    }
)


@router.post(
    "/",
    response_model=FileRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def upload_file(
    session: SessionDep,
    file: UploadFile,
    note: Annotated[str | None, Form()] = None,
) -> File:
    await validate_upload_size(
        file, max_size_bytes=settings.file_upload_max_size_bytes
    )
    filename = sanitize_filename(file.filename)
    link = await s3_client.create(
        file_obj=file.file,
        filename=filename,
        content_type=file.content_type or "application/octet-stream",
    )
    try:
        return await CRUD.create(
            data=FileCreate(link=link, name=filename, note=note),
            model=File,
            session=session,
        )
    except Exception:
        await s3_client.delete(link)
        raise


@router.get(
    "/{id}",
    response_class=StreamingResponse,
    dependencies=[Depends(require_admin_or_service)],
)
async def download_file(
    id: int,
    session: SessionDep,
) -> StreamingResponse:
    file_record: File = await CRUD.get(model=File, session=session, id=id)
    stream_gen = s3_client.stream(link=file_record.link)

    content_type, _ = mimetypes.guess_type(file_record.name)
    media_type = content_type or "application/octet-stream"
    # Опасные для инлайнового рендера типы понижаем до octet-stream, чтобы
    # браузер их скачивал, а не исполнял как документ (защита от Stored XSS).
    if media_type in DANGEROUS_INLINE_MIME_TYPES:
        media_type = "application/octet-stream"

    encoded_name = quote(file_record.name, safe="")
    return StreamingResponse(
        stream_gen,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}",
            # Запрещаем браузеру угадывать MIME по содержимому — иначе он мог бы
            # «распознать» octet-stream как SVG/HTML и всё равно отрендерить.
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/{id}", dependencies=[Depends(require_admin)])
async def delete_file(
    id: int,
    session: SessionDep,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    file_record: File = await CRUD.get(model=File, session=session, id=id)
    link = file_record.link

    # DB first — transactional. If this fails, S3 file is untouched.
    await session.delete(file_record)
    await session.flush()

    # S3 after commit — best-effort. If this fails, the DB record is already
    # gone so no broken link exists; the orphaned object can be cleaned manually.
    async def delete_s3_file(s3_link: str):
        try:
            await s3_client.delete(link=s3_link)
        except Exception:
            logger.warning(
                "S3 delete failed for link %s after DB record was removed", s3_link
            )

    background_tasks.add_task(delete_s3_file, link)

    return {"status": "ok"}
