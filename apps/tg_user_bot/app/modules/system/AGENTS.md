# System Module Agent Context

## Purpose

`app/modules/system` is the mandatory platform layer for `telegram_template`.
Every other Telegram module may depend on it for auth, backend access and runtime
introspection.

## What Belongs Here

- auth orchestration against the backend Telegram API
- process-level in-memory auth cache
- shared system commands
- module-specific config derived from the shared app config
- transport code for backend API calls
- current-update auth context helpers

## What Does Not Belong Here

- product or domain business logic
- module-specific user journeys unrelated to platform/auth
- persistent storage owned by the bot
- direct imports from `fastapi_template` runtime code

## Design Rules

- Keep backend integration isolated in `client.py`.
- Keep deep-link payload parsing isolated in `deep_link.py`.
- Keep auth orchestration in `auth/service.py`.
- Keep handler protection in `auth/decorators.py`.
- Keep user-facing strings in `messages.json`.
- Keep process-wide state explicit and small.
- Preserve top-of-file docstrings when editing files.
- Prefer extending local `schemas.py` instead of importing backend schemas.

## Auth Contract

Protected handlers should use `@login_required`.

The expected flow is:

1. check in-memory cache by `telegram_id`
2. call `POST /api/telegram/login`
3. if backend returns `404`, call `POST /api/telegram/users`
4. call `POST /api/telegram/login` again
5. cache the successful backend payload
6. expose the auth session through `app.core.context`

### Request/Response Shapes

`POST /api/telegram/users` expects a nested composite body. Only the
`telegram_user` identity is required. `profile` is always omitted. `stats` is
sent only when `/start` carried a `source_*` deep-link (first-touch marketing
attribution); otherwise it is omitted. `last_seen_at` is NOT sent — the backend
sets it server-side.

```json
{
  "telegram_user": {
    "telegram_id": 123,
    "username": "ivan",
    "first_name": "Ivan",
    "last_name": "Petrov",
    "is_blocket_bot": false,
    "language_code": "ru"
  },
  "stats": {
    "source": "instagram"
  }
}
```

### Source Deep-Links

`deep_link.parse_source()` extracts the marketing source from the `/start`
payload via the `source_<value>` prefix scheme (`source_instagram` →
`"instagram"`). The value is threaded through
`ensure_authenticated(..., source=...)` →
`_provision_backend_user(..., source)` → `_build_create_payload(..., source)`
and only affects the provisioning branch. Attribution is first-touch: returning
users keep their original source because backend registration is idempotent.

`POST /api/telegram/login` (`{ "telegram_id": 123 }`) returns `TelegramUserRead`.
`last_seen_at` is NO LONGER top-level; it now lives inside the nested
`user_stats` object (alongside `source` and `state`), mirroring `user_profile`.

## Safe Extension Points

- add more backend methods to `client.py`
- add more auth helpers to `auth/service.py`
- add more system commands to `handlers.py`
- add cache invalidation or refresh helpers to `auth/cache.py`

## Caution

- `BACKEND_URL` may be absent in local development; handlers must fail clearly
- the cache is intentionally in-memory only, so restarts clear all sessions
- `/usersysinfo` must stay debug-only unless explicitly redesigned
