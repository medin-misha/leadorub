import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import parse_qsl


def parse_telegram_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int,
    now: int | None = None,
) -> dict[str, Any] | None:
    """Проверяет подпись и срок жизни Telegram WebApp initData.

    Алгоритм соответствует официальной документации Telegram:
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app
    """
    if not init_data or not bot_token:
        return False

    try:
        # Парсим query-строку в словарь
        parsed_data = dict(parse_qsl(init_data, keep_blank_values=True))
    except Exception:
        return False

    if "hash" not in parsed_data:
        return False

    received_hash = parsed_data.pop("hash")

    # Сортируем параметры по алфавиту и соединяем через '\n'
    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(parsed_data.items())
    )

    # Шаг 1: Секретный ключ вычисляется как HMAC-SHA256 от токена бота с ключом "WebAppData"
    secret_key = hmac.new(
        b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256
    ).digest()

    # Шаг 2: Хэш вычисляется как HMAC-SHA256 от data_check_string с секретным ключом
    computed_hash = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    try:
        auth_date = int(parsed_data["auth_date"])
    except (KeyError, TypeError, ValueError):
        return None

    current_time = int(time.time()) if now is None else now
    # Небольшой допуск покрывает рассинхронизацию часов, но не позволяет
    # использовать initData, выпущенные заметно в будущем.
    if auth_date > current_time + 30 or current_time - auth_date > max_age_seconds:
        return None

    try:
        user = json.loads(parsed_data["user"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(user, dict):
        return None

    return {**parsed_data, "auth_date": auth_date, "user": user}


def validate_telegram_init_data(init_data: str, bot_token: str) -> bool:
    """Проверяет подпись initData без ограничения срока жизни.

    Оставлено для обратной совместимости. В HTTP-эндпоинтах следует использовать
    ``parse_telegram_init_data`` с конечным ``max_age_seconds``.
    """
    return (
        parse_telegram_init_data(
            init_data,
            bot_token,
            max_age_seconds=2**63 - 1,
        )
        is not None
    )
