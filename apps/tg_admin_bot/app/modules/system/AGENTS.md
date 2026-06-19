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

### Backend Payload Contract

- `POST /api/telegram/users` takes a NESTED composite body: a required
  `telegram_user` block plus optional `profile`/`stats`. The bot sends only
  `telegram_user` (via `TelegramUserIdentityCreate`) and lets backend create an
  empty profile and default stats. `last_seen_at` is NOT sent on create.
- `TelegramUserRead` has no top-level `last_seen_at`. It is nested under
  `user_stats` (mirrors the `user_profile` nesting). Read schemas keep
  `extra="ignore"`.

## Safe Extension Points

- add more backend methods to `client.py`
- add more auth helpers to `auth/service.py`
- add more system commands to `handlers.py`
- add cache invalidation or refresh helpers to `auth/cache.py`

## Caution

- `BACKEND_URL` may be absent in local development; handlers must fail clearly
- the cache is intentionally in-memory only, so restarts clear all sessions
- `/usersysinfo` must stay debug-only unless explicitly redesigned
