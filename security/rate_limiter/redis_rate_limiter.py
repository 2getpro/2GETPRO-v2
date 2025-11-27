"""
Redis-based rate limiter с использованием sliding window алгоритма.
"""

import time
from typing import Optional, Tuple
import redis.asyncio as redis
from redis.asyncio import Redis
import logging

logger = logging.getLogger(__name__)


class RedisRateLimiter:
    """
    Redis-based rate limiter для защиты от спама и DDoS атак.
    
    Использует sliding window алгоритм для точного подсчета запросов.
    """
    
    def __init__(self, redis_client: Redis, prefix: str = "rate_limit"):
        """
        Инициализация rate limiter.
        
        Args:
            redis_client: Async Redis клиент
            prefix: Префикс для ключей в Redis
        """
        self.redis = redis_client
        self.prefix = prefix
        
    def _get_key(self, key: str) -> str:
        """Получить полный ключ для Redis."""
        return f"{self.prefix}:{key}"
    
    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window: int
    ) -> Tuple[bool, int, int]:
        """
        Проверить rate limit для ключа.
        
        Args:
            key: Уникальный ключ (user_id, ip, endpoint и т.д.)
            limit: Максимальное количество запросов
            window: Временное окно в секундах
            
        Returns:
            Tuple[allowed, current_count, reset_time]:
                - allowed: Разрешен ли запрос
                - current_count: Текущее количество запросов
                - reset_time: Время до сброса счетчика (секунды)
        """
        redis_key = self._get_key(key)
        current_time = time.time()
        window_start = current_time - window
        
        try:
            # Используем pipeline для атомарности операций
            pipe = self.redis.pipeline()
            
            # Удаляем старые записи за пределами окна
            pipe.zremrangebyscore(redis_key, 0, window_start)
            
            # Получаем текущее количество запросов
            pipe.zcard(redis_key)
            
            # Добавляем текущий запрос
            pipe.zadd(redis_key, {str(current_time): current_time})
            
            # Устанавливаем TTL для автоматической очистки
            pipe.expire(redis_key, window + 1)
            
            results = await pipe.execute()
            current_count = results[1]
            
            # Проверяем, не превышен ли лимит
            allowed = current_count < limit
            reset_time = window
            
            if not allowed:
                # Если лимит превышен, удаляем последний запрос
                await self.redis.zrem(redis_key, str(current_time))
                
                # Вычисляем время до сброса
                oldest_request = await self.redis.zrange(redis_key, 0, 0, withscores=True)
                if oldest_request:
                    oldest_time = oldest_request[0][1]
                    reset_time = int(window - (current_time - oldest_time))
                    
            logger.debug(
                f"Rate limit check: key={key}, count={current_count}/{limit}, "
                f"allowed={allowed}, reset_in={reset_time}s"
            )
            
            return allowed, current_count, reset_time
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}", exc_info=True)
            # В случае ошибки разрешаем запрос (fail-open)
            return True, 0, window
    
    async def increment(self, key: str, window: int = 60) -> int:
        """
        Инкрементировать счетчик для ключа.
        
        Args:
            key: Уникальный ключ
            window: Временное окно в секундах
            
        Returns:
            Текущее количество запросов
        """
        redis_key = self._get_key(key)
        current_time = time.time()
        
        try:
            pipe = self.redis.pipeline()
            pipe.zadd(redis_key, {str(current_time): current_time})
            pipe.expire(redis_key, window + 1)
            pipe.zcard(redis_key)
            results = await pipe.execute()
            
            return results[2]
            
        except Exception as e:
            logger.error(f"Error incrementing rate limit: {e}", exc_info=True)
            return 0
    
    async def reset(self, key: str) -> bool:
        """
        Сбросить счетчик для ключа.
        
        Args:
            key: Уникальный ключ
            
        Returns:
            True если успешно сброшен
        """
        redis_key = self._get_key(key)
        
        try:
            await self.redis.delete(redis_key)
            logger.info(f"Rate limit reset for key: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting rate limit: {e}", exc_info=True)
            return False
    
    async def get_remaining(self, key: str, limit: int, window: int) -> int:
        """
        Получить количество оставшихся запросов.
        
        Args:
            key: Уникальный ключ
            limit: Максимальное количество запросов
            window: Временное окно в секундах
            
        Returns:
            Количество оставшихся запросов
        """
        redis_key = self._get_key(key)
        current_time = time.time()
        window_start = current_time - window
        
        try:
            # Удаляем старые записи
            await self.redis.zremrangebyscore(redis_key, 0, window_start)
            
            # Получаем текущее количество
            current_count = await self.redis.zcard(redis_key)
            
            remaining = max(0, limit - current_count)
            return remaining
            
        except Exception as e:
            logger.error(f"Error getting remaining requests: {e}", exc_info=True)
            return limit
    
    async def is_blocked(self, key: str, limit: int, window: int) -> bool:
        """
        Проверить, заблокирован ли ключ.
        
        Args:
            key: Уникальный ключ
            limit: Максимальное количество запросов
            window: Временное окно в секундах
            
        Returns:
            True если заблокирован
        """
        allowed, _, _ = await self.check_rate_limit(key, limit, window)
        return not allowed
    
    async def get_stats(self, key: str) -> dict:
        """
        Получить статистику по ключу.
        
        Args:
            key: Уникальный ключ
            
        Returns:
            Словарь со статистикой
        """
        redis_key = self._get_key(key)
        
        try:
            count = await self.redis.zcard(redis_key)
            ttl = await self.redis.ttl(redis_key)
            
            requests = await self.redis.zrange(redis_key, 0, -1, withscores=True)
            
            return {
                'key': key,
                'count': count,
                'ttl': ttl,
                'requests': [
                    {'timestamp': score, 'time': time.ctime(score)}
                    for _, score in requests
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}", exc_info=True)
            return {'key': key, 'count': 0, 'ttl': -1, 'requests': []}