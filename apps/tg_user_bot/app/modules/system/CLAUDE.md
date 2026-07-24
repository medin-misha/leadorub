# System Module Guide For AI Agents

## Purpose

`app/modules/system` is the mandatory platform layer for the Telegram user bot.
Every other Telegram module may depend on it for auth, backend access and runtime
introspection.

This module is infrastructure, not business logic. It solves transport and
platform concerns that are shared across all Telegram modules: how the bot
authenticates a Telegram user against the backend, how auth state is cached in
the process, how modules read the authenticated backend payload, and how
operators inspect the runtime in debug mode.

## What Belongs Here

- auth orchestration against the backend Telegram API
- process-level in-memory auth cache
- shared system commands (`/start`, `/authstatus`, `/usersysinfo`)
- `/start` deep-link routing (funnel selection and marketing-source parsing)
- module-specific config derived from the shared app config
- transport code for backend API calls
- current-update auth context helpers

## What Does Not Belong Here

- product or domain business logic (funnel content lives in `persona`/`business`)
- module-specific user journeys unrelated to platform/auth
- persistent storage owned by the bot
- direct imports from backend runtime code

## Design Rules

- Keep backend integration isolated in `client.py`.
- Keep deep-link payload parsing isolated in `deep_link.py`.
- Keep auth orchestration in `auth/service.py`.
- Keep handler protection in `auth/decorators.py`.
- Keep user-facing strings in `messages.json`.
- Keep process-wide state explicit and small.
- Preserve top-of-file docstrings when editing files.
- Prefer extending local `schemas.py` instead of importing backend schemas.

## Module Map

- `config.py` — `SystemModuleSettings`, a projection of `app.core.settings` (it
  does not read `.env` itself). Exposes `backend_api_base_url`.
- `client.py` — process-wide `aiohttp` client and `BackendClient` request
  helpers. The `X-Service-Token` header is set once as a default session header
  in `startup_backend_client()`; it is not attached per request.
- `deep_link.py` — `parse_source()` only. Extracts the marketing source from the
  `/start` payload via the `source_<value>` scheme.
- `schemas.py` — local Pydantic schemas mirroring the backend payload contract.
- `runtime.py` — startup/shutdown hooks for system resources.
- `handlers.py` — the three public system commands and `/start` routing.
- `messages.py` / `messages.json` — cached user-facing text templates.
- `auth/cache.py` — bounded in-memory LRU auth cache (`auth_cache` singleton).
- `auth/service.py` — login and auto-provisioning orchestration.
- `auth/decorators.py` — `login_required` decorator and auth error mapping.

## `/start` Routing

`start_command` runs on every `/start`:

1. `state.clear()` — resets FSM (also exits support mode).
2. `parse_source(command.args)` → best-effort provisioning; backend errors are
   logged and swallowed so the greeting still sends.
3. Presentation branch by deep-link payload:
   - payload `business` (`BUSINESS_START_PAYLOAD`) → `persona`/`business`: the
     `business` funnel;
   - anything else (empty, `source_*`, arbitrary) → the `persona` funnel.

Marketing-source attribution and funnel selection are independent: `source_*`
never selects a funnel — it only feeds provisioning and always lands in
`persona`.

## Auth Contract

Protected handlers should use `@login_required` (add `no_cache=True` when a fresh
backend check is required). The flow:

1. check the in-memory cache by `telegram_id`;
2. `POST /telegram/login`;
3. on backend `404`, `POST /telegram/users`;
4. `POST /telegram/login` again;
5. cache the successful backend payload;
6. expose the auth session through `app.core.context`.

Attribution is first-touch: because backend registration is idempotent
(`get_or_create` by `telegram_id`), a returning user with a new `source_*` link
keeps the original source. Exact request/response shapes live in
[interface contracts](API.md).

## Safe Extension Points

- add backend methods to `client.py`;
- add auth helpers to `auth/service.py`;
- add system commands to `handlers.py`;
- add cache invalidation or refresh helpers to `auth/cache.py`.

## Caution

- `BACKEND_URL` may be absent in local development; handlers must fail clearly.
- the cache is in-memory only, so restarts clear all sessions; there is no TTL or
  background refresh.
- `/usersysinfo` must stay debug-only (`DEBUG=true`) unless explicitly redesigned.
- if you change exported primitives, update `__init__.py`.
- if a change adds settings, update `app/core/config.py` and `.env` documentation.
