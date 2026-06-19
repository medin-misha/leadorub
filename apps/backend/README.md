# Контекст проекта

> [!NOTE]
> Этот раздел предназначен для описания конкретного сервиса, создаваемого на базе данного шаблона. При начале разработки заполните этот блок актуальной бизнес-информацией.

### Описание сервиса

[Кратко опишите назначение разрабатываемого сервиса. Какую бизнес-задачу или функционал он реализует в рамках общей архитектуры?]

### Ключевой функционал

- [Функция 1: например, обработка входящих заказов]
- [Функция 2: например, генерация ежемесячных отчётов]
- [Функция 3: например, синхронизация данных с внешней CRM]

### Окружения и ссылки

- **Development**: [Домен или IP-адрес стенда разработки]
- **Production**: [Домен или IP-адрес продакшена]

### Контакты команды

- **Product Owner**: [Имя / Telegram]
- **Tech Lead**: [Имя / Telegram]
- **Разработчики**: [Имя / Telegram]

---

# Документация шаблона

`fastapi_template` — это модульный backend-шаблон на базе FastAPI и PostgreSQL, спроектированный для быстрой разработки масштабируемых и изолированных сервисов.

## Технологический стек

- **Язык и среда**: Python 3.11+, пакетный менеджер `uv` для детерминированной сборки зависимостей.
- **Веб-фреймворк**: FastAPI (с настроенной поддержкой CORS), Pydantic v2 (валидация данных), Pydantic Settings (конфигурация).
- **База данных**: PostgreSQL, асинхронный движок SQLAlchemy 2.0.
- **Миграции**: Alembic с полной поддержкой асинхронного режима.
- **Объектное хранилище**: асинхронная библиотека `aiobotocore` для S3-совместимых хранилищ (MinIO, AWS S3).
- **Очереди сообщений**: асинхронная библиотека `aio-pika` для интеграции с RabbitMQ (AMQP).
- **Отложенные задачи**: `taskiq` (broker на RabbitMQ, schedule source и result backend на Redis) для фоновых и запланированных задач.

---

## Архитектура и структура проекта

Шаблон реализует модульную архитектуру, обеспечивающую изоляцию логики отдельных доменов. Все сквозные инфраструктурные элементы вынесены на глобальный уровень.

### Файловая структура шаблона

```text
fastapi_template/
├── alembic/                  # Скрипты и версии миграций базы данных
├── app/                      # Исходный код приложения
│   ├── api/
│   │   └── router.py         # Главный роутер, объединяющий роутеры модулей
│   ├── core/                 # Общесистемные примитивы конфигурации и инфраструктуры
│   │   ├── config.py         # Загрузка и валидация настроек приложения из .env
│   │   ├── database.py       # Асинхронное подключение, сессии SQLAlchemy
│   │   └── security.py       # Общие утилиты шифрования и авторизации
│   ├── lifecycle.py          # Управление запуском и завершением внешних ресурсов
│   └── modules/              # Изолированные модули
│       ├── system/           # Общие системные примитивы и хелперы
│       ├── rmq_module/       # Встроенная подсистема RabbitMQ
│       ├── taskiq_module/    # Инфраструктура отложенных и фоновых задач
│       └── file_module/      # Встроенный модуль файлового хранилища
├── main.py                   # Точка входа в FastAPI-приложение
├── pyproject.toml            # Декларация (не)зависимостей
└── uv.lock                   # Точный слепок установленных версий библиотек
```

### Стандартная структура модуля

Каждая доменная область в каталоге `app/modules/` должна следовать единой структуре каталогов:

```text
app/modules/module_name/
├── handlers.py               # Роутеры эндпоинтов API (FastAPI)
├── models/                   # Определение SQLAlchemy-моделей базы данных
├── schemas/                  # Схемы валидации запросов и ответов (Pydantic DTO)
├── services/                 # Классы и функции бизнес-логики (сервисный слой)
├── utils/                    # Изолированные утилиты этого конкретного модуля
├── AGENTS.md                 # Описание зоны отвецтвенности, API, и функционала для ИИ агента (Всегда на англиском)
└── README.md                 # Описание зоны ответственности и API модуля (Всегда на русском)
```

---

## Назначение встроенных модулей

Шаблон поставляется с четырьмя базовыми модулями, которые решают ключевые инфраструктурные задачи и служат примером реализации модульного подхода.

### 1. Системный модуль (`app/modules/system`)

Предоставляет базовые ORM-классы и обобщенную логику взаимодействия с СУБД:

- **Базовая модель** (`Base` в `models/base.py`): задаёт целочисленный первичный ключ `id` для всех таблиц проекта.
- **Временные метки** (`TimestampMixin` в `models/base.py`): автоматически проставляет поля `created_at` и `updated_at` на уровне СУБД.
- **Обобщенный CRUD-сервис** (`CRUD` в `services/crud.py`): содержит методы асинхронного создания (`create`, `bulk_create`, `get_or_create` для атомарной бесконфликтной вставки), чтения (`get` с поддержкой пагинации, сортировки, фильтрации и полнотекстового поиска), обновления (`patch`) и удаления (`delete`).
- **Обработка ошибок базы данных** (`DBErrorHandler` в `services/errors.py`): перехватывает исключения SQLAlchemy и транслирует их в стандартные ошибки FastAPI (`HTTPException`) с логированием деталей.
- **Health check эндпоинты**: эндпоинты проверки жизнеспособности сервиса (`GET /api/system/health`) и доступности подключения к базе данных (`GET /api/system/health/db`).

### 2. Файловый модуль (`app/modules/file_module`)

Реализует полный цикл управления пользовательскими и системными файлами:

- **Асинхронная S3-интеграция** (`S3Client` в `services/s3_client.py`): стримит файлы напрямую в бакет из объекта `SpooledTemporaryFile` без временного сохранения на локальный диск сервера. Уникальные имена файлов генерируются в формате `UUID`.
- **Метаданные файлов**: сохраняет метаданные каждого файла (оригинальное имя, ссылка, заметка) в таблице `files` в PostgreSQL.
- **API эндпоинты**:
  - `POST /api/files/` — загрузка файлов через multipart/form-data. При сбое транзакции СУБД загруженный в S3 файл автоматически удаляется.
  - `GET /api/files/{id}` — стриминг файла с оригинальным именем (включая поддержку кириллицы) в заголовке `Content-Disposition`.
  - `DELETE /api/files/{id}` — транзакционное удаление метаданных из базы данных с последующей очисткой объектного хранилища.

### 3. Модуль интеграции очередей (`app/modules/rmq_module`)

Служит единой точкой подключения и обмена сообщениями через RabbitMQ:

- **Отказоустойчивость**: при выключенном RabbitMQ (`rabbitmq_enabled=false`) приложение продолжает полноценно работать, пропуская инициализацию брокера в жизненном цикле.
- **Публикация сообщений** (`RMQPublisher`): асинхронно отправляет структурированные сообщения, оборачивая полезную нагрузку в стандартный конверт с метаданными (`message_id`, `correlation_id`, `timestamp`, `source`).
- **Подписка на очереди** (`register_consumer`): предоставляет декларативный декоратор для регистрации функций-обработчиков событий непосредственно внутри ваших модулей.
- **Отладка**: предоставляет отладочные ручки (`POST /api/rmq/publish`, `POST /api/rmq/consume`) для локального тестирования и ручной отправки сообщений, доступные при активации `rabbitmq_debug_endpoints_enabled=true`.

### 4. Модуль отложенных задач (`app/modules/taskiq_module`)

Предоставляет общую инфраструктуру для фоновых и отложенных задач на базе `taskiq` (исполнение через RabbitMQ, расписания и результаты — через Redis):

- **Объявление задач**: любой модуль кладёт рядом `tasks.py` и декорирует функции через `@taskiq_broker.task`. Файлы `tasks.py` подхватываются автоматически (auto-discovery) — инфраструктуру менять не нужно.
- **Обобщённое планирование**: единый API для **любой** задачи — `schedule_task_at` (на дату), `schedule_task_after` (через интервал), `schedule_task_cron` (повторяющиеся), плюс `cancel_scheduled_task` / `list_scheduled_tasks` и немедленный запуск `enqueue_task`.
- **Строгий UTC**: всё время запуска нормализуется к UTC через `astimezone` в единственной точке `ensure_utc`; наивные (без таймзоны) даты отклоняются.
- **Результаты задач**: подключён Redis result backend — результат `enqueue_task(...)` можно дождаться через `await task.wait_result()`.
- **Отдельные процессы**: воркер (`taskiq worker app.modules.taskiq_module.broker:broker`) и планировщик (`taskiq scheduler app.modules.taskiq_module.scheduler:scheduler`) запускаются как отдельные процессы.
- **Отладка**: ручки `POST /api/taskiq/schedule`, `POST /api/taskiq/schedule/after`, `GET /api/taskiq/schedules`, `DELETE /api/taskiq/schedules/{id}` доступны при `debug=true` и `taskiq_debug_endpoints_enabled=true`.

Подробности — в [app/modules/taskiq_module/README.md](app/modules/taskiq_module/README.md).

---

## Инструкция по созданию новых модулей

Для добавления нового функционального домена или интеграции выполните следующие шаги.

> [!IMPORTANT]
> Если создаваемый модуль (сервис) оформляется в виде отдельного независимого проекта со своим `Dockerfile`, обязательно создайте в его корневом каталоге файл `.dockerignore` и исключите из сборки директории `.venv/`, `.git/`, локальные конфигурационные файлы `.env` и кэш (`__pycache__/`). Это предотвратит копирование локального окружения хоста и конфликты версий интерпретатора при сборке.

### Шаг 1. Создание каталога и файлов

Создайте каталог в `app/modules/<module_name>/` со стандартной структурой файлов:

```bash
mkdir -p app/modules/billing/{models,schemas,services,utils}
touch app/modules/billing/{__init__.py,handlers.py,README.md}
touch app/modules/billing/models/__init__.py
touch app/modules/billing/schemas/__init__.py
touch app/modules/billing/services/__init__.py
```

### Шаг 2. Разработка модели БД

Опишите модель, унаследовав её от `Base` и при необходимости можете использовать системные миксины см app/modules/system/:

```python
# app/modules/billing/models/invoice.py
from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from app.modules.system import Base, TimestampMixin

class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"

    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
```

### Шаг 3. Регистрация модели в Alembic

Для того чтобы Alembic мог автоматически отслеживать изменения схемы и генерировать миграции, импортируйте вашу новую модель в [app/modules/\_\_init\_\_.py](app/modules/__init__.py):

```python
from .system import Base, TimestampMixin
from .file_module import File
from .billing.models.invoice import Invoice  # Добавленный импорт

__all__ = [
    "Base",
    "TimestampMixin",
    "File",
    "Invoice",
]
```

### Шаг 4. Реализация API эндпоинтов

Опишите ручки в `handlers.py`, используя зависимости для получения сессии базы данных:

```python
# app/modules/billing/handlers.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import database
from app.modules.system import CRUD
from .models.invoice import Invoice

router = APIRouter(prefix="/billing", tags=["Billing"])

@router.get("/invoices/{id}")
async def get_invoice(id: int, session: AsyncSession = Depends(database.get_session)):
    return await CRUD.get(model=Invoice, session=session, id=id)
```

### Шаг 5. Подключение роутера к приложению

Импортируйте созданный роутер и включите его в центральный роутер в [app/api/router.py](app/api/router.py):

```python
from app.modules.billing.handlers import router as billing_router

# ...
router.include_router(billing_router)
```

### Шаг 6. Генерация и применение миграций СУБД

Создайте новую миграцию Alembic и обновите базу данных:

```bash
uv run alembic revision --autogenerate -m "add invoice model"
uv run alembic upgrade head
```

---

## Быстрый старт для разработчика

### Инициализация окружения

1. Установите зависимости проекта:
   ```bash
   uv sync
   ```
2. Скопируйте и настройте файл конфигурации окружения (включая переменную `cors_origins` для управления разрешенными источниками CORS):
   ```bash
   cp .env.example .env
   ```

### Накатывание миграций

Примените актуальную схему базы данных:

```bash
uv run alembic upgrade head
```

### Локальный запуск

Запустите сервер разработки FastAPI:

```bash
uv run uvicorn main:app --reload
```

Документация Swagger станет доступна по адресу `http://localhost:8000/docs`.
