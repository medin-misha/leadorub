import unittest
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException, UploadFile

from app.modules.chat_module import handlers as chat_handlers
from app.modules.file_module import handlers as file_handlers
from app.modules.file_module.utils import validate_upload_size
from app.modules.telegram_module import handlers as telegram_handlers


def upload(content: bytes = b"1234") -> UploadFile:
    return UploadFile(filename="document.bin", file=BytesIO(content))


class UploadSizeHelperTests(unittest.IsolatedAsyncioTestCase):
    async def test_uses_actual_file_size_and_rewinds_stream(self) -> None:
        file = upload(b"12345")
        await file.seek(3)

        size = await validate_upload_size(file, max_size_bytes=5)

        self.assertEqual(size, 5)
        self.assertEqual(file.file.tell(), 0)

    async def test_rejects_file_over_limit(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            await validate_upload_size(upload(b"12345"), max_size_bytes=4)

        self.assertEqual(raised.exception.status_code, 413)


class UploadEndpointLimitTests(unittest.IsolatedAsyncioTestCase):
    async def test_file_upload_is_rejected_before_s3(self) -> None:
        with (
            patch.object(file_handlers.settings, "file_upload_max_size_bytes", 3),
            patch.object(file_handlers.s3_client, "create", AsyncMock()) as create,
        ):
            with self.assertRaises(HTTPException) as raised:
                await file_handlers.upload_file(
                    session=MagicMock(), file=upload(), note=None
                )

        self.assertEqual(raised.exception.status_code, 413)
        create.assert_not_awaited()

    async def test_chat_reply_is_rejected_before_service(self) -> None:
        with (
            patch.object(chat_handlers.settings, "chat_upload_max_size_bytes", 3),
            patch.object(
                chat_handlers, "send_admin_reply_service", AsyncMock()
            ) as service,
        ):
            with self.assertRaises(HTTPException) as raised:
                await chat_handlers.reply(
                    telegram_user_id=1,
                    session=MagicMock(),
                    text=None,
                    file=upload(),
                )

        self.assertEqual(raised.exception.status_code, 413)
        service.assert_not_awaited()

    async def test_inbound_media_is_rejected_before_service(self) -> None:
        with (
            patch.object(chat_handlers.settings, "chat_upload_max_size_bytes", 3),
            patch.object(
                chat_handlers, "store_inbound_media_service", AsyncMock()
            ) as service,
        ):
            with self.assertRaises(HTTPException) as raised:
                await chat_handlers.inbound_media(
                    session=MagicMock(),
                    file=upload(),
                    telegram_id=123,
                    tg_message_id=None,
                    caption=None,
                )

        self.assertEqual(raised.exception.status_code, 413)
        service.assert_not_awaited()

    async def test_newsletter_is_rejected_before_service(self) -> None:
        with (
            patch.object(
                telegram_handlers.settings, "newsletter_upload_max_size_bytes", 3
            ),
            patch.object(
                telegram_handlers, "send_newsletter_service", AsyncMock()
            ) as service,
        ):
            with self.assertRaises(HTTPException) as raised:
                await telegram_handlers.send_newsletter(
                    session=MagicMock(),
                    payload='{"filters": {}, "text": "hi"}',
                    file=upload(),
                )

        self.assertEqual(raised.exception.status_code, 413)
        service.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
