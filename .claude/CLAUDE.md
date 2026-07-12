# Leadorub — Claude Code Project Context

## Product

Leadorub is a Telegram lead-management platform for influencers. It consists of a
FastAPI backend, an Aiogram user bot, an admin Vue SPA, a client Telegram Mini App,
and Docker-based infrastructure.

Current product capabilities:

- Telegram user registration and attribution;
- consultation requisitions from the bot and Client Mini App;
- admin/user support chat with attachments;
- filtered newsletter broadcasts with files and keyboards;
- admin authentication and user/requisition management;
- PostgreSQL, RabbitMQ, Redis, MinIO, Caddy, Loki, Alloy, and Grafana.

## Repository layout

- `apps/backend` — FastAPI, SQLAlchemy, Alembic, RabbitMQ outbox, MinIO.
- `apps/tg_user_bot` — Aiogram long-polling bot and RMQ notification consumer.
- `apps/admin_miniapp` — authenticated Vue/Pinia admin SPA.
- `apps/client_miniapp` — Telegram WebApp consultation form.
- `infra` — Compose files, edge Caddy, monitoring, and shared `.env`.
- `.github/workflows/quality.yml` — Python and frontend quality gates.

Runtime configuration for the composed stack comes from `infra/.env`, based on
`infra/.env.example`.

## Security invariants

- The Client Mini App must send raw Telegram `initData` in
  `X-Telegram-Init-Data`. The backend validates its HMAC, `auth_date`, and TTL and
  derives `telegram_id` from signed data. Never trust `initDataUnsafe` as identity.
- Never expose `X-Service-Token` through a public reverse proxy. It is only for
  controlled server-to-server calls.
- Admin API uses Bearer JWT. Login is rate-limited by IP and IP+username.
- Public requisitions are rate-limited by IP and IP+Telegram user.
- All upload paths must call the shared actual-size validator before S3 upload.
- Newsletter and admin chat reply events use the transactional outbox. New
  DB-dependent RabbitMQ flows must follow that pattern; direct publishing from an
  uncommitted transaction introduces a commit/publish race.
- Newsletter delivery uses two-phase Redis idempotency (`processing` -> `sent`).
  Retryable failures must release the claim and requeue the RMQ message.
- Production exposure is edge Caddy only: TCP 80/443 and UDP 443. Diagnostic
  service ports bind to `127.0.0.1`; Grafana, MinIO Console, and RabbitMQ UI have
  an additional edge Basic Auth barrier.

## Development commands

Use `uv`, never `pip`:

```bash
cd apps/backend && uv sync --dev && uv run ruff check . && uv run pytest -q
cd apps/tg_user_bot && uv sync --dev && uv run ruff check . && uv run pytest -q
cd apps/admin_miniapp && npm ci && npm test && npm run build
cd apps/client_miniapp && npm ci && npm run build
```

Run the composed stack from `infra/` so Compose reads `infra/.env`:

```bash
docker compose -f docker-compose.infra.yml up -d
docker compose -f docker-compose.apps.yml up -d --build
```

Before the first start, generate `EDGE_ADMIN_PASSWORD_HASH` as documented in
`infra/README.md`. Apply migrations with `uv run alembic upgrade head`; the backend
container also applies them from its entrypoint.

## Claude Code documentation routing

- Read the nearest `AGENTS.md` and `.claude/CLAUDE.md` before editing a service or
  module. More local instructions override this file.
- Agent-facing documents (`CLAUDE.md`, `AGENTS.md`) are written in English.
- User-facing `README.md` files are written in Russian.
- When behavior, API, configuration, lifecycle, or deployment changes, update both
  the nearest agent-facing context and its Russian README in the same task.
- Do not duplicate detailed module contracts at the repository level. Keep them in
  the module's `AGENTS.md`/`CLAUDE.md` and `README.md`, then link to them.

## Engineering rules

- Preserve the modular architecture: handlers validate/delegate, services contain
  business logic, models/schemas stay in their module.
- Register new ORM models in `app/modules/__init__.py` and add an Alembic migration.
- Use settings and `.env.example`; never hardcode secrets.
- Keep changes scoped and commits atomic. Preserve unrelated dirty worktree changes.
- Add tests for behavior changes and run the relevant quality commands before commit.
- Use type annotations and structured logging. Comments explain non-obvious reasons,
  not the history of an edit.

@include .claude/skills/*/SKILL.md
@include apps/*/.claude/CLAUDE.md
