"""Тесты sweep-логики капельных рассылок: окна выборки и оркестрация правила."""

import unittest
from datetime import datetime, time, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.modules.telegram_module.services import drip_sweep
from app.modules.telegram_module.services.drip_sweep import (
    compute_entry_windows,
    process_drip_rule,
    run_drip_sweep,
)

KYIV = ZoneInfo("Europe/Kyiv")
UTC = timezone.utc


class ComputeEntryWindowsTests(unittest.TestCase):
    def test_due_now_returns_yesterday_window(self) -> None:
        # Вход вчера (по Киеву), правило «через 1 день в 10:00».
        # Сейчас 10:00:30 Киева (07:00:30 UTC, лето → UTC+3) — due наступил.
        now = datetime(2026, 7, 20, 7, 0, 30, tzinfo=UTC)
        windows = compute_entry_windows(
            now_utc=now,
            tz=KYIV,
            days_offset=1,
            send_time=time(10, 0),
            catchup_seconds=21600,
        )
        # Локальные сутки 19 июля Киева = [18.07 21:00 UTC; 19.07 21:00 UTC).
        self.assertEqual(
            windows,
            [
                (
                    datetime(2026, 7, 18, 21, 0, tzinfo=UTC),
                    datetime(2026, 7, 19, 21, 0, tzinfo=UTC),
                )
            ],
        )

    def test_before_send_time_returns_empty(self) -> None:
        # 09:59 Киева — due (10:00) ещё не наступил.
        now = datetime(2026, 7, 20, 6, 59, 0, tzinfo=UTC)
        windows = compute_entry_windows(now, KYIV, 1, time(10, 0), 21600)
        self.assertEqual(windows, [])

    def test_past_catchup_window_returns_empty(self) -> None:
        # 16:01 Киева при catchup 6 часов: due был в 10:00 — опоздали.
        now = datetime(2026, 7, 20, 13, 1, 0, tzinfo=UTC)
        windows = compute_entry_windows(now, KYIV, 1, time(10, 0), 21600)
        self.assertEqual(windows, [])

    def test_zero_offset_window_capped_at_due_time(self) -> None:
        # days_offset=0: окно суток входа обрезается по due_at, чтобы вошедшие
        # ПОСЛЕ send_time не получили сообщение задним числом.
        now = datetime(2026, 7, 20, 7, 30, 0, tzinfo=UTC)  # 10:30 Киева
        windows = compute_entry_windows(now, KYIV, 0, time(10, 0), 21600)
        self.assertEqual(len(windows), 1)
        start, end = windows[0]
        # Начало суток 20 июля Киева = 19.07 21:00 UTC; конец — due (10:00 Киева).
        self.assertEqual(start, datetime(2026, 7, 19, 21, 0, tzinfo=UTC))
        self.assertEqual(end, datetime(2026, 7, 20, 7, 0, tzinfo=UTC))

    def test_at_most_one_window_for_sub_day_catchup(self) -> None:
        # due-моменты соседних дат входа отстоят на 24 часа: окно догона < суток
        # не может накрыть два due одновременно.
        for hour in range(24):
            now = datetime(2026, 7, 20, hour, 7, 0, tzinfo=UTC)
            windows = compute_entry_windows(now, KYIV, 1, time(2, 0), 21600)
            self.assertLessEqual(len(windows), 1)

    def test_dst_transition_does_not_crash(self) -> None:
        # Переход Киева на летнее время (29.03.2026, 03:00→04:00): send_time
        # 03:30 в эти сутки не существует — zoneinfo сдвигает, окно считается.
        now = datetime(2026, 3, 29, 1, 45, 0, tzinfo=UTC)
        windows = compute_entry_windows(now, KYIV, 1, time(3, 30), 21600)
        self.assertIsInstance(windows, list)


def make_rule(**overrides) -> MagicMock:
    rule = MagicMock()
    rule.id = 7
    rule.trigger_state = "persona_start"
    rule.days_offset = 1
    rule.send_time = time(10, 0)
    rule.text = "hello"
    rule.use_buttons = None
    rule.buttons = None
    rule.file_id = None
    for key, value in overrides.items():
        setattr(rule, key, value)
    return rule


NOW_DUE = datetime(2026, 7, 20, 7, 0, 30, tzinfo=UTC)  # 10:00:30 Киева


class ProcessDripRuleTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_window_no_queries(self) -> None:
        session = MagicMock()
        session.execute = AsyncMock()
        rule = make_rule()
        now = datetime(2026, 7, 20, 6, 0, 0, tzinfo=UTC)  # 09:00 Киева — рано

        queued = await process_drip_rule(rule, now, KYIV, session)

        self.assertEqual(queued, 0)
        session.execute.assert_not_awaited()

    async def test_claims_and_enqueues_only_inserted_users(self) -> None:
        rule = make_rule()
        session = MagicMock()
        candidates_result = MagicMock()
        candidates_result.all.return_value = [(1, 111), (2, 222)]
        claim_result = MagicMock()
        # ON CONFLICT вернул только user_id=1: второго уже claim'нул
        # конкурентный запуск — ему не шлём.
        claim_result.scalars.return_value.all.return_value = [1]
        session.execute = AsyncMock(side_effect=[candidates_result, claim_result])

        with patch.object(
            drip_sweep, "enqueue_outbox_message", AsyncMock()
        ) as enqueue:
            queued = await process_drip_rule(rule, NOW_DUE, KYIV, session)

        self.assertEqual(queued, 1)
        enqueue.assert_awaited_once()
        kwargs = enqueue.await_args.kwargs
        self.assertEqual(kwargs["event"], "telegram.newsletter")
        self.assertEqual(kwargs["queue_name"], "telegram_notifications")
        self.assertEqual(kwargs["exchange_name"], "app.events")
        payload = kwargs["payload"]
        self.assertEqual(payload["chat_ids"], [111])
        self.assertEqual(payload["message"], "hello")
        self.assertTrue(payload["broadcast_id"].startswith("drip-7-"))
        self.assertEqual(payload["chunk_index"], 0)
        self.assertEqual(payload["chunk_total"], 1)

    async def test_no_candidates_no_claim(self) -> None:
        rule = make_rule()
        session = MagicMock()
        candidates_result = MagicMock()
        candidates_result.all.return_value = []
        session.execute = AsyncMock(return_value=candidates_result)

        with patch.object(
            drip_sweep, "enqueue_outbox_message", AsyncMock()
        ) as enqueue:
            queued = await process_drip_rule(rule, NOW_DUE, KYIV, session)

        self.assertEqual(queued, 0)
        # Только select кандидатов, без insert-claim.
        session.execute.assert_awaited_once()
        enqueue.assert_not_awaited()

    async def test_chunks_large_audience(self) -> None:
        rule = make_rule()
        user_ids = list(range(1, 1201))
        session = MagicMock()
        candidates_result = MagicMock()
        candidates_result.all.return_value = [(uid, uid * 10) for uid in user_ids]
        claim_result = MagicMock()
        claim_result.scalars.return_value.all.return_value = user_ids
        session.execute = AsyncMock(side_effect=[candidates_result, claim_result])

        with (
            patch.object(settings, "newsletter_chunk_size", 500),
            patch.object(drip_sweep, "enqueue_outbox_message", AsyncMock()) as enqueue,
        ):
            queued = await process_drip_rule(rule, NOW_DUE, KYIV, session)

        self.assertEqual(queued, 1200)
        self.assertEqual(enqueue.await_count, 3)
        sizes = [
            len(call.kwargs["payload"]["chat_ids"]) for call in enqueue.await_args_list
        ]
        self.assertEqual(sizes, [500, 500, 200])
        # broadcast_id общий для всех чанков правила в этом запуске.
        broadcast_ids = {
            call.kwargs["payload"]["broadcast_id"] for call in enqueue.await_args_list
        }
        self.assertEqual(len(broadcast_ids), 1)


class RunDripSweepTests(unittest.IsolatedAsyncioTestCase):
    async def test_disabled_flag_skips_everything(self) -> None:
        with (
            patch.object(settings, "drip_enabled", False),
            patch.object(drip_sweep.database, "sessionmaker") as sessionmaker,
        ):
            total = await run_drip_sweep()

        self.assertEqual(total, 0)
        sessionmaker.assert_not_called()


class DueSemanticsIntegrationTests(unittest.TestCase):
    def test_entry_window_shifts_with_days_offset(self) -> None:
        # Одно и то же «сейчас», разные offset — окна уезжают назад день за днём.
        for offset in (1, 2, 7):
            windows = compute_entry_windows(NOW_DUE, KYIV, offset, time(10, 0), 21600)
            self.assertEqual(len(windows), 1)
            start, _ = windows[0]
            expected_start = datetime(2026, 7, 19, 21, 0, tzinfo=UTC) - timedelta(
                days=offset
            )
            self.assertEqual(start, expected_start)
