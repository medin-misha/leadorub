# System Module Guide For AI Agents

## Purpose

`app.modules.system` is the shared infrastructure module for other application modules.

Use it as the place for reusable foundations, not for product-specific business logic.

This module currently provides:

- a common SQLAlchemy base model via `Base`
- automatic timestamp fields via `TimestampMixin`
- a reusable async `CRUD` service
- centralized database error normalization via `DBErrorHandler`
- a base FastAPI router in `handlers.py`

If you are working inside another module and need common persistence primitives, check `system` first before introducing duplicates.

## Preferred Imports

When an agent needs shared ORM primitives, prefer importing from `app.modules.system` instead of deep internal paths.

Preferred imports:

```python
from app.modules.system import Base, TimestampMixin, CRUD
```

Use these rules:

- Import `Base` for all shared SQLAlchemy models that need the default primary key.
- Import `TimestampMixin` for models that should automatically store `created_at` and `updated_at`.
- Import `CRUD` when a module needs standard create/read/update/delete behavior without custom query logic.

If you specifically need the error handler implementation, import it from:

```python
from app.modules.system.services.errors import DBErrorHandler
```

Do not reimplement generic DB error mapping in feature modules if `DBErrorHandler` already covers the case.

## Module Map

### `models/`

Contains shared ORM model foundations.

Important file:

- `models/base.py`

Agent expectations:

- `Base` defines a shared `id` primary key.
- `TimestampMixin` adds `created_at` and `updated_at`.
- New shared model primitives belong here only if they are reusable across modules.

### `services/`

Contains reusable service-layer infrastructure.

Important files:

- `services/crud.py`
- `services/errors.py`

Agent expectations:

- `CRUD` is the main reusable abstraction for standard async database operations.
- `DBErrorHandler` converts SQLAlchemy-level failures into consistent `HTTPException` responses.
- Shared persistence behavior should be added here only if it is generic and module-agnostic.

### `handlers.py`

Contains a base router for the module.

Treat this file as infrastructure-level routing, not as a place for business workflows.

### `schemas/` and `utils/`

Currently minimal.

Add code here only if it is truly shared and belongs to the `system` layer rather than a feature module.

## How To Use `CRUD`

`CRUD` is intended as the default tool for simple entity persistence.

Use it when:

- the model follows the standard `Base` shape
- operations are ordinary create/get/patch/delete flows
- create semantics should be idempotent for one or more lookup fields
- filtering needs are simple
- feature-specific query optimization is not required

Do not force `CRUD` when:

- the query spans multiple models
- you need custom joins, aggregates, or domain rules
- the endpoint behavior is business-specific rather than generic

In those cases, create a feature-level service in the owning module and only reuse pieces from `system` when helpful.

### `CRUD.get(...)` Behavior

`CRUD.get(...)` is an interface method that dispatches by scenario.

Current scenarios:

- `_get_by_id(...)` for reading a single record by primary key
- `_get_field_search(...)` for searching a specific model field
- `_get_text_search(...)` for text search across all string columns

Agent expectations:

- Keep `get()` as the public orchestration layer.
- Keep `_get*` helpers focused on one search scenario each.
- Preserve stable ordering for paginated list queries.
- Keep input normalization in the public interface or in clearly named helpers.

### `CRUD.bulk_create(...)` Behavior

`CRUD.bulk_create(...)` is the shared path for batch inserting multiple records in a single transactional operation.

- Accepts a list of Pydantic schemas, a target model, and an `AsyncSession`.
- Creates instances and uses `session.add_all()` to add all instances to the session.
- Commits the transaction and refreshes all instances so their generated database defaults (like `id`, `created_at`, `updated_at`) are available.
- Automatically rolls back the session via `session.rollback()` and delegates database error handling to `DBErrorHandler` on failure.

### `CRUD.get_or_create(...)` Behavior

`CRUD.get_or_create(...)` is the shared path for idempotent create flows.

Use it when:

- a feature must treat repeated create requests as "return existing"
- existence is determined by one or more explicit `lookup_fields`
- the fallback behavior after a uniqueness race should stay generic

Current contract:

- accepts a Pydantic `data` object, a target `model`, an `AsyncSession`, and `lookup_fields`
- returns a tuple `(instance, created)`
- returns `(existing_instance, False)` when a matching row already exists
- returns `(new_instance, True)` when a new row is created
- on `IntegrityError` during insert, performs `rollback()` and re-reads by the same `lookup_fields`

Agent expectations:

- Keep `lookup_fields` aligned with actual uniqueness semantics at the model/database level.
- Use `get_or_create()` from feature services, not directly from handlers, when follow-up domain actions depend on whether the row was newly created.
- Do not add module-specific side effects into `CRUD.get_or_create()`; keep it limited to generic persistence behavior.

## Change Rules

When editing `system`, optimize for reuse and predictability.

Good changes:

- improving generic CRUD behavior
- improving reusable error handling
- adding shared model mixins
- documenting infrastructure conventions

Avoid these changes:

- adding feature-specific business rules
- coupling `system` to Telegram or another product module
- hardcoding module-specific assumptions that do not generalize
- placing endpoint logic directly into shared services

## Safety Notes

- Preserve backward-compatible imports from `app.modules.system` when possible.
- If you change exported primitives, update both `__init__.py` and `README.md`.
- If your change introduces new settings or env variables, update `app/core/config.py` explicitly and document the new configuration contract.
- If you change `CRUD`, verify that its behavior is still generic, async-friendly, and safe for reuse.
- If you change search or error behavior, document the new contract clearly because other modules may rely on it.

## Practical Agent Workflow

When working in or around this module:

1. Check whether the needed primitive already exists in `system`.
2. Reuse `Base`, `TimestampMixin`, and `CRUD` before creating parallel abstractions.
3. Keep generic infrastructure in `system`; move business-specific logic to the owning module.
4. Update module documentation when shared behavior changes.
5. If the work adds configurable behavior, reflect it in `app/core/config.py`, not only in docs or `.env.example`.

This module should stay small, boring, reusable, and dependable.
