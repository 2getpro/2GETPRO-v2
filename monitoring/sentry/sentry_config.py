"""
Конфигурация Sentry для отслеживания ошибок.

Настраивает:
- Инициализацию Sentry SDK
- Traces sample rate
- Environment
- Фильтры для чувствительных данных
- Breadcrumbs
"""

from typing import Optional, Dict, Any, List
import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
import logging


# Список полей, которые нужно скрыть
SENSITIVE_FIELDS = [
    'password',
    'token',
    'api_key',
    'secret',
    'authorization',
    'cookie',
    'session',
    'credit_card',
    'card_number',
    'cvv',
    'ssn',
    'private_key'
]


def before_send(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Обработчик событий перед отправкой в Sentry.
    Фильтрует чувствительные данные.
    
    Args:
        event: Событие Sentry
        hint: Дополнительная информация
    
    Returns:
        Обработанное событие или None для игнорирования
    """
    # Фильтруем чувствительные данные из request
    if 'request' in event:
        request = event['request']
        
        # Фильтруем headers
        if 'headers' in request:
            for field in SENSITIVE_FIELDS:
                if field in request['headers']:
                    request['headers'][field] = '[Filtered]'
        
        # Фильтруем cookies
        if 'cookies' in request:
            for field in SENSITIVE_FIELDS:
                if field in request['cookies']:
                    request['cookies'][field] = '[Filtered]'
        
        # Фильтруем query string
        if 'query_string' in request:
            for field in SENSITIVE_FIELDS:
                if field in request['query_string']:
                    request['query_string'] = request['query_string'].replace(
                        field, '[Filtered]'
                    )
        
        # Фильтруем данные формы
        if 'data' in request and isinstance(request['data'], dict):
            for field in SENSITIVE_FIELDS:
                if field in request['data']:
                    request['data'][field] = '[Filtered]'
    
    # Фильтруем чувствительные данные из extra
    if 'extra' in event:
        for field in SENSITIVE_FIELDS:
            if field in event['extra']:
                event['extra'][field] = '[Filtered]'
    
    # Фильтруем чувствительные данные из contexts
    if 'contexts' in event:
        for context_name, context_data in event['contexts'].items():
            if isinstance(context_data, dict):
                for field in SENSITIVE_FIELDS:
                    if field in context_data:
                        context_data[field] = '[Filtered]'
    
    return event


def before_breadcrumb(crumb: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Обработчик breadcrumbs перед добавлением.
    Фильтрует чувствительные данные.
    
    Args:
        crumb: Breadcrumb
        hint: Дополнительная информация
    
    Returns:
        Обработанный breadcrumb или None для игнорирования
    """
    # Фильтруем чувствительные данные из data
    if 'data' in crumb and isinstance(crumb['data'], dict):
        for field in SENSITIVE_FIELDS:
            if field in crumb['data']:
                crumb['data'][field] = '[Filtered]'
    
    # Фильтруем чувствительные данные из message
    if 'message' in crumb:
        for field in SENSITIVE_FIELDS:
            if field in crumb['message'].lower():
                crumb['message'] = '[Filtered sensitive data]'
    
    return crumb


def init_sentry(
    dsn: str,
    environment: str = 'production',
    traces_sample_rate: float = 0.1,
    profiles_sample_rate: float = 0.1,
    release: Optional[str] = None,
    server_name: Optional[str] = None,
    ignored_errors: Optional[List[type]] = None,
    max_breadcrumbs: int = 50,
    debug: bool = False
) -> None:
    """
    Инициализация Sentry SDK.
    
    Args:
        dsn: Sentry DSN
        environment: Окружение (production, staging, development)
        traces_sample_rate: Процент трассировок для отправки (0.0 - 1.0)
        profiles_sample_rate: Процент профилей для отправки (0.0 - 1.0)
        release: Версия релиза
        server_name: Имя сервера
        ignored_errors: Список типов ошибок для игнорирования
        max_breadcrumbs: Максимальное количество breadcrumbs
        debug: Режим отладки
    """
    if not dsn:
        logging.warning('Sentry DSN not provided, skipping initialization')
        return
    
    # Список игнорируемых ошибок по умолчанию
    default_ignored_errors = [
        KeyboardInterrupt,
        SystemExit,
    ]
    
    if ignored_errors:
        default_ignored_errors.extend(ignored_errors)
    
    # Настройка интеграции логирования
    logging_integration = LoggingIntegration(
        level=logging.INFO,  # Захватывать логи уровня INFO и выше
        event_level=logging.ERROR  # Отправлять события для ERROR и выше
    )
    
    # Инициализация Sentry
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        server_name=server_name,
        traces_sample_rate=traces_sample_rate,
        profiles_sample_rate=profiles_sample_rate,
        max_breadcrumbs=max_breadcrumbs,
        debug=debug,
        before_send=before_send,
        before_breadcrumb=before_breadcrumb,
        integrations=[
            AsyncioIntegration(),
            AioHttpIntegration(),
            SqlalchemyIntegration(),
            RedisIntegration(),
            logging_integration,
        ],
        ignore_errors=default_ignored_errors,
        # Дополнительные настройки
        attach_stacktrace=True,
        send_default_pii=False,  # Не отправлять PII по умолчанию
        in_app_include=['bot', 'monitoring', 'db', 'config'],
        in_app_exclude=['site-packages', 'dist-packages'],
    )
    
    logging.info(
        f'Sentry initialized for environment: {environment}, '
        f'traces_sample_rate: {traces_sample_rate}'
    )


def configure_scope(
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    email: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None
) -> None:
    """
    Настройка scope для текущего контекста.
    
    Args:
        user_id: ID пользователя
        username: Имя пользователя
        email: Email пользователя
        extra: Дополнительные данные
        tags: Теги для группировки
    """
    with sentry_sdk.configure_scope() as scope:
        # Устанавливаем пользователя
        if user_id or username or email:
            scope.set_user({
                'id': user_id,
                'username': username,
                'email': email
            })
        
        # Добавляем extra данные
        if extra:
            for key, value in extra.items():
                scope.set_extra(key, value)
        
        # Добавляем теги
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)


def add_breadcrumb(
    message: str,
    category: str = 'default',
    level: str = 'info',
    data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Добавить breadcrumb для контекста.
    
    Args:
        message: Сообщение
        category: Категория (http, db, navigation, etc.)
        level: Уровень (debug, info, warning, error, fatal)
        data: Дополнительные данные
    """
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data or {}
    )


def set_context(
    name: str,
    context: Dict[str, Any]
) -> None:
    """
    Установить контекст для событий.
    
    Args:
        name: Имя контекста
        context: Данные контекста
    """
    sentry_sdk.set_context(name, context)


def set_tag(key: str, value: str) -> None:
    """
    Установить тег для событий.
    
    Args:
        key: Ключ тега
        value: Значение тега
    """
    sentry_sdk.set_tag(key, value)


def set_extra(key: str, value: Any) -> None:
    """
    Установить дополнительные данные для событий.
    
    Args:
        key: Ключ
        value: Значение
    """
    sentry_sdk.set_extra(key, value)