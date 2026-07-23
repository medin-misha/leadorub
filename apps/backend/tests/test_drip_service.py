"""Тесты admin-CRUD сервиса капельных рассылок (без реальной БД/S3)."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.modules.system import CRUD
from app.modules.telegram_module.schemas import DripNewsletterCreate
from app.modules.telegram_module.services import drip_service
from app.modules.telegram_module.services.drip_service import (
    create_drip_newsletter,
    delete_drip_newsletter,
)


def make_data(**overrides) -> DripNewsletterCreate:
    payload = {
        "trigger_state": "persona_start",
        "days_offset": 1,
        "send_time": "10:00",
        "text": "hi",
    }
    payload.update(overrides)
    return DripNewsletterCreate.model_validate(payload)


def make_session() -> MagicMock:
    session = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


class CreateDripNewsletterTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_content_raises_400(self) -> None:
        data = make_data(text=None)
        with self.assertRaises(HTTPException) as ctx:
            await create_drip_newsletter(data=data, file=None, session=make_session())
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_text_over_limit_raises_400(self) -> None:
        data = make_data(text="a" * 1025)
        with self.assertRaises(HTTPException) as ctx:
            await create_drip_newsletter(data=data, file=None, session=make_session())
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_creates_rule_without_file(self) -> None:
        data = make_data(
            use_buttons="INLINE",
            buttons=[{"text": "x", "url": "https://example.com"}],
        )
        session = make_session()

        rule = await create_drip_newsletter(data=data, file=None, session=session)

        session.add.assert_called_once_with(rule)
        session.flush.assert_awaited_once()
        self.assertEqual(rule.trigger_state, "persona_start")
        self.assertEqual(rule.days_offset, 1)
        self.assertIsNone(rule.file_id)
        # Кнопки сериализуются в JSON-совместимые dict без None-полей.
        self.assertEqual(rule.buttons, [{"text": "x", "url": "https://example.com"}])

    async def test_s3_object_deleted_when_file_record_fails(self) -> None:
        data = make_data()
        upload = MagicMock()
        upload.filename = "doc.pdf"
        upload.content_type = "application/pdf"
        s3 = MagicMock()
        s3.create = AsyncMock(return_value="s3://link")
        s3.delete = AsyncMock()

        with (
            patch.object(drip_service, "s3_client", s3),
            patch.object(
                CRUD, "create", AsyncMock(side_effect=HTTPException(status_code=503))
            ),
        ):
            with self.assertRaises(HTTPException):
                await create_drip_newsletter(
                    data=data, file=upload, session=make_session()
                )

        # Компенсация: строка File не создана → объект в S3 удалён.
        s3.delete.assert_awaited_once_with("s3://link")


class DeleteDripNewsletterTests(unittest.IsolatedAsyncioTestCase):
    async def test_deletes_rule_and_file_row_returns_link(self) -> None:
        rule = MagicMock(file_id=5)
        file_record = MagicMock(link="s3://old")
        session = make_session()
        session.get = AsyncMock(return_value=file_record)
        session.delete = AsyncMock()

        with patch.object(CRUD, "get", AsyncMock(return_value=rule)):
            link = await delete_drip_newsletter(id=1, session=session)

        self.assertEqual(link, "s3://old")
        session.delete.assert_any_await(file_record)
        session.delete.assert_any_await(rule)

    async def test_deletes_rule_without_file(self) -> None:
        rule = MagicMock(file_id=None)
        session = make_session()
        session.delete = AsyncMock()

        with patch.object(CRUD, "get", AsyncMock(return_value=rule)):
            link = await delete_drip_newsletter(id=1, session=session)

        self.assertIsNone(link)
        session.delete.assert_awaited_once_with(rule)
