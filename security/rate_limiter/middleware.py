"""
Middleware для rate limiting в aiogram.
"""

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
import logging

from .redis_rate_limiter import RedisRateLimiter

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseMiddleware):
    """
    Middleware для автоматической проверки rate limits.
    
    Проверяет лимиты перед обработкой сообщений и блокирует спамеров.
    """
    
    def __init__(
        self,
        rate_limiter: RedisRateLimiter,
        default_limit: int = 20,
        default_window: int = 60,
        spam_limit: int = 100,
        spam_window: int = 3600,
        block_duration: int = 3600
    ):
        """
        Инициализация middleware.
        
        Args:
            rate_limiter: Экземпляр RedisRateLimiter
            default_limit: Лимит по умолчанию (запросов)
            default_window: Окно по умолчанию (секунд)
            spam_limit: Лимит для определения спама
            spam_window: Окно для определения спама
            block_duration: Длительность блокировки спамеров (секунд)
        """
        super().__init__()
        self.rate_limiter = rate_limiter
        self.default_limit = default_limit
        self.default_window = default_window
        self.spam_limit = spam_limit
        self.spam_window = spam_window
        self.block_duration = block_duration
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Обработка события.
        
        Args:
            handler: Следующий обработчик
            event: Событие Telegram
            data: Данные контекста
            
        Returns:
            Результат обработки или None если заблокирован
        """
        # Получаем user_id
        user_id = None
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id
        
        if not user_id:
            # Если не можем определить пользователя, пропускаем
            return await handler(event, data)
        
        # Проверяем, не заблокирован ли пользователь
        block_key = f"blocked:{user_id}"
        is_blocked = await self.rate_limiter.redis.exists(
            self.rate_limiter._get_key(block_key)
        )
        
        if is_blocked:
            logger.warning(f"Blocked user {user_id} attempted to send message")
            
            if isinstance(event, Message):
                await event.answer(
                    "Вы временно заблокированы за спам. "
                    "Попробуйте позже."
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "Вы временно заблокированы за спам.",
                    show_alert=True
                )
            
            return None
        
        # Проверяем обычный rate limit
        rate_key = f"user:{user_id}"
        allowed, current_count, reset_time = await self.rate_limiter.check_rate_limit(
            rate_key,
            self.default_limit,
            self.default_window
        )
        
        if not allowed:
            logger.warning(
                f"Rate limit exceeded for user {user_id}: "
                f"{current_count}/{self.default_limit}"
            )
            
            # Проверяем на спам
            spam_key = f"spam:{user_id}"
            spam_allowed, spam_count, _ = await self.rate_limiter.check_rate_limit(
                spam_key,
                self.spam_limit,
                self.spam_window
            )
            
            if not spam_allowed:
                # Блокируем спамера
                await self._block_user(user_id)
                
                logger.error(
                    f"User {user_id} blocked for spam: "
                    f"{spam_count}/{self.spam_limit} in {self.spam_window}s"
                )
                
                if isinstance(event, Message):
                    await event.answer(
                        "Вы заблокированы за спам на "
                        f"{self.block_duration // 3600} часов."
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        f"Вы заблокированы за спам на "
                        f"{self.block_duration // 3600} часов.",
                        show_alert=True
                    )
                
                return None
            
            # Отправляем предупреждение
            if isinstance(event, Message):
                await event.answer(
                    f"Слишком много запросов. "
                    f"Попробуйте через {reset_time} секунд."
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    f"Слишком много запросов. "
                    f"Попробуйте через {reset_time} секунд.",
                    show_alert=True
                )
            
            return None
        
        # Добавляем rate_limiter в контекст для использования в декораторах
        data['rate_limiter'] = self.rate_limiter
        
        # Логируем активность
        await self._log_activity(user_id, event)
        
        # Продолжаем обработку
        return await handler(event, data)
    
    async def _block_user(self, user_id: int) -> None:
        """
        Заблокировать пользователя за спам.
        
        Args:
            user_id: ID пользователя
        """
        block_key = f"blocked:{user_id}"
        redis_key = self.rate_limiter._get_key(block_key)
        
        await self.rate_limiter.redis.setex(
            redis_key,
            self.block_duration,
            "1"
        )
        
        logger.error(
            f"User {user_id} blocked for {self.block_duration}s"
        )
    
    async def _log_activity(
        self,
        user_id: int,
        event: TelegramObject
    ) -> None:
        """
        Логировать активность пользователя.
        
        Args:
            user_id: ID пользователя
            event: Событие
        """
        activity_key = f"activity:{user_id}"
        
        try:
            if isinstance(event, Message):
                event_type = "message"
                event_data = event.text or event.caption or "media"
            elif isinstance(event, CallbackQuery):
                event_type = "callback"
                event_data = event.data
            else:
                event_type = "unknown"
                event_data = ""
            
            # Сохраняем последнюю активность
            await self.rate_limiter.redis.hset(
                self.rate_limiter._get_key(activity_key),
                mapping={
                    'type': event_type,
                    'data': event_data[:100],  # Ограничиваем длину
                    'timestamp': str(event.date.timestamp() if hasattr(event, 'date') else 0)
                }
            )
            
            # Устанавливаем TTL
            await self.rate_limiter.redis.expire(
                self.rate_limiter._get_key(activity_key),
                86400  # 24 часа
            )
            
        except Exception as e:
            logger.error(f"Error logging activity: {e}", exc_info=True)
    
    async def get_user_stats(self, user_id: int) -> dict:
        """
        Получить статистику пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь со статистикой
        """
        rate_key = f"user:{user_id}"
        spam_key = f"spam:{user_id}"
        block_key = f"blocked:{user_id}"
        activity_key = f"activity:{user_id}"
        
        try:
            # Получаем данные
            rate_stats = await self.rate_limiter.get_stats(rate_key)
            spam_stats = await self.rate_limiter.get_stats(spam_key)
            
            is_blocked = await self.rate_limiter.redis.exists(
                self.rate_limiter._get_key(block_key)
            )
            
            block_ttl = 0
            if is_blocked:
                block_ttl = await self.rate_limiter.redis.ttl(
                    self.rate_limiter._get_key(block_key)
                )
            
            activity = await self.rate_limiter.redis.hgetall(
                self.rate_limiter._get_key(activity_key)
            )
            
            return {
                'user_id': user_id,
                'rate_limit': rate_stats,
                'spam_check': spam_stats,
                'is_blocked': bool(is_blocked),
                'block_ttl': block_ttl,
                'last_activity': {
                    k.decode() if isinstance(k, bytes) else k: 
                    v.decode() if isinstance(v, bytes) else v
                    for k, v in activity.items()
                } if activity else None
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}", exc_info=True)
            return {
                'user_id': user_id,
                'error': str(e)
            }
    
    async def unblock_user(self, user_id: int) -> bool:
        """
        Разблокировать пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если успешно разблокирован
        """
        block_key = f"blocked:{user_id}"
        
        try:
            await self.rate_limiter.redis.delete(
                self.rate_limiter._get_key(block_key)
            )
            
            logger.info(f"User {user_id} unblocked")
            return True
            
        except Exception as e:
            logger.error(f"Error unblocking user: {e}", exc_info=True)
            return False