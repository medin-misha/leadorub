# Telegram Module Guide For AI Agents

## Purpose

`app.modules.telegram_module` is the reusable Telegram integration module for the FastAPI application.

Use it as the canonical place for Telegram bot user identity, profile data, and behavioral stats.
This module exists to:

- store Telegram-facing user identity in `TelegramUser`
- store collected profile data in `UserProfile`
- store behavioral stats (last seen, acquisition source, dialog state) in `UserStats`
- provide reusable create/login flows for Telegram users
- expose HTTP endpoints for authentication-adjacent Telegram user lifecycle operations

This module depends on `app.modules.system` and should reuse its shared persistence primitives instead of re-implementing them locally.

## Dependency On `system`

`telegram_module` is a feature module built on top of `system`.

Current dependencies:

- `Base` and `TimestampMixin` for ORM models
- `CRUD` for generic create/read/update/delete behavior
- `DBErrorHandler` for normalized database error handling

Preferred imports:

```python
from app.modules.system import Base, TimestampMixin, CRUD
from app.modules.system.services.errors import DBErrorHandler
```

Do not duplicate generic CRUD logic, timestamp mixins, or DB exception normalization inside this module unless the Telegram workflow truly requires behavior that `system` cannot provide.

## What This Module Owns

This module owns three related entities:

- `TelegramUser`
  The Telegram bot user identity record.
- `UserProfile`
  The editable profile record linked to one Telegram user.
- `UserStats`
  The behavioral stats record linked to one Telegram user.

Think of the boundary like this:

- `TelegramUser` stores Telegram-originated identity fields such as `telegram_id`, `username`, and `language_code`
- `UserProfile` stores application-level collected data such as `phone`, `email`, `timezone`, `full_name`, and `note`
- `UserStats` stores values that change over the user's life in the bot: `last_seen_at`, `source`, and `state`

Routing rule for new fields:

- coming directly from Telegram identity → `TelegramUser`
- collected/enriched/maintained by the product → `UserProfile`
- behavioral / changing over time (activity, acquisition, FSM state) → `UserStats`

## Preferred Imports

If another module only needs the exported ORM models, prefer:

```python
from app.modules.telegram_module import TelegramUser, UserProfile, UserStats
```

Internal module structure should still use local imports when that keeps files simpler.

## Module Map

### `models/`

Contains the ORM models for Telegram user storage.

Important files:

- `models/telegram_user.py`
- `models/user_profile.py`
- `models/user_stats.py`
- `models/drip.py` — `DripNewsletter` (drip rule) and `DripNewsletterSend` (per-user send log)

Agent expectations:

- `TelegramUser` is the source of truth for Telegram identity.
- `UserProfile` is a one-to-one extension of `TelegramUser`.
- `UserStats` is a one-to-one extension of `TelegramUser`.
- All models inherit shared primitives from `system`.
- Relationship changes must preserve the intended one-user-one-profile / one-user-one-stats behavior.

### `schemas/`

Contains request/response DTOs for the Telegram API layer.

Important files:

- `schemas/telegram_user.py`
- `schemas/user_profile.py`
- `schemas/user_stats.py`

Agent expectations:

- `TelegramUserRegister` is the composite input DTO for registration. It nests `telegram_user` (required) plus optional `profile` and `stats`.
- `TelegramUserCreate`, `UserProfileCreate`, `UserStatsCreate` are flat input DTOs for single-entity creation flows.
- `UserProfileRegister` and `UserStatsRegister` are the nested register DTOs. They intentionally omit `telegram_user_id` (derived from the created `TelegramUser`); `UserStatsRegister` also omits `last_seen_at` (set server-side at registration).
- `TelegramUserPatch`, `UserProfilePatch`, `UserStatsPatch` are partial update DTOs.
- `TelegramUserRead` includes nested `user_profile` and `user_stats`.
- Schema changes should stay aligned with model fields and handler response contracts.

### `services/`

Contains feature-specific business logic that wraps shared `CRUD`.

Important file:

- `services/user_service.py`

Current service responsibilities:

- atomic registration of a Telegram user together with its `UserProfile` and `UserStats`
- idempotent creation by `telegram_id`
- bulk registration (also creates profile + stats per user)
- login flow that updates `UserStats.last_seen_at`

Agent expectations:

- Keep orchestration logic here when a workflow spans more than one model.
- Reuse `CRUD` for generic persistence and keep Telegram-specific coordination in this layer.
- Rely on single-transaction atomicity (see below) for multi-step creation flows.

### `handlers.py`

Contains the FastAPI router for Telegram endpoints.

Current routes are grouped under `/telegram` and expose:

- login
- single and bulk Telegram user registration
- CRUD-style read/update/delete for `TelegramUser`
- CRUD-style create/read/update/delete for `UserProfile`
- CRUD-style create/read/update/delete for `UserStats`

Treat handlers as thin transport code.
If a change affects multiple models or requires business coordination, move that logic into `services/` instead of growing `handlers.py`.

### `utils/`

Currently minimal.

Only place code here if it is Telegram-specific and reused across this module.
Do not move generic utilities here if they belong in `system`.

## Data Model Contract

### `TelegramUser`

`TelegramUser` represents the Telegram-side identity.

Important fields:

- `telegram_id` is the external unique identifier and is the main idempotency key
- `username`, `first_name`, `last_name`, `language_code` store Telegram metadata
- `is_blocket_bot` stores bot-block status using the current field name as implemented

Relationships:

- `user_profile` — one-to-one, `uselist=False`, `lazy="selectin"`, `cascade="all, delete-orphan"`
- `user_stats` — one-to-one, `uselist=False`, `lazy="selectin"`, `cascade="all, delete-orphan"`

Agent note:

- `last_seen_at` no longer lives on `TelegramUser`; it moved to `UserStats`.
- The field `is_blocket_bot` is intentionally spelled this way. Even if it looks like a typo, do not rename it casually because that would affect models, schemas, migrations, and API contracts.

### `UserProfile`

`UserProfile` represents collected profile data for a Telegram user.

Important fields:

- `telegram_user_id` links the profile to `TelegramUser` (`ForeignKey(..., ondelete="CASCADE")`, unique)
- `phone`, `email`, `timezone`, `full_name`, `note`

Relationship rules:

- each `TelegramUser` is expected to have at most one `UserProfile`
- deleting a `TelegramUser` removes the linked profile through cascade behavior

### `UserStats`

`UserStats` represents behavioral stats for a Telegram user.

Important fields:

- `telegram_user_id` links stats to `TelegramUser` (`ForeignKey(..., ondelete="CASCADE")`, unique)
- `last_seen_at` — last time the user touched the bot; has `server_default=now()` and is updated on login
- `source` — acquisition source (deep-link payload, UTM, etc.)
- `state` — current dialog/FSM state of the user (free-form string)
- `state_changed_at` — UTC moment of the last ACTUAL `state` value change. Maintained by a
  SQLAlchemy attribute listener on `UserStats.state` (`active_history=True`) in
  `models/user_stats.py` — NOT by `onupdate` — so any write path (service, generic PATCH)
  stamps it, and re-assigning the same value does not bump it. Drip newsletters count
  days from this timestamp; the composite index `ix_userstats_state_changed`
  (`state`, `state_changed_at`) serves the sweep query.

Relationship rules:

- each `TelegramUser` is expected to have at most one `UserStats`
- deleting a `TelegramUser` removes the linked stats through cascade behavior

If you modify relationship settings, verify both ORM behavior and database-level foreign key behavior together.

## Service Behavior That Must Be Preserved

### Atomicity model

All creation flows persist their rows through a single `AsyncSession` that commits once at the
request boundary (`database.get_session`). Because `CRUD` operations only `flush()` (never commit),
all writes in one request belong to one transaction. If any step raises, `DBErrorHandler` converts it
to an `HTTPException`, the request fails, and `get_session` rolls the whole transaction back.

This is why the multi-model flows do **not** need manual cleanup/compensation: a partial failure
rolls back the user, profile, and stats together.

### `create_telegram_user(...)`

This is the atomic registration flow. Its contract:

1. It uses `CRUD.get_or_create(...)` with `lookup_fields=("telegram_id",)` for the `TelegramUser`.
2. If the Telegram user already exists, it returns the existing row and `created=False` (profile/stats are not recreated).
3. If the Telegram user is new, it also creates a linked `UserProfile` and a linked `UserStats` via `CRUD.create(...)`.
4. `UserStats.last_seen_at` is set to the registration moment; `profile`/`stats` inputs are optional and default to empty.
5. Before returning, it refreshes `user_profile` and `user_stats` so the response can serialize them.

Preserve this behavior unless the product explicitly changes the lifecycle contract.

### `bulk_create_telegram_users(...)`

Bulk registration creates, per input item, one `TelegramUser`, one `UserProfile`, and one `UserStats`,
using `CRUD.bulk_create(...)` for each model. It is **not** idempotent — a duplicate `telegram_id`
raises an `IntegrityError` (400). The whole batch shares one transaction, so any failure rolls it back entirely.

### `login_telegram_user(...)`

Login is a write event, not only a read:

- it finds a user by `telegram_id`
- returns `404` if not found
- updates `UserStats.last_seen_at` (skipped defensively if stats are missing)
- flushes and refreshes the entity

If you change login semantics, document whether it is still read-plus-touch or becomes pure authentication lookup.

## Handler Contract

Important behavior in `handlers.py`:

- `POST /telegram/login` logs in an existing Telegram user by `telegram_id`
- `PUT /telegram/state` sets the named funnel state (`user_stats.state`) by `telegram_id`;
  creates the stats row defensively if it is missing, returns `404` for unknown users
- `POST /telegram/users` accepts the composite `TelegramUserRegister` body, is idempotent, and returns `201` for new rows, `200` for existing rows
- `POST /telegram/users/bulk` accepts a list of `TelegramUserRegister` and creates users + profiles + stats
- `GET /telegram/users` and `GET /telegram/users/{id}` return `TelegramUserRead` with nested `user_profile` and `user_stats` (loaded via `lazy="selectin"`)
- `GET /telegram/profile`, `GET /telegram/stats` and their `{id}` variants rely on shared `CRUD.get(...)` pagination and search behavior
- `PATCH`/`DELETE`/`POST` flows for `profile` and `stats` rely on shared `CRUD` contracts

`profile` and `stats` in the `POST /telegram/users` body are optional. If omitted, an empty profile and a default stats row are created. See [API contracts](API.md) for the full per-endpoint request/response JSON.

If handler behavior changes, keep response codes and idempotency rules explicit in both code and docs.

### Authorization

All endpoints are gated by dependencies from `app.modules.admin_module.dependencies`:

- `POST /telegram/login` → `require_service` (only the user bot, via `X-Service-Token`).
- `PUT /telegram/state` → `require_service` (the bot moves users through funnel states).
- `POST /telegram/users` → `require_admin_or_service` (bot registers users; admin panel also creates them).
- Everything else (`users/bulk`, `GET`/`PATCH`/`DELETE` users, all `profile`/`stats`, `newsletter`,
  all `drip-newsletters`) → `require_admin` (Bearer JWT).

When adding a new endpoint here, pick the matching gate explicitly via `dependencies=[Depends(...)]`.

## Change Rules

Good changes in this module:

- extending Telegram user, profile, or stats fields that clearly belong to this domain
- adding Telegram-specific service orchestration
- improving consistency between Telegram user creation and profile/stats creation
- documenting API or model contracts more clearly

Avoid these changes:

- moving generic persistence logic out of `system` into this module
- adding unrelated product-specific workflows that do not belong to Telegram identity/profile/stats storage
- breaking single-transaction atomicity for multi-step create flows
- renaming existing public fields without handling migration and schema impact

## Safety Notes

- If you add or rename model fields, update models, schemas, handlers, and migrations together.
- If you change exports, update `telegram_module/__init__.py` and `app/modules/__init__.py` (Alembic discovery).
- If you change creation or login semantics, update this file.
- If you add feature-specific queries beyond simple CRUD, prefer new service functions instead of overloading handlers.
- Keep search, pagination, and generic patch/delete behavior delegated to `system.CRUD` unless there is a strong Telegram-specific reason not to.

## Practical Agent Workflow

When working in or around this module:

1. Check whether the change is Telegram-domain logic or shared infrastructure logic.
2. If it is shared infrastructure, edit `system` instead of `telegram_module`.
3. If it is Telegram-specific orchestration, prefer `services/user_service.py`.
4. Keep `handlers.py` thin and transport-focused.
5. Preserve the `TelegramUser` ↔ `UserProfile` / `UserStats` lifecycle contract.
6. Update module documentation when behavior or exported interfaces change.

This module should stay reusable, predictable, and centered on Telegram user identity, profile collection, and behavioral stats.

## Newsletter broadcast

`POST /telegram/newsletter` — `multipart/form-data`: `payload` (JSON string of
`NewsletterRequest`) + optional `file` (UploadFile). See [API contracts](API.md) for
the HTTP request/response shape.

`NewsletterRequest` validation (schema, mirrors the admin-panel checks so a bad value
never reaches Telegram): each INLINE button needs exactly one of `url` / `callback_data`;
`url` must be `http(s)`/`tg://`, and for `http(s)` a real host — a dot with a ≥2-char TLD
(or IPv4), since `https://asdasd`/`localhost` are rejected by Telegram as `Wrong HTTP URL`;
`callback_data` must be ≤ `CALLBACK_DATA_MAX_BYTES` (64) UTF-8 **bytes**, not characters.

Flow (`services/newsletter_service.py`): validate (text OR file required) →
`CRUD.count(TelegramUser, search, field)` (0 → 404) → upload `file` via `file_module`
(`s3_client` + `File`) capturing `File.id` → `CRUD.get_column(TelegramUser,
TelegramUser.telegram_id, ...)` → generate one `broadcast_id` (`uuid4`) → split recipients
into chunks of `settings.newsletter_chunk_size` (default 500, ENV `newsletter_chunk_size`)
→ enqueue ONE outbox row **per chunk** in the request transaction (`ceil(N / chunk_size)`
rows, all sharing the same `broadcast_id`). The outbox runtime publishes only after commit.

Published message (`enqueue_outbox_message`): event `telegram.newsletter`, queue
`telegram_notifications`, routing key `telegram_notifications`, exchange `app.events`
(direct). Payload: `{ chat_ids: list[int], message: str|None, use_buttons:
"INLINE"|"REPLY"|null, buttons: [{text,url?,callback_data?}]|null, file_id: int|null,
broadcast_id: str, chunk_index: int, chunk_total: int }`. `chat_ids` are the recipients of
ONE chunk (not the whole audience); `broadcast_id` is shared by every chunk of a broadcast
and is the dedup key the bot uses (`IdempotencyStore`, `SET NX`); `chunk_index`/`chunk_total`
are diagnostics for logs. `file_id` is the backend `File.id`; the bot resolves it via
`GET /api/files/{id}`. The endpoint response carries `broadcast_id` (`NewsletterResult`) for
tracing.

Why chunk: one message = one chunk (≤`chunk_size` recipients), so the un-acked message
window stays small and well within RabbitMQ `consumer_timeout` (30 min). Without it a long
broadcast would exceed the timeout → redelivery → the whole audience duplicated.

Recipient filtering reuses `CRUD` (`count` / `get_column` with the same `search`/`field`
semantics as `GET /telegram/users`). Outbox rows share the transaction with the optional
`File`, so consumers never observe an uncommitted or rolled-back `file_id`.

## Drip newsletters (state-triggered scheduled broadcasts)

A drip rule (`DripNewsletter`) says: "user entered `trigger_state` → `days_offset` days
later at `send_time` (wall time in `settings.drip_timezone`) send this content". Content
fields mirror the regular newsletter (`text`, `use_buttons`, `buttons` JSON, `file_id`)
and are delivered through the SAME `telegram.newsletter` RMQ contract — the bot needs no
changes and cannot tell a drip from a manual broadcast.

Schemas (`schemas/drip.py`): `DripNewsletterCreate` inherits `NewsletterContent`
(extracted base of `NewsletterRequest` holding text/buttons + `_validate_buttons`), so
button validation is identical everywhere. `DripNewsletterPatch` allows only
`title`/`is_active` — content is immutable in v1 (recreate the rule instead; the send
log is keyed by rule id and must stay honest).

Admin endpoints (all `require_admin`; full request/response JSON in
[API contracts](API.md)):

- `POST /telegram/drip-newsletters` — multipart like `/telegram/newsletter`
  (`payload` JSON + optional `file`); same content gates (text or file required,
  `MESSAGE_MAX_LENGTH`); S3 compensation on DB failure. → 201 `DripNewsletterRead`.
- `GET /telegram/drip-newsletters?page&limit` — list with `sent_count` (single
  outer-join GROUP BY over `DripNewsletterSend`).
- `PATCH /telegram/drip-newsletters/{id}` — title / is_active only.
- `DELETE /telegram/drip-newsletters/{id}` — deletes the rule, its send log
  (CASCADE) and the attached `File` row; the S3 object is removed best-effort in a
  background task after commit (mirrors `file_module` semantics).

Delivery (`services/drip_sweep.py` + `tasks.py`): a TaskIQ cron task
(`drip_newsletter_sweep`, `* * * * *`) runs `run_drip_sweep()`. Per active rule, in ONE
transaction (opened via `database.sessionmaker()` — sanctioned non-request pattern):

1. `compute_entry_windows(...)` inverts the due condition into UTC ranges over
   `state_changed_at` (index-friendly; the entry-day window is capped at `due_at`
   so `days_offset=0` users entering AFTER `send_time` are never sent retroactively).
2. Candidate select: `state == trigger_state` AND `state_changed_at` in window AND
   NOT EXISTS in `dripnewslettersend` — "still in state" + "once ever" semantics.
3. Claim: `INSERT INTO dripnewslettersend ... ON CONFLICT (rule, user) DO NOTHING
   RETURNING` — only returned users become recipients (concurrent sweeps are safe).
4. Chunk by `newsletter_chunk_size` → `build_newsletter_payload` +
   `enqueue_outbox_message` with the newsletter constants. `broadcast_id` is
   `drip-{rule_id}-{uuid}` per rule per run: the bot's Redis dedup only guards RMQ
   redelivery of a chunk; the once-ever guarantee lives in the DB unique constraint.

INVARIANT: the send-log claim and the outbox enqueue MUST stay in the same
transaction. Splitting them reintroduces either duplicates or silently lost sends.

Behavioral notes: rules never fire retroactively (due time already past at rule
creation → skipped); scheduler downtime is forgiven up to `drip_catchup_seconds`
(default 6h), later — skipped; a user who left the state is skipped WITHOUT a log
row, so re-entering the state grants a new chance until the first actual send.

Runtime requirements: `taskiq_enabled=true` + the `backend_worker` and
`backend_scheduler` compose services (infra). The scheduler needs
`LabelScheduleSource` (added in `taskiq_module/scheduler.py`) to pick up the
decorator-declared cron. Settings: `drip_enabled`, `drip_timezone` (validated
`ZoneInfo` name), `drip_catchup_seconds`.
