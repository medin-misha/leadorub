from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.modules import Base, TimestampMixin


class Admin(Base, TimestampMixin):
    """Администратор системы (вход в admin_miniapp по username/password).

    Пароль хранится только в виде bcrypt-хеша. `is_active=False` мгновенно
    лишает админа доступа (проверяется в `get_current_admin` на каждом запросе).
    """

    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
