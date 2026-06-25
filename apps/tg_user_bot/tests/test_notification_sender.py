import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.types import (
    BufferedInputFile,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)

from app.modules.notification_module.schemas import (
    TelegramButton,
    TelegramNotification,
)
from app.modules.notification_module.services import sender


class BuildMarkupTests(unittest.TestCase):
    def test_inline_url_and_callback_one_per_row(self) -> None:
        buttons = [
            TelegramButton(text="A", url="http://a"),
            TelegramButton(text="B", callback_data="cb"),
        ]
        markup = sender.build_markup("INLINE", buttons)
        self.assertIsInstance(markup, InlineKeyboardMarkup)
        self.assertEqual(len(markup.inline_keyboard), 2)
        self.assertEqual(markup.inline_keyboard[0][0].url, "http://a")
        self.assertEqual(markup.inline_keyboard[1][0].callback_data, "cb")

    def test_reply_contact(self) -> None:
        buttons = [TelegramButton(text="c", requests_contect=True)]
        markup = sender.build_markup("REPLY", buttons)
        self.assertIsInstance(markup, ReplyKeyboardMarkup)
        self.assertTrue(markup.keyboard[0][0].request_contact)

    def test_none_without_buttons(self) -> None:
        self.assertIsNone(sender.build_markup(None, None))
        self.assertIsNone(sender.build_markup("INLINE", None))


class IsPhotoTests(unittest.TestCase):
    def test_image_vs_document(self) -> None:
        self.assertTrue(sender.is_photo("image/png"))
        self.assertFalse(sender.is_photo("application/pdf"))


class BroadcastTests(unittest.IsolatedAsyncioTestCase):
    async def test_text_broadcast_reaches_all_and_survives_one_failure(self) -> None:
        n = TelegramNotification.model_validate(
            {"chat_ids": [1, 2, 3], "message": "hi"}
        )
        fake_bot = MagicMock()
        fake_bot.send_message = AsyncMock(side_effect=[None, Exception("boom"), None])
        with patch.object(sender, "bot", fake_bot), patch("asyncio.sleep", AsyncMock()):
            await sender.send_notification(n)
        self.assertEqual(fake_bot.send_message.await_count, 3)

    async def test_file_broadcast_reuses_telegram_file_id(self) -> None:
        n = TelegramNotification.model_validate(
            {"chat_ids": [1, 2], "message": "cap", "file_id": 9}
        )
        first_msg = MagicMock()
        first_msg.photo = [MagicMock(file_id="TG123")]
        fake_bot = MagicMock()
        fake_bot.send_photo = AsyncMock(return_value=first_msg)
        with (
            patch.object(sender, "bot", fake_bot),
            patch.object(
                sender, "fetch_file", AsyncMock(return_value=(b"x", "image/png"))
            ),
            patch("asyncio.sleep", AsyncMock()),
        ):
            await sender.send_notification(n)
        self.assertEqual(fake_bot.send_photo.await_count, 2)
        # второй вызов переиспользует пойманный Telegram file_id (строку)
        self.assertEqual(
            fake_bot.send_photo.await_args_list[1].kwargs["photo"], "TG123"
        )

    async def test_text_broadcast_skips_already_claimed(self) -> None:
        # claim: True для 1 и 3, False для 2 (как будто 2-му уже слали).
        async def fake_claim(broadcast_id, chat_id):
            return chat_id != 2

        n = TelegramNotification.model_validate(
            {"chat_ids": [1, 2, 3], "message": "hi", "broadcast_id": "b1"}
        )
        fake_bot = MagicMock()
        fake_bot.send_message = AsyncMock()
        with (
            patch.object(
                sender.idempotency_store, "claim", AsyncMock(side_effect=fake_claim)
            ),
            patch.object(sender, "bot", fake_bot),
            patch("asyncio.sleep", AsyncMock()),
        ):
            await sender.send_notification(n)

        sent_to = [
            call.kwargs["chat_id"] for call in fake_bot.send_message.await_args_list
        ]
        self.assertEqual(sent_to, [1, 3])  # 2-й пропущен по claim=False

    async def test_file_broadcast_skip_does_not_consume_reuse_file_id(self) -> None:
        # claim False для 1 (пропуск), True для 2 и 3. Байты должен загрузить
        # ПЕРВЫЙ реально отправленный (2-й), а 3-й — переиспользовать file_id.
        async def fake_claim(broadcast_id, chat_id):
            return chat_id != 1

        n = TelegramNotification.model_validate(
            {
                "chat_ids": [1, 2, 3],
                "message": "cap",
                "file_id": 9,
                "broadcast_id": "b1",
            }
        )
        first_msg = MagicMock()
        first_msg.photo = [MagicMock(file_id="TG123")]
        fake_bot = MagicMock()
        fake_bot.send_photo = AsyncMock(return_value=first_msg)
        with (
            patch.object(
                sender.idempotency_store, "claim", AsyncMock(side_effect=fake_claim)
            ),
            patch.object(sender, "bot", fake_bot),
            patch.object(
                sender, "fetch_file", AsyncMock(return_value=(b"x", "image/png"))
            ),
            patch("asyncio.sleep", AsyncMock()),
        ):
            await sender.send_notification(n)

        # 1-й пропущен → ровно 2 отправки, получатели 2 и 3.
        self.assertEqual(fake_bot.send_photo.await_count, 2)
        sent_to = [
            call.kwargs["chat_id"] for call in fake_bot.send_photo.await_args_list
        ]
        self.assertEqual(sent_to, [2, 3])
        # Первый РЕАЛЬНО отправленный (2-й) грузит байты, не пропущенный 1-й.
        self.assertIsInstance(
            fake_bot.send_photo.await_args_list[0].kwargs["photo"], BufferedInputFile
        )
        # 3-й переиспользует пойманный Telegram file_id.
        self.assertEqual(
            fake_bot.send_photo.await_args_list[1].kwargs["photo"], "TG123"
        )
