# Telegram User Bot — Agent Context

## Purpose

Aiogram 3 long-polling bot for Leadorub. It is the Telegram transport/UI layer;
persistent business data belongs to the FastAPI backend.

## Active modules

- `system` — backend authentication client, bounded in-memory auth cache,
  `login_required`, runtime update context, and system commands.
- `tocka_zborki` — product funnel, training PDF, and Client MiniApp launch.
- `requisition_module` — bot-side requisition flows.
- `support_module` — support FSM; text goes through RMQ and media through the
  authenticated backend HTTP endpoint.
- `notification_module` — consumes `telegram_notifications`, downloads optional
  backend files, and delivers text/media/keyboards.
- `rmq_module` — shared publisher, consumer registry, retry/requeue lifecycle.

Routers are registered explicitly in `app/bot/registry.py`. Preserve ordering:
`system` must precede support catch-all handlers so `/start` can leave support mode.

## Delivery semantics

Newsletter payloads are chunked by backend. For each recipient, the notification
module uses a Redis-owned two-phase claim:

1. acquire `processing` with a unique owner token;
2. send to Telegram;
3. atomically transition to `sent` on success or permanent 403;
4. release on retryable failure and requeue the RMQ delivery.

Do not replace this with a one-step claim-before-send marker: it loses messages on
temporary Telegram/network failures. If Redis is unavailable, delivery degrades to
at-least-once without deduplication.

## Integration rules

- Never add a database or ORM to this service.
- Backend calls use the shared `aiohttp` client and `X-Service-Token`; never expose
  that token to browser code.
- Notification file downloads also require `X-Service-Token` because backend
  `GET /api/files/{id}` is gated by `require_admin_or_service`.
- Keep binary media out of RabbitMQ. Support uploads media to backend over HTTP.
- External resources start/stop in `app/bot/lifecycle.py`, not handlers.
- Module-specific behavior belongs in the nearest module `AGENTS.md` and Russian
  `README.md`.

## Adding a module

Follow `MODULETEMPLATE.md`: create an isolated directory with `handlers.py`, expose
an Aiogram `Router`, add English `AGENTS.md`, Russian `README.md`, and register the
router explicitly in `app/bot/registry.py`.

## Environment

Key settings:

- `TOKEN` — required Telegram bot token;
- `BACKEND_URL`, `BACKEND_API_PREFIX`, `BACKEND_REQUEST_TIMEOUT`;
- `SERVICE_TOKEN` — shared server-to-server backend secret;
- `CLIENT_MINIAPP_URL`, `TRAINING_GUIDE_PATH`;
- `AMQP_URL` and RabbitMQ runtime settings;
- `redis_password`, host/port/db, and
  `newsletter_idempotency_ttl_seconds` for delivery deduplication;
- `DEBUG`, `BOT_PARSE_MODE`, `drop_pending_updates`.

## Quality commands

Use `uv`, never `pip`:

```bash
uv sync --dev
uv run ruff check .
uv run pytest -q
uv run python main.py
```

Preserve unrelated dirty worktree changes and keep commits scoped.
