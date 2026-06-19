from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.system import Base, TimestampMixin


class File(Base, TimestampMixin):
    link: Mapped[str] = mapped_column(String(1024))
    name: Mapped[str] = mapped_column(String(512))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
