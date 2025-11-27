"""
Модуль оптимизации базы данных.

Предоставляет инструменты для оптимизации SQL запросов,
управления индексами и connection pooling.
"""

from .query_optimizer import QueryOptimizer
from .connection_pool import setup_connection_pool

__all__ = ['QueryOptimizer', 'setup_connection_pool']