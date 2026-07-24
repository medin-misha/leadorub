# Chat Module

All module endpoints live under the global prefix `/api` and the router prefix `/chat`.
Authorization:

- `require_admin` — admin Bearer JWT.
- `require_service` — `X-Service-Token` header (server-to-server, bot only).

## GET /api/chat/conversations

> List of support conversations: one per user, with the unread count and a preview of the last message. Requires admin Bearer JWT (`require_admin`).

request

No request body. Query parameters:

- `page` (int, `>= 1`, default `1`) — page number.
- `limit` (int, `1..100`, default `20`) — page size.
- `search` (string, optional) — filter by user (name/username).

```
GET /api/chat/conversations?page=1&limit=20&search=ivan
```

response

```json
[
  {
    "telegram_user_id": 42,
    "telegram_id": 123456789,
    "username": "ivan",
    "first_name": "Иван",
    "last_name": "Петров",
    "last_text": "Спасибо за помощь!",
    "last_at": "2026-07-24T10:15:00Z",
    "last_direction": "user",
    "unread_count": 3
  }
]
```

## GET /api/chat/conversations/{telegram_user_id}/messages

> Thread of a single conversation. Without `after_id` — the last N messages in chronological order; with `after_id` — only messages with `id > after_id` (incremental polling of new ones). Requires admin Bearer JWT (`require_admin`).

request

No request body. Path parameter:

- `telegram_user_id` (int) — internal user id (`TelegramUser.id`).

Query parameters:

- `after_id` (int, `>= 0`, optional) — return only messages newer than the given id.
- `limit` (int, `1..200`, default `50`) — maximum number of messages.

```
GET /api/chat/conversations/42/messages?after_id=100&limit=50
```

response

```json
[
  {
    "id": 101,
    "telegram_user_id": 42,
    "direction": "user",
    "text": "Здравствуйте!",
    "tg_message_id": 5567,
    "file_id": null,
    "file_name": null,
    "is_read": false,
    "created_at": "2026-07-24T10:14:00Z"
  },
  {
    "id": 102,
    "telegram_user_id": 42,
    "direction": "admin",
    "text": "Добрый день, чем помочь?",
    "tg_message_id": null,
    "file_id": 7,
    "file_name": "screenshot.png",
    "is_read": true,
    "created_at": "2026-07-24T10:15:00Z"
  }
]
```

## POST /api/chat/conversations/{telegram_user_id}/reply

> Admin reply to a user. Saves a `direction='admin'` row, uploads the attachment to S3 if present, and enqueues a notification in the outbox for delivery by the bot. You must provide text OR a file (or both). Requires admin Bearer JWT (`require_admin`).

request

`multipart/form-data` (not JSON). Path parameter:

- `telegram_user_id` (int) — internal user id.

Form fields:

- `text` (string, optional) — reply text. No more than `MESSAGE_MAX_LENGTH` characters (Telegram caption limit), otherwise `400`.
- `file` (file, optional) — attachment. The size is checked by a validator (`chat_upload_max_size_bytes`).

If neither `text` nor `file` is provided — `400 Bad Request`.

```
Content-Type: multipart/form-data

text=Добрый день, чем помочь?
file=<binary>
```

response

```json
{
  "id": 102,
  "telegram_user_id": 42,
  "direction": "admin",
  "text": "Добрый день, чем помочь?",
  "tg_message_id": null,
  "file_id": 7,
  "file_name": "screenshot.png",
  "is_read": true,
  "created_at": "2026-07-24T10:15:00Z"
}
```

## POST /api/chat/conversations/{telegram_user_id}/read

> Marks all of the user's messages in the conversation as read and returns the number of updated rows. Requires admin Bearer JWT (`require_admin`).

request

No request body. Path parameter:

- `telegram_user_id` (int) — internal user id.

```
POST /api/chat/conversations/42/read
```

response

```json
{
  "status": "ok",
  "updated": 3
}
```

## POST /api/chat/inbound-media

> Receiving media from a user: the bot downloaded the file from Telegram and forwards it here. The file is uploaded to S3, and a `direction='user'` row is created with `file_id`. The binary goes over HTTP, not through RMQ. Server-to-server, requires the `X-Service-Token` header (`require_service`).

request

`multipart/form-data` (not JSON). Form fields:

- `file` (file, required) — the attachment itself. The size is checked by a validator (`chat_upload_max_size_bytes`).
- `telegram_id` (int, required) — Telegram id of the sending user.
- `tg_message_id` (int, optional) — message id in Telegram.
- `caption` (string, optional) — caption for the media.

If no user with the given `telegram_id` is found — `404 Not Found`.

```
Content-Type: multipart/form-data

file=<binary>
telegram_id=123456789
tg_message_id=5568
caption=Вот скриншот ошибки
```

response

```json
{
  "id": 103,
  "telegram_user_id": 42,
  "direction": "user",
  "text": "Вот скриншот ошибки",
  "tg_message_id": 5568,
  "file_id": 8,
  "file_name": "error.png",
  "is_read": false,
  "created_at": "2026-07-24T10:16:00Z"
}
```
