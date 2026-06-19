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

Сейчас в шаблоне подключены три модуля с разной ролью:

- `system` — обязательный системный infrastructure layer
- `rmq_module` — общий RabbitMQ transport-layer
- `test_rmq_module` — демонстрационный модуль для проверки RMQ wiring

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

`test_rmq_module` нужен как встроенный пример использования `rmq_module`:

- регистрирует тестовый consumer во время импорта
- добавляет команду `/rmqping`, которая публикует тестовое сообщение в RabbitMQ

Если вам не нужен демонстрационный RMQ-сценарий, уберите `test_rmq_module` из
`app/bot/registry.py`.

## Структура проекта

```text
telegram_template/
├── app/
│   ├── bot/
│   │   ├── app.py
│   │   ├── dispatcher.py
│   │   ├── lifecycle.py
│   │   └── registry.py
│   ├── core/
│   │   ├── config.py
│   │   ├── context.py
│   │   └── logging.py
│   └── modules/
│       ├── rmq_module/
│       │   ├── AGENTS.md
│       │   ├── README.md
│       │   ├── config.py
│       │   ├── handlers.py
│       │   ├── runtime.py
│       │   ├── schemas/
│       │   └── services/
│       ├── system/
│       │   ├── auth/
│       │   ├── AGENTS.md
│       │   ├── README.md
│       │   ├── client.py
│       │   ├── config.py
│       │   ├── handlers.py
│       │   ├── messages.json
│       │   ├── messages.py
│       │   ├── runtime.py
│       │   └── schemas.py
│       └── test_rmq_module/
│           ├── handlers.py
│           └── services/
├── docs/
│   └── plans/
├── main.py
├── pyproject.toml
└── .env
```

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

Сейчас там явная регистрация:

- импортируется `system_router`
- импортируется пустой инфраструктурный `rmq_router`
- импортируется `test_rmq_router` для demo-команды `/rmqping`
- каждый роутер подключается через `dispatcher.include_router(...)`

Это сделано намеренно.

Почему явная регистрация хороша:

- видно, какие модули реально активны
- меньше магии
- проще дебажить
- все активные модули видны в одном месте

Если вы добавляете новый модуль, именно здесь он становится частью приложения.
Точно так же здесь можно явно отключить demo-модули перед production-использованием шаблона.

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
BOT_PARSE_MODE="HTML"
```

### Что обязательно

- `TOKEN`

### Что опционально

- `BACKEND_URL`
- `BOT_PARSE_MODE`

## Запуск проекта

Если зависимости уже установлены:

```bash
python main.py
```

Если вы работаете через локальное виртуальное окружение:

```bash
.venv/bin/python main.py
```

## Полезные проверки

Проверка, что проект компилируется:

```bash
python -m compileall app main.py
```

## Что важно помнить при развитии проекта

- Не переносите базу данных в этого бота.
- Не перегружайте `main.py`.
- Не подключайте модули скрытой магией, пока вам важна прозрачность.
- Каждый модуль должен быть самостоятельным и понятным.
- Если появляется новая ответственность, лучше вынести её в отдельный файл, чем раздувать `handlers.py`.

## Куда двигаться дальше

Следующие разумные шаги для развития шаблона:

- добавить `services.py` в модули для внешних интеграций
- добавить клавиатуры и callback-handlers
- добавить FSM для пошаговых сценариев
- добавить общий HTTP-клиент для общения с FastAPI
- добавить middleware, если появится общая логика для всех модулей

Этот шаблон уже можно использовать как основу для реального модульного Telegram-бота.
