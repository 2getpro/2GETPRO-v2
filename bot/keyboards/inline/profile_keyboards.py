"""
Клавиатуры для профиля пользователя.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Optional


def get_profile_keyboard(
    balance: int,
    subscriptions_count: int,
    lang: str,
    i18n_instance
) -> InlineKeyboardMarkup:
    """
    Клавиатура профиля пользователя.
    
    Args:
        balance: Баланс пользователя в копейках
        subscriptions_count: Количество активных подписок
        lang: Код языка
        i18n_instance: Экземпляр i18n для переводов
        
    Returns:
        Клавиатура профиля
    """
    _ = lambda key, **kwargs: i18n_instance.gettext(lang, key, **kwargs)
    builder = InlineKeyboardBuilder()
    
    # Кнопки баланса и подписок
    builder.row(
        InlineKeyboardButton(
            text=_("profile_balance_button"),
            callback_data="profile:show_balance"
        ),
        InlineKeyboardButton(
            text=_("profile_subscriptions_button"),
            callback_data="main_action:my_subscription"
        )
    )
    
    # Кнопка пополнения баланса
    builder.row(
        InlineKeyboardButton(
            text=_("profile_add_balance_button"),
            callback_data="profile:add_balance"
        )
    )
    
    # Кнопка управления подписками (если есть активные)
    if subscriptions_count > 0:
        builder.row(
            InlineKeyboardButton(
                text=_("profile_manage_subscriptions_button"),
                callback_data="main_action:my_subscription"
            )
        )
    
    # Кнопка возврата в главное меню
    builder.row(
        InlineKeyboardButton(
            text=_("back_to_main_menu_button"),
            callback_data="main_action:back_to_main"
        )
    )
    
    return builder.as_markup()


def get_balance_details_keyboard(
    lang: str,
    i18n_instance
) -> InlineKeyboardMarkup:
    """
    Клавиатура для детального просмотра баланса.
    
    Args:
        lang: Код языка
        i18n_instance: Экземпляр i18n для переводов
        
    Returns:
        Клавиатура деталей баланса
    """
    _ = lambda key, **kwargs: i18n_instance.gettext(lang, key, **kwargs)
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=_("profile_add_balance_button"),
            callback_data="profile:add_balance"
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text=_("profile_transaction_history_button"),
            callback_data="profile:transaction_history"
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text=_("back_to_profile_button"),
            callback_data="profile:show"
        )
    )
    
    return builder.as_markup()


def get_transaction_history_keyboard(
    lang: str,
    i18n_instance,
    page: int = 0,
    has_more: bool = False
) -> InlineKeyboardMarkup:
    """
    Клавиатура для истории транзакций с пагинацией.
    
    Args:
        lang: Код языка
        i18n_instance: Экземпляр i18n для переводов
        page: Текущая страница
        has_more: Есть ли еще транзакции
        
    Returns:
        Клавиатура истории транзакций
    """
    _ = lambda key, **kwargs: i18n_instance.gettext(lang, key, **kwargs)
    builder = InlineKeyboardBuilder()
    
    # Кнопки навигации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=f"profile:history:{page-1}"
            )
        )
    if has_more:
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=f"profile:history:{page+1}"
            )
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Кнопка возврата
    builder.row(
        InlineKeyboardButton(
            text=_("back_to_balance_button"),
            callback_data="profile:show_balance"
        )
    )
    
    return builder.as_markup()


def get_add_balance_keyboard(
    lang: str,
    i18n_instance
) -> InlineKeyboardMarkup:
    """
    Клавиатура для пополнения баланса.
    
    Args:
        lang: Код языка
        i18n_instance: Экземпляр i18n для переводов
        
    Returns:
        Клавиатура пополнения баланса
    """
    _ = lambda key, **kwargs: i18n_instance.gettext(lang, key, **kwargs)
    builder = InlineKeyboardBuilder()
    
    # Предустановленные суммы для пополнения
    amounts = [100, 300, 500, 1000, 2000, 5000]
    
    for i in range(0, len(amounts), 2):
        row_buttons = []
        for j in range(2):
            if i + j < len(amounts):
                amount = amounts[i + j]
                row_buttons.append(
                    InlineKeyboardButton(
                        text=f"{amount} ₽",
                        callback_data=f"profile:add_balance:{amount * 100}"
                    )
                )
        builder.row(*row_buttons)
    
    # Кнопка для ввода произвольной суммы
    builder.row(
        InlineKeyboardButton(
            text=_("profile_custom_amount_button"),
            callback_data="profile:add_balance:custom"
        )
    )
    
    # Кнопка отмены
    builder.row(
        InlineKeyboardButton(
            text=_("cancel_button"),
            callback_data="profile:show"
        )
    )
    
    return builder.as_markup()