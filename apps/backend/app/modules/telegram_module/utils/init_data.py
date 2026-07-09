import hashlib
import hmac
from urllib.parse import parse_qsl


def validate_telegram_init_data(init_data: str, bot_token: str) -> bool:
    """Проверяет подлинность строки initData, присланной Telegram WebApp.

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

    # Шаг 1: Секретный ключ вычисляется как HMAC-SHA256 от токена бота с ключом "WebAppsData"
    secret_key = hmac.new(
        b"WebAppsData", bot_token.encode("utf-8"), hashlib.sha256
    ).digest()

    # Шаг 2: Хэш вычисляется как HMAC-SHA256 от data_check_string с секретным ключом
    computed_hash = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    # Безопасное сравнение хэшей
    return hmac.compare_digest(computed_hash, received_hash)
