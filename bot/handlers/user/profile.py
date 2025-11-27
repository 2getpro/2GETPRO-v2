"""
Обработчики для профиля пользователя.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from bot.services.balance_service import BalanceService
from db.dal import subscription_dal, user_dal
from bot.keyboards.inline.profile_keyboards import (
    get_profile_keyboard,
    get_balance_details_keyboard,
    get_transaction_history_keyboard,
    get_add_balance_keyboard
)
from bot.utils.formatters import (
    format_balance,
    format_date,
    format_amount_with_sign,
    format_transaction_type
)
from bot.middlewares.i18n import JsonI18n
from config.settings import Settings

router = Router(name="user_profile_router")


@router.message(Command("profile"))
async def show_profile_command(
    message: Message,
    session: AsyncSession,
    settings: Settings,
    i18n_data: dict
):
    """Показать профиль пользователя по команде /profile"""
    await show_profile(message, session, settings, i18n_data, is_callback=False)


@router.callback_query(F.data == "profile:show")
async def show_profile_callback(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
    i18n_data: dict
):
    """Показать профиль пользователя по callback"""
    await callback.answer()
    await show_profile(callback, session, settings, i18n_data, is_callback=True)


async def show_profile(
    event: Message | CallbackQuery,
    session: AsyncSession,
    settings: Settings,
    i18n_data: dict,
    is_callback: bool = False
):
    """
    Показать профиль пользователя.
    
    Args:
        event: Событие (Message или CallbackQuery)
        session: Сессия БД
        settings: Настройки бота
        i18n_data: Данные локализации
        is_callback: Является ли событие callback
    """
    user_id = event.from_user.id
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    
    if not i18n:
        logging.error(f"i18n_instance missing for user {user_id}")
        return
    
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)
    
    # Получить данные пользователя
    balance_service = BalanceService(session)
    
    try:
        balance = await balance_service.get_balance(user_id)
    except ValueError:
        balance = 0
    
    # Получить количество активных подписок
    user = await user_dal.get_user_by_id(session, user_id)
    subscriptions_count = 0
    
    if user and user.panel_user_uuid:
        active_sub = await subscription_dal.get_active_subscription_by_user_id(
            session, user_id, user.panel_user_uuid
        )
        if active_sub and active_sub.is_active:
            subscriptions_count = 1
    
    # Форматировать сообщение
    text = f"👤 <b>{_('profile_title')}</b>\n\n"
    text += f"💰 {_('profile_balance_label')}: <b>{format_balance(balance)}</b>\n"
    text += f"📊 {_('profile_subscriptions_label')}: <b>{subscriptions_count}</b>\n\n"
    
    if subscriptions_count > 0:
        text += f"<i>{_('profile_has_active_subscriptions')}</i>"
    else:
        text += f"<i>{_('profile_no_active_subscriptions')}</i>"
    
    keyboard = get_profile_keyboard(balance, subscriptions_count, current_lang, i18n)
    
    if is_callback and isinstance(event, CallbackQuery) and event.message:
        try:
            await event.message.edit_text(text, reply_markup=keyboard)
        except Exception as e:
            logging.warning(f"Failed to edit profile message: {e}")
            await event.message.answer(text, reply_markup=keyboard)
    else:
        await event.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "profile:show_balance")
async def show_balance_details(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
    i18n_data: dict
):
    """Показать детали баланса"""
    await callback.answer()
    
    user_id = callback.from_user.id
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    
    if not i18n:
        logging.error(f"i18n_instance missing for user {user_id}")
        return
    
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)
    
    balance_service = BalanceService(session)
    
    try:
        balance = await balance_service.get_balance(user_id)
        transactions = await balance_service.get_transaction_history(user_id, limit=5)
    except ValueError as e:
        logging.error(f"Error getting balance for user {user_id}: {e}")
        await callback.answer(_("error_occurred_try_again"), show_alert=True)
        return
    
    text = f"💰 <b>{_('balance_details_title')}</b>\n\n"
    text += f"{_('current_balance_label')}: <b>{format_balance(balance)}</b>\n\n"
    
    if transactions:
        text += f"<b>{_('recent_transactions_label')}:</b>\n"
        for trans in transactions:
            amount_str = format_amount_with_sign(trans.amount_kopeks)
            trans_type = format_transaction_type(trans.transaction_type)
            text += f"\n{amount_str} - {trans_type}\n"
            text += f"<i>{format_date(trans.created_at)}</i>\n"
    else:
        text += f"<i>{_('no_transactions_yet')}</i>"
    
    keyboard = get_balance_details_keyboard(current_lang, i18n)
    
    if callback.message:
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception as e:
            logging.warning(f"Failed to edit balance details: {e}")
            await callback.message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "profile:transaction_history")
@router.callback_query(F.data.startswith("profile:history:"))
async def show_transaction_history(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
    i18n_data: dict
):
    """Показать историю транзакций"""
    await callback.answer()
    
    user_id = callback.from_user.id
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    
    if not i18n:
        logging.error(f"i18n_instance missing for user {user_id}")
        return
    
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)
    
    # Определить страницу
    page = 0
    if callback.data.startswith("profile:history:"):
        try:
            page = int(callback.data.split(":")[-1])
        except (ValueError, IndexError):
            page = 0
    
    balance_service = BalanceService(session)
    per_page = 10
    
    try:
        transactions = await balance_service.get_transaction_history(
            user_id,
            limit=per_page + 1,  # +1 чтобы проверить есть ли еще
            offset=page * per_page
        )
    except Exception as e:
        logging.error(f"Error getting transaction history for user {user_id}: {e}")
        await callback.answer(_("error_occurred_try_again"), show_alert=True)
        return
    
    has_more = len(transactions) > per_page
    transactions = transactions[:per_page]
    
    text = f"📜 <b>{_('transaction_history_title')}</b>\n"
    text += f"<i>{_('page_label')}: {page + 1}</i>\n\n"
    
    if transactions:
        for trans in transactions:
            amount_str = format_amount_with_sign(trans.amount_kopeks)
            trans_type = format_transaction_type(trans.transaction_type)
            text += f"{amount_str} - {trans_type}\n"
            if trans.description:
                text += f"<i>{trans.description}</i>\n"
            text += f"{format_date(trans.created_at)}\n\n"
    else:
        text += f"<i>{_('no_transactions_on_page')}</i>"
    
    keyboard = get_transaction_history_keyboard(current_lang, i18n, page, has_more)
    
    if callback.message:
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception as e:
            logging.warning(f"Failed to edit transaction history: {e}")
            await callback.message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "profile:add_balance")
async def show_add_balance_options(
    callback: CallbackQuery,
    settings: Settings,
    i18n_data: dict
):
    """Показать опции пополнения баланса"""
    await callback.answer()
    
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    
    if not i18n:
        logging.error(f"i18n_instance missing")
        return
    
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)
    
    text = f"💳 <b>{_('add_balance_title')}</b>\n\n"
    text += f"{_('add_balance_description')}\n\n"
    text += f"<i>{_('select_amount_or_custom')}</i>"
    
    keyboard = get_add_balance_keyboard(current_lang, i18n)
    
    if callback.message:
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception as e:
            logging.warning(f"Failed to edit add balance message: {e}")
            await callback.message.answer(text, reply_markup=keyboard)