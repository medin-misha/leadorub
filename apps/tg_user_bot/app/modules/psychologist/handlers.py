"""
Telegram-хендлеры для воронки психолога.

Этот модуль отвечает за логику воронки: переходы между разделами
главного меню, консультаций и контактов.
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.modules.psychologist.keyboards import (
    CALLBACK_CONSULTATIONS,
    CALLBACK_CONTACTS,
    CALLBACK_MAIN_MENU,
    get_consultations_keyboard,
    get_contacts_keyboard,
    get_main_menu_keyboard,
)
from app.modules.psychologist.messages import get_messages

router = Router(name="psychologist")
_MESSAGES = get_messages()


@router.callback_query(F.data == CALLBACK_CONSULTATIONS)
async def show_consultations(query: CallbackQuery) -> None:
    """Переход в меню консультаций с описанием трех форматов."""
    if not query.message or not isinstance(query.message, Message):
        await query.answer()
        return

    await query.message.edit_text(
        text=_MESSAGES["consultations"],
        reply_markup=get_consultations_keyboard(),
    )
    await query.answer()


@router.callback_query(F.data == CALLBACK_CONTACTS)
async def show_contacts(query: CallbackQuery) -> None:
    """Переход в меню контактов."""
    if not query.message or not isinstance(query.message, Message):
        await query.answer()
        return

    await query.message.edit_text(
        text=_MESSAGES["contacts"],
        reply_markup=get_contacts_keyboard(),
    )
    await query.answer()


@router.callback_query(F.data == CALLBACK_MAIN_MENU)
async def show_main_menu(query: CallbackQuery) -> None:
    """Возврат в главное меню воронки."""
    if not query.message or not isinstance(query.message, Message):
        await query.answer()
        return

    await query.message.edit_text(
        text=_MESSAGES["welcome"],
        reply_markup=get_main_menu_keyboard(),
    )
    await query.answer()
