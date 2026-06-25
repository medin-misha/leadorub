import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.modules.rmq_module import rmq_publisher
from app.modules.system import CRUD
from app.modules.chat_module.handlers import reply as reply_handler
from app.modules.chat_module.schemas import SupportMessageRMQ
from app.modules.chat_module.services import chat_service
from app.modules.chat_module.services.chat_service import (
    SupportUserNotFound,
    send_admin_reply,
    store_inbound_media,
    store_inbound_message,
)


def _upload_file(name="pic.jpg", content_type="image/jpeg"):
    return MagicMock(filename=name, content_type=content_type, file=MagicMock())


def _session_returning_scalar(value):
    """MagicMock-сессия, у которой execute(...).scalar_one_or_none() == value."""
    session = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    session.execute = AsyncMock(return_value=result)
    return session


class StoreInboundMessageTests(unittest.IsolatedAsyncioTestCase):
    async def test_resolves_user_and_stores_user_message(self) -> None:
        session = _session_returning_scalar(7)  # telegramuser.id
        data = SupportMessageRMQ(telegram_id=555, text="help me", tg_message_id=42)

        with patch.object(CRUD, "create", AsyncMock()) as create:
            await store_inbound_message(data, session)

        create.assert_awaited_once()
        payload = create.await_args.args[0]
        self.assertEqual(payload.telegram_user_id, 7)
        self.assertEqual(payload.direction, "user")
        self.assertEqual(payload.text, "help me")
        self.assertEqual(payload.tg_message_id, 42)
        self.assertFalse(payload.is_read)

    async def test_unknown_user_raises(self) -> None:
        session = _session_returning_scalar(None)
        data = SupportMessageRMQ(telegram_id=999, text="hi")

        with patch.object(CRUD, "create", AsyncMock()) as create:
            with self.assertRaises(SupportUserNotFound):
                await store_inbound_message(data, session)
        create.assert_not_awaited()


class SendAdminReplyTests(unittest.IsolatedAsyncioTestCase):
    async def test_creates_admin_row_and_publishes(self) -> None:
        session = _session_returning_scalar(555)  # telegram_id получателя

        with (
            patch.object(CRUD, "create", AsyncMock()) as create,
            patch.object(rmq_publisher, "publish", AsyncMock()) as publish,
        ):
            await send_admin_reply(session, telegram_user_id=1, text="hello")

        # строка admin создаётся ДО публикации
        create.assert_awaited_once()
        payload = create.await_args.args[0]
        self.assertEqual(payload.direction, "admin")
        self.assertEqual(payload.text, "hello")
        self.assertEqual(payload.telegram_user_id, 1)

        publish.assert_awaited_once()
        kwargs = publish.await_args.kwargs
        self.assertEqual(kwargs["queue_name"], "telegram_notifications")
        self.assertEqual(kwargs["routing_key"], "telegram_notifications")
        self.assertEqual(kwargs["exchange_name"], "app.events")
        self.assertEqual(kwargs["payload"]["chat_ids"], [555])
        self.assertEqual(kwargs["payload"]["message"], "hello")

    async def test_unknown_user_raises_404_and_does_not_publish(self) -> None:
        session = _session_returning_scalar(None)

        with (
            patch.object(CRUD, "create", AsyncMock()) as create,
            patch.object(rmq_publisher, "publish", AsyncMock()) as publish,
        ):
            with self.assertRaises(HTTPException) as ctx:
                await send_admin_reply(session, telegram_user_id=1, text="hello")

        self.assertEqual(ctx.exception.status_code, 404)
        create.assert_not_awaited()
        publish.assert_not_awaited()

    async def test_publish_failure_propagates_after_create(self) -> None:
        # Если публикация падает — исключение пробрасывается (get_session откатит строку).
        session = _session_returning_scalar(555)

        with (
            patch.object(CRUD, "create", AsyncMock()) as create,
            patch.object(
                rmq_publisher,
                "publish",
                AsyncMock(side_effect=RuntimeError("broker down")),
            ),
        ):
            with self.assertRaises(RuntimeError):
                await send_admin_reply(session, telegram_user_id=1, text="hello")

        create.assert_awaited_once()

    async def test_reply_with_file_publishes_file_id(self) -> None:
        session = _session_returning_scalar(555)
        file_rec = MagicMock(id=77)
        message = MagicMock()

        with (
            patch.object(
                chat_service.s3_client, "create", AsyncMock(return_value="http://l")
            ),
            patch.object(
                CRUD, "create", AsyncMock(side_effect=[file_rec, message])
            ) as create,
            patch.object(rmq_publisher, "publish", AsyncMock()) as publish,
        ):
            await send_admin_reply(
                session, telegram_user_id=1, text=None, file=_upload_file()
            )

        # File создаётся первым, затем chat_message с file_id.
        self.assertEqual(create.await_count, 2)
        self.assertEqual(create.await_args_list[1].args[0].file_id, 77)
        kwargs = publish.await_args.kwargs
        self.assertEqual(kwargs["payload"]["file_id"], 77)
        self.assertEqual(kwargs["payload"]["chat_ids"], [555])


class StoreInboundMediaTests(unittest.IsolatedAsyncioTestCase):
    async def test_uploads_and_stores_user_media(self) -> None:
        session = _session_returning_scalar(7)
        file_rec = MagicMock(id=99)
        message = MagicMock()

        with (
            patch.object(
                chat_service.s3_client, "create", AsyncMock(return_value="http://l")
            ),
            patch.object(
                CRUD, "create", AsyncMock(side_effect=[file_rec, message])
            ) as create,
        ):
            await store_inbound_media(
                session,
                telegram_id=555,
                file=_upload_file(),
                caption="look",
                tg_message_id=42,
            )

        self.assertEqual(create.await_count, 2)
        chat_payload = create.await_args_list[1].args[0]
        self.assertEqual(chat_payload.direction, "user")
        self.assertEqual(chat_payload.file_id, 99)
        self.assertEqual(chat_payload.text, "look")

    async def test_unknown_user_skips_upload(self) -> None:
        session = _session_returning_scalar(None)

        with (
            patch.object(chat_service.s3_client, "create", AsyncMock()) as s3_create,
            patch.object(CRUD, "create", AsyncMock()) as create,
        ):
            with self.assertRaises(SupportUserNotFound):
                await store_inbound_media(session, telegram_id=999, file=_upload_file())

        s3_create.assert_not_awaited()
        create.assert_not_awaited()


class ReplyValidationTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_reply_raises_400(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            await reply_handler(
                telegram_user_id=1, session=MagicMock(), text=None, file=None
            )
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_reply_over_limit_raises_400(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            await reply_handler(
                telegram_user_id=1, session=MagicMock(), text="a" * 1025, file=None
            )
        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
