"""
Валидация подписей webhook запросов от различных платежных систем.
"""

import hmac
import hashlib
import json
import time
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SignatureValidator:
    """
    Валидатор подписей для webhook запросов от платежных систем.
    
    Поддерживает:
    - YooKassa
    - CryptoPay
    - FreeKassa
    - Tribute
    - Telegram Stars
    - Panel webhook
    """
    
    def __init__(self, secrets: Dict[str, str]):
        """
        Инициализация валидатора.
        
        Args:
            secrets: Словарь с секретными ключами для каждой системы
                {
                    'yookassa': 'secret_key',
                    'cryptopay': 'api_token',
                    'freekassa': 'secret_key',
                    'tribute': 'secret_key',
                    'stars': 'bot_token',
                    'panel': 'webhook_secret'
                }
        """
        self.secrets = secrets
        self.replay_window = 300  # 5 минут для защиты от replay attacks
    
    def validate_yookassa(
        self,
        payload: Dict[str, Any],
        signature: str
    ) -> bool:
        """
        Валидация подписи YooKassa webhook.
        
        Args:
            payload: Тело запроса
            signature: Подпись из заголовка
            
        Returns:
            True если подпись валидна
        """
        try:
            secret = self.secrets.get('yookassa')
            if not secret:
                logger.error("YooKassa secret not configured")
                return False
            
            # YooKassa использует HMAC-SHA256
            # Формат: event_type + '&' + object_id + '&' + secret
            event_type = payload.get('event')
            object_data = payload.get('object', {})
            object_id = object_data.get('id')
            
            if not event_type or not object_id:
                logger.error("Invalid YooKassa payload structure")
                return False
            
            message = f"{event_type}&{object_id}&{secret}"
            expected_signature = hmac.new(
                secret.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            is_valid = hmac.compare_digest(signature, expected_signature)
            
            if not is_valid:
                logger.warning(f"Invalid YooKassa signature for event {event_type}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error validating YooKassa signature: {e}", exc_info=True)
            return False
    
    def validate_cryptopay(
        self,
        payload: Dict[str, Any],
        signature: str
    ) -> bool:
        """
        Валидация подписи CryptoPay webhook.
        
        Args:
            payload: Тело запроса
            signature: Подпись из заголовка Crypto-Pay-Api-Signature
            
        Returns:
            True если подпись валидна
        """
        try:
            secret = self.secrets.get('cryptopay')
            if not secret:
                logger.error("CryptoPay secret not configured")
                return False
            
            # CryptoPay использует HMAC-SHA256 от JSON body
            body_string = json.dumps(payload, separators=(',', ':'), sort_keys=True)
            
            expected_signature = hmac.new(
                secret.encode(),
                body_string.encode(),
                hashlib.sha256
            ).hexdigest()
            
            is_valid = hmac.compare_digest(signature, expected_signature)
            
            if not is_valid:
                logger.warning("Invalid CryptoPay signature")
            
            # Проверка timestamp для защиты от replay
            if is_valid and 'timestamp' in payload:
                if not self._check_timestamp(payload['timestamp']):
                    logger.warning("CryptoPay webhook timestamp too old")
                    return False
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error validating CryptoPay signature: {e}", exc_info=True)
            return False
    
    def validate_freekassa(
        self,
        payload: Dict[str, Any],
        signature: str
    ) -> bool:
        """
        Валидация подписи FreeKassa webhook.
        
        Args:
            payload: Тело запроса
            signature: Подпись из параметра SIGN
            
        Returns:
            True если подпись валидна
        """
        try:
            secret = self.secrets.get('freekassa')
            if not secret:
                logger.error("FreeKassa secret not configured")
                return False
            
            # FreeKassa: MD5(MERCHANT_ID:AMOUNT:SECRET:MERCHANT_ORDER_ID)
            merchant_id = payload.get('MERCHANT_ID')
            amount = payload.get('AMOUNT')
            order_id = payload.get('MERCHANT_ORDER_ID')
            
            if not all([merchant_id, amount, order_id]):
                logger.error("Invalid FreeKassa payload structure")
                return False
            
            message = f"{merchant_id}:{amount}:{secret}:{order_id}"
            expected_signature = hashlib.md5(message.encode()).hexdigest()
            
            is_valid = hmac.compare_digest(signature.lower(), expected_signature.lower())
            
            if not is_valid:
                logger.warning(f"Invalid FreeKassa signature for order {order_id}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error validating FreeKassa signature: {e}", exc_info=True)
            return False
    
    def validate_tribute(
        self,
        payload: Dict[str, Any],
        signature: str
    ) -> bool:
        """
        Валидация подписи Tribute webhook.
        
        Args:
            payload: Тело запроса
            signature: Подпись из заголовка
            
        Returns:
            True если подпись валидна
        """
        try:
            secret = self.secrets.get('tribute')
            if not secret:
                logger.error("Tribute secret not configured")
                return False
            
            # Tribute использует HMAC-SHA256
            body_string = json.dumps(payload, separators=(',', ':'), sort_keys=True)
            
            expected_signature = hmac.new(
                secret.encode(),
                body_string.encode(),
                hashlib.sha256
            ).hexdigest()
            
            is_valid = hmac.compare_digest(signature, expected_signature)
            
            if not is_valid:
                logger.warning("Invalid Tribute signature")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error validating Tribute signature: {e}", exc_info=True)
            return False
    
    def validate_stars(
        self,
        payload: Dict[str, Any],
        signature: str
    ) -> bool:
        """
        Валидация подписи Telegram Stars webhook.
        
        Args:
            payload: Тело запроса
            signature: Подпись из заголовка X-Telegram-Bot-Api-Secret-Token
            
        Returns:
            True если подпись валидна
        """
        try:
            secret = self.secrets.get('stars')
            if not secret:
                logger.error("Telegram Stars secret not configured")
                return False
            
            # Telegram использует простое сравнение токена
            is_valid = hmac.compare_digest(signature, secret)
            
            if not is_valid:
                logger.warning("Invalid Telegram Stars signature")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error validating Telegram Stars signature: {e}", exc_info=True)
            return False
    
    def validate_panel(
        self,
        payload: Dict[str, Any],
        signature: str
    ) -> bool:
        """
        Валидация подписи Panel webhook.
        
        Args:
            payload: Тело запроса
            signature: Подпись из заголовка X-Panel-Signature
            
        Returns:
            True если подпись валидна
        """
        try:
            secret = self.secrets.get('panel')
            if not secret:
                logger.error("Panel secret not configured")
                return False
            
            # Panel использует HMAC-SHA256
            body_string = json.dumps(payload, separators=(',', ':'), sort_keys=True)
            
            expected_signature = hmac.new(
                secret.encode(),
                body_string.encode(),
                hashlib.sha256
            ).hexdigest()
            
            is_valid = hmac.compare_digest(signature, expected_signature)
            
            if not is_valid:
                logger.warning("Invalid Panel signature")
            
            # Проверка timestamp
            if is_valid and 'timestamp' in payload:
                if not self._check_timestamp(payload['timestamp']):
                    logger.warning("Panel webhook timestamp too old")
                    return False
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error validating Panel signature: {e}", exc_info=True)
            return False
    
    def validate(
        self,
        provider: str,
        payload: Dict[str, Any],
        signature: str
    ) -> bool:
        """
        Универсальный метод валидации для любого провайдера.
        
        Args:
            provider: Название провайдера (yookassa, cryptopay, и т.д.)
            payload: Тело запроса
            signature: Подпись
            
        Returns:
            True если подпись валидна
        """
        validators = {
            'yookassa': self.validate_yookassa,
            'cryptopay': self.validate_cryptopay,
            'freekassa': self.validate_freekassa,
            'tribute': self.validate_tribute,
            'stars': self.validate_stars,
            'panel': self.validate_panel,
        }
        
        validator = validators.get(provider.lower())
        if not validator:
            logger.error(f"Unknown provider: {provider}")
            return False
        
        return validator(payload, signature)
    
    def _check_timestamp(self, timestamp: int) -> bool:
        """
        Проверка timestamp для защиты от replay attacks.
        
        Args:
            timestamp: Unix timestamp
            
        Returns:
            True если timestamp в допустимом окне
        """
        current_time = int(time.time())
        time_diff = abs(current_time - timestamp)
        
        if time_diff > self.replay_window:
            logger.warning(
                f"Timestamp too old: {time_diff}s > {self.replay_window}s"
            )
            return False
        
        return True
    
    def get_signature_header(self, provider: str) -> str:
        """
        Получить название заголовка с подписью для провайдера.
        
        Args:
            provider: Название провайдера
            
        Returns:
            Название заголовка
        """
        headers = {
            'yookassa': 'X-YooKassa-Signature',
            'cryptopay': 'Crypto-Pay-Api-Signature',
            'freekassa': 'SIGN',
            'tribute': 'X-Tribute-Signature',
            'stars': 'X-Telegram-Bot-Api-Secret-Token',
            'panel': 'X-Panel-Signature',
        }
        
        return headers.get(provider.lower(), 'X-Signature')