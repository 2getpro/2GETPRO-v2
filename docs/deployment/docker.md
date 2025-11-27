# Docker Развертывание

## Обзор

Docker Compose - рекомендуемый способ развертывания 2GETPRO v2 для большинства случаев использования.

## Содержание

- [Подготовка окружения](#подготовка-окружения)
- [Конфигурация](#конфигурация)
- [Запуск](#запуск)
- [Управление](#управление)
- [Мониторинг](#мониторинг)
- [Обновление](#обновление)

## Подготовка окружения

### Установка Docker

#### Ubuntu/Debian

```bash
# Удаление старых версий
sudo apt remove docker docker-engine docker.io containerd runc

# Установка зависимостей
sudo apt update
sudo apt install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Добавление GPG ключа Docker
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Добавление репозитория
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Установка Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Проверка установки
docker --version
docker compose version
```

#### CentOS/RHEL

```bash
# Установка зависимостей
sudo yum install -y yum-utils

# Добавление репозитория
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# Установка Docker
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Запуск Docker
sudo systemctl start docker
sudo systemctl enable docker

# Проверка
docker --version
```

### Настройка пользователя

```bash
# Добавление пользователя в группу docker
sudo usermod -aG docker $USER

# Применение изменений
newgrp docker

# Проверка
docker ps
```

### Настройка Docker

Создайте `/etc/docker/daemon.json`:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "default-address-pools": [
    {
      "base": "172.17.0.0/16",
      "size": 24
    }
  ]
}
```

Перезапустите Docker:

```bash
sudo systemctl restart docker
```

## Конфигурация

### Структура файлов

```
2GETPRO_v2/
├── docker-compose.yml       # Основная конфигурация
├── Dockerfile              # Образ приложения
├── .env                    # Переменные окружения
├── .env.example           # Пример конфигурации
└── infrastructure/
    ├── nginx/
    │   └── nginx.conf     # Конфигурация Nginx
    └── prometheus/
        └── prometheus.yml # Конфигурация Prometheus
```

### Файл docker-compose.yml

Основной файл уже создан в [`docker-compose.yml`](../../docker-compose.yml:1). Рассмотрим его компоненты:

#### PostgreSQL

```yaml
postgres:
  image: postgres:15-alpine
  container_name: 2getpro_v2_postgres
  environment:
    POSTGRES_DB: ${DB_NAME:-2getpro_v2}
    POSTGRES_USER: ${DB_USER:-postgres}
    POSTGRES_PASSWORD: ${DB_PASSWORD:-postgres}
  volumes:
    - postgres_data:/var/lib/postgresql/data
  ports:
    - "${DB_PORT:-5432}:5432"
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-postgres}"]
    interval: 10s
    timeout: 5s
    retries: 5
```

#### Redis

```yaml
redis:
  image: redis:7-alpine
  container_name: 2getpro_v2_redis
  command: redis-server --requirepass ${REDIS_PASSWORD:-}
  volumes:
    - redis_data:/data
  ports:
    - "${REDIS_PORT:-6379}:6379"
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 5s
    retries: 5
```

#### Bot Service

```yaml
bot:
  build: .
  container_name: 2getpro_v2_bot
  env_file:
    - .env
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy
  volumes:
    - ./logs:/app/logs
    - ./backups:/app/backups
    - ./cache:/app/cache
  restart: unless-stopped
```

### Конфигурация .env

Скопируйте и отредактируйте:

```bash
cp .env.example .env
nano .env
```

**Критически важные параметры:**

```env
# ===== BOT CONFIGURATION =====
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_IDS=123456789,987654321

# ===== DATABASE =====
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=2getpro_v2
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_strong_password_here

# ===== REDIS =====
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password
REDIS_ENABLED=true

# ===== PANEL API =====
PANEL_API_URL=https://your-panel.example.com
PANEL_API_KEY=your_panel_api_key_here
PANEL_WEBHOOK_SECRET=your_webhook_secret

# ===== PAYMENT SYSTEMS =====
# YooKassa
YOOKASSA_ENABLED=true
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key
YOOKASSA_RETURN_URL=https://t.me/your_bot

# CryptoPay
CRYPTOPAY_ENABLED=true
CRYPTOPAY_TOKEN=your_cryptopay_token
CRYPTOPAY_NETWORK=mainnet

# FreeKassa
FREEKASSA_ENABLED=false
FREEKASSA_MERCHANT_ID=your_merchant_id
FREEKASSA_API_KEY=your_api_key
FREEKASSA_SECOND_SECRET=your_second_secret

# Tribute
TRIBUTE_ENABLED=true
TRIBUTE_API_KEY=your_tribute_api_key

# ===== WEBHOOK =====
WEBHOOK_BASE_URL=https://your-domain.com
WEBHOOK_VALIDATION_ENABLED=true

# ===== MONITORING =====
SENTRY_DSN=your_sentry_dsn
SENTRY_ENABLED=true
SENTRY_ENVIRONMENT=production

PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090

# ===== SECURITY =====
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_WINDOW=60

# ===== FEATURES =====
TRIAL_ENABLED=true
TRIAL_DURATION_DAYS=3
TRIAL_TRAFFIC_LIMIT_GB=5.0

REFERRAL_ENABLED=true
REFERRAL_ONE_BONUS_PER_REFEREE=true

# ===== PRICES =====
1_MONTH_ENABLED=true
RUB_PRICE_1_MONTH=100
STARS_PRICE_1_MONTH=100

3_MONTHS_ENABLED=true
RUB_PRICE_3_MONTHS=270
STARS_PRICE_3_MONTHS=270

6_MONTHS_ENABLED=true
RUB_PRICE_6_MONTHS=500
STARS_PRICE_6_MONTHS=500

12_MONTHS_ENABLED=true
RUB_PRICE_12_MONTHS=900
STARS_PRICE_12_MONTHS=900
```

### Dockerfile

Образ приложения определен в [`Dockerfile`](../../Dockerfile:1):

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Python зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код приложения
COPY . .

# Директории
RUN mkdir -p logs cache backups

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["python", "main.py"]
```

## Запуск

### Первый запуск

```bash
# 1. Клонирование репозитория
git clone https://github.com/your-repo/2GETPRO_v2.git
cd 2GETPRO_v2

# 2. Конфигурация
cp .env.example .env
nano .env  # Отредактируйте параметры

# 3. Сборка образов
docker compose build

# 4. Запуск сервисов
docker compose up -d

# 5. Проверка статуса
docker compose ps

# 6. Просмотр логов
docker compose logs -f bot
```

### Применение миграций

```bash
# Автоматически при запуске или вручную:
docker compose exec bot alembic upgrade head

# Проверка текущей версии
docker compose exec bot alembic current

# История миграций
docker compose exec bot alembic history
```

### Проверка работоспособности

```bash
# Проверка всех контейнеров
docker compose ps

# Проверка логов
docker compose logs --tail=50 bot

# Проверка БД
docker compose exec postgres psql -U postgres -d 2getpro_v2 -c "\dt"

# Проверка Redis
docker compose exec redis redis-cli ping

# Проверка webhook endpoint
curl -I http://localhost:8080/health
```

## Управление

### Основные команды

```bash
# Запуск всех сервисов
docker compose up -d

# Остановка всех сервисов
docker compose down

# Перезапуск конкретного сервиса
docker compose restart bot

# Просмотр логов
docker compose logs -f bot

# Просмотр логов всех сервисов
docker compose logs -f

# Выполнение команды в контейнере
docker compose exec bot python -c "print('Hello')"

# Вход в контейнер
docker compose exec bot bash

# Просмотр ресурсов
docker compose stats
```

### Управление данными

```bash
# Создание бэкапа БД
docker compose exec postgres pg_dump -U postgres 2getpro_v2 > backup.sql

# Восстановление из бэкапа
docker compose exec -T postgres psql -U postgres 2getpro_v2 < backup.sql

# Очистка логов
docker compose exec bot sh -c "rm -rf logs/*.log"

# Очистка кэша
docker compose exec bot sh -c "rm -rf cache/*"
```

### Масштабирование

Для увеличения количества worker'ов:

```yaml
# docker-compose.override.yml
services:
  bot:
    deploy:
      replicas: 3
```

Запуск:

```bash
docker compose up -d --scale bot=3
```

## Мониторинг

### Логи

```bash
# Все логи
docker compose logs

# Логи конкретного сервиса
docker compose logs bot

# Следить за логами в реальном времени
docker compose logs -f bot

# Последние N строк
docker compose logs --tail=100 bot

# Логи с временными метками
docker compose logs -t bot

# Логи за период
docker compose logs --since 2024-01-01T00:00:00 bot
```

### Метрики

#### Prometheus

Доступ: `http://localhost:9090`

Примеры запросов:

```promql
# Количество запросов
rate(bot_requests_total[5m])

# Использование памяти
container_memory_usage_bytes{name="2getpro_v2_bot"}

# CPU usage
rate(container_cpu_usage_seconds_total{name="2getpro_v2_bot"}[5m])
```

#### Grafana

Доступ: `http://localhost:3000` (admin/admin)

Импортируйте дашборды:
- Docker Container Metrics (ID: 193)
- PostgreSQL Database (ID: 9628)
- Redis Dashboard (ID: 11835)

### Health Checks

```bash
# Проверка здоровья контейнеров
docker compose ps

# Детальная информация
docker inspect 2getpro_v2_bot | jq '.[0].State.Health'

# Проверка через API
curl http://localhost:8080/health
```

## Обновление

### Обновление кода

```bash
# 1. Остановка сервисов
docker compose down

# 2. Обновление кода
git pull origin main

# 3. Обновление зависимостей
docker compose build --no-cache

# 4. Применение миграций
docker compose run --rm bot alembic upgrade head

# 5. Запуск
docker compose up -d

# 6. Проверка
docker compose logs -f bot
```

### Обновление образов

```bash
# Обновление базовых образов
docker compose pull

# Пересборка с новыми образами
docker compose build --pull

# Запуск
docker compose up -d
```

### Откат версии

```bash
# Остановка
docker compose down

# Откат кода
git checkout v1.0.0  # или нужный тег

# Откат миграций
docker compose run --rm bot alembic downgrade <revision>

# Пересборка
docker compose build

# Запуск
docker compose up -d
```

## Резервное копирование

### Автоматический бэкап

Создайте скрипт `backup.sh`:

```bash
#!/bin/bash
set -e

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

# Создание директории
mkdir -p "$BACKUP_DIR"

# Бэкап PostgreSQL
echo "Backing up PostgreSQL..."
docker compose exec -T postgres pg_dump -U postgres 2getpro_v2 | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# Бэкап Redis (опционально)
echo "Backing up Redis..."
docker compose exec -T redis redis-cli --rdb /data/dump.rdb SAVE
docker cp 2getpro_v2_redis:/data/dump.rdb "$BACKUP_DIR/redis_$DATE.rdb"

# Бэкап конфигурации
echo "Backing up configuration..."
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" .env docker-compose.yml

# Удаление старых бэкапов
echo "Cleaning old backups..."
find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "redis_*.rdb" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "config_*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $DATE"
```

Добавьте в cron:

```bash
chmod +x backup.sh

# Ежедневно в 3:00
echo "0 3 * * * /path/to/backup.sh >> /var/log/backup.log 2>&1" | crontab -
```

### Восстановление

```bash
# Восстановление БД
gunzip < backup.sql.gz | docker compose exec -T postgres psql -U postgres 2getpro_v2

# Восстановление Redis
docker cp redis_backup.rdb 2getpro_v2_redis:/data/dump.rdb
docker compose restart redis

# Восстановление конфигурации
tar -xzf config_backup.tar.gz
```

## Troubleshooting

### Контейнер не запускается

```bash
# Проверка логов
docker compose logs bot

# Проверка конфигурации
docker compose config

# Проверка образа
docker compose build --no-cache bot

# Запуск в интерактивном режиме
docker compose run --rm bot bash
```

### Проблемы с сетью

```bash
# Проверка сетей
docker network ls

# Проверка подключений
docker compose exec bot ping postgres
docker compose exec bot ping redis

# Пересоздание сети
docker compose down
docker network prune
docker compose up -d
```

### Проблемы с volumes

```bash
# Список volumes
docker volume ls

# Проверка использования
docker volume inspect 2getpro_v2_postgres_data

# Очистка неиспользуемых volumes
docker volume prune

# Пересоздание volume
docker compose down -v
docker compose up -d
```

### Высокое использование ресурсов

```bash
# Мониторинг ресурсов
docker stats

# Ограничение ресурсов в docker-compose.yml
services:
  bot:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## Оптимизация

### Уменьшение размера образа

```dockerfile
# Многоступенчатая сборка
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["python", "main.py"]
```

### Кэширование слоев

```dockerfile
# Сначала зависимости (меняются реже)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Потом код (меняется чаще)
COPY . .
```

### Оптимизация логов

```yaml
services:
  bot:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## Дополнительные ресурсы

- [Deployment Overview](./README.md)
- [Kubernetes Deployment](./kubernetes.md)
- [Production Checklist](./production.md)
- [Operations Guide](../operations/README.md)