"""
Декораторы для проверки прав доступа.
"""

import functools
from typing import Callable, Any
from aiogram.types import Message, CallbackQuery
import logging

from .permissions import Permission, Role, PermissionChecker

logger = logging.getLogger(__name__)


def require_permission(permission: Permission):
    """
    Декоратор для проверки разрешения.
    
    Args:
        permission: Требуемое разрешение
        
    Example:
        @require_permission(Permission.MANAGE_USERS)
        async def delete_user(message: Message):
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Получаем checker из контекста
            checker: PermissionChecker = kwargs.get('permission_checker')
            
            if not checker:
                logger.error(f"PermissionChecker not provided for {func.__name__}")
                return None
            
            # Получаем user_id
            user_id = None
            for arg in args:
                if isinstance(arg, (Message, CallbackQuery)):
                    user_id = arg.from_user.id
                    break
            
            if not user_id:
                logger.error(f"Could not determine user_id for {func.__name__}")
                return None
            
            # Проверяем разрешение
            has_perm = await checker.has_permission(user_id, permission)
            
            if not has_perm:
                logger.warning(
                    f"User {user_id} denied access to {func.__name__}: "
                    f"missing permission {permission}"
                )
                
                # Отправляем сообщение об ошибке
                for arg in args:
                    if isinstance(arg, Message):
                        await arg.answer("У вас нет прав для выполнения этого действия.")
                        break
                    elif isinstance(arg, CallbackQuery):
                        await arg.answer(
                            "У вас нет прав для выполнения этого действия.",
                            show_alert=True
                        )
                        break
                
                return None
            
            # Выполняем функцию
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_role(role: Role):
    """
    Декоратор для проверки роли.
    
    Args:
        role: Требуемая роль
        
    Example:
        @require_role(Role.ADMIN)
        async def admin_panel(message: Message):
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            checker: PermissionChecker = kwargs.get('permission_checker')
            
            if not checker:
                logger.error(f"PermissionChecker not provided for {func.__name__}")
                return None
            
            user_id = None
            for arg in args:
                if isinstance(arg, (Message, CallbackQuery)):
                    user_id = arg.from_user.id
                    break
            
            if not user_id:
                logger.error(f"Could not determine user_id for {func.__name__}")
                return None
            
            has_role = await checker.has_role(user_id, role)
            
            if not has_role:
                logger.warning(
                    f"User {user_id} denied access to {func.__name__}: "
                    f"missing role {role}"
                )
                
                for arg in args:
                    if isinstance(arg, Message):
                        await arg.answer("Эта функция доступна только администраторам.")
                        break
                    elif isinstance(arg, CallbackQuery):
                        await arg.answer(
                            "Эта функция доступна только администраторам.",
                            show_alert=True
                        )
                        break
                
                return None
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator