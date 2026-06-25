import unittest
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.types import ReactionTypeEmoji

from app.modules.rmq_module import rmq_publisher
from app.modules.system.auth import decorators
from app.modules.support_module import handlers
from app.modules.support_module.states import SupportStates


class SupportMessageTests(unittest.IsolatedAsyncioTestCase):
    def _message(self) -> MagicMock:
        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = 555
        message.text = "help me"
        message.message_id = 42
        message.react = AsyncMock()
        message.answer = AsyncMock()
        return message

    async def test_publishes_then_reacts_in_order(self) -> None:
        message = self._message()
        calls: list[str] = []
        message.react.side_effect = lambda *a, **k: calls.append("react")

        with patch.object(
            rmq_publisher,
            "publish",
            AsyncMock(side_effect=lambda **k: calls.append("publish")),
        ) as publish:
            await handlers.support_message(message)

        publish.assert_awaited_once()
        kwargs = publish.await_args.kwargs
        self.assertEqual(kwargs["queue_name"], "telegram_support_in")
        self.assertEqual(kwargs["routing_key"], "telegram_support_in")
        self.assertEqual(kwargs["exchange_name"], "app.events")
        self.assertEqual(
            kwargs["payload"],
            {"telegram_id": 555, "text": "help me", "tg_message_id": 42},
        )

        # 👀 ставится строго ПОСЛЕ публикации.
        message.react.assert_awaited_once()
        reaction = message.react.await_args.args[0]
        self.assertIsInstance(reaction[0], ReactionTypeEmoji)
        self.assertEqual(reaction[0].emoji, "👀")
        self.assertEqual(calls, ["publish", "react"])

    async def test_publish_failure_skips_reaction(self) -> None:
        message = self._message()
        with patch.object(
            rmq_publisher, "publish", AsyncMock(side_effect=RuntimeError("broker down"))
        ):
            await handlers.support_message(message)

        message.react.assert_not_awaited()
        message.answer.assert_awaited_once()


class SupportExitTests(unittest.IsolatedAsyncioTestCase):
    async def test_stop_command_clears_state(self) -> None:
        message = MagicMock()
        message.answer = AsyncMock()
        state = AsyncMock()
        await handlers.support_stop(message, state)
        state.clear.assert_awaited_once()
        message.answer.assert_awaited_once()

    async def test_callback_clears_state(self) -> None:
        query = MagicMock()
        query.answer = AsyncMock()
        query.message.answer = AsyncMock()
        state = AsyncMock()
        await handlers.support_stop_callback(query, state)
        state.clear.assert_awaited_once()
        query.answer.assert_awaited_once()


class SupportMediaTests(unittest.IsolatedAsyncioTestCase):
    def _doc_message(self, size: int = 1000) -> MagicMock:
        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = 555
        message.message_id = 42
        message.caption = "look"
        message.document = MagicMock(
            file_name="report.pdf", mime_type="application/pdf", file_size=size
        )
        message.bot = MagicMock()
        message.bot.download = AsyncMock(return_value=BytesIO(b"PDFDATA"))
        message.react = AsyncMock()
        message.answer = AsyncMock()
        return message

    async def test_document_uploads_and_reacts(self) -> None:
        message = self._doc_message()
        with patch.object(handlers, "upload_inbound_media", AsyncMock()) as upload:
            await handlers.support_document(message)

        upload.assert_awaited_once()
        kwargs = upload.await_args.kwargs
        self.assertEqual(kwargs["telegram_id"], 555)
        self.assertEqual(kwargs["filename"], "report.pdf")
        self.assertEqual(kwargs["content_type"], "application/pdf")
        self.assertEqual(kwargs["caption"], "look")
        self.assertEqual(kwargs["data"], b"PDFDATA")
        message.react.assert_awaited_once()

    async def test_oversize_document_rejected_before_download(self) -> None:
        message = self._doc_message(size=20 * 1024 * 1024)
        with patch.object(handlers, "upload_inbound_media", AsyncMock()) as upload:
            await handlers.support_document(message)

        message.bot.download.assert_not_awaited()
        upload.assert_not_awaited()
        message.react.assert_not_awaited()
        message.answer.assert_awaited_once()

    async def test_upload_failure_skips_reaction(self) -> None:
        message = self._doc_message()
        with patch.object(
            handlers,
            "upload_inbound_media",
            AsyncMock(side_effect=RuntimeError("boom")),
        ):
            await handlers.support_document(message)

        message.react.assert_not_awaited()
        message.answer.assert_awaited_once()


class SupportStartTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_sets_active_state(self) -> None:
        message = MagicMock()
        message.from_user = MagicMock()
        message.answer = AsyncMock()
        state = AsyncMock()
        # Обходим backend-аутентификацию в login_required.
        with patch.object(
            decorators, "ensure_authenticated", AsyncMock(return_value=MagicMock())
        ):
            await handlers.support_start(message, state)
        state.set_state.assert_awaited_once_with(SupportStates.active)


if __name__ == "__main__":
    unittest.main()
