"""Тесты сервисного обновления user_stats.state по telegram_id."""

import unittest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException

from app.modules.telegram_module.models import UserStats
from app.modules.telegram_module.services.user_service import set_user_state


def make_session(telegram_user: MagicMock | None) -> MagicMock:
    """Собирает мок AsyncSession, отдающий telegram_user из select-запроса."""
    session = MagicMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = telegram_user
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


class SetUserStateTests(unittest.IsolatedAsyncioTestCase):
    async def test_updates_existing_stats_state(self) -> None:
        stats = MagicMock()
        telegram_user = MagicMock(user_stats=stats)
        session = make_session(telegram_user)

        updated = await set_user_state(
            telegram_id=42, state="persona_start", session=session
        )

        self.assertIs(updated, stats)
        self.assertEqual(stats.state, "persona_start")
        session.flush.assert_awaited_once()

    async def test_creates_stats_when_missing(self) -> None:
        telegram_user = MagicMock(id=7, user_stats=None)
        session = make_session(telegram_user)

        updated = await set_user_state(
            telegram_id=42, state="persona_start", session=session
        )

        session.add.assert_called_once_with(updated)
        self.assertEqual(updated.telegram_user_id, 7)
        self.assertEqual(updated.state, "persona_start")

    async def test_unknown_user_raises_404(self) -> None:
        session = make_session(None)

        with self.assertRaises(HTTPException) as ctx:
            await set_user_state(
                telegram_id=42, state="persona_start", session=session
            )

        self.assertEqual(ctx.exception.status_code, 404)


class StateChangedAtListenerTests(unittest.TestCase):
    """Listener на UserStats.state ставит state_changed_at только при
    фактической смене значения — от него капельные рассылки считают дни."""

    def test_setting_state_on_new_object_stamps_timestamp(self) -> None:
        stats = UserStats(telegram_user_id=1, state="persona_start")
        self.assertIsNotNone(stats.state_changed_at)

    def test_object_without_state_has_no_timestamp(self) -> None:
        stats = UserStats(telegram_user_id=1)
        self.assertIsNone(stats.state_changed_at)

    def test_same_value_does_not_bump_timestamp(self) -> None:
        stats = UserStats(telegram_user_id=1, state="persona_start")
        first = stats.state_changed_at
        stats.state = "persona_start"
        # Идентичность объекта datetime доказывает отсутствие переприсвоения.
        self.assertIs(stats.state_changed_at, first)

    def test_new_value_bumps_timestamp(self) -> None:
        stats = UserStats(telegram_user_id=1, state="persona_start")
        first = stats.state_changed_at
        stats.state = "business_start"
        self.assertIsNot(stats.state_changed_at, first)
        self.assertGreaterEqual(stats.state_changed_at, first)
