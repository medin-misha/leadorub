from aiogram.fsm.state import State, StatesGroup


class ConsultationStates(StatesGroup):
    """Состояния для заявки на консультацию."""

    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_description = State()


class CommunityStates(StatesGroup):
    """Состояния для заявки в закрытое сообщество."""

    waiting_for_name = State()
    waiting_for_experience = State()
    waiting_for_motivation = State()
