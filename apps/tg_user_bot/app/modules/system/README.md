# System Module

`app/modules/system` is the mandatory infrastructure module for `telegram_template`.

It provides the base services that every future Telegram module can rely on:

- system-level commands such as `/start`, `/authstatus`, `/usersysinfo`
- a dedicated config layer built from the shared app config
- an `aiohttp` backend client for `fastapi_template`
- in-memory authentication cache
- `login_required` decorator for protected handlers
- runtime auth context for the current update

## Responsibility

This module is not business logic.

It exists to solve transport and platform concerns that should be shared across
all Telegram modules:

- how the bot authenticates a Telegram user against backend
- how auth state is cached inside the bot process
- how modules access the authenticated backend payload
- how operators inspect the current runtime in debug mode

## Backend Contract

The auth flow is tailored to the backend Telegram API in `fastapi_template`.

Expected endpoints:

- `POST /api/telegram/login`
- `POST /api/telegram/users`

The flow is:

1. protected handler enters through `@login_required`
2. decorator checks the in-memory auth cache
3. if no cache entry exists, bot calls `POST /api/telegram/login`
4. if backend returns `404`, bot calls `POST /api/telegram/users`
5. bot retries `POST /api/telegram/login`
6. the successful backend response is cached and exposed to the handler

### Payload Shapes

`POST /api/telegram/users` accepts a nested composite body. The bot sends only
the required `telegram_user` identity; the optional `profile` and `stats`
objects are omitted because the bot has no such data at `/start`. The field
`last_seen_at` is no longer part of the create payload — the backend sets it
server-side.

```json
{
  "telegram_user": {
    "telegram_id": 123,
    "username": "ivan",
    "first_name": "Ivan",
    "last_name": "Petrov",
    "is_blocket_bot": false,
    "language_code": "ru"
  }
}
```

`POST /api/telegram/login` accepts `{ "telegram_id": 123 }` and returns the
Telegram user. In the response, `last_seen_at` is no longer a top-level field —
it now lives inside a nested `user_stats` object (with `source` and `state`),
mirroring the existing `user_profile` object.

## File Map

- `config.py`
  Module-specific settings built from the shared app config.
- `schemas.py`
  Local Pydantic schemas that mirror the backend payload contract.
- `client.py`
  Process-wide `aiohttp` client and backend request helpers.
- `runtime.py`
  Startup and shutdown hooks for system resources.
- `handlers.py`
  Public Telegram commands of the system module.
- `messages.py` and `messages.json`
  Shared user-facing text templates.
- `auth/cache.py`
  In-memory auth session storage.
- `auth/service.py`
  Login and auto-provisioning orchestration.
- `auth/decorators.py`
  `login_required` decorator and auth error handling.

## Commands

- `/start`
  Shows available system commands and backend presence.
- `/authstatus`
  Protected command. Triggers auth flow if needed and prints cached auth state.
- `/usersysinfo`
  Debug-only command. Works only when the app runs with `debug=True`.

## How To Use `login_required`

Example:

```python
from aiogram.filters import Command
from aiogram.types import Message

from app.core.context import get_current_auth_session
from app.modules.system.auth import login_required


@router.message(Command("profile"))
@login_required
async def profile_command(message: Message) -> None:
    auth_session = get_current_auth_session()
    assert auth_session is not None

    await message.answer(
        f"Hello, backend user #{auth_session.telegram_user.id}"
    )
```

## Environment

The module reads its settings from the shared application `.env`.

- `BACKEND_URL`
  Base backend URL, for example `http://localhost:8000/`
- `BACKEND_API_PREFIX`
  API prefix, defaults to `/api`
- `BACKEND_REQUEST_TIMEOUT`
  Total backend request timeout in seconds
- `AUTH_CACHE_MAX_SIZE`
  Maximum number of in-memory auth sessions
- `DEBUG`
  When true, enables `/usersysinfo`

## Operational Notes

- auth cache is in-memory only and is cleared on process restart
- there is currently no TTL or background refresh for cached sessions
- if backend is down, protected handlers return a standard system message
- this module intentionally does not own a database or persistent storage
