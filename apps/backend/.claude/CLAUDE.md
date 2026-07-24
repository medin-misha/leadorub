# Leadorub Backend

This section contains information about the Leadorub backend.

# Template Documentation and Instructions for Agents

This repository is a modular FastAPI backend template designed for high performance, module isolation, and scalability. All agents working with this codebase must strictly follow the rules below.

## Technology Stack

* **Runtime**: Python 3.11+, with `uv` as the mandatory package manager for dependency synchronization.
* **Web framework**: FastAPI, Pydantic v2 for validation, and Pydantic Settings for configuration.
* **Database**: PostgreSQL with asynchronous SQLAlchemy 2.0 and the `asyncpg` driver.
* **Migrations**: Alembic configured for asynchronous connections.
* **Storage**: S3-compatible storage, such as MinIO or AWS S3, implemented through `aiobotocore` in `file_module`.
* **Message broker**: RabbitMQ over AMQP through `aio-pika` in `rmq_module`.
* **Deferred tasks**: Deferred tasks are implemented with TaskIQ in `taskiq_module`.

## Project Structure and Architecture Rules

The project follows a strict modular architecture. There are three levels of responsibility:

1. **Application core (`app/core/`)** — global settings, database engine creation, and security primitives.
2. **Lifecycle orchestration (`app/lifecycle.py`)** — manages the startup and shutdown of shared external connections. Do not place lifecycle code directly in `main.py`.
3. **Modules (`app/modules/`)** — isolated domains containing their own APIs, models, schemas, and services.

### Main File Structure

```text
backend/
├── alembic/                  # Database migration versions
├── app/                      # Application source code
│   ├── api/
│   │   └── router.py         # Main APIRouter that includes all module routers
│   ├── core/                 # Global settings and process-level primitives
│   │   ├── config.py         # Settings loader using pydantic-settings
│   │   ├── database.py       # Async SQLAlchemy engine and session factory
│   │   └── security.py       # Authentication and encryption helper functions
│   ├── lifecycle.py          # Unified startup and shutdown orchestration
│   └── modules/              # Built-in and feature-specific business modules
│       ├── system/           # Base database model, generic CRUD, and health checks
│       ├── rmq_module/       # RabbitMQ publisher, consumer registry, and lifecycle
│       ├── file_module/      # S3/MinIO file storage and PostgreSQL metadata synchronization
│       └── taskiq_module/    # TaskIQ broker, scheduler, and deferred/cron task discovery
├── main.py                   # Main FastAPI entry point
├── pyproject.toml            # Project metadata and dependencies
└── uv.lock                   # Dependency tree lockfile
```

## Built-In Infrastructure Modules

The template provides four built-in modules in `app/modules/`. Under no circumstances may these modules be duplicated or bypassed.

### 1. System Module (`app/modules/system/CLAUDE.md`)

Provides the core model architecture and database interaction patterns.

### 2. File Module (`app/modules/file_module/CLAUDE.md`)

Manages the file storage pipeline.

### 3. RMQ Module (`app/modules/rmq_module/CLAUDE.md`)

Acts as the central communication channel for RabbitMQ.

### 4. TaskIQ Module (`app/modules/taskiq_module/CLAUDE.md`)

Scheduled Tasks Module.

## Guide for Implementing New Feature Modules (`./MODULES.md`)

## Strict Coding Rules for AI Agents

* **Preserve comments** — do not remove or modify existing comments, annotations, or docstrings unless explicitly asked to do so.

* **Do not create database sessions directly** — never manually instantiate a database session or engine inside business logic or API endpoints. Always use dependency injection: `Depends(database.get_session)`.

  **The only permitted exception:** RMQ consumer handlers run outside a FastAPI request, so `Depends` is unavailable to them. They open a session directly through `database.sessionmaker()` and manage `commit` and `rollback` themselves. The reference implementation is located in `chat_module/services/consumer_handler.py`. It is the backend’s first RMQ consumer and uses the `telegram_support_in` queue.

* **Transactional consistency** — database operations inside services must use the transaction rollback safety mechanisms already built into the CRUD operations in `app/modules/system`. Never publish a message that references data from the current uncommitted transaction. Enqueue it through the RMQ outbox.

* **Broker abstraction** — never import `aio-pika` or `pika` directly inside business modules. All message broker interactions must use `rmq_publisher` and `register_consumer`.

* **No hardcoded secrets** — secrets, credentials, access keys, and passwords must never be committed to the repository. Always use the `settings` object from `app/core/config.py`, which loads values from `.env`.

* **Package management** — use only `uv add <package>` and `uv sync` to modify dependencies. Do not use `pip` or `poetry`.
