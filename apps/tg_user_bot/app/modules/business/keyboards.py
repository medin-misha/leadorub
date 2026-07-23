"""Inline-клавиатуры воронки DMCAGuardian для агентств."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.core import settings


def get_contact_keyboard() -> InlineKeyboardMarkup:
    """Кнопки связи: личка админа и заявка через Client MiniApp.

    Кнопка «Написать» появляется только при настроенном ADMIN_CONTACT_URL —
    URL-кнопка без адреса невозможна, а вести пользователя в никуда нельзя.
    """

    row: list[InlineKeyboardButton] = []
    if settings.admin_contact_url:
        row.append(
            InlineKeyboardButton(
                text="✍️ Написать",
                url=settings.admin_contact_url,
            )
        )
    row.append(
        InlineKeyboardButton(
            text="📩 Оставить заявку",
            web_app=WebAppInfo(url=settings.client_miniapp_url),
        )
    )
    return InlineKeyboardMarkup(inline_keyboard=[row])
