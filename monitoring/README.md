# Система мониторинга и логирования 2GETPRO_v2

Комплексная система мониторинга, включающая Prometheus метрики, Sentry интеграцию, health checks и структурированное логирование.

## Компоненты

### 1. Prometheus Метрики (`metrics/`)

#### PrometheusMetrics
Основные метрики для мониторинга приложения:

**Counter метрики:**
- `http_requests_total` - Общее количество HTTP запросов
- `bot_messages_total` - Количество сообщений бота
- `errors_total` - Количество ошибок
- `payment_requests_total` - Запросы на оплату
- `payment_success_total` - Успешные платежи
- `subscription_created_total` - Созданные подписки

**Histogram метрики:**
- `http_request_duration_seconds` - Длительность HTTP запросов
- `bot_handler_duration_seconds` - Длительность обработки хендлеров
- `payment_processing_duration_seconds` - Длительность обработки платежей

**Gauge метрики:**
- `active_users` - Количество активных пользователей
- `active_subscriptions` - Количество активных подписок
- `database_connections` - Количество подключений к БД

#### CustomMetrics
Бизнес-метрики и метрики для специфичных операций:

- `conversion_rate` - Коэффициент конверсии
- `average_ltv` - Средний LTV пользователя
- `churn_rate` - Процент оттока
- `payment_system_availability` - Доступность платежных систем
- `panel_api_response_time` - Время ответа API панели

### 2. Health Checks (`health/`)

#### HealthChecker
Проверяет состояние всех компонентов системы:

- Подключение к БД
- Подключение к Redis
- Доступность Telegram API
- Доступность панели управления
- Доступность платежных систем

#### ReadinessChecker
Проверяет готовность системы к приему трафика:

- Применение миграций БД
- Доступность кэша
- Готовность подключений

### 3. Sentry Интеграция (`sentry/`)

#### Функции
- Автоматическая отправка ошибок
- Фильтрация чувствительных данных
- Добавление контекста (user_id, action, etc.)
- Группировка ошибок
- Breadcrumbs для отслеживания действий

#### Декоратор error_handler
```python
from monitoring.sentry import error_handler

@error_handler(tags={'module': 'payment'})
async def process_payment(payment_id: int):
    # код обработки платежа
    pass
```

### 4. Логирование (`logging/`)

#### Структурированное логирование
- JSON формат для ELK Stack
- Ротация логов
- Фильтрация чувствительных данных
- Разные уровни для разных модулей

#### StructuredLogger
```python
from monitoring.logging import StructuredLogger

logger = StructuredLogger('my_module')

# Логирование с контекстом
with logger.with_user(user_id=123, username='john'):
    logger.info('User action', action='payment')
```

## Быстрый старт

### 1. Инициализация в main.py

```python
from monitoring.monitor import setup_monitoring, shutdown_monitoring

async def main():
    # Инициализация мониторинга
    monitoring_server = await setup_monitoring(
        # Logging
        log_level='INFO',
        log_dir='logs',
        use_json_logs=True,
        
        # Sentry
        sentry_dsn='https://your-sentry-dsn',
        sentry_environment='production',
        sentry_traces_sample_rate=0.1,
        
        # Monitoring server
        monitoring_host='0.0.0.0',
        monitoring_port=9090,
        enable_monitoring_server=True,
        
        # Health checks
        db_session=db_session,
        redis_url='redis://localhost:6379',
        telegram_token='YOUR_BOT_TOKEN',
        panel_url='https://panel.example.com',
        payment_systems={
            'yookassa': 'https://yookassa.ru',
            'cryptopay': 'https://pay.crypt.bot'
        }
    )
    
    try:
        # Запуск бота
        await bot.start()
    finally:
        # Остановка мониторинга
        await shutdown_monitoring(monitoring_server)
```

### 2. Использование метрик

```python
from monitoring.metrics import PrometheusMetrics, CustomMetrics

# Инкремент счетчика
PrometheusMetrics.increment_payment_success('yookassa')

# Запись времени выполнения
PrometheusMetrics.observe_payment_processing_duration('yookassa', 1.5)

# Установка gauge
PrometheusMetrics.set_active_users(150)

# Кастомные метрики
CustomMetrics.set_conversion_rate('daily', 15.5)
CustomMetrics.increment_referral_revenue('RUB', 1000.0)
```

### 3. Использование декораторов

```python
from monitoring.metrics import PrometheusMetrics
from monitoring.sentry import error_handler

@error_handler(tags={'module': 'payment'})
@PrometheusMetrics.track_time('payment', {'payment_system': 'yookassa'})
async def process_payment(payment_id: int):
    # Автоматический трекинг времени и ошибок
    pass
```

### 4. Структурированное логирование

```python
from monitoring.logging import StructuredLogger

logger = StructuredLogger('payment_service')

# Добавление постоянного контекста
logger.add_context(service='payment', version='1.0.0')

# Логирование с временным контекстом
with logger.with_request_id():
    logger.info('Processing payment', payment_id=123, amount=1000)
    
    try:
        # обработка платежа
        pass
    except Exception as e:
        logger.exception('Payment processing failed', payment_id=123)
```

## Endpoints мониторинга

После запуска сервера мониторинга доступны следующие endpoints:

- `http://localhost:9090/metrics` - Prometheus метрики
- `http://localhost:9090/health` - Health check (все компоненты)
- `http://localhost:9090/ready` - Readiness check (готовность к трафику)
- `http://localhost:9090/live` - Liveness check (сервер работает)

## Интеграция с Prometheus

### prometheus.yml
```yaml
scrape_configs:
  - job_name: '2getpro_bot'
    static_configs:
      - targets: ['localhost:9090']
    scrape_interval: 15s
```

## Интеграция с Grafana

Импортируйте дашборды из `monitoring/grafana/` для визуализации метрик.

## Интеграция с Kubernetes

### Liveness Probe
```yaml
livenessProbe:
  httpGet:
    path: /live
    port: 9090
  initialDelaySeconds: 30
  periodSeconds: 10
```

### Readiness Probe
```yaml
readinessProbe:
  httpGet:
    path: /ready
    port: 9090
  initialDelaySeconds: 5
  periodSeconds: 5
```

## Переменные окружения

```env
# Logging
LOG_LEVEL=INFO
LOG_DIR=logs
USE_JSON_LOGS=true

# Sentry
SENTRY_DSN=https://your-sentry-dsn
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1

# Monitoring
MONITORING_HOST=0.0.0.0
MONITORING_PORT=9090
ENABLE_MONITORING_SERVER=true
```

## Лучшие практики

1. **Метрики:**
   - Используйте Counter для событий (платежи, ошибки)
   - Используйте Histogram для времени выполнения
   - Используйте Gauge для текущих значений (активные пользователи)

2. **Логирование:**
   - Всегда добавляйте контекст (user_id, request_id)
   - Используйте структурированное логирование для ELK
   - Фильтруйте чувствительные данные

3. **Sentry:**
   - Добавляйте теги для группировки ошибок
   - Используйте breadcrumbs для контекста
   - Настройте fingerprint для правильной группировки

4. **Health Checks:**
   - Проверяйте все критичные зависимости
   - Используйте readiness для Kubernetes
   - Настройте алерты на основе health checks

## Troubleshooting

### Метрики не отображаются
- Проверьте, что сервер мониторинга запущен
- Проверьте доступность endpoint `/metrics`
- Проверьте конфигурацию Prometheus

### Ошибки не попадают в Sentry
- Проверьте SENTRY_DSN
- Проверьте сетевое подключение
- Проверьте фильтры ошибок

### Логи не пишутся
- Проверьте права на директорию логов
- Проверьте уровень логирования
- Проверьте конфигурацию handlers

## Дополнительная информация

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Sentry Documentation](https://docs.sentry.io/)
- [Python Logging](https://docs.python.org/3/library/logging.html)