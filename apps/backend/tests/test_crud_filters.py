import unittest

from sqlalchemy import select, func

from app.modules.system import CRUD
from app.modules.telegram_module.models import TelegramUser


class ApplySearchTests(unittest.TestCase):
    """_apply_search строит тот же фильтр, что и CRUD.get, без обращения к БД."""

    def test_field_search_builds_where_clause(self) -> None:
        stmt = CRUD._apply_search(
            select(TelegramUser), TelegramUser, search="ivan", field="username"
        )
        compiled = str(stmt)
        self.assertIn("WHERE", compiled)
        self.assertIn("username", compiled)

    def test_text_search_builds_where_clause(self) -> None:
        stmt = CRUD._apply_search(
            select(TelegramUser), TelegramUser, search="ivan", field=None
        )
        self.assertIn("WHERE", str(stmt))

    def test_no_search_returns_unfiltered(self) -> None:
        stmt = CRUD._apply_search(
            select(func.count()).select_from(TelegramUser),
            TelegramUser,
            search=None,
            field=None,
        )
        self.assertNotIn("WHERE", str(stmt))
