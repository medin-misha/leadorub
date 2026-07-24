# Requisition Module — Technical Specification

This module manages the creation and lifecycle of user requisitions (e.g., consultation requests, community access applications, product orders).

## Technology Stack & Architecture

- **Models**: [models/requisition.py](models/requisition.py) (SQLAlchemy ORM, table `requisitions`), linked to `telegramuser.id`.
- **Database**: PostgreSQL (JSON/JSONB for dynamic requisition payloads).
- **Broker**: RabbitMQ via `rmq_publisher` for requisition-created and status-notification events.

---

## Data Model

The `Requisition` model:
- `telegram_user_id`: ForeignKey to `telegramuser.id` (CASCADE, indexed).
- `type`: String(50), representing the product type (e.g., `'consultation'`, `'community'`).
- `status`: String(30), with values: `'pending'` (default), `'in_progress'`, `'approved'`, `'rejected'`.
- `payload`: JSON, storing free-form survey data or form inputs.
- `admin_comment`: String(1024), comments added by administrators upon processing.
- `created_at`, `updated_at`: timestamps from `TimestampMixin`.

---

## API Endpoints

Registered prefix: `/api/requisitions` (tag `requisitions`). Endpoints: create via
`X-Service-Token`, public MiniApp create via `X-Telegram-Init-Data` (HMAC + rate
limit), and admin JWT list/detail/status-update.

See [API contracts](API.md).

---

## RabbitMQ Integration Contracts

This module currently publishes these contracts directly. The transactional
outbox is already used by newsletter and admin chat reply flows; migrating
requisition events to it is a separate consistency improvement.

### A. Inbound / Admin Notifications (New Requisition -> Future `admin_bot`)
- **Queue**: `admin_requisitions`
- **Exchange**: `app.events` (direct)
- **Routing Key**: `admin_requisitions`
- **Event Name**: `requisition.created`
- **Payload Shape**:
```json
{
  "requisition_id": 42,
  "telegram_id": 987654321,
  "username": "username",
  "type": "consultation",
  "payload": {
    "name": "User Name",
    "phone": "+123456789"
  },
  "created_at": "2026-07-09T10:08:03Z"
}
```

### B. Outbound User Notifications (Status Change -> `tg_user_bot`)
- **Queue**: `telegram_notifications`
- **Exchange**: `app.events` (direct)
- **Routing Key**: `telegram_notifications`
- **Event Name**: `telegram.notification`
- **Payload Shape**:
```json
{
  "chat_ids": [987654321],
  "message": "Status of your application 'Consultation' has changed to: approved...",
  "use_buttons": null,
  "buttons": null,
  "file_id": null
}
```
