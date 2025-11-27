"""
Настройка connection pooling для SQLAlchemy.

Оптимизирует управление соединениями с базой данных для
повышения производительности и надежности.
"""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.pool import NullPool, QueuePool

logger = logging.getLogger(__name__)


def setup_connection_pool(
    database_url: str,
    pool_size: int = 20,
    max_overflow: int = 10,
    pool_timeout: int = 30,
    pool_recycle: int = 3600,
    pool_pre_ping: bool = True,
    echo: bool = False,
    echo_pool: bool = False
) -> AsyncEngine:
    """
    Настройка оптимизированного connection pool для SQLAlchemy.
    
    Args:
        database_url: URL подключения к базе данных
        pool_size: Размер пула соединений (по умолчанию 20)
        max_overflow: Максимальное количество дополнительных соединений (по умолчанию 10)
        pool_timeout: Таймаут ожидания соединения в секундах (по умолчанию 30)
        pool_recycle: Время переподключения в секундах (по умолчанию 3600 - 1 час)
        pool_pre_ping: Проверка соединения перед использованием (по умолчанию True)
        echo: Логирование SQL запросов (по умолчанию False)
        echo_pool: Логирование событий пула (по умолчанию False)
        
    Returns:
        Настроенный AsyncEngine
        
    Example:
        engine = setup_connection_pool(
            database_url="postgresql+asyncpg://user:pass@localhost/db",
            pool_size=20,
            max_overflow=10
        )
    """
    logger.info(f"Настройка connection pool для {database_url}")
    logger.info(f"Параметры пула: size={pool_size}, max_overflow={max_overflow}, "
                f"timeout={pool_timeout}s, recycle={pool_recycle}s")
    
    # Создаем engine с оптимизированными настройками пула
    engine = create_async_engine(
        database_url,
        # Настройки пула соединений
        poolclass=QueuePool,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        pool_pre_ping=pool_pre_ping,
        
        # Настройки логирования
        echo=echo,
        echo_pool=echo_pool,
        
        # Дополнительные настройки
        future=True,
        
        # Параметры для asyncpg
        connect_args={
            "server_settings": {
                "application_name": "2GETPRO_v2",
                "jit": "off"  # Отключаем JIT для стабильности
            },
            "command_timeout": 60,  # Таймаут команд 60 секунд
            "timeout": 10  # Таймаут подключения 10 секунд
        }
    )
    
    logger.info("Connection pool успешно настроен")
    return engine


def setup_connection_pool_for_testing(
    database_url: str,
    echo: bool = True
) -> AsyncEngine:
    """
    Настройка connection pool для тестирования.
    
    Использует NullPool для изоляции тестов.
    
    Args:
        database_url: URL подключения к базе данных
        echo: Логирование SQL запросов
        
    Returns:
        Настроенный AsyncEngine для тестирования
    """
    logger.info("Настройка connection pool для тестирования")
    
    engine = create_async_engine(
        database_url,
        poolclass=NullPool,  # Без пула для тестов
        echo=echo,
        future=True
    )
    
    logger.info("Test connection pool настроен")
    return engine


async def get_pool_status(engine: AsyncEngine) -> dict:
    """
    Получение статуса connection pool.
    
    Args:
        engine: AsyncEngine с настроенным пулом
        
    Returns:
        Словарь со статистикой пула
    """
    pool = engine.pool
    
    status = {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "total_connections": pool.size() + pool.overflow()
    }
    
    logger.debug(f"Pool status: {status}")
    return status


async def close_connection_pool(engine: AsyncEngine) -> None:
    """
    Корректное закрытие connection pool.
    
    Args:
        engine: AsyncEngine для закрытия
    """
    logger.info("Закрытие connection pool")
    await engine.dispose()
    logger.info("Connection pool закрыт")


class ConnectionPoolMonitor:
    """
    Мониторинг состояния connection pool.
    
    Отслеживает метрики пула и логирует предупреждения
    при достижении пороговых значений.
    """
    
    def __init__(
        self,
        engine: AsyncEngine,
        warning_threshold: float = 0.8,
        critical_threshold: float = 0.95
    ):
        """
        Инициализация монитора.
        
        Args:
            engine: AsyncEngine для мониторинга
            warning_threshold: Порог предупреждения (80% от pool_size)
            critical_threshold: Критический порог (95% от pool_size)
        """
        self.engine = engine
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.pool = engine.pool
    
    async def check_pool_health(self) -> dict:
        """
        Проверка здоровья пула соединений.
        
        Returns:
            Словарь с метриками и статусом здоровья
        """
        status = await get_pool_status(self.engine)
        
        # Вычисляем использование пула
        total_capacity = self.pool.size() + self.pool._max_overflow
        usage_ratio = status["total_connections"] / total_capacity if total_capacity > 0 else 0
        
        # Определяем статус здоровья
        health_status = "healthy"
        if usage_ratio >= self.critical_threshold:
            health_status = "critical"
            logger.error(f"Connection pool критически загружен: {usage_ratio:.1%}")
        elif usage_ratio >= self.warning_threshold:
            health_status = "warning"
            logger.warning(f"Connection pool сильно загружен: {usage_ratio:.1%}")
        
        return {
            **status,
            "usage_ratio": usage_ratio,
            "health_status": health_status,
            "capacity": total_capacity
        }
    
    async def log_pool_metrics(self) -> None:
        """Логирование метрик пула."""
        health = await self.check_pool_health()
        logger.info(
            f"Pool metrics: "
            f"connections={health['total_connections']}/{health['capacity']}, "
            f"usage={health['usage_ratio']:.1%}, "
            f"status={health['health_status']}"
        )