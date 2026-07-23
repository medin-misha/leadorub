"""Тесты стартовой воронки DMCAGuardian (модуль persona)."""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Настройки процесса читаются на импорте модулей; тестам живой токен не нужен.
os.environ.setdefault("TOKEN", "123456:test-token")

from app.modules.persona import PERSONA_START_STATE, run_start_funnel  # noqa: E402
from app.modules.persona.messages import get_messages  # noqa: E402

# Лимиты Telegram Bot API: текст сообщения и подпись к медиа.
TELEGRAM_MESSAGE_LIMIT = 4096
TELEGRAM_CAPTION_LIMIT = 1024


class PersonaMessagesTests(unittest.TestCase):
    def test_welcome_fits_message_limit(self) -> None:
        self.assertLessEqual(len(get_messages()["welcome"]), TELEGRAM_MESSAGE_LIMIT)

    def test_video_caption_fits_caption_limit(self) -> None:
        self.assertLessEqual(
            len(get_messages()["video_caption"]), TELEGRAM_CAPTION_LIMIT
        )


class PersonaFunnelTests(unittest.IsolatedAsyncioTestCase):
    async def test_funnel_sends_chain_and_sets_state(self) -> None:
        """Цепочка /start: текст → PDF → видео с кнопками → state в backend.

        Пути к ассетам не подменяются: тест заодно проверяет, что файлы
        гайда и видео реально лежат в assets/.
        """

        message = MagicMock()
        message.from_user = MagicMock(id=42)
        message.answer = AsyncMock()
        message.answer_document = AsyncMock()
        message.answer_video = AsyncMock()

        backend_client = MagicMock()
        backend_client.set_user_state = AsyncMock()

        with (
            patch("app.modules.persona.service.asyncio.sleep", AsyncMock()),
            patch(
                "app.modules.system.client.get_backend_client",
                return_value=backend_client,
            ),
        ):
            await run_start_funnel(message)

        message.answer.assert_awaited_once()
        message.answer_document.assert_awaited_once()
        message.answer_video.assert_awaited_once()
        backend_client.set_user_state.assert_awaited_once_with(
            telegram_id=42, state=PERSONA_START_STATE
        )
