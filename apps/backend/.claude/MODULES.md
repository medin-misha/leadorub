## New Feature Module Implementation Guide

### Module structure rule

Every module inside `app/modules/` must follow this standard structure:

```text
app/modules/module_name/
├── handlers.py               # API Router and endpoint functions
├── models/                   # SQLAlchemy ORM models
├── schemas/                  # Pydantic models and DTOs
├── services/                 # Core business logic — the service layer
├── utils/                    # Module-specific helper functions
├── CLAUDE.md                 # Local AI-agent instructions — always in English
└── API.md                    # Module API documentation — always in English
```

### How to create a new module?

1. Create the module folder in `modules/` following the standard structure above.
2. Create `CLAUDE.md` and `API.md`, fill them in, and link them with a markdown link `[API contracts](API.md)`.
3. Define the database models based on the system module's `Base` and its mixins.
4. Register the new models in `app/modules/__init__.py`. This is critical: without the import, Alembic autogenerate will not detect the new tables.
5. Create and apply the migrations. Never write migrations by hand — generate them with `uv run alembic revision --autogenerate -m "<comment>"`, then `uv run alembic upgrade head`.
6. Implement the Pydantic schemas in the module's `schemas/`.
7. Implement the business logic in `services/`, reusing `system.CRUD`.
8. Create the routers in `handlers.py` per `API.md`.
9. Register the router in `app/api/router.py`.
10. If the module introduces new environment variables, add them to the `MainSettings` class in `app/core/config.py` and document them in `.env.example`.

When adding a new feature or domain, follow this checklist without deviation.
