# Telegram Template Agent Context

## Purpose

This repository is a minimally working Telegram bot template built on `aiogram` in `polling-only` mode.
It is intentionally small and is meant to be extended by adding modules under `app/modules`.

The bot itself does **not** own a database.
It acts as a Telegram transport layer that can be extended with additional modules.

## Architecture

- `main.py`
  Entrypoint. Configures logging and starts polling.
- `app/core/config.py`
  Loads settings from `.env`.
- `app/core/logging.py`
  Configures process-wide logging.
- `app/bot/app.py`
  Assembles the runtime objects: `Bot`, `Dispatcher`, lifecycle hooks.
- `app/bot/dispatcher.py`
  Creates the dispatcher and attaches routers.
- `app/bot/registry.py`
  Explicit router registry. New modules are connected here manually.
- `app/bot/lifecycle.py`
  Startup and shutdown hooks for polling mode.
- `app/modules/*`
  Modular bot features. Each module should expose its own `router`.

## Current Behavior

At the moment the template includes one module:

- `app/modules/system/handlers.py`
  Provides `/start`, `/authstatus`, and `/usersysinfo`.

This module is also the mandatory infrastructure layer for future modules:

- it owns the backend auth client
- it keeps the in-memory auth cache
- it exposes `login_required`
- it publishes auth session data through runtime context

The bot also includes `app/modules/notification_module` — an RMQ consumer (built on
`rmq_module`) that delivers backend-originated messages to users: single notifications
and broadcasts. A broadcast arrives as ONE message with a `chat_ids` list (the bot
iterates recipients itself), supports an optional attachment (`file_id` resolved via
backend `GET /api/files/{id}`; image → photo, else document) and `use_buttons:
INLINE|REPLY` with a flat button list. See `app/modules/notification_module/AGENTS.md`.

The bot also includes `app/modules/support_module` — support mode (FSM). `/support`
enters `SupportStates.active`; every text message is published to the `telegram_support_in`
queue (`rmq_publisher`) and gets a 👀 reaction strictly AFTER a successful publish.
`/stop`, an inline button, or `/start` exit the mode. Admin replies arrive back through
the existing `notification_module` (no extra code). Handler order matters — see
`app/modules/support_module/AGENTS.md`.

## Design Rules

- Keep `main.py` thin.
- Keep bot assembly inside `app/bot/app.py`.
- Keep module registration explicit in `app/bot/registry.py`.
- Keep modules isolated inside `app/modules/<module_name>`.
- Do not add database code to the bot project.
- If a module needs data, keep that integration outside the bot storage layer.
- Preserve and extend existing DocStrings instead of removing them.
- Extend the system module instead of bypassing it for shared auth logic.
- Every module must include both `README.md` and `AGENTS.md`.

Module creation guide:

- See [MODULETEMPLATE.md](/home/misha/code/module_service/telegram_template/MODULETEMPLATE.md)
  for the canonical module structure, required files, auth usage, and
  registration flow.
- If a new module is structured as an independent service with its own `Dockerfile`, it **must** have a `.dockerignore` file in its root to exclude `.venv/`, `.git/`, local `.env` files, and `__pycache__/`.

## How To Add A Module

1. Create a folder under `app/modules/<module_name>/`.
2. Add `handlers.py`.
3. Define `router = Router(name="<module_name>")`.
4. Add command/message/callback handlers to that router.
5. Import that router in `app/bot/registry.py`.
6. Register it with `dispatcher.include_router(...)`.

Optional module files may include:

- `services.py` for external integrations
- `states.py` for FSM states
- `keyboards.py` or `buttons.py` for Telegram UI helpers
- `messages.json` for text templates

If a module needs backend user auth, prefer:

1. `@login_required`
2. `get_current_auth_session()`

## Environment

Expected `.env` values:

- `TOKEN` required
- `BACKEND_URL` optional but required for protected handlers
- `BACKEND_API_PREFIX` optional, defaults to `/api`
- `BACKEND_REQUEST_TIMEOUT` optional
- `AUTH_CACHE_MAX_SIZE` optional
- `BOT_PARSE_MODE` optional, defaults to `HTML`
- `DEBUG` optional, enables debug-only commands

## Validation

Useful local checks:

- `python main.py`
- `python -m compileall app main.py`

## Notes For Future Agents

- The repository may contain placeholder directories or empty files from early scaffolding.
  Prefer improving the current modular pattern rather than introducing a new architecture.
- If you add a new module, explain both the code and the runtime flow in simple language.
- When documenting changes, describe the bot as a minimally working template with explicit module registration.
