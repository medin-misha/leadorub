# System Module

## GET /api/system/health

> Application availability check. No authorization required. No request body (no path/query parameters).

request

```
No request body.
```

response

```json
{
  "status": "ok",
  "service": "Leadorub",
  "timestamp": "2026-07-24T12:00:00+00:00",
  "checks": {
    "application": {
      "status": "ok"
    }
  }
}
```

## GET /api/system/health/db

> Database availability check via a `SELECT 1` query. No authorization required. No request body. Returns `503 Service Unavailable` when the database is unavailable.

request

```
No request body.
```

response

```json
{
  "status": "ok",
  "service": "Leadorub",
  "timestamp": "2026-07-24T12:00:00+00:00",
  "checks": {
    "database": {
      "status": "ok",
      "message": "Database connection is available."
    }
  }
}
```

When the database is unavailable (`503 Service Unavailable`), the response is returned in the `detail` field:

```json
{
  "detail": {
    "status": "error",
    "service": "Leadorub",
    "timestamp": "2026-07-24T12:00:00+00:00",
    "checks": {
      "database": {
        "status": "error",
        "message": "Database is unavailable.",
        "error_type": "OperationalError"
      }
    }
  }
}
```
