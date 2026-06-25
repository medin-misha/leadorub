"""Клавиатуры режима поддержки."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# callback_data кнопки выхода из режима поддержки.
EXIT_CALLBACK = "support:stop"


def support_exit_keyboard() -> InlineKeyboardMarkup:
    """Инлайн-клавиатура с единственной кнопкой «Завершить диалог»."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✖️ Завершить диалог",
                    callback_data=EXIT_CALLBACK,
                )
            ]
        ]
    )
