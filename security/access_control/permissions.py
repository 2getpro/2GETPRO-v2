"""
Система прав доступа и ролей.
"""

from enum import Enum
from typing import Set, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """Роли пользователей."""
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class Permission(str, Enum):
    """Разрешения для действий."""
    # Базовые разрешения
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    
    # Управление пользователями
    MANAGE_USERS = "manage_users"
    BAN_USERS = "ban_users"
    VIEW_USER_DATA = "view_user_data"
    
    # Управление подписками
    MANAGE_SUBSCRIPTIONS = "manage_subscriptions"
    GRANT_SUBSCRIPTION = "grant_subscription"
    
    # Управление платежами
    VIEW_PAYMENTS = "view_payments"
    MANAGE_PAYMENTS = "manage_payments"
    REFUND_PAYMENTS = "refund_payments"
    
    # Управление промокодами
    CREATE_PROMO = "create_promo"
    MANAGE_PROMO = "manage_promo"
    
    # Управление рекламой
    MANAGE_ADS = "manage_ads"
    
    # Управление системой
    VIEW_LOGS = "view_logs"
    MANAGE_SETTINGS = "manage_settings"
    ACCESS_ADMIN_PANEL = "access_admin_panel"
    
    # Рассылки
    SEND_BROADCAST = "send_broadcast"
    
    # Статистика
    VIEW_STATISTICS = "view_statistics"
    EXPORT_DATA = "export_data"


# Маппинг ролей на разрешения
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.USER: {
        Permission.READ,
    },
    Role.MODERATOR: {
        Permission.READ,
        Permission.WRITE,
        Permission.VIEW_USER_DATA,
        Permission.VIEW_PAYMENTS,
        Permission.VIEW_STATISTICS,
        Permission.MANAGE_ADS,
    },
    Role.ADMIN: {
        Permission.READ,
        Permission.WRITE,
        Permission.DELETE,
        Permission.MANAGE_USERS,
        Permission.BAN_USERS,
        Permission.VIEW_USER_DATA,
        Permission.MANAGE_SUBSCRIPTIONS,
        Permission.GRANT_SUBSCRIPTION,
        Permission.VIEW_PAYMENTS,
        Permission.MANAGE_PAYMENTS,
        Permission.CREATE_PROMO,
        Permission.MANAGE_PROMO,
        Permission.MANAGE_ADS,
        Permission.VIEW_LOGS,
        Permission.ACCESS_ADMIN_PANEL,
        Permission.SEND_BROADCAST,
        Permission.VIEW_STATISTICS,
    },
    Role.SUPER_ADMIN: set(Permission),  # Все разрешения
}


class PermissionChecker:
    """
    Проверка прав доступа пользователей.
    """
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        """
        Инициализация checker.
        
        Args:
            db_session: Сессия БД для проверки прав из базы
        """
        self.db_session = db_session
        # Кэш прав пользователей
        self._cache: Dict[int, Set[Permission]] = {}
    
    async def has_permission(
        self,
        user_id: int,
        permission: Permission,
        use_cache: bool = True
    ) -> bool:
        """
        Проверить, есть ли у пользователя разрешение.
        
        Args:
            user_id: ID пользователя
            permission: Требуемое разрешение
            use_cache: Использовать ли кэш
            
        Returns:
            True если есть разрешение
        """
        # Проверяем кэш
        if use_cache and user_id in self._cache:
            return permission in self._cache[user_id]
        
        # Получаем роль пользователя
        role = await self._get_user_role(user_id)
        
        if not role:
            logger.warning(f"User {user_id} has no role")
            return False
        
        # Получаем разрешения для роли
        permissions = ROLE_PERMISSIONS.get(role, set())
        
        # Кэшируем
        if use_cache:
            self._cache[user_id] = permissions
        
        has_perm = permission in permissions
        
        logger.debug(
            f"Permission check: user={user_id}, role={role}, "
            f"permission={permission}, result={has_perm}"
        )
        
        return has_perm
    
    async def has_role(self, user_id: int, role: Role) -> bool:
        """
        Проверить, есть ли у пользователя роль.
        
        Args:
            user_id: ID пользователя
            role: Требуемая роль
            
        Returns:
            True если есть роль
        """
        user_role = await self._get_user_role(user_id)
        return user_role == role
    
    async def has_any_role(self, user_id: int, roles: Set[Role]) -> bool:
        """
        Проверить, есть ли у пользователя хотя бы одна из ролей.
        
        Args:
            user_id: ID пользователя
            roles: Множество ролей
            
        Returns:
            True если есть хотя бы одна роль
        """
        user_role = await self._get_user_role(user_id)
        return user_role in roles
    
    async def grant_permission(
        self,
        user_id: int,
        permission: Permission
    ) -> bool:
        """
        Выдать разрешение пользователю.
        
        Args:
            user_id: ID пользователя
            permission: Разрешение
            
        Returns:
            True если успешно выдано
        """
        try:
            # Получаем текущие разрешения
            if user_id not in self._cache:
                role = await self._get_user_role(user_id)
                self._cache[user_id] = ROLE_PERMISSIONS.get(role, set()).copy()
            
            # Добавляем разрешение
            self._cache[user_id].add(permission)
            
            # Сохраняем в БД если есть сессия
            if self.db_session:
                await self._save_custom_permission(user_id, permission)
            
            logger.info(f"Granted permission {permission} to user {user_id}")
            return True
            
        except Exception as e:
            logger.error(
                f"Error granting permission to user {user_id}: {e}",
                exc_info=True
            )
            return False
    
    async def revoke_permission(
        self,
        user_id: int,
        permission: Permission
    ) -> bool:
        """
        Отозвать разрешение у пользователя.
        
        Args:
            user_id: ID пользователя
            permission: Разрешение
            
        Returns:
            True если успешно отозвано
        """
        try:
            # Удаляем из кэша
            if user_id in self._cache:
                self._cache[user_id].discard(permission)
            
            # Удаляем из БД если есть сессия
            if self.db_session:
                await self._remove_custom_permission(user_id, permission)
            
            logger.info(f"Revoked permission {permission} from user {user_id}")
            return True
            
        except Exception as e:
            logger.error(
                f"Error revoking permission from user {user_id}: {e}",
                exc_info=True
            )
            return False
    
    async def get_user_permissions(self, user_id: int) -> Set[Permission]:
        """
        Получить все разрешения пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Множество разрешений
        """
        # Проверяем кэш
        if user_id in self._cache:
            return self._cache[user_id].copy()
        
        # Получаем роль
        role = await self._get_user_role(user_id)
        
        if not role:
            return set()
        
        # Получаем базовые разрешения роли
        permissions = ROLE_PERMISSIONS.get(role, set()).copy()
        
        # Добавляем кастомные разрешения из БД
        if self.db_session:
            custom_perms = await self._get_custom_permissions(user_id)
            permissions.update(custom_perms)
        
        # Кэшируем
        self._cache[user_id] = permissions
        
        return permissions
    
    async def _get_user_role(self, user_id: int) -> Optional[Role]:
        """
        Получить роль пользователя из БД.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Роль пользователя или None
        """
        if not self.db_session:
            # Если нет сессии БД, возвращаем роль USER по умолчанию
            return Role.USER
        
        try:
            from db.models import User
            
            result = await self.db_session.execute(
                select(User.role).where(User.telegram_id == user_id)
            )
            role_str = result.scalar_one_or_none()
            
            if role_str:
                return Role(role_str)
            
            return Role.USER
            
        except Exception as e:
            logger.error(f"Error getting user role: {e}", exc_info=True)
            return Role.USER
    
    async def _get_custom_permissions(self, user_id: int) -> Set[Permission]:
        """Получить кастомные разрешения пользователя из БД."""
        # Заглушка - в реальной реализации нужна таблица для кастомных разрешений
        return set()
    
    async def _save_custom_permission(
        self,
        user_id: int,
        permission: Permission
    ) -> None:
        """Сохранить кастомное разрешение в БД."""
        # Заглушка - в реальной реализации нужна таблица для кастомных разрешений
        pass
    
    async def _remove_custom_permission(
        self,
        user_id: int,
        permission: Permission
    ) -> None:
        """Удалить кастомное разрешение из БД."""
        # Заглушка - в реальной реализации нужна таблица для кастомных разрешений
        pass
    
    def clear_cache(self, user_id: Optional[int] = None) -> None:
        """
        Очистить кэш разрешений.
        
        Args:
            user_id: ID пользователя (если None, очищается весь кэш)
        """
        if user_id:
            self._cache.pop(user_id, None)
            logger.debug(f"Cleared permission cache for user {user_id}")
        else:
            self._cache.clear()
            logger.debug("Cleared all permission cache")