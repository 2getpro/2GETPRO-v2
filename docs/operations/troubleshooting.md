# Troubleshooting Guide

## Обзор

Руководство по диагностике и решению типичных проблем.

## Содержание

- [Бот не запускается](#бот-не-запускается)
- [Проблемы с базой данных](#проблемы-с-базой-данных)
- [Проблемы с платежами](#проблемы-с-платежами)
- [Проблемы с webhook](#проблемы-с-webhook)
- [Проблемы с производительностью](#проблемы-с-производительностью)

## Бот не запускается

### Симптомы
- Контейнер постоянно перезапускается
- Ошибка при запуске
- Бот не отвечает на команды

### Диагностика

```bash
# Проверка логов
docker-compose logs bot

# Проверка конфигурации
docker-compose config

# Проверка переменных окружения
docker-compose exec bot env | grep BOT_TOKEN
```

### Решения

**Проблема: Invalid BOT_TOKEN**
```bash
# Проверьте токен
echo $BOT_TOKEN

# Обновите .env
nano .env

# Перезапустите
docker-compose restart bot
```

**Проблема: Не может подключиться к БД**
```bash
# Проверка PostgreSQL
docker-compose ps postgres

# Проверка подключения
docker-compose exec bot python -c "
from db.database_setup import test_connection
import asyncio
asyncio.run(test_connection())
"

# Проверка сети
docker-compose exec bot ping postgres
```

**Проблема: Миграции не применены**
```bash
# Проверка текущей версии
docker-compose exec bot alembic current

# Применение миграций
docker-compose exec bot alembic upgrade head
```

## Проблемы с базой данных

### Симптомы
- Медленные запросы
- Ошибки подключения
- Блокировки таблиц

### Диагностика

```sql
-- Активные подключения
SELECT count(*) FROM pg_stat_activity;

-- Долгие запросы
SELECT pid, now() - query_start as duration, query 
FROM pg_stat_activity 
WHERE state = 'active' 
AND now() - query_start > interval '1 minute';

-- Блокировки
SELECT * FROM pg_locks WHERE NOT granted;

-- Размер БД
SELECT pg_size_pretty(pg_database_size('2getpro_v2'));
```

### Решения

**Проблема: Слишком много подключений**
```bash
# Увеличить max_connections в postgresql.conf
docker-compose exec postgres psql -U postgres -c "ALTER SYSTEM SET max_connections = 200;"
docker-compose restart postgres
```

**Проблема: Медленные запросы**
```sql
-- Создание индексов
CREATE INDEX idx_payments_user_id ON payments(user_id);
CREATE INDEX idx_subscriptions_end_date ON subscriptions(end_date);

-- Vacuum
VACUUM ANALYZE;
```

**Проблема: Блокировки**
```sql
-- Найти блокирующие запросы
SELECT pid, query FROM pg_stat_activity WHERE pid IN (
  SELECT blocking_pid FROM pg_blocking_pids(123)  -- замените 123 на заблокированный PID
);

-- Убить блокирующий процесс (осторожно!)
SELECT pg_terminate_backend(pid);
```

## Проблемы с платежами

### Симптомы
- Платежи не обрабатываются
- Webhook не приходят
- Подписка не активируется

### Диагностика

```bash
# Проверка логов платежей
docker-compose logs bot | grep payment

# Проверка webhook endpoint
curl -I https://your-domain.com/webhook/yookassa

# Проверка последних платежей
docker-compose exec postgres psql -U postgres -d 2getpro_v2 -c "
SELECT payment_id, user_id, provider, status, created_at 
FROM payments 
ORDER BY created_at DESC 
LIMIT 10;
"
```

### Решения

**Проблема: Webhook не приходят**
```bash
# Проверка доступности
curl -X POST https://your-domain.com/webhook/yookassa \
  -H "Content-Type: application/json" \
  -d '{"test": true}'

# Проверка firewall
sudo ufw status

# Проверка nginx
sudo nginx -t
sudo systemctl status nginx
```

**Проблема: Неверная подпись webhook**
```bash
# Проверка секретов
docker-compose exec bot env | grep SECRET

# Обновление секретов
nano .env
docker-compose restart bot
```

**Проблема: Платеж создан, но подписка не активирована**
```sql
-- Проверка платежа
SELECT * FROM payments WHERE payment_id = 123;

-- Проверка подписки
SELECT * FROM subscriptions WHERE user_id = 456;

-- Ручная активация (если необходимо)
-- Используйте admin команды бота
```

## Проблемы с webhook

### Симптомы
- Webhook возвращает ошибку
- Webhook не обрабатывается
- Дублирующиеся обработки

### Диагностика

```bash
# Логи webhook
docker-compose logs bot | grep webhook

# Тест webhook локально
curl -X POST http://localhost:8080/webhook/yookassa \
  -H "Content-Type: application/json" \
  -d @test_webhook.json
```

### Решения

**Проблема: 403 Forbidden**
- Проверьте валидацию подписи
- Проверьте IP whitelist
- Проверьте секретные ключи

**Проблема: 500 Internal Server Error**
```bash
# Проверьте логи
docker-compose logs bot | tail -100

# Проверьте Sentry
# Откройте Sentry dashboard
```

**Проблема: Дублирующиеся обработки**
- Проверьте идемпотентность
- Проверьте логику обработки
- Добавьте уникальные ограничения в БД

## Проблемы с производительностью

### Симптомы
- Медленный отклик бота
- Высокое использование CPU/RAM
- Таймауты запросов

### Диагностика

```bash
# Использование ресурсов
docker stats

# Метрики
curl http://localhost:9090/metrics | grep bot_

# Slow queries
docker-compose exec postgres psql -U postgres -d 2getpro_v2 -c "
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
"
```

### Решения

**Проблема: Высокое использование памяти**
```yaml
# docker-compose.yml
services:
  bot:
    deploy:
      resources:
        limits:
          memory: 2G
```

**Проблема: Медленные запросы**
```sql
-- Добавление индексов
CREATE INDEX CONCURRENTLY idx_name ON table_name(column_name);

-- Оптимизация запросов
EXPLAIN ANALYZE SELECT ...;
```

**Проблема: Redis переполнен**
```bash
# Проверка использования
docker-compose exec redis redis-cli INFO memory

# Очистка кэша
docker-compose exec redis redis-cli FLUSHDB

# Настройка eviction policy
docker-compose exec redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

## Частые ошибки

### "Connection refused" при подключении к БД

**Причина:** PostgreSQL не запущен или недоступен

**Решение:**
```bash
docker-compose ps postgres
docker-compose restart postgres
```

### "Too many connections" в PostgreSQL

**Причина:** Превышен лимит подключений

**Решение:**
```sql
ALTER SYSTEM SET max_connections = 200;
-- Перезапуск PostgreSQL
```

### "Redis connection timeout"

**Причина:** Redis недоступен или перегружен

**Решение:**
```bash
docker-compose restart redis
# Проверка
docker-compose exec redis redis-cli ping
```

### "Webhook signature validation failed"

**Причина:** Неверный секретный ключ

**Решение:**
```bash
# Проверьте ключи в .env
nano .env
# Перезапустите
docker-compose restart bot
```

## Диагностические команды

```bash
# Полная диагностика системы
cat > diagnose.sh << 'EOF'
#!/bin/bash
echo "=== System Info ==="
uname -a
df -h
free -h

echo "=== Docker Status ==="
docker-compose ps

echo "=== Recent Logs ==="
docker-compose logs --tail=50 bot

echo "=== Database Status ==="
docker-compose exec postgres psql -U postgres -c "\l"

echo "=== Redis Status ==="
docker-compose exec redis redis-cli INFO server

echo "=== Network ==="
docker network ls
EOF

chmod +x diagnose.sh
./diagnose.sh
```

## Получение помощи

Если проблема не решена:

1. Соберите диагностическую информацию
2. Проверьте [GitHub Issues](https://github.com/your-repo/issues)
3. Создайте новый Issue с:
   - Описанием проблемы
   - Шагами для воспроизведения
   - Логами
   - Версией системы

## Дополнительные ресурсы

- [Operations Guide](./README.md)
- [Database Management](./database.md)
- [Monitoring](./monitoring.md)
- [Deployment Guide](../deployment/README.md)