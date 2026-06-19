# Telegram System Module Design

## Goal

Turn `app/modules/system` into the mandatory infrastructure module for
`telegram_template`.

## Scope

- dedicated system config derived from shared app config
- `aiohttp` backend client for Telegram auth endpoints
- in-memory auth cache
- auth service with `login -> create -> login` flow
- `login_required` decorator
- runtime auth context
- system commands `/start`, `/authstatus`, `/usersysinfo`
- module-local `README.md` and `AGENTS.md`

## Runtime Flow

1. bot startup initializes the backend HTTP client and clears auth cache
2. a protected handler enters through `@login_required`
3. decorator checks the in-memory cache by `telegram_id`
4. if missing, bot calls `POST /api/telegram/login`
5. if backend returns `404`, bot registers the user through
   `POST /api/telegram/users`
6. bot retries login and caches the successful backend payload
7. auth session is exposed through `app.core.context`
8. bot shutdown closes the backend HTTP client and clears auth cache

## Non-Goals

- persistent auth storage
- cache TTL or background refresh
- business-specific user flows
- direct code coupling to `fastapi_template`
