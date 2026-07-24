# Support Module — Interface Contracts

## Telegram Commands

- `/support` — enter support mode (protected, `@login_required`).
- `/stop` — leave support mode (only while `active`). The inline "Завершить
  диалог" button (`support:stop`) does the same.

## Published Queue: `telegram_support_in`

Text messages only. Published via `rmq_publisher.publish` with
`event="telegram.support_message"`, exchange `app.events` (`direct`), routing key
`telegram_support_in`. The contract must match the backend `chat_module` consumer.

```json
{
  "telegram_id": 123,
  "text": "user message",
  "tg_message_id": 4567
}
```

- `telegram_id` — `message.from_user.id`.
- `text` — `message.text`.
- `tg_message_id` — `message.message_id`.

The 👀 reaction means "queued to the broker", NOT "the admin has read it".

## Backend Endpoint Consumed

### POST /api/chat/inbound-media

Uploads a photo/document (binary over HTTP, not RMQ). Header `X-Service-Token`
required. Separate 60 s timeout. Multipart `FormData`:

- `telegram_id` (str)
- `tg_message_id` (str, when present)
- `caption` (only when non-empty)
- `file` (bytes, with `filename` and `content_type`)

Photos are sent as `photo_{message_id}.jpg` (`image/jpeg`); documents keep the
original `file_name` / `mime_type` (fallbacks `document_{message_id}` /
`application/octet-stream`). The bot enforces `MAX_MEDIA_BYTES = 10 MB` before and
after download; the backend validates size independently.
