import hashlib
import hmac
import json
import unittest
from urllib.parse import urlencode

from app.modules.telegram_module.utils import parse_telegram_init_data


BOT_TOKEN = "123456:test-token"
NOW = 1_750_000_000


def build_init_data(
    *,
    auth_date: int = NOW,
    user: object | None = None,
    bot_token: str = BOT_TOKEN,
) -> str:
    data = {
        "auth_date": str(auth_date),
        "query_id": "AAExample",
        "user": json.dumps(
            user if user is not None else {"id": 987654321, "first_name": "Михаил"},
            ensure_ascii=False,
            separators=(",", ":"),
        ),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    data["hash"] = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    return urlencode(data)


class TelegramInitDataTests(unittest.TestCase):
    def test_valid_data_is_parsed(self) -> None:
        result = parse_telegram_init_data(
            build_init_data(), BOT_TOKEN, max_age_seconds=3600, now=NOW
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["user"]["id"], 987654321)
        self.assertEqual(result["auth_date"], NOW)

    def test_tampered_data_is_rejected(self) -> None:
        init_data = build_init_data().replace("987654321", "111111111")

        result = parse_telegram_init_data(
            init_data, BOT_TOKEN, max_age_seconds=3600, now=NOW
        )

        self.assertIsNone(result)

    def test_expired_data_is_rejected(self) -> None:
        result = parse_telegram_init_data(
            build_init_data(auth_date=NOW - 3601),
            BOT_TOKEN,
            max_age_seconds=3600,
            now=NOW,
        )

        self.assertIsNone(result)

    def test_data_from_future_is_rejected(self) -> None:
        result = parse_telegram_init_data(
            build_init_data(auth_date=NOW + 31),
            BOT_TOKEN,
            max_age_seconds=3600,
            now=NOW,
        )

        self.assertIsNone(result)

    def test_non_object_user_is_rejected(self) -> None:
        result = parse_telegram_init_data(
            build_init_data(user="invalid"),
            BOT_TOKEN,
            max_age_seconds=3600,
            now=NOW,
        )

        self.assertIsNone(result)
