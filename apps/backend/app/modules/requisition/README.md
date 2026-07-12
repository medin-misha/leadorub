# Модуль заявок (Requisition Module)

Модуль отвечает за создание, хранение и обработку заявок пользователей в системе Leadorub. Заявки могут быть кастомными (на консультацию, вступление в закрытое сообщество, покупку продуктов и т.д.).

## Структура файлов

```text
app/modules/requisition/
├── models/
│   ├── __init__.py
│   └── requisition.py       # ORM модель Requisition
├── schemas/
│   ├── __init__.py
│   └── requisition.py       # Pydantic схемы (DTO)
├── services/
│   └── requisition_service.py # Бизнес-логика и RabbitMQ публикации
├── handlers.py              # APIRouter и REST эндпоинты
├── .claude/
│   └── CLAUDE.md            # Инструкции для ИИ-агентов (English)
└── README.md                # Данный файл документации (Russian)
```

## Функционал

1. **Создание заявки от пользователя:**
   * Эндпоинт `POST /api/requisitions` вызывается продукт-ботом (`tg_user_bot`) с использованием сервисного токена (`X-Service-Token`).
   * Client MiniApp отправляет заявку через `POST /api/requisitions/public`. Его Caddy проксирует с сервисным токеном только этот точный маршрут и только для метода `POST`; остальные `/api/*` на домене MiniApp возвращают `404`.
   * Это временная узкая граница доверия: до внедрения серверной проверки Telegram `initData` переданный клиентом `telegram_id` нельзя считать подтверждённой личностью пользователя.
   * Заявка сохраняется в БД со статусом `pending`.
   * Кастомные поля опросников хранятся в виде JSON в поле `payload`.
   * Событие о новой заявке публикуется в RabbitMQ (очередь `admin_requisitions`) для последующей обработки в `admin_bot`.

2. **Администрирование заявок:**
   * Список заявок с фильтрацией по статусу/типу и пагинацией доступен по адресу `GET /api/requisitions` (`require_admin`).
   * Детали заявки доступны по адресу `GET /api/requisitions/{id}` (`require_admin`).
   * Обновление статуса (одобрение/отклонение) и добавление комментария админа доступно по адресу `PATCH /api/requisitions/{id}/status` (`require_admin`).
   * При обновлении статуса бэкенд отправляет уведомление пользователю в продукт-бот через RabbitMQ (очередь `telegram_notifications`).

## Спецификация событий RabbitMQ

### 1. Новая заявка (Очередь: `admin_requisitions`)
* **Событие (event):** `requisition.created`
* **Полезная нагрузка (payload):**
  ```json
  {
    "requisition_id": 1,
    "telegram_id": 987654321,
    "username": "ivan_dev",
    "type": "consultation",
    "payload": {
      "name": "Иван",
      "phone": "+79998887766"
    },
    "created_at": "2026-07-09T10:08:03.000000Z"
  }
  ```

### 2. Уведомление об изменении статуса (Очередь: `telegram_notifications`)
* **Событие (event):** `telegram.notification`
* **Полезная нагрузка (payload):**
  ```json
  {
    "chat_ids": [987654321],
    "message": "Статус вашей заявки 'Вступление в сообщество' изменился на: одобрена.\n\nКомментарий администратора:\nДобро пожаловать в наше комьюнити!",
    "use_buttons": null,
    "buttons": null,
    "file_id": null
  }
  ```
