# Module Template For `telegram_template`

This document defines the canonical way to create new modules for
`telegram_template`.

The goal is straightforward: every new module should fit into the existing
architecture without hidden magic, should not bypass the system layer, and
should keep transport concerns separate from module-specific logic.

> [!IMPORTANT]
> If the new module is structured as a standalone service (with its own `Dockerfile`), you **must** include a `.dockerignore` file in its root directory to exclude `.venv/`, `.git/`, local `.env` files, and `__pycache__/`. This prevents polluting the Docker build context with the host's virtual environment and avoids Python interpreter conflicts.

## Core Rules

- Every module lives in `app/modules/<module_name>/`.
- Every module must expose its own `router`.
- Every module must include `README.md`.
- Every module must include `AGENTS.md`.
- Module registration is always explicit in `app/bot/registry.py`.
- Shared authentication and backend user context must come from the `system`
  module.
- A module should not read `.env` directly if the shared app config is enough.
- If a module needs backend access, first check whether the existing
  `app/modules/system` mechanisms already cover the need.

## Required Structure

Every module must include at least this structure:

```text
app/modules/<module_name>/
├── __init__.py
├── AGENTS.md
├── README.md
└── handlers.py
```

Common extended structure:

```text
app/modules/<module_name>/
├── __init__.py
├── AGENTS.md
├── README.md
├── handlers.py
├── services.py
├── messages.json
├── states.py
└── keyboards.py
```

Not every optional file is required, but `README.md` and `AGENTS.md` are always
required.

## File Responsibilities

### `handlers.py`

Contains Telegram handlers:

- commands
- message handlers
- callback handlers

Heavy business logic should not live here. A handler should accept the update,
delegate work to services, and produce the Telegram response.

The file must start with a meaningful top-level `docstring` that explains:

- why the module exists
- which scenarios it handles
- what belongs in this file
- what does not belong in this file

### `services.py`

Contains module-level application logic:

- external API integration
- orchestration of multiple steps
- adaptation of backend data for Telegram UI

If the module is tiny, a separate `services.py` may be unnecessary. Once
handlers start growing, move logic here.

### `messages.json`

Stores module text templates:

- response texts
- error texts
- help texts

Do not keep larger reusable text blocks hardcoded inside handlers.

### `states.py`

Needed only if the module uses FSM.

### `keyboards.py`

Needed only if the module exposes inline or reply keyboards.

### `README.md`

Required for every module.

It should explain:

- the module purpose
- commands and user-facing flows
- dependencies
- runtime behavior
- any important limitations

The point of `README.md` is to explain the module to a human developer who is
new to the codebase.

### `AGENTS.md`

Required for every module.

It should explain:

- the module boundaries
- architecture expectations
- extension rules
- module-specific constraints
- the preferred way to modify the module safely

The point of `AGENTS.md` is to explain the module to an agent or developer who
needs to change it without breaking its contract.

## Required `router`

Each module must export `router`.

Example:

```python
"""
Telegram handlers for the profile module.

This module serves user-facing commands related to viewing and editing the
profile and relies on the shared system auth session.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="profile")


@router.message(Command("profile"))
async def profile_command(message: Message) -> None:
    await message.answer("Profile module is active.")
```

## Module Registration

After creating a module, register it explicitly in `app/bot/registry.py`.

Example:

```python
from aiogram import Dispatcher

from app.modules.profile.handlers import router as profile_router
from app.modules.system.handlers import router as system_router


def register_routers(dispatcher: Dispatcher) -> None:
    dispatcher.include_router(system_router)
    dispatcher.include_router(profile_router)
```

If a module is not registered in `registry.py`, it does not exist for runtime.

## Authentication Usage

If a module needs backend user context, use the system layer:

- `@login_required`
- `@login_required(no_cache=True)` when a fresh backend check is required
- `get_current_auth_session()`

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
        f"Backend user id: {auth_session.telegram_user.id}"
    )
```

If a module starts re-implementing authentication through its own backend flow,
that is almost certainly an architectural mistake.

## Startup Delivery Semantics

The application startup currently calls:

```python
await bot.delete_webhook(
    drop_pending_updates=settings.drop_pending_updates
)
```

This matters for module design:

- with `drop_pending_updates=True`, old Telegram updates are discarded on startup
- with `drop_pending_updates=False`, modules may receive updates that were queued
  before the restart

Module handlers should therefore be written to be safe under repeated delivery
or delayed delivery when a project decides to disable dropping pending updates.

## What A Module Must Not Do

- It must not import runtime code directly from `fastapi_template`.
- It must not create its own separate auth storage if the shared system layer is
  enough.
- It must not turn `handlers.py` into a large procedural script.
- It must not read `.env` directly without a real reason.
- It must not auto-register routers through filesystem scanning.

## When To Add `config.py`

If a module needs its own settings, create a local `config.py`.

Follow the same pattern as the `system` module:

- do not create a second direct `.env` reader if the shared app config is enough
- define only the fields the module actually needs
- keep the module contract local and explicit

## Recommended Flow For Adding A Module

1. Create `app/modules/<module_name>/`.
2. Create `README.md` and `AGENTS.md`.
3. Add a top-level `docstring` to `handlers.py`.
4. Create `router = Router(name="<module_name>")`.
5. Add `services.py` if handlers are not trivial.
6. Add `messages.json` if the module has more than one or two reusable texts.
7. Register the module in `app/bot/registry.py`.
8. If auth is needed, use the shared `system` module rather than inventing a
   separate auth flow.
9. Run at least `python -m compileall app main.py`.

## Quick Checklist

- `router = Router(name="<module_name>")` exists
- `README.md` exists
- `AGENTS.md` exists
- `handlers.py` has a top-level `docstring`
- the module is registered in `app/bot/registry.py`
- shared auth logic is not duplicated
- business logic is not smeared across handlers
