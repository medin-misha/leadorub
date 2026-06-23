import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup

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
        with patch.object(sender, "bot", fake_bot), patch(
            "asyncio.sleep", AsyncMock()
        ):
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
        with patch.object(sender, "bot", fake_bot), patch.object(
            sender, "fetch_file", AsyncMock(return_value=(b"x", "image/png"))
        ), patch("asyncio.sleep", AsyncMock()):
            await sender.send_notification(n)
        self.assertEqual(fake_bot.send_photo.await_count, 2)
        # второй вызов переиспользует пойманный Telegram file_id (строку)
        self.assertEqual(
            fake_bot.send_photo.await_args_list[1].kwargs["photo"], "TG123"
        )
