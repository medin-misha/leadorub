import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.modules.rmq_module import rmq_publisher
from app.modules.system import CRUD
from app.modules.telegram_module.models import TelegramUser
from app.modules.requisition.models import Requisition
from app.modules.requisition.schemas import (
    RequisitionCreate,
    RequisitionStatusUpdate,
)
from app.modules.requisition.services.requisition_service import (
    create_requisition,
    list_requisitions,
    update_requisition_status,
)


class RequisitionServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_requisition_user_not_found_raises_404(self) -> None:
        # Тестируем, что если пользователь отсутствует в БД, возвращается 404
        data = RequisitionCreate(
            telegram_id=999,
            type="consultation",
            payload={"name": "Тест"},
        )
        session = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        with self.assertRaises(HTTPException) as ctx:
            await create_requisition(data=data, session=session)

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found", ctx.exception.detail)

    async def test_create_requisition_success(self) -> None:
        # Тестируем успешное создание заявки
        data = RequisitionCreate(
            telegram_id=123,
            type="community",
            payload={"motivation": "Хочу войти"},
        )
        session = MagicMock()

        # Создаем мок пользователя Telegram
        mock_user = TelegramUser(id=5, telegram_id=123, username="test_user")

        # Мокаем возврат пользователя из БД
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = mock_user
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        # Мокаем сохранение и генерацию id в БД
        async def mock_flush():
            # Назначаем фейковые авто-поля
            pass

        session.flush = mock_flush
        session.refresh = AsyncMock()

        with patch.object(rmq_publisher, "publish", AsyncMock()) as publish:
            requisition = await create_requisition(data=data, session=session)

            self.assertEqual(requisition.telegram_user_id, mock_user.id)
            self.assertEqual(requisition.type, "community")
            self.assertEqual(requisition.payload, {"motivation": "Хочу войти"})
            self.assertEqual(requisition.status, "pending")

            # Проверяем, что в RabbitMQ ушло правильное событие
            publish.assert_awaited_once()
            kwargs = publish.await_args.kwargs
            self.assertEqual(kwargs["event"], "requisition.created")
            self.assertEqual(kwargs["queue_name"], "admin_requisitions")
            self.assertEqual(kwargs["payload"]["telegram_id"], 123)
            self.assertEqual(kwargs["payload"]["type"], "community")

    async def test_update_requisition_status_success(self) -> None:
        # Тестируем успешное обновление статуса заявки админом
        update_data = RequisitionStatusUpdate(
            status="approved",
            admin_comment="Добро пожаловать!",
        )
        session = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        # Мокаем сущность заявки с вложенным пользователем
        mock_user = TelegramUser(telegram_id=123)
        mock_requisition = Requisition(
            id=1,
            telegram_user_id=5,
            type="community",
            status="pending",
            payload={"name": "Тест"},
            telegram_user=mock_user,
        )

        with (
            patch.object(CRUD, "get", AsyncMock(return_value=mock_requisition)),
            patch.object(rmq_publisher, "publish", AsyncMock()) as publish,
        ):
            updated = await update_requisition_status(
                requisition_id=1, data=update_data, session=session
            )

            self.assertEqual(updated.status, "approved")
            self.assertEqual(updated.admin_comment, "Добро пожаловать!")

            # Проверяем публикацию уведомления пользователю
            publish.assert_awaited_once()
            kwargs = publish.await_args.kwargs
            self.assertEqual(kwargs["event"], "telegram.notification")
            self.assertEqual(kwargs["queue_name"], "telegram_notifications")
            self.assertEqual(kwargs["payload"]["chat_ids"], [123])
            self.assertIn("одобрена", kwargs["payload"]["message"])
            self.assertIn("Добро пожаловать!", kwargs["payload"]["message"])
