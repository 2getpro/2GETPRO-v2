"""
Обработчик ошибок для автоматической отправки в Sentry.

Включает:
- Декоратор для автоматической отправки ошибок
- Добавление контекста
- Группировка ошибок
- Игнорирование определенных ошибок
"""

from typing import Optional, Dict, Any, Callable, TypeVar, List
from functools import wraps
import sentry_sdk
from sentry_sdk import capture_exception as sentry_capture_exception
from sentry_sdk import capture_message as sentry_capture_message
import logging


# Type variable для декоратора
F = TypeVar('F', bound=Callable[..., Any])


# Список ошибок, которые нужно игнорировать
IGNORED_EXCEPTIONS = [
    KeyboardInterrupt,
    SystemExit,
]


def capture_exception(
    error: Exception,
    level: str = 'error',
    extra: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None,
    user: Optional[Dict[str, Any]] = None,
    fingerprint: Optional[List[str]] = None
) -> Optional[str]:
    """
    Захватить и отправить исключение в Sentry.
    
    Args:
        error: Исключение для отправки
        level: Уровень серьезности (fatal, error, warning, info, debug)
        extra: Дополнительные данные
        tags: Теги для группировки
        user: Информация о пользователе
        fingerprint: Fingerprint для группировки событий
    
    Returns:
        Event ID или None
    """
    # Проверяем, нужно ли игнорировать ошибку
    if type(error) in IGNORED_EXCEPTIONS:
        return None
    
    with sentry_sdk.push_scope() as scope:
        # Устанавливаем уровень
        scope.level = level
        
        # Добавляем extra данные
        if extra:
            for key, value in extra.items():
                scope.set_extra(key, value)
        
        # Добавляем теги
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)
        
        # Добавляем информацию о пользователе
        if user:
            scope.set_user(user)
        
        # Устанавливаем fingerprint для группировки
        if fingerprint:
            scope.fingerprint = fingerprint
        
        # Отправляем исключение
        event_id = sentry_capture_exception(error)
        
        logging.debug(f'Exception captured in Sentry: {event_id}')
        
        return event_id


def capture_message(
    message: str,
    level: str = 'info',
    extra: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None,
    user: Optional[Dict[str, Any]] = None,
    fingerprint: Optional[List[str]] = None
) -> Optional[str]:
    """
    Захватить и отправить сообщение в Sentry.
    
    Args:
        message: Сообщение для отправки
        level: Уровень серьезности (fatal, error, warning, info, debug)
        extra: Дополнительные данные
        tags: Теги для группировки
        user: Информация о пользователе
        fingerprint: Fingerprint для группировки событий
    
    Returns:
        Event ID или None
    """
    with sentry_sdk.push_scope() as scope:
        # Устанавливаем уровень
        scope.level = level
        
        # Добавляем extra данные
        if extra:
            for key, value in extra.items():
                scope.set_extra(key, value)
        
        # Добавляем теги
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)
        
        # Добавляем информацию о пользователе
        if user:
            scope.set_user(user)
        
        # Устанавливаем fingerprint для группировки
        if fingerprint:
            scope.fingerprint = fingerprint
        
        # Отправляем сообщение
        event_id = sentry_capture_message(message)
        
        logging.debug(f'Message captured in Sentry: {event_id}')
        
        return event_id


def error_handler(
    level: str = 'error',
    extra: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None,
    capture_locals: bool = False,
    reraise: bool = True,
    ignored_exceptions: Optional[List[type]] = None
) -> Callable[[F], F]:
    """
    Декоратор для автоматической отправки ошибок в Sentry.
    
    Args:
        level: Уровень серьезности
        extra: Дополнительные данные
        tags: Теги для группировки
        capture_locals: Захватывать локальные переменные
        reraise: Повторно выбрасывать исключение
        ignored_exceptions: Список исключений для игнорирования
    
    Returns:
        Декоратор
    
    Example:
        @error_handler(tags={'module': 'payment'})
        async def process_payment(payment_id: int):
            # код обработки платежа
            pass
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Проверяем, нужно ли игнорировать ошибку
                exceptions_to_ignore = IGNORED_EXCEPTIONS.copy()
                if ignored_exceptions:
                    exceptions_to_ignore.extend(ignored_exceptions)
                
                if type(e) not in exceptions_to_ignore:
                    # Собираем контекст
                    context_extra = extra.copy() if extra else {}
                    context_extra['function'] = func.__name__
                    context_extra['module'] = func.__module__
                    
                    # Добавляем аргументы функции
                    if args:
                        context_extra['args'] = str(args)
                    if kwargs:
                        context_extra['kwargs'] = str(kwargs)
                    
                    # Захватываем локальные переменные если нужно
                    if capture_locals:
                        import inspect
                        frame = inspect.currentframe()
                        if frame and frame.f_back:
                            context_extra['locals'] = str(frame.f_back.f_locals)
                    
                    # Отправляем в Sentry
                    capture_exception(
                        e,
                        level=level,
                        extra=context_extra,
                        tags=tags
                    )
                
                # Повторно выбрасываем исключение если нужно
                if reraise:
                    raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Проверяем, нужно ли игнорировать ошибку
                exceptions_to_ignore = IGNORED_EXCEPTIONS.copy()
                if ignored_exceptions:
                    exceptions_to_ignore.extend(ignored_exceptions)
                
                if type(e) not in exceptions_to_ignore:
                    # Собираем контекст
                    context_extra = extra.copy() if extra else {}
                    context_extra['function'] = func.__name__
                    context_extra['module'] = func.__module__
                    
                    # Добавляем аргументы функции
                    if args:
                        context_extra['args'] = str(args)
                    if kwargs:
                        context_extra['kwargs'] = str(kwargs)
                    
                    # Захватываем локальные переменные если нужно
                    if capture_locals:
                        import inspect
                        frame = inspect.currentframe()
                        if frame and frame.f_back:
                            context_extra['locals'] = str(frame.f_back.f_locals)
                    
                    # Отправляем в Sentry
                    capture_exception(
                        e,
                        level=level,
                        extra=context_extra,
                        tags=tags
                    )
                
                # Повторно выбрасываем исключение если нужно
                if reraise:
                    raise
        
        # Определяем, является ли функция асинхронной
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore
    
    return decorator


def add_error_context(
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    action: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None
) -> None:
    """
    Добавить контекст для последующих ошибок.
    
    Args:
        user_id: ID пользователя
        username: Имя пользователя
        action: Действие пользователя
        extra: Дополнительные данные
        tags: Теги для группировки
    """
    with sentry_sdk.configure_scope() as scope:
        # Добавляем информацию о пользователе
        if user_id or username:
            scope.set_user({
                'id': user_id,
                'username': username
            })
        
        # Добавляем действие
        if action:
            scope.set_tag('action', action)
        
        # Добавляем extra данные
        if extra:
            for key, value in extra.items():
                scope.set_extra(key, value)
        
        # Добавляем теги
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)


def clear_error_context() -> None:
    """Очистить контекст ошибок."""
    with sentry_sdk.configure_scope() as scope:
        scope.clear()


class SentryContextManager:
    """
    Контекстный менеджер для автоматического добавления контекста в Sentry.
    
    Example:
        async with SentryContextManager(user_id=123, action='payment'):
            await process_payment()
    """
    
    def __init__(
        self,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        action: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None
    ):
        """
        Инициализация контекстного менеджера.
        
        Args:
            user_id: ID пользователя
            username: Имя пользователя
            action: Действие пользователя
            extra: Дополнительные данные
            tags: Теги для группировки
        """
        self.user_id = user_id
        self.username = username
        self.action = action
        self.extra = extra
        self.tags = tags
    
    def __enter__(self):
        """Вход в контекст."""
        add_error_context(
            user_id=self.user_id,
            username=self.username,
            action=self.action,
            extra=self.extra,
            tags=self.tags
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Выход из контекста."""
        clear_error_context()
        return False
    
    async def __aenter__(self):
        """Асинхронный вход в контекст."""
        add_error_context(
            user_id=self.user_id,
            username=self.username,
            action=self.action,
            extra=self.extra,
            tags=self.tags
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный выход из контекста."""
        clear_error_context()
        return False