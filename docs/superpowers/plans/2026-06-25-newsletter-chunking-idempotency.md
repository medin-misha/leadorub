# Newsletter Chunking + Redis Idempotency — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Устранить дубль всей рассылки при срабатывании RabbitMQ `consumer_timeout`: бэкенд дробит аудиторию на чанки и публикует по одному RMQ-сообщению на чанк; бот обрабатывает и акает каждый чанк отдельно, а каждого получателя дедуплицирует через Redis (`SET NX`), чтобы редоставка чанка не порождала повторные отправки.

**Architecture:**
- **Producer (backend, `telegram_module`)** генерирует один `broadcast_id` на рассылку, режет `chat_ids` на чанки по `newsletter_chunk_size` (default 500) и публикует N сообщений (тот же payload, короче `chat_ids`, + `broadcast_id`/`chunk_index`/`chunk_total`).
- **Consumer (bot, `notification_module`)** обрабатывает каждый чанк как сейчас (per-recipient try/except), но перед отправкой каждому получателю делает `claim` в Redis: `SET newsletter:{broadcast_id}:{chat_id} 1 NX EX <ttl>`. `True` → шлём, `False` → пропускаем (уже слали). Маркер не удаляется — живёт по TTL.
- **Degrade:** если `broadcast_id` отсутствует (старое сообщение в очереди во время деплоя) ИЛИ Redis недоступен — `claim` всегда возвращает `True` (шлём без дедупа, логируем warning). Доставка приоритетнее дедупа.
- Ack по-прежнему происходит после обработки сообщения, но теперь сообщение = один чанк (≤500 получателей, ~25–50 c), что с огромным запасом укладывается в `consumer_timeout` (30 мин).

**Tech Stack:** Python 3.11, FastAPI, aio-pika (через `rmq_publisher`/`register_consumer`), aiogram, `redis` (redis.asyncio), Pydantic v2, pytest, uv.

## Global Constraints

Эти правила действуют для ВСЕХ задач ниже:

- **RMQ-контракт (единый источник истины).** Очередь/топология не меняются: queue `telegram_notifications`, exchange `app.events` (`direct`), routing key `telegram_notifications`. Payload расширяется тремя полями:
  ```json
  {
    "chat_ids": [111, 222],
    "message": "…",
    "use_buttons": "INLINE",
    "buttons": [ … ],
    "file_id": 42,
    "broadcast_id": "0f3a…-uuid4",   // НОВОЕ: общий для всех чанков одной рассылки
    "chunk_index": 0,                  // НОВОЕ: номер чанка (для логов)
    "chunk_total": 60                  // НОВОЕ: всего чанков (для логов)
  }
  ```
  `broadcast_id` — единственное поле, нужное для дедупа. `chunk_index`/`chunk_total` — только диагностика. Все три на стороне бота **опциональны** (`… | None = None`): отсутствие `broadcast_id` означает «дедуп выключен» (degrade), что даёт обратную совместимость при rolling-деплое.
- **Размер чанка:** default `500`, читается из ENV `newsletter_chunk_size` (backend, `MainSettings`, `ge=1`).
- **TTL маркера идемпотентности:** default `172800` (48 ч), ENV `newsletter_idempotency_ttl_seconds` (bot, `MainSettings`, `ge=1`). TTL должен быть заведомо больше окна редоставки и короче интервала легитимной повторной рассылки тем же людям (та получит новый `broadcast_id`).
- **Ключ Redis:** `newsletter:{broadcast_id}:{chat_id}`. Namespace `newsletter:` отделяет маркеры от ключей taskiq в той же БД.
- **Redis-конфиг бота — зеркало бэкенда.** Те же поля `redis_host`/`redis_port`/`redis_db`/`redis_password` и `@property redis_url`, тот же единый секрет `redis_password` из `infra/.env`. Никакого нового способа конфигурации.
- **Брокер только через `rmq_publisher`** (backend) — не импортировать aio-pika в бизнес-коде. Redis в боте инкапсулирован в `IdempotencyStore` (один класс, одно место импорта `redis`).
- **Стиль проекта:** аннотации типов везде; логирование; комментарии/докстринги на русском (как в окружающем коде); перед коммитом — `ruff format`.
- **Документация:** после изменений синхронизировать `apps/<module>/.claude/CLAUDE.md` (EN) и `README.md` (RU) затронутых модулей (правило проекта).

## File Structure

**Backend (`apps/backend`) — Track A (producer):**
- Modify `app/core/config.py` — добавить `newsletter_chunk_size`.
- Modify `app/modules/telegram_module/utils/newsletter.py` — `build_newsletter_payload` принимает `broadcast_id`/`chunk_index`/`chunk_total`.
- Modify `app/modules/telegram_module/services/newsletter_service.py` — генерация `broadcast_id`, нарезка на чанки, цикл публикаций.
- Modify `app/modules/telegram_module/schemas/newsletter.py` — `NewsletterResult.broadcast_id` (трассировка).
- Modify `.env.example`, `infra/.env.example` — `newsletter_chunk_size`.
- Modify `app/modules/telegram_module/{CLAUDE.md,README.md}` — новый контракт.
- Tests: `tests/test_newsletter_service.py`, `tests/test_newsletter_schema.py`.

**Bot (`apps/tg_user_bot`) — Track B (consumer):**
- Modify `pyproject.toml` — зависимость `redis`.
- Modify `app/core/config.py` — redis-поля + `redis_url` + `newsletter_idempotency_ttl_seconds`.
- Create `app/modules/notification_module/services/idempotency.py` — `IdempotencyStore` + singleton.
- Modify `app/modules/notification_module/services/__init__.py` (если есть реэкспорт) — экспорт `idempotency_store`.
- Modify `app/bot/lifecycle.py` — connect/close стора на startup/shutdown.
- Modify `app/modules/notification_module/schemas.py` — `broadcast_id`/`chunk_index`/`chunk_total`.
- Modify `app/modules/notification_module/services/sender.py` — `claim` в обоих циклах рассылки.
- Modify `infra/.env.example` — `newsletter_idempotency_ttl_seconds` (комментарий, что `redis_password` теперь читает и бот).
- Modify `app/modules/notification_module/{CLAUDE.md|AGENTS.md,README.md}` — новый контракт + идемпотентность.
- Tests: `tests/test_idempotency.py`, `tests/test_notification_schema.py`, `tests/test_notification_sender.py`.

**Параллелизация:** Track A и Track B независимы (разные каталоги/venv, общий интерфейс — RMQ-контракт из Global Constraints). Их можно отдать двум исполнителям параллельно. End-to-end проверка (docker + RabbitMQ + Redis) — один ручной шаг пользователя после обоих треков.

---

## Track A — Backend (producer)

### Task A1: Настройка `newsletter_chunk_size`

**Files:**
- Modify: `apps/backend/app/core/config.py` (блок настроек `MainSettings`)
- Modify: `apps/backend/.env.example`
- Modify: `infra/.env.example`

**Interfaces:**
- Produces: `settings.newsletter_chunk_size: int` (default 500, `ge=1`).

- [ ] **Step 1: Добавить поле в `MainSettings`**

В `apps/backend/app/core/config.py` после блока `# Storage`/`# taskiq` (рядом с другими настройками) добавить:

```python
    # Newsletter
    # Размер чанка рассылки: бэкенд режет аудиторию на пачки по N получателей
    # и публикует одно RMQ-сообщение на пачку (см. план chunking+idempotency).
    newsletter_chunk_size: int = Field(default=500, ge=1)
```

- [ ] **Step 2: Задокументировать ENV**

В `apps/backend/.env.example` и `infra/.env.example` добавить строку (рядом с RabbitMQ-блоком):

```dotenv
# Newsletter — размер чанка рассылки (получателей на одно RMQ-сообщение).
newsletter_chunk_size=500
```

- [ ] **Step 3: Smoke-проверка импорта настроек**

Run: `cd apps/backend && uv run python -c "from app.core.config import settings; print(settings.newsletter_chunk_size)"`
Expected: `500`

- [ ] **Step 4: Commit**

```bash
git add apps/backend/app/core/config.py apps/backend/.env.example infra/.env.example
git commit -m "feat(backend): add configurable newsletter_chunk_size setting"
```

---

### Task A2: `build_newsletter_payload` несёт `broadcast_id`/`chunk_index`/`chunk_total`

**Files:**
- Modify: `apps/backend/app/modules/telegram_module/utils/newsletter.py`
- Test: `apps/backend/tests/test_newsletter_service.py` (новый тест на payload)

**Interfaces:**
- Produces: `build_newsletter_payload(chat_ids, request, file_id, broadcast_id: str, chunk_index: int, chunk_total: int) -> dict` — словарь с ключами `chat_ids, message, use_buttons, buttons, file_id, broadcast_id, chunk_index, chunk_total`.

- [ ] **Step 1: Написать падающий тест**

Добавить в `apps/backend/tests/test_newsletter_service.py`:

```python
from app.modules.telegram_module.utils.newsletter import build_newsletter_payload
from app.modules.telegram_module.schemas import NewsletterRequest


def test_build_payload_carries_broadcast_meta():
    request = NewsletterRequest(text="hi")
    payload = build_newsletter_payload(
        chat_ids=[1, 2],
        request=request,
        file_id=None,
        broadcast_id="bcast-1",
        chunk_index=3,
        chunk_total=10,
    )
    assert payload["chat_ids"] == [1, 2]
    assert payload["broadcast_id"] == "bcast-1"
    assert payload["chunk_index"] == 3
    assert payload["chunk_total"] == 10
```

- [ ] **Step 2: Запустить тест — убедиться, что падает**

Run: `cd apps/backend && uv run pytest tests/test_newsletter_service.py::test_build_payload_carries_broadcast_meta -v`
Expected: FAIL — `build_newsletter_payload() got unexpected keyword argument 'broadcast_id'`.

- [ ] **Step 3: Расширить функцию**

В `apps/backend/app/modules/telegram_module/utils/newsletter.py`:

```python
from ..schemas.newsletter import NewsletterRequest


def build_newsletter_payload(
    chat_ids: list,
    request: NewsletterRequest,
    file_id: int | None,
    broadcast_id: str,
    chunk_index: int,
    chunk_total: int,
) -> dict:
    """Собирает payload RMQ-сообщения для бота из запроса рассылки.

    chat_ids — получатели ОДНОГО чанка (не вся аудитория); broadcast_id — общий
    id всех чанков рассылки (для идемпотентности на стороне бота); chunk_index/
    chunk_total — диагностика для логов. use_buttons — единый ключ; buttons —
    плоский список; file_id — id модели File бэкенда (или None).
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
        "broadcast_id": broadcast_id,
        "chunk_index": chunk_index,
        "chunk_total": chunk_total,
    }
```

- [ ] **Step 4: Запустить тест — убедиться, что проходит**

Run: `cd apps/backend && uv run pytest tests/test_newsletter_service.py::test_build_payload_carries_broadcast_meta -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/backend/app/modules/telegram_module/utils/newsletter.py apps/backend/tests/test_newsletter_service.py
git commit -m "feat(backend): add broadcast_id/chunk meta to newsletter payload"
```

---

### Task A3: Чанкованная публикация в `send_newsletter`

**Files:**
- Modify: `apps/backend/app/modules/telegram_module/services/newsletter_service.py` (строки ~91-104: единственный publish → цикл)
- Modify: `apps/backend/app/modules/telegram_module/schemas/newsletter.py` (`NewsletterResult.broadcast_id`)
- Test: `apps/backend/tests/test_newsletter_service.py`

**Interfaces:**
- Consumes: `settings.newsletter_chunk_size` (A1), `build_newsletter_payload(... broadcast_id, chunk_index, chunk_total)` (A2).
- Produces: `send_newsletter(...) -> dict` теперь возвращает `{"status": "queued", "recipients": N, "broadcast_id": <uuid>}` и делает `ceil(N / chunk_size)` вызовов `rmq_publisher.publish` с общим `broadcast_id`.

- [ ] **Step 1: Написать падающий тест на нарезку (мок publisher)**

Изучить, как существующие тесты в `tests/test_newsletter_service.py` мокают `rmq_publisher` и CRUD (повторить их паттерн фикстур — не выдумывать новый). Добавить тест в том же стиле:

```python
import math
from unittest.mock import AsyncMock

import pytest

from app.modules.telegram_module.services import newsletter_service


@pytest.mark.asyncio
async def test_send_newsletter_splits_into_chunks(monkeypatch):
    # 1200 получателей при chunk_size=500 → 3 чанка (500,500,200)
    chat_ids = list(range(1, 1201))
    monkeypatch.setattr(newsletter_service.settings, "newsletter_chunk_size", 500)
    monkeypatch.setattr(newsletter_service.CRUD, "count", AsyncMock(return_value=len(chat_ids)))
    monkeypatch.setattr(newsletter_service.CRUD, "get_column", AsyncMock(return_value=chat_ids))
    publish_mock = AsyncMock()
    monkeypatch.setattr(newsletter_service.rmq_publisher, "publish", publish_mock)

    from app.modules.telegram_module.schemas import NewsletterRequest
    request = NewsletterRequest(text="hello")
    result = await newsletter_service.send_newsletter(request=request, file=None, session=AsyncMock())

    assert result["recipients"] == 1200
    assert publish_mock.await_count == math.ceil(1200 / 500) == 3
    # broadcast_id одинаков во всех чанках
    broadcast_ids = {call.kwargs["payload"]["broadcast_id"] for call in publish_mock.await_args_list}
    assert broadcast_ids == {result["broadcast_id"]}
    # размеры чанков и сумма получателей
    sizes = [len(call.kwargs["payload"]["chat_ids"]) for call in publish_mock.await_args_list]
    assert sizes == [500, 500, 200]
    # chunk_index/chunk_total корректны
    totals = {call.kwargs["payload"]["chunk_total"] for call in publish_mock.await_args_list}
    assert totals == {3}
    indices = sorted(call.kwargs["payload"]["chunk_index"] for call in publish_mock.await_args_list)
    assert indices == [0, 1, 2]
```

> Если существующие тесты используют не `monkeypatch`, а свои фикстуры/`respx`/`dependency_overrides` — адаптируй тест под их стиль, сохранив проверяемые инварианты (число публикаций, единый broadcast_id, размеры чанков).

- [ ] **Step 2: Запустить — убедиться, что падает**

Run: `cd apps/backend && uv run pytest tests/test_newsletter_service.py::test_send_newsletter_splits_into_chunks -v`
Expected: FAIL — сейчас `publish` вызывается один раз, и в payload нет `broadcast_id`.

- [ ] **Step 3: Переписать публикацию на цикл по чанкам**

В `apps/backend/app/modules/telegram_module/services/newsletter_service.py`:

Добавить импорты вверху файла:
```python
from uuid import uuid4

from app.core.config import settings
```

Заменить блок «5. Публикуем ОДНО сообщение …» (строки ~91-104) на:

```python
    # 5. Один broadcast_id на всю рассылку — общий ключ дедупа для всех чанков.
    broadcast_id = str(uuid4())

    # Режем аудиторию на чанки: одно RMQ-сообщение = один чанк. Это ограничивает
    # окно неакнутого сообщения (иначе длинная рассылка > consumer_timeout RMQ
    # → редоставка → дубль всей аудитории) и радиус повторных отправок при краше.
    chunk_size = settings.newsletter_chunk_size
    chunks = [chat_ids[i : i + chunk_size] for i in range(0, len(chat_ids), chunk_size)]
    chunk_total = len(chunks)

    for chunk_index, chunk in enumerate(chunks):
        payload = build_newsletter_payload(
            chat_ids=chunk,
            request=request,
            file_id=file_id,
            broadcast_id=broadcast_id,
            chunk_index=chunk_index,
            chunk_total=chunk_total,
        )
        await rmq_publisher.publish(
            event=NEWSLETTER_EVENT,
            payload=payload,
            queue_name=NEWSLETTER_QUEUE,
            routing_key=NEWSLETTER_QUEUE,
            exchange_name=NEWSLETTER_EXCHANGE,
            exchange_type=NEWSLETTER_EXCHANGE_TYPE,
        )

    return {"status": "queued", "recipients": recipients, "broadcast_id": broadcast_id}
```

- [ ] **Step 4: Расширить `NewsletterResult`**

В `apps/backend/app/modules/telegram_module/schemas/newsletter.py`:

```python
class NewsletterResult(BaseModel):
    status: str
    recipients: int
    broadcast_id: str | None = None
```

- [ ] **Step 5: Запустить тесты ньюслеттера целиком**

Run: `cd apps/backend && uv run pytest tests/test_newsletter_service.py tests/test_newsletter_schema.py tests/test_newsletter_endpoint.py -v`
Expected: PASS (новый тест + старые не сломаны). Если старый тест ожидал ровно один `publish` — обновить его на «≥1 publish с broadcast_id», т.к. контракт сознательно изменён.

- [ ] **Step 6: Обновить документацию модуля**

В `apps/backend/app/modules/telegram_module/CLAUDE.md` и `README.md`: описать, что `send_newsletter` теперь публикует N сообщений (по `newsletter_chunk_size`), payload несёт `broadcast_id`/`chunk_index`/`chunk_total`, ответ содержит `broadcast_id`. Если существует локальный design-doc контракта — добавить пометку, что чанкование больше не «out of scope».

- [ ] **Step 7: Commit**

```bash
git add apps/backend/app/modules/telegram_module/ apps/backend/tests/test_newsletter_service.py
git commit -m "feat(backend): publish newsletter in chunks with shared broadcast_id"
```

---

## Track B — Bot (consumer)

### Task B1: Redis-конфиг бота + зависимость `redis`

**Files:**
- Modify: `apps/tg_user_bot/pyproject.toml` (через `uv add`)
- Modify: `apps/tg_user_bot/app/core/config.py`
- Modify: `infra/.env.example`

**Interfaces:**
- Produces: `settings.redis_url: str | None` (None если нет `redis_password`); `settings.newsletter_idempotency_ttl_seconds: int`.

- [ ] **Step 1: Добавить зависимость**

Run: `cd apps/tg_user_bot && uv add redis`
Expected: `redis` (>=5) появляется в `pyproject.toml`/`uv.lock`. (Нужен `redis.asyncio`, входит в пакет `redis`.)

- [ ] **Step 2: Добавить настройки в `MainSettings`**

В `apps/tg_user_bot/app/core/config.py` добавить поля (зеркало бэкенда; имена в нижнем регистре совпадают с `infra/.env`, поэтому без AliasChoices, как в backend):

```python
    # Redis — идемпотентность рассылки. Единый секрет redis_password из infra/.env
    # (тот же, что использует taskiq на бэкенде). redis_url собирается ниже.
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None
    # TTL маркера «кому уже отправили» (сек). 48ч: заведомо больше окна редоставки.
    newsletter_idempotency_ttl_seconds: int = Field(
        default=172800,
        ge=1,
        validation_alias=AliasChoices(
            "NEWSLETTER_IDEMPOTENCY_TTL_SECONDS",
            "newsletter_idempotency_ttl_seconds",
        ),
    )
```

И добавить `@property` рядом с `bot_token`:

```python
    @property
    def redis_url(self) -> str | None:
        """Строка подключения к Redis из единого redis_password.

        None, если пароль не задан, — IdempotencyStore трактует это как
        «дедуп выключен» (degrade, шлём без дедупа)."""
        if not self.redis_password:
            return None
        return (
            f"redis://:{self.redis_password}@"
            f"{self.redis_host}:{self.redis_port}/{self.redis_db}"
        )
```

- [ ] **Step 3: Задокументировать ENV**

В `infra/.env.example` рядом с redis-блоком добавить:

```dotenv
# Newsletter idempotency (tg_user_bot) — TTL маркера «кому уже отправили» (сек, 48ч).
# Бот переиспользует redis_password (см. выше) для дедупа рассылки.
newsletter_idempotency_ttl_seconds=172800
```

- [ ] **Step 4: Smoke-проверка**

Run: `cd apps/tg_user_bot && uv run python -c "from app.core import settings; print(settings.redis_url, settings.newsletter_idempotency_ttl_seconds)"`
Expected: печатает `None 172800` (если `redis_password` не задан локально) или собранный URL.

- [ ] **Step 5: Commit**

```bash
git add apps/tg_user_bot/pyproject.toml apps/tg_user_bot/uv.lock apps/tg_user_bot/app/core/config.py infra/.env.example
git commit -m "feat(tg_user_bot): add redis config for newsletter idempotency"
```

---

### Task B2: `IdempotencyStore` (claim-before-send + degrade)

**Files:**
- Create: `apps/tg_user_bot/app/modules/notification_module/services/idempotency.py`
- Test: `apps/tg_user_bot/tests/test_idempotency.py`

**Interfaces:**
- Consumes: `settings.redis_url`, `settings.newsletter_idempotency_ttl_seconds` (B1).
- Produces:
  - `class IdempotencyStore` с `async connect(settings) -> None`, `async close() -> None`, `async claim(broadcast_id: str | None, chat_id: int | str) -> bool`.
  - `idempotency_store: IdempotencyStore` — модульный синглтон.
  - Семантика `claim`: `True` = «нужно слать» (мы первые, ИЛИ дедуп выключен/Redis недоступен → degrade); `False` = «пропустить, уже слали».

- [ ] **Step 1: Написать падающие тесты**

Создать `apps/tg_user_bot/tests/test_idempotency.py`:

```python
import pytest

from app.modules.notification_module.services.idempotency import IdempotencyStore


class _FakeRedis:
    """Мини-фейк Redis: SET NX EX через локальный dict."""

    def __init__(self):
        self.store = {}

    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.store:
            return None  # NX: ключ уже есть → не поставили
        self.store[key] = value
        return True

    async def ping(self):
        return True

    async def aclose(self):
        pass


@pytest.mark.asyncio
async def test_claim_first_true_second_false():
    store = IdempotencyStore()
    store._redis = _FakeRedis()  # обходим connect: подставляем фейк
    store._ttl = 100
    assert await store.claim("bcast-1", 111) is True   # первый — шлём
    assert await store.claim("bcast-1", 111) is False  # повтор — пропускаем
    assert await store.claim("bcast-1", 222) is True   # другой chat_id — шлём


@pytest.mark.asyncio
async def test_claim_degrades_without_broadcast_id():
    store = IdempotencyStore()
    store._redis = _FakeRedis()
    store._ttl = 100
    # Нет broadcast_id (старое сообщение) → дедуп выключен, всегда True.
    assert await store.claim(None, 111) is True
    assert await store.claim(None, 111) is True


@pytest.mark.asyncio
async def test_claim_degrades_when_redis_unavailable():
    store = IdempotencyStore()
    store._redis = None  # Redis не подключён
    store._ttl = 100
    assert await store.claim("bcast-1", 111) is True


@pytest.mark.asyncio
async def test_claim_degrades_on_redis_error():
    class _BoomRedis(_FakeRedis):
        async def set(self, *a, **k):
            raise RuntimeError("redis down")

    store = IdempotencyStore()
    store._redis = _BoomRedis()
    store._ttl = 100
    # Ошибка Redis в рантайме → degrade, шлём (True), не роняем рассылку.
    assert await store.claim("bcast-1", 111) is True
```

- [ ] **Step 2: Запустить — убедиться, что падает**

Run: `cd apps/tg_user_bot && uv run pytest tests/test_idempotency.py -v`
Expected: FAIL — модуль `idempotency` ещё не создан.

- [ ] **Step 3: Реализовать `IdempotencyStore`**

Создать `apps/tg_user_bot/app/modules/notification_module/services/idempotency.py`:

```python
"""Идемпотентность рассылки через Redis.

Стратегия claim-before-send: перед отправкой каждому получателю ставим маркер
`SET newsletter:{broadcast_id}:{chat_id} 1 NX EX <ttl>`. Если поставили (ключа
не было) — мы первые, шлём. Если ключ уже есть — уже слали, пропускаем. Маркер
НЕ удаляется: он переживает рассылку и при редоставке чанка не даёт отправить
повторно. Чистит его TTL.

Degrade: если broadcast_id нет (старое сообщение) или Redis недоступен/упал —
claim возвращает True (шлём без дедупа). Доставка приоритетнее дедупа.
"""

import logging

from redis.asyncio import Redis, from_url

logger = logging.getLogger(__name__)

# Префикс отделяет маркеры рассылки от прочих ключей в той же БД Redis.
KEY_PREFIX = "newsletter"


class IdempotencyStore:
    """Redis-хранилище маркеров «кому уже отправили» в рамках одной рассылки."""

    def __init__(self) -> None:
        self._redis: Redis | None = None
        self._ttl: int = 172800

    async def connect(self, settings) -> None:
        """Подключается к Redis на старте бота. Best-effort: при ошибке/отсутствии
        конфига остаёмся в degrade (claim всегда True)."""
        self._ttl = settings.newsletter_idempotency_ttl_seconds
        if not settings.redis_url:
            logger.warning(
                "[idempotency] redis_url не задан — рассылка пойдёт без дедупа"
            )
            return
        try:
            self._redis = from_url(settings.redis_url, decode_responses=True)
            await self._redis.ping()
            logger.info("[idempotency] Redis подключён, дедуп рассылки активен")
        except Exception:
            logger.warning(
                "[idempotency] Redis недоступен на старте — degrade (без дедупа)",
                exc_info=True,
            )
            self._redis = None

    async def close(self) -> None:
        """Закрывает соединение с Redis при остановке бота."""
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def claim(self, broadcast_id: str | None, chat_id: int | str) -> bool:
        """Пытается застолбить отправку. True = слать, False = пропустить (уже слали).

        degrade → True: нет broadcast_id (старое сообщение) или Redis недоступен.
        """
        if broadcast_id is None or self._redis is None:
            return True
        key = f"{KEY_PREFIX}:{broadcast_id}:{chat_id}"
        try:
            # SET ... NX EX: вернёт True если поставили, None если ключ уже был.
            was_set = await self._redis.set(key, 1, nx=True, ex=self._ttl)
            return bool(was_set)
        except Exception:
            logger.warning(
                "[idempotency] ошибка Redis при claim chat_id=%s — degrade",
                chat_id,
                exc_info=True,
            )
            return True


# Модульный синглтон: создаётся при импорте, подключается в lifecycle.
idempotency_store = IdempotencyStore()
```

- [ ] **Step 4: Запустить — убедиться, что проходит**

Run: `cd apps/tg_user_bot && uv run pytest tests/test_idempotency.py -v`
Expected: PASS (все 4 теста).

- [ ] **Step 5: Commit**

```bash
git add apps/tg_user_bot/app/modules/notification_module/services/idempotency.py apps/tg_user_bot/tests/test_idempotency.py
git commit -m "feat(tg_user_bot): add Redis IdempotencyStore for newsletter dedup"
```

---

### Task B3: Подключить стор в lifecycle бота

**Files:**
- Modify: `apps/tg_user_bot/app/bot/lifecycle.py`

**Interfaces:**
- Consumes: `idempotency_store` (B2), `settings` (closure в `register_lifecycle`).

- [ ] **Step 1: Добавить connect/close в хуки**

В `apps/tg_user_bot/app/bot/lifecycle.py`:

Импорт вверху:
```python
from app.modules.notification_module.services.idempotency import idempotency_store
```

В `on_startup` (после `startup_rmq_runtime`):
```python
        await idempotency_store.connect(settings)
```

В `on_shutdown` (рядом с прочими close, например после `shutdown_rmq_runtime`):
```python
        await idempotency_store.close()
```

- [ ] **Step 2: Smoke-проверка импорта**

Run: `cd apps/tg_user_bot && uv run python -c "import app.bot.lifecycle"`
Expected: без ошибок импорта.

- [ ] **Step 3: Commit**

```bash
git add apps/tg_user_bot/app/bot/lifecycle.py
git commit -m "feat(tg_user_bot): wire IdempotencyStore into bot lifecycle"
```

---

### Task B4: Расширить схему `TelegramNotification`

**Files:**
- Modify: `apps/tg_user_bot/app/modules/notification_module/schemas.py`
- Test: `apps/tg_user_bot/tests/test_notification_schema.py`

**Interfaces:**
- Produces: `TelegramNotification.broadcast_id: str | None`, `.chunk_index: int | None`, `.chunk_total: int | None` (все default `None`).

- [ ] **Step 1: Написать падающий тест**

Добавить в `apps/tg_user_bot/tests/test_notification_schema.py`:

```python
from app.modules.notification_module.schemas import TelegramNotification


def test_notification_parses_broadcast_meta():
    n = TelegramNotification.model_validate(
        {
            "chat_ids": [1, 2],
            "message": "hi",
            "broadcast_id": "bcast-1",
            "chunk_index": 0,
            "chunk_total": 5,
        }
    )
    assert n.broadcast_id == "bcast-1"
    assert n.chunk_index == 0
    assert n.chunk_total == 5


def test_notification_broadcast_meta_optional():
    # Обратная совместимость: сообщение без новых полей валидно, broadcast_id=None.
    n = TelegramNotification.model_validate({"chat_ids": [1], "message": "hi"})
    assert n.broadcast_id is None
    assert n.chunk_index is None
    assert n.chunk_total is None
```

- [ ] **Step 2: Запустить — убедиться, что падает**

Run: `cd apps/tg_user_bot && uv run pytest tests/test_notification_schema.py::test_notification_parses_broadcast_meta -v`
Expected: FAIL — `broadcast_id` неизвестное поле (или `AttributeError`).

- [ ] **Step 3: Добавить поля**

В `apps/tg_user_bot/app/modules/notification_module/schemas.py`, в класс `TelegramNotification`, после `file_id`:

```python
    # Идемпотентность рассылки: общий id всех чанков одной рассылки. None =
    # дедуп выключен (старое сообщение / degrade на стороне бота).
    broadcast_id: str | None = None
    # Диагностика чанкования (для логов).
    chunk_index: int | None = None
    chunk_total: int | None = None
```

- [ ] **Step 4: Запустить — убедиться, что проходит**

Run: `cd apps/tg_user_bot && uv run pytest tests/test_notification_schema.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/tg_user_bot/app/modules/notification_module/schemas.py apps/tg_user_bot/tests/test_notification_schema.py
git commit -m "feat(tg_user_bot): add broadcast_id/chunk meta to notification schema"
```

---

### Task B5: Дедуп в циклах рассылки (`sender.py`)

**Files:**
- Modify: `apps/tg_user_bot/app/modules/notification_module/services/sender.py` (`_broadcast_text` строки ~87-99, `_broadcast_file` строки ~107-133)
- Test: `apps/tg_user_bot/tests/test_notification_sender.py`

**Interfaces:**
- Consumes: `idempotency_store.claim(broadcast_id, chat_id) -> bool` (B2), `TelegramNotification.broadcast_id` (B4).
- Produces: оба цикла перед отправкой получателю вызывают `claim`; при `False` — `continue` (пропуск), при `True` — отправляют как раньше. Поведение reuse Telegram `file_id` сохраняется (первый РЕАЛЬНО отправленный получатель грузит байты).

- [ ] **Step 1: Написать падающий тест (мок bot + claim)**

Изучить, как `tests/test_notification_sender.py` сейчас мокает `bot` (вероятно через monkeypatch `sender.bot`). В том же стиле добавить:

```python
from unittest.mock import AsyncMock

import pytest

from app.modules.notification_module.services import sender
from app.modules.notification_module.schemas import TelegramNotification


@pytest.mark.asyncio
async def test_text_broadcast_skips_already_claimed(monkeypatch):
    # claim: True для 1 и 3, False для 2 (уже отправляли 2-му).
    async def fake_claim(broadcast_id, chat_id):
        return chat_id != 2

    monkeypatch.setattr(sender.idempotency_store, "claim", AsyncMock(side_effect=fake_claim))
    send_message = AsyncMock()
    monkeypatch.setattr(sender.bot, "send_message", send_message)
    monkeypatch.setattr(sender.asyncio, "sleep", AsyncMock())  # убрать троттлинг в тесте

    n = TelegramNotification(chat_ids=[1, 2, 3], message="hi", broadcast_id="b1")
    await sender.send_notification(n)

    sent_to = [call.kwargs["chat_id"] for call in send_message.await_args_list]
    assert sent_to == [1, 3]  # 2-й пропущен по claim=False
```

- [ ] **Step 2: Запустить — убедиться, что падает**

Run: `cd apps/tg_user_bot && uv run pytest tests/test_notification_sender.py::test_text_broadcast_skips_already_claimed -v`
Expected: FAIL — сейчас шлёт всем троим (claim не вызывается).

- [ ] **Step 3: Встроить `claim` в оба цикла**

В `apps/tg_user_bot/app/modules/notification_module/services/sender.py`:

Импорт рядом с `from .backend_files import fetch_file`:
```python
from .idempotency import idempotency_store
```

В `_broadcast_text` — в начало тела цикла:
```python
    for chat_id in notification.chat_ids:
        # Дедуп: уже отправляли этому получателю в рамках этой рассылки — пропускаем.
        if not await idempotency_store.claim(notification.broadcast_id, chat_id):
            continue
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
```

В `_broadcast_file` — в начало тела цикла, ДО построения `media`:
```python
    for chat_id in notification.chat_ids:
        # Дедуп до загрузки байтов: пропущенный получатель не «съедает» reuse file_id.
        if not await idempotency_store.claim(notification.broadcast_id, chat_id):
            continue
        # первый раз — байты; дальше — уже загруженный Telegram file_id
        media = tg_file_id or BufferedInputFile(
            data, filename=f"file_{notification.file_id}"
        )
        ...  # остальной код send_photo/send_document без изменений
```

- [ ] **Step 4: Запустить тесты sender целиком**

Run: `cd apps/tg_user_bot && uv run pytest tests/test_notification_sender.py -v`
Expected: PASS (новый тест + старые; старые без `broadcast_id` идут в degrade-ветку `claim`→True, поведение не меняется).

- [ ] **Step 5: Обновить документацию модуля**

В `apps/tg_user_bot/app/modules/notification_module/README.md` (RU) и `CLAUDE.md`/`AGENTS.md` (EN): описать новые поля контракта (`broadcast_id`/`chunk_index`/`chunk_total`), идемпотентность через Redis (claim-before-send, TTL), поведение degrade (нет broadcast_id / Redis недоступен → без дедупа), новые ENV.

- [ ] **Step 6: Commit**

```bash
git add apps/tg_user_bot/app/modules/notification_module/ apps/tg_user_bot/tests/test_notification_sender.py
git commit -m "feat(tg_user_bot): dedup newsletter recipients via Redis claim"
```

---

## Final verification (оба трека)

- [ ] **Backend unit-тесты:** `cd apps/backend && uv run pytest -q` → PASS.
- [ ] **Bot unit-тесты:** `cd apps/tg_user_bot && uv run pytest -q` → PASS.
- [ ] **Ruff format:** `cd apps/backend && uv run ruff format .` и `cd apps/tg_user_bot && uv run ruff format .`.
- [ ] **Manual end-to-end (ручной шаг пользователя, не автоматизируется):**
  1. Поднять инфру + сервисы: `docker compose -f infra/docker-compose.infra.yml -f infra/docker-compose.apps.yml up --build -d`.
  2. Создать тестовую аудиторию > `newsletter_chunk_size` (например, 1200 пользователей).
  3. Отправить рассылку через админку/`POST /telegram/newsletter`; в ответе появится `broadcast_id`.
  4. В логах бота — последовательные чанки (`chunk_index/chunk_total`), ack каждого чанка.
  5. **Тест дедупа:** перезапустить бота (`docker restart`) в середине рассылки → после восстановления редоставленные чанки НЕ шлют повторно уже отправленным (по логам claim=skip). Полного дубля аудитории нет.
  6. **Тест degrade:** остановить Redis (`docker stop <redis>`) и повторить рассылку → доставка идёт, в логах warning про degrade, дедупа нет.

## Out of scope (YAGNI)

- Ретрай чанка при временной ошибке `fetch_file`/Redis с DLX/лимитом попыток (сейчас: упавший чанк теряется, но это один чанк, а не вся рассылка; degrade покрывает Redis). Отметить как возможное будущее улучшение.
- Перенос публикации чанков в Taskiq-фон (для аудиторий в миллионы, когда сама публикация N сообщений перестанет укладываться в запрос).
- Персистентная история рассылок, delivery receipts, расписание.
- Прогресс-бар рассылки в админке.
