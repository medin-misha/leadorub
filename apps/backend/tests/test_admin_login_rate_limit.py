import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from starlette.requests import Request

from app.modules.admin_module import handlers
from app.modules.admin_module.schemas import LoginRequest
from app.modules.admin_module.services.login_rate_limit import (
    LoginRateLimiter,
    get_client_ip,
)


def make_request(
    *, peer: str = "203.0.113.10", forwarded_for: str | None = None
) -> Request:
    headers = []
    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode()))
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/auth/login",
            "headers": headers,
            "client": (peer, 12345),
        }
    )


class ClientIpTests(unittest.TestCase):
    def test_forwarded_for_from_untrusted_peer_is_ignored(self) -> None:
        request = make_request(peer="198.51.100.20", forwarded_for="1.2.3.4")

        self.assertEqual(get_client_ip(request, ["172.16.0.0/12"]), "198.51.100.20")

    def test_first_untrusted_address_is_read_behind_trusted_proxies(self) -> None:
        request = make_request(
            peer="172.18.0.5",
            forwarded_for="203.0.113.10, 172.18.0.2",
        )

        self.assertEqual(get_client_ip(request, ["172.16.0.0/12"]), "203.0.113.10")


class LoginRateLimitEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.now = 100.0
        self.limiter = LoginRateLimiter(
            attempts=2,
            ip_attempts=10,
            window_seconds=60,
            clock=lambda: self.now,
        )
        self.request = make_request()
        self.data = LoginRequest(username="admin", password="secret")

    async def test_successful_login_resets_failed_attempts(self) -> None:
        admin = MagicMock(id=7)
        with (
            patch.object(handlers, "login_rate_limiter", self.limiter),
            patch.object(handlers, "authenticate", AsyncMock(side_effect=[None, admin, None, None])),
            patch.object(handlers, "create_access_token", return_value="jwt"),
            patch.object(handlers.settings, "admin_login_trusted_proxy_cidrs", []),
        ):
            with self.assertRaises(HTTPException) as first_failure:
                await handlers.login(self.data, MagicMock(), self.request)
            response = await handlers.login(self.data, MagicMock(), self.request)
            with self.assertRaises(HTTPException):
                await handlers.login(self.data, MagicMock(), self.request)
            with self.assertRaises(HTTPException) as second_failure:
                await handlers.login(self.data, MagicMock(), self.request)

        self.assertEqual(first_failure.exception.status_code, 401)
        self.assertEqual(response.access_token, "jwt")
        self.assertEqual(second_failure.exception.status_code, 401)

    async def test_limit_returns_429_and_retry_after(self) -> None:
        authenticate = AsyncMock(return_value=None)
        with (
            patch.object(handlers, "login_rate_limiter", self.limiter),
            patch.object(handlers, "authenticate", authenticate),
            patch.object(handlers.settings, "admin_login_trusted_proxy_cidrs", []),
        ):
            for _ in range(2):
                with self.assertRaises(HTTPException) as failure:
                    await handlers.login(self.data, MagicMock(), self.request)
                self.assertEqual(failure.exception.status_code, 401)

            with self.assertRaises(HTTPException) as limited:
                await handlers.login(self.data, MagicMock(), self.request)

        self.assertEqual(limited.exception.status_code, 429)
        self.assertEqual(limited.exception.headers["Retry-After"], "60")
        self.assertEqual(authenticate.await_count, 2)

    async def test_expired_window_allows_attempts_again(self) -> None:
        for _ in range(2):
            self.assertIsNone(
                await self.limiter.acquire(client_ip="203.0.113.10", username="admin")
            )
        self.assertEqual(
            await self.limiter.acquire(client_ip="203.0.113.10", username="admin"),
            60,
        )

        self.now += 60

        self.assertIsNone(
            await self.limiter.acquire(client_ip="203.0.113.10", username="admin")
        )


if __name__ == "__main__":
    unittest.main()
