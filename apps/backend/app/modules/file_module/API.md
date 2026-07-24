# File Module

## POST /api/files/

> Upload a file to S3 (MinIO) and store its metadata in the database. Authorization: `require_admin` (Bearer JWT). Body — `multipart/form-data`. The actual file size is validated before upload; if it exceeds `file_upload_max_size_bytes` (20 MiB by default), `413` is returned. Response — `201 Created` with the `FileRead` schema.

request

```
Content-Type: multipart/form-data

# form fields:
file  (required) — the file to upload (UploadFile)
note  (optional) — a text note about the file
```

response

```json
{
  "id": 1,
  "link": "https://minio.example.com/bucket/3f2a...c1.pdf",
  "name": "договор.pdf",
  "note": "комментарий или null",
  "created_at": "2026-07-24T10:00:00Z",
  "updated_at": "2026-07-24T10:00:00Z"
}
```

## GET /api/files/{id}

> Download the file as a stream (`StreamingResponse`) from S3. Authorization: `require_admin_or_service` (admin Bearer JWT or `X-Service-Token` for server-to-server, e.g. the bot downloading a file for a broadcast). Returns `404` if the record is not found. Response is not JSON but a binary stream of the file's bytes.

request

```
# path parameter:
id (integer, required) — the identifier of the File record in the database

# no request body
```

response

```
Body: binary stream of the file contents (not JSON).

Response headers:
Content-Type: <MIME derived from the filename extension> or application/octet-stream.
  Types that are dangerous for inline rendering (image/svg+xml, text/html,
  application/xhtml+xml, text/xml, application/xml) are forcibly
  downgraded to application/octet-stream (protection against Stored XSS).
Content-Disposition: attachment; filename*=UTF-8''<url-encoded-name>
X-Content-Type-Options: nosniff
```

## DELETE /api/files/{id}

> Delete the file record from the database (transactionally) and the object from S3 (best-effort, in a background task). Authorization: `require_admin` (Bearer JWT). Returns `404` if the record is not found. Response — JSON with the status.

request

```
# path parameter:
id (integer, required) — the identifier of the File record in the database

# no request body
```

response

```json
{
  "status": "ok"
}
```
