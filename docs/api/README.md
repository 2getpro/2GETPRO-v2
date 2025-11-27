# API Документация 2GETPRO v2

## Обзор

2GETPRO v2 предоставляет REST API для интеграции с внешними сервисами и webhook endpoints для обработки платежей и событий панели управления.

## Содержание

- [Webhook Endpoints](#webhook-endpoints)
- [Аутентификация](#аутентификация)
- [Форматы данных](#форматы-данных)
- [Коды ошибок](#коды-ошибок)
- [Сервисы](#сервисы)

## Webhook Endpoints

### Обзор Webhook'ов

Все webhook endpoints доступны по базовому URL, указанному в `WEBHOOK_BASE_URL`:

```
https://your-domain.com/webhook/{provider}
```

### Доступные Webhook'и

| Провайдер | Endpoint | Описание |
|-----------|----------|----------|
| YooKassa | `/webhook/yookassa` | Обработка платежей YooKassa |
| CryptoPay | `/webhook/cryptopay` | Обработка криптовалютных платежей |
| FreeKassa | `/webhook/freekassa` | Обработка платежей FreeKassa |
| Tribute | `/webhook/tribute` | Обработка подписок Tribute |
| Stars | `/webhook/stars` | Обработка Telegram Stars |
| Panel | `/webhook/panel` | События от панели управления Remnawave |

Подробная документация по каждому webhook доступна в [`webhooks.md`](./webhooks.md).

## Аутентификация

### Webhook Валидация

Все webhook запросы валидируются с использованием подписей:

#### YooKassa
- Использует встроенную валидацию SDK
- Проверка IP адресов YooKassa

#### CryptoPay
- Валидация через aiocryptopay SDK
- Автоматическая проверка подписи

#### FreeKassa
- HMAC-SHA256 подпись
- Формат: `MERCHANT_ID:AMOUNT:SECRET:ORDER_ID`

#### Tribute
- HMAC-SHA256 подпись в заголовке `trbt-signature`
- Ключ: `TRIBUTE_API_KEY`

#### Panel (Remnawave)
- HMAC-SHA256 подпись в заголовке `X-Remnawave-Signature`
- Ключ: `PANEL_WEBHOOK_SECRET`

### Rate Limiting

API защищен rate limiting'ом:

```python
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=30  # Максимум запросов
RATE_LIMIT_WINDOW=60    # Временное окно в секундах
```

## Форматы данных

### Стандартный формат ответа

```json
{
  "status": "success|error",
  "data": {},
  "message": "Описание результата",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Формат ошибки

```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Описание ошибки",
    "details": {}
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Коды ошибок

| Код | Описание | HTTP Status |
|-----|----------|-------------|
| `INVALID_SIGNATURE` | Неверная подпись webhook | 403 |
| `PAYMENT_NOT_FOUND` | Платеж не найден | 404 |
| `USER_NOT_FOUND` | Пользователь не найден | 404 |
| `INVALID_AMOUNT` | Неверная сумма платежа | 400 |
| `DUPLICATE_PAYMENT` | Дублирующийся платеж | 409 |
| `SERVICE_UNAVAILABLE` | Сервис недоступен | 503 |
| `RATE_LIMIT_EXCEEDED` | Превышен лимит запросов | 429 |
| `INTERNAL_ERROR` | Внутренняя ошибка сервера | 500 |

## Сервисы

Подробная документация по сервисам доступна в [`services.md`](./services.md):

- **BalanceService** - Управление балансом пользователей
- **SubscriptionService** - Управление подписками
- **PaymentService** - Обработка платежей
- **ReferralService** - Реферальная система
- **PromoCodeService** - Промокоды
- **NotificationService** - Уведомления

## Мониторинг

### Prometheus Метрики

Метрики доступны по адресу:

```
http://localhost:9090/metrics
```

Основные метрики:

- `bot_requests_total` - Общее количество запросов
- `bot_request_duration_seconds` - Длительность запросов
- `bot_errors_total` - Количество ошибок
- `payment_transactions_total` - Количество транзакций
- `active_subscriptions` - Активные подписки

### Health Check

```bash
GET /health
```

Ответ:
```json
{
  "status": "healthy",
  "services": {
    "database": "ok",
    "redis": "ok",
    "bot": "ok"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Примеры использования

### Создание платежа (YooKassa)

```python
from bot.services.yookassa_service import YooKassaService

service = YooKassaService(
    shop_id="your_shop_id",
    secret_key="your_secret_key",
    configured_return_url="https://t.me/your_bot"
)

payment = await service.create_payment(
    amount=100.0,
    currency="RUB",
    description="Подписка на 1 месяц",
    metadata={
        "user_id": "123456",
        "subscription_months": "1"
    },
    receipt_email="user@example.com"
)
```

### Обработка webhook

```python
from aiohttp import web

async def webhook_handler(request: web.Request):
    # Получение данных
    data = await request.json()
    
    # Валидация подписи
    signature = request.headers.get('X-Signature')
    if not validate_signature(data, signature):
        return web.Response(status=403)
    
    # Обработка события
    await process_payment(data)
    
    return web.Response(status=200, text="OK")
```

## Дополнительные ресурсы

- [Документация Webhook'ов](./webhooks.md)
- [Документация Сервисов](./services.md)
- [Примеры интеграции](../development/examples/)

## Поддержка

При возникновении проблем:

1. Проверьте логи: `docker-compose logs -f bot`
2. Проверьте метрики Prometheus
3. Обратитесь к [troubleshooting guide](../operations/troubleshooting.md)