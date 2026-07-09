from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from app.core import settings

# Callback-даты для воронки
CALLBACK_CONSULTATIONS = "psy:consultations"
CALLBACK_CONTACTS = "psy:contacts"
CALLBACK_MAIN_MENU = "psy:main_menu"
CALLBACK_APPLY_STUB = "psy:apply_stub"
# Альтернативный callback для реальной записи через requisition_module:
# CALLBACK_APPLY_REAL = "apply:consultation"


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру главного меню воронки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💼 Консультации",
                    callback_data=CALLBACK_CONSULTATIONS,
                ),
                InlineKeyboardButton(
                    text="📞 Контакты",
                    callback_data=CALLBACK_CONTACTS,
                ),
            ]
        ]
    )


def get_consultations_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для раздела консультаций."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✍ Записаться",
                    web_app=WebAppInfo(url=settings.client_miniapp_url),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅ Назад в меню",
                    callback_data=CALLBACK_MAIN_MENU,
                )
            ],
        ]
    )


def get_contacts_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для раздела контактов."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅ Назад в меню",
                    callback_data=CALLBACK_MAIN_MENU,
                )
            ]
        ]
    )



