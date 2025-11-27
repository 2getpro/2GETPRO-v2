"""
Профилировщик производительности.

Предоставляет декоратор @profile для измерения времени выполнения
и использования памяти функций.
"""

import asyncio
import functools
import logging
import time
import tracemalloc
from typing import Callable, Any

from monitoring.metrics.prometheus_metrics import (
    function_duration_histogram,
    function_memory_gauge
)

logger = logging.getLogger(__name__)


class PerformanceProfiler:
    """
    Профилировщик производительности функций.
    
    Измеряет:
    - Время выполнения
    - Использование памяти
    - Экспортирует метрики в Prometheus
    """
    
    def __init__(self, func_name: str):
        """
        Инициализация профилировщика.
        
        Args:
            func_name: Имя функции для профилирования
        """
        self.func_name = func_name
        self.start_time = 0.0
        self.start_memory = 0
    
    def __enter__(self):
        """Начало профилирования."""
        self.start_time = time.perf_counter()
        tracemalloc.start()
        self.start_memory = tracemalloc.get_traced_memory()[0]
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Завершение профилирования."""
        # Измеряем время
        duration = time.perf_counter() - self.start_time
        
        # Измеряем память
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        memory_used = current_memory - self.start_memory
        tracemalloc.stop()
        
        # Логируем результаты
        logger.info(
            f"Performance [{self.func_name}]: "
            f"duration={duration:.3f}s, "
            f"memory={memory_used / 1024 / 1024:.2f}MB"
        )
        
        # Экспортируем метрики
        try:
            function_duration_histogram.labels(function=self.func_name).observe(duration)
            function_memory_gauge.labels(function=self.func_name).set(memory_used)
        except Exception as e:
            logger.warning(f"Ошибка экспорта метрик: {e}")


def profile(func: Callable) -> Callable:
    """
    Декоратор для профилирования функций.
    
    Автоматически измеряет время выполнения и использование памяти.
    Поддерживает как синхронные, так и асинхронные функции.
    
    Args:
        func: Функция для профилирования
        
    Returns:
        Декорированная функция
        
    Example:
        @profile
        async def expensive_operation():
            # Автоматическое измерение времени и памяти
            pass
    """
    func_name = f"{func.__module__}.{func.__name__}"
    is_async = asyncio.iscoroutinefunction(func)
    
    if is_async:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            with PerformanceProfiler(func_name):
                return await func(*args, **kwargs)
        return async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with PerformanceProfiler(func_name):
                return func(*args, **kwargs)
        return sync_wrapper


def profile_method(threshold_ms: float = 100.0):
    """
    Декоратор для профилирования методов с порогом.
    
    Логирует только если время выполнения превышает порог.
    
    Args:
        threshold_ms: Порог в миллисекундах
        
    Returns:
        Декоратор
        
    Example:
        @profile_method(threshold_ms=500)
        async def slow_method(self):
            # Логируется только если > 500ms
            pass
    """
    def decorator(func: Callable) -> Callable:
        func_name = f"{func.__module__}.{func.__name__}"
        is_async = asyncio.iscoroutinefunction(func)
        
        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                result = await func(*args, **kwargs)
                duration = (time.perf_counter() - start_time) * 1000
                
                if duration > threshold_ms:
                    logger.warning(
                        f"Slow method [{func_name}]: {duration:.2f}ms "
                        f"(threshold: {threshold_ms}ms)"
                    )
                
                return result
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                result = func(*args, **kwargs)
                duration = (time.perf_counter() - start_time) * 1000
                
                if duration > threshold_ms:
                    logger.warning(
                        f"Slow method [{func_name}]: {duration:.2f}ms "
                        f"(threshold: {threshold_ms}ms)"
                    )
                
                return result
            return sync_wrapper
    
    return decorator