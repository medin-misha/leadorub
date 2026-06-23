# Notification Module (Telegram Client)

`notification_module` — клиентский модуль-потребитель для приёма и физической доставки уведомлений в Telegram из RabbitMQ в приложении `telegram_template`.

Этот модуль слушает очередь RabbitMQ и отправляет сообщения в Telegram с помощью `aiogram.Bot`.

## Принцип работы

1. Модуль подписывается на очередь `telegram_notifications` в обменнике `app.events` с ключом маршрутизации `telegram_notifications`.
2. При поступлении сообщения запускается callback-функция `handle_telegram_notification`.
3. Содержимое сообщения валидируется на соответствие контракту с помощью Pydantic-модели `TelegramNotification`.
4. Собирается соответствующая клавиатура (inline или reply) с учётом параметров кнопок.
5. Если указан `file_id` — файл скачивается из бэкенда один раз (`GET /api/files/{id}` с заголовком `X-Service-Token`, см. ниже); при первой отправке используются байты, для остальных получателей переиспользуется Telegram file_id из ответа.
6. Рассылка перебирает всех получателей из `chat_ids`; ошибка на одном получателе не прерывает рассылку.

## Контракт сообщения

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

## Авторизация на бэкенде

Эндпоинт `GET /api/files/{id}` защищён на backend гейтом `require_admin_or_service`.
Резолвер вложений (`services/backend_files.py`) шлёт статический заголовок
`X-Service-Token` (значение из `SERVICE_TOKEN`, общий секрет с backend `service_token`).
Без токена backend ответит `401` и рассылка с вложением не уйдёт.

## Подключение в приложении

Модуль подключается автоматически при регистрации его роутера в реестре `app/bot/registry.py`:

```python
from app.modules.notification_module.handlers import router as notification_router

def register_routers(dispatcher: Dispatcher) -> None:
    # ...
    dispatcher.include_router(notification_router)
```

Импорт роутера активирует импорт обработчика очередей, который регистрирует консьюмер в RMQ-клиенте на этапе инициализации приложения.
