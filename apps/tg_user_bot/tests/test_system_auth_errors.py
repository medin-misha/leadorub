import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.modules.system.auth.cache import auth_cache
from app.modules.system.auth.service import (
    AuthenticationFlowError,
    ensure_authenticated,
)
from app.modules.system.client import (
    BackendClient,
    BackendUnavailableError,
    BackendUnexpectedResponseError,
    BackendUserNotFoundError,
)
from app.modules.system.schemas import TelegramUserRead


class _FakeResponse:
    def __init__(self, status: int, payload=None, text: str = "") -> None:
        self.status = status
        self._payload = payload
        self._text = text

    async def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload

    async def text(self) -> str:
        return self._text


class _ResponseContext:
    def __init__(self, response=None, error: Exception | None = None) -> None:
        self._response = response
        self._error = error

    async def __aenter__(self):
        if self._error is not None:
            raise self._error
        return self._response

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSession:
    def __init__(self, response=None, error: Exception | None = None) -> None:
        self._response = response
        self._error = error

    def request(self, **kwargs):
        return _ResponseContext(response=self._response, error=self._error)


def _build_backend_user(telegram_id: int) -> TelegramUserRead:
    payload = {
        "id": 42,
        "telegram_id": telegram_id,
        "username": "tester",
        "first_name": "Test",
        "last_name": "User",
        "is_blocket_bot": False,
        "language_code": "en",
        "created_at": "2026-05-07T10:00:00Z",
        "updated_at": "2026-05-07T10:00:00Z",
        "user_profile": None,
        "user_stats": {
            "id": 7,
            "telegram_user_id": 42,
            "last_seen_at": "2026-05-07T10:00:00Z",
            "source": None,
            "state": None,
            "created_at": "2026-05-07T10:00:00Z",
            "updated_at": "2026-05-07T10:00:00Z",
        },
    }
    return TelegramUserRead.model_validate(payload)


class BackendClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_request_timeout_maps_to_backend_unavailable(self) -> None:
        client = BackendClient(
            session=_FakeSession(error=asyncio.TimeoutError()),
            base_url="https://example.com/api",
        )

        with self.assertRaises(BackendUnavailableError):
            await client._request(
                method="POST",
                path="/telegram/login",
                json_payload={"telegram_id": 1},
            )

    async def test_login_404_maps_to_backend_user_not_found(self) -> None:
        client = BackendClient(
            session=_FakeSession(response=_FakeResponse(status=404, text="missing")),
            base_url="https://example.com/api",
        )

        with self.assertRaises(BackendUserNotFoundError):
            await client.login_telegram_user(1)

    async def test_create_404_maps_to_backend_unexpected_response(self) -> None:
        client = BackendClient(
            session=_FakeSession(response=_FakeResponse(status=404, text="missing")),
            base_url="https://example.com/api",
        )

        with self.assertRaises(BackendUnexpectedResponseError):
            await client.create_telegram_user(
                SimpleNamespace(
                    model_dump=lambda **kwargs: {"telegram_user": {"telegram_id": 1}}
                )
            )

    async def test_server_error_maps_to_backend_unavailable(self) -> None:
        client = BackendClient(
            session=_FakeSession(response=_FakeResponse(status=503, text="down")),
            base_url="https://example.com/api",
        )

        with self.assertRaises(BackendUnavailableError):
            await client.login_telegram_user(1)


class EnsureAuthenticatedTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        auth_cache.clear()

    def tearDown(self) -> None:
        auth_cache.clear()

    async def test_second_login_404_becomes_authentication_flow_error(self) -> None:
        telegram_user = SimpleNamespace(
            id=99,
            username="tester",
            first_name="Test",
            last_name="User",
            is_bot=False,
            language_code="en",
        )
        client = SimpleNamespace(
            login_telegram_user=unittest.mock.AsyncMock(
                side_effect=[
                    BackendUserNotFoundError("missing"),
                    BackendUserNotFoundError("missing"),
                ]
            ),
            create_telegram_user=unittest.mock.AsyncMock(
                return_value=_build_backend_user(99)
            ),
        )

        with patch(
            "app.modules.system.auth.service.get_backend_client", return_value=client
        ):
            with self.assertRaises(AuthenticationFlowError):
                await ensure_authenticated(telegram_user, no_cache=True)

    async def test_backend_unavailable_propagates_unchanged(self) -> None:
        telegram_user = SimpleNamespace(
            id=100,
            username="tester",
            first_name="Test",
            last_name="User",
            is_bot=False,
            language_code="en",
        )
        client = SimpleNamespace(
            login_telegram_user=unittest.mock.AsyncMock(
                side_effect=BackendUnavailableError("timeout")
            ),
            create_telegram_user=unittest.mock.AsyncMock(),
        )

        with patch(
            "app.modules.system.auth.service.get_backend_client", return_value=client
        ):
            with self.assertRaises(BackendUnavailableError):
                await ensure_authenticated(telegram_user, no_cache=True)
