# Requisition Module

Full HTTP contracts for the requisition module endpoints. The full path = `/api` (global prefix) + `/requisitions` (module router prefix) + the route path.

## POST /api/requisitions

> Create a new requisition on behalf of a Telegram user (called by the product bot `tg_user_bot`). Authorization is server-to-server only, via the `X-Service-Token` header. No rate limit. The user is looked up by `telegram_id`; if not found — `404`. The requisition is created with status `pending`, and a `requisition.created` event is published to the `admin_requisitions` queue. Returns `201`.

request

```json
// Header: X-Service-Token: <service token>
{
  "telegram_id": 987654321,
  "type": "consultation",
  "payload": {
    "name": "Иван",
    "phone": "+79998887766"
  }
}
```

- `telegram_id` (int, required) — the user's Telegram ID.
- `type` (str, required, 1..50) — product/requisition type (`consultation`, `community`, etc.).
- `payload` (object, optional, defaults to `{}`) — arbitrary requisition field data.

response

```json
{
  "id": 42,
  "telegram_user_id": 15,
  "type": "consultation",
  "status": "pending",
  "payload": {
    "name": "Иван",
    "phone": "+79998887766"
  },
  "admin_comment": null,
  "created_at": "2026-07-09T10:08:03Z",
  "updated_at": "2026-07-09T10:08:03Z",
  "telegram_user": {
    "id": 15,
    "telegram_id": 987654321,
    "username": "ivan_dev",
    "first_name": "Иван",
    "last_name": null,
    "is_blocket_bot": false,
    "language_code": "ru",
    "created_at": "2026-07-01T09:00:00Z",
    "updated_at": "2026-07-01T09:00:00Z",
    "user_profile": null,
    "user_stats": null
  }
}
```

## POST /api/requisitions/public

> Create a requisition from the Client Mini App. Authorization is via the signed Telegram WebApp `initData` string in the `X-Telegram-Init-Data` header: the backend verifies the HMAC signature, `auth_date`, and TTL, then extracts `telegram_id` from the signed `user.id` field. `X-Service-Token` is not accepted as a browser credential; the `telegram_id` passed in the body is ignored (the field is forbidden by the schema). Rate limit: a sliding window applied separately per IP and per IP+Telegram ID pair; on exceeding it — `429` with a `Retry-After` header. If WebApp authentication is not configured — `503`. Invalid/expired `initData` — `401`. On success, `requisition.created` is published to `admin_requisitions` and an instant notification to `telegram_notifications`. Returns `201`.

request

```json
// Header: X-Telegram-Init-Data: <raw Telegram WebApp initData string>
{
  "type": "consultation",
  "name": "Иван",
  "phone": "+79998887766",
  "description": "Нужна консультация по продукту"
}
```

- `type` (str, optional, defaults to `"consultation"`) — requisition type.
- `name` (str, required) — client's name.
- `phone` (str, required) — client's phone number.
- `description` (str | null, optional) — problem description.

The server builds a `payload` of the form `{ "name", "phone", "description", "source": "miniapp" }` and fills in `telegram_id` from the signed `initData`.

response

```json
{
  "id": 43,
  "telegram_user_id": 15,
  "type": "consultation",
  "status": "pending",
  "payload": {
    "name": "Иван",
    "phone": "+79998887766",
    "description": "Нужна консультация по продукту",
    "source": "miniapp"
  },
  "admin_comment": null,
  "created_at": "2026-07-09T10:12:00Z",
  "updated_at": "2026-07-09T10:12:00Z",
  "telegram_user": {
    "id": 15,
    "telegram_id": 987654321,
    "username": "ivan_dev",
    "first_name": "Иван",
    "last_name": null,
    "is_blocket_bot": false,
    "language_code": "ru",
    "created_at": "2026-07-01T09:00:00Z",
    "updated_at": "2026-07-01T09:00:00Z",
    "user_profile": null,
    "user_stats": null
  }
}
```

## GET /api/requisitions

> Paginated list of requisitions with filters. Authorization: `require_admin` (admin Bearer JWT). Sorted by `created_at` DESC (newest first). No rate limit.

request

No body. Query parameters:

- `status` (str, optional) — filter by requisition status (`pending`, `in_progress`, `approved`, `rejected`).
- `type` (str, optional) — filter by product type.
- `page` (int, optional, `>= 1`, defaults to `1`) — page number.
- `limit` (int, optional, `>= 1`, defaults to `10`) — page size.
- `search` (str, optional) — full-text search across text columns.

Header: `Authorization: Bearer <admin JWT>`.

response

```json
[
  {
    "id": 43,
    "telegram_user_id": 15,
    "type": "consultation",
    "status": "pending",
    "payload": {
      "name": "Иван",
      "phone": "+79998887766"
    },
    "admin_comment": null,
    "created_at": "2026-07-09T10:12:00Z",
    "updated_at": "2026-07-09T10:12:00Z",
    "telegram_user": {
      "id": 15,
      "telegram_id": 987654321,
      "username": "ivan_dev",
      "first_name": "Иван",
      "last_name": null,
      "is_blocket_bot": false,
      "language_code": "ru",
      "created_at": "2026-07-01T09:00:00Z",
      "updated_at": "2026-07-01T09:00:00Z",
      "user_profile": null,
      "user_stats": null
    }
  }
]
```

## GET /api/requisitions/{id}

> Detailed information about a specific requisition. Authorization: `require_admin` (admin Bearer JWT). If the requisition is not found — `404`. No rate limit.

request

No body. Path parameter:

- `id` (int, required) — requisition identifier.

Header: `Authorization: Bearer <admin JWT>`.

response

```json
{
  "id": 43,
  "telegram_user_id": 15,
  "type": "consultation",
  "status": "pending",
  "payload": {
    "name": "Иван",
    "phone": "+79998887766"
  },
  "admin_comment": null,
  "created_at": "2026-07-09T10:12:00Z",
  "updated_at": "2026-07-09T10:12:00Z",
  "telegram_user": {
    "id": 15,
    "telegram_id": 987654321,
    "username": "ivan_dev",
    "first_name": "Иван",
    "last_name": null,
    "is_blocket_bot": false,
    "language_code": "ru",
    "created_at": "2026-07-01T09:00:00Z",
    "updated_at": "2026-07-01T09:00:00Z",
    "user_profile": null,
    "user_stats": null
  }
}
```

## PATCH /api/requisitions/{id}/status

> Update a requisition's status and the administrator's comment (approval, rejection, etc.). Authorization: `require_admin` (admin Bearer JWT). If the requisition is not found — `404`. After saving, a `telegram.notification` user notification is published to the `telegram_notifications` queue. No rate limit.

request

```json
// Header: Authorization: Bearer <admin JWT>
// Path parameter: id (int) — requisition identifier
{
  "status": "approved",
  "admin_comment": "Добро пожаловать в наше комьюнити!"
}
```

- `status` (str, required, 1..30) — new status (`pending`, `in_progress`, `approved`, `rejected`).
- `admin_comment` (str | null, optional, up to 1024) — administrator's comment.

response

```json
{
  "id": 43,
  "telegram_user_id": 15,
  "type": "consultation",
  "status": "approved",
  "payload": {
    "name": "Иван",
    "phone": "+79998887766"
  },
  "admin_comment": "Добро пожаловать в наше комьюнити!",
  "created_at": "2026-07-09T10:12:00Z",
  "updated_at": "2026-07-09T11:00:00Z",
  "telegram_user": {
    "id": 15,
    "telegram_id": 987654321,
    "username": "ivan_dev",
    "first_name": "Иван",
    "last_name": null,
    "is_blocket_bot": false,
    "language_code": "ru",
    "created_at": "2026-07-01T09:00:00Z",
    "updated_at": "2026-07-01T09:00:00Z",
    "user_profile": null,
    "user_stats": null
  }
}
```
