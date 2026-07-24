# Telegram Module

Full HTTP contracts of the module's endpoints. Full path = `/api` (global prefix) + `/telegram` (module router prefix) + route path.

Authorization types:
- `X-Service-Token` — server-to-server calls from `tg_user_bot` (header `X-Service-Token: <token>`).
- Admin Bearer JWT (header `Authorization: Bearer <access_token>`).
- `admin_or_service` — passes either an admin via JWT or the bot via `X-Service-Token`.

There is no rate limit on the module's endpoints.

## Dialog state and login

## PUT /api/telegram/state

> Service update of the dialog state (`user_stats.state`) by `telegram_id`. Used by the bot to move the user through the funnel. Authorization is `X-Service-Token` only. Defensively creates the stats row if it does not exist; returns `404` for an unknown user.

request

```json
// Header: X-Service-Token: <service token>
{
  "telegram_id": 123456789,
  "state": "waiting_phone"
}
```

- `telegram_id` (int, required) — the user's Telegram ID.
- `state` (str | null) — the new funnel state name.

response

```json
{
  "id": 15,
  "telegram_user_id": 15,
  "last_seen_at": "2026-07-24T10:15:30.000000",
  "source": "instagram_bio",
  "state": "waiting_phone",
  "created_at": "2026-07-01T09:00:00.000000",
  "updated_at": "2026-07-24T10:15:30.000000"
}
```

## POST /api/telegram/login

> Login of an existing Telegram user by `telegram_id`. This is a write event: it updates `UserStats.last_seen_at`. Authorization is `X-Service-Token` only. Returns `404` if the user is not found.

request

```json
// Header: X-Service-Token: <service token>
{
  "telegram_id": 123456789
}
```

response

```json
{
  "id": 15,
  "telegram_id": 123456789,
  "username": "ivan",
  "first_name": "Ivan",
  "last_name": "Petrov",
  "is_blocket_bot": false,
  "language_code": "ru",
  "created_at": "2026-07-01T09:00:00.000000",
  "updated_at": "2026-07-24T10:15:30.000000",
  "user_profile": {
    "id": 15,
    "telegram_user_id": 15,
    "phone": "+79998887766",
    "email": null,
    "timezone": null,
    "full_name": "Ivan Petrov",
    "note": null,
    "created_at": "2026-07-01T09:00:00.000000",
    "updated_at": "2026-07-01T09:00:00.000000"
  },
  "user_stats": {
    "id": 15,
    "telegram_user_id": 15,
    "last_seen_at": "2026-07-24T10:15:30.000000",
    "source": "instagram_bio",
    "state": "start",
    "created_at": "2026-07-01T09:00:00.000000",
    "updated_at": "2026-07-24T10:15:30.000000"
  }
}
```

## Telegram users

## POST /api/telegram/users

> Atomic idempotent user registration: creates `TelegramUser` + `UserProfile` + `UserStats` in a single transaction. Authorization is `admin_or_service` (the bot registers users; the admin panel can also create them). Idempotency is by `telegram_id`: `201 Created` if the user was created, `200 OK` if it already existed. The nested `profile` and `stats` are optional — when absent they are created with defaults.

request

```json
{
  "telegram_user": {
    "telegram_id": 123456789,
    "username": "ivan",
    "first_name": "Ivan",
    "last_name": "Petrov",
    "is_blocket_bot": false,
    "language_code": "ru"
  },
  "profile": {
    "phone": "+79998887766",
    "email": null,
    "timezone": null,
    "full_name": "Ivan Petrov",
    "note": null
  },
  "stats": {
    "source": "instagram_bio",
    "state": "start"
  }
}
```

- `telegram_user` (object, required) — Telegram identity: `telegram_id` (int, required), `username`, `first_name`, `last_name`, `language_code` (str | null), `is_blocket_bot` (bool, default `false`).
- `profile` (object | null) — profile data without `telegram_user_id`: `phone`, `email`, `timezone`, `full_name`, `note`.
- `stats` (object | null) — stats without `telegram_user_id` and `last_seen_at`: `source`, `state`.

response

```json
{
  "id": 15,
  "telegram_id": 123456789,
  "username": "ivan",
  "first_name": "Ivan",
  "last_name": "Petrov",
  "is_blocket_bot": false,
  "language_code": "ru",
  "created_at": "2026-07-24T10:15:30.000000",
  "updated_at": "2026-07-24T10:15:30.000000",
  "user_profile": {
    "id": 15,
    "telegram_user_id": 15,
    "phone": "+79998887766",
    "email": null,
    "timezone": null,
    "full_name": "Ivan Petrov",
    "note": null,
    "created_at": "2026-07-24T10:15:30.000000",
    "updated_at": "2026-07-24T10:15:30.000000"
  },
  "user_stats": {
    "id": 15,
    "telegram_user_id": 15,
    "last_seen_at": "2026-07-24T10:15:30.000000",
    "source": "instagram_bio",
    "state": "start",
    "created_at": "2026-07-24T10:15:30.000000",
    "updated_at": "2026-07-24T10:15:30.000000"
  }
}
```

## POST /api/telegram/users/bulk

> Bulk registration: for each item creates `TelegramUser` + `UserProfile` + `UserStats`. Authorization is admin Bearer JWT. NOT idempotent: a duplicate `telegram_id` raises `IntegrityError` (`400`). The whole batch is one transaction and rolls back entirely on failure. Always returns `201`.

request

```json
[
  {
    "telegram_user": { "telegram_id": 111, "username": "a", "language_code": "ru" },
    "profile": { "full_name": "User A" },
    "stats": { "source": "utm_a", "state": "start" }
  },
  {
    "telegram_user": { "telegram_id": 222, "username": "b" }
  }
]
```

Each array item is a `TelegramUserRegister` body (see `POST /api/telegram/users`).

response

```json
[
  {
    "id": 16,
    "telegram_id": 111,
    "username": "a",
    "first_name": null,
    "last_name": null,
    "is_blocket_bot": false,
    "language_code": "ru",
    "created_at": "2026-07-24T10:15:30.000000",
    "updated_at": "2026-07-24T10:15:30.000000",
    "user_profile": { "id": 16, "telegram_user_id": 16, "phone": null, "email": null, "timezone": null, "full_name": "User A", "note": null, "created_at": "2026-07-24T10:15:30.000000", "updated_at": "2026-07-24T10:15:30.000000" },
    "user_stats": { "id": 16, "telegram_user_id": 16, "last_seen_at": "2026-07-24T10:15:30.000000", "source": "utm_a", "state": "start", "created_at": "2026-07-24T10:15:30.000000", "updated_at": "2026-07-24T10:15:30.000000" }
  }
]
```

## GET /api/telegram/users/{id}

> A single user by internal `id` with nested `user_profile` and `user_stats`. Authorization is admin Bearer JWT.

request

```
No request body.
Path parameter:
- id: int — internal id of the TelegramUser.
Authorization: Authorization: Bearer <access_token>.
```

response

```json
{
  "id": 15,
  "telegram_id": 123456789,
  "username": "ivan",
  "first_name": "Ivan",
  "last_name": "Petrov",
  "is_blocket_bot": false,
  "language_code": "ru",
  "created_at": "2026-07-01T09:00:00.000000",
  "updated_at": "2026-07-24T10:15:30.000000",
  "user_profile": { "id": 15, "telegram_user_id": 15, "phone": "+79998887766", "email": null, "timezone": null, "full_name": "Ivan Petrov", "note": null, "created_at": "2026-07-01T09:00:00.000000", "updated_at": "2026-07-01T09:00:00.000000" },
  "user_stats": { "id": 15, "telegram_user_id": 15, "last_seen_at": "2026-07-24T10:15:30.000000", "source": "instagram_bio", "state": "start", "created_at": "2026-07-01T09:00:00.000000", "updated_at": "2026-07-24T10:15:30.000000" }
}
```

## GET /api/telegram/users

> Paginated list of users with search (generic `CRUD.get`). Authorization is admin Bearer JWT. Returns an array of `TelegramUserRead` with nested profile and stats.

request

```
No request body.
Query parameters:
- page: int, >= 1, default 1 — page number.
- limit: int, >= 1, default 10 — page size.
- search: str | null — search string.
- field: str | null — a specific field for exact filtering.
Authorization: Authorization: Bearer <access_token>.
```

response

```json
[
  {
    "id": 15,
    "telegram_id": 123456789,
    "username": "ivan",
    "first_name": "Ivan",
    "last_name": "Petrov",
    "is_blocket_bot": false,
    "language_code": "ru",
    "created_at": "2026-07-01T09:00:00.000000",
    "updated_at": "2026-07-24T10:15:30.000000",
    "user_profile": { "id": 15, "telegram_user_id": 15, "phone": "+79998887766", "email": null, "timezone": null, "full_name": "Ivan Petrov", "note": null, "created_at": "2026-07-01T09:00:00.000000", "updated_at": "2026-07-01T09:00:00.000000" },
    "user_stats": { "id": 15, "telegram_user_id": 15, "last_seen_at": "2026-07-24T10:15:30.000000", "source": "instagram_bio", "state": "start", "created_at": "2026-07-01T09:00:00.000000", "updated_at": "2026-07-24T10:15:30.000000" }
  }
]
```

## PATCH /api/telegram/users/{id}

> Partial update of a user (generic `CRUD.patch`). Authorization is admin Bearer JWT. Only the fields to change are sent.

request

```json
{
  "username": "ivan_new",
  "is_blocket_bot": true,
  "language_code": "en"
}
```

- All fields are optional: `telegram_id` (int), `username`, `first_name`, `last_name`, `language_code` (str | null), `is_blocket_bot` (bool | null).

response

```json
{
  "id": 15,
  "telegram_id": 123456789,
  "username": "ivan_new",
  "first_name": "Ivan",
  "last_name": "Petrov",
  "is_blocket_bot": true,
  "language_code": "en",
  "created_at": "2026-07-01T09:00:00.000000",
  "updated_at": "2026-07-24T10:20:00.000000",
  "user_profile": null,
  "user_stats": null
}
```

## DELETE /api/telegram/users/{id}

> Delete a user by internal `id`. The related `UserProfile` and `UserStats` are deleted by cascade. Authorization is admin Bearer JWT.

request

```
No request body.
Path parameter:
- id: int — internal id of the TelegramUser.
Authorization: Authorization: Bearer <access_token>.
```

response

```json
{ "status": "ok" }
```

## Profiles

## POST /api/telegram/profile

> Create a user profile (generic `CRUD.create`). Authorization is admin Bearer JWT. Returns `201`.

request

```json
{
  "telegram_user_id": 15,
  "phone": "+79998887766",
  "email": "ivan@example.com",
  "timezone": "Europe/Moscow",
  "full_name": "Ivan Petrov",
  "note": "VIP"
}
```

- `telegram_user_id` (int, required) — foreign key to `TelegramUser`.
- `phone`, `email`, `timezone`, `full_name`, `note` (str | null) — optional.

response

```json
{
  "id": 15,
  "telegram_user_id": 15,
  "phone": "+79998887766",
  "email": "ivan@example.com",
  "timezone": "Europe/Moscow",
  "full_name": "Ivan Petrov",
  "note": "VIP",
  "created_at": "2026-07-24T10:15:30.000000",
  "updated_at": "2026-07-24T10:15:30.000000"
}
```

## GET /api/telegram/profile/{id}

> A profile by internal `id`. Authorization is admin Bearer JWT.

request

```
No request body.
Path parameter:
- id: int — internal id of the UserProfile.
Authorization: Authorization: Bearer <access_token>.
```

response

```json
{
  "id": 15,
  "telegram_user_id": 15,
  "phone": "+79998887766",
  "email": "ivan@example.com",
  "timezone": "Europe/Moscow",
  "full_name": "Ivan Petrov",
  "note": "VIP",
  "created_at": "2026-07-24T10:15:30.000000",
  "updated_at": "2026-07-24T10:15:30.000000"
}
```

## GET /api/telegram/profile

> Paginated list of profiles with search (generic `CRUD.get`). Authorization is admin Bearer JWT.

request

```
No request body.
Query parameters:
- page: int, >= 1, default 1.
- limit: int, >= 1, default 10.
- search: str | null — search string.
- field: str | null — a specific field for exact filtering.
Authorization: Authorization: Bearer <access_token>.
```

response

```json
[
  {
    "id": 15,
    "telegram_user_id": 15,
    "phone": "+79998887766",
    "email": "ivan@example.com",
    "timezone": "Europe/Moscow",
    "full_name": "Ivan Petrov",
    "note": "VIP",
    "created_at": "2026-07-24T10:15:30.000000",
    "updated_at": "2026-07-24T10:15:30.000000"
  }
]
```

## PATCH /api/telegram/profile/{id}

> Partial update of a profile (generic `CRUD.patch`). Authorization is admin Bearer JWT.

request

```json
{
  "phone": "+70001112233",
  "note": "moved"
}
```

- All fields are optional: `telegram_user_id` (int), `phone`, `email`, `timezone`, `full_name`, `note` (str | null).

response

```json
{
  "id": 15,
  "telegram_user_id": 15,
  "phone": "+70001112233",
  "email": "ivan@example.com",
  "timezone": "Europe/Moscow",
  "full_name": "Ivan Petrov",
  "note": "moved",
  "created_at": "2026-07-24T10:15:30.000000",
  "updated_at": "2026-07-24T10:20:00.000000"
}
```

## DELETE /api/telegram/profile/{id}

> Delete a profile by internal `id`. Authorization is admin Bearer JWT.

request

```
No request body.
Path parameter:
- id: int — internal id of the UserProfile.
Authorization: Authorization: Bearer <access_token>.
```

response

```json
{ "status": "ok" }
```

## Stats

## POST /api/telegram/stats

> Create a stats row (generic `CRUD.create`). Authorization is admin Bearer JWT. Returns `201`.

request

```json
{
  "telegram_user_id": 15,
  "last_seen_at": "2026-07-24T10:15:30.000000",
  "source": "instagram_bio",
  "state": "start"
}
```

- `telegram_user_id` (int, required) — foreign key to `TelegramUser`.
- `last_seen_at` (datetime | null), `source` (str | null), `state` (str | null) — optional.

response

```json
{
  "id": 15,
  "telegram_user_id": 15,
  "last_seen_at": "2026-07-24T10:15:30.000000",
  "source": "instagram_bio",
  "state": "start",
  "created_at": "2026-07-24T10:15:30.000000",
  "updated_at": "2026-07-24T10:15:30.000000"
}
```

## GET /api/telegram/stats/{id}

> Stats by internal `id`. Authorization is admin Bearer JWT.

request

```
No request body.
Path parameter:
- id: int — internal id of the UserStats.
Authorization: Authorization: Bearer <access_token>.
```

response

```json
{
  "id": 15,
  "telegram_user_id": 15,
  "last_seen_at": "2026-07-24T10:15:30.000000",
  "source": "instagram_bio",
  "state": "start",
  "created_at": "2026-07-24T10:15:30.000000",
  "updated_at": "2026-07-24T10:15:30.000000"
}
```

## GET /api/telegram/stats

> Paginated list of stats with search (generic `CRUD.get`). Authorization is admin Bearer JWT.

request

```
No request body.
Query parameters:
- page: int, >= 1, default 1.
- limit: int, >= 1, default 10.
- search: str | null — search string.
- field: str | null — a specific field for exact filtering.
Authorization: Authorization: Bearer <access_token>.
```

response

```json
[
  {
    "id": 15,
    "telegram_user_id": 15,
    "last_seen_at": "2026-07-24T10:15:30.000000",
    "source": "instagram_bio",
    "state": "start",
    "created_at": "2026-07-24T10:15:30.000000",
    "updated_at": "2026-07-24T10:15:30.000000"
  }
]
```

## PATCH /api/telegram/stats/{id}

> Partial update of stats, for example changing `state` (generic `CRUD.patch`). Authorization is admin Bearer JWT.

request

```json
{
  "state": "finished",
  "source": "referral"
}
```

- All fields are optional: `telegram_user_id` (int), `last_seen_at` (datetime | null), `source` (str | null), `state` (str | null).

response

```json
{
  "id": 15,
  "telegram_user_id": 15,
  "last_seen_at": "2026-07-24T10:15:30.000000",
  "source": "referral",
  "state": "finished",
  "created_at": "2026-07-24T10:15:30.000000",
  "updated_at": "2026-07-24T10:20:00.000000"
}
```

## DELETE /api/telegram/stats/{id}

> Delete a stats row by internal `id`. Authorization is admin Bearer JWT.

request

```
No request body.
Path parameter:
- id: int — internal id of the UserStats.
Authorization: Authorization: Bearer <access_token>.
```

response

```json
{ "status": "ok" }
```

## Newsletters

## POST /api/telegram/newsletter

> Launch a one-off newsletter to a filtered audience. Authorization is admin Bearer JWT. The body is `multipart/form-data`: a `payload` field (JSON of the `NewsletterRequest` string) and an optional `file` (attachment). The service counts the recipients under the filter (0 → `404`), splits the audience into chunks of `newsletter_chunk_size`, and publishes `telegram.newsletter` events via the transactional outbox. The response contains a shared `broadcast_id` for tracing.

request

```
Content-Type: multipart/form-data
Authorization: Authorization: Bearer <access_token>.

Form fields:
- payload (str, required) — JSON of the NewsletterRequest body:
  {
    "filters": { "search": "ivan", "field": "username" },
    "text": "Newsletter text",
    "use_buttons": "INLINE",
    "buttons": [
      { "text": "Open website", "url": "https://example.com" },
      { "text": "Button", "callback_data": "cb_open" }
    ]
  }
- file (UploadFile, optional) — attachment (size is checked against newsletter_upload_max_size_bytes).

payload fields:
- filters (object) — { search: str|null, field: str|null }, same semantics as GET /telegram/users.
- text (str | null) — newsletter text (required if there is no file).
- use_buttons ("INLINE" | "REPLY" | null) — keyboard type.
- buttons (list | null) — [{ text, url?, callback_data? }]; for INLINE each button has exactly one of url / callback_data.
```

response

```json
{
  "status": "queued",
  "recipients": 1240,
  "broadcast_id": "3f1c2b8e-9a4d-4c7e-9b2a-0f1e2d3c4b5a"
}
```

## Drip newsletters

## POST /api/telegram/drip-newsletters

> Create a drip newsletter rule: "the user entered `trigger_state` → after `days_offset` days at `send_time` send a message". Authorization is admin Bearer JWT. The body is `multipart/form-data`: `payload` (JSON of `DripNewsletterCreate`) + an optional `file`. Button validation is the same as for a regular newsletter. Returns `201`.

request

```
Content-Type: multipart/form-data
Authorization: Authorization: Bearer <access_token>.

Form fields:
- payload (str, required) — JSON of the DripNewsletterCreate body:
  {
    "title": "Warm-up after 3 days",
    "trigger_state": "start",
    "days_offset": 3,
    "send_time": "10:00",
    "text": "Message text",
    "use_buttons": "INLINE",
    "buttons": [ { "text": "Open", "url": "https://example.com" } ]
  }
- file (UploadFile, optional) — attachment.

payload fields:
- title (str | null, <= 255) — rule name.
- trigger_state (str, required, 1..255) — trigger state.
- days_offset (int, required, 0..365) — delay in days.
- send_time (str, required) — send time "HH:MM" (or "HH:MM:SS") in drip_timezone.
- text (str | null) — message text (required if there is no file).
- use_buttons ("INLINE" | "REPLY" | null), buttons (list | null) — same as newsletter.
```

response

```json
{
  "id": 7,
  "title": "Догрев через 3 дня",
  "trigger_state": "start",
  "days_offset": 3,
  "send_time": "10:00:00",
  "text": "Текст сообщения",
  "use_buttons": "INLINE",
  "buttons": [ { "text": "Открыть", "url": "https://example.com", "callback_data": null } ],
  "file_id": null,
  "is_active": true,
  "sent_count": 0,
  "created_at": "2026-07-24T10:15:30.000000",
  "updated_at": "2026-07-24T10:15:30.000000"
}
```

## GET /api/telegram/drip-newsletters

> Paginated list of drip newsletter rules with the number of sends already performed (`sent_count`). Authorization is admin Bearer JWT.

request

```
No request body.
Query parameters:
- page: int, >= 1, default 1.
- limit: int, >= 1, default 10.
Authorization: Authorization: Bearer <access_token>.
```

response

```json
[
  {
    "id": 7,
    "title": "Догрев через 3 дня",
    "trigger_state": "start",
    "days_offset": 3,
    "send_time": "10:00:00",
    "text": "Текст сообщения",
    "use_buttons": "INLINE",
    "buttons": [ { "text": "Открыть", "url": "https://example.com", "callback_data": null } ],
    "file_id": null,
    "is_active": true,
    "sent_count": 42,
    "created_at": "2026-07-24T10:15:30.000000",
    "updated_at": "2026-07-24T10:15:30.000000"
  }
]
```

## PATCH /api/telegram/drip-newsletters/{id}

> Edit a rule: only `title` and `is_active` (on/off). Content is immutable in v1 — the rule is recreated instead. Authorization is admin Bearer JWT.

request

```json
{
  "title": "Новое название",
  "is_active": false
}
```

- Both fields are optional: `title` (str | null, <= 255), `is_active` (bool | null).

response

```json
{
  "id": 7,
  "title": "Новое название",
  "trigger_state": "start",
  "days_offset": 3,
  "send_time": "10:00:00",
  "text": "Текст сообщения",
  "use_buttons": "INLINE",
  "buttons": [ { "text": "Открыть", "url": "https://example.com", "callback_data": null } ],
  "file_id": null,
  "is_active": false,
  "sent_count": 42,
  "created_at": "2026-07-24T10:15:30.000000",
  "updated_at": "2026-07-24T10:20:00.000000"
}
```

## DELETE /api/telegram/drip-newsletters/{id}

> Delete a drip newsletter rule. The send log (`DripNewsletterSend`) and the `File` record are deleted by cascade; the S3 object itself is removed best-effort in a background task after commit. Authorization is admin Bearer JWT.

request

```
No request body.
Path parameter:
- id: int — internal id of the DripNewsletter.
Authorization: Authorization: Bearer <access_token>.
```

response

```json
{ "status": "ok" }
```
