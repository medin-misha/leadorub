# Telegram Module

`telegram_module` - это прикладной модуль `fastapi_template` для хранения Telegram-пользователей, их профилей и поведенческой статистики.

Модуль используется как единая точка для:

- хранения Telegram-identity в модели `TelegramUser`;
- хранения прикладных данных профиля в модели `UserProfile`;
- хранения поведенческой статистики в модели `UserStats` (последний заход, источник привлечения, состояние диалога);
- атомарной регистрации пользователя (создание сразу трёх связанных моделей);
- идемпотентного создания Telegram-пользователей по `telegram_id`;
- обновления `last_seen_at` при логине;
- HTTP-эндпоинтов для CRUD-операций над Telegram-пользователями, профилями и статистикой.

Модуль опирается на инфраструктуру из `app.modules.system` и не должен дублировать общие CRUD- и DB-error-механизмы локально.

## Структура

```text
telegram_module/
├── __init__.py
├── handlers.py
├── models/
│   ├── __init__.py
│   ├── telegram_user.py
│   ├── user_profile.py
│   └── user_stats.py
├── schemas/
│   ├── __init__.py
│   ├── telegram_user.py
│   ├── user_profile.py
│   └── user_stats.py
├── services/
│   ├── __init__.py
│   └── user_service.py
├── utils/
├── AGENTS.md
└── README.md
```

## Зависимость от `system`

`telegram_module` построен поверх `system` и повторно использует его общие примитивы:

- `Base` и `TimestampMixin` для ORM-моделей;
- `CRUD` для типовых операций create/get/patch/delete;
- `DBErrorHandler` для нормализации ошибок SQLAlchemy.

Предпочтительные импорты:

```python
from app.modules.system import Base, TimestampMixin, CRUD
from app.modules.system.services.errors import DBErrorHandler
```

## Граница ответственности

Модуль владеет тремя сущностями:

- `TelegramUser` - Telegram-identity пользователя;
- `UserProfile` - прикладной профиль, связанный с Telegram-пользователем;
- `UserStats` - поведенческая статистика, связанная с Telegram-пользователем.

Разделение ответственности такое:

- поля, приходящие из Telegram как внешней системы → `TelegramUser`
  (`telegram_id`, `username`, `first_name`, `last_name`, `language_code`);
- поля, которые собирает или изменяет само приложение → `UserProfile`
  (`phone`, `email`, `timezone`, `full_name`, `note`);
- поля, меняющиеся по ходу жизни пользователя в боте → `UserStats`
  (`last_seen_at`, `source`, `state`).

## Основные модели

### `TelegramUser`

Находится в [models/telegram_user.py](models/telegram_user.py).

`TelegramUser` хранит неизменную Telegram-identity пользователя.

Ключевые поля:

- `telegram_id: int` - внешний уникальный идентификатор Telegram-пользователя;
- `username: str | None` - username в Telegram;
- `first_name: str | None`;
- `last_name: str | None`;
- `language_code: str | None` - языковой код Telegram-клиента;
- `is_blocket_bot: bool` - текущий флаг блокировки бота.

Связи:

- `user_profile` - one-to-one профиль (`uselist=False`, `lazy="selectin"`, каскадное удаление);
- `user_stats` - one-to-one статистика (`uselist=False`, `lazy="selectin"`, каскадное удаление).

> Поле `last_seen_at` больше не хранится в `TelegramUser` - оно переехало в `UserStats`.

### `UserProfile`

Находится в [models/user_profile.py](models/user_profile.py).

`UserProfile` хранит прикладные данные, связанные с Telegram-пользователем.

Ключевые поля:

- `telegram_user_id: int` - внешний ключ на `TelegramUser` (`ondelete="CASCADE"`, unique);
- `phone`, `email`, `timezone`, `full_name`, `note`.

Правила связи:

- у одного `TelegramUser` ожидается не более одного `UserProfile`;
- удаление `TelegramUser` удаляет и связанный профиль.

### `UserStats`

Находится в [models/user_stats.py](models/user_stats.py).

`UserStats` хранит поведенческую статистику пользователя.

Ключевые поля:

- `telegram_user_id: int` - внешний ключ на `TelegramUser` (`ondelete="CASCADE"`, unique);
- `last_seen_at: datetime | None` - последний заход; `server_default=now()`, обновляется при логине;
- `source: str | None` - источник, из которого пришёл пользователь (deep-link payload, UTM и т.п.);
- `state: str | None` - текущее состояние пользователя в диалоге бота (FSM-state).

Правила связи:

- у одного `TelegramUser` ожидается не более одного `UserStats`;
- удаление `TelegramUser` удаляет и связанную статистику.

При изменении конфигурации relationship или foreign key проверяйте и ORM-поведение, и фактическое поведение базы данных.

## Pydantic-схемы

Схемы находятся в:

- [schemas/telegram_user.py](schemas/telegram_user.py)
- [schemas/user_profile.py](schemas/user_profile.py)
- [schemas/user_stats.py](schemas/user_stats.py)

Основные DTO:

- `TelegramUserRegister` - **композитная** входная схема регистрации: вложенные `telegram_user` (обязателен), `profile` и `stats` (опциональны);
- `TelegramUserCreate` / `UserProfileCreate` / `UserStatsCreate` - плоские схемы создания одной сущности;
- `UserProfileRegister` / `UserStatsRegister` - вложенные схемы для регистрации (без `telegram_user_id`, у статистики - ещё и без `last_seen_at`, оно ставится сервером);
- `TelegramUserLogin` - схема логина по `telegram_id`;
- `TelegramUserPatch` / `UserProfilePatch` / `UserStatsPatch` - частичное обновление;
- `TelegramUserRead` - чтение пользователя с вложенными `user_profile` и `user_stats`;
- `UserProfileRead` / `UserStatsRead` - схемы чтения профиля и статистики.

При изменении моделей синхронно обновляйте схемы, чтобы не расходились ORM-структура и API-ответы.

## Сервисный слой

Сервисная логика находится в [services/user_service.py](services/user_service.py). Здесь собрана Telegram-специфичная orchestration-логика поверх `CRUD`.

### Модель атомарности

Все вставки в рамках одного запроса идут через одну `AsyncSession`, которая коммитит единожды на границе запроса (`database.get_session`). Методы `CRUD` делают только `flush()` (без commit), поэтому все записи запроса - это одна транзакция. Если любой шаг падает, `DBErrorHandler` поднимает `HTTPException`, запрос завершается ошибкой, а `get_session` откатывает транзакцию целиком.

Именно поэтому многошаговым flow **не нужен** ручной cleanup: при сбое пользователь, профиль и статистика откатываются вместе.

### `create_telegram_user(...)`

Атомарная регистрация. Контракт:

1. вызывает `CRUD.get_or_create(...)` с `lookup_fields=("telegram_id",)` для `TelegramUser`;
2. если пользователь уже существует - возвращает его и `created=False` (профиль/статистику не пересоздаёт);
3. если пользователь новый - дополнительно создаёт `UserProfile` и `UserStats` через `CRUD.create(...)`;
4. `UserStats.last_seen_at` ставится в момент регистрации; `profile`/`stats` на входе опциональны;
5. перед возвратом подгружает `user_profile` и `user_stats` для сериализации ответа.

За счёт `get_or_create` `POST /telegram/users` остаётся идемпотентным.

### `bulk_create_telegram_users(...)`

Для каждого элемента создаёт `TelegramUser` + `UserProfile` + `UserStats` (через `CRUD.bulk_create`). Идемпотентности нет: дубликат `telegram_id` приведёт к `IntegrityError` (400). Вся партия пишется в одной транзакции - при сбое откатывается целиком.

### `login_telegram_user(...)`

Логин - это событие записи, а не только чтение:

- ищет пользователя по `telegram_id`;
- возвращает `404`, если не найден;
- обновляет `UserStats.last_seen_at` (пропускается, если статистики нет);
- делает `flush()` и `refresh()`.

## HTTP API

Router находится в [handlers.py](handlers.py) и объявлен с префиксом `/telegram`.

### TelegramUser endpoints

- `POST /api/telegram/login` - логин существующего пользователя по `telegram_id`;
- `POST /api/telegram/users` - атомарная идемпотентная регистрация (композитное тело);
- `POST /api/telegram/users/bulk` - массовая регистрация (список композитных тел);
- `GET /api/telegram/users/{id}` - пользователь по внутреннему `id` (с `user_profile` и `user_stats`);
- `GET /api/telegram/users` - список пользователей с пагинацией и поиском;
- `PATCH /api/telegram/users/{id}` - частичное обновление пользователя;
- `DELETE /api/telegram/users/{id}` - удаление пользователя (каскадом удалит профиль и статистику).

Тело `POST /api/telegram/users`:

```json
{
  "telegram_user": { "telegram_id": 123456789, "username": "ivan", "language_code": "ru" },
  "profile": { "phone": "+7...", "full_name": "Ivan Petrov" },
  "stats": { "source": "instagram_bio", "state": "start" }
}
```

`profile` и `stats` опциональны. Если их не передать - создаются пустой профиль и статистика с дефолтами.

Поведение по статус-кодам:

- `201 Created`, если пользователь был создан;
- `200 OK`, если пользователь с таким `telegram_id` уже существовал.

### UserProfile endpoints

- `POST /api/telegram/profile` - создание профиля;
- `GET /api/telegram/profile/{id}` - профиль по внутреннему `id`;
- `GET /api/telegram/profile` - список профилей с пагинацией и поиском;
- `PATCH /api/telegram/profile/{id}` - частичное обновление профиля;
- `DELETE /api/telegram/profile/{id}` - удаление профиля.

### UserStats endpoints

- `POST /api/telegram/stats` - создание статистики;
- `GET /api/telegram/stats/{id}` - статистика по внутреннему `id`;
- `GET /api/telegram/stats` - список статистики с пагинацией и поиском;
- `PATCH /api/telegram/stats/{id}` - частичное обновление статистики (например, смена `state`);
- `DELETE /api/telegram/stats/{id}` - удаление статистики.

Списковые `GET`-эндпоинты используют общий `CRUD.get(...)` и наследуют стандартное поведение `system`:

- `page` и `limit` для пагинации;
- `search` для поиска;
- `field` для поиска по конкретному полю.

## Экспорт модуля

В [telegram_module/__init__.py](__init__.py) наружу экспортируются:

- `TelegramUser`
- `UserProfile`
- `UserStats`

Предпочтительный импорт моделей из других модулей:

```python
from app.modules.telegram_module import TelegramUser, UserProfile, UserStats
```

## Правила изменений

Хорошие изменения в этом модуле:

- добавление полей, которые действительно относятся к identity/профилю/статистике;
- расширение сервисной логики, координирующей несколько моделей;
- улучшение согласованности между созданием `TelegramUser`, `UserProfile` и `UserStats`;
- уточнение API-контрактов и документации.

Нежелательные изменения:

- перенос общей инфраструктурной логики из `system` в `telegram_module`;
- разрастание `handlers.py` бизнес-логикой;
- нарушение атомарности (single-transaction) в многошаговых create-flow;
- переименование публичных полей без миграций и синхронного обновления схем.

## Практические заметки

- если меняются модели - синхронно обновляйте `models`, `schemas`, `handlers` и миграции;
- если меняется экспорт - обновляйте `telegram_module/__init__.py` и `app/modules/__init__.py` (для обнаружения Alembic);
- если меняется поведение логина или создания пользователя - обновляйте и `README.md`, и `AGENTS.md`;
- если логика затрагивает несколько сущностей - держите координацию в `services/user_service.py`, а не в `handlers.py`.

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
