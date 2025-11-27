"""
Главный менеджер безопасности для инициализации всех компонентов.
"""

import os
from typing import Optional, Dict, Any
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from .rate_limiter import RedisRateLimiter, RateLimitMiddleware
from .webhook_validator import SignatureValidator, IPWhitelist
from .secrets import SecretsManager, Encryptor
from .access_control import PermissionChecker
from .audit import AuditLogger

logger = logging.getLogger(__name__)


class SecurityManager:
    """
    Центральный менеджер для управления всеми компонентами безопасности.
    """
    
    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        db_session: Optional[AsyncSession] = None,
        secrets_file: Optional[str] = None,
        master_key: Optional[str] = None
    ):
        """
        Инициализация менеджера безопасности.
        
        Args:
            redis_client: Redis клиент для rate limiting
            db_session: Сессия БД для audit log и permissions
            secrets_file: Путь к файлу с секретами
            master_key: Мастер-ключ для шифрования
        """
        self.redis_client = redis_client
        self.db_session = db_session
        
        # Инициализация компонентов
        self.rate_limiter: Optional[RedisRateLimiter] = None
        self.rate_limit_middleware: Optional[RateLimitMiddleware] = None
        self.signature_validator: Optional[SignatureValidator] = None
        self.ip_whitelist: Optional[IPWhitelist] = None
        self.secrets_manager: Optional[SecretsManager] = None
        self.encryptor: Optional[Encryptor] = None
        self.permission_checker: Optional[PermissionChecker] = None
        self.audit_logger: Optional[AuditLogger] = None
        
        # Инициализируем компоненты
        self._init_rate_limiter()
        self._init_webhook_validator()
        self._init_secrets_manager(secrets_file, master_key)
        self._init_access_control()
        self._init_audit_logger()
    
    def _init_rate_limiter(self) -> None:
        """Инициализация rate limiter."""
        if self.redis_client:
            try:
                self.rate_limiter = RedisRateLimiter(
                    redis_client=self.redis_client,
                    prefix="2getpro:rate_limit"
                )
                
                self.rate_limit_middleware = RateLimitMiddleware(
                    rate_limiter=self.rate_limiter,
                    default_limit=20,
                    default_window=60,
                    spam_limit=100,
                    spam_window=3600,
                    block_duration=3600
                )
                
                logger.info("Rate limiter initialized")
            except Exception as e:
                logger.error(f"Error initializing rate limiter: {e}", exc_info=True)
        else:
            logger.warning("Redis client not provided, rate limiting disabled")
    
    def _init_webhook_validator(self) -> None:
        """Инициализация webhook validator."""
        try:
            # Получаем секреты для валидации
            secrets = {
                'yookassa': os.getenv('YOOKASSA_SECRET_KEY', ''),
                'cryptopay': os.getenv('CRYPTOPAY_API_TOKEN', ''),
                'freekassa': os.getenv('FREEKASSA_SECRET_KEY', ''),
                'tribute': os.getenv('TRIBUTE_SECRET_KEY', ''),
                'stars': os.getenv('BOT_TOKEN', ''),
                'panel': os.getenv('PANEL_WEBHOOK_SECRET', ''),
            }
            
            self.signature_validator = SignatureValidator(secrets)
            self.ip_whitelist = IPWhitelist()
            
            logger.info("Webhook validator initialized")
        except Exception as e:
            logger.error(f"Error initializing webhook validator: {e}", exc_info=True)
    
    def _init_secrets_manager(
        self,
        secrets_file: Optional[str],
        master_key: Optional[str]
    ) -> None:
        """Инициализация secrets manager."""
        try:
            # Используем мастер-ключ из переменной окружения если не указан
            if not master_key:
                master_key = os.getenv('SECURITY_MASTER_KEY')
            
            # Используем файл секретов из переменной окружения если не указан
            if not secrets_file:
                secrets_file = os.getenv('SECRETS_FILE', 'secrets.json')
            
            self.secrets_manager = SecretsManager(
                secrets_file=secrets_file,
                master_key=master_key,
                use_encryption=True,
                cache_secrets=True
            )
            
            self.encryptor = Encryptor(master_key)
            
            logger.info("Secrets manager initialized")
        except Exception as e:
            logger.error(f"Error initializing secrets manager: {e}", exc_info=True)
    
    def _init_access_control(self) -> None:
        """Инициализация access control."""
        try:
            self.permission_checker = PermissionChecker(
                db_session=self.db_session
            )
            
            logger.info("Access control initialized")
        except Exception as e:
            logger.error(f"Error initializing access control: {e}", exc_info=True)
    
    def _init_audit_logger(self) -> None:
        """Инициализация audit logger."""
        try:
            sentry_enabled = os.getenv('SENTRY_ENABLED', 'false').lower() == 'true'
            
            self.audit_logger = AuditLogger(
                db_session=self.db_session,
                sentry_enabled=sentry_enabled
            )
            
            logger.info("Audit logger initialized")
        except Exception as e:
            logger.error(f"Error initializing audit logger: {e}", exc_info=True)
    
    def get_components(self) -> Dict[str, Any]:
        """
        Получить все компоненты безопасности.
        
        Returns:
            Словарь с компонентами
        """
        return {
            'rate_limiter': self.rate_limiter,
            'rate_limit_middleware': self.rate_limit_middleware,
            'signature_validator': self.signature_validator,
            'ip_whitelist': self.ip_whitelist,
            'secrets_manager': self.secrets_manager,
            'encryptor': self.encryptor,
            'permission_checker': self.permission_checker,
            'audit_logger': self.audit_logger,
        }
    
    async def health_check(self) -> Dict[str, bool]:
        """
        Проверка здоровья всех компонентов.
        
        Returns:
            Словарь со статусом каждого компонента
        """
        health = {}
        
        # Проверка Redis
        if self.redis_client:
            try:
                await self.redis_client.ping()
                health['redis'] = True
            except Exception:
                health['redis'] = False
        else:
            health['redis'] = None
        
        # Проверка БД
        if self.db_session:
            try:
                await self.db_session.execute("SELECT 1")
                health['database'] = True
            except Exception:
                health['database'] = False
        else:
            health['database'] = None
        
        # Проверка компонентов
        health['rate_limiter'] = self.rate_limiter is not None
        health['webhook_validator'] = self.signature_validator is not None
        health['secrets_manager'] = self.secrets_manager is not None
        health['access_control'] = self.permission_checker is not None
        health['audit_logger'] = self.audit_logger is not None
        
        return health


async def setup_security(
    redis_url: Optional[str] = None,
    db_session: Optional[AsyncSession] = None,
    secrets_file: Optional[str] = None,
    master_key: Optional[str] = None
) -> SecurityManager:
    """
    Настройка системы безопасности.
    
    Args:
        redis_url: URL для подключения к Redis
        db_session: Сессия БД
        secrets_file: Путь к файлу с секретами
        master_key: Мастер-ключ для шифрования
        
    Returns:
        Экземпляр SecurityManager
        
    Example:
        security = await setup_security(
            redis_url='redis://localhost:6379',
            db_session=session,
            secrets_file='secrets.json',
            master_key='your-master-key'
        )
    """
    # Подключаемся к Redis если указан URL
    redis_client = None
    if redis_url:
        try:
            redis_client = await redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info(f"Connected to Redis: {redis_url}")
        except Exception as e:
            logger.error(f"Error connecting to Redis: {e}", exc_info=True)
    
    # Создаем менеджер безопасности
    security_manager = SecurityManager(
        redis_client=redis_client,
        db_session=db_session,
        secrets_file=secrets_file,
        master_key=master_key
    )
    
    # Проверяем здоровье
    health = await security_manager.health_check()
    logger.info(f"Security system initialized. Health: {health}")
    
    return security_manager