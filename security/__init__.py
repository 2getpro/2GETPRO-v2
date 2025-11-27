"""
Модуль безопасности для 2GETPRO_v2.

Включает:
- Rate limiting
- Webhook validation
- Secrets management
- Access control
- Audit logging
"""

from .security_manager import setup_security, SecurityManager

__all__ = [
    'setup_security',
    'SecurityManager',
]