# Newsletter Broadcast — tg_user_bot Consumer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update `tg_user_bot`'s `notification_module` to consume the new broadcast RMQ message — fan out a single message across all `chat_ids`, support an optional attachment (`file_id` = backend `File.id`, resolved via `GET /api/files/{id}`), and build inline buttons with `url` / `callback_data`.

**Architecture:** The RMQ consumer wiring (`consumer_handler.py`, queue `telegram_notifications`) is unchanged. We change the payload schema (`schemas.py`), add a small backend file resolver (`services/backend_files.py`), and rewrite the sender (`services/sender.py`) to loop over `chat_ids`, resolve+send the attachment once (reusing the returned Telegram file_id), and build keyboards from a flat button list. Keyboard building, photo/document selection, and the broadcast loop are unit-tested with stdlib `unittest` (the framework already used in `apps/tg_user_bot/tests/`).

**Tech Stack:** Python 3.11, aiogram (Bot, Inline/Reply keyboards, BufferedInputFile), Pydantic v2, aiohttp (already a dependency, used by `system/client.py`). Package manager: `uv`.

## Global Constraints

- **RMQ contract (verbatim) — the message this consumer must parse:** `{ "chat_ids": list[int|str], "message": str|None, "use_buttons": "INLINE"|"REPLY"|null, "buttons": list[{text,url?,callback_data?}]|null, "file_id": int|null }`.
- **Do not change the consumer wiring:** queue `telegram_notifications`, exchange `app.events`, routing key `telegram_notifications` (in `consumer_handler.py`) stay as-is.
- **`file_id` is the backend `File.id`** — resolve it via the backend's `GET /api/files/{id}` (streams bytes + `Content-Type`). The bot already has `settings.backend_url` + `settings.backend_api_prefix` (`/api`).
- **Single download, reuse Telegram file_id:** download the file once per broadcast; send to the first recipient with the bytes, then reuse the Telegram `file_id` from the response for the rest.
- **Keep the `requests_contect` typo + its alias** in `TelegramButton` (existing established behavior). New `url` / `callback_data` fields use correct spelling.
- **Code comments in Russian** (module style).
- **No new dependencies.**
- **One button per row** for both INLINE and REPLY keyboards.

### Verification approach (read first)

The bot uses stdlib **`unittest`** (see `apps/tg_user_bot/tests/test_rmq_module.py`: `unittest.IsolatedAsyncioTestCase`). No pytest. All commands run from `apps/tg_user_bot/`:

- **Unit tests:** `uv run python -m unittest tests.<module> -v` (schema parsing, keyboard building, broadcast loop with a fake bot — no network/Telegram).
- **Import/syntax gate:** `uv run python -m compileall app`.
- Tests that import `services/sender.py` construct an aiogram `Bot`, which needs a syntactically valid `TOKEN` in the bot's environment — the same requirement the existing suite already has (run with the project's `.env` present). If `uv` is not wired for this service, fall back to `python -m unittest` with the venv active.
- **End-to-end** (RabbitMQ + backend + bot + a real broadcast) is verified manually on the docker stack after both plans land.

---

### Task 1: Rewrite the notification schema

**Files:**
- Modify: `apps/tg_user_bot/app/modules/notification_module/schemas.py`
- Test: `apps/tg_user_bot/tests/test_notification_schema.py` (create)

**Interfaces:**
- Produces:
  - `TelegramButton{ text: str, url: str|None, callback_data: str|None, requests_contect: bool|None, request_location: bool|None, web_app: str|None }` (keeps `request_contact`→`requests_contect` alias).
  - `TelegramNotification{ chat_ids: list[int|str], message: str|None, use_buttons: Literal["INLINE","REPLY"]|None, buttons: list[TelegramButton]|None, file_id: int|None }`.

- [ ] **Step 1: Write the failing test**

Create `apps/tg_user_bot/tests/test_notification_schema.py`:

```python
import unittest

from app.modules.notification_module.schemas import (
    TelegramButton,
    TelegramNotification,
)


class TelegramNotificationSchemaTests(unittest.TestCase):
    def test_parses_new_contract(self) -> None:
        n = TelegramNotification.model_validate(
            {
                "chat_ids": [1, 2, "3"],
                "message": "hi",
                "use_buttons": "INLINE",
                "buttons": [
                    {"text": "Site", "url": "http://a"},
                    {"text": "Cb", "callback_data": "x"},
                ],
                "file_id": 42,
            }
        )
        self.assertEqual(n.chat_ids, [1, 2, "3"])
        self.assertEqual(n.use_buttons, "INLINE")
        self.assertEqual(n.buttons[0].url, "http://a")
        self.assertEqual(n.buttons[1].callback_data, "x")
        self.assertEqual(n.file_id, 42)

    def test_optional_message_use_buttons_and_file(self) -> None:
        n = TelegramNotification.model_validate({"chat_ids": [1]})
        self.assertIsNone(n.message)
        self.assertIsNone(n.use_buttons)
        self.assertIsNone(n.buttons)
        self.assertIsNone(n.file_id)

    def test_request_contact_alias_preserved(self) -> None:
        btn = TelegramButton.model_validate({"text": "c", "request_contact": True})
        self.assertTrue(btn.requests_contect)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/tg_user_bot && uv run python -m unittest tests.test_notification_schema -v`
Expected: FAIL — the current schema has no `chat_ids` (it has `chat_id`), so `model_validate({"chat_ids": ...})` raises a missing-`chat_id` `ValidationError`.

- [ ] **Step 3: Implement the schema**

Replace the entire contents of `apps/tg_user_bot/app/modules/notification_module/schemas.py` with:

```python
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class TelegramButton(BaseModel):
    text: str
    url: str | None = Field(default=None, description="URL for inline button")
    callback_data: str | None = Field(
        default=None, description="Callback data for inline button"
    )
    requests_contect: bool | None = Field(
        default=None, description="Request contact button (user-specified spelling)"
    )
    request_location: bool | None = Field(
        default=None, description="Request location button"
    )
    web_app: str | None = Field(default=None, description="Web App URL")

    @model_validator(mode="before")
    @classmethod
    def handle_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Совместимость: корректное написание request_contact мапим в исторический typo
            if "request_contact" in data and "requests_contect" not in data:
                data["requests_contect"] = data["request_contact"]
        return data


class TelegramNotification(BaseModel):
    # Рассылка приходит ОДНИМ сообщением со списком получателей — бот сам перебирает.
    chat_ids: list[int | str]
    message: str | None = None  # текст или подпись к файлу
    use_buttons: Literal["INLINE", "REPLY"] | None = None
    buttons: list[TelegramButton] | None = None  # плоский список
    file_id: int | None = None  # id модели File бэкенда (не Telegram file_id)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd apps/tg_user_bot && uv run python -m unittest tests.test_notification_schema -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add apps/tg_user_bot/app/modules/notification_module/schemas.py apps/tg_user_bot/tests/test_notification_schema.py
git commit -m "feat(tg_user_bot): notification schema for broadcast (chat_ids, use_buttons, file_id)"
```

---

### Task 2: Backend file resolver

**Files:**
- Create: `apps/tg_user_bot/app/modules/notification_module/services/backend_files.py`
- Test: `apps/tg_user_bot/tests/test_backend_files.py` (create)

**Interfaces:**
- Consumes: `settings.backend_url`, `settings.backend_api_prefix`, `settings.backend_request_timeout` (from `app.core`).
- Produces:
  - `build_file_url(file_id: int) -> str` — `"{backend_url}{backend_api_prefix}/files/{file_id}"`; raises `RuntimeError` if `backend_url` is unset.
  - `async fetch_file(file_id: int) -> tuple[bytes, str]` — downloads the file via `GET /api/files/{id}`, returns `(bytes, content_type)`.

- [ ] **Step 1: Write the failing test**

Create `apps/tg_user_bot/tests/test_backend_files.py`:

```python
import unittest
from unittest.mock import patch

from app.modules.notification_module.services import backend_files


class BuildFileUrlTests(unittest.TestCase):
    def test_builds_url_from_settings(self) -> None:
        with patch.object(backend_files.settings, "backend_url", "http://backend:8000/"), \
             patch.object(backend_files.settings, "backend_api_prefix", "/api"):
            self.assertEqual(
                backend_files.build_file_url(42), "http://backend:8000/api/files/42"
            )

    def test_raises_when_backend_url_missing(self) -> None:
        with patch.object(backend_files.settings, "backend_url", None):
            with self.assertRaises(RuntimeError):
                backend_files.build_file_url(1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/tg_user_bot && uv run python -m unittest tests.test_backend_files -v`
Expected: FAIL — `ModuleNotFoundError: ...backend_files`.

- [ ] **Step 3: Implement the resolver**

Create `apps/tg_user_bot/app/modules/notification_module/services/backend_files.py`:

```python
"""Резолвер вложений рассылки: id модели File бэкенда → байты файла.

Бот не имеет доступа к S3/БД бэкенда, поэтому скачивает файл по HTTP через
существующий backend API (`GET /api/files/{id}`), используя BACKEND_URL.
"""

import logging

import aiohttp

from app.core import settings

logger = logging.getLogger(__name__)


def build_file_url(file_id: int) -> str:
    """Строит URL скачивания файла из бэкенда по id модели File."""
    if not settings.backend_url:
        raise RuntimeError("BACKEND_URL is not configured; cannot resolve file_id")
    base = settings.backend_url.rstrip("/")
    prefix = settings.backend_api_prefix
    return f"{base}{prefix}/files/{file_id}"


async def fetch_file(file_id: int) -> tuple[bytes, str]:
    """Скачивает файл из бэкенда → (байты, content_type)."""
    url = build_file_url(file_id)
    timeout = aiohttp.ClientTimeout(total=settings.backend_request_timeout)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as response:
            response.raise_for_status()
            content_type = response.headers.get(
                "Content-Type", "application/octet-stream"
            )
            data = await response.read()
    logger.info("[notification] fetched file_id=%s (%s, %d bytes)", file_id, content_type, len(data))
    return data, content_type
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd apps/tg_user_bot && uv run python -m unittest tests.test_backend_files -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Import gate**

Run: `cd apps/tg_user_bot && uv run python -m compileall app/modules/notification_module/services/backend_files.py`
Expected: compiles, exit 0.

- [ ] **Step 6: Commit**

```bash
git add apps/tg_user_bot/app/modules/notification_module/services/backend_files.py apps/tg_user_bot/tests/test_backend_files.py
git commit -m "feat(tg_user_bot): backend file resolver (file_id -> bytes via GET /api/files/{id})"
```

---

### Task 3: Rewrite the sender (loop, attachment, keyboards)

**Files:**
- Modify: `apps/tg_user_bot/app/modules/notification_module/services/sender.py`
- Test: `apps/tg_user_bot/tests/test_notification_sender.py` (create)

**Interfaces:**
- Consumes: `TelegramNotification`, `TelegramButton` (Task 1); `fetch_file` (Task 2); aiogram `Bot`, `BufferedInputFile`, keyboard types; `settings`.
- Produces:
  - `build_markup(use_buttons, buttons) -> InlineKeyboardMarkup | ReplyKeyboardMarkup | None` (pure; one button per row).
  - `is_photo(content_type: str) -> bool`.
  - `async send_notification(notification: TelegramNotification) -> None` (loops `chat_ids`; resolves+reuses the attachment; per-recipient failures are caught and logged).

- [ ] **Step 1: Write the failing test**

Create `apps/tg_user_bot/tests/test_notification_sender.py`:

```python
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup

from app.modules.notification_module.schemas import (
    TelegramButton,
    TelegramNotification,
)
from app.modules.notification_module.services import sender


class BuildMarkupTests(unittest.TestCase):
    def test_inline_url_and_callback_one_per_row(self) -> None:
        buttons = [
            TelegramButton(text="A", url="http://a"),
            TelegramButton(text="B", callback_data="cb"),
        ]
        markup = sender.build_markup("INLINE", buttons)
        self.assertIsInstance(markup, InlineKeyboardMarkup)
        self.assertEqual(len(markup.inline_keyboard), 2)
        self.assertEqual(markup.inline_keyboard[0][0].url, "http://a")
        self.assertEqual(markup.inline_keyboard[1][0].callback_data, "cb")

    def test_reply_contact(self) -> None:
        buttons = [TelegramButton(text="c", requests_contect=True)]
        markup = sender.build_markup("REPLY", buttons)
        self.assertIsInstance(markup, ReplyKeyboardMarkup)
        self.assertTrue(markup.keyboard[0][0].request_contact)

    def test_none_without_buttons(self) -> None:
        self.assertIsNone(sender.build_markup(None, None))
        self.assertIsNone(sender.build_markup("INLINE", None))


class IsPhotoTests(unittest.TestCase):
    def test_image_vs_document(self) -> None:
        self.assertTrue(sender.is_photo("image/png"))
        self.assertFalse(sender.is_photo("application/pdf"))


class BroadcastTests(unittest.IsolatedAsyncioTestCase):
    async def test_text_broadcast_reaches_all_and_survives_one_failure(self) -> None:
        n = TelegramNotification.model_validate(
            {"chat_ids": [1, 2, 3], "message": "hi"}
        )
        fake_bot = MagicMock()
        fake_bot.send_message = AsyncMock(side_effect=[None, Exception("boom"), None])
        with patch.object(sender, "bot", fake_bot), patch(
            "asyncio.sleep", AsyncMock()
        ):
            await sender.send_notification(n)
        self.assertEqual(fake_bot.send_message.await_count, 3)

    async def test_file_broadcast_reuses_telegram_file_id(self) -> None:
        n = TelegramNotification.model_validate(
            {"chat_ids": [1, 2], "message": "cap", "file_id": 9}
        )
        first_msg = MagicMock()
        first_msg.photo = [MagicMock(file_id="TG123")]
        fake_bot = MagicMock()
        fake_bot.send_photo = AsyncMock(return_value=first_msg)
        with patch.object(sender, "bot", fake_bot), patch.object(
            sender, "fetch_file", AsyncMock(return_value=(b"x", "image/png"))
        ), patch("asyncio.sleep", AsyncMock()):
            await sender.send_notification(n)
        self.assertEqual(fake_bot.send_photo.await_count, 2)
        # второй вызов переиспользует пойманный Telegram file_id (строку)
        self.assertEqual(
            fake_bot.send_photo.await_args_list[1].kwargs["photo"], "TG123"
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/tg_user_bot && uv run python -m unittest tests.test_notification_sender -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'build_markup'`.

- [ ] **Step 3: Implement the sender**

Replace the entire contents of `apps/tg_user_bot/app/modules/notification_module/services/sender.py` with:

```python
import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    BufferedInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from app.core import settings
from ..schemas import TelegramNotification
from .backend_files import fetch_file

logger = logging.getLogger(__name__)

# Отдельный Bot-инстанс только для фоновых рассылок.
bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=settings.bot_parse_mode),
)

# Лёгкий троттлинг между отправками (Telegram ~30 msg/s на разные чаты).
THROTTLE_SECONDS = 0.05


def build_markup(use_buttons, buttons):
    """Собирает клавиатуру из плоского списка кнопок: каждая кнопка — отдельный ряд."""
    if not use_buttons or not buttons:
        return None

    if use_buttons == "INLINE":
        rows = []
        for btn in buttons:
            kwargs = {"text": btn.text}
            if btn.url:
                kwargs["url"] = btn.url
            elif btn.callback_data:
                kwargs["callback_data"] = btn.callback_data
            elif btn.web_app:
                kwargs["web_app"] = WebAppInfo(url=btn.web_app)
            else:
                # последний фолбэк: inline-кнопке нужен хоть один target
                kwargs["callback_data"] = btn.text
            rows.append([InlineKeyboardButton(**kwargs)])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    if use_buttons == "REPLY":
        rows = []
        for btn in buttons:
            kwargs = {"text": btn.text}
            if btn.requests_contect:
                kwargs["request_contact"] = True
            if btn.request_location:
                kwargs["request_location"] = True
            if btn.web_app:
                kwargs["web_app"] = WebAppInfo(url=btn.web_app)
            rows.append([KeyboardButton(**kwargs)])
        return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

    return None


def is_photo(content_type: str) -> bool:
    """Картинки шлём через send_photo, остальное — send_document."""
    return content_type.startswith("image/")


async def send_notification(notification: TelegramNotification) -> None:
    """Рассылает одно уведомление по всему списку chat_ids.

    Если есть file_id — файл скачивается из бэкенда один раз; первому получателю
    шлём байтами, дальше переиспользуем Telegram file_id из ответа.
    """
    reply_markup = build_markup(notification.use_buttons, notification.buttons)

    if notification.file_id is not None:
        await _broadcast_file(notification, reply_markup)
    else:
        await _broadcast_text(notification, reply_markup)


async def _broadcast_text(notification: TelegramNotification, reply_markup) -> None:
    for chat_id in notification.chat_ids:
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=notification.message or "",
                reply_markup=reply_markup,
            )
        except Exception:
            logger.exception(
                "[notification] send_message failed for chat_id=%s", chat_id
            )
        await asyncio.sleep(THROTTLE_SECONDS)


async def _broadcast_file(notification: TelegramNotification, reply_markup) -> None:
    data, content_type = await fetch_file(notification.file_id)
    photo = is_photo(content_type)
    tg_file_id: str | None = None  # пойманный Telegram file_id для переиспользования

    for chat_id in notification.chat_ids:
        # первый раз — байты; дальше — уже загруженный Telegram file_id
        media = tg_file_id or BufferedInputFile(
            data, filename=f"file_{notification.file_id}"
        )
        try:
            if photo:
                message = await bot.send_photo(
                    chat_id=chat_id,
                    photo=media,
                    caption=notification.message,
                    reply_markup=reply_markup,
                )
                if tg_file_id is None and message.photo:
                    tg_file_id = message.photo[-1].file_id
            else:
                message = await bot.send_document(
                    chat_id=chat_id,
                    document=media,
                    caption=notification.message,
                    reply_markup=reply_markup,
                )
                if tg_file_id is None and message.document:
                    tg_file_id = message.document.file_id
        except Exception:
            logger.exception(
                "[notification] send file failed for chat_id=%s", chat_id
            )
        await asyncio.sleep(THROTTLE_SECONDS)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd apps/tg_user_bot && uv run python -m unittest tests.test_notification_sender -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Import gate + full notification suite**

Run: `cd apps/tg_user_bot && uv run python -m compileall app && uv run python -m unittest tests.test_notification_schema tests.test_backend_files tests.test_notification_sender -v`
Expected: compile exit 0; all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/tg_user_bot/app/modules/notification_module/services/sender.py apps/tg_user_bot/tests/test_notification_sender.py
git commit -m "feat(tg_user_bot): broadcast sender (chat_ids loop, attachment, url/callback buttons)"
```

---

### Task 4: Sync notification module docs

**Files:**
- Modify: `apps/tg_user_bot/app/modules/notification_module/README.md` (Russian)
- Modify: `apps/tg_user_bot/app/modules/notification_module/AGENTS.md` (English)

**Interfaces:** docs only.

- [ ] **Step 1: Update `README.md` (Russian)**

In `apps/tg_user_bot/app/modules/notification_module/README.md`, replace the "Входящие сообщения из RMQ..." structure block (the one describing `chat_id`, `inline_buttons`, `reply_buttons`, 2D `buttons`) with the new contract:

```markdown
Входящие сообщения из RMQ должны соответствовать следующей структуре:

- `chat_ids` (list[int | str]): список получателей — бот сам рассылает по всем.
- `message` (str | None): текст сообщения или подпись к файлу.
- `use_buttons` (None | "INLINE" | "REPLY"): тип клавиатуры.
- `buttons` (list[dict] | None): плоский список кнопок (каждая — отдельный ряд):
  - `text` (str): текст кнопки.
  - `url` (str | None): ссылка (для INLINE).
  - `callback_data` (str | None): callback (для INLINE).
  - `requests_contect` / `request_location` / `web_app`: для REPLY-кнопок.
- `file_id` (int | None): id модели `File` бэкенда. Бот скачивает файл по
  `GET /api/files/{id}`, отправляет первому получателю и переиспользует Telegram
  file_id для остальных. Картинка (`image/*`) уходит как фото, остальное — документом.
```

- [ ] **Step 2: Update `AGENTS.md` (English)**

In `apps/tg_user_bot/app/modules/notification_module/AGENTS.md`, update the incoming-message description to the new contract (replace any `chat_id` / `inline_buttons` / `reply_buttons` / 2D `buttons` description):

```markdown
## Incoming RMQ message (broadcast)

`TelegramNotification` payload:
- `chat_ids: list[int|str]` — the consumer loops and sends to each (single message per broadcast, not per recipient).
- `message: str|None` — text, or caption when a file is attached.
- `use_buttons: "INLINE"|"REPLY"|None` — single key (replaces the old `inline_buttons`/`reply_buttons` flags).
- `buttons: list[TelegramButton]|None` — FLAT list (one button per row). INLINE buttons use `url`/`callback_data`; REPLY buttons use `requests_contect`/`request_location`/`web_app`.
- `file_id: int|None` — backend `File.id`. Resolved via `GET /api/files/{id}` (download bytes once, reuse the returned Telegram file_id; `image/*` → `send_photo`, else `send_document`).

Sender: `services/sender.py` (`build_markup`, `is_photo`, `send_notification`). File resolver: `services/backend_files.py`. Consumer wiring (`consumer_handler.py`, queue `telegram_notifications`) is unchanged.
```

- [ ] **Step 3: Commit**

```bash
git add apps/tg_user_bot/app/modules/notification_module/README.md apps/tg_user_bot/app/modules/notification_module/AGENTS.md
git commit -m "docs(tg_user_bot): document broadcast notification contract"
```

---

## Self-Review

**Spec coverage:**
- `chat_id`→`chat_ids`, two flags→`use_buttons`, 2D→flat `buttons`, `+file_id`, `+url`/`callback_data` → Task 1 (schema) + Task 3 (sender). ✓
- Fan-out in the bot (loop `chat_ids`, per-recipient try/except) → Task 3. ✓
- `file_id` resolved via `GET /api/files/{id}`; download once, reuse Telegram file_id; photo/document by `Content-Type` → Task 2 + Task 3. ✓
- Inline buttons with `url`/`callback_data` (drop hardcoded `callback_data=text` to a last-resort fallback) → Task 3 `build_markup`. ✓
- Keep `requests_contect` typo + alias → Task 1. ✓
- Consumer wiring unchanged → no task touches `consumer_handler.py`. ✓
- Docs sync → Task 4. ✓

**Placeholder scan:** No TBD/TODO; every code step has full code. ✓

**Type consistency:** `TelegramNotification.chat_ids`/`use_buttons`/`file_id` defined Task 1, consumed by `build_markup`/`send_notification` in Task 3. `fetch_file(file_id) -> (bytes, str)` defined Task 2, called in Task 3 `_broadcast_file`. `build_markup(use_buttons, buttons)` and `is_photo(content_type)` defined and tested in Task 3. Payload keys match the backend producer plan and the spec contract. ✓
