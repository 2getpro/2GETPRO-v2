"""
Кастомные метрики для бизнес-логики и специфичных операций.

Включает метрики для:
- Конверсии
- LTV (Lifetime Value)
- Churn Rate
- Платежных систем
- Панели управления
"""

from typing import Optional, Dict, Any
from prometheus_client import Counter, Gauge, Histogram
from .prometheus_metrics import PrometheusMetrics
from functools import wraps
import time


class CustomMetrics:
    """Класс для управления кастомными метриками."""
    
    # Бизнес-метрики
    conversion_rate = Gauge(
        'conversion_rate',
        'Коэффициент конверсии (регистрация -> подписка)',
        ['period'],
        registry=PrometheusMetrics.registry
    )
    
    average_ltv = Gauge(
        'average_ltv',
        'Средний LTV пользователя',
        ['currency'],
        registry=PrometheusMetrics.registry
    )
    
    churn_rate = Gauge(
        'churn_rate',
        'Процент оттока пользователей',
        ['period'],
        registry=PrometheusMetrics.registry
    )
    
    average_subscription_duration = Gauge(
        'average_subscription_duration_days',
        'Средняя длительность подписки в днях',
        ['plan_type'],
        registry=PrometheusMetrics.registry
    )
    
    # Метрики платежных систем
    payment_system_availability = Gauge(
        'payment_system_availability',
        'Доступность платежной системы (0 или 1)',
        ['payment_system'],
        registry=PrometheusMetrics.registry
    )
    
    payment_system_response_time = Histogram(
        'payment_system_response_time_seconds',
        'Время ответа платежной системы',
        ['payment_system', 'operation'],
        registry=PrometheusMetrics.registry
    )
    
    payment_system_errors = Counter(
        'payment_system_errors_total',
        'Количество ошибок платежной системы',
        ['payment_system', 'error_code'],
        registry=PrometheusMetrics.registry
    )
    
    # Метрики панели управления
    panel_api_requests = Counter(
        'panel_api_requests_total',
        'Количество запросов к панели управления',
        ['endpoint', 'method', 'status'],
        registry=PrometheusMetrics.registry
    )
    
    panel_api_response_time = Histogram(
        'panel_api_response_time_seconds',
        'Время ответа API панели управления',
        ['endpoint'],
        registry=PrometheusMetrics.registry
    )
    
    panel_sync_operations = Counter(
        'panel_sync_operations_total',
        'Количество операций синхронизации с панелью',
        ['operation_type', 'status'],
        registry=PrometheusMetrics.registry
    )
    
    panel_sync_lag = Gauge(
        'panel_sync_lag_seconds',
        'Задержка синхронизации с панелью в секундах',
        registry=PrometheusMetrics.registry
    )
    
    # Метрики промокодов
    promo_code_redemption_rate = Gauge(
        'promo_code_redemption_rate',
        'Процент использования промокодов',
        ['promo_type'],
        registry=PrometheusMetrics.registry
    )
    
    promo_code_revenue = Counter(
        'promo_code_revenue_total',
        'Выручка от промокодов',
        ['promo_type', 'currency'],
        registry=PrometheusMetrics.registry
    )
    
    # Метрики реферальной программы
    referral_conversion_rate = Gauge(
        'referral_conversion_rate',
        'Коэффициент конверсии реферальной программы',
        registry=PrometheusMetrics.registry
    )
    
    referral_revenue = Counter(
        'referral_revenue_total',
        'Выручка от реферальной программы',
        ['currency'],
        registry=PrometheusMetrics.registry
    )
    
    active_referrers = Gauge(
        'active_referrers',
        'Количество активных рефереров',
        registry=PrometheusMetrics.registry
    )
    
    # Метрики триала
    trial_conversion_rate = Gauge(
        'trial_conversion_rate',
        'Процент конверсии из триала в платную подписку',
        registry=PrometheusMetrics.registry
    )
    
    active_trials = Gauge(
        'active_trials',
        'Количество активных триалов',
        registry=PrometheusMetrics.registry
    )
    
    @classmethod
    def set_conversion_rate(
        cls,
        period: str,
        rate: float
    ) -> None:
        """
        Установить коэффициент конверсии.
        
        Args:
            period: Период (daily, weekly, monthly)
            rate: Коэффициент конверсии (0-100)
        """
        cls.conversion_rate.labels(period=period).set(rate)
    
    @classmethod
    def set_average_ltv(
        cls,
        currency: str,
        ltv: float
    ) -> None:
        """
        Установить средний LTV.
        
        Args:
            currency: Валюта
            ltv: Средний LTV
        """
        cls.average_ltv.labels(currency=currency).set(ltv)
    
    @classmethod
    def set_churn_rate(
        cls,
        period: str,
        rate: float
    ) -> None:
        """
        Установить процент оттока.
        
        Args:
            period: Период (daily, weekly, monthly)
            rate: Процент оттока (0-100)
        """
        cls.churn_rate.labels(period=period).set(rate)
    
    @classmethod
    def set_average_subscription_duration(
        cls,
        plan_type: str,
        days: float
    ) -> None:
        """
        Установить среднюю длительность подписки.
        
        Args:
            plan_type: Тип плана
            days: Длительность в днях
        """
        cls.average_subscription_duration.labels(plan_type=plan_type).set(days)
    
    @classmethod
    def set_payment_system_availability(
        cls,
        payment_system: str,
        is_available: bool
    ) -> None:
        """
        Установить доступность платежной системы.
        
        Args:
            payment_system: Название платежной системы
            is_available: Доступна ли система
        """
        cls.payment_system_availability.labels(
            payment_system=payment_system
        ).set(1 if is_available else 0)
    
    @classmethod
    def observe_payment_system_response_time(
        cls,
        payment_system: str,
        operation: str,
        duration: float
    ) -> None:
        """
        Записать время ответа платежной системы.
        
        Args:
            payment_system: Название платежной системы
            operation: Тип операции
            duration: Длительность в секундах
        """
        cls.payment_system_response_time.labels(
            payment_system=payment_system,
            operation=operation
        ).observe(duration)
    
    @classmethod
    def increment_payment_system_errors(
        cls,
        payment_system: str,
        error_code: str
    ) -> None:
        """
        Увеличить счетчик ошибок платежной системы.
        
        Args:
            payment_system: Название платежной системы
            error_code: Код ошибки
        """
        cls.payment_system_errors.labels(
            payment_system=payment_system,
            error_code=error_code
        ).inc()
    
    @classmethod
    def increment_panel_api_requests(
        cls,
        endpoint: str,
        method: str,
        status: int
    ) -> None:
        """
        Увеличить счетчик запросов к панели.
        
        Args:
            endpoint: Endpoint API
            method: HTTP метод
            status: HTTP статус
        """
        cls.panel_api_requests.labels(
            endpoint=endpoint,
            method=method,
            status=str(status)
        ).inc()
    
    @classmethod
    def observe_panel_api_response_time(
        cls,
        endpoint: str,
        duration: float
    ) -> None:
        """
        Записать время ответа API панели.
        
        Args:
            endpoint: Endpoint API
            duration: Длительность в секундах
        """
        cls.panel_api_response_time.labels(
            endpoint=endpoint
        ).observe(duration)
    
    @classmethod
    def increment_panel_sync_operations(
        cls,
        operation_type: str,
        status: str
    ) -> None:
        """
        Увеличить счетчик операций синхронизации.
        
        Args:
            operation_type: Тип операции
            status: Статус (success, failed)
        """
        cls.panel_sync_operations.labels(
            operation_type=operation_type,
            status=status
        ).inc()
    
    @classmethod
    def set_panel_sync_lag(cls, lag_seconds: float) -> None:
        """
        Установить задержку синхронизации.
        
        Args:
            lag_seconds: Задержка в секундах
        """
        cls.panel_sync_lag.set(lag_seconds)
    
    @classmethod
    def set_promo_code_redemption_rate(
        cls,
        promo_type: str,
        rate: float
    ) -> None:
        """
        Установить процент использования промокодов.
        
        Args:
            promo_type: Тип промокода
            rate: Процент использования (0-100)
        """
        cls.promo_code_redemption_rate.labels(
            promo_type=promo_type
        ).set(rate)
    
    @classmethod
    def increment_promo_code_revenue(
        cls,
        promo_type: str,
        currency: str,
        amount: float
    ) -> None:
        """
        Увеличить выручку от промокодов.
        
        Args:
            promo_type: Тип промокода
            currency: Валюта
            amount: Сумма
        """
        cls.promo_code_revenue.labels(
            promo_type=promo_type,
            currency=currency
        ).inc(amount)
    
    @classmethod
    def set_referral_conversion_rate(cls, rate: float) -> None:
        """
        Установить коэффициент конверсии реферальной программы.
        
        Args:
            rate: Коэффициент конверсии (0-100)
        """
        cls.referral_conversion_rate.set(rate)
    
    @classmethod
    def increment_referral_revenue(
        cls,
        currency: str,
        amount: float
    ) -> None:
        """
        Увеличить выручку от реферальной программы.
        
        Args:
            currency: Валюта
            amount: Сумма
        """
        cls.referral_revenue.labels(currency=currency).inc(amount)
    
    @classmethod
    def set_active_referrers(cls, count: int) -> None:
        """
        Установить количество активных рефереров.
        
        Args:
            count: Количество рефереров
        """
        cls.active_referrers.set(count)
    
    @classmethod
    def set_trial_conversion_rate(cls, rate: float) -> None:
        """
        Установить процент конверсии из триала.
        
        Args:
            rate: Процент конверсии (0-100)
        """
        cls.trial_conversion_rate.set(rate)
    
    @classmethod
    def set_active_trials(cls, count: int) -> None:
        """
        Установить количество активных триалов.
        
        Args:
            count: Количество триалов
        """
        cls.active_trials.set(count)
    
    @staticmethod
    def track_payment_system(payment_system: str, operation: str):
        """
        Декоратор для отслеживания операций платежной системы.
        
        Args:
            payment_system: Название платежной системы
            operation: Тип операции
        """
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    CustomMetrics.set_payment_system_availability(
                        payment_system, True
                    )
                    return result
                except Exception as e:
                    CustomMetrics.set_payment_system_availability(
                        payment_system, False
                    )
                    CustomMetrics.increment_payment_system_errors(
                        payment_system,
                        type(e).__name__
                    )
                    raise
                finally:
                    duration = time.time() - start_time
                    CustomMetrics.observe_payment_system_response_time(
                        payment_system,
                        operation,
                        duration
                    )
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    CustomMetrics.set_payment_system_availability(
                        payment_system, True
                    )
                    return result
                except Exception as e:
                    CustomMetrics.set_payment_system_availability(
                        payment_system, False
                    )
                    CustomMetrics.increment_payment_system_errors(
                        payment_system,
                        type(e).__name__
                    )
                    raise
                finally:
                    duration = time.time() - start_time
                    CustomMetrics.observe_payment_system_response_time(
                        payment_system,
                        operation,
                        duration
                    )
            
            # Определяем, является ли функция асинхронной
            if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:
                return async_wrapper
            return sync_wrapper
        
        return decorator
    
    @staticmethod
    def track_panel_api(endpoint: str, method: str):
        """
        Декоратор для отслеживания запросов к панели управления.
        
        Args:
            endpoint: Endpoint API
            method: HTTP метод
        """
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                status = 200
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    status = 500
                    raise
                finally:
                    duration = time.time() - start_time
                    CustomMetrics.increment_panel_api_requests(
                        endpoint,
                        method,
                        status
                    )
                    CustomMetrics.observe_panel_api_response_time(
                        endpoint,
                        duration
                    )
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                status = 200
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    status = 500
                    raise
                finally:
                    duration = time.time() - start_time
                    CustomMetrics.increment_panel_api_requests(
                        endpoint,
                        method,
                        status
                    )
                    CustomMetrics.observe_panel_api_response_time(
                        endpoint,
                        duration
                    )
            
            # Определяем, является ли функция асинхронной
            if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:
                return async_wrapper
            return sync_wrapper
        
        return decorator