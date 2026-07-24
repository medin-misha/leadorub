# System Module — Interface Contracts

The bot serves no HTTP. This module's surface is: Telegram commands, the `/start`
deep-link scheme, and the backend endpoints its auth flow consumes. The shared
`BackendClient` (`client.py`) is owned here; endpoints consumed by other modules
are documented in those modules (`persona`/`business` → `PUT /telegram/state`,
`requisition_module` → `POST /requisitions`).

## Telegram Commands

- `/start [payload]` — resets FSM, best-effort provisions the user, then runs a
  funnel (see Deep Links). Backend errors here are swallowed so the greeting
  still sends; the full auth flow runs later on the first protected handler.
- `/authstatus` — protected (`@login_required(no_cache=True)`). Forces the auth
  flow and prints the cached auth state.
- `/usersysinfo` — debug-only. Returns a disabled notice unless `DEBUG=true`.

## Deep Links

`t.me/<bot>?start=<payload>` arrives as `/start <payload>`. Telegram restricts
`payload` to `A-Za-z0-9_-`, max 64 chars.

- `?start=business` → the `business` funnel.
- `?start=source_<value>` → marketing source (`source_instagram` → `"instagram"`,
  truncated to 255 chars), captured first-touch during provisioning; the funnel
  is still `persona`.
- any other payload / empty → the `persona` funnel, no source.

Generate links with `aiogram.utils.deep_linking.create_start_link(bot,
payload="source_instagram")`.

## Backend Endpoints Consumed

Base URL is `BACKEND_URL` + `BACKEND_API_PREFIX` (default `/api`). Every call
carries the `X-Service-Token` header (default session header). Both auth
endpoints are gated on the backend by `require_service` / `require_admin_or_service`;
without a valid token the backend answers `401`.

### POST /telegram/login

Look up a Telegram user. `404` triggers provisioning (see below).

request

```json
{ "telegram_id": 123 }
```

response — `TelegramUserRead`. `last_seen_at` is NOT top-level; it lives inside
the nested `user_stats` object (with `source` and `state`), mirroring
`user_profile`.

### POST /telegram/users

Provision a user. The body is a nested composite; only `telegram_user` is
required. `profile` is always omitted. `stats` is sent only when `/start` carried
a `source_*` deep link. `last_seen_at` is never sent — the backend sets it. Sent
with `exclude_none`.

request

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

response — `TelegramUserRead` (same shape as login).

## Client Error Mapping

`BackendClient` normalizes failures: `>= 500` → `BackendUnavailableError`;
`>= 400` → `BackendUnexpectedResponseError`; a `404` on login →
`BackendUserNotFoundError`; invalid/non-object JSON → `BackendUnexpectedResponseError`.
