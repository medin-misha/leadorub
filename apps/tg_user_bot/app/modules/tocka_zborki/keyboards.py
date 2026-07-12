from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.core import settings

CALLBACK_GET_GUIDE = "tocka_zborki:get_guide"


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Возвращает кнопку выдачи тренировочного пособия."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Получить пособие",
                    callback_data=CALLBACK_GET_GUIDE,
                ),
            ]
        ]
    )


def get_consultation_keyboard() -> InlineKeyboardMarkup:
    """Возвращает Web App-кнопку записи на консультацию."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Записаться на консультацию",
                    web_app=WebAppInfo(url=settings.client_miniapp_url),
                )
            ]
        ]
    )
