"""
Декораторы для валидации webhook запросов.
"""

import functools
from typing import Callable, Any
from aiohttp import web
import logging

from .signature_validator import SignatureValidator
from .ip_whitelist import IPWhitelist

logger = logging.getLogger(__name__)


def validate_webhook(
    provider: str,
    signature_header: str = None,
    check_ip: bool = True
):
    """
    Декоратор для валидации webhook запросов.
    
    Args:
        provider: Название провайдера (yookassa, cryptopay, и т.д.)
        signature_header: Название заголовка с подписью (опционально)
        check_ip: Проверять ли IP адрес
        
    Example:
        @validate_webhook(provider='yookassa')
        async def handle_yookassa_webhook(request):
            data = await request.json()
            # обработка webhook
            return web.Response(status=200)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(request: web.Request, *args, **kwargs) -> Any:
            # Получаем validator и whitelist из app
            validator: SignatureValidator = request.app.get('signature_validator')
            whitelist: IPWhitelist = request.app.get('ip_whitelist')
            
            if not validator:
                logger.error("SignatureValidator not configured")
                return web.Response(
                    status=500,
                    text='Internal server error'
                )
            
            # Проверка IP адреса
            if check_ip and whitelist:
                client_ip = request.headers.get('X-Forwarded-For', request.remote)
                if client_ip:
                    client_ip = client_ip.split(',')[0].strip()
                
                if not whitelist.is_allowed(provider, client_ip):
                    logger.warning(
                        f"Webhook from unauthorized IP: {client_ip} "
                        f"for provider {provider}"
                    )
                    return web.Response(
                        status=403,
                        text='Forbidden'
                    )
            
            # Получаем подпись из заголовка
            header_name = signature_header or validator.get_signature_header(provider)
            signature = request.headers.get(header_name)
            
            if not signature:
                logger.warning(
                    f"Missing signature header {header_name} "
                    f"for provider {provider}"
                )
                return web.Response(
                    status=401,
                    text='Unauthorized: Missing signature'
                )
            
            # Получаем тело запроса
            try:
                payload = await request.json()
            except Exception as e:
                logger.error(f"Error parsing webhook payload: {e}")
                return web.Response(
                    status=400,
                    text='Bad request: Invalid JSON'
                )
            
            # Валидируем подпись
            is_valid = validator.validate(provider, payload, signature)
            
            if not is_valid:
                logger.error(
                    f"Invalid webhook signature for provider {provider}"
                )
                return web.Response(
                    status=401,
                    text='Unauthorized: Invalid signature'
                )
            
            # Логируем успешную валидацию
            logger.info(
                f"Valid webhook received from {provider}, "
                f"IP: {request.remote}"
            )
            
            # Выполняем обработчик
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def validate_webhook_simple(secret_key: str, header_name: str = 'X-Signature'):
    """
    Простой декоратор для валидации webhook с одним секретным ключом.
    
    Args:
        secret_key: Секретный ключ
        header_name: Название заголовка с подписью
        
    Example:
        @validate_webhook_simple(secret_key='my_secret', header_name='X-Signature')
        async def handle_webhook(request):
            return web.Response(status=200)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(request: web.Request, *args, **kwargs) -> Any:
            signature = request.headers.get(header_name)
            
            if not signature:
                logger.warning(f"Missing signature header {header_name}")
                return web.Response(
                    status=401,
                    text='Unauthorized: Missing signature'
                )
            
            # Простая проверка - сравнение с секретным ключом
            import hmac
            if not hmac.compare_digest(signature, secret_key):
                logger.error("Invalid webhook signature")
                return web.Response(
                    status=401,
                    text='Unauthorized: Invalid signature'
                )
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def log_webhook(provider: str):
    """
    Декоратор для логирования webhook запросов.
    
    Args:
        provider: Название провайдера
        
    Example:
        @log_webhook(provider='yookassa')
        async def handle_webhook(request):
            return web.Response(status=200)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(request: web.Request, *args, **kwargs) -> Any:
            client_ip = request.headers.get('X-Forwarded-For', request.remote)
            
            logger.info(
                f"Webhook received: provider={provider}, "
                f"ip={client_ip}, "
                f"path={request.path}"
            )
            
            try:
                result = await func(request, *args, **kwargs)
                
                logger.info(
                    f"Webhook processed successfully: provider={provider}, "
                    f"status={result.status if hasattr(result, 'status') else 'unknown'}"
                )
                
                return result
                
            except Exception as e:
                logger.error(
                    f"Error processing webhook: provider={provider}, "
                    f"error={str(e)}",
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator