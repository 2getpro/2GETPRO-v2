"""
Модуль мониторинга и логирования для 2GETPRO_v2.

Включает:
- Prometheus метрики
- Health checks
- Sentry интеграцию
- Структурированное логирование
"""

from .monitor import setup_monitoring

__all__ = ['setup_monitoring']