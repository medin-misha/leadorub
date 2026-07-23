"""Sweep капельных рассылок: кто «дозрел» — тем ставим отправку в outbox.

Запускается cron-таской TaskIQ раз в минуту (см. telegram_module/tasks.py).
Для каждого активного правила ищем пользователей, у которых:
- state == trigger_state (решение «шлём только тем, кто ещё в состоянии»);
- вход в состояние был days_offset дней назад и send_time уже наступило
  (в settings.drip_timezone), но не позже окна догона drip_catchup_seconds;
- нет записи в dripnewslettersend (гарантия «один раз на юзера»).

Claim получателей — INSERT .. ON CONFLICT DO NOTHING RETURNING в ОДНОЙ
транзакции с постановкой outbox-сообщений: конкурентные запуски sweep
не могут отправить дубль, а падение до commit не оставляет «съеденных»
пользователей без сообщения.
"""

import logging
from datetime import datetime, time, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import database
from app.modules.rmq_module import enqueue_outbox_message

from ..models import DripNewsletter, DripNewsletterSend, TelegramUser, UserStats
from ..schemas import NewsletterContent
from ..utils.newsletter import build_newsletter_payload
from .newsletter_service import (
    NEWSLETTER_EVENT,
    NEWSLETTER_EXCHANGE,
    NEWSLETTER_EXCHANGE_TYPE,
    NEWSLETTER_QUEUE,
)

logger = logging.getLogger(__name__)


def compute_entry_windows(
    now_utc: datetime,
    tz: ZoneInfo,
    days_offset: int,
    send_time: time,
    catchup_seconds: int,
) -> list[tuple[datetime, datetime]]:
    """UTC-границы локальных суток входа в состояние, чьё due-время сейчас в окне.

    Прямое условие due (`state_changed_at + days_offset дней в send_time`)
    не ложится на btree-индекс, поэтому инвертируем: перебираем локальные даты
    входа d и оставляем те, для которых due_at(d) попадает в
    (now - catchup, now]. Для каждой подходящей даты возвращаем UTC-интервал
    [начало суток d; min(начало суток d+1, due_at)) — прямой range-scan по
    ix_userstats_state_changed. Верхняя граница обрезается по due_at ради
    days_offset=0: вошедший в состояние ПОСЛЕ send_time «дозреет» не сегодня
    (его due уже в прошлом относительно входа), а никогда — по решению
    «правило не срабатывает задним числом». При days_offset>=1 due_at всегда
    позже конца суток входа, так что обрезка ничего не меняет.
    """
    window_start = now_utc - timedelta(seconds=catchup_seconds)
    first_entry_date = window_start.astimezone(tz).date() - timedelta(days=days_offset)
    last_entry_date = now_utc.astimezone(tz).date() - timedelta(days=days_offset)

    windows: list[tuple[datetime, datetime]] = []
    entry_date = first_entry_date
    while entry_date <= last_entry_date:
        due_at = datetime.combine(
            entry_date + timedelta(days=days_offset), send_time, tzinfo=tz
        ).astimezone(timezone.utc)
        if window_start < due_at <= now_utc:
            day_start = datetime.combine(entry_date, time.min, tzinfo=tz).astimezone(
                timezone.utc
            )
            day_end = datetime.combine(
                entry_date + timedelta(days=1), time.min, tzinfo=tz
            ).astimezone(timezone.utc)
            windows.append((day_start, min(day_end, due_at)))
        entry_date += timedelta(days=1)
    return windows


async def process_drip_rule(
    rule: DripNewsletter,
    now_utc: datetime,
    tz: ZoneInfo,
    session: AsyncSession,
) -> int:
    """Обрабатывает одно правило: выборка → claim → outbox. Возвращает
    число пользователей, поставленных в отправку. Commit — на вызывающем."""
    windows = compute_entry_windows(
        now_utc=now_utc,
        tz=tz,
        days_offset=rule.days_offset,
        send_time=rule.send_time,
        catchup_seconds=settings.drip_catchup_seconds,
    )
    if not windows:
        return 0

    range_filters = [
        (UserStats.state_changed_at >= start) & (UserStats.state_changed_at < end)
        for start, end in windows
    ]
    candidates_stmt = (
        select(UserStats.telegram_user_id, TelegramUser.telegram_id)
        .join(TelegramUser, TelegramUser.id == UserStats.telegram_user_id)
        .where(
            UserStats.state == rule.trigger_state,
            or_(*range_filters),
            ~select(DripNewsletterSend.id)
            .where(
                DripNewsletterSend.drip_newsletter_id == rule.id,
                DripNewsletterSend.telegram_user_id == UserStats.telegram_user_id,
            )
            .exists(),
        )
    )
    candidates = (await session.execute(candidates_stmt)).all()
    if not candidates:
        return 0

    chat_id_by_user = {user_id: chat_id for user_id, chat_id in candidates}
    broadcast_id = f"drip-{rule.id}-{uuid4().hex}"

    # Claim: только строки, которые реально вставились, становятся получателями.
    claim_stmt = (
        pg_insert(DripNewsletterSend)
        .values(
            [
                {
                    "drip_newsletter_id": rule.id,
                    "telegram_user_id": user_id,
                    "broadcast_id": broadcast_id,
                }
                for user_id in chat_id_by_user
            ]
        )
        .on_conflict_do_nothing(
            index_elements=["drip_newsletter_id", "telegram_user_id"]
        )
        .returning(DripNewsletterSend.telegram_user_id)
    )
    claimed_user_ids = (await session.execute(claim_stmt)).scalars().all()
    if not claimed_user_ids:
        return 0

    chat_ids = [chat_id_by_user[user_id] for user_id in claimed_user_ids]
    content = NewsletterContent(
        text=rule.text,
        use_buttons=rule.use_buttons,
        buttons=rule.buttons,
    )

    chunk_size = settings.newsletter_chunk_size
    chunks = [chat_ids[i : i + chunk_size] for i in range(0, len(chat_ids), chunk_size)]
    chunk_total = len(chunks)
    for chunk_index, chunk in enumerate(chunks):
        payload = build_newsletter_payload(
            chat_ids=chunk,
            request=content,
            file_id=rule.file_id,
            broadcast_id=broadcast_id,
            chunk_index=chunk_index,
            chunk_total=chunk_total,
        )
        await enqueue_outbox_message(
            session,
            event=NEWSLETTER_EVENT,
            payload=payload,
            queue_name=NEWSLETTER_QUEUE,
            routing_key=NEWSLETTER_QUEUE,
            exchange_name=NEWSLETTER_EXCHANGE,
            exchange_type=NEWSLETTER_EXCHANGE_TYPE,
        )
    return len(chat_ids)


async def run_drip_sweep() -> int:
    """Полный проход по активным правилам. Возвращает всего поставленных в отправку.

    Каждое правило — своя транзакция: ошибка одного правила (битые кнопки,
    гонка с удалением) логируется и не стопорит остальные.
    """
    if not settings.drip_enabled:
        return 0

    tz = ZoneInfo(settings.drip_timezone)
    now_utc = datetime.now(timezone.utc)

    async with database.sessionmaker() as session:
        rules = (
            (
                await session.execute(
                    select(DripNewsletter).where(DripNewsletter.is_active)
                )
            )
            .scalars()
            .all()
        )

    total = 0
    for rule in rules:
        async with database.sessionmaker() as session:
            try:
                queued = await process_drip_rule(rule, now_utc, tz, session)
                await session.commit()
            except Exception:
                await session.rollback()
                logger.exception("[drip] rule id=%s sweep failed", rule.id)
                continue
        if queued:
            logger.info("[drip] rule id=%s queued %s recipients", rule.id, queued)
        total += queued
    return total
