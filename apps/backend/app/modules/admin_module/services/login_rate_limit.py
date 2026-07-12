import asyncio
import hashlib
import ipaddress
import math
import time
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Request


@dataclass(slots=True)
class _Window:
    attempts: int
    expires_at: float


class LoginRateLimiter:
    """Ограничивает попытки входа в пределах одного процесса backend."""

    def __init__(
        self,
        *,
        attempts: int,
        ip_attempts: int,
        window_seconds: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._attempts = attempts
        self._ip_attempts = ip_attempts
        self._window_seconds = window_seconds
        self._clock = clock
        self._windows: dict[str, _Window] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, *, client_ip: str, username: str) -> int | None:
        """Резервирует попытку и возвращает Retry-After, если лимит исчерпан."""

        now = self._clock()
        keys = self._keys(client_ip=client_ip, username=username)
        async with self._lock:
            self._remove_expired(now)
            retry_after = self._retry_after_if_limited(keys, now)
            if retry_after is not None:
                return retry_after

            for key, _ in keys:
                window = self._windows.get(key)
                if window is None:
                    self._windows[key] = _Window(1, now + self._window_seconds)
                else:
                    window.attempts += 1
        return None

    async def reset(self, *, client_ip: str, username: str) -> None:
        """Успешный вход сбрасывает оба счётчика для клиента."""

        async with self._lock:
            for key, _ in self._keys(client_ip=client_ip, username=username):
                self._windows.pop(key, None)

    def _keys(self, *, client_ip: str, username: str) -> tuple[tuple[str, int], ...]:
        # Username хешируется, чтобы limiter не удерживал учётные данные в памяти.
        username_hash = hashlib.sha256(username.casefold().encode()).hexdigest()
        return (
            (f"ip:{client_ip}", self._ip_attempts),
            (f"login:{client_ip}:{username_hash}", self._attempts),
        )

    def _retry_after_if_limited(
        self, keys: tuple[tuple[str, int], ...], now: float
    ) -> int | None:
        waits = [
            math.ceil(window.expires_at - now)
            for key, limit in keys
            if (window := self._windows.get(key)) is not None
            and window.attempts >= limit
        ]
        return max(1, max(waits)) if waits else None

    def _remove_expired(self, now: float) -> None:
        expired = [key for key, window in self._windows.items() if window.expires_at <= now]
        for key in expired:
            self._windows.pop(key, None)


def get_client_ip(request: Request, trusted_proxy_cidrs: list[str]) -> str:
    """Возвращает исходный IP, доверяя proxy-заголовку только от trusted peer."""

    peer = request.client.host if request.client else "unknown"
    try:
        peer_address = ipaddress.ip_address(peer)
        trusted_networks = [ipaddress.ip_network(cidr) for cidr in trusted_proxy_cidrs]
    except ValueError:
        return peer

    if not any(peer_address in network for network in trusted_networks):
        return peer

    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded:
        return peer

    candidates: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for value in forwarded.split(","):
        try:
            candidates.append(ipaddress.ip_address(value.strip()))
        except ValueError:
            return peer

    # Идём от ближайшего proxy к клиенту и пропускаем только доверенные узлы.
    for candidate in reversed(candidates):
        if not any(candidate in network for network in trusted_networks):
            return str(candidate)
    return str(candidates[0]) if candidates else peer
