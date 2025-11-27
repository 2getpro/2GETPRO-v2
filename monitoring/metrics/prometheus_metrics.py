"""
Prometheus метрики для мониторинга приложения.

Включает метрики для:
- HTTP запросов
- Ошибок
- Платежей
- Времени ответа
- Активных пользователей
"""

from typing import Optional
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
import time
from functools import wraps


class PrometheusMetrics:
    """Класс для управления Prometheus метриками."""
    
    # Реестр метрик
    registry = CollectorRegistry()
    
    # Counter метрики
    http_requests_total = Counter(
        'http_requests_total',
        'Общее количество HTTP запросов',
        ['method', 'endpoint', 'status'],
        registry=registry
    )
    
    bot_messages_total = Counter(
        'bot_messages_total',
        'Общее количество сообщений бота',
        ['handler', 'status'],
        registry=registry
    )
    
    errors_total = Counter(
        'errors_total',
        'Общее количество ошибок',
        ['error_type', 'module'],
        registry=registry
    )
    
    payment_requests_total = Counter(
        'payment_requests_total',
        'Общее количество запросов на оплату',
        ['payment_system', 'status'],
        registry=registry
    )
    
    payment_success_total = Counter(
        'payment_success_total',
        'Количество успешных платежей',
        ['payment_system'],
        registry=registry
    )
    
    payment_failed_total = Counter(
        'payment_failed_total',
        'Количество неудачных платежей',
        ['payment_system', 'reason'],
        registry=registry
    )
    
    subscription_created_total = Counter(
        'subscription_created_total',
        'Количество созданных подписок',
        ['plan_type'],
        registry=registry
    )
    
    subscription_renewed_total = Counter(
        'subscription_renewed_total',
        'Количество продленных подписок',
        ['plan_type'],
        registry=registry
    )
    
    subscription_cancelled_total = Counter(
        'subscription_cancelled_total',
        'Количество отмененных подписок',
        ['reason'],
        registry=registry
    )
    
    promo_code_used_total = Counter(
        'promo_code_used_total',
        'Количество использованных промокодов',
        ['promo_type'],
        registry=registry
    )
    
    referral_registrations_total = Counter(
        'referral_registrations_total',
        'Количество регистраций по реферальным ссылкам',
        registry=registry
    )
    
    # Histogram метрики
    http_request_duration_seconds = Histogram(
        'http_request_duration_seconds',
        'Длительность HTTP запросов в секундах',
        ['method', 'endpoint'],
        registry=registry
    )
    
    bot_handler_duration_seconds = Histogram(
        'bot_handler_duration_seconds',
        'Длительность обработки хендлеров бота в секундах',
        ['handler'],
        registry=registry
    )
    
    payment_processing_duration_seconds = Histogram(
        'payment_processing_duration_seconds',
        'Длительность обработки платежей в секундах',
        ['payment_system'],
        registry=registry
    )
    
    database_query_duration_seconds = Histogram(
        'database_query_duration_seconds',
        'Длительность запросов к БД в секундах',
        ['query_type'],
        registry=registry
    )
    
    # Gauge метрики
    active_users = Gauge(
        'active_users',
        'Количество активных пользователей',
        registry=registry
    )
    
    active_subscriptions = Gauge(
        'active_subscriptions',
        'Количество активных подписок',
        ['plan_type'],
        registry=registry
    )
    
    total_users = Gauge(
        'total_users',
        'Общее количество пользователей',
        registry=registry
    )
    
    database_connections = Gauge(
        'database_connections',
        'Количество активных подключений к БД',
        registry=registry
    )
    
    cache_size = Gauge(
        'cache_size',
        'Размер кэша',
        ['cache_type'],
        registry=registry
    )
    
    balance_total = Gauge(
        'balance_total',
        'Общий баланс пользователей',
        registry=registry
    )
    
    revenue_total = Gauge(
        'revenue_total',
        'Общая выручка',
        ['currency'],
        registry=registry
    )
    
    @classmethod
    def increment_http_requests(
        cls,
        method: str,
        endpoint: str,
        status: int
    ) -> None:
        """Увеличить счетчик HTTP запросов."""
        cls.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=str(status)
        ).inc()
    
    @classmethod
    def increment_bot_messages(
        cls,
        handler: str,
        status: str = 'success'
    ) -> None:
        """Увеличить счетчик сообщений бота."""
        cls.bot_messages_total.labels(
            handler=handler,
            status=status
        ).inc()
    
    @classmethod
    def increment_errors(
        cls,
        error_type: str,
        module: str
    ) -> None:
        """Увеличить счетчик ошибок."""
        cls.errors_total.labels(
            error_type=error_type,
            module=module
        ).inc()
    
    @classmethod
    def increment_payment_requests(
        cls,
        payment_system: str,
        status: str = 'pending'
    ) -> None:
        """Увеличить счетчик запросов на оплату."""
        cls.payment_requests_total.labels(
            payment_system=payment_system,
            status=status
        ).inc()
    
    @classmethod
    def increment_payment_success(
        cls,
        payment_system: str
    ) -> None:
        """Увеличить счетчик успешных платежей."""
        cls.payment_success_total.labels(
            payment_system=payment_system
        ).inc()
    
    @classmethod
    def increment_payment_failed(
        cls,
        payment_system: str,
        reason: str
    ) -> None:
        """Увеличить счетчик неудачных платежей."""
        cls.payment_failed_total.labels(
            payment_system=payment_system,
            reason=reason
        ).inc()
    
    @classmethod
    def increment_subscription_created(
        cls,
        plan_type: str
    ) -> None:
        """Увеличить счетчик созданных подписок."""
        cls.subscription_created_total.labels(
            plan_type=plan_type
        ).inc()
    
    @classmethod
    def increment_subscription_renewed(
        cls,
        plan_type: str
    ) -> None:
        """Увеличить счетчик продленных подписок."""
        cls.subscription_renewed_total.labels(
            plan_type=plan_type
        ).inc()
    
    @classmethod
    def increment_subscription_cancelled(
        cls,
        reason: str
    ) -> None:
        """Увеличить счетчик отмененных подписок."""
        cls.subscription_cancelled_total.labels(
            reason=reason
        ).inc()
    
    @classmethod
    def increment_promo_code_used(
        cls,
        promo_type: str
    ) -> None:
        """Увеличить счетчик использованных промокодов."""
        cls.promo_code_used_total.labels(
            promo_type=promo_type
        ).inc()
    
    @classmethod
    def increment_referral_registrations(cls) -> None:
        """Увеличить счетчик регистраций по реферальным ссылкам."""
        cls.referral_registrations_total.inc()
    
    @classmethod
    def observe_http_request_duration(
        cls,
        method: str,
        endpoint: str,
        duration: float
    ) -> None:
        """Записать длительность HTTP запроса."""
        cls.http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    @classmethod
    def observe_bot_handler_duration(
        cls,
        handler: str,
        duration: float
    ) -> None:
        """Записать длительность обработки хендлера."""
        cls.bot_handler_duration_seconds.labels(
            handler=handler
        ).observe(duration)
    
    @classmethod
    def observe_payment_processing_duration(
        cls,
        payment_system: str,
        duration: float
    ) -> None:
        """Записать длительность обработки платежа."""
        cls.payment_processing_duration_seconds.labels(
            payment_system=payment_system
        ).observe(duration)
    
    @classmethod
    def observe_database_query_duration(
        cls,
        query_type: str,
        duration: float
    ) -> None:
        """Записать длительность запроса к БД."""
        cls.database_query_duration_seconds.labels(
            query_type=query_type
        ).observe(duration)
    
    @classmethod
    def set_active_users(cls, count: int) -> None:
        """Установить количество активных пользователей."""
        cls.active_users.set(count)
    
    @classmethod
    def set_active_subscriptions(
        cls,
        plan_type: str,
        count: int
    ) -> None:
        """Установить количество активных подписок."""
        cls.active_subscriptions.labels(
            plan_type=plan_type
        ).set(count)
    
    @classmethod
    def set_total_users(cls, count: int) -> None:
        """Установить общее количество пользователей."""
        cls.total_users.set(count)
    
    @classmethod
    def set_database_connections(cls, count: int) -> None:
        """Установить количество подключений к БД."""
        cls.database_connections.set(count)
    
    @classmethod
    def set_cache_size(
        cls,
        cache_type: str,
        size: int
    ) -> None:
        """Установить размер кэша."""
        cls.cache_size.labels(
            cache_type=cache_type
        ).set(size)
    
    @classmethod
    def set_balance_total(cls, amount: float) -> None:
        """Установить общий баланс пользователей."""
        cls.balance_total.set(amount)
    
    @classmethod
    def set_revenue_total(
        cls,
        currency: str,
        amount: float
    ) -> None:
        """Установить общую выручку."""
        cls.revenue_total.labels(
            currency=currency
        ).set(amount)
    
    @classmethod
    def get_metrics(cls) -> bytes:
        """Получить метрики в формате Prometheus."""
        return generate_latest(cls.registry)
    
    @staticmethod
    def track_time(metric_name: str, labels: Optional[dict] = None):
        """
        Декоратор для отслеживания времени выполнения функции.
        
        Args:
            metric_name: Имя метрики для записи
            labels: Дополнительные метки для метрики
        """
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    if metric_name == 'http_request':
                        PrometheusMetrics.observe_http_request_duration(
                            labels.get('method', 'unknown'),
                            labels.get('endpoint', 'unknown'),
                            duration
                        )
                    elif metric_name == 'bot_handler':
                        PrometheusMetrics.observe_bot_handler_duration(
                            labels.get('handler', 'unknown'),
                            duration
                        )
                    elif metric_name == 'payment':
                        PrometheusMetrics.observe_payment_processing_duration(
                            labels.get('payment_system', 'unknown'),
                            duration
                        )
                    elif metric_name == 'database':
                        PrometheusMetrics.observe_database_query_duration(
                            labels.get('query_type', 'unknown'),
                            duration
                        )
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    if metric_name == 'http_request':
                        PrometheusMetrics.observe_http_request_duration(
                            labels.get('method', 'unknown'),
                            labels.get('endpoint', 'unknown'),
                            duration
                        )
                    elif metric_name == 'bot_handler':
                        PrometheusMetrics.observe_bot_handler_duration(
                            labels.get('handler', 'unknown'),
                            duration
                        )
                    elif metric_name == 'payment':
                        PrometheusMetrics.observe_payment_processing_duration(
                            labels.get('payment_system', 'unknown'),
                            duration
                        )
                    elif metric_name == 'database':
                        PrometheusMetrics.observe_database_query_duration(
                            labels.get('query_type', 'unknown'),
                            duration
                        )
            
            # Определяем, является ли функция асинхронной
            if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:
                return async_wrapper
            return sync_wrapper
        
        return decorator