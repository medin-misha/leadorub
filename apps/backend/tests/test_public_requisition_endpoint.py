import hashlib
import hmac
import json
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlencode

from fastapi import HTTPException

from app.modules.requisition import handlers


BOT_TOKEN = "123456:test-token"


def build_init_data(*, auth_date: int) -> str:
    data = {
        "auth_date": str(auth_date),
        "user": json.dumps({"id": 987654321}, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    data["hash"] = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    return urlencode(data)


class PublicRequisitionEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_verified_user_id_is_used_for_requisition(self) -> None:
        data = handlers.RequisitionPublicCreate(
            name="Михаил",
            phone="",
            description="Хочу стать сильнее",
        )
        session = MagicMock()
        expected = MagicMock()

        with (
            patch.object(handlers.settings, "user_bot", BOT_TOKEN),
            patch.object(handlers.settings, "telegram_init_data_max_age_seconds", 3600),
            patch.object(
                handlers,
                "create_requisition_service",
                AsyncMock(return_value=expected),
            ) as service,
        ):
            result = await handlers.create_public_requisition(
                data=data,
                session=session,
                telegram_init_data=build_init_data(auth_date=int(time.time())),
            )

        self.assertIs(result, expected)
        requisition_data = service.await_args.kwargs["data"]
        self.assertEqual(requisition_data.telegram_id, 987654321)
        self.assertEqual(requisition_data.payload["source"], "miniapp")

    async def test_invalid_init_data_is_rejected(self) -> None:
        data = handlers.RequisitionPublicCreate(name="Михаил", phone="")

        with patch.object(handlers.settings, "user_bot", BOT_TOKEN):
            with self.assertRaises(HTTPException) as raised:
                await handlers.create_public_requisition(
                    data=data,
                    session=MagicMock(),
                    telegram_init_data="auth_date=1&hash=invalid",
                )

        self.assertEqual(raised.exception.status_code, 401)

    async def test_missing_bot_token_fails_closed(self) -> None:
        data = handlers.RequisitionPublicCreate(name="Михаил", phone="")

        with patch.object(handlers.settings, "user_bot", None):
            with self.assertRaises(HTTPException) as raised:
                await handlers.create_public_requisition(
                    data=data,
                    session=MagicMock(),
                    telegram_init_data=build_init_data(auth_date=int(time.time())),
                )

        self.assertEqual(raised.exception.status_code, 503)
