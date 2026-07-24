# Business Module — Interface Contracts

This module has no router and no commands of its own. Its surface is the funnel it
sends and the single backend endpoint it calls.

## Trigger

Invoked by the system `/start` handler when the deep-link payload equals
`business` (`t.me/<bot>?start=business`). See `system/API.md` → Deep Links.

## Outbound Telegram Surface

A message chain (welcome → captioned guide PDF → video) ending in a contact
keyboard:

- "✍️ Написать" — URL button to `ADMIN_CONTACT_URL` (omitted when unset).
- "📩 Оставить заявку" — WebApp button to `CLIENT_MINIAPP_URL`.

## Backend Endpoint Consumed

### PUT /api/telegram/state

Sets the funnel state after the chain. In the client the path is `/telegram/state`
(the `/api` prefix comes from `BACKEND_API_PREFIX`); header `X-Service-Token`.

request

```json
{ "telegram_id": 123, "state": "business_start" }
```

Failures are logged as a warning only — the `/start` UX must not break.
