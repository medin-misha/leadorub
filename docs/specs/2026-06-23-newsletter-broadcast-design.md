# Newsletter broadcast — backend producer + bot consumer (design)

Date: 2026-06-23
Status: approved

## Goal

Add server-side broadcast (newsletter) to Leadorub. An admin sends a request from the
admin panel; the backend validates it, confirms the audience is non-empty, uploads the
optional attachment, and publishes **one** RabbitMQ message containing the full list of
recipient chat ids. The `tg_user_bot` consumes that single message and fans the send-out
across all recipients itself (resolving the attachment, building the keyboard, sending).

Two services change and can be implemented in parallel once the RMQ contract below is
fixed:
- **backend** (`apps/backend`) — the producer (new endpoint + service inside the existing
  `telegram_module`).
- **tg_user_bot** (`apps/tg_user_bot`) — the consumer (`notification_module` schema + sender).

## Decisions (from brainstorming)

- **Attachment = backend `File.id`.** The optional file is uploaded through the existing
  `file_module` (S3/MinIO). The RMQ message carries `file_id` = the backend `File` model PK
  (NOT a Telegram file_id and NOT a raw URL). The bot resolves it by downloading the bytes
  from the backend's existing `GET /api/files/{id}` (it already has `BACKEND_URL` + an
  aiohttp client), then uploads to Telegram once and reuses the returned Telegram file_id
  for the remaining recipients.
- **Fan-out happens in the bot.** The backend publishes RMQ message(s) carrying
  `chat_ids: list`. One message per recipient is explicitly forbidden.
  **Update (2026-06-25):** superseded — the backend now splits the audience into chunks of
  `newsletter_chunk_size` (one RMQ message per chunk, all sharing one `broadcast_id`) to bound
  the un-acked window under RabbitMQ `consumer_timeout`; the bot dedups recipients via Redis
  `SET NX`. See plan `superpowers/plans/2026-06-25-newsletter-chunking-idempotency.md`.
- **Single `use_buttons` key.** The RMQ contract uses one field `use_buttons: null|INLINE|REPLY`
  (mirroring the backend request contract), replacing the bot's current two boolean flags
  `inline_buttons` / `reply_buttons`.
- **Flat button list.** Both the admin request and the RMQ message carry a flat
  `buttons` list. The bot arranges layout: one button per row (vertical stack).
- **No backend fan-out task (no taskiq).** Because the backend publishes a single message,
  the endpoint stays synchronous and fast: count → upload → fetch ids → publish → respond.
- **No new DB model / no migration.** The broadcast itself is not persisted; the attachment
  reuses the `File` model.
- **Add the feature inside `telegram_module`** (per the request), not a new module.

## RMQ contract (single source of truth — both services code against this)

Queue/topology the bot already consumes (unchanged):
- queue `telegram_notifications`, exchange `app.events` (type `direct`), routing key `telegram_notifications`.

Message `payload` (inside the standard `RMQMessage` envelope `{event, payload, message_id, timestamp, source, correlation_id}`):

```json
{
  "chat_ids": [111, 222, 333],
  "message": "Text, or caption when a file is attached",
  "use_buttons": "INLINE",
  "buttons": [
    { "text": "Open site", "url": "https://example.com" },
    { "text": "Press me",  "callback_data": "act:1" }
  ],
  "file_id": 42
}
```

Field rules:
- `chat_ids: list[int | str]` — recipient Telegram chat ids (from `TelegramUser.telegram_id`). Non-empty.
- `message: str | None` — the text; used as the caption when `file_id` is set. `null` allowed only when `file_id` is set.
- `use_buttons: "INLINE" | "REPLY" | null` — keyboard kind (or none).
- `buttons: list[Button] | null` — flat list. `Button = { text, url?, callback_data?, requests_contect?, request_location?, web_app? }`. For `INLINE`, each button has exactly one of `url` / `callback_data` (or `web_app`); for `REPLY`, buttons carry `text` (+ optional reply props). Layout: one button per row.
- `file_id: int | null` — backend `File.id`. `null` = text-only broadcast.

Producer publishes with `event = "telegram.newsletter"`, `queue_name = "telegram_notifications"`, `routing_key = "telegram_notifications"`, `exchange_name = "app.events"`, `exchange_type = "direct"`.

## Backend (producer) — `apps/backend/app/modules/telegram_module`

### Endpoint

`POST /telegram/newsletter` — `multipart/form-data`:
- `file: UploadFile | None` — optional attachment.
- `payload: str` (a `Form()` field) — JSON string of the request body (lets us combine a
  binary file with nested JSON in one request).

`handlers.py` only validates/parses/delegates; logic lives in `services/`.

### Request schema (`schemas/`)

```python
NewsletterFilters: { search: str | None, field: str | None }
NewsletterButton:  { text: str, url: str | None, callback_data: str | None }
NewsletterRequest: {
    filters: NewsletterFilters,
    text: str | None,
    use_buttons: Literal["INLINE", "REPLY"] | None,
    buttons: list[NewsletterButton] | None,
}
```

Validation:
- `text` OR `file` must be present (reject empty broadcast → 422/400).
- `use_buttons == INLINE` → each button has exactly one of `url` / `callback_data`.
- `use_buttons == REPLY` → buttons carry `text` only (ignore/forbid url/callback_data).
- `buttons` non-empty requires `use_buttons` set, and vice-versa.

### Service flow (`services/`)

1. Parse + validate `NewsletterRequest`.
2. `count_recipients(filters)` → if `0`, raise `404` ("no recipients for filter"). Do NOT upload the file yet.
3. If `file` present → upload via `file_module` (`s3_client.create` + `CRUD.create(File)`); capture `file_id = File.id`.
4. `get_recipient_chat_ids(filters)` → `list[int]` of `TelegramUser.telegram_id`.
5. Build RMQ payload (`chat_ids`, `message=text`, `use_buttons`, `buttons` flat, `file_id`).
6. `rmq_publisher.publish(event="telegram.newsletter", payload=..., queue_name="telegram_notifications", routing_key="telegram_notifications", exchange_name="app.events", exchange_type="direct")` — a single publish.
7. Return `200 { "status": "queued", "recipients": <N> }`.

### New recipient queries

`count_recipients(session, search, field)` and `get_recipient_chat_ids(session, search, field)`
must reuse the SAME filter semantics as `CRUD.get` (the `_get_field_search` /
`_get_text_search` logic in `app/modules/system/services/crud.py`). Preferred:
add generic `CRUD.count(model, search, field)` and `CRUD.get_column(model, column, search, field)`
to the `system` module so the filter logic is written once; the telegram service calls them
with `TelegramUser` / `TelegramUser.telegram_id`. (Decided at plan time; either generic in
`system` CRUD or local helpers, but the filter logic MUST NOT be copy-pasted divergently.)

### Constraints (from backend CLAUDE.md)

- Handlers validate/format/delegate only; business logic in `services/`.
- DB only via `Depends(database.get_session)`; never instantiate sessions in logic.
- Broker only via `rmq_publisher` (never import aio-pika in business code).
- New settings (if any) go in `MainSettings` (`app/core/config.py`) + `.env.example`. None expected.
- Sync docs: `telegram_module` `CLAUDE.md` (EN) + `README.md` (RU).

## Bot (consumer) — change map for `apps/tg_user_bot/app/modules/notification_module`

### `schemas.py`

| Symbol | Now | Becomes |
|---|---|---|
| `TelegramNotification.chat_id` | `int \| str` (single) | **`chat_ids: list[int \| str]`** |
| `TelegramNotification.message` | `str` (required) | `str \| None` (optional caption) |
| `TelegramNotification.inline_buttons` + `reply_buttons` | two `bool \| None` flags | **replaced by `use_buttons: Literal["INLINE","REPLY"] \| None`** |
| `TelegramNotification.buttons` | `list[list[TelegramButton]]` (2D) | **`list[TelegramButton]`** (flat) |
| `TelegramNotification.file_id` | — | **`int \| None`** (backend `File.id`) |
| `TelegramButton.url` | — | `str \| None` |
| `TelegramButton.callback_data` | — | `str \| None` |

Keep existing `TelegramButton` reply props (`requests_contect` typo + alias, `request_location`, `web_app`). New `url`/`callback_data` use correct spelling (do NOT repeat the typo pattern).

### `services/sender.py`

- **Loop over `chat_ids`** with a light throttle (Telegram ≈30 msg/s) and per-recipient
  `try/except` so one bad chat id does not abort the batch (log failures).
- **Keyboard:** branch on `use_buttons`:
  - `INLINE` → inline keyboard, one button per row, priority `url` → `callback_data` → `web_app`; remove the current `callback_data = btn.text` hardcoded fallback (use it only as a last-resort default, or skip the button).
  - `REPLY` → reply keyboard, one button per row, using `text` (+ `requests_contect`/`request_location`/`web_app` if present).
- **Attachment:** if `file_id` set, download bytes once from backend `GET /api/files/{id}`
  (via the bot's aiohttp backend client + `BACKEND_URL`); pick `send_photo` when the
  response `Content-Type` is `image/*`, else `send_document`. Send to the first recipient
  with the bytes (`BufferedInputFile`), capture the returned Telegram file_id from the
  response, and reuse that file_id for the remaining recipients (no re-upload). Caption = `message`.
- **Text-only:** if no `file_id`, `bot.send_message(chat_id, message, reply_markup=...)`.

### Bot-side file resolver

Add a small helper that calls the backend `GET /api/files/{id}` and returns `(bytes, content_type)`,
reusing the existing `system/client.py` aiohttp pattern (`BACKEND_URL`). One download per
broadcast, not per recipient.

### Consumer wiring

`consumer_handler.py` already validates the envelope and calls `send_notification`. No queue
change. The handler keeps `TelegramNotification.model_validate(message.payload)`; the model
change does the rest.

### Docs

Update `notification_module` `README.md` (RU) and `AGENTS.md`/`CLAUDE.md` (EN) to the new
contract (`chat_ids`, `use_buttons`, flat `buttons`, `file_id`).

## Error handling

- Backend: empty audience → `404`; invalid body → `422`/`400` (FastAPI/Pydantic); S3 upload
  failure → propagate (existing `file_module` purges the orphaned object); RMQ publish failure
  → `503`/`500` (existing `DBErrorHandler`/RMQ error path).
- Bot: per-recipient failures are caught and logged; the message is acked once the loop
  completes. ⚠️ Known trade-off of the single-message design: if the bot crashes mid-loop,
  redelivery re-sends to the already-processed prefix (possible duplicates). Accepted for now;
  batching would bound this later.
- ⚠️ The backend must be reachable from the bot at `BACKEND_URL` inside the docker network
  (already configured) for file resolution.

## Testing

- **Backend** (check the existing pytest harness style first): `count_recipients` /
  `get_recipient_chat_ids` filter parity with `CRUD.get`; `use_buttons` + button validation;
  the publish payload shape (mock `rmq_publisher`); empty-audience → 404; file path sets `file_id`.
- **Bot** (mirror the existing `test_rmq_module` style): `TelegramNotification` parsing of the
  new contract (`chat_ids`, `use_buttons`, flat `buttons`, `file_id`, optional `message`);
  inline keyboard built with `url`/`callback_data`; photo-vs-document selection by content-type;
  loop over `chat_ids` (mock bot) including a per-recipient failure not aborting the batch.

## Implementation / parallelization

The RMQ contract above is the fixed interface between the two services. After the spec:
- Two implementation plans: **(A) backend producer**, **(B) bot consumer** — each self-contained.
- They can run as two parallel implementer subagents (separate dirs, separate venvs, no shared
  code → no conflicts), each verifying its own unit tests.
- End-to-end verification (RabbitMQ + backend + bot + DB via docker) is a single manual step by
  the user after both tracks land — it cannot be parallelized.

## Out of scope (YAGNI)

~~Batching/chunking of `chat_ids`~~ (**now implemented** — plan
`2026-06-25-newsletter-chunking-idempotency.md`: chunks of `newsletter_chunk_size` with a
shared `broadcast_id`, Redis dedup in the bot); persisting broadcast history; scheduling; delivery
receipts; admin-panel frontend changes to send `use_buttons`/`buttons` (the current frontend
sends text+file only — a small follow-up will extend it to the richer body); real Telegram
file_id pre-upload; rate-limit tuning beyond a basic throttle.
