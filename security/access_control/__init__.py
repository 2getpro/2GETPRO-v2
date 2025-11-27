"""
Access Control модуль для управления правами доступа.
"""

from .permissions import (
    Role,
    Permission,
    PermissionChecker,
)
from .decorators import require_permission, require_role

__all__ = [
    'Role',
    'Permission',
    'PermissionChecker',
    'require_permission',
    'require_role',
]