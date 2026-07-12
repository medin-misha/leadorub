import unittest
from unittest.mock import AsyncMock, MagicMock

from app.modules.rmq_module.services.outbox import (
    OutboxPublisherRuntime,
    enqueue_outbox_message,
)


class EnqueueOutboxMessageTests(unittest.IsolatedAsyncioTestCase):
    async def test_adds_event_to_caller_session_without_commit(self) -> None:
        session = MagicMock()
        session.flush = AsyncMock()

        message = await enqueue_outbox_message(
            session,
            event="telegram.notification",
            payload={"chat_ids": [1], "message": "hello"},
            exchange_name="app.events",
            exchange_type="direct",
            routing_key="telegram_notifications",
            queue_name="telegram_notifications",
        )

        session.add.assert_called_once_with(message)
        session.flush.assert_awaited_once_with()
        self.assertEqual(message.status, "pending")
        self.assertEqual(message.attempts, 0)
        self.assertEqual(message.payload["chat_ids"], [1])
        self.assertTrue(message.message_id)
        # Commit принадлежит request dependency: outbox атомарен с business rows.
        self.assertFalse(hasattr(session, "commit") and session.commit.called)


class OutboxDispatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_success_reuses_message_id_and_marks_published(self) -> None:
        publisher = MagicMock()
        publisher.publish = AsyncMock()
        runtime = OutboxPublisherRuntime(MagicMock(), publisher)
        message = MagicMock(
            id=7,
            message_id="stable-id",
            event="event",
            payload={"value": 1},
            exchange_name="exchange",
            exchange_type="direct",
            routing_key="route",
            queue_name="queue",
            source="backend",
            correlation_id=None,
            attempts=1,
        )
        runtime._claim_batch = AsyncMock(return_value=[message])
        runtime._mark_published = AsyncMock()
        runtime._release_for_retry = AsyncMock()

        claimed = await runtime.dispatch_batch()

        self.assertEqual(claimed, 1)
        self.assertEqual(publisher.publish.await_args.kwargs["message_id"], "stable-id")
        runtime._mark_published.assert_awaited_once_with(7)
        runtime._release_for_retry.assert_not_awaited()

    async def test_failure_releases_message_for_retry(self) -> None:
        publisher = MagicMock()
        publisher.publish = AsyncMock(side_effect=RuntimeError("broker down"))
        runtime = OutboxPublisherRuntime(MagicMock(), publisher)
        message = MagicMock(
            id=9,
            message_id="stable-id",
            event="event",
            payload={},
            exchange_name="exchange",
            exchange_type="direct",
            routing_key="route",
            queue_name="queue",
            source="backend",
            correlation_id=None,
            attempts=2,
        )
        runtime._claim_batch = AsyncMock(return_value=[message])
        runtime._mark_published = AsyncMock()
        runtime._release_for_retry = AsyncMock()

        await runtime.dispatch_batch()

        runtime._mark_published.assert_not_awaited()
        args = runtime._release_for_retry.await_args.args
        self.assertEqual(args[:2], (9, 2))
        self.assertIsInstance(args[2], RuntimeError)


if __name__ == "__main__":
    unittest.main()
