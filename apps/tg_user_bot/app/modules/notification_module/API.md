# Notification Module — Interface Contracts

This module consumes one RabbitMQ queue and calls one backend endpoint. It exposes
no Telegram commands.

## Consumed Queue: `telegram_notifications`

- exchange `app.events`, routing key `telegram_notifications`.
- handler: `handle_telegram_notification` validates `message.payload` against
  `TelegramNotification` and calls `send_notification`.

### Payload: `TelegramNotification`

```json
{
  "chat_ids": [123, 456],
  "message": "Hello",
  "use_buttons": "INLINE",
  "buttons": [
    { "text": "Open", "url": "https://example.com" }
  ],
  "file_id": 42,
  "broadcast_id": "b-2026-07-24-1",
  "chunk_index": 0,
  "chunk_total": 4
}
```

| Field | Type | Notes |
| --- | --- | --- |
| `chat_ids` | `list[int \| str]` | recipients of ONE chunk; the consumer loops and sends to each. Required. |
| `message` | `str \| null` | text, or caption when a file is attached. |
| `use_buttons` | `"INLINE" \| "REPLY" \| null` | keyboard type. |
| `buttons` | `list[TelegramButton] \| null` | FLAT list — one button per row. |
| `file_id` | `int \| null` | backend `File.id` (NOT a Telegram file_id). Resolved via `GET /api/files/{id}`; `image/*` → `send_photo`, else `send_document`. |
| `broadcast_id` | `str \| null` | shared id of all chunks of one broadcast; the dedup key. `null` = dedup off. |
| `chunk_index` / `chunk_total` | `int \| null` | diagnostics only; not used by delivery or dedup. |

### `TelegramButton`

```json
{ "text": "Share phone", "requests_contect": true }
```

- `text` — required.
- INLINE keyboards use `url` → `callback_data` → `web_app` (first present wins;
  fallback `callback_data = text`). `request_contact` / `request_location` are
  ignored for INLINE.
- REPLY keyboards use `requests_contect` (share contact), `request_location`,
  `web_app`.
- Note the historical typo `requests_contect`: a `model_validator` accepts BOTH
  `request_contact` and `requests_contect` on input and maps to the internal
  `requests_contect`.

## Backend Endpoint Consumed

### GET /api/files/{id}

Downloads an attachment once (bytes reused as a Telegram file_id for the rest of
the chunk). Header `X-Service-Token` required — the backend gates this endpoint
with `require_admin_or_service`; without the token the download is `401`. Timeout
is `BACKEND_REQUEST_TIMEOUT`. Missing content type defaults to
`application/octet-stream`.
