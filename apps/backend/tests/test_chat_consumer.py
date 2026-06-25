import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.database import database
from app.modules.rmq_module import RMQMessage
from app.modules.chat_module.services import consumer_handler
from app.modules.chat_module.services.chat_service import SupportUserNotFound


def _patch_sessionmaker():
    """Подменяет database.sessionmaker на async-context-manager с mock-сессией.

    Возвращает (patcher, session) — session.commit/rollback это AsyncMock.
    """
    session = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    maker = MagicMock(return_value=cm)
    return patch.object(database, "sessionmaker", maker), session


def _message() -> RMQMessage:
    return RMQMessage(
        event="telegram.support_message",
        payload={"telegram_id": 555, "text": "help", "tg_message_id": 42},
        source="tg_user_bot",
    )


class HandleSupportMessageTests(unittest.IsolatedAsyncioTestCase):
    async def test_stores_and_commits(self) -> None:
        sm_patch, session = _patch_sessionmaker()
        with (
            sm_patch,
            patch.object(
                consumer_handler, "store_inbound_message", AsyncMock()
            ) as store,
        ):
            await consumer_handler.handle_support_message(_message())

        store.assert_awaited_once()
        session.commit.assert_awaited_once()
        session.rollback.assert_not_awaited()

    async def test_unknown_user_is_acked_not_raised(self) -> None:
        # SupportUserNotFound не должен пробрасываться (иначе consumer сделает reject):
        # сообщение дропается через rollback + лог, без requeue-петли.
        sm_patch, session = _patch_sessionmaker()
        with (
            sm_patch,
            patch.object(
                consumer_handler,
                "store_inbound_message",
                AsyncMock(side_effect=SupportUserNotFound(555)),
            ),
        ):
            await consumer_handler.handle_support_message(_message())

        session.rollback.assert_awaited_once()
        session.commit.assert_not_awaited()

    async def test_other_error_propagates(self) -> None:
        sm_patch, session = _patch_sessionmaker()
        with (
            sm_patch,
            patch.object(
                consumer_handler,
                "store_inbound_message",
                AsyncMock(side_effect=RuntimeError("db down")),
            ),
        ):
            with self.assertRaises(RuntimeError):
                await consumer_handler.handle_support_message(_message())

        session.rollback.assert_awaited_once()
        session.commit.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
