from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from app.core import settings
from ..schemas import TelegramNotification

# Separate Bot instance used exclusively for background notifications sending
bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=settings.bot_parse_mode),
)


async def send_notification(notification: TelegramNotification) -> None:
    """Assembles the required keyboard (inline or reply) and sends the message

    to the specified chat_id using the Telegram bot client.
    """
    reply_markup = None

    if notification.buttons:
        if notification.inline_buttons:
            inline_keyboard = []
            for row in notification.buttons:
                inline_row = []
                for btn in row:
                    btn_kwargs = {"text": btn.text}
                    if btn.web_app:
                        btn_kwargs["web_app"] = WebAppInfo(url=btn.web_app)
                    else:
                        # For inline keyboard, callback_data or url must be provided.
                        btn_kwargs["callback_data"] = btn.text
                    inline_row.append(InlineKeyboardButton(**btn_kwargs))
                inline_keyboard.append(inline_row)
            reply_markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

        elif notification.reply_buttons:
            keyboard = []
            for row in notification.buttons:
                reply_row = []
                for btn in row:
                    btn_kwargs = {"text": btn.text}
                    if btn.requests_contect:
                        btn_kwargs["request_contact"] = True
                    if btn.request_location:
                        btn_kwargs["request_location"] = True
                    if btn.web_app:
                        btn_kwargs["web_app"] = WebAppInfo(url=btn.web_app)
                    reply_row.append(KeyboardButton(**btn_kwargs))
                keyboard.append(reply_row)
            reply_markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

    await bot.send_message(
        chat_id=notification.chat_id,
        text=notification.message,
        reply_markup=reply_markup,
    )
