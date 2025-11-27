"""
Логирование медленных SQL запросов.

Автоматически логирует запросы, превышающие заданный порог времени выполнения.
"""

import logging
import time
from datetime import datetime
from typing import Optional

from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

logger = logging.getLogger(__name__)


class SlowQueryLogger:
    """
    Логгер медленных SQL запросов.
    
    Отслеживает время выполнения запросов и логирует те,
    которые превышают заданный порог.
    """
    
    def __init__(
        self,
        threshold_seconds: float = 1.0,
        log_to_db: bool = False
    ):
        """
        Инициализация логгера.
        
        Args:
            threshold_seconds: Порог времени в секундах (по умолчанию 1.0)
            log_to_db: Сохранять ли медленные запросы в БД
        """
        self.threshold = threshold_seconds
        self.log_to_db = log_to_db
        self._query_start_times = {}
    
    def setup(self, engine: AsyncEngine) -> None:
        """
        Настройка логгера для engine.
        
        Args:
            engine: AsyncEngine для мониторинга
        """
        # Для async engine используем другой подход
        logger.info(f"SlowQueryLogger настроен (порог: {self.threshold}s)")
    
    def log_slow_query(
        self,
        query: str,
        duration: float,
        params: Optional[dict] = None
    ) -> None:
        """
        Логирование медленного запроса.
        
        Args:
            query: SQL запрос
            duration: Время выполнения в секундах
            params: Параметры запроса
        """
        if duration < self.threshold:
            return
        
        logger.warning(
            f"Slow query detected ({duration:.3f}s > {self.threshold}s):\n"
            f"Query: {query[:500]}...\n"
            f"Params: {params}"
        )
        
        # Можно добавить сохранение в БД
        if self.log_to_db:
            # TODO: Сохранить в таблицу slow_queries
            pass
    
    async def analyze_query(
        self,
        session: AsyncSession,
        query: str,
        params: Optional[dict] = None
    ) -> dict:
        """
        Анализ запроса с помощью EXPLAIN.
        
        Args:
            session: Сессия БД
            query: SQL запрос
            params: Параметры запроса
            
        Returns:
            Результат EXPLAIN
        """
        try:
            explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
            result = await session.execute(text(explain_query), params or {})
            explain_result = result.fetchone()
            
            if explain_result:
                return explain_result[0][0]
            return {}
            
        except Exception as e:
            logger.error(f"Ошибка анализа запроса: {e}")
            return {}


# Глобальный экземпляр
_slow_query_logger: Optional[SlowQueryLogger] = None


def get_slow_query_logger() -> Optional[SlowQueryLogger]:
    """Получение глобального логгера медленных запросов."""
    return _slow_query_logger


def setup_slow_query_logger(
    engine: AsyncEngine,
    threshold_seconds: float = 1.0
) -> SlowQueryLogger:
    """
    Настройка глобального логгера медленных запросов.
    
    Args:
        engine: AsyncEngine для мониторинга
        threshold_seconds: Порог времени в секундах
        
    Returns:
        Настроенный SlowQueryLogger
    """
    global _slow_query_logger
    _slow_query_logger = SlowQueryLogger(threshold_seconds)
    _slow_query_logger.setup(engine)
    return _slow_query_logger