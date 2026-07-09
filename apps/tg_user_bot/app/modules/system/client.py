"""
HTTP-клиент для интеграции Telegram-бота с backend API.

Файл отвечает только за transport-layer: создание и закрытие `aiohttp`
сессии, выполнение запросов и преобразование ответов backend в локальные
схемы системного модуля.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiohttp import ClientError, ClientResponse, ClientSession, ClientTimeout

from .config import system_settings
from .schemas import (
    RequisitionCreatePayload,
    RequisitionRead,
    TelegramUserCreatePayload,
    TelegramUserLoginPayload,
    TelegramUserRead,
)

logger = logging.getLogger(__name__)


class BackendClientError(RuntimeError):
    """Базовая ошибка HTTP-клиента системного модуля."""


class BackendNotConfiguredError(BackendClientError):
    """Backend URL не настроен, а модуль пытается использовать auth API."""


class BackendUnavailableError(BackendClientError):
    """Backend недоступен по сети или вернул неожиданный транспортный сбой."""


class BackendUnexpectedResponseError(BackendClientError):
    """Backend ответил статусом, который модуль не умеет обработать штатно."""


class BackendUserNotFoundError(BackendClientError):
    """Backend не нашёл пользователя при попытке логина."""


class BackendClient:
    """Тонкий API-клиент поверх `aiohttp.ClientSession`."""

    def __init__(self, session: ClientSession, base_url: str) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")

    async def login_telegram_user(self, telegram_id: int) -> TelegramUserRead:
        """Запрашивает login пользователя по его Telegram ID."""

        payload = TelegramUserLoginPayload(telegram_id=telegram_id)
        response_data = await self._request(
            method="POST",
            path="/telegram/login",
            json_payload=payload.model_dump(mode="json"),
            not_found_is_user_absence=True,
        )
        return TelegramUserRead.model_validate(response_data)

    async def create_telegram_user(
        self,
        payload: TelegramUserCreatePayload,
    ) -> TelegramUserRead:
        """Регистрирует пользователя в backend и возвращает backend response."""

        response_data = await self._request(
            method="POST",
            path="/telegram/users",
            json_payload=payload.model_dump(mode="json", exclude_none=True),
        )
        return TelegramUserRead.model_validate(response_data)

    async def create_requisition(
        self,
        telegram_id: int,
        type_: str,
        payload: dict,
    ) -> RequisitionRead:
        """Отправляет заявку пользователя на бэкенд."""

        req_payload = RequisitionCreatePayload(
            telegram_id=telegram_id,
            type=type_,
            payload=payload,
        )
        response_data = await self._request(
            method="POST",
            path="/requisitions",
            json_payload=req_payload.model_dump(mode="json"),
        )
        return RequisitionRead.model_validate(response_data)

    async def _request(
        self,
        method: str,
        path: str,
        json_payload: dict[str, Any],
        *,
        not_found_is_user_absence: bool = False,
    ) -> dict[str, Any]:
        """Выполняет JSON-запрос к backend и нормализует базовые ошибки."""

        url = f"{self._base_url}{path}"

        try:
            async with self._session.request(
                method=method, url=url, json=json_payload
            ) as response:
                return await self._parse_response(
                    response,
                    not_found_is_user_absence=not_found_is_user_absence,
                )
        except BackendClientError:
            raise
        except (ClientError, asyncio.TimeoutError) as exc:
            raise BackendUnavailableError(f"Backend request failed: {exc}") from exc

    async def _parse_response(
        self,
        response: ClientResponse,
        *,
        not_found_is_user_absence: bool,
    ) -> dict[str, Any]:
        """Преобразует HTTP-ответ в словарь или бросает доменную ошибку."""

        if response.status == 404 and not_found_is_user_absence:
            raise BackendUserNotFoundError("Telegram user not found in backend.")

        if response.status >= 500:
            body = await response.text()
            raise BackendUnavailableError(
                f"Backend returned server error {response.status}: {body}"
            )

        if response.status >= 400:
            body = await response.text()
            raise BackendUnexpectedResponseError(
                f"Backend returned unexpected status {response.status}: {body}"
            )

        try:
            payload = await response.json()
        except Exception as exc:
            body = await response.text()
            raise BackendUnexpectedResponseError(
                f"Backend returned invalid JSON: {body}"
            ) from exc

        if not isinstance(payload, dict):
            raise BackendUnexpectedResponseError(
                "Backend JSON payload must be an object."
            )

        return payload


_backend_client: BackendClient | None = None


async def startup_backend_client() -> None:
    """Создаёт process-wide HTTP client для системного модуля, если backend настроен."""

    global _backend_client

    if _backend_client is not None:
        return

    base_url = system_settings.backend_api_base_url
    if not base_url:
        logger.warning("Backend URL is not configured; system auth API is disabled.")
        return

    timeout = ClientTimeout(total=system_settings.backend_request_timeout)
    # Сервисный токен уходит дефолтным заголовком на каждый запрос сессии —
    # один раз настроили, и оба вызова (/telegram/login, /telegram/users) уже
    # авторизованы на стороне backend (require_service / require_admin_or_service).
    headers: dict[str, str] = {}
    if system_settings.backend_service_token:
        headers["X-Service-Token"] = system_settings.backend_service_token
    else:
        logger.warning(
            "SERVICE_TOKEN is not configured; backend calls will be rejected (401)."
        )
    session = ClientSession(timeout=timeout, headers=headers or None)
    _backend_client = BackendClient(session=session, base_url=base_url)
    logger.info("System backend client initialized for %s", base_url)


async def shutdown_backend_client() -> None:
    """Закрывает process-wide HTTP client системного модуля."""

    global _backend_client

    if _backend_client is None:
        return

    await _backend_client._session.close()
    _backend_client = None


def get_backend_client() -> BackendClient:
    """Возвращает активный backend client или объяснимую ошибку конфигурации."""

    if _backend_client is None:
        if not system_settings.backend_api_base_url:
            raise BackendNotConfiguredError(
                "BACKEND_URL is not configured for system auth."
            )

        raise BackendUnavailableError("System backend client is not initialized.")

    return _backend_client
