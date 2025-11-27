# Grafana Dashboards для 2GETPRO v2

Этот каталог содержит JSON-конфигурации дашбордов Grafana для мониторинга бота.

## Структура дашбордов

### 1. Bot Overview Dashboard (`bot_overview.json`)

**Основной дашборд с общей информацией о боте**

#### Панели:

**Общие метрики:**
- Статус всех инстансов бота (up/down)
- Общее количество запросов в секунду (RPS)
- Средняя задержка ответа (latency)
- Количество ошибок в секунду
- Процент успешных запросов

**Ресурсы:**
- Использование CPU по инстансам
- Использование памяти по инстансам
- Использование сети (входящий/исходящий трафик)
- Количество горутин

**Бизнес-метрики:**
- Активные пользователи (за последний час/день)
- Новые регистрации
- Активные подписки
- Доход за период
- Конверсия trial → paid

**Алерты:**
- Активные критические алерты
- Активные предупреждения
- История алертов за последние 24 часа

#### Queries примеры:

```promql
# RPS
sum(rate(bot_requests_total[5m]))

# Error rate
sum(rate(bot_errors_total[5m])) / sum(rate(bot_requests_total[5m])) * 100

# Memory usage
bot_memory_usage_bytes / bot_memory_limit_bytes * 100

# Active users
bot_active_users_total

# Revenue
sum(increase(bot_payment_amount_total[24h]))
```

---

### 2. Performance Dashboard (`bot_performance.json`)

**Детальный анализ производительности**

#### Панели:

**Request Metrics:**
- Request rate по эндпоинтам
- Response time percentiles (p50, p95, p99)
- Request duration histogram
- Slow requests (>2s)

**Database Performance:**
- Query duration
- Connection pool usage
- Slow queries count
- Transaction rate

**Cache Performance:**
- Redis hit/miss ratio
- Cache response time
- Memory usage
- Eviction rate

**External APIs:**
- Payment gateway response time
- Panel API response time
- Timeout rate
- Error rate по провайдерам

#### Queries примеры:

```promql
# P95 latency
histogram_quantile(0.95, rate(bot_request_duration_seconds_bucket[5m]))

# DB connection pool
bot_db_connections_active / bot_db_connections_max * 100

# Cache hit ratio
rate(bot_cache_hits_total[5m]) / (rate(bot_cache_hits_total[5m]) + rate(bot_cache_misses_total[5m])) * 100
```

---

### 3. Business Metrics Dashboard (`bot_business.json`)

**Бизнес-метрики и аналитика**

#### Панели:

**Users:**
- Total users
- New users (hourly/daily)
- Active users (DAU/MAU)
- User retention rate
- Churn rate

**Subscriptions:**
- Active subscriptions by plan
- New subscriptions
- Cancellations
- Renewal rate
- Trial conversions

**Revenue:**
- Total revenue
- Revenue by payment method
- Revenue by subscription plan
- Average revenue per user (ARPU)
- Lifetime value (LTV)

**Payments:**
- Successful payments
- Failed payments
- Payment failure reasons
- Refunds
- Average transaction value

**Referrals:**
- Referral conversions
- Referral revenue
- Top referrers

#### Queries примеры:

```promql
# DAU
count(bot_user_last_activity_timestamp > (time() - 86400))

# Conversion rate
sum(increase(bot_subscription_activations_total[24h])) / sum(increase(bot_trial_starts_total[24h])) * 100

# ARPU
sum(increase(bot_payment_amount_total[30d])) / count(bot_user_subscription_active == 1)
```

---

### 4. Infrastructure Dashboard (`infrastructure.json`)

**Мониторинг инфраструктуры**

#### Панели:

**System Resources:**
- CPU usage by node
- Memory usage by node
- Disk usage
- Network I/O
- System load

**PostgreSQL:**
- Connection count
- Query rate
- Slow queries
- Cache hit ratio
- Replication lag
- Database size

**Redis:**
- Memory usage
- Hit/miss ratio
- Connected clients
- Commands per second
- Evicted keys

**Nginx:**
- Request rate
- Response codes
- Active connections
- Request duration
- Upstream response time

**Kubernetes:**
- Pod status
- Container restarts
- Resource limits
- Node status

#### Queries примеры:

```promql
# Node CPU
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Postgres connections
pg_stat_activity_count

# Redis memory
redis_memory_used_bytes / redis_memory_max_bytes * 100

# Nginx requests
rate(nginx_http_requests_total[5m])
```

---

### 5. Security Dashboard (`security.json`)

**Мониторинг безопасности**

#### Панели:

**Authentication:**
- Failed login attempts
- Suspicious activity patterns
- Blocked IPs
- Rate limit hits

**API Security:**
- Invalid tokens
- Unauthorized access attempts
- API abuse patterns

**Payment Security:**
- Fraud detection alerts
- Suspicious transactions
- Chargeback rate

**System Security:**
- Failed SSH attempts
- Sudo usage
- File integrity violations

#### Queries примеры:

```promql
# Failed auth attempts
rate(bot_failed_auth_attempts_total[5m])

# Rate limit hits
rate(bot_rate_limit_hits_total[5m])

# Suspicious payments
bot_payment_fraud_score > 0.7
```

---

## Установка дашбордов

### Автоматическая установка (через provisioning):

1. Поместите JSON файлы в `/etc/grafana/provisioning/dashboards/`
2. Создайте конфигурацию provisioning:

```yaml
apiVersion: 1

providers:
  - name: '2GETPRO v2'
    orgId: 1
    folder: 'Bot Monitoring'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
```

3. Перезапустите Grafana

### Ручная установка:

1. Откройте Grafana UI
2. Перейдите в Dashboards → Import
3. Загрузите JSON файл или вставьте содержимое
4. Выберите Prometheus datasource
5. Нажмите Import

## Создание собственных дашбордов

### Рекомендации:

1. **Используйте переменные** для фильтрации по инстансам, окружениям и т.д.
2. **Группируйте панели** по логическим блокам
3. **Добавляйте описания** к панелям для понимания метрик
4. **Используйте цветовые схемы** для быстрой идентификации проблем
5. **Настройте алерты** прямо в дашбордах
6. **Экспортируйте дашборды** в JSON для версионирования

### Полезные переменные:

```
$instance - выбор инстанса бота
$interval - интервал агрегации
$environment - окружение (prod/staging)
$datasource - источник данных
```

### Примеры панелей:

**Time Series (график):**
```json
{
  "type": "timeseries",
  "title": "Request Rate",
  "targets": [{
    "expr": "sum(rate(bot_requests_total{instance=~\"$instance\"}[5m]))",
    "legendFormat": "{{instance}}"
  }]
}
```

**Stat (число):**
```json
{
  "type": "stat",
  "title": "Active Users",
  "targets": [{
    "expr": "bot_active_users_total"
  }],
  "options": {
    "colorMode": "value",
    "graphMode": "area"
  }
}
```

**Gauge (шкала):**
```json
{
  "type": "gauge",
  "title": "Memory Usage",
  "targets": [{
    "expr": "bot_memory_usage_bytes / bot_memory_limit_bytes * 100"
  }],
  "options": {
    "min": 0,
    "max": 100,
    "thresholds": {
      "steps": [
        {"value": 0, "color": "green"},
        {"value": 70, "color": "yellow"},
        {"value": 90, "color": "red"}
      ]
    }
  }
}
```

## Troubleshooting

### Дашборд не отображает данные:

1. Проверьте, что Prometheus собирает метрики: `http://prometheus:9090/targets`
2. Проверьте datasource в Grafana: Configuration → Data Sources
3. Проверьте query в панели: Edit → Query Inspector
4. Проверьте временной диапазон

### Медленная загрузка дашборда:

1. Уменьшите временной диапазон
2. Увеличьте интервал агрегации ($interval)
3. Используйте recording rules в Prometheus
4. Оптимизируйте queries (избегайте `rate()` на больших диапазонах)

### Дашборд не обновляется:

1. Проверьте auto-refresh настройки
2. Проверьте, что Prometheus получает новые данные
3. Очистите кэш браузера
4. Проверьте логи Grafana

## Дополнительные ресурсы

- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Query Examples](https://prometheus.io/docs/prometheus/latest/querying/examples/)
- [PromQL Cheat Sheet](https://promlabs.com/promql-cheat-sheet/)