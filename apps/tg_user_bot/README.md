# Telegram Template

Минимально рабочий шаблон Telegram-бота на `aiogram 3` в режиме `polling-only`.

Этот шаблон нужен как фундамент, к которому дальше подключаются дополнительные модули.
Он специально сделан тонким:

- бот не хранит базу данных
- бот не содержит бизнес-хранилище
- бот отвечает только за Telegram-слой
- при необходимости внешние интеграции подключаются отдельно

## Идея проекта

Внутри шаблона ответственность разделена по слоям:

- есть точка входа
- есть слой конфигурации
- есть слой сборки приложения
- есть lifecycle запуска и остановки
- есть явная регистрация модулей
- есть папка `app/modules`, где живут функции бота

За счёт этого проект легко расширять без превращения `main.py` в один большой файл.

## Текущий функционал

В боте подключены две воронки DMCAGuardian: `/start` отправляет питч бесплатного
гайда, PDF-файл, видео с кнопками связи («Написать» и «Оставить заявку» через
Client MiniApp) и выставляет пользователю состояние `persona_start` в backend.
Deep link `/start business` ведёт в аналогичную воронку для агентств
(состояние `business_start`). Подробности — в
[app/modules/persona/CLAUDE.md](app/modules/persona/CLAUDE.md) и
[app/modules/business/CLAUDE.md](app/modules/business/CLAUDE.md).

Сейчас в приложении подключены модули с разной ролью:

- `system` — обязательный системный infrastructure layer
- `rmq_module` — общий RabbitMQ transport-layer
- `notification_module` — RMQ-consumer, доставляющий пользователям сообщения и массовые рассылки от backend
- `support_module` — чат пользователя с администратором, включая фото и документы
- `requisition_module` — создание заявок из сценариев бота
- `persona` — продуктовая воронка DMCAGuardian: гайд, видео и кнопки связи на `/start`
- `business` — воронка DMCAGuardian для агентств на deep link `/start business`

Системный модуль предоставляет базовые команды:

- `/start` — проверка, что бот запущен
- `/authstatus` — базовая проверка auth-сессии через backend
- `/usersysinfo` — техническая информация о пользователе и runtime в debug-режиме

Он также является обязательным infrastructure layer для остальных Telegram-модулей:

- хранит in-memory auth cache
- предоставляет `aiohttp`-клиент для backend
- даёт `login_required` декоратор для защищённых хендлеров
- публикует auth-сессию в runtime context текущего update

`rmq_module` не добавляет пользовательских Telegram-команд, но встраивается в
общий lifecycle и поднимает RabbitMQ runtime, если есть consumer
registrations и включён `RABBITMQ_CONSUMER_ENABLED=true`.

`notification_module` — это RMQ-consumer поверх `rmq_module`. Он слушает очередь
`telegram_notifications` и доставляет пользователям сообщения от backend: одиночные
уведомления и массовые рассылки. Backend режет аудиторию на настраиваемые чанки,
каждый RMQ payload содержит список `chat_ids`, который бот последовательно обрабатывает.
Двухфазные Redis-маркеры `processing → sent` предотвращают повтор успешных доставок;
временная ошибка освобождает claim и возвращает сообщение в очередь. Поддерживаются текст, одно вложение
(резолвится по `file_id` через backend `GET /api/files/{id}`; картинка → фото,
остальное → документ) и клавиатуры (`use_buttons: INLINE|REPLY` с плоским списком
кнопок). Контракт сообщения — в
[app/modules/notification_module/API.md](app/modules/notification_module/API.md).

Точные контракты и семантика повторов описаны в
[notification_module/API.md](app/modules/notification_module/API.md),
[notification_module/CLAUDE.md](app/modules/notification_module/CLAUDE.md) и
[rmq_module/CLAUDE.md](app/modules/rmq_module/CLAUDE.md).

## Структура проекта

Каждый модуль документируется парой файлов на английском: `CLAUDE.md`
(инструкции для агента) и `API.md` (контракты интерфейсов — команды, deep links,
RMQ- и backend-контракты). Отдельных модульных `README.md` больше нет.

```text
tg_user_bot/
├── .claude/
│   ├── CLAUDE.md            # контекст сервиса для агента
│   └── MODULES.md           # как добавлять новые модули
├── app/
│   ├── bot/
│   │   ├── app.py
│   │   ├── dispatcher.py
│   │   ├── lifecycle.py     # startup/shutdown внешних ресурсов
│   │   └── registry.py      # явная регистрация роутеров
│   ├── core/
│   │   ├── config.py
│   │   ├── context.py
│   │   └── logging.py
│   └── modules/
│       ├── system/          # обязательный слой: auth, backend-клиент, /start
│       ├── rmq_module/      # общий RabbitMQ transport-layer
│       ├── notification_module/  # RMQ-consumer доставки уведомлений/рассылок
│       ├── support_module/  # FSM поддержки (текст → RMQ, медиа → HTTP)
│       ├── requisition_module/   # FSM-опросники заявок (/apply)
│       ├── persona/         # воронка DMCAGuardian на /start (без router)
│       └── business/        # воронка для агентств на /start business (без router)
├── assets/                  # PDF/видео воронок
├── docs/
│   └── plans/
├── tests/
├── main.py
├── pyproject.toml
└── .env
```

Каждый модуль внутри содержит `CLAUDE.md`, `API.md`, `handlers.py` (или
`service.py` у безроутерных воронок) и, по необходимости, `services/`,
`schemas.py`, `states.py`, `keyboards.py`, `messages.json`, `config.py`.

## Как устроен запуск

Полный поток запуска такой:

1. Вы вызываете `python main.py`.
2. `main.py` включает логирование.
3. `main.py` вызывает `run_polling()` из `app/bot/app.py`.
4. `app.py` создаёт `Bot`.
5. `app.py` создаёт `Dispatcher`.
6. `dispatcher.py` просит `registry.py` подключить все модульные роутеры.
7. `lifecycle.py` регистрирует действия на старт и остановку.
8. Запускается polling.
9. Когда Telegram присылает update, aiogram направляет его в нужный модульный `router`.

## Объяснение файлов

### `main.py`

Точка входа в приложение.

Его задача специально очень маленькая:

- включить logging
- передать настройки
- запустить polling

Почему так хорошо:
`main.py` не должен знать детали модулей, lifecycle и внутренних зависимостей.
Он только запускает приложение.

### `app/core/config.py`

Файл конфигурации.

Он:

- читает `.env`
- валидирует настройки
- даёт удобный объект `settings`

Сейчас он понимает:

- `TOKEN` — обязательный токен Telegram-бота
- `drop_pending_updates` — управляет тем, очищать ли накопленные Telegram-updates при старте; по умолчанию `True`
- `BACKEND_URL` — адрес backend-сервиса
- `BACKEND_API_PREFIX` — API-prefix backend, по умолчанию `/api`
- `BACKEND_REQUEST_TIMEOUT` — таймаут HTTP-запросов к backend
- `AUTH_CACHE_MAX_SIZE` — максимальный размер in-memory auth cache
- `BOT_PARSE_MODE` — режим форматирования, по умолчанию `HTML`
- `CLIENT_MINIAPP_URL` — HTTPS URL клиентского Mini App
- `ADMIN_CONTACT_URL` — ссылка на аккаунт админа для кнопки «Написать»; без неё кнопка скрыта
- `PERSONA_GUIDE_PATH` — путь к PDF-гайду; по умолчанию `assets/sila_tvorozhka.pdf`
- `PERSONA_VIDEO_PATH` — путь к видео воронки; по умолчанию `assets/coala.mp4`
- `BUSINESS_GUIDE_PATH`, `BUSINESS_VIDEO_PATH` — ассеты воронки для агентств;
  по умолчанию те же файлы, что у persona
- `DEBUG` — включает debug-only команды вроде `/usersysinfo`

Важно:
бот не читает настройки базы данных, потому что база должна жить не здесь.

Отдельно про `drop_pending_updates`:

- это значение прокидывается в `bot.delete_webhook(drop_pending_updates=...)` на startup
- при `True` бот удаляет накопившиеся апдейты и не пытается дообработать старую очередь после простоя
- это безопасный дефолт для `polling`, когда важнее стартовать из чистого состояния
- если вам принципиально обработать сообщения, которые пришли во время остановки, установите `drop_pending_updates=false`

Так как `MainSettings` объявлен с `case_sensitive=True` и у поля нет отдельного alias,
в `.env` сейчас нужно использовать именно ключ `drop_pending_updates`.

### `app/core/logging.py`

Отвечает за базовое логирование процесса.

Смысл этого файла:

- не смешивать logging с `main.py`
- иметь одну точку настройки формата логов
- легко расширить логирование позже

### `app/bot/app.py`

Это слой сборки приложения.

Здесь происходит следующее:

- создаётся `Bot`
- создаётся `Dispatcher`
- подключаются lifecycle-хуки
- всё собирается в контейнер `TelegramApplication`

Почему это полезно:
если потом понадобится расширять способ сборки, `main.py` останется прежним.

### `app/bot/dispatcher.py`

Создаёт и настраивает `Dispatcher`.

Сейчас его роль простая:

- создать объект `Dispatcher`
- подключить модульные роутеры через `registry.py`

Почему отдельный файл удобен:
сюда позже можно добавить middleware, filters, FSM storage и другие настройки dispatcher, не трогая точку входа.

### `app/bot/registry.py`

Единая точка подключения модулей.

Сейчас там явно регистрируются:

- `system_router`;
- инфраструктурный `rmq_router`;
- опциональные `notification_router` и `support_router`;
- `requisition_router`.

Это сделано намеренно.

Почему явная регистрация хороша:

- видно, какие модули реально активны
- меньше магии
- проще дебажить
- все активные модули видны в одном месте

Если вы добавляете новый модуль, именно здесь он становится частью приложения.
Порядок важен: системный `/start` подключается раньше catch-all обработчиков поддержки.

### `app/bot/lifecycle.py`

Здесь живёт код старта и остановки.

Сейчас на старте выполняется:

- `delete_webhook(drop_pending_updates=settings.drop_pending_updates)`
- инициализация runtime-ресурсов system-модуля
- попытка поднять runtime `rmq_module`

Это важно для polling-режима:
если у бота раньше был webhook или накопились старые апдейты, мы очищаем состояние и стартуем чисто.

Что означает `drop_pending_updates`:

- `True` — Telegram удалит накопленную очередь updates
- `False` — бот после старта сможет получить старые updates через polling

Используйте `False` только если вы действительно готовы обрабатывать старые входящие
события после рестарта. Для большинства шаблонных сценариев безопаснее оставлять `True`.

Сейчас на остановке выполняется:

- закрытие `bot.session`
- закрытие backend HTTP client
- очистка auth cache
- остановка RMQ runtime, если он был запущен

Это нужно, чтобы корректно закрывать сетевые ресурсы aiogram.

### `app/modules/system/handlers.py`

Это первый модуль.

Внутри него:

- создаётся `router = Router(name="system")`
- описываются хендлеры
- команды `/start`, `/authstatus` и `/usersysinfo` обрабатываются именно этим роутером

Смысл файла:
показать минимальный канонический пример модульного `handlers.py`.

### `app/modules/system/auth/*`

Подпакет базовой аутентификации Telegram-модулей.

Он:

- кеширует auth-сессии в памяти процесса
- выполняет backend flow `login -> create user -> login`
- предоставляет `login_required`

### `app/modules/system/client.py`

Изолирует HTTP-общение с backend.

Это нужно, чтобы:

- не размазывать `aiohttp` по хендлерам
- иметь одну точку обработки network-ошибок
- держать backend contract рядом с system-модулем

### `app/modules/system/messages.json`

Файл с текстовыми шаблонами.

Сейчас используется для auth- и debug-сообщений system-модуля.

Зачем выносить тексты отдельно:

- легче редактировать ответы
- меньше “жёстко вшитого” текста в коде
- удобно для роста модуля

## Как добавить новый модуль

Канонический гайд для агентов — [.claude/MODULES.md](.claude/MODULES.md)
(структура, документация `CLAUDE.md`/`API.md`, регистрация, auth). Ниже —
краткий пример «на пальцах».

Допустим, вы хотите сделать модуль `profile`.

### Шаг 1. Создайте папку модуля

```text
app/modules/profile/
├── handlers.py
├── services.py
├── states.py
└── messages.json
```

Не все файлы обязательны.
Минимально нужен только `handlers.py`.

### Шаг 2. Создайте router

Пример:

```python
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="profile")


@router.message(Command("profile"))
async def profile_command(message: Message) -> None:
    await message.answer("Профильный модуль подключён")
```

### Шаг 3. Подключите модуль в `registry.py`

Пример:

```python
from app.modules.profile.handlers import router as profile_router


def register_routers(dispatcher):
    dispatcher.include_router(system_router)
    dispatcher.include_router(profile_router) # <<<<
```

После этого модуль становится активной частью бота.

## Рекомендуемая структура модуля

Для каждого нового модуля удобно придерживаться такой логики:

- `handlers.py`
  Telegram-хендлеры: команды, callback, сообщения
- `services.py`
  Работа с внешними интеграциями
- `states.py`
  FSM состояния, если есть сценарий из нескольких шагов
- `messages.json`
  Текстовые шаблоны
- `keyboards.py` или `buttons.py`
  Клавиатуры и кнопки

Важно:
не складывайте внешние HTTP-вызовы прямо в handlers, если логика становится нетривиальной.
Лучше вынести это в `services.py`.

## Переменные окружения

Пример `.env`:

```env
TOKEN="your-telegram-bot-token"
BACKEND_URL="http://localhost:8000/"
SERVICE_TOKEN="shared-service-secret"
BOT_PARSE_MODE="HTML"
CLIENT_MINIAPP_URL="http://localhost:8081"
ADMIN_CONTACT_URL="https://t.me/your-admin-username"
redis_password="shared-redis-password"
```

### Что обязательно

- `TOKEN`

### Что опционально

- `BACKEND_URL`
- `SERVICE_TOKEN` — обязателен для защищённых server-to-server вызовов backend
- `BOT_PARSE_MODE`
- `CLIENT_MINIAPP_URL`
- `ADMIN_CONTACT_URL` — без него не показывается кнопка «Написать»
- `PERSONA_GUIDE_PATH`, `PERSONA_VIDEO_PATH` — пути к ассетам воронки
- `BUSINESS_GUIDE_PATH`, `BUSINESS_VIDEO_PATH` — ассеты воронки для агентств
- `redis_password` — включает идемпотентность рассылок через Redis

## Запуск проекта

Установить зависимости и запустить:

```bash
uv sync --dev
uv run python main.py
```

## Полезные проверки

Проверка, что проект компилируется:

```bash
python -m compileall app main.py
uv run ruff check .
uv run pytest -q
```

## Что важно помнить при развитии проекта

- Не переносите базу данных в этого бота.
- Не перегружайте `main.py`.
- Не подключайте модули скрытой магией, пока вам важна прозрачность.
- Каждый модуль должен быть самостоятельным и понятным.
- Если появляется новая ответственность, лучше вынести её в отдельный файл, чем раздувать `handlers.py`.

## Автоматические проверки

Workflow `.github/workflows/quality.yml` выполняет `uv sync --dev`, Ruff и pytest.
Не добавляйте зависимости через `pip`: изменяйте `pyproject.toml` и lock-файл через `uv`.
