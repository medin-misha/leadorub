import asyncio
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from logging import getLogger
from uuid import uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.modules.rmq_module.models import OutboxMessage

from .publisher import RMQPublisher, rmq_publisher

logger = getLogger(__name__)


async def enqueue_outbox_message(
    session: AsyncSession,
    *,
    event: str,
    payload: dict,
    exchange_name: str,
    exchange_type: str,
    routing_key: str,
    queue_name: str | None = None,
    source: str | None = None,
    correlation_id: str | None = None,
) -> OutboxMessage:
    """Добавляет событие в ту же транзакцию, что и бизнес-изменения."""
    message = OutboxMessage(
        message_id=str(uuid4()),
        event=event,
        payload=payload,
        exchange_name=exchange_name,
        exchange_type=exchange_type,
        routing_key=routing_key,
        queue_name=queue_name,
        source=source or settings.project_name,
        correlation_id=correlation_id,
        status="pending",
        attempts=0,
        available_at=datetime.now(UTC),
    )
    session.add(message)
    await session.flush()
    return message


class OutboxPublisherRuntime:
    """Арендует committed outbox-строки и доставляет их с безопасным retry."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        publisher: RMQPublisher,
    ) -> None:
        self._session_factory = session_factory
        self._publisher = publisher
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    @property
    def started(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if self.started:
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="rmq-outbox-publisher")
        logger.info("RMQ outbox publisher started")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop.set()
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        logger.info("RMQ outbox publisher stopped")

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                claimed = await self.dispatch_batch()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Unexpected RMQ outbox dispatch error")
                claimed = 0
            if claimed == 0:
                try:
                    await asyncio.wait_for(
                        self._stop.wait(), timeout=settings.rabbitmq_outbox_poll_interval
                    )
                except TimeoutError:
                    pass

    async def dispatch_batch(self) -> int:
        messages = await self._claim_batch()
        for message in messages:
            try:
                await self._publisher.publish(
                    event=message.event,
                    payload=message.payload,
                    exchange_name=message.exchange_name,
                    exchange_type=message.exchange_type,
                    routing_key=message.routing_key,
                    queue_name=message.queue_name,
                    source=message.source,
                    correlation_id=message.correlation_id,
                    message_id=message.message_id,
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await self._release_for_retry(message.id, message.attempts, exc)
            else:
                await self._mark_published(message.id)
        return len(messages)

    async def _claim_batch(self) -> list[OutboxMessage]:
        now = datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            statement = (
                select(OutboxMessage)
                .where(
                    or_(
                        and_(
                            OutboxMessage.status == "pending",
                            OutboxMessage.available_at <= now,
                        ),
                        and_(
                            OutboxMessage.status == "processing",
                            OutboxMessage.locked_until <= now,
                        ),
                    )
                )
                .order_by(OutboxMessage.id)
                .limit(settings.rabbitmq_outbox_batch_size)
                .with_for_update(skip_locked=True)
            )
            messages = list((await session.scalars(statement)).all())
            locked_until = now + timedelta(seconds=settings.rabbitmq_outbox_lease_seconds)
            for message in messages:
                message.status = "processing"
                message.locked_until = locked_until
                message.attempts += 1
                message.last_error = None
        return messages

    async def _mark_published(self, message_id: int) -> None:
        async with self._session_factory() as session, session.begin():
            message = await session.get(OutboxMessage, message_id, with_for_update=True)
            if message is not None and message.status == "processing":
                message.status = "published"
                message.published_at = datetime.now(UTC)
                message.locked_until = None
                message.last_error = None

    async def _release_for_retry(
        self, message_id: int, attempts: int, exc: Exception
    ) -> None:
        delay = min(
            settings.rabbitmq_outbox_retry_max_seconds,
            settings.rabbitmq_reconnect_interval * (2 ** min(attempts - 1, 8)),
        )
        async with self._session_factory() as session, session.begin():
            message = await session.get(OutboxMessage, message_id, with_for_update=True)
            if message is not None and message.status == "processing":
                message.status = "pending"
                message.available_at = datetime.now(UTC) + timedelta(seconds=delay)
                message.locked_until = None
                message.last_error = str(exc)[:4000]
        logger.warning("RMQ outbox message %s failed; retry in %ss", message_id, delay)


def build_outbox_runtime() -> OutboxPublisherRuntime:
    # Локальный import исключает цикл core.database → config → modules.
    from app.core.database import database

    return OutboxPublisherRuntime(database.sessionmaker, rmq_publisher)
