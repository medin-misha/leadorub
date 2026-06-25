# Newsletter Broadcast — Backend Producer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `POST /telegram/newsletter` to the backend: validate a broadcast request, confirm the filtered audience is non-empty, upload the optional attachment via `file_module`, and publish ONE RabbitMQ message (with the full `chat_ids` list) to the queue the `tg_user_bot` consumes.

**Architecture:** New endpoint + service inside the existing `telegram_module` (no new module, no DB model, no migration). Recipient counting/fetching reuses the `system` `CRUD` filter logic (extended with generic `count` / `get_column`). The attachment reuses `file_module`'s `s3_client` + `File` model. Publishing reuses `rmq_publisher`. The payload-building and request validation are pure functions, unit-tested with stdlib `unittest`; the service flow is unit-tested with mocked dependencies.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, async SQLAlchemy 2.0, `aio-pika` (via `rmq_publisher`), `aiobotocore` (via `s3_client`). Package manager: `uv`.

## Global Constraints

- **Module architecture (backend CLAUDE.md):** handlers validate/format/delegate only — business logic lives in `services/`.
- **DB access only via** `Depends(database.get_session)` — never instantiate a session in logic.
- **Broker only via `rmq_publisher`** — never import `aio-pika` in business code.
- **No new dependencies** (`uv` only if ever needed; none here). **No new DB model, no Alembic migration.**
- **Code comments in Russian** (matches existing backend module code, e.g. `system/services/crud.py`).
- **RMQ contract — exact values (verbatim):** event `"telegram.newsletter"`, queue `"telegram_notifications"`, routing key `"telegram_notifications"`, exchange `"app.events"`, exchange type `"direct"`.
- **RMQ payload shape (verbatim):** `{ "chat_ids": list[int], "message": str|None, "use_buttons": "INLINE"|"REPLY"|null, "buttons": list[{text,url?,callback_data?}]|null, "file_id": int|null }`.
- **Filter logic is single-source:** recipient count/fetch MUST reuse `CRUD`'s `_get_field_search`/`_get_text_search` — do not copy-paste a divergent filter.

### Verification approach (read first)

The backend has **no pytest and no test directory**. We add stdlib `unittest` tests (the same framework the `tg_user_bot` already uses) under a new `apps/backend/tests/` dir — no new dependency. All commands run from `apps/backend/`:

- **Unit tests:** `uv run python -m unittest discover -s tests -v` (pure validation/payload logic + mocked service flow — no real DB/RMQ).
- **Import/syntax gate:** `uv run python -m compileall app` (catches syntax/import errors in DB-touching code that unit tests don't execute).
- **DB + RMQ + end-to-end** are verified manually on the docker stack after both this plan and the bot plan land (out of scope for per-task automated checks).

---

### Task 1: Extend `system` CRUD with `count` and `get_column`

**Files:**
- Modify: `apps/backend/app/modules/system/services/crud.py`
- Test: `apps/backend/tests/test_crud_filters.py` (create), `apps/backend/tests/__init__.py` (create, empty)

**Interfaces:**
- Consumes: existing `CRUD._get_field_search`, `CRUD._get_text_search`, `DBErrorHandler`.
- Produces:
  - `CRUD._apply_search(stmt, model, search, field) -> stmt` — applies the same search/field filtering `get()` uses.
  - `async CRUD.count(model, session, search=None, field=None) -> int`
  - `async CRUD.get_column(model, session, column, search=None, field=None) -> list` — returns the scalar values of `column` for all matching rows (no pagination).

- [ ] **Step 1: Write the failing test**

Create `apps/backend/tests/__init__.py` (empty file).

Create `apps/backend/tests/test_crud_filters.py`:

```python
import unittest

from sqlalchemy import select, func

from app.modules.system import CRUD
from app.modules.telegram_module.models import TelegramUser


class ApplySearchTests(unittest.TestCase):
    """_apply_search строит тот же фильтр, что и CRUD.get, без обращения к БД."""

    def test_field_search_builds_where_clause(self) -> None:
        stmt = CRUD._apply_search(
            select(TelegramUser), TelegramUser, search="ivan", field="username"
        )
        compiled = str(stmt)
        self.assertIn("WHERE", compiled)
        self.assertIn("username", compiled)

    def test_text_search_builds_where_clause(self) -> None:
        stmt = CRUD._apply_search(
            select(TelegramUser), TelegramUser, search="ivan", field=None
        )
        self.assertIn("WHERE", str(stmt))

    def test_no_search_returns_unfiltered(self) -> None:
        stmt = CRUD._apply_search(
            select(func.count()).select_from(TelegramUser),
            TelegramUser,
            search=None,
            field=None,
        )
        self.assertNotIn("WHERE", str(stmt))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/backend && uv run python -m unittest tests.test_crud_filters -v`
Expected: FAIL — `AttributeError: type object 'CRUD' has no attribute '_apply_search'`.

- [ ] **Step 3: Implement**

In `apps/backend/app/modules/system/services/crud.py`:

a) Add `func` to the `sqlalchemy` import block (line 4-16), so it reads `from sqlalchemy import (insert, select, Result, String, or_, and_, Boolean, Integer, DateTime, Date, Float, func)`.

b) Add these three methods to the `CRUD` class (place them right before the existing `get` method at line 218):

```python
    @staticmethod
    def _apply_search(stmt, model: Type[ModelT], search: str | None, field: str | None):
        """Применяет к запросу ту же фильтрацию search/field, что и `get()`.

        Вынесено отдельно, чтобы count/get_column не дублировали логику фильтра.
        """
        search = search.strip() if search else None
        field = field.strip() if field else None
        if not search:
            return stmt

        mapper: Mapper = inspect(model)
        model_columns = {column.name: column for column in mapper.columns}
        if field is not None:
            return CRUD._get_field_search(
                stmt=stmt,
                model=model,
                model_columns=model_columns,
                field=field,
                search=search,
            )
        return CRUD._get_text_search(
            stmt=stmt,
            model_columns=model_columns,
            search=search,
        )

    @staticmethod
    async def count(
        model: Type[ModelT],
        session: AsyncSession,
        search: str | None = None,
        field: str | None = None,
    ) -> int:
        """Считает записи модели под фильтром search/field (без пагинации)."""
        try:
            stmt = CRUD._apply_search(
                select(func.count()).select_from(model), model, search, field
            )
            result: Result = await session.execute(stmt)
            return int(result.scalar_one())
        except HTTPException:
            raise
        except Exception as err:
            DBErrorHandler.handle(err=err, model=model, action="counting")

    @staticmethod
    async def get_column(
        model: Type[ModelT],
        session: AsyncSession,
        column,
        search: str | None = None,
        field: str | None = None,
    ) -> list:
        """Возвращает значения одной колонки для всех записей под фильтром (без пагинации)."""
        try:
            stmt = CRUD._apply_search(select(column), model, search, field)
            result: Result = await session.execute(stmt)
            return list(result.scalars().all())
        except HTTPException:
            raise
        except Exception as err:
            DBErrorHandler.handle(err=err, model=model, action="reading")
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd apps/backend && uv run python -m unittest tests.test_crud_filters -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Import gate**

Run: `cd apps/backend && uv run python -m compileall app/modules/system/services/crud.py`
Expected: compiles, exit 0.

- [ ] **Step 6: Commit**

```bash
git add apps/backend/app/modules/system/services/crud.py apps/backend/tests/__init__.py apps/backend/tests/test_crud_filters.py
git commit -m "feat(backend): CRUD.count + CRUD.get_column with shared filter logic"
```

---

### Task 2: Newsletter request schemas + payload builder

**Files:**
- Create: `apps/backend/app/modules/telegram_module/schemas/newsletter.py`
- Modify: `apps/backend/app/modules/telegram_module/schemas/__init__.py`
- Create: `apps/backend/app/modules/telegram_module/utils/newsletter.py`
- Test: `apps/backend/tests/test_newsletter_schema.py` (create)

**Interfaces:**
- Produces:
  - `NewsletterFilters{ search: str|None, field: str|None }`
  - `NewsletterButton{ text: str, url: str|None, callback_data: str|None }`
  - `NewsletterRequest{ filters: NewsletterFilters, text: str|None, use_buttons: Literal["INLINE","REPLY"]|None, buttons: list[NewsletterButton]|None }` (validates button/use_buttons consistency)
  - `NewsletterResult{ status: str, recipients: int }`
  - `build_newsletter_payload(chat_ids: list, request: NewsletterRequest, file_id: int|None) -> dict`

- [ ] **Step 1: Write the failing test**

Create `apps/backend/tests/test_newsletter_schema.py`:

```python
import unittest

from pydantic import ValidationError

from app.modules.telegram_module.schemas import NewsletterRequest
from app.modules.telegram_module.utils.newsletter import build_newsletter_payload


class NewsletterRequestValidationTests(unittest.TestCase):
    def test_inline_button_requires_exactly_one_target(self) -> None:
        # both url and callback_data -> invalid
        with self.assertRaises(ValidationError):
            NewsletterRequest.model_validate(
                {
                    "filters": {},
                    "text": "hi",
                    "use_buttons": "INLINE",
                    "buttons": [{"text": "x", "url": "http://a", "callback_data": "c"}],
                }
            )
        # neither -> invalid
        with self.assertRaises(ValidationError):
            NewsletterRequest.model_validate(
                {
                    "filters": {},
                    "text": "hi",
                    "use_buttons": "INLINE",
                    "buttons": [{"text": "x"}],
                }
            )
        # exactly one -> valid
        ok = NewsletterRequest.model_validate(
            {
                "filters": {},
                "text": "hi",
                "use_buttons": "INLINE",
                "buttons": [{"text": "x", "url": "http://a"}],
            }
        )
        self.assertEqual(ok.use_buttons, "INLINE")

    def test_buttons_require_use_buttons_and_vice_versa(self) -> None:
        with self.assertRaises(ValidationError):
            NewsletterRequest.model_validate(
                {"filters": {}, "text": "hi", "buttons": [{"text": "x"}]}
            )
        with self.assertRaises(ValidationError):
            NewsletterRequest.model_validate(
                {"filters": {}, "text": "hi", "use_buttons": "INLINE"}
            )

    def test_defaults(self) -> None:
        req = NewsletterRequest.model_validate({"text": "hi"})
        self.assertIsNone(req.use_buttons)
        self.assertIsNone(req.buttons)
        self.assertIsNone(req.filters.search)


class BuildPayloadTests(unittest.TestCase):
    def test_payload_shape(self) -> None:
        req = NewsletterRequest.model_validate(
            {
                "filters": {"search": "ru", "field": "language_code"},
                "text": "hello",
                "use_buttons": "INLINE",
                "buttons": [{"text": "Site", "url": "http://a"}],
            }
        )
        payload = build_newsletter_payload(chat_ids=[1, 2, 3], request=req, file_id=42)
        self.assertEqual(payload["chat_ids"], [1, 2, 3])
        self.assertEqual(payload["message"], "hello")
        self.assertEqual(payload["use_buttons"], "INLINE")
        self.assertEqual(payload["buttons"], [{"text": "Site", "url": "http://a"}])
        self.assertEqual(payload["file_id"], 42)

    def test_payload_no_buttons_no_file(self) -> None:
        req = NewsletterRequest.model_validate({"text": "hello"})
        payload = build_newsletter_payload(chat_ids=[1], request=req, file_id=None)
        self.assertIsNone(payload["buttons"])
        self.assertIsNone(payload["file_id"])
        self.assertIsNone(payload["use_buttons"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/backend && uv run python -m unittest tests.test_newsletter_schema -v`
Expected: FAIL — `ImportError: cannot import name 'NewsletterRequest'`.

- [ ] **Step 3: Implement the schemas**

Create `apps/backend/app/modules/telegram_module/schemas/newsletter.py`:

```python
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class NewsletterFilters(BaseModel):
    """Фильтр аудитории — та же семантика, что у GET /telegram/users."""

    search: str | None = None
    field: str | None = None


class NewsletterButton(BaseModel):
    """Кнопка рассылки. url/callback_data — только для INLINE."""

    text: str
    url: str | None = None
    callback_data: str | None = None


class NewsletterRequest(BaseModel):
    filters: NewsletterFilters = Field(default_factory=NewsletterFilters)
    text: str | None = None
    use_buttons: Literal["INLINE", "REPLY"] | None = None
    buttons: list[NewsletterButton] | None = None

    @model_validator(mode="after")
    def _validate_buttons(self) -> "NewsletterRequest":
        # buttons и use_buttons включаются только вместе
        if self.buttons and not self.use_buttons:
            raise ValueError("use_buttons must be set when buttons are provided")
        if self.use_buttons and not self.buttons:
            raise ValueError("buttons must be provided when use_buttons is set")
        # для INLINE у каждой кнопки ровно одно из url / callback_data
        if self.use_buttons == "INLINE" and self.buttons:
            for btn in self.buttons:
                has_url = bool(btn.url)
                has_cb = bool(btn.callback_data)
                if has_url == has_cb:  # оба или ни одного
                    raise ValueError(
                        "each INLINE button needs exactly one of url / callback_data"
                    )
        return self


class NewsletterResult(BaseModel):
    status: str
    recipients: int
```

- [ ] **Step 4: Export the schemas**

In `apps/backend/app/modules/telegram_module/schemas/__init__.py`, add (alongside existing exports):

```python
from .newsletter import (
    NewsletterButton,
    NewsletterFilters,
    NewsletterRequest,
    NewsletterResult,
)
```

If the file defines `__all__`, append `"NewsletterButton"`, `"NewsletterFilters"`, `"NewsletterRequest"`, `"NewsletterResult"` to it.

- [ ] **Step 5: Implement the payload builder**

Create `apps/backend/app/modules/telegram_module/utils/newsletter.py`:

```python
from ..schemas.newsletter import NewsletterRequest


def build_newsletter_payload(
    chat_ids: list, request: NewsletterRequest, file_id: int | None
) -> dict:
    """Собирает payload RMQ-сообщения для бота из запроса рассылки.

    Контракт (см. docs/specs/2026-06-23-newsletter-broadcast-design.md):
    chat_ids — все получатели одним сообщением; use_buttons — единый ключ;
    buttons — плоский список; file_id — id модели File бэкенда (или None).
    """
    return {
        "chat_ids": chat_ids,
        "message": request.text,
        "use_buttons": request.use_buttons,
        "buttons": (
            [btn.model_dump(exclude_none=True) for btn in request.buttons]
            if request.buttons
            else None
        ),
        "file_id": file_id,
    }
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `cd apps/backend && uv run python -m unittest tests.test_newsletter_schema -v`
Expected: PASS (5 tests).

- [ ] **Step 7: Commit**

```bash
git add apps/backend/app/modules/telegram_module/schemas/newsletter.py apps/backend/app/modules/telegram_module/schemas/__init__.py apps/backend/app/modules/telegram_module/utils/newsletter.py apps/backend/tests/test_newsletter_schema.py
git commit -m "feat(backend): newsletter request schemas + RMQ payload builder"
```

---

### Task 3: Newsletter service (count → upload → fetch ids → publish)

**Files:**
- Create: `apps/backend/app/modules/telegram_module/services/newsletter_service.py`
- Modify: `apps/backend/app/modules/telegram_module/services/__init__.py`
- Test: `apps/backend/tests/test_newsletter_service.py` (create)

**Interfaces:**
- Consumes: `CRUD.count`, `CRUD.get_column` (Task 1); `NewsletterRequest`, `build_newsletter_payload` (Task 2); `s3_client.create`/`delete`, `File`, `FileCreate`, `sanitize_filename` (file_module); `rmq_publisher.publish` (rmq_module); `TelegramUser` model.
- Produces: `async send_newsletter(request: NewsletterRequest, file: UploadFile | None, session: AsyncSession) -> dict` returning `{"status": "queued", "recipients": <int>}`.

- [ ] **Step 1: Write the failing test**

Create `apps/backend/tests/test_newsletter_service.py`:

```python
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.modules.system import CRUD
from app.modules.rmq_module import rmq_publisher
from app.modules.telegram_module.schemas import NewsletterRequest
from app.modules.telegram_module.services.newsletter_service import send_newsletter


class SendNewsletterTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_audience_raises_404_and_does_not_publish(self) -> None:
        request = NewsletterRequest.model_validate({"text": "hi"})
        session = MagicMock()
        with patch.object(CRUD, "count", AsyncMock(return_value=0)), patch.object(
            rmq_publisher, "publish", AsyncMock()
        ) as publish:
            with self.assertRaises(HTTPException) as ctx:
                await send_newsletter(request=request, file=None, session=session)
            self.assertEqual(ctx.exception.status_code, 404)
            publish.assert_not_awaited()

    async def test_no_content_raises_400(self) -> None:
        request = NewsletterRequest.model_validate({"text": None})
        session = MagicMock()
        with patch.object(CRUD, "count", AsyncMock(return_value=5)):
            with self.assertRaises(HTTPException) as ctx:
                await send_newsletter(request=request, file=None, session=session)
            self.assertEqual(ctx.exception.status_code, 400)

    async def test_text_only_publishes_one_message(self) -> None:
        request = NewsletterRequest.model_validate({"text": "hello"})
        session = MagicMock()
        with patch.object(CRUD, "count", AsyncMock(return_value=3)), patch.object(
            CRUD, "get_column", AsyncMock(return_value=[10, 20, 30])
        ), patch.object(rmq_publisher, "publish", AsyncMock()) as publish:
            result = await send_newsletter(
                request=request, file=None, session=session
            )

        self.assertEqual(result, {"status": "queued", "recipients": 3})
        publish.assert_awaited_once()
        kwargs = publish.await_args.kwargs
        self.assertEqual(kwargs["event"], "telegram.newsletter")
        self.assertEqual(kwargs["queue_name"], "telegram_notifications")
        self.assertEqual(kwargs["routing_key"], "telegram_notifications")
        self.assertEqual(kwargs["exchange_name"], "app.events")
        self.assertEqual(kwargs["exchange_type"], "direct")
        self.assertEqual(kwargs["payload"]["chat_ids"], [10, 20, 30])
        self.assertEqual(kwargs["payload"]["message"], "hello")
        self.assertIsNone(kwargs["payload"]["file_id"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/backend && uv run python -m unittest tests.test_newsletter_service -v`
Expected: FAIL — `ModuleNotFoundError: ...newsletter_service`.

- [ ] **Step 3: Implement the service**

Create `apps/backend/app/modules/telegram_module/services/newsletter_service.py`:

```python
from fastapi import HTTPException, UploadFile, status

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.system import CRUD
from app.modules.rmq_module import rmq_publisher
from app.modules.file_module.models import File
from app.modules.file_module.schemas import FileCreate
from app.modules.file_module.services import s3_client
from app.modules.file_module.utils import sanitize_filename

from ..models import TelegramUser
from ..schemas import NewsletterRequest
from ..utils.newsletter import build_newsletter_payload

# Контракт очереди бота (см. spec). Должны совпадать с consumer_handler в tg_user_bot.
NEWSLETTER_EVENT = "telegram.newsletter"
NEWSLETTER_QUEUE = "telegram_notifications"
NEWSLETTER_EXCHANGE = "app.events"
NEWSLETTER_EXCHANGE_TYPE = "direct"


async def send_newsletter(
    request: NewsletterRequest,
    file: UploadFile | None,
    session: AsyncSession,
) -> dict:
    """Готовит и публикует рассылку ОДНИМ сообщением со списком chat_ids.

    Шаги: контент-валидация → подсчёт получателей (0 → 404) → загрузка файла →
    выборка telegram_id → публикация в RMQ.
    """
    # 1. Пустую рассылку запрещаем: нужен текст или файл.
    if not (request.text and request.text.strip()) and file is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Newsletter must contain text or a file",
        )

    # 2. Сначала проверяем, что под фильтр есть получатели — иначе не льём файл.
    recipients = await CRUD.count(
        model=TelegramUser,
        session=session,
        search=request.filters.search,
        field=request.filters.field,
    )
    if recipients == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No recipients match the filter",
        )

    # 3. Загружаем файл (если есть) — переиспользуем file_module.
    file_id: int | None = None
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

    # 4. Список chat_ids всех получателей под тем же фильтром.
    chat_ids = await CRUD.get_column(
        model=TelegramUser,
        session=session,
        column=TelegramUser.telegram_id,
        search=request.filters.search,
        field=request.filters.field,
    )

    # 5. Публикуем ОДНО сообщение со списком chat_ids.
    payload = build_newsletter_payload(
        chat_ids=chat_ids, request=request, file_id=file_id
    )
    await rmq_publisher.publish(
        event=NEWSLETTER_EVENT,
        payload=payload,
        queue_name=NEWSLETTER_QUEUE,
        routing_key=NEWSLETTER_QUEUE,
        exchange_name=NEWSLETTER_EXCHANGE,
        exchange_type=NEWSLETTER_EXCHANGE_TYPE,
    )

    return {"status": "queued", "recipients": recipients}
```

- [ ] **Step 4: Export the service**

In `apps/backend/app/modules/telegram_module/services/__init__.py`, add:

```python
from .newsletter_service import send_newsletter
```

If the file defines `__all__`, append `"send_newsletter"`.

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd apps/backend && uv run python -m unittest tests.test_newsletter_service -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Import gate**

Run: `cd apps/backend && uv run python -m compileall app/modules/telegram_module`
Expected: compiles, exit 0.

- [ ] **Step 7: Commit**

```bash
git add apps/backend/app/modules/telegram_module/services/newsletter_service.py apps/backend/app/modules/telegram_module/services/__init__.py apps/backend/tests/test_newsletter_service.py
git commit -m "feat(backend): newsletter service (count, upload, publish single RMQ message)"
```

---

### Task 4: `POST /telegram/newsletter` endpoint

**Files:**
- Modify: `apps/backend/app/modules/telegram_module/handlers.py`
- Test: `apps/backend/tests/test_newsletter_endpoint.py` (create)

**Interfaces:**
- Consumes: `send_newsletter` service (Task 3); `NewsletterRequest`, `NewsletterResult` schemas (Task 2).
- Produces: route `POST /telegram/newsletter` accepting `multipart/form-data` (`payload: str` Form + optional `file: UploadFile`), returning `NewsletterResult`.

Note: the `telegram` router is already included in `app/api/router.py`; adding a route to its `handlers.py` needs no router registration change.

- [ ] **Step 1: Write the failing test**

Create `apps/backend/tests/test_newsletter_endpoint.py`:

```python
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.telegram_module import handlers


class NewsletterEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_handler_parses_payload_and_delegates(self) -> None:
        session = MagicMock()
        payload = '{"filters": {}, "text": "hi"}'
        with patch.object(
            handlers,
            "send_newsletter_service",
            AsyncMock(return_value={"status": "queued", "recipients": 7}),
        ) as service:
            result = await handlers.send_newsletter(
                session=session, payload=payload, file=None
            )

        self.assertEqual(result, {"status": "queued", "recipients": 7})
        service.assert_awaited_once()
        # переданный в сервис request распарсен из JSON payload
        call_kwargs = service.await_args.kwargs
        self.assertEqual(call_kwargs["request"].text, "hi")
        self.assertIsNone(call_kwargs["file"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/backend && uv run python -m unittest tests.test_newsletter_endpoint -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'send_newsletter'` (or `send_newsletter_service`).

- [ ] **Step 3: Implement the endpoint**

In `apps/backend/app/modules/telegram_module/handlers.py`:

a) Extend the FastAPI import (line 3) to include `Form` and `UploadFile`:

```python
from fastapi import APIRouter, Depends, Form, Query, Response, UploadFile, status
```

b) Add `NewsletterRequest`, `NewsletterResult` to the `.schemas` import block (lines 10-21).

c) Add `send_newsletter as send_newsletter_service` to the `.services` import block (lines 22-26), so it becomes:

```python
from .services import (
    bulk_create_telegram_users as bulk_create_telegram_users_service,
    create_telegram_user as create_telegram_user_service,
    login_telegram_user as login_telegram_user_service,
    send_newsletter as send_newsletter_service,
)
```

d) Add the endpoint (place it after the `list_telegram_users` endpoint, before the `patch_telegram_user` endpoint at line 97):

```python
@router.post("/newsletter", response_model=NewsletterResult)
async def send_newsletter(
    session: SessionDep,
    payload: Annotated[str, Form()],
    file: UploadFile | None = None,
) -> dict:
    """Запускает рассылку: парсит JSON payload (multipart) и делегирует в сервис.

    payload — JSON тела рассылки (filters/text/use_buttons/buttons);
    file — опциональное вложение (multipart). Логика — в services.
    """
    request = NewsletterRequest.model_validate_json(payload)
    return await send_newsletter_service(request=request, file=file, session=session)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd apps/backend && uv run python -m unittest tests.test_newsletter_endpoint -v`
Expected: PASS (1 test).

- [ ] **Step 5: Full unit suite + import gate**

Run: `cd apps/backend && uv run python -m unittest discover -s tests -v && uv run python -m compileall app`
Expected: all tests PASS; compile exit 0.

- [ ] **Step 6: Commit**

```bash
git add apps/backend/app/modules/telegram_module/handlers.py apps/backend/tests/test_newsletter_endpoint.py
git commit -m "feat(backend): POST /telegram/newsletter endpoint"
```

---

### Task 5: Sync module docs

**Files:**
- Modify: `apps/backend/app/modules/telegram_module/AGENTS.md` (English)
- Modify: `apps/backend/app/modules/telegram_module/README.md` (Russian)

**Interfaces:** docs only.

- [ ] **Step 1: Update `AGENTS.md` (English)**

Append a new section to `apps/backend/app/modules/telegram_module/AGENTS.md`:

```markdown
## Newsletter broadcast

`POST /telegram/newsletter` — `multipart/form-data`: `payload` (JSON string of
`NewsletterRequest`) + optional `file` (UploadFile).

Flow (`services/newsletter_service.py`): validate (text OR file required) →
`CRUD.count(TelegramUser, search, field)` (0 → 404) → upload `file` via `file_module`
(`s3_client` + `File`) capturing `File.id` → `CRUD.get_column(TelegramUser,
TelegramUser.telegram_id, ...)` → publish ONE RMQ message.

Published message (`rmq_publisher.publish`): event `telegram.newsletter`, queue
`telegram_notifications`, routing key `telegram_notifications`, exchange `app.events`
(direct). Payload: `{ chat_ids: list[int], message: str|None, use_buttons:
"INLINE"|"REPLY"|null, buttons: [{text,url?,callback_data?}]|null, file_id: int|null }`.
`file_id` is the backend `File.id`; the bot resolves it via `GET /api/files/{id}`.

Recipient filtering reuses `CRUD` (`count` / `get_column` with the same `search`/`field`
semantics as `GET /telegram/users`). No new DB model/migration.
```

- [ ] **Step 2: Update `README.md` (Russian)**

Append to `apps/backend/app/modules/telegram_module/README.md`:

```markdown
## Рассылка (newsletter)

`POST /telegram/newsletter` — `multipart/form-data`: поле `payload` (JSON тела) и
опциональный `file`.

Тело `payload`:
- `filters`: `{ search, field }` — та же фильтрация, что в `GET /telegram/users`.
- `text`: текст рассылки (обязателен, если нет файла).
- `use_buttons`: `null | "INLINE" | "REPLY"`.
- `buttons`: плоский список `{ text, url?, callback_data? }` (url/callback_data — только для INLINE).

Логика: проверяем число получателей под фильтром (если 0 — `404`), грузим файл через
`file_module`, берём `telegram_id` всех получателей и публикуем **одно** сообщение в
RabbitMQ (очередь `telegram_notifications`) со списком `chat_ids`. Сам перебор получателей
делает `tg_user_bot`. Поле `file_id` в сообщении — это `id` модели `File` бэкенда.
```

- [ ] **Step 3: Commit**

```bash
git add apps/backend/app/modules/telegram_module/AGENTS.md apps/backend/app/modules/telegram_module/README.md
git commit -m "docs(backend): document /telegram/newsletter"
```

---

## Self-Review

**Spec coverage:**
- `POST /telegram/newsletter` multipart (payload JSON + file) → Task 4. ✓
- Validate text-or-file; empty audience → 404 → Task 3. ✓
- Upload file via file_module → `file_id = File.id` → Task 3. ✓
- Reuse CRUD filter logic for count + chat_ids (single source) → Task 1 (`_apply_search`). ✓
- Publish ONE message; exact queue/exchange/routing/event values → Task 3 (constants) + payload builder Task 2. ✓
- RMQ payload shape (`chat_ids`, `message`, `use_buttons`, flat `buttons`, `file_id`) → Task 2. ✓
- No new model/migration; handlers delegate; broker via rmq_publisher; DB via Depends → respected across tasks. ✓
- Docs sync → Task 5. ✓

**Placeholder scan:** No TBD/TODO; every code step has full code. ✓

**Type consistency:** `send_newsletter(request, file, session)` defined in Task 3, imported as `send_newsletter_service` and called with the same kwargs in Task 4. `build_newsletter_payload(chat_ids, request, file_id)` defined Task 2, called Task 3. `CRUD.count`/`CRUD.get_column` defined Task 1, called Task 3. Payload keys identical across Task 2 builder, Task 3 publish, Task 5 docs. ✓
