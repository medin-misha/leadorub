import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.modules.system import CRUD
from app.modules.rmq_module import rmq_publisher
from app.modules.telegram_module.schemas import NewsletterRequest
from app.modules.telegram_module.services.newsletter_service import send_newsletter
from app.modules.telegram_module.utils.newsletter import build_newsletter_payload


class SendNewsletterTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_audience_raises_404_and_does_not_publish(self) -> None:
        request = NewsletterRequest.model_validate({"text": "hi"})
        session = MagicMock()
        with (
            patch.object(CRUD, "count", AsyncMock(return_value=0)),
            patch.object(rmq_publisher, "publish", AsyncMock()) as publish,
        ):
            with self.assertRaises(HTTPException) as ctx:
                await send_newsletter(request=request, file=None, session=session)
            self.assertEqual(ctx.exception.status_code, 404)
            publish.assert_not_awaited()

    async def test_no_content_raises_400(self) -> None:
        request = NewsletterRequest.model_validate({"text": None})
        session = MagicMock()
        with patch.object(CRUD, "count", AsyncMock(return_value=5)):
            with self.assertRaises(HTTPException) as ctx:
                await send_newsletter(request=request, file=None, session=session)
            self.assertEqual(ctx.exception.status_code, 400)

    async def test_text_over_limit_raises_400_and_does_not_publish(self) -> None:
        request = NewsletterRequest.model_validate({"text": "a" * 1025})
        session = MagicMock()
        with patch.object(rmq_publisher, "publish", AsyncMock()) as publish:
            with self.assertRaises(HTTPException) as ctx:
                await send_newsletter(request=request, file=None, session=session)
            self.assertEqual(ctx.exception.status_code, 400)
            publish.assert_not_awaited()

    async def test_text_only_publishes_one_message(self) -> None:
        request = NewsletterRequest.model_validate({"text": "hello"})
        session = MagicMock()
        with (
            patch.object(CRUD, "count", AsyncMock(return_value=3)),
            patch.object(CRUD, "get_column", AsyncMock(return_value=[10, 20, 30])),
            patch.object(rmq_publisher, "publish", AsyncMock()) as publish,
        ):
            result = await send_newsletter(request=request, file=None, session=session)

        self.assertEqual(result, {"status": "queued", "recipients": 3})
        publish.assert_awaited_once()
        kwargs = publish.await_args.kwargs
        self.assertEqual(kwargs["event"], "telegram.newsletter")
        self.assertEqual(kwargs["queue_name"], "telegram_notifications")
        self.assertEqual(kwargs["routing_key"], "telegram_notifications")
        self.assertEqual(kwargs["exchange_name"], "app.events")
        self.assertEqual(kwargs["exchange_type"], "direct")
        self.assertEqual(kwargs["payload"]["chat_ids"], [10, 20, 30])
        self.assertEqual(kwargs["payload"]["message"], "hello")
        self.assertIsNone(kwargs["payload"]["file_id"])


class BuildNewsletterPayloadTests(unittest.TestCase):
    def test_build_payload_carries_broadcast_meta(self) -> None:
        # Payload одного чанка несёт общий broadcast_id и диагностику chunk_*.
        request = NewsletterRequest.model_validate({"text": "hi"})
        payload = build_newsletter_payload(
            chat_ids=[1, 2],
            request=request,
            file_id=None,
            broadcast_id="bcast-1",
            chunk_index=3,
            chunk_total=10,
        )
        self.assertEqual(payload["chat_ids"], [1, 2])
        self.assertEqual(payload["broadcast_id"], "bcast-1")
        self.assertEqual(payload["chunk_index"], 3)
        self.assertEqual(payload["chunk_total"], 10)
