from fastapi import HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool


async def validate_upload_size(file: UploadFile, *, max_size_bytes: int) -> int:
    """Проверяет реальный размер multipart-файла и возвращает позицию в начало.

    Заголовку Content-Length доверять нельзя: клиент может не передать его или
    указать размер всего multipart-тела. Поэтому размер берём из уже заполненного
    SpooledTemporaryFile, который FastAPI передаёт как ``UploadFile.file``.
    """

    def measure() -> int:
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        return size

    size = await run_in_threadpool(measure)
    if size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File must not exceed {max_size_bytes} bytes",
        )
    return size
