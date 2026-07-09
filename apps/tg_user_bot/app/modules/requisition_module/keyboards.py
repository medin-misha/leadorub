from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

CANCEL_CALLBACK = "apply:cancel"
APPLY_CONSULTATION_CALLBACK = "apply:consultation"
APPLY_COMMUNITY_CALLBACK = "apply:community"


def get_product_selection_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру выбора продукта для подачи заявки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Заявка на консультацию 📅",
                    callback_data=APPLY_CONSULTATION_CALLBACK,
                )
            ],
            [
                InlineKeyboardButton(
                    text="Заявка в сообщество 👥",
                    callback_data=APPLY_COMMUNITY_CALLBACK,
                )
            ],
            [
                InlineKeyboardButton(
                    text="Отмена ❌",
                    callback_data=CANCEL_CALLBACK,
                )
            ],
        ]
    )


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру отмены заполнения заявки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Отменить заполнение ❌",
                    callback_data=CANCEL_CALLBACK,
                )
            ]
        ]
    )


def get_phone_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает reply-клавиатуру для отправки номера телефона."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Поделиться контактом 📱", request_contact=True)],
            [KeyboardButton(text="Отмена ❌")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
