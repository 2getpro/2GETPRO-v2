"""
Главный модуль мониторинга для инициализации всех компонентов.

Включает:
- Инициализацию Prometheus метрик
- Запуск Prometheus exporter
- Инициализацию Sentry
- Настройку логирования
- Регистрацию health checks
"""

from typing import Optional, Dict, Any
import asyncio
import logging
from aiohttp import web
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from .metrics import PrometheusMetrics, CustomMetrics
from .health import HealthChecker, ReadinessChecker
from .sentry import init_sentry
from .logging import setup_logging, get_logger


logger = get_logger(__name__)


class MonitoringServer:
    """Сервер для экспорта метрик и health checks."""
    
    def __init__(
        self,
        host: str = '0.0.0.0',
        port: int = 9090,
        health_checker: Optional[HealthChecker] = None,
        readiness_checker: Optional[ReadinessChecker] = None
    ):
        """
        Инициализация сервера мониторинга.
        
        Args:
            host: Хост для прослушивания
            port: Порт для прослушивания
            health_checker: Health checker
            readiness_checker: Readiness checker
        """
        self.host = host
        self.port = port
        self.health_checker = health_checker
        self.readiness_checker = readiness_checker
        self.app = web.Application()
        self._setup_routes()
        self.runner: Optional[web.AppRunner] = None
    
    def _setup_routes(self) -> None:
        """Настроить маршруты."""
        self.app.router.add_get('/metrics', self.metrics_handler)
        self.app.router.add_get('/health', self.health_handler)
        self.app.router.add_get('/ready', self.readiness_handler)
        self.app.router.add_get('/live', self.liveness_handler)
    
    async def metrics_handler(self, request: web.Request) -> web.Response:
        """
        Обработчик для экспорта метрик Prometheus.
        
        Args:
            request: HTTP запрос
        
        Returns:
            HTTP ответ с метриками
        """
        try:
            metrics = PrometheusMetrics.get_metrics()
            return web.Response(
                body=metrics,
                content_type=CONTENT_TYPE_LATEST
            )
        except Exception as e:
            logger.error(f'Error generating metrics: {e}', exc_info=True)
            return web.Response(
                text='Error generating metrics',
                status=500
            )
    
    async def health_handler(self, request: web.Request) -> web.Response:
        """
        Обработчик для health check.
        
        Args:
            request: HTTP запрос
        
        Returns:
            HTTP ответ с результатом проверки
        """
        try:
            if not self.health_checker:
                return web.json_response(
                    {'status': 'unknown', 'message': 'Health checker not configured'},
                    status=503
                )
            
            result = await self.health_checker.check_all()
            
            status_code = 200 if result['status'] == 'healthy' else 503
            
            return web.json_response(result, status=status_code)
        except Exception as e:
            logger.error(f'Error in health check: {e}', exc_info=True)
            return web.json_response(
                {
                    'status': 'unhealthy',
                    'message': f'Health check failed: {str(e)}'
                },
                status=503
            )
    
    async def readiness_handler(self, request: web.Request) -> web.Response:
        """
        Обработчик для readiness check.
        
        Args:
            request: HTTP запрос
        
        Returns:
            HTTP ответ с результатом проверки
        """
        try:
            if not self.readiness_checker:
                return web.json_response(
                    {'status': 'unknown', 'message': 'Readiness checker not configured'},
                    status=503
                )
            
            result = await self.readiness_checker.check_all()
            
            status_code = 200 if result['status'] == 'ready' else 503
            
            return web.json_response(result, status=status_code)
        except Exception as e:
            logger.error(f'Error in readiness check: {e}', exc_info=True)
            return web.json_response(
                {
                    'status': 'not_ready',
                    'message': f'Readiness check failed: {str(e)}'
                },
                status=503
            )
    
    async def liveness_handler(self, request: web.Request) -> web.Response:
        """
        Обработчик для liveness check (простая проверка что сервер работает).
        
        Args:
            request: HTTP запрос
        
        Returns:
            HTTP ответ
        """
        return web.json_response({'status': 'alive'})
    
    async def start(self) -> None:
        """Запустить сервер мониторинга."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, self.host, self.port)
        await site.start()
        logger.info(f'Monitoring server started on {self.host}:{self.port}')
    
    async def stop(self) -> None:
        """Остановить сервер мониторинга."""
        if self.runner:
            await self.runner.cleanup()
            logger.info('Monitoring server stopped')


async def setup_monitoring(
    # Logging settings
    log_level: str = 'INFO',
    log_dir: str = 'logs',
    use_json_logs: bool = True,
    use_syslog: bool = False,
    syslog_address: Optional[tuple] = None,
    
    # Sentry settings
    sentry_dsn: Optional[str] = None,
    sentry_environment: str = 'production',
    sentry_traces_sample_rate: float = 0.1,
    sentry_release: Optional[str] = None,
    
    # Monitoring server settings
    monitoring_host: str = '0.0.0.0',
    monitoring_port: int = 9090,
    enable_monitoring_server: bool = True,
    
    # Health check settings
    db_session: Optional[Any] = None,
    redis_url: Optional[str] = None,
    telegram_token: Optional[str] = None,
    panel_url: Optional[str] = None,
    payment_systems: Optional[Dict[str, str]] = None,
    
    # Additional settings
    server_name: Optional[str] = None
) -> Optional[MonitoringServer]:
    """
    Инициализация всех компонентов мониторинга.
    
    Args:
        log_level: Уровень логирования
        log_dir: Директория для логов
        use_json_logs: Использовать JSON формат для логов
        use_syslog: Использовать syslog
        syslog_address: Адрес syslog сервера
        sentry_dsn: Sentry DSN
        sentry_environment: Окружение Sentry
        sentry_traces_sample_rate: Процент трассировок для Sentry
        sentry_release: Версия релиза
        monitoring_host: Хост для сервера мониторинга
        monitoring_port: Порт для сервера мониторинга
        enable_monitoring_server: Запустить сервер мониторинга
        db_session: Сессия БД для health checks
        redis_url: URL Redis для health checks
        telegram_token: Токен Telegram для health checks
        panel_url: URL панели для health checks
        payment_systems: Словарь платежных систем для health checks
        server_name: Имя сервера
    
    Returns:
        MonitoringServer если enable_monitoring_server=True, иначе None
    """
    logger.info('Initializing monitoring system...')
    
    # 1. Настройка логирования
    logger.info('Setting up logging...')
    setup_logging(
        log_level=log_level,
        log_dir=log_dir,
        use_json=use_json_logs,
        use_syslog=use_syslog,
        syslog_address=syslog_address
    )
    logger.info('Logging configured successfully')
    
    # 2. Инициализация Sentry
    if sentry_dsn:
        logger.info('Initializing Sentry...')
        init_sentry(
            dsn=sentry_dsn,
            environment=sentry_environment,
            traces_sample_rate=sentry_traces_sample_rate,
            release=sentry_release,
            server_name=server_name
        )
        logger.info('Sentry initialized successfully')
    else:
        logger.warning('Sentry DSN not provided, skipping Sentry initialization')
    
    # 3. Инициализация health checkers
    health_checker = None
    readiness_checker = None
    
    if db_session or redis_url or telegram_token or panel_url:
        logger.info('Initializing health checkers...')
        
        health_checker = HealthChecker(
            db_session=db_session,
            redis_url=redis_url,
            telegram_token=telegram_token,
            panel_url=panel_url,
            payment_systems=payment_systems
        )
        
        readiness_checker = ReadinessChecker(
            db_session=db_session,
            redis_url=redis_url
        )
        
        logger.info('Health checkers initialized successfully')
    else:
        logger.warning('Health check parameters not provided, health checks will be limited')
    
    # 4. Запуск сервера мониторинга
    monitoring_server = None
    if enable_monitoring_server:
        logger.info('Starting monitoring server...')
        
        monitoring_server = MonitoringServer(
            host=monitoring_host,
            port=monitoring_port,
            health_checker=health_checker,
            readiness_checker=readiness_checker
        )
        
        await monitoring_server.start()
        logger.info(f'Monitoring server started on {monitoring_host}:{monitoring_port}')
        logger.info(f'Metrics available at: http://{monitoring_host}:{monitoring_port}/metrics')
        logger.info(f'Health check available at: http://{monitoring_host}:{monitoring_port}/health')
        logger.info(f'Readiness check available at: http://{monitoring_host}:{monitoring_port}/ready')
        logger.info(f'Liveness check available at: http://{monitoring_host}:{monitoring_port}/live')
    
    logger.info('Monitoring system initialized successfully')
    
    return monitoring_server


async def shutdown_monitoring(monitoring_server: Optional[MonitoringServer] = None) -> None:
    """
    Остановка системы мониторинга.
    
    Args:
        monitoring_server: Сервер мониторинга для остановки
    """
    logger.info('Shutting down monitoring system...')
    
    if monitoring_server:
        await monitoring_server.stop()
    
    logger.info('Monitoring system shut down successfully')