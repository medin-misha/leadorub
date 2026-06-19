# File Module Guide for AI Agents

## Purpose

`app.modules.file_module` is a functional business module for uploading, downloading, and deleting files and managing their database metadata.

Key responsibilities:
- Managing file metadata in the PostgreSQL database using the `File` model.
- Managing raw file assets in S3-compatible storage (MinIO) via the `S3Client`.
- Exposing HTTP upload, download, and delete API endpoints.

This module depends heavily on `app.modules.system` and reuse its shared database and error-handling utilities instead of implementing them locally.

---

## Dependency on System Module

The `file_module` is built on top of the shared core infrastructure in `system`.

Specific integrations:
- `Base` and `TimestampMixin` for the `File` ORM model.
- `CRUD` service class for performing transactional PostgreSQL operations.

Preferred import pattern:
```python
from app.modules.system import Base, TimestampMixin, CRUD
```

Do not duplicate CRUD operations, transaction management, or low-level database error handling within this module.

---

## Domain Ownership

The module owns a single model:
- `File` — Stores the metadata of an uploaded file.

Key architectural concepts:
- In the S3 bucket, files are saved using a unique generated key: `<uuid4_hex>.<extension>`.
- `File.link` stores the full public URL of the object inside the S3 bucket.
- `File.name` stores the original human-readable filename (supporting Russian/Cyrillic and special characters).
- `File.note` stores an optional user-provided note.

The bucket object key is intentionally decoupled from the original filename to prevent file-system encoding issues inside the object storage.

---

## Module Layout

### `models/`
Defines the database schema.
- **File**: `models/file.py`
  - Inherits from `Base` (primary key `id`) and `TimestampMixin` (`created_at`, `updated_at`).
  - `link` — `String(1024)`, non-nullable.
  - `name` — `String(512)`, non-nullable.
  - `note` — `Text`, nullable.

### `schemas/`
Defines Pydantic DTO validation schemas.
- **File schemas**: `schemas/file.py`
  - `FileCreate` — Internal schema for database insertion via `CRUD.create()`. Contains `link`, `name`, `note`.
  - `FileRead` — Public schema returned by API endpoints. Contains `id`, `link`, `name`, `note`, `created_at`, `updated_at`.
  - `FileCreate` is never accepted directly from client requests. The handler constructs it dynamically after a file is successfully uploaded to the S3 bucket.

### `services/`
Defines the asynchronous object storage connector.
- **S3 Client**: `services/s3_client.py`
  - `S3Client` — Class exposing four asynchronous methods: `create`, `read`, `stream`, `delete`.
  - `create(file_obj: BinaryIO, filename: str, content_type: str) → str` — Streams a file directly to the S3 bucket using `aiobotocore` without loading the entire payload into server memory. File size is determined via `seek` and `tell` on the file-like object. Returns the public link.
  - `read(link: str) → bytes` — Downloads file contents from the S3 bucket by its URL. Returns raw bytes.
  - `stream(link: str, chunk_size: int) → AsyncGenerator[bytes, None]` — Asynchronously streams chunks of a file from the S3 bucket without full buffering in memory.
  - `delete(link: str) → None` — Deletes the file from the S3 bucket by its URL.
  - `_scheme` — Property returning `"https"` or `"http"` based on `settings.minio_secure`.
  - `_key_from_link(link: str) → str` — Extracts the S3 object key from a full public bucket URL.
  - `s3_client` — Instantiated singleton of `S3Client` to be imported in handlers.

All connection parameters are read from `app.core.config.settings`: `minio_endpoint`, `minio_access_key`, `minio_secret_key`, `minio_bucket`, and `minio_secure`. 

The client instantiates a new `aiobotocore` session and client for each call inside an `async with self._client()` context. Do not cache the client across calls since connection pooling is managed internally by botocore.

### `handlers.py`
FastAPI router containing the endpoint routes.
- Registered with the `/files` prefix and `Files` tag.
- Endpoints:
  - `POST /api/files/` — Uploads a file.
  - `GET /api/files/{id}` — Downloads a file.
  - `DELETE /api/files/{id}` — Deletes a file.
- Router requirements:
  - Keep handlers thin; coordinate between services and do not put business rules inside endpoints.
  - `SessionDep` dependency uses `Annotated[AsyncSession, Depends(database.get_session)]`.
  - Upload endpoints accept `UploadFile` and an optional `Form` parameter for `note`.
  - Download endpoints return a `StreamingResponse` using chunked generator `s3_client.stream` with a URL-encoded `Content-Disposition` header supporting special and Cyrillic character sets.
  - `Content-Type` headers are determined using the standard `mimetypes` library.

---

## Handler Operational Contracts

### `POST /api/files/`
1. Normalizes the filename: `filename = file.filename or "unnamed"`.
2. Calls `s3_client.create(file.file, filename, file.content_type)`. The `SpooledTemporaryFile` is streamed directly.
3. Inserts metadata into PostgreSQL using `CRUD.create(...)` with the `File` model and a `FileCreate` schema.
4. **Error handling**: If `CRUD.create(...)` raises a database exception, the handler catches it, triggers `s3_client.delete(link)` to prevent orphaned files in the S3 bucket, and propagates the exception.
5. Returns `FileRead` with a `201 Created` status code.

### `GET /api/files/{id}`
1. Queries the database using `CRUD.get(File, session, id=id)`. Throws a `404` error if the record does not exist.
2. Streams chunks from the bucket using the async generator `s3_client.stream(file_record.link)`.
3. Returns a `StreamingResponse` consuming the async generator with appropriate MIME types and `Content-Disposition` headers.

### `DELETE /api/files/{id}`
The execution order is strict:
1. Queries the database using `CRUD.get(File, session, id=id)` to obtain the record and extract the `link`.
2. Deletes the database record: `session.delete(file_record)` and `session.flush()`.
3. Deletes the object from the S3 bucket using `s3_client.delete(link)` inside a background task. If the S3 operation fails, it is logged as a warning, and the API request successfully completes.
4. Returns `{"status": "ok"}`.

**Rationale for Database → S3 order**:
- If the database deletion fails, the file in the bucket remains fully intact and accessible; the state is consistent.
- Since the S3 deletion executes as a background task after the database commit, if the S3 deletion fails, the database record is already gone. There is no broken or orphaned link exposed to the API. The orphaned object remains in the bucket and can be garbage-collected asynchronously.
- Bypassing this order (S3 → Database) can lead to data inconsistency. If the file is deleted from S3 first, but the database connection fails before the metadata is deleted, a broken link pointing to a non-existent asset will persist in the database.

---

## Extension and Maintenance Rules

Approved updates:
- Adding metadata fields to the `File` database model.
- Extending `S3Client` with additional S3 operations (e.g., pre-signed URLs, bucket listing).
- Improving error handling for network bottlenecks.

Prohibited updates:
- Placing business logic inside `handlers.py`.
- Re-implementing CRUD utilities or error logging already available in the `system` module.
- Hardcoding secrets, bucket configurations, or endpoints.
- Reordering steps in the delete handler.

---

## Operational Safety

- When adding or modifying fields on the `File` model, update the corresponding Pydantic schemas and generate a new migration revision immediately: `uv run alembic revision --autogenerate -m "..."`.
- When modifying exported primitives, update exports inside `file_module/__init__.py` and the general `app/modules/__init__.py` container.
- When modifying the public behavior of `S3Client` or handlers, update both `README.md` and this file.
- The `_key_from_link` parser relies on the URL structure `http(s)://{endpoint}/{bucket}/{key}`. If the S3 storage domain format changes, this helper must be updated.
