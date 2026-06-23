# Модуль admin_module

Аутентификация и авторизация администраторов backend.

## Зачем
- Модель `Admin` (`username`, `hashed_password`, `is_active`) — учётка для входа в `admin_miniapp`.
- Выдаёт один access-JWT при логине (без refresh-токена).
- Предоставляет FastAPI-гейты, которыми защищены чувствительные эндпоинты всего API.

## Структура
- `models/admin.py` — модель `Admin(Base, TimestampMixin)`, таблица `admin`.
- `schemas/auth.py` — `LoginRequest`, `TokenResponse`.
- `schemas/admin.py` — `AdminCreate`, `AdminPatch`, `AdminRead`. Пароль ограничен 72 байтами (лимит bcrypt).
- `services/auth.py` — `authenticate`, `bootstrap_admin`, `create/list/update/delete_admin`.
- `dependencies.py` — гейты авторизации.
- `handlers.py` — роутер `/auth`.

## Гейты авторизации
Импортируются из `app.modules.admin_module.dependencies`:
- `get_current_admin` / `require_admin` — доступ по Bearer-JWT, возвращает активного `Admin`.
  `is_active` проверяется в БД на каждом запросе → удаление/деактивация мгновенно отзывают доступ.
- `require_service` — заголовок `X-Service-Token` должен совпасть с `settings.service_token`.
  Fail-closed: если `service_token` не задан, отклоняются все запросы. Используется юзер-ботом.
- `require_admin_or_service` — проходит, если сработал любой из гейтов. Для эндпоинтов, которые
  дёргают и админка, и бот (например, `POST /telegram/users`, `GET /files/{id}`).

## Эндпоинты (`/api/auth`)
- `POST /login` — публичный. `{username, password}` → `{access_token, token_type}`. На неверные данные — общий 401.
- `GET /me` — текущий админ (нужен JWT).
- `GET /admins` — список (нужен JWT).
- `POST /admins` — создать (нужен JWT). 400 при дубле username.
- `PATCH /admins/{id}` — смена пароля / активности (нужен JWT). Нельзя деактивировать себя.
- `DELETE /admins/{id}` — удалить (нужен JWT). Нельзя удалить себя (гарантирует, что останется ≥1 админ).

## Bootstrap
`bootstrap_admin()` вызывается из `app/lifecycle.py` (lifespan), после применения миграций
(`docker-entrypoint.sh` гонит `alembic upgrade head`). Создаёт админа из
`settings.admin_username` / `settings.admin_password`, только если такого ещё нет
(идемпотентно, не затирает сменённый пароль).

## Переменные окружения (`infra/.env`, lowercase)
`admin_username`, `admin_password`, `jwt_secret_key` (обязателен), `jwt_algorithm` (HS256),
`jwt_access_token_expire_minutes` (720), `service_token`.
