"""
Модуль интеграции с Sentry для отслеживания ошибок.
"""

from .sentry_config import init_sentry
from .error_handler import error_handler, capture_exception, capture_message

__all__ = [
    'init_sentry',
    'error_handler',
    'capture_exception',
    'capture_message'
]