"""
Декораторы для rate limiting.
"""

import functools
from typing import Callable, Optional, Any
from aiogram import types
from aiogram.types import Message, CallbackQuery
import logging

from .redis_rate_limiter import RedisRateLimiter

logger = logging.getLogger(__name__)


def rate_limit(
    limit: int = 10,
    window: int = 60,
    key_func: Optional[Callable] = None,
    error_message: str = "Слишком много запросов. Попробуйте позже."
):
    """
    Декоратор для rate limiting функций.
    
    Args:
        limit: Максимальное количество запросов
        window: Временное окно в секундах
        key_func: Функция для генерации ключа (по умолчанию использует user_id)
        error_message: Сообщение об ошибке при превышении лимита
        
    Example:
        @rate_limit(limit=10, window=60)
        async def send_message(message: Message):
            await message.answer("Hello!")
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Получаем rate limiter из контекста
            rate_limiter = kwargs.get('rate_limiter')
            if not rate_limiter:
                # Если rate limiter не передан, выполняем функцию без проверки
                logger.warning(f"Rate limiter not provided for {func.__name__}")
                return await func(*args, **kwargs)
            
            # Определяем ключ для rate limiting
            key = None
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                # Пытаемся получить user_id из аргументов
                for arg in args:
                    if isinstance(arg, (Message, CallbackQuery)):
                        key = f"user:{arg.from_user.id}:{func.__name__}"
                        break
            
            if not key:
                logger.warning(f"Could not determine rate limit key for {func.__name__}")
                return await func(*args, **kwargs)
            
            # Проверяем rate limit
            allowed, current_count, reset_time = await rate_limiter.check_rate_limit(
                key, limit, window
            )
            
            if not allowed:
                logger.warning(
                    f"Rate limit exceeded: key={key}, count={current_count}/{limit}, "
                    f"reset_in={reset_time}s"
                )
                
                # Отправляем сообщение об ошибке
                for arg in args:
                    if isinstance(arg, Message):
                        await arg.answer(
                            f"{error_message}\n"
                            f"Попробуйте через {reset_time} секунд."
                        )
                        break
                    elif isinstance(arg, CallbackQuery):
                        await arg.answer(
                            f"{error_message} Попробуйте через {reset_time} секунд.",
                            show_alert=True
                        )
                        break
                
                return None
            
            # Выполняем функцию
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def rate_limit_user(
    limit: int = 100,
    window: int = 3600,
    error_message: str = "Вы превысили лимит запросов."
):
    """
    Декоратор для rate limiting на пользователя.
    
    Args:
        limit: Максимальное количество запросов на пользователя
        window: Временное окно в секундах (по умолчанию 1 час)
        error_message: Сообщение об ошибке
        
    Example:
        @rate_limit_user(limit=100, window=3600)
        async def handle_command(message: Message):
            pass
    """
    def key_func(*args, **kwargs):
        for arg in args:
            if isinstance(arg, (Message, CallbackQuery)):
                return f"user:{arg.from_user.id}"
        return None
    
    return rate_limit(
        limit=limit,
        window=window,
        key_func=key_func,
        error_message=error_message
    )


def rate_limit_ip(
    limit: int = 1000,
    window: int = 3600,
    error_message: str = "Слишком много запросов с вашего IP."
):
    """
    Декоратор для rate limiting на IP адрес.
    
    Args:
        limit: Максимальное количество запросов с IP
        window: Временное окно в секундах (по умолчанию 1 час)
        error_message: Сообщение об ошибке
        
    Example:
        @rate_limit_ip(limit=1000, window=3600)
        async def handle_webhook(request):
            pass
    """
    def key_func(*args, **kwargs):
        # Для webhook запросов
        request = kwargs.get('request')
        if request:
            ip = request.headers.get('X-Forwarded-For', request.remote)
            return f"ip:{ip}"
        return None
    
    return rate_limit(
        limit=limit,
        window=window,
        key_func=key_func,
        error_message=error_message
    )


def rate_limit_endpoint(
    endpoint: str,
    limit: int = 100,
    window: int = 60,
    error_message: str = "Слишком много запросов к этому endpoint."
):
    """
    Декоратор для rate limiting на endpoint.
    
    Args:
        endpoint: Название endpoint
        limit: Максимальное количество запросов
        window: Временное окно в секундах
        error_message: Сообщение об ошибке
        
    Example:
        @rate_limit_endpoint('payment', limit=10, window=60)
        async def handle_payment(message: Message):
            pass
    """
    def key_func(*args, **kwargs):
        for arg in args:
            if isinstance(arg, (Message, CallbackQuery)):
                return f"endpoint:{endpoint}:{arg.from_user.id}"
        return f"endpoint:{endpoint}"
    
    return rate_limit(
        limit=limit,
        window=window,
        key_func=key_func,
        error_message=error_message
    )


def rate_limit_global(
    limit: int = 10000,
    window: int = 60,
    error_message: str = "Система перегружена. Попробуйте позже."
):
    """
    Декоратор для глобального rate limiting.
    
    Args:
        limit: Максимальное количество запросов глобально
        window: Временное окно в секундах
        error_message: Сообщение об ошибке
        
    Example:
        @rate_limit_global(limit=10000, window=60)
        async def handle_request():
            pass
    """
    def key_func(*args, **kwargs):
        return "global"
    
    return rate_limit(
        limit=limit,
        window=window,
        key_func=key_func,
        error_message=error_message
    )