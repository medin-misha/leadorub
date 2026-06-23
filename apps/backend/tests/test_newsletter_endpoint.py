import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.telegram_module import handlers


class NewsletterEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_handler_parses_payload_and_delegates(self) -> None:
        session = MagicMock()
        payload = '{"filters": {}, "text": "hi"}'
        with patch.object(
            handlers,
            "send_newsletter_service",
            AsyncMock(return_value={"status": "queued", "recipients": 7}),
        ) as service:
            result = await handlers.send_newsletter(
                session=session, payload=payload, file=None
            )

        self.assertEqual(result, {"status": "queued", "recipients": 7})
        service.assert_awaited_once()
        # переданный в сервис request распарсен из JSON payload
        call_kwargs = service.await_args.kwargs
        self.assertEqual(call_kwargs["request"].text, "hi")
        self.assertIsNone(call_kwargs["file"])
