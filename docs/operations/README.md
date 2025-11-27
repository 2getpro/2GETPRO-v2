# Операционное руководство

## Обзор

Это руководство описывает ежедневные операционные задачи и процедуры для поддержки 2GETPRO v2 в продакшн окружении.

## Содержание

- [Ежедневные задачи](#ежедневные-задачи)
- [Еженедельные задачи](#еженедельные-задачи)
- [Ежемесячные задачи](#ежемесячные-задачи)
- [Документация](#документация)

## Ежедневные задачи

### Утренняя проверка (9:00)

```bash
# 1. Проверка статуса сервисов
docker-compose ps

# 2. Проверка логов за последние 24 часа
docker-compose logs --since 24h --tail=100 bot | grep ERROR

# 3. Проверка метрик
curl http://localhost:9090/api/v1/query?query=up
```

**Что проверять:**
- ✅ Все контейнеры запущены
- ✅ Нет критических ошибок в логах
- ✅ Метрики собираются
- ✅ Использование ресурсов в норме

### Мониторинг в течение дня

**Каждые 2 часа:**

1. **Проверка Grafana дашбордов**
   - Открыть http://your-server:3000
   - Проверить основные метрики
   - Убедиться в отсутствии аномалий

2. **Проверка Sentry**
   - Открыть Sentry dashboard
   - Проверить новые ошибки
   - Приоритизировать критические

3. **Проверка платежей**
   ```sql
   -- Платежи за последний час
   SELECT COUNT(*), SUM(amount), provider 
   FROM payments 
   WHERE created_at > NOW() - INTERVAL '1 hour'
   GROUP BY provider;
   ```

### Вечерняя проверка (18:00)

```bash
# 1. Проверка бэкапов
ls -lh /backups/ | tail -5

# 2. Проверка дискового пространства
df -h

# 3. Проверка использования памяти
free -h

# 4. Сводка за день
docker-compose exec postgres psql -U postgres -d 2getpro_v2 -c "
SELECT 
  COUNT(DISTINCT user_id) as new_users,
  COUNT(*) FILTER (WHERE status='succeeded') as successful_payments,
  SUM(amount) FILTER (WHERE status='succeeded') as total_revenue
FROM payments 
WHERE created_at::date = CURRENT_DATE;
"
```

## Еженедельные задачи

### Понедельник: Анализ метрик

```bash
# Статистика за неделю
docker-compose exec postgres psql -U postgres -d 2getpro_v2 << EOF
-- Новые пользователи
SELECT COUNT(*) as new_users 
FROM users 
WHERE registration_date > NOW() - INTERVAL '7 days';

-- Активные подписки
SELECT COUNT(*) as active_subscriptions 
FROM subscriptions 
WHERE is_active = true;

-- Доход за неделю
SELECT 
  SUM(amount) as total_revenue,
  COUNT(*) as payment_count,
  AVG(amount) as avg_payment
FROM payments 
WHERE status = 'succeeded' 
AND created_at > NOW() - INTERVAL '7 days';
EOF
```

### Вторник: Обновление зависимостей

```bash
# Проверка обновлений
docker-compose exec bot pip list --outdated

# Обновление (в тестовом окружении сначала!)
# pip install --upgrade package_name
```

### Среда: Проверка безопасности

```bash
# Проверка уязвимостей
docker-compose exec bot pip-audit

# Проверка SSL сертификатов
echo | openssl s_client -servername your-domain.com -connect your-domain.com:443 2>/dev/null | openssl x509 -noout -dates

# Проверка firewall правил
sudo ufw status
```

### Четверг: Оптимизация БД

```bash
# Анализ размера таблиц
docker-compose exec postgres psql -U postgres -d 2getpro_v2 -c "
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"

# Vacuum и analyze
docker-compose exec postgres psql -U postgres -d 2getpro_v2 -c "VACUUM ANALYZE;"
```

### Пятница: Проверка бэкапов

```bash
# Список бэкапов
ls -lh /backups/

# Тестовое восстановление (в тестовом окружении)
gunzip < /backups/latest.sql.gz | docker-compose exec -T postgres psql -U postgres test_db

# Проверка целостности
docker-compose exec postgres pg_dump -U postgres 2getpro_v2 --schema-only > schema_check.sql
```

## Ежемесячные задачи

### Первая неделя: Аудит безопасности

- [ ] Проверка логов доступа
- [ ] Анализ подозрительной активности
- [ ] Обновление паролей (если требуется)
- [ ] Проверка прав доступа
- [ ] Аудит API ключей

### Вторая неделя: Capacity Planning

```bash
# Анализ роста данных
docker-compose exec postgres psql -U postgres -d 2getpro_v2 << EOF
SELECT 
  DATE_TRUNC('month', registration_date) as month,
  COUNT(*) as new_users
FROM users 
GROUP BY month 
ORDER BY month DESC 
LIMIT 12;
EOF

# Прогноз использования диска
df -h | awk '{print $5, $6}' | grep -v Use
```

### Третья неделя: Disaster Recovery Drill

1. Создать тестовый бэкап
2. Развернуть в тестовом окружении
3. Проверить функциональность
4. Документировать время восстановления
5. Обновить DR план

### Четвертая неделя: Отчетность

```bash
# Генерация месячного отчета
docker-compose exec postgres psql -U postgres -d 2getpro_v2 -o monthly_report.txt << EOF
-- Общая статистика
SELECT 
  'Total Users' as metric, COUNT(*)::text as value FROM users
UNION ALL
SELECT 
  'Active Subscriptions', COUNT(*)::text FROM subscriptions WHERE is_active = true
UNION ALL
SELECT 
  'Monthly Revenue', SUM(amount)::text 
  FROM payments 
  WHERE status = 'succeeded' 
  AND created_at > DATE_TRUNC('month', CURRENT_DATE);
EOF
```

## Документация

### Основные руководства

- [Database Management](./database.md) - Управление базой данных
- [Monitoring](./monitoring.md) - Настройка мониторинга
- [Backup & Restore](./backup.md) - Резервное копирование
- [Troubleshooting](./troubleshooting.md) - Решение проблем
- [Security](./security.md) - Безопасность

### Быстрые команды

```bash
# Перезапуск бота
docker-compose restart bot

# Просмотр логов
docker-compose logs -f bot

# Проверка БД
docker-compose exec postgres psql -U postgres -d 2getpro_v2

# Бэкап БД
docker-compose exec postgres pg_dump -U postgres 2getpro_v2 | gzip > backup.sql.gz

# Проверка метрик
curl http://localhost:9090/metrics

# Очистка логов
docker-compose exec bot sh -c "find logs/ -name '*.log' -mtime +7 -delete"
```

### Контакты экстренной поддержки

```
Команда:
- On-call Engineer: [контакт]
- Tech Lead: [контакт]
- DevOps: [контакт]

Внешние сервисы:
- Хостинг: [контакт]
- YooKassa: [контакт]
- Panel Support: [контакт]
```

## Escalation Process

### Level 1: Minor Issues
- Время ответа: 4 часа
- Примеры: Небольшие ошибки, вопросы пользователей
- Ответственный: On-call Engineer

### Level 2: Major Issues
- Время ответа: 1 час
- Примеры: Проблемы с платежами, частичная недоступность
- Ответственный: Tech Lead

### Level 3: Critical Issues
- Время ответа: 15 минут
- Примеры: Полная недоступность, потеря данных, security breach
- Ответственный: Вся команда

## Incident Response

### Шаги при инциденте

1. **Обнаружение**
   - Алерт от мониторинга
   - Сообщение пользователя
   - Проактивная проверка

2. **Оценка**
   - Определить серьезность
   - Оценить влияние
   - Классифицировать

3. **Реагирование**
   - Уведомить команду
   - Начать расследование
   - Применить временное решение

4. **Решение**
   - Найти root cause
   - Применить fix
   - Проверить решение

5. **Документирование**
   - Создать incident report
   - Провести post-mortem
   - Обновить runbook

## Полезные запросы

### Статистика пользователей

```sql
-- Активные пользователи за последние 30 дней
SELECT COUNT(DISTINCT user_id) 
FROM message_logs 
WHERE timestamp > NOW() - INTERVAL '30 days';

-- Топ пользователей по платежам
SELECT 
  u.user_id,
  u.username,
  COUNT(p.payment_id) as payment_count,
  SUM(p.amount) as total_spent
FROM users u
JOIN payments p ON u.user_id = p.user_id
WHERE p.status = 'succeeded'
GROUP BY u.user_id, u.username
ORDER BY total_spent DESC
LIMIT 10;
```

### Статистика платежей

```sql
-- Платежи по провайдерам
SELECT 
  provider,
  COUNT(*) as count,
  SUM(amount) as total,
  AVG(amount) as average
FROM payments
WHERE status = 'succeeded'
AND created_at > NOW() - INTERVAL '30 days'
GROUP BY provider;

-- Конверсия по периодам
SELECT 
  subscription_duration_months,
  COUNT(*) as count,
  SUM(amount) as revenue
FROM payments
WHERE status = 'succeeded'
GROUP BY subscription_duration_months
ORDER BY subscription_duration_months;
```

### Статистика подписок

```sql
-- Истекающие подписки
SELECT 
  COUNT(*) as expiring_soon
FROM subscriptions
WHERE is_active = true
AND end_date BETWEEN NOW() AND NOW() + INTERVAL '7 days';

-- Распределение по провайдерам
SELECT 
  provider,
  COUNT(*) as count
FROM subscriptions
WHERE is_active = true
GROUP BY provider;
```

## Дополнительные ресурсы

- [Deployment Guide](../deployment/README.md)
- [API Documentation](../api/README.md)
- [Development Guide](../development/README.md)