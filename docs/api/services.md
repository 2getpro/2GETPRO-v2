# Документация Сервисов

## Обзор

Сервисы содержат бизнес-логику приложения и предоставляют высокоуровневый API для работы с различными функциями системы.

## Содержание

- [BalanceService](#balanceservice)
- [SubscriptionService](#subscriptionservice)
- [PaymentService](#paymentservice)
- [ReferralService](#referralservice)
- [PromoCodeService](#promocodeservice)
- [NotificationService](#notificationservice)
- [PanelApiService](#panelapiservice)

---

## BalanceService

Управление балансом пользователей.

### Расположение

[`bot/services/balance_service.py`](../../bot/services/balance_service.py:1)

### Инициализация

```python
from bot.services.balance_service import BalanceService

service = BalanceService(session=async_session)
```

### Методы

#### add_balance()

Пополнить баланс пользователя.

```python
async def add_balance(
    user_id: int,
    amount_kopeks: int,
    description: Optional[str] = None
) -> Transaction
```

**Параметры:**
- `user_id` - ID пользователя
- `amount_kopeks` - Сумма в копейках (положительное число)
- `description` - Описание операции

**Возвращает:** Объект [`Transaction`](../../db/models.py:274)

**Исключения:**
- `ValueError` - Если сумма <= 0 или пользователь не найден

**Пример:**

```python
transaction = await service.add_balance(
    user_id=123456,
    amount_kopeks=10000,  # 100 рублей
    description="Пополнение баланса"
)
print(f"Новый баланс: {transaction.user.balance_kopeks}")
```

#### deduct_balance()

Списать средства с баланса.

```python
async def deduct_balance(
    user_id: int,
    amount_kopeks: int,
    description: Optional[str] = None
) -> Transaction
```

**Параметры:**
- `user_id` - ID пользователя
- `amount_kopeks` - Сумма списания в копейках
- `description` - Описание операции

**Возвращает:** Объект [`Transaction`](../../db/models.py:274)

**Исключения:**
- `ValueError` - Если недостаточно средств или пользователь не найден

**Пример:**

```python
try:
    transaction = await service.deduct_balance(
        user_id=123456,
        amount_kopeks=5000,
        description="Покупка подписки"
    )
except ValueError as e:
    print(f"Ошибка: {e}")
```

#### get_balance()

Получить текущий баланс.

```python
async def get_balance(user_id: int) -> int
```

**Возвращает:** Баланс в копейках

#### can_afford()

Проверить достаточность средств.

```python
async def can_afford(user_id: int, amount_kopeks: int) -> bool
```

**Возвращает:** `True` если средств достаточно

#### get_transaction_history()

Получить историю транзакций.

```python
async def get_transaction_history(
    user_id: int,
    limit: int = 10,
    offset: int = 0
) -> List[Transaction]
```

**Пример:**

```python
transactions = await service.get_transaction_history(
    user_id=123456,
    limit=20
)
for tx in transactions:
    print(f"{tx.created_at}: {tx.amount_kopeks/100} руб - {tx.description}")
```

---

## SubscriptionService

Управление подписками пользователей.

### Расположение

[`bot/services/subscription_service.py`](../../bot/services/subscription_service.py:1)

### Инициализация

```python
from bot.services.subscription_service import SubscriptionService

service = SubscriptionService(
    settings=settings,
    panel_service=panel_service,
    bot=bot,
    i18n=i18n
)
```

### Методы

#### activate_trial_subscription()

Активировать пробную подписку.

```python
async def activate_trial_subscription(
    session: AsyncSession,
    user_id: int
) -> Optional[Dict[str, Any]]
```

**Возвращает:**

```python
{
    "eligible": True,
    "activated": True,
    "end_date": datetime,
    "days": 3,
    "traffic_gb": 5.0,
    "panel_user_uuid": "uuid",
    "subscription_url": "https://..."
}
```

**Пример:**

```python
result = await service.activate_trial_subscription(session, user_id=123456)
if result["activated"]:
    print(f"Триал активирован до {result['end_date']}")
```

#### activate_subscription()

Активировать платную подписку.

```python
async def activate_subscription(
    session: AsyncSession,
    user_id: int,
    months: int,
    payment_amount: float,
    payment_db_id: int,
    promo_code_id_from_payment: Optional[int] = None,
    provider: str = "yookassa"
) -> Optional[Dict[str, Any]]
```

**Параметры:**
- `months` - Количество месяцев (1, 3, 6, 12)
- `payment_amount` - Сумма платежа
- `payment_db_id` - ID платежа в БД
- `promo_code_id_from_payment` - ID промокода (опционально)
- `provider` - Провайдер платежа

**Возвращает:**

```python
{
    "subscription_id": 123,
    "end_date": datetime,
    "is_active": True,
    "panel_user_uuid": "uuid",
    "subscription_url": "https://...",
    "applied_promo_bonus_days": 7
}
```

#### extend_active_subscription_days()

Продлить активную подписку на N дней.

```python
async def extend_active_subscription_days(
    session: AsyncSession,
    user_id: int,
    bonus_days: int,
    reason: str = "bonus"
) -> Optional[datetime]
```

**Параметры:**
- `bonus_days` - Количество дней для продления
- `reason` - Причина продления (admin, promo code, referral, bonus)

**Возвращает:** Новая дата окончания

**Пример:**

```python
new_end = await service.extend_active_subscription_days(
    session=session,
    user_id=123456,
    bonus_days=7,
    reason="referral bonus"
)
```

#### get_active_subscription_details()

Получить детали активной подписки.

```python
async def get_active_subscription_details(
    session: AsyncSession,
    user_id: int
) -> Optional[Dict[str, Any]]
```

**Возвращает:**

```python
{
    "user_id": "panel-uuid",
    "end_date": datetime,
    "status_from_panel": "ACTIVE",
    "config_link": "https://...",
    "traffic_limit_bytes": 107374182400,
    "traffic_used_bytes": 5368709120,
    "max_devices": 5
}
```

#### get_subscriptions_ending_soon()

Получить подписки, истекающие в ближайшие N дней.

```python
async def get_subscriptions_ending_soon(
    session: AsyncSession,
    days_threshold: int
) -> List[Dict[str, Any]]
```

**Используется:** Для отправки уведомлений об истечении

---

## PaymentService

Обработка платежей через различные провайдеры.

### YooKassaService

[`bot/services/yookassa_service.py`](../../bot/services/yookassa_service.py:1)

#### create_payment()

```python
async def create_payment(
    amount: float,
    currency: str,
    description: str,
    metadata: Dict[str, Any],
    receipt_email: Optional[str] = None,
    save_payment_method: bool = False,
    payment_method_id: Optional[str] = None,
    capture: bool = True
) -> Optional[Dict[str, Any]]
```

**Параметры:**
- `amount` - Сумма платежа
- `currency` - Валюта (RUB, USD, EUR)
- `description` - Описание платежа
- `metadata` - Метаданные (user_id, subscription_months)
- `receipt_email` - Email для чека
- `save_payment_method` - Сохранить платежный метод
- `payment_method_id` - ID сохраненного метода
- `capture` - Автоматическое подтверждение

**Пример:**

```python
payment = await yookassa_service.create_payment(
    amount=100.0,
    currency="RUB",
    description="Подписка на 1 месяц",
    metadata={
        "user_id": "123456",
        "subscription_months": "1"
    },
    receipt_email="user@example.com",
    save_payment_method=True
)

if payment:
    confirmation_url = payment["confirmation_url"]
    # Отправить URL пользователю
```

### CryptoPayService

[`bot/services/crypto_pay_service.py`](../../bot/services/crypto_pay_service.py:1)

#### create_invoice()

```python
async def create_invoice(
    session: AsyncSession,
    user_id: int,
    months: int,
    amount: float,
    description: str
) -> Optional[str]
```

**Возвращает:** URL для оплаты

### FreeKassaService

[`bot/services/freekassa_service.py`](../../bot/services/freekassa_service.py:1)

#### create_order()

```python
async def create_order(
    payment_db_id: int,
    user_id: int,
    months: int,
    amount: float,
    currency: Optional[str],
    email: Optional[str] = None,
    ip_address: Optional[str] = None
) -> Tuple[bool, Dict[str, Any]]
```

**Возвращает:** `(success, response_data)`

---

## ReferralService

Управление реферальной программой.

### Расположение

[`bot/services/referral_service.py`](../../bot/services/referral_service.py:1)

### Методы

#### apply_referral_bonuses_for_payment()

Применить реферальные бонусы при оплате.

```python
async def apply_referral_bonuses_for_payment(
    session: AsyncSession,
    user_id: int,
    months: int,
    current_payment_db_id: int,
    skip_if_active_before_payment: bool = False
) -> Optional[Dict[str, Any]]
```

**Логика:**

1. Проверка наличия реферера
2. Проверка условий (первый платеж, если `REFERRAL_ONE_BONUS_PER_REFEREE=true`)
3. Начисление бонуса рефереру
4. Начисление бонуса рефералу

**Возвращает:**

```python
{
    "inviter_bonus_applied_days": 7,
    "inviter_new_end_date": datetime,
    "referee_bonus_applied_days": 3,
    "referee_new_end_date": datetime
}
```

**Конфигурация:**

```env
# Бонусы для реферера
REFERRAL_BONUS_DAYS_1_MONTH=3
REFERRAL_BONUS_DAYS_3_MONTHS=7
REFERRAL_BONUS_DAYS_6_MONTHS=15
REFERRAL_BONUS_DAYS_12_MONTHS=30

# Бонусы для реферала
REFEREE_BONUS_DAYS_1_MONTH=1
REFEREE_BONUS_DAYS_3_MONTHS=3
REFEREE_BONUS_DAYS_6_MONTHS=7
REFEREE_BONUS_DAYS_12_MONTHS=15

# Одноразовый бонус
REFERRAL_ONE_BONUS_PER_REFEREE=true
```

---

## PromoCodeService

Управление промокодами.

### Расположение

[`bot/services/promo_code_service.py`](../../bot/services/promo_code_service.py:1)

### Методы

#### create_promo_code()

```python
async def create_promo_code(
    session: AsyncSession,
    code: str,
    bonus_days: int,
    max_activations: int,
    admin_id: int,
    valid_until: Optional[datetime] = None
) -> PromoCode
```

#### activate_promo_code()

```python
async def activate_promo_code(
    session: AsyncSession,
    code: str,
    user_id: int
) -> Dict[str, Any]
```

**Возвращает:**

```python
{
    "success": True,
    "bonus_days": 7,
    "new_end_date": datetime,
    "message_key": "promo_activated"
}
```

**Проверки:**

1. Промокод существует и активен
2. Не истек срок действия
3. Не превышен лимит активаций
4. Пользователь не активировал ранее

---

## NotificationService

Отправка уведомлений администраторам.

### Расположение

[`bot/services/notification_service.py`](../../bot/services/notification_service.py:1)

### Методы

#### notify_payment_received()

```python
async def notify_payment_received(
    user_id: int,
    amount: float,
    currency: str,
    months: int,
    payment_provider: str,
    username: Optional[str] = None
)
```

**Отправляет:** Уведомление в LOG_CHAT_ID

**Формат:**

```
💰 Новый платеж

👤 Пользователь: @username (123456)
💵 Сумма: 100.00 RUB
📅 Подписка: 1 мес.
💳 Провайдер: yookassa
🕐 Время: 2024-01-01 12:00:00
```

#### notify_new_user()

```python
async def notify_new_user(
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None
)
```

#### notify_trial_activation()

```python
async def notify_trial_activation(
    user_id: int,
    username: Optional[str] = None
)
```

#### notify_promo_activation()

```python
async def notify_promo_activation(
    user_id: int,
    promo_code: str,
    bonus_days: int,
    username: Optional[str] = None
)
```

**Конфигурация:**

```env
LOG_CHAT_ID=-1001234567890
LOG_THREAD_ID=123  # Опционально для супергрупп

# Типы уведомлений
LOG_NEW_USERS=true
LOG_PAYMENTS=true
LOG_PROMO_ACTIVATIONS=true
LOG_TRIAL_ACTIVATIONS=true
LOG_SUSPICIOUS_ACTIVITY=true
```

---

## PanelApiService

Интеграция с панелью управления Remnawave.

### Расположение

[`bot/services/panel_api_service.py`](../../bot/services/panel_api_service.py:1)

### Методы

#### create_panel_user()

```python
async def create_panel_user(
    username_on_panel: str,
    telegram_id: int,
    description: str,
    specific_squad_uuids: Optional[List[str]] = None,
    external_squad_uuid: Optional[str] = None,
    default_traffic_limit_bytes: int = 0,
    default_traffic_limit_strategy: str = "NO_RESET"
) -> Dict[str, Any]
```

#### get_user_by_uuid()

```python
async def get_user_by_uuid(panel_user_uuid: str) -> Optional[Dict[str, Any]]
```

#### get_users_by_filter()

```python
async def get_users_by_filter(
    telegram_id: Optional[int] = None,
    username: Optional[str] = None
) -> List[Dict[str, Any]]
```

#### update_user_details_on_panel()

```python
async def update_user_details_on_panel(
    panel_user_uuid: str,
    update_payload: Dict[str, Any],
    log_response: bool = True
) -> Optional[Dict[str, Any]]
```

**Пример обновления:**

```python
payload = {
    "expireAt": "2024-12-31T23:59:59.999Z",
    "status": "ACTIVE",
    "trafficLimitBytes": 107374182400,  # 100 GB
    "trafficLimitStrategy": "NO_RESET"
}

result = await panel_service.update_user_details_on_panel(
    panel_user_uuid="user-uuid",
    update_payload=payload
)
```

---

## Общие паттерны

### Обработка ошибок

```python
try:
    result = await service.some_method(...)
except ValueError as e:
    # Ошибка валидации
    logging.error(f"Validation error: {e}")
except Exception as e:
    # Неожиданная ошибка
    logging.error(f"Unexpected error: {e}", exc_info=True)
    await session.rollback()
```

### Транзакции

```python
async with async_session_factory() as session:
    try:
        # Выполнение операций
        await service.method1(session, ...)
        await service.method2(session, ...)
        
        # Коммит
        await session.commit()
    except Exception as e:
        # Откат при ошибке
        await session.rollback()
        raise
```

### Логирование

```python
import logging

logging.info(f"Operation started: user_id={user_id}")
logging.debug(f"Details: {data}")
logging.warning(f"Potential issue: {issue}")
logging.error(f"Error occurred: {error}", exc_info=True)
```

## Тестирование

### Unit тесты

```python
import pytest
from bot.services.balance_service import BalanceService

@pytest.mark.asyncio
async def test_add_balance(db_session, test_user):
    service = BalanceService(db_session)
    
    transaction = await service.add_balance(
        user_id=test_user.user_id,
        amount_kopeks=10000,
        description="Test"
    )
    
    assert transaction.amount_kopeks == 10000
    assert test_user.balance_kopeks == 10000
```

### Integration тесты

```python
@pytest.mark.asyncio
async def test_payment_flow(db_session, test_user, yookassa_service):
    # Создание платежа
    payment = await yookassa_service.create_payment(...)
    assert payment["status"] == "pending"
    
    # Симуляция webhook
    await process_webhook(payment["id"])
    
    # Проверка активации подписки
    sub = await subscription_dal.get_active_subscription(...)
    assert sub.is_active
```

## Дополнительные ресурсы

- [API Overview](./README.md)
- [Webhook Documentation](./webhooks.md)
- [Database Models](../../db/models.py)
- [Testing Guide](../development/testing.md)