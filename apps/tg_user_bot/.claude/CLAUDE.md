# Telegram User Bot — контекст для агента

## Назначение

Бот Leadorub на Aiogram 3, работающий через long polling. Он выполняет роль транспортного и пользовательского слоя Telegram; постоянные бизнес-данные должны храниться в FastAPI-бэкенде.

## Build-in модули

* `system` — клиент аутентификации бэкенда, ограниченный in-memory кэш авторизации, `login_required`, runtime-контекст обновлений и системные команды.
* `rmq_module` — общий publisher, реестр consumers и lifecycle повторных попыток и повторной постановки сообщений в очередь.
* `requisition_module` — сценарии создания заявок на стороне бота.
* `support_module` — FSM поддержки; текст передаётся через RabbitMQ, а медиа — через аутентифицированный HTTP endpoint бэкенда.
* `notification_module` — получает сообщения из очереди `telegram_notifications`, при необходимости скачивает файлы из бэкенда и отправляет текст, медиа и клавиатуры.

Routers регистрируются явно в `app/bot/registry.py`. Сохраняй порядок регистрации: `system` должен находиться перед catch-all handlers модуля поддержки, чтобы команда `/start` могла вывести пользователя из режима поддержки.

## Бизнес модули

* `persona` — воронка DMCAGuardian для команды `/start`: PDF-гайд, видео, кнопки для связи и состояние `persona_start` в бэкенде. Не имеет собственного router.
* `business` — воронка агентства DMCAGuardian, доступная по deep link `/start business`: PDF-гайд с подписью, видео, кнопки для связи и состояние `business_start` в бэкенде. Собственного router нет; маршрутизация `/start` находится в модуле `system`.

## Правила интеграции

* Никогда не добавляй базу данных или ORM в этот сервис.
* Запросы к бэкенду должны использовать общий клиент `aiohttp` и заголовок `X-Service-Token`. Никогда не передавай этот токен в браузерный код.
* Для скачивания файлов модулем уведомлений также требуется `X-Service-Token`, поскольку backend endpoint `GET /api/files/{id}` защищён зависимостью `require_admin_or_service`.
* Не передавай бинарные медиафайлы через RabbitMQ. Модуль поддержки загружает медиа в бэкенд через HTTP.
* Внешние ресурсы должны запускаться и останавливаться в `app/bot/lifecycle.py`, а не в handlers.
* Поведение конкретного модуля должно быть описано в ближайшем модульном `CLAUDE.md`.

## Добавление модуля

Следуй инструкциям из `MODULES.md`.

## Переменные окружения

Основные настройки:

* `TOKEN` — обязательный токен Telegram-бота;
* `BACKEND_URL`, `BACKEND_API_PREFIX`, `BACKEND_REQUEST_TIMEOUT`;
* `SERVICE_TOKEN` — общий server-to-server секрет для взаимодействия с бэкендом;
* `CLIENT_MINIAPP_URL`, `ADMIN_CONTACT_URL`;
* `PERSONA_GUIDE_PATH`, `PERSONA_VIDEO_PATH` — файлы воронки persona;
* `BUSINESS_GUIDE_PATH`, `BUSINESS_VIDEO_PATH` — файлы воронки business; по умолчанию используются файлы persona;
* `AMQP_URL` и runtime-настройки RabbitMQ;
* `redis_password`, host, port, db и `newsletter_idempotency_ttl_seconds` для дедупликации доставки;
* `DEBUG`, `BOT_PARSE_MODE`, `drop_pending_updates`.

## Команды проверки качества

Используй `uv`, никогда не используй `pip`:

```bash
uv sync --dev
uv run ruff check .
uv run pytest -q
uv run python main.py
```

