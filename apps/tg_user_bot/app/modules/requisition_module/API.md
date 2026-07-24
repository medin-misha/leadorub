# Requisition Module — Interface Contracts

## Telegram Commands & Callbacks

- `/apply` (`@login_required`) — opens the product menu.
- callbacks: `apply:consultation`, `apply:community`, `apply:cancel`.
- cancel also via typed text "Отмена ❌".

## FSM Steps

- `ConsultationStates`: `waiting_for_name` → `waiting_for_phone` →
  `waiting_for_description`.
- `CommunityStates`: `waiting_for_name` → `waiting_for_experience` →
  `waiting_for_motivation`.

Phone is read from `message.contact.phone_number` (reply "Поделиться контактом 📱"
button) or from typed text.

## Backend Endpoint Consumed

### POST /api/requisitions

Called as `get_backend_client().create_requisition(telegram_id, type_, payload)`.
In the client the path is `/requisitions`; the `/api` prefix comes from
`BACKEND_API_PREFIX`.

request

```json
{
  "telegram_id": 123,
  "type": "consultation",
  "payload": { "name": "Ivan", "phone": "+7...", "description": "..." }
}
```

- `type` — `"consultation"` or `"community"`.
- `payload` for consultation: `{ name, phone, description }`.
- `payload` for community: `{ name, experience, motivation }`.

On `BackendClientError` the FSM state is preserved and a generic retry message is
shown. On success the state is cleared and a confirmation is sent.
