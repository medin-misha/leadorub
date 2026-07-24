# Admin Module

## POST /api/auth/login

> Login with `username`/`password`. Public endpoint, additionally rate-limited (per IP and per IP+username). When the limit is exceeded — `429` with a `Retry-After` header. On invalid credentials — a generic `401`. On success returns an access JWT.

request

```json
{
  "username": "admin",
  "password": "s3cret-password"
}
```

response

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

## GET /api/auth/me

> Returns the current administrator identified by the Bearer JWT. Requires authorization (`Authorization: Bearer <token>`). `is_active` is checked in the DB on every request.

request

```
No request body. Authorization: Authorization: Bearer <access_token> header.
```

response

```json
{
  "id": 1,
  "username": "admin",
  "is_active": true,
  "created_at": "2026-07-24T10:15:30.000000",
  "updated_at": "2026-07-24T10:15:30.000000"
}
```

## GET /api/auth/admins

> Returns a paginated list of administrators. Requires a Bearer JWT.

request

```
No request body. Query parameters:
- page: int, >= 1, default 1 — page number.
- limit: int, >= 1, default 50 — page size.
Authorization: Authorization: Bearer <access_token> header.
```

response

```json
[
  {
    "id": 1,
    "username": "admin",
    "is_active": true,
    "created_at": "2026-07-24T10:15:30.000000",
    "updated_at": "2026-07-24T10:15:30.000000"
  },
  {
    "id": 2,
    "username": "manager",
    "is_active": false,
    "created_at": "2026-07-24T11:00:00.000000",
    "updated_at": "2026-07-24T11:05:00.000000"
  }
]
```

## POST /api/auth/admins

> Creates a new administrator. Requires a Bearer JWT. Returns `201 Created`. On a duplicate `username` — `400`. Password length: from 6 to 72 bytes (bcrypt limit).

request

```json
{
  "username": "manager",
  "password": "new-password"
}
```

response

```json
{
  "id": 2,
  "username": "manager",
  "is_active": true,
  "created_at": "2026-07-24T11:00:00.000000",
  "updated_at": "2026-07-24T11:00:00.000000"
}
```

## PATCH /api/auth/admins/{id}

> Partial update of an administrator: change password and/or the active flag. Requires a Bearer JWT. You cannot deactivate your own account. Both fields are optional.

request

```
Path parameter:
- id: int — administrator identifier.

Request body (both fields are optional):
```

```json
{
  "password": "another-password",
  "is_active": false
}
```

response

```json
{
  "id": 2,
  "username": "manager",
  "is_active": false,
  "created_at": "2026-07-24T11:00:00.000000",
  "updated_at": "2026-07-24T12:30:00.000000"
}
```

## DELETE /api/auth/admins/{id}

> Deletes an administrator. Requires a Bearer JWT. You cannot delete your own account (guarantees at least one administrator remains in the system).

request

```
No request body. Path parameter:
- id: int — administrator identifier.
Authorization: Authorization: Bearer <access_token> header.
```

response

```json
{
  "status": "ok"
}
```
