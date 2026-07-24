# admin_module

Admin authentication & authorization for the backend.

## Responsibility
- `Admin` model (`username`, `hashed_password`, `is_active`) — login identity for `admin_miniapp`.
- Issues a single access JWT on login (no refresh token).
- Provides the FastAPI gates used across the API to protect sensitive endpoints.

## Layout
- `models/admin.py` — `Admin(Base, TimestampMixin)`. Table `admin`.
- `schemas/auth.py` — `LoginRequest`, `TokenResponse`.
- `schemas/admin.py` — `AdminCreate`, `AdminPatch`, `AdminRead`. Password length is capped at 72 bytes (bcrypt limit).
- `services/auth.py` — `authenticate`, `bootstrap_admin`, `create/list/update/delete_admin`, `get_admin_by_username`.
- `dependencies.py` — auth gates (see below).
- `handlers.py` — `APIRouter(prefix="/auth")`.

## Auth gates (import from `app.modules.admin_module.dependencies`)
- `get_current_admin` / `require_admin` — Bearer JWT, returns the active `Admin`. Validates `is_active` against the DB on every request, so deleting/deactivating an admin revokes access immediately.
- `require_service` — `X-Service-Token` header must equal `settings.service_token`. Fail-closed: if `service_token` is unset, all requests are rejected. Used by the user bot (`tg_user_bot`) for server-to-server calls.
- `require_admin_or_service` — passes if either gate passes. Used by endpoints both the admin panel and the bot call (e.g. `POST /telegram/users`, `GET /files/{id}`).

## Crypto primitives
Live in `app/core/security.py` (core must not depend on modules): `hash_password`, `verify_password` (bcrypt), `create_access_token`, `decode_access_token` (PyJWT, HS256).

## Endpoints (prefix `/api/auth`)

See [API contracts](API.md) for the full per-endpoint request/response JSON.

- `POST /login` — public. Generic 401 on bad creds.
  Login attempts use fixed in-memory windows: per IP+username and per IP. A successful
  login resets both counters; an exhausted window returns 429 with `Retry-After`.
- `GET /me` — current admin (requires JWT).
- `GET /admins` — list (requires JWT).
- `POST /admins` — create (requires JWT). 400 on duplicate username.
- `PATCH /admins/{id}` — change password / `is_active` (requires JWT). Cannot deactivate self.
- `DELETE /admins/{id}` — delete (requires JWT). Cannot delete self (guarantees ≥1 admin remains).

## Bootstrap
`bootstrap_admin()` runs in `app/lifecycle.py` lifespan (after Alembic migrations applied by `docker-entrypoint.sh`). Creates the admin from `settings.admin_username` / `settings.admin_password` only if it does not already exist (idempotent; never overwrites a changed password).

## Settings (`app/core/config.py`, read from `infra/.env`, lowercase)
`admin_username`, `admin_password`, `jwt_secret_key` (required), `jwt_algorithm` (HS256), `jwt_access_token_expire_minutes` (720), `service_token`.

Login rate limiting settings: `admin_login_rate_limit_attempts` (5 per IP+username),
`admin_login_rate_limit_ip_attempts` (20 per IP),
`admin_login_rate_limit_window_seconds` (300), and
`admin_login_trusted_proxy_cidrs` (comma-separated CIDRs). `X-Forwarded-For` is
ignored unless the direct peer belongs to one of these trusted networks. The
limiter is process-local, which matches the current single-worker deployment;
multiple backend replicas require a shared store such as Redis.
