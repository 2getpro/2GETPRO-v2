# Security System Documentation

Комплексная система безопасности для проекта 2GETPRO_v2.

## Компоненты

### 1. Rate Limiter
Защита от спама и DDoS атак с использованием Redis.

**Файлы:**
- `rate_limiter/redis_rate_limiter.py` - Redis-based rate limiting
- `rate_limiter/decorators.py` - Декораторы для rate limiting
- `rate_limiter/middleware.py` - Middleware для aiogram

**Использование:**

```python
from security.rate_limiter import rate_limit, RateLimitMiddleware

# Декоратор для функции
@rate_limit(limit=10, window=60)
async def send_message(message: Message, rate_limiter):
    await message.answer("Hello!")

# Middleware
dp.message.middleware(RateLimitMiddleware(rate_limiter))
```

### 2. Webhook Validator
Валидация подписей webhook запросов от платежных систем.

**Файлы:**
- `webhook_validator/signature_validator.py` - Валидация подписей
- `webhook_validator/decorators.py` - Декораторы для webhook
- `webhook_validator/ip_whitelist.py` - IP whitelist

**Поддерживаемые системы:**
- YooKassa
- CryptoPay
- FreeKassa
- Tribute
- Telegram Stars
- Panel webhook

**Использование:**

```python
from security.webhook_validator import validate_webhook

@validate_webhook(provider='yookassa')
async def handle_yookassa_webhook(request):
    data = await request.json()
    # обработка webhook
    return web.Response(status=200)
```

### 3. Secrets Manager
Безопасное управление секретами с шифрованием.

**Файлы:**
- `secrets/secrets_manager.py` - Менеджер секретов
- `secrets/encryption.py` - Шифрование данных

**Использование:**

```python
from security.secrets import SecretsManager

secrets = SecretsManager(
    secrets_file='secrets.json',
    master_key='your-master-key',
    use_encryption=True
)

# Получить секрет
api_key = secrets.get_secret('YOOKASSA_API_KEY')

# Установить секрет
secrets.set_secret('NEW_KEY', 'value', persist=True)

# Зашифровать данные
encrypted = secrets.encrypt('sensitive data')
decrypted = secrets.decrypt(encrypted)
```

### 4. Access Control
Система прав доступа и ролей.

**Файлы:**
- `access_control/permissions.py` - Роли и разрешения
- `access_control/decorators.py` - Декораторы для проверки прав

**Роли:**
- `USER` - Обычный пользователь
- `MODERATOR` - Модератор
- `ADMIN` - Администратор
- `SUPER_ADMIN` - Супер-администратор

**Использование:**

```python
from security.access_control import require_permission, Permission

@require_permission(Permission.MANAGE_USERS)
async def delete_user(message: Message, permission_checker):
    # только для пользователей с правом MANAGE_USERS
    pass
```

### 5. Audit Log
Логирование действий пользователей и событий безопасности.

**Файлы:**
- `audit/audit_logger.py` - Audit logger

**Использование:**

```python
from security.audit import AuditLogger, AuditEvent

audit = AuditLogger(db_session=session, sentry_enabled=True)

# Логировать действие
await audit.log_action(
    user_id=123,
    action=AuditEvent.USER_LOGIN,
    details={'ip': '1.2.3.4'}
)

# Логировать событие безопасности
await audit.log_security_event(
    event_type=SecurityEvent.RATE_LIMIT_EXCEEDED,
    details={'limit': 10, 'count': 15},
    user_id=123,
    severity='warning'
)
```

## Инициализация

### Быстрый старт

```python
from security import setup_security

# Инициализация всей системы безопасности
security = await setup_security(
    redis_url='redis://localhost:6379',
    db_session=session,
    secrets_file='secrets.json',
    master_key='your-master-key'
)

# Получить компоненты
components = security.get_components()
rate_limiter = components['rate_limiter']
audit_logger = components['audit_logger']
```

### Ручная инициализация

```python
from security import SecurityManager
import redis.asyncio as redis

# Подключение к Redis
redis_client = await redis.from_url('redis://localhost:6379')

# Создание менеджера
security = SecurityManager(
    redis_client=redis_client,
    db_session=session,
    secrets_file='secrets.json',
    master_key='your-master-key'
)

# Проверка здоровья
health = await security.health_check()
print(health)
```

## Конфигурация

### Переменные окружения

```bash
# Redis
REDIS_URL=redis://localhost:6379

# Секреты платежных систем
YOOKASSA_SECRET_KEY=your_secret
CRYPTOPAY_API_TOKEN=your_token
FREEKASSA_SECRET_KEY=your_secret
TRIBUTE_SECRET_KEY=your_secret
PANEL_WEBHOOK_SECRET=your_secret

# Шифрование
SECURITY_MASTER_KEY=your_master_key
SECRETS_FILE=secrets.json

# Sentry
SENTRY_ENABLED=true
SENTRY_DSN=your_dsn
```

## Примеры использования

### Rate Limiting в handlers

```python
from aiogram import Router
from security.rate_limiter import rate_limit_user

router = Router()

@router.message(Command("start"))
@rate_limit_user(limit=5, window=60)
async def start_handler(message: Message, rate_limiter):
    await message.answer("Welcome!")
```

### Webhook с валидацией

```python
from aiohttp import web
from security.webhook_validator import validate_webhook

@validate_webhook(provider='yookassa', check_ip=True)
async def yookassa_webhook(request):
    data = await request.json()
    
    # Обработка платежа
    payment_id = data['object']['id']
    
    return web.Response(status=200)
```

### Проверка прав доступа

```python
from security.access_control import require_role, Role

@require_role(Role.ADMIN)
async def admin_panel(message: Message, permission_checker):
    await message.answer("Admin panel")
```

### Audit logging

```python
from security.audit import AuditLogger, AuditEvent

async def process_payment(user_id: int, amount: float):
    # Обработка платежа
    
    # Логирование
    await audit_logger.log_action(
        user_id=user_id,
        action=AuditEvent.PAYMENT_SUCCESS,
        details={
            'amount': amount,
            'currency': 'RUB'
        }
    )
```

## Безопасность

### Рекомендации

1. **Секреты:**
   - Используйте сильные мастер-ключи (минимум 32 символа)
   - Храните секреты в зашифрованном виде
   - Регулярно ротируйте секреты

2. **Rate Limiting:**
   - Настройте лимиты в зависимости от нагрузки
   - Используйте разные лимиты для разных endpoints
   - Мониторьте превышения лимитов

3. **Webhook:**
   - Всегда проверяйте подписи
   - Используйте IP whitelist где возможно
   - Логируйте все невалидные запросы

4. **Access Control:**
   - Следуйте принципу минимальных привилегий
   - Регулярно проверяйте права пользователей
   - Логируйте все изменения прав

5. **Audit Log:**
   - Логируйте все критические действия
   - Регулярно анализируйте логи
   - Настройте алерты для подозрительной активности

## Мониторинг

### Health Check

```python
# Проверка здоровья системы безопасности
health = await security.health_check()

# Результат:
{
    'redis': True,
    'database': True,
    'rate_limiter': True,
    'webhook_validator': True,
    'secrets_manager': True,
    'access_control': True,
    'audit_logger': True
}
```

### Метрики

Система безопасности интегрируется с Prometheus для сбора метрик:

- `rate_limit_exceeded_total` - Количество превышений rate limit
- `webhook_invalid_signature_total` - Количество невалидных подписей
- `access_denied_total` - Количество отказов в доступе
- `security_events_total` - Количество событий безопасности

## Troubleshooting

### Rate Limiter не работает

1. Проверьте подключение к Redis
2. Убедитесь, что middleware добавлен в dispatcher
3. Проверьте, что rate_limiter передается в контексте

### Webhook валидация не проходит

1. Проверьте правильность секретных ключей
2. Убедитесь, что IP адрес в whitelist
3. Проверьте формат подписи для конкретной системы

### Secrets не расшифровываются

1. Проверьте правильность мастер-ключа
2. Убедитесь, что файл секретов не поврежден
3. Проверьте версию библиотеки cryptography

## Зависимости

```txt
redis>=4.5.0
cryptography>=41.0.0
aiogram>=3.0.0
aiohttp>=3.8.0
sqlalchemy>=2.0.0
sentry-sdk>=1.40.0
```

## Лицензия

MIT License