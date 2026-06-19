# Project Context

This section contains information about the specific business application built on top of this template.

## Service Description
*The agent should look at the primary `README.md` under "Контекст проекта" for the actual business goals, key features, and environments of the service currently being built. Do not hardcode feature lists in this file.*

---

# Template Documentation and Agent Instructions

This repository is a modular FastAPI backend template designed for high performance, modular isolation, and scalability. All agents working in this codebase must strictly adhere to the guidelines below.

## Technology Stack

- **Runtime**: Python 3.11+, package manager `uv` (mandatory for dependency sync).
- **Web Framework**: FastAPI, Pydantic v2 (validation), Pydantic Settings (configuration).
- **Database**: PostgreSQL, async SQLAlchemy 2.0 (asyncpg driver).
- **Migrations**: Alembic (configured for async connection).
- **Storage**: S3-compatible storage (MinIO / AWS S3) via `aiobotocore`.
- **Message Broker**: RabbitMQ (AMQP) via `aio-pika`.

---

## Project Structure and Architecture Rules

We enforce a strict modular architecture. There are three levels of responsibility:

1. **Application Core (`app/core/`)** — Global settings, database engine creation, security primitives.
2. **Lifecycle Orchestration (`app/lifecycle.py`)** — Handles startup/shutdown of shared external connections (S3, RabbitMQ workers). Do not put lifecycle code directly inside `main.py`.
3. **Built-in Modules (`app/modules/`)** — Isolated domains containing their own APIs, models, schemas, and services.

### Core File Structure

```text
fastapi_template/
├── alembic/                  # Database migration versions
├── app/                      # Application source code
│   ├── api/
│   │   └── router.py         # Main APIRouter including all module routers
│   ├── core/                 # Global settings & process-level primitives
│   │   ├── config.py         # Settings loader using pydantic-settings
│   │   ├── database.py       # Async SQLAlchemy engine & session factory
│   │   └── security.py       # Helper functions for authentication & encryption
│   ├── lifecycle.py          # Unified startup/shutdown orchestration
│   └── modules/              # Built-in and feature business modules
│       ├── system/           # Core database model class, generic CRUD, & health checks
│       ├── rmq_module/       # RabbitMQ publisher, consumer registry & lifecycle
│       └── file_module/      # S3/MinIO file storage & PostgreSQL metadata sync
├── main.py                   # Main FastAPI entry point
├── pyproject.toml            # Project metadata & dependencies
└── uv.lock                   # Lockfile for dependency tree
```

### Module Layout Rule

Every module under `app/modules/` must follow this standardized directory structure:

```text
app/modules/module_name/
├── handlers.py               # API Router and endpoint functions (routers)
├── models/                   # SQLAlchemy ORM models
├── schemas/                  # Pydantic models (DTOs)
├── services/                 # Core business logic (service layer)
├── utils/                    # Module-specific helper functions
├── AGENTS.md/CLAUDE.md       # Local module instructions for AI agents (Always in English)
└── README.md                 # Local module documentation (Always in Russian)
```

---

## Built-In Infrastructure Modules

The template provides three built-in modules in `app/modules/`. Under no circumstances should these modules be duplicated or bypassed.

### 1. System Module (`app/modules/system`)
Provides core model architecture and database patterns:
- **Base Model** (`Base` in `models/base.py`): Sets the primary key `id: Mapped[int]` for all models in the system.
- **Timestamp Mixin** (`TimestampMixin` in `models/base.py`): Adds `created_at` and `updated_at` timestamps managed at the database level.
- **Generic CRUD Service** (`CRUD` in `services/crud.py`): Implements standardized methods for creating (`create`, `bulk_create`), reading (`get` with pagination, sorting, text search, and exact field filtering), patching (`patch`), and deleting (`delete`) models.
- **Database Error Handler** (`DBErrorHandler` in `services/errors.py`): Captures SQLAlchemy exceptions, executes necessary rollbacks, and maps them to HTTPExceptions (e.g., translating user constraint errors to 400 Bad Request and database connection losses to 503 Service Unavailable).
- **Health Checks**: Provides endpoints `GET /api/system/health` and `GET /api/system/health/db`.

### 2. File Module (`app/modules/file_module`)
Handles file storage pipeline:
- **S3 Storage Client** (`S3Client` in `services/s3_client.py`): Asynchronously streams files directly to S3-compatible buckets (MinIO) using `SpooledTemporaryFile` to prevent high memory allocation. Filenames are randomized via UUID.
- **Metadata Management**: Stores file metadata (original filename, public link, comment) in the `files` PostgreSQL table.
- **API Endpoints**:
  - `POST /api/files/` — Uploads a file. If the PostgreSQL transaction fails, the file is automatically purged from the S3 bucket to prevent orphaned objects.
  - `GET /api/files/{id}` — Downloads the file as a `StreamingResponse` with correct character encoding support in the `Content-Disposition` header.
  - `DELETE /api/files/{id}` — Deletes the database record transactionally first, then removes the corresponding S3 object (best-effort).

### 3. RMQ Module (`app/modules/rmq_module`)
Acts as the central communication channel for RabbitMQ:
- **Resiliency**: If `rabbitmq_enabled=false`, the system completely skips broker initialization during startup, allowing standalone operation.
- **Event Publisher** (`RMQPublisher`): Publishes structured events wrapped in a standard event envelope containing `event`, `payload`, `message_id`, `correlation_id`, `timestamp`, and `source`.
- **Consumer Registry** (`register_consumer`): Provides a decorator to register listener methods directly within business modules. Registered listeners are launched inside background tasks at startup if `rabbitmq_consumer_enabled=true`.
- **Debug Route Support**: Provides `POST /api/rmq/publish` and `POST /api/rmq/consume` endpoints under `debug=true` and `rabbitmq_debug_endpoints_enabled=true` configuration flags.

---

## Guide for Implementing New Feature Modules

When tasked with adding a new feature or domain, follow this exact checklist:

> [!IMPORTANT]
> If the new module is packaged as an independent service with its own `Dockerfile`, a `.dockerignore` file **must** be created at its root directory to exclude `.venv/`, `.git/`, local `.env` files, and `__pycache__/` to avoid Docker build context pollution and virtual environment conflicts.

1. **Generate the Module Directory**: Create the folder structure under `app/modules/<new_module>/`.
2. **Define Database Models**: Write SQLAlchemy models inside `models/`, inheriting from `Base` and optionally `TimestampMixin`. You can also use other system mixins from `app/modules/system/`.
3. **Register Models for Alembic**: Import the new model classes inside `app/modules/__init__.py`. This is critical; otherwise, Alembic autogeneration will not discover your new tables.
4. **Implement Schemas**: Create Pydantic input and output DTOs inside `schemas/`.
5. **Write Business Logic**: Keep business logic inside `services/`. Endpoints in `handlers.py` must only validate, format, and delegate execution.
6. **Expose APIRouter**: Setup an `APIRouter` inside `handlers.py` with an appropriate prefix and tags.
7. **Include Router globally**: Import and register the new router in [app/api/router.py](app/api/router.py).
8. **Generate and Run Migrations**: Run the following commands:
   ```bash
   uv run alembic revision --autogenerate -m "add <new_module> models"
   uv run alembic upgrade head
   ```
9. **Configure Environment Variables**: If your module introduces new settings, define them inside the `MainSettings` class in `app/core/config.py` and document them inside `.env.example`.

---

## Strict Coding Guidelines for AI Agents

- **Maintain Comments**: Preserve all comments, annotations, and docstrings unless explicitly asked to modify them.
- **No Direct Database Sessions**: Never instantiate a database session or engine manually inside business logic or API endpoints. Always use the dependency injection pattern (`Depends(database.get_session)`).
- **Transactional Consistency**: Database operations inside services must rely on the transactional rollback safety already integrated into `app/modules/system` CRUD operations.
- **Broker Abstraction**: Never import `aio-pika` or `pika` directly inside business modules. All message broker interactions must utilize `rmq_publisher` and `register_consumer`.
- **No Hardcoded Secrets**: Secrets, credentials, access keys, or passwords must never be committed. Always use the `settings` config projection in `app/core/config.py` loaded from `.env`.
- **Package Management**: Only use `uv add <package>` and `uv sync` to modify dependencies. Do not use `pip` or `poetry`.
