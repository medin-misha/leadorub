# Persona Module — Interface Contracts

This module has no router and no commands of its own. Its surface is the funnel it
sends and the single backend endpoint it calls.

## Trigger

Invoked by the system `/start` handler for any payload that is not `business`
(empty, `source_*`, or arbitrary). See `system/API.md` → Deep Links.

## Outbound Telegram Surface

A message chain ending in a video with a contact keyboard:

- "✍️ Написать" — URL button to `ADMIN_CONTACT_URL` (omitted when unset).
- "📩 Оставить заявку" — WebApp button to `CLIENT_MINIAPP_URL`.

## Backend Endpoint Consumed

### PUT /api/telegram/state

Sets the funnel state after the chain. In the client the path is `/telegram/state`
(the `/api` prefix comes from `BACKEND_API_PREFIX`); header `X-Service-Token`.

request

```json
{ "telegram_id": 123, "state": "persona_start" }
```

Failures are logged as a warning only — the `/start` UX must not break.
