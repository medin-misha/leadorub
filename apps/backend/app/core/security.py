"""
Process-level security primitives: хеширование паролей и работа с JWT.

Это слой `core`: он не зависит от модулей приложения, поэтому здесь только
чистые helper-функции. FastAPI-зависимости авторизации (извлечение токена из
запроса, загрузка администратора из БД) живут в `app/modules/admin_module`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


def hash_password(raw_password: str) -> str:
    """Хеширует пароль bcrypt'ом и возвращает строку для хранения в БД.

    bcrypt работает с байтами и не принимает пароли длиннее 72 байт — длину
    ограничиваем на уровне схем (`AdminCreate`/`AdminPatch`).
    """

    hashed = bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(raw_password: str, hashed_password: str) -> bool:
    """Проверяет пароль против сохранённого хеша. Любой сбой → False."""

    try:
        return bcrypt.checkpw(
            raw_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except ValueError:
        # Повреждённый/некорректный хеш не должен ронять процесс аутентификации.
        return False


def create_access_token(subject: int | str) -> str:
    """Создаёт подписанный access-JWT с `sub` и `exp`.

    `sub` приводим к строке: спецификация JWT и PyJWT требуют строкового
    subject (иначе при декодировании будет ошибка валидации).
    """

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload = {"sub": str(subject), "exp": expire}
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def decode_access_token(token: str) -> dict | None:
    """Декодирует и валидирует JWT. Возвращает payload или None при любой ошибке.

    Ловим базовый `PyJWTError`, который покрывает истёкший токен, неверную
    подпись и прочие проблемы — наружу отдаём единый None.
    """

    try:
        return jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError:
        return None
