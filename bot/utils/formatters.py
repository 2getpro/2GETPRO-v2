"""
Утилиты для форматирования данных в читаемый вид.
"""
from datetime import datetime
from typing import Optional


def format_balance(kopeks: int) -> str:
    """
    Форматировать баланс из копеек в рубли.
    
    Args:
        kopeks: Сумма в копейках
        
    Returns:
        Отформатированная строка с суммой в рублях
        
    Examples:
        >>> format_balance(10050)
        '100.50 ₽'
        >>> format_balance(0)
        '0.00 ₽'
        >>> format_balance(-5000)
        '-50.00 ₽'
    """
    rubles = kopeks / 100
    return f"{rubles:.2f} ₽"


def format_date(dt: Optional[datetime]) -> str:
    """
    Форматировать дату и время в читаемый вид.
    
    Args:
        dt: Объект datetime для форматирования
        
    Returns:
        Отформатированная строка с датой и временем
        
    Examples:
        >>> from datetime import datetime
        >>> format_date(datetime(2025, 11, 27, 15, 30, 0))
        '27.11.2025 15:30'
        >>> format_date(None)
        'Не указано'
    """
    if not dt:
        return "Не указано"
    return dt.strftime("%d.%m.%Y %H:%M")


def format_transaction_type(transaction_type: str) -> str:
    """
    Форматировать тип транзакции в читаемый вид.
    
    Args:
        transaction_type: Тип транзакции
        
    Returns:
        Читаемое название типа транзакции
    """
    type_names = {
        "balance_add": "Пополнение баланса",
        "balance_deduct": "Списание с баланса",
        "subscription_purchase": "Покупка подписки",
        "refund": "Возврат средств",
        "gift_sent": "Отправка подарка",
        "gift_received": "Получение подарка"
    }
    return type_names.get(transaction_type, transaction_type)


def format_amount_with_sign(amount_kopeks: int) -> str:
    """
    Форматировать сумму с знаком + или -.
    
    Args:
        amount_kopeks: Сумма в копейках
        
    Returns:
        Отформатированная строка с суммой и знаком
        
    Examples:
        >>> format_amount_with_sign(10000)
        '+100.00 ₽'
        >>> format_amount_with_sign(-5000)
        '-50.00 ₽'
    """
    sign = "+" if amount_kopeks >= 0 else ""
    rubles = amount_kopeks / 100
    return f"{sign}{rubles:.2f} ₽"