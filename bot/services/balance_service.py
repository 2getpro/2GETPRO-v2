"""
Сервис для управления балансом пользователей.
"""
import logging
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from db.dal import user_dal
from db.dal import transaction_dal
from db.models import Transaction


class BalanceService:
    """Сервис для работы с балансом пользователей"""
    
    def __init__(self, session: AsyncSession):
        """
        Инициализация сервиса баланса.
        
        Args:
            session: Асинхронная сессия БД
        """
        self.session = session
    
    async def add_balance(
        self,
        user_id: int,
        amount_kopeks: int,
        description: Optional[str] = None
    ) -> Transaction:
        """
        Пополнить баланс пользователя.
        
        Args:
            user_id: ID пользователя
            amount_kopeks: Сумма пополнения в копейках
            description: Описание операции
            
        Returns:
            Созданная транзакция
            
        Raises:
            ValueError: Если сумма <= 0 или пользователь не найден
        """
        if amount_kopeks <= 0:
            raise ValueError("Amount must be positive")
        
        user = await user_dal.get_user_by_id(self.session, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Обновить баланс
        user.balance_kopeks += amount_kopeks
        
        # Создать транзакцию
        transaction = await transaction_dal.create_transaction(
            session=self.session,
            user_id=user_id,
            amount_kopeks=amount_kopeks,
            transaction_type="balance_add",
            description=description or "Пополнение баланса"
        )
        
        await self.session.commit()
        
        logging.info(
            f"Balance added for user {user_id}: +{amount_kopeks} kopeks. "
            f"New balance: {user.balance_kopeks}"
        )
        
        return transaction
    
    async def deduct_balance(
        self,
        user_id: int,
        amount_kopeks: int,
        description: Optional[str] = None
    ) -> Transaction:
        """
        Списать средства с баланса пользователя.
        
        Args:
            user_id: ID пользователя
            amount_kopeks: Сумма списания в копейках
            description: Описание операции
            
        Returns:
            Созданная транзакция
            
        Raises:
            ValueError: Если сумма <= 0, недостаточно средств или пользователь не найден
        """
        if amount_kopeks <= 0:
            raise ValueError("Amount must be positive")
        
        user = await user_dal.get_user_by_id(self.session, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        if user.balance_kopeks < amount_kopeks:
            raise ValueError(
                f"Insufficient balance: has {user.balance_kopeks}, "
                f"needs {amount_kopeks}"
            )
        
        # Списать с баланса
        user.balance_kopeks -= amount_kopeks
        
        # Создать транзакцию (с отрицательной суммой)
        transaction = await transaction_dal.create_transaction(
            session=self.session,
            user_id=user_id,
            amount_kopeks=-amount_kopeks,
            transaction_type="balance_deduct",
            description=description or "Списание с баланса"
        )
        
        await self.session.commit()
        
        logging.info(
            f"Balance deducted for user {user_id}: -{amount_kopeks} kopeks. "
            f"New balance: {user.balance_kopeks}"
        )
        
        return transaction
    
    async def get_balance(self, user_id: int) -> int:
        """
        Получить текущий баланс пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Баланс в копейках
            
        Raises:
            ValueError: Если пользователь не найден
        """
        user = await user_dal.get_user_by_id(self.session, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        return user.balance_kopeks
    
    async def can_afford(self, user_id: int, amount_kopeks: int) -> bool:
        """
        Проверить, достаточно ли средств на балансе.
        
        Args:
            user_id: ID пользователя
            amount_kopeks: Требуемая сумма в копейках
            
        Returns:
            True если средств достаточно, иначе False
        """
        try:
            balance = await self.get_balance(user_id)
            return balance >= amount_kopeks
        except ValueError:
            return False
    
    async def get_transaction_history(
        self,
        user_id: int,
        limit: int = 10,
        offset: int = 0
    ) -> List[Transaction]:
        """
        Получить историю транзакций пользователя.
        
        Args:
            user_id: ID пользователя
            limit: Максимальное количество записей
            offset: Смещение для пагинации
            
        Returns:
            Список транзакций
        """
        return await transaction_dal.get_user_transactions(
            session=self.session,
            user_id=user_id,
            limit=limit,
            offset=offset
        )
    
    async def process_subscription_purchase(
        self,
        user_id: int,
        amount_kopeks: int,
        subscription_months: int,
        description: Optional[str] = None
    ) -> Transaction:
        """
        Обработать покупку подписки с баланса.
        
        Args:
            user_id: ID пользователя
            amount_kopeks: Стоимость подписки в копейках
            subscription_months: Количество месяцев подписки
            description: Описание операции
            
        Returns:
            Созданная транзакция
            
        Raises:
            ValueError: Если недостаточно средств или пользователь не найден
        """
        if amount_kopeks <= 0:
            raise ValueError("Amount must be positive")
        
        user = await user_dal.get_user_by_id(self.session, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        if user.balance_kopeks < amount_kopeks:
            raise ValueError(
                f"Insufficient balance for subscription purchase: "
                f"has {user.balance_kopeks}, needs {amount_kopeks}"
            )
        
        # Списать с баланса
        user.balance_kopeks -= amount_kopeks
        
        # Создать транзакцию
        transaction = await transaction_dal.create_transaction(
            session=self.session,
            user_id=user_id,
            amount_kopeks=-amount_kopeks,
            transaction_type="subscription_purchase",
            description=description or f"Покупка подписки на {subscription_months} мес."
        )
        
        await self.session.commit()
        
        logging.info(
            f"Subscription purchased from balance for user {user_id}: "
            f"{subscription_months} months, -{amount_kopeks} kopeks. "
            f"New balance: {user.balance_kopeks}"
        )
        
        return transaction