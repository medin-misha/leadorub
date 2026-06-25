"""FSM-состояния режима поддержки."""

from aiogram.fsm.state import State, StatesGroup


class SupportStates(StatesGroup):
    # Пользователь в режиме поддержки: каждое текстовое сообщение пересылается
    # в backend, пока он не выйдет (/stop, кнопка, /start).
    active = State()
