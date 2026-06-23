from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# bcrypt не принимает пароли длиннее 72 байт — ограничиваем длину здесь,
# чтобы не получить ValueError при хешировании.
PasswordField = Field(min_length=6, max_length=72)


class AdminBase(BaseModel):
    username: str = Field(min_length=1, max_length=255)


class AdminCreate(AdminBase):
    password: str = PasswordField


class AdminPatch(BaseModel):
    """Частичное обновление: смена пароля и/или активности."""

    password: str | None = Field(default=None, min_length=6, max_length=72)
    is_active: bool | None = None


class AdminRead(AdminBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
