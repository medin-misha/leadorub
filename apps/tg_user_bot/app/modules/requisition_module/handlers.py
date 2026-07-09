import logging

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    Message,
    ReplyKeyboardRemove,
)

from app.modules.system.auth import login_required
from app.modules.system.client import get_backend_client, BackendClientError

from .keyboards import (
    CANCEL_CALLBACK,
    APPLY_COMMUNITY_CALLBACK,
    APPLY_CONSULTATION_CALLBACK,
    get_cancel_keyboard,
    get_phone_keyboard,
    get_product_selection_keyboard,
)
from .states import CommunityStates, ConsultationStates

logger = logging.getLogger(__name__)

router = Router(name="requisitions")

# Текстовые сообщения
_CHOOSE_PRODUCT = "Выберите продукт, на который хотите подать заявку:"
_CANCELLED = "Подача заявки отменена."
_GET_NAME = "Как к вам обращаться? (Введите ваше имя):"
_GET_PHONE = "Пожалуйста, укажите ваш номер телефона. Вы можете воспользоваться кнопкой ниже, чтобы поделиться им автоматически:"
_GET_DESC = "Кратко опишите вашу цель/проблему для консультации:"
_GET_EXP = "Укажите ссылку на ваши соцсети/профиль или кратко опишите ваш опыт:"
_GET_MOTIVATION = "Опишите вашу мотивацию (почему хотите вступить в наше сообщество):"
_SUCCESS = "🎉 Ваша заявка на '{product}' успешно отправлена и ожидает рассмотрения!"
_ERROR = "⚠️ Произошла ошибка при отправке заявки. Пожалуйста, попробуйте позже."


# --- НАЧАЛО И ОТМЕНА ---

@router.message(Command("apply"))
@login_required
async def apply_start(message: Message, state: FSMContext) -> None:
    """Выводит меню выбора продукта для подачи заявки."""
    await state.clear()  # Сбрасываем старые состояния
    await message.answer(_CHOOSE_PRODUCT, reply_markup=get_product_selection_keyboard())


@router.callback_query(F.data == CANCEL_CALLBACK)
async def apply_cancel_callback(query: CallbackQuery, state: FSMContext) -> None:
    """Отмена подачи заявки через инлайн-кнопку."""
    await state.clear()
    await query.answer()
    if query.message is not None:
        await query.message.answer(_CANCELLED, reply_markup=ReplyKeyboardRemove())


@router.message(F.text == "Отмена ❌")
async def apply_cancel_text(message: Message, state: FSMContext) -> None:
    """Отмена подачи заявки через текстовую кнопку (Reply)."""
    await state.clear()
    await message.answer(_CANCELLED, reply_markup=ReplyKeyboardRemove())


# --- ЗАЯВКА НА КОНСУЛЬТАЦИЮ ---

@router.callback_query(F.data == APPLY_CONSULTATION_CALLBACK)
async def start_consultation_flow(query: CallbackQuery, state: FSMContext) -> None:
    """Запуск опроса для консультации."""
    await state.set_state(ConsultationStates.waiting_for_name)
    await query.answer()
    if query.message is not None:
        await query.message.answer(_GET_NAME, reply_markup=get_cancel_keyboard())


@router.message(ConsultationStates.waiting_for_name, F.text)
async def consultation_name(message: Message, state: FSMContext) -> None:
    """Сохраняет имя и запрашивает телефон."""
    if message.text == "Отмена ❌":
        await apply_cancel_text(message, state)
        return

    await state.update_data(name=message.text)
    await state.set_state(ConsultationStates.waiting_for_phone)
    await message.answer(_GET_PHONE, reply_markup=get_phone_keyboard())


@router.message(ConsultationStates.waiting_for_phone)
async def consultation_phone(message: Message, state: FSMContext) -> None:
    """Сохраняет телефон и запрашивает описание."""
    if message.text == "Отмена ❌":
        await apply_cancel_text(message, state)
        return

    phone = None
    if message.contact:
        phone = message.contact.phone_number
    elif message.text:
        phone = message.text

    if not phone:
        await message.answer("Пожалуйста, отправьте контакт кнопкой или введите номер текстом.")
        return

    await state.update_data(phone=phone)
    await state.set_state(ConsultationStates.waiting_for_description)
    # Удаляем reply-клавиатуру при переходе на следующий шаг
    await message.answer(_GET_DESC, reply_markup=ReplyKeyboardRemove())


@router.message(ConsultationStates.waiting_for_description, F.text)
async def consultation_description(message: Message, state: FSMContext) -> None:
    """Сохраняет описание и отправляет заявку на бэкенд."""
    if message.text == "Отмена ❌":
        await apply_cancel_text(message, state)
        return

    data = await state.get_data()
    name = data.get("name")
    phone = data.get("phone")
    description = message.text

    payload = {
        "name": name,
        "phone": phone,
        "description": description,
    }

    try:
        client = get_backend_client()
        await client.create_requisition(
            telegram_id=message.from_user.id,
            type_="consultation",
            payload=payload,
        )
        await state.clear()
        await message.answer(
            _SUCCESS.format(product="Консультация"),
            reply_markup=ReplyKeyboardRemove(),
        )
    except BackendClientError as exc:
        logger.error("Ошибка при отправке заявки на бэкенд: %s", exc)
        await message.answer(_ERROR)


# --- ЗАЯВКА В СООБЩЕСТВО ---

@router.callback_query(F.data == APPLY_COMMUNITY_CALLBACK)
async def start_community_flow(query: CallbackQuery, state: FSMContext) -> None:
    """Запуск опроса для сообщества."""
    await state.set_state(CommunityStates.waiting_for_name)
    await query.answer()
    if query.message is not None:
        await query.message.answer(_GET_NAME, reply_markup=get_cancel_keyboard())


@router.message(CommunityStates.waiting_for_name, F.text)
async def community_name(message: Message, state: FSMContext) -> None:
    """Сохраняет имя и запрашивает опыт."""
    if message.text == "Отмена ❌":
        await apply_cancel_text(message, state)
        return

    await state.update_data(name=message.text)
    await state.set_state(CommunityStates.waiting_for_experience)
    await message.answer(_GET_EXP, reply_markup=get_cancel_keyboard())


@router.message(CommunityStates.waiting_for_experience, F.text)
async def community_experience(message: Message, state: FSMContext) -> None:
    """Сохраняет опыт и запрашивает мотивацию."""
    if message.text == "Отмена ❌":
        await apply_cancel_text(message, state)
        return

    await state.update_data(experience=message.text)
    await state.set_state(CommunityStates.waiting_for_motivation)
    await message.answer(_GET_MOTIVATION, reply_markup=get_cancel_keyboard())


@router.message(CommunityStates.waiting_for_motivation, F.text)
async def community_motivation(message: Message, state: FSMContext) -> None:
    """Сохраняет мотивацию и отправляет заявку на бэкенд."""
    if message.text == "Отмена ❌":
        await apply_cancel_text(message, state)
        return

    data = await state.get_data()
    name = data.get("name")
    experience = data.get("experience")
    motivation = message.text

    payload = {
        "name": name,
        "experience": experience,
        "motivation": motivation,
    }

    try:
        client = get_backend_client()
        await client.create_requisition(
            telegram_id=message.from_user.id,
            type_="community",
            payload=payload,
        )
        await state.clear()
        await message.answer(
            _SUCCESS.format(product="Вступление в сообщество"),
            reply_markup=ReplyKeyboardRemove(),
        )
    except BackendClientError as exc:
        logger.error("Ошибка при отправке заявки на бэкенд: %s", exc)
        await message.answer(_ERROR)
