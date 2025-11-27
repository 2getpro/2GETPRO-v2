"""
Data Access Layer для работы с транзакциями пользователей.
"""
import logging
from typing import Optional, List
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Transaction


async def create_transaction(
    session: AsyncSession,
    user_id: int,
    amount_kopeks: int,
    transaction_type: str,
    description: Optional[str] = None
) -> Transaction:
    """
    Создать новую транзакцию.
    
    Args:
        session: Асинхронная сессия БД
        user_id: ID пользователя
        amount_kopeks: Сумма в копейках (может быть отрицательной)
        transaction_type: Тип транзакции
        description: Описание транзакции
        
    Returns:
        Созданная транзакция
    """
    transaction = Transaction(
        user_id=user_id,
        amount_kopeks=amount_kopeks,
        transaction_type=transaction_type,
        description=description
    )
    session.add(transaction)
    await session.flush()
    await session.refresh(transaction)
    
    logging.info(
        f"Transaction created: id={transaction.id}, user_id={user_id}, "
        f"amount={amount_kopeks}, type={transaction_type}"
    )
    
    return transaction


async def get_user_transactions(
    session: AsyncSession,
    user_id: int,
    limit: int = 10,
    offset: int = 0
) -> List[Transaction]:
    """
    Получить историю транзакций пользователя.
    
    Args:
        session: Асинхронная сессия БД
        user_id: ID пользователя
        limit: Максимальное количество записей
        offset: Смещение для пагинации
        
    Returns:
        Список транзакций
    """
    query = (
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(desc(Transaction.created_at))
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_transaction_by_id(
    session: AsyncSession,
    transaction_id: int
) -> Optional[Transaction]:
    """
    Получить транзакцию по ID.
    
    Args:
        session: Асинхронная сессия БД
        transaction_id: ID транзакции
        
    Returns:
        Транзакция или None
    """
    query = select(Transaction).where(Transaction.id == transaction_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_transactions_by_type(
    session: AsyncSession,
    user_id: int,
    transaction_type: str,
    limit: int = 10
) -> List[Transaction]:
    """
    Получить транзакции пользователя определенного типа.
    
    Args:
        session: Асинхронная сессия БД
        user_id: ID пользователя
        transaction_type: Тип транзакции
        limit: Максимальное количество записей
        
    Returns:
        Список транзакций
    """
    query = (
        select(Transaction)
        .where(
            Transaction.user_id == user_id,
            Transaction.transaction_type == transaction_type
        )
        .order_by(desc(Transaction.created_at))
        .limit(limit)
    )
    result = await session.execute(query)
    return list(result.scalars().all())