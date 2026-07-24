# Leadorub — Claude Code Project Context

## Product

Leadorub is a Telegram lead-management platform designed for influencers. The project consists of a FastAPI backend, an Aiogram user bot, a Vue-based admin SPA, a client-facing Telegram Mini App, and Docker-based infrastructure.

Current product capabilities:

* Telegram user registration and attribution;
* consultation request creation through the bot and Client Mini App;
* admin-to-user support chat with attachment support;
* filtered newsletter broadcasts with files and keyboards;
* admin authentication and user/request management;
* PostgreSQL, RabbitMQ, Redis, MinIO, Caddy, Loki, Alloy, and Grafana.

## Repository Structure

* `apps/backend` — FastAPI, SQLAlchemy, Alembic, RabbitMQ transactional outbox, and MinIO.
* `apps/tg_user_bot` — Aiogram user bot using long polling and a RabbitMQ notification consumer.
* `apps/admin_miniapp` — authenticated Vue/Pinia admin SPA.
* `apps/client_miniapp` — Telegram WebApp containing the consultation request form.
* `infra` — Compose files, edge Caddy proxy, monitoring, and the shared `.env` file.

Runtime configuration for the entire Docker Compose stack is loaded from `infra/.env`, which is based on `infra/.env.example`.

## Security Invariants

* The Client Mini App must send the raw Telegram `initData` string in the `X-Telegram-Init-Data` header. The backend validates its HMAC signature, `auth_date`, and TTL, then derives the `telegram_id` from the signed data. Never trust `initDataUnsafe` as a source of user identity.
* Never expose `X-Service-Token` through a public reverse proxy. It is intended only for controlled server-to-server requests.
* The Admin API uses Bearer JWT authentication. Login attempts are rate-limited separately by IP address and by the IP + username combination.
* Public request creation is rate-limited separately by IP address and by the IP + Telegram user combination.
* Before uploading files to S3, every upload path must call the shared actual-file-size validator.
* Newsletter events and admin chat reply events use the transactional outbox. New RabbitMQ flows that depend on database state must follow the same pattern. Publishing directly from an uncommitted transaction creates a race condition between the database commit and message publication.
* Newsletter delivery uses two-phase Redis idempotency: `processing` → `sent`. Retryable failures must release the claim and requeue the RabbitMQ message.
* In production, only the edge Caddy proxy is exposed publicly: TCP ports 80/443 and UDP port 443. Diagnostic service ports must bind to `127.0.0.1`. Grafana, MinIO Console, and RabbitMQ UI are additionally protected by Basic Auth at the edge layer.

## Development Commands

Use `uv`; never use `pip`:

```bash
cd apps/backend && uv sync --dev && uv run ruff check . && uv run pytest -q
cd apps/tg_user_bot && uv sync --dev && uv run ruff check . && uv run pytest -q
cd apps/admin_miniapp && npm ci && npm test && npm run build
cd apps/client_miniapp && npm ci && npm run build
```

Run the Compose stack from the `infra/` directory so that Docker Compose loads `infra/.env`:

```bash
docker compose -f docker-compose.infra.yml up -d
docker compose -f docker-compose.apps.yml up -d --build
```

Apply migrations with `uv run alembic upgrade head`. The backend container also applies migrations through its entrypoint.

## Claude Code Documentation Routing

* Before editing a service or module, read `AGENTS.md` if it exists alongside `CLAUDE.md`.
* Agent-facing documentation files (`CLAUDE.md`, `AGENTS.md`) must be written in English.
* User-facing `README.md` files must be written in Russian.
* When behavior, APIs, configuration, lifecycle, or deployment changes, update the nearest relevant context files as part of the same task: `AGENTS.md`, `CLAUDE.md`, `API.md`, and files under `obsidian/`.

## Engineering Rules

* Preserve the modular architecture: handlers perform validation and delegation, services contain business logic, and models and schemas remain within their respective modules.
* Register new ORM models in `app/modules/__init__.py` and add an Alembic migration.
* Use application settings and `.env.example`; never hardcode secrets.
* Keep changes scoped to the current task and make atomic commits. Preserve unrelated uncommitted changes in the working tree.
* Add tests for behavior changes and run the relevant quality checks before committing.
* Use type annotations and structured logging. Comments should explain non-obvious reasoning, not the history of an edit.
* Before committing, run `uv run ruff check . --fix`.

