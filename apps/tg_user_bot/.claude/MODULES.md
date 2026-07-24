# Module Guide For The Telegram User Bot

This document defines the canonical way to create new modules for the Telegram
user bot.

The goal is straightforward: every new module should fit the existing
architecture without hidden magic, should not bypass the `system` layer, and
should keep transport concerns separate from module-specific logic.

> [!IMPORTANT]
> If a module is structured as a standalone service (with its own `Dockerfile`),
> you MUST include a `.dockerignore` that excludes `.venv/`, `.git/`, local
> `.env` files, and `__pycache__/`. This keeps the host virtual environment out
> of the build context and avoids Python interpreter conflicts.

## Core Rules

- Every module lives in `app/modules/<module_name>/`.
- Every module documents itself with an English `CLAUDE.md` (agent guidance) and
  an English `API.md` (interface contracts). No `AGENTS.md`, no per-module
  `README.md`.
- A module that handles Telegram updates exposes its own `router` and is
  registered explicitly in `app/bot/registry.py`. A product funnel invoked by
  another module's handler (like `persona`/`business`, driven by system `/start`)
  has no router and registers nothing.
- Shared authentication and backend user context come from the `system` module.
- A module should not read `.env` directly if the shared app config is enough.
- If a module needs backend access, first check whether `app/modules/system`
  already covers the need.

## Required Structure

Minimum for a module with a router:

```text
app/modules/<module_name>/
├── __init__.py
├── CLAUDE.md
├── API.md
└── handlers.py
```

Common extended structure:

```text
app/modules/<module_name>/
├── __init__.py
├── CLAUDE.md
├── API.md
├── handlers.py
├── services/            # or services.py — external calls, orchestration
├── messages.json
├── states.py
└── keyboards.py
```

A routerless funnel module replaces `handlers.py` with a `service.py` entry point
(see `persona`/`business`).

## Documentation Files

### `CLAUDE.md` (English, required)

Explains the module to an agent who needs to change it safely: boundaries,
architecture expectations, extension rules, module-specific constraints, and the
preferred way to modify it without breaking its contract. Link the contracts with
`[interface contracts](API.md)`.

### `API.md` (English, required)

The module's interface contracts. The bot serves no HTTP, so `API.md` documents,
as applicable:

- Telegram commands, callbacks, and `/start` deep links the module exposes;
- RabbitMQ contracts it consumes or publishes (queue, exchange, routing key,
  event, payload shape);
- backend endpoints it consumes (method, path, `X-Service-Token`, request/response).

A module with no external contract (a pure funnel) still gets a short `API.md`
describing its trigger, outbound Telegram surface, and any backend call.

## Code Responsibilities

- `handlers.py` — Telegram handlers (commands, messages, callbacks). Start it with
  a meaningful top-level docstring: why the module exists, which scenarios it
  handles, and what does / does not belong in the file. Delegate real work to
  services; do not turn it into a large procedural script.
- `services/` (or `services.py`) — external API integration and multi-step
  orchestration. Add it once handlers stop being trivial.
- `messages.json` — reusable user-facing text; do not hardcode larger blocks in
  handlers.
- `states.py` — only if the module uses FSM.
- `keyboards.py` — only if the module exposes inline/reply keyboards.
- `config.py` — only if the module needs its own settings; follow the `system`
  pattern (project a subset of the shared config, do not add a second `.env`
  reader).

## Router

A module that handles updates must export `router`:

```python
"""
Telegram handlers for the profile module.

Serves user-facing profile commands and relies on the shared system auth session.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="profile")


@router.message(Command("profile"))
async def profile_command(message: Message) -> None:
    await message.answer("Profile module is active.")
```

## Registration

Register the module explicitly in `app/bot/registry.py`. If it is not registered
there, it does not exist for the runtime. Keep `system` first so `/start` (which
resets FSM) keeps priority over the support catch-all.

```python
from aiogram import Dispatcher

from app.modules.profile.handlers import router as profile_router
from app.modules.system.handlers import router as system_router


def register_routers(dispatcher: Dispatcher) -> None:
    dispatcher.include_router(system_router)
    dispatcher.include_router(profile_router)
```

## Authentication

If a module needs backend user context, use the system layer — never re-implement
an auth flow:

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
    await message.answer(f"Backend user id: {auth_session.telegram_user.id}")
```

Use `@login_required(no_cache=True)` when a fresh backend check is required, and
`get_current_auth_session()` to read the session.

## Startup Delivery Semantics

Startup calls `bot.delete_webhook(drop_pending_updates=settings.drop_pending_updates)`.
With `drop_pending_updates=False`, handlers may receive updates queued before a
restart, so write them to be safe under repeated or delayed delivery.

## What A Module Must Not Do

- import backend runtime code directly;
- create its own auth storage when the shared system layer is enough;
- turn `handlers.py` into a large procedural script;
- read `.env` directly without a real reason;
- auto-register routers through filesystem scanning.

## Checklist

1. Create `app/modules/<module_name>/`.
2. Create `CLAUDE.md` and `API.md` (English) and link them.
3. Add a top-level docstring to the entry file (`handlers.py` or `service.py`).
4. Create `router = Router(name="<module_name>")` if the module handles updates.
5. Add `services/` once handlers are non-trivial; add `messages.json`,
   `states.py`, `keyboards.py` as needed.
6. Register the router in `app/bot/registry.py` (routerless funnels are invoked
   by their owning handler instead).
7. Use the shared `system` auth rather than inventing a separate flow.
8. Run `uv run ruff check .` and `uv run pytest -q`.
